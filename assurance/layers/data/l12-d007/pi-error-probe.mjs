// L12-D007 characterization (minion-agent#199; #69 / #125 / #67): pinned Pi's literal toFileError codes for the Layer 12
// error-condition family, through the REAL NodeExecutionEnv (b7bb00b9 packages/agent/src/harness/env/nodejs.ts).
//   node --experimental-strip-types pi-error-probe.mjs <pi checkout> <out.json>
// Each condition is prepared natively in a fresh case directory; every operation then runs on its target. Recorded
// per case: the Result (ok, or code + path as UTF-16 components relative to the case directory) and Node's raw error
// code (err.code from a direct fs call with the same argument, for the libuv / Node-override audit).
import fs from "node:fs";
import { execFileSync, spawn } from "node:child_process";
import { tmpdir } from "node:os";
import * as path from "node:path";
import { pathToFileURL } from "node:url";
import { PROJECT_ROOT, makeSandbox, assertInside, assertOutput } from "./fs-guard/fs-guard.mjs";

const [piDir, outPath] = process.argv.slice(2);
const { NodeExecutionEnv } = await import(pathToFileURL(`${piDir}/packages/agent/src/harness/env/nodejs.ts`).href);
const win = process.platform === "win32";
const units = (s) => Array.from({ length: s.length }, (_, i) => s.charCodeAt(i));

// Conditions: setup(cwd) prepares the fixture and returns { target, cleanup? }.
// Every fixture path passes the guard BEFORE its native write (L12D007-C001).
const at = (cwd, rel, from = cwd) => assertInside(cwd, rel, from);
const CONDITIONS = {
  "missing": () => ({ target: "missing" }),
  "file": (cwd) => { fs.writeFileSync(at(cwd, "f"), "x"); return { target: "f" }; },
  "directory-empty": (cwd) => { fs.mkdirSync(at(cwd, "d")); return { target: "d" }; },
  "directory-nonempty": (cwd) => { fs.mkdirSync(at(cwd, "d")); fs.writeFileSync(at(cwd, "d/c"), "x"); return { target: "d" }; },
  "non-directory-component": (cwd) => { fs.writeFileSync(at(cwd, "f"), "x"); return { target: "f/x" }; },
  // Relative link texts, each checked from the link's own directory; the loop never leaves cwd.
  "symlink-loop": (cwd) => { at(cwd, "b"); fs.symlinkSync("b", at(cwd, "a")); at(cwd, "a"); fs.symlinkSync("a", at(cwd, "b")); return { target: "a" }; },
  "name-too-long": () => ({ target: "n".repeat(300) }),
  ...(win ? {
    "invalid-name": () => ({ target: "x<y" }),
    // "./" keeps "f:" from parsing as drive F:. (A former "bad-pathname" case used a ".."-chain that escaped to
    // the drive root and was removed after it ran destructive operations on E:\ -- see fs-guard.mjs.)
    "ntfs-stream-syntax": (cwd) => { fs.writeFileSync(at(cwd, "f"), "x"); return { target: "./f:stream:bad" }; },
    "sharing-violation": (cwd) => {
      const p = at(cwd, "f"); fs.writeFileSync(p, "x");
      // Hold the file open with FileShare.None in another process for the duration of the case.
      const holder = spawn("powershell", ["-NoProfile", "-Command",
        `$s=[IO.File]::Open('${p}','Open','ReadWrite','None'); Write-Output ready; Start-Sleep 120`], { stdio: ["ignore", "pipe", "ignore"] });
      return { target: "f", ready: new Promise((r) => holder.stdout.once("data", r)), cleanup: () => holder.kill() };
    },
    "lock-violation": (cwd) => {
      const p = at(cwd, "f"); fs.writeFileSync(p, "xxxxxxxx");
      const holder = spawn("powershell", ["-NoProfile", "-Command",
        `$s=[IO.File]::Open('${p}','Open','ReadWrite','ReadWrite'); $s.Lock(0,8); Write-Output ready; Start-Sleep 120`], { stdio: ["ignore", "pipe", "ignore"] });
      return { target: "f", ready: new Promise((r) => holder.stdout.once("data", r)), cleanup: () => holder.kill() };
    },
  } : {}),
};

const OPS = {
  readTextFile: (env, t) => env.readTextFile(t),
  readTextLines: (env, t) => env.readTextLines(t),
  readBinaryFile: (env, t) => env.readBinaryFile(t),
  writeFile: (env, t) => env.writeFile(t, "w"),
  appendFile: (env, t) => env.appendFile(t, "w"),
  "renameFile-source": (env, t) => env.renameFile(t, "renamed"),
  "renameFile-destination-onto": (env, t, cwd) => { fs.writeFileSync(assertInside(cwd, "src"), "s"); return env.renameFile("src", t); },
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
// The Node primitive each Minion-only operation maps (EXEC-007/008/009), observed directly with Pi's toFileError rule.
const PRIMITIVES = {
  "list_dir_raw(readdir)": (p) => fs.promises.readdir(p),
  "probe_dir_entry(lstat)": (p) => fs.promises.lstat(p),
  "check_readable(access R)": (p) => fs.promises.access(p, fs.constants.R_OK),
  "check_read_write(access RW)": (p) => fs.promises.access(p, fs.constants.R_OK | fs.constants.W_OK),
};

function observe(cwd, r) {
  if (r.ok) return { ok: true };
  const e = r.error;
  return { error: e.code, path: typeof e.path === "string" ? path.relative(cwd, e.path).split(path.sep).map(units) : null };
}

const root = fs.realpathSync(makeSandbox(path.join(PROJECT_ROOT, ".tmp", "claude-scratch", "l12d007", `sandbox-${Date.now()}`)));
const results = [];
let n = 0;
const started = Date.now();
try { fs.unlinkSync(assertOutput(outPath + ".jsonl")); } catch {}
for (const [condition, setup] of Object.entries(CONDITIONS)) {
  for (const [op, run] of [...Object.entries(OPS), ...Object.entries(PRIMITIVES).map(([k, f]) => [k, null, f])]) {
    const cwd = assertInside(root, String(n++));
    fs.mkdirSync(cwd);
    let prepared;
    try { prepared = setup(cwd); } catch (e) { results.push({ condition, op, setup_failed: String(e) }); continue; }
    if (prepared.ready) {
      const ready = await Promise.race([prepared.ready.then(() => true), new Promise((r) => setTimeout(() => r(false), 15000))]);
      if (!ready) { prepared.cleanup?.(); results.push({ condition, op, setup_failed: "holder not ready within 15s" }); continue; }
    }
    // Containment: every path any operation can touch must stay strictly inside this case directory.
    try {
      for (const t of [prepared.target, "renamed", "src"]) assertInside(cwd, t);
    } catch (e) { prepared.cleanup?.(); results.push({ condition, op, setup_failed: String(e) }); continue; }
    const env = new NodeExecutionEnv({ cwd });
    let observed, node_code = null;
    try {
      if (run) {
        const guard = new Promise((_, reject) => setTimeout(() => reject(new Error("operation exceeded 20s")), 20000));
        observed = observe(cwd, await Promise.race([run(env, prepared.target, cwd), guard]));
      } else {
        const primitive = PRIMITIVES[op];
        try { await primitive(path.resolve(cwd, prepared.target)); observed = { ok: true }; }
        catch (e) { node_code = e.code ?? null; observed = { node_error: e.code ?? String(e) }; }
      }
    } catch (e) { observed = { threw: `${e?.code ?? ""} ${e?.message}` }; }
    if (run) {
      // The raw Node code for the same operation's primary fs call, for the libuv / override audit.
      try { await fs.promises.lstat(path.resolve(cwd, prepared.target)); } catch (e) { node_code = e.code ?? null; }
    }
    prepared.cleanup?.();
    results.push({ condition, op, observed, lstat_code: node_code });
    fs.appendFileSync(assertOutput(outPath + ".jsonl"), JSON.stringify(results.at(-1)) + "\n");
    console.log(`${condition} ${op} ${JSON.stringify(observed).slice(0, 60)} (${Math.round((Date.now() - started) / 1000)}s)`);
  }
}
assertInside(path.dirname(root), path.basename(root)); // the guard refuses absolute raw targets
try { fs.rmSync(root, { recursive: true, force: true }); } catch {}
fs.writeFileSync(assertOutput(outPath), JSON.stringify({ platform: process.platform, node: process.versions.node, uv: process.versions.uv,
  pi: "b7bb00b936dbe21b8e160b3e89efdec361846699", results }, null, 1) + "\n");
console.log(`l12-d007 pi probe (${process.platform}): ${results.length} rows`);
