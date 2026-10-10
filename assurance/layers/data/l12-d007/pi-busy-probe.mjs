// L12-D007 focused Windows probe: pinned Pi NodeExecutionEnv under a sharing violation (FileShare.None)
// and a byte-range lock violation. One long-lived holder per condition; every operation is timed.
import fs from "node:fs";
import { spawn } from "node:child_process";
import * as path from "node:path";
import { pathToFileURL } from "node:url";

const [piDir, outPath, scratch] = process.argv.slice(2);
const { NodeExecutionEnv } = await import(pathToFileURL(`${piDir}/packages/agent/src/harness/env/nodejs.ts`).href);

const HOLDERS = {
  "sharing-violation": (p) => `$s=[IO.File]::Open('${p}','Open','ReadWrite','None'); Write-Output ready; Start-Sleep 300`,
  "lock-violation": (p) => `$s=[IO.File]::Open('${p}','Open','ReadWrite','ReadWrite'); $s.Lock(0,64); Write-Output ready; Start-Sleep 300`,
};
const OPS = {
  readTextFile: (env, t) => env.readTextFile(t),
  readTextLines: (env, t) => env.readTextLines(t),
  readBinaryFile: (env, t) => env.readBinaryFile(t),
  writeFile: (env, t) => env.writeFile(t, "w"),
  appendFile: (env, t) => env.appendFile(t, "w"),
  "renameFile-source": (env, t) => env.renameFile(t, "renamed"),
  "renameFile-destination-onto": (env, t, cwd) => { fs.writeFileSync(path.join(cwd, "src"), "s"); return env.renameFile("src", t); },
  fileInfo: (env, t) => env.fileInfo(t),
  exists: (env, t) => env.exists(t),
  listDir: (env, t) => env.listDir(t),
  canonicalPath: (env, t) => env.canonicalPath(t),
  "createDir-recursive": (env, t) => env.createDir(t, { recursive: true }),
  "createDir-nonrecursive": (env, t) => env.createDir(t, { recursive: false }),
  remove: (env, t) => env.remove(t),
  "remove-recursive": (env, t) => env.remove(t, { recursive: true }),
  "remove-force": (env, t) => env.remove(t, { force: true }),
};
const PRIMITIVES = {
  "list_dir_raw(readdir)": (p) => fs.promises.readdir(p),
  "probe_dir_entry(lstat)": (p) => fs.promises.lstat(p),
  "check_readable(access R)": (p) => fs.promises.access(p, fs.constants.R_OK),
  "check_read_write(access RW)": (p) => fs.promises.access(p, fs.constants.R_OK | fs.constants.W_OK),
};

const results = [];
for (const [condition, script] of Object.entries(HOLDERS)) {
  const cwd = fs.mkdtempSync(path.join(scratch, `${condition}-`));
  const target = path.join(cwd, "f");
  fs.writeFileSync(target, "0123456789".repeat(10));
  const holder = spawn("powershell", ["-NoProfile", "-Command", script(target)], { stdio: ["ignore", "pipe", "ignore"] });
  await new Promise((r) => holder.stdout.once("data", r));
  const env = new NodeExecutionEnv({ cwd });
  for (const [op, run] of Object.entries(OPS)) {
    const t = Date.now();
    let observed;
    try {
      const r = await run(env, "f", cwd);
      observed = r.ok ? { ok: true } : { error: r.error.code, message: r.error.message };
    } catch (e) { observed = { threw: String(e) }; }
    results.push({ condition, op, observed, ms: Date.now() - t });
  }
  for (const [op, run] of Object.entries(PRIMITIVES)) {
    const t = Date.now();
    let observed;
    try { await run(target); observed = { ok: true }; } catch (e) { observed = { node_error: e.code }; }
    results.push({ condition, op, observed, ms: Date.now() - t });
  }
  results.push({ condition, op: "holder-alive-at-end", observed: { alive: holder.exitCode === null } });
  holder.kill();
}
fs.writeFileSync(outPath, JSON.stringify({ node: process.version, uv: process.versions.uv, platform: process.platform, results }, null, 1));
for (const r of results) console.log(r.condition.padEnd(18), r.op.padEnd(28), JSON.stringify(r.observed).slice(0, 70), r.ms ?? "", "ms");
