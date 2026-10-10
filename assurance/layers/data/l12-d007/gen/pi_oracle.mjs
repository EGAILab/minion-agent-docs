// L12-D007 canonical authority (minion-agent#199; #69 / #125 / #67): gen/cases.json through pinned Pi b7bb00b9
// packages/agent/src/harness/env/nodejs.ts NodeExecutionEnv (imported unmodified), Node v22.15.1 / libuv 1.49.2.
//   node --experimental-strip-types pi_oracle.mjs <pi checkout> <cases.json> <out.json>
// Fixture-only steps build the OS condition natively (make_symlink; on Windows hold_exclusive = a FileShare.None
// handle and lock_range = a byte-range lock, each held by a separate PowerShell process until the case ends).
// CONTAINMENT (Owner rule 2026-10-10): the sandbox is created by fs-guard under the project root (or FS_GUARD_ROOT
// inside a container); every step's path and destination is asserted inside its case directory before it runs.
import fs from "node:fs";
import { spawn } from "node:child_process";
import * as path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { PROJECT_ROOT, makeSandbox, assertInside } from "../fs-guard/fs-guard.mjs";

const [piDir, casesPath, outPath] = process.argv.slice(2);
const { NodeExecutionEnv } = await import(pathToFileURL(`${piDir}/packages/agent/src/harness/env/nodejs.ts`).href);

const units = (s) => Array.from({ length: s.length }, (_, i) => s.charCodeAt(i));
const text = (u) => String.fromCharCode(...u);
function observePath(cwd, value) {
  const rel = path.relative(cwd, value);
  if (rel === "") return { components: [] };
  if (rel.startsWith("..") || path.isAbsolute(rel)) return { outside: true };
  return { components: rel.split(path.sep).map(units) };
}
const observeError = (cwd, e) => ({ error: e.code, path: typeof e.path === "string" ? observePath(cwd, e.path) : null });
const okOr = (cwd, r, f) => (r.ok ? f(r.value) : observeError(cwd, r.error));

const HOLD = {
  hold_exclusive: (p) => `$s=[IO.File]::Open('${p}','Open','ReadWrite','None'); Write-Output ready; Start-Sleep 300`,
  lock_range: (p) => `$s=[IO.File]::Open('${p}','Open','ReadWrite','ReadWrite'); $s.Lock(0,64); Write-Output ready; Start-Sleep 300`,
};
async function hold(kind, target, holders) {
  if (process.platform !== "win32") throw new Error(`${kind} is a win32-only fixture`);
  const proc = spawn("powershell", ["-NoProfile", "-Command", HOLD[kind](target)], { stdio: ["ignore", "pipe", "ignore"] });
  holders.push(proc);
  const ready = await Promise.race([new Promise((r) => proc.stdout.once("data", () => r(true))),
    new Promise((r) => setTimeout(() => r(false), 20000))]);
  if (!ready) throw new Error(`${kind} holder not ready`);
  return { ok: null };
}

async function run(env, cwd, step, holders) {
  const p = text(step.path.utf16);
  const target = assertInside(cwd, p);
  if (step.to) assertInside(cwd, text(step.to.utf16));
  switch (step.op) {
    case "make_symlink": fs.symlinkSync(text(step.to.utf16), target); return { ok: null };
    case "hold_exclusive": case "lock_range": return hold(step.op, target, holders);
    case "write_file": return okOr(cwd, await env.writeFile(p, text(step.content)), () => ({ ok: null }));
    case "append_file": return okOr(cwd, await env.appendFile(p, text(step.content)), () => ({ ok: null }));
    case "read_text_file": return okOr(cwd, await env.readTextFile(p), (v) => ({ ok: units(v) }));
    case "read_text_lines": return okOr(cwd, await env.readTextLines(p, {}), (v) => ({ ok: v.map(units) }));
    case "read_binary_file": return okOr(cwd, await env.readBinaryFile(p), (v) => ({ ok: Array.from(v) }));
    case "rename_file": return okOr(cwd, await env.renameFile(p, text(step.to.utf16)), () => ({ ok: null }));
    case "file_info": return okOr(cwd, await env.fileInfo(p), (v) => ({ kind: v.kind, name: units(v.name) }));
    case "exists": return okOr(cwd, await env.exists(p), (v) => ({ ok: v }));
    case "list_dir": return okOr(cwd, await env.listDir(p), (v) => ({ names: v.map((i) => units(i.name)).sort() }));
    case "canonical_path": return okOr(cwd, await env.canonicalPath(p), (v) => observePath(cwd, v));
    case "create_dir": return okOr(cwd, await env.createDir(p, { recursive: step.recursive }), () => ({ ok: null }));
    case "remove": return okOr(cwd, await env.remove(p, { recursive: step.recursive ?? false, force: step.force ?? false }), () => ({ ok: null }));
    default: throw new Error(`op ${step.op}`);
  }
}

const platform = process.platform === "win32" ? "win32" : "linux";
const cases = JSON.parse(fs.readFileSync(casesPath, "utf8")).cases.filter((c) => c.platforms.includes(platform));
const root = fs.realpathSync(makeSandbox(path.join(PROJECT_ROOT, ".tmp", "l12d007-oracle", `run-${Date.now()}`)));
const results = [];
for (const [n, c] of cases.entries()) {
  const cwd = path.join(root, String(n));
  fs.mkdirSync(cwd);
  const env = new NodeExecutionEnv({ cwd });
  const holders = [];
  const observed = [];
  try {
    for (const step of c.steps) observed.push(await run(env, cwd, step, holders));
  } finally {
    for (const h of holders) h.kill();
  }
  results.push({ id: c.id, observed });
}
await new Promise((r) => setTimeout(r, 500)); // let killed holders release their handles
assertInside(path.dirname(root), root);
fs.rmSync(root, { recursive: true, force: true });
fs.writeFileSync(outPath, JSON.stringify({ platform, node: process.versions.node, uv: process.versions.uv,
  pi: "b7bb00b936dbe21b8e160b3e89efdec361846699", results }, null, 1) + "\n");
console.log(`l12-d007 oracle (${platform}): ${results.length} cases`);
