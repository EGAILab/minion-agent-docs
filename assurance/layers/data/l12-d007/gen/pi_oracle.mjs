// L12-D007 canonical authority (minion-agent#199; #69 / #125 / #67): gen/cases.json through pinned Pi b7bb00b9
// packages/agent/src/harness/env/nodejs.ts NodeExecutionEnv (imported unmodified), Node v22.15.1 / libuv 1.49.2.
//   node --experimental-strip-types pi_oracle.mjs <pi checkout> <cases.json> <out.json>
// Fixture-only steps build the OS condition natively (make_symlink; on Windows hold_exclusive = a FileShare.None
// handle and lock_range = a byte-range lock, each held by a separate PowerShell process until the case ends).
// CONTAINMENT (Owner rule 2026-10-10): the sandbox is created by fs-guard under the project root (or FS_GUARD_ROOT
// inside a container); every step's path and destination is asserted inside its case directory before it runs.
import fs from "node:fs";
import { execFileSync, spawn } from "node:child_process";
import * as path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { PROJECT_ROOT, makeSandbox, assertInside, assertOutput } from "../fs-guard/fs-guard.mjs";

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

// A directory cannot be opened through [IO.File]::Open, so its no-sharing hold is CreateFileW with
// FILE_FLAG_BACKUP_SEMANTICS (read+write, share none), through P/Invoke.
const DIR_HOLD = (p) => "$sig='[DllImport(\"kernel32.dll\",SetLastError=true,CharSet=CharSet.Unicode)] public static extern " +
  "Microsoft.Win32.SafeHandles.SafeFileHandle CreateFileW(string n,uint a,uint s,IntPtr sa,uint d,uint f,IntPtr t);'; " +
  "$ErrorActionPreference='Stop'; $k=Add-Type -MemberDefinition $sig -Name K -Namespace W -PassThru; " +
  // [uint32] literals: PowerShell 5.1 reads 0xC0000000 as a NEGATIVE Int32, whose conversion fails.
  `$h=$k::CreateFileW('${p}',[uint32]3221225472,[uint32]0,[IntPtr]::Zero,[uint32]3,[uint32]33554432,[IntPtr]::Zero); ` +
  "if ($h -eq $null -or $h.IsInvalid) { exit 1 }; Write-Output ready; Start-Sleep 300";
const HOLD = {
  hold_exclusive: (p) => (fs.statSync(p).isDirectory() ? DIR_HOLD(p)
    : `$s=[IO.File]::Open('${p}','Open','ReadWrite','None'); Write-Output ready; Start-Sleep 300`),
  lock_range: (p) => `$s=[IO.File]::Open('${p}','Open','ReadWrite','ReadWrite'); $s.Lock(0,64); Write-Output ready; Start-Sleep 300`,
};
// deny_access: Windows denies Everyone read (`icacls /deny *S-1-1-0:(R)`); POSIX removes every mode
// bit (chmod 000; meaningful only for a non-root user). Each is undone at case end so cleanup works.
function denyAccess(target, releases) {
  if (process.platform === "win32") {
    execFileSync("icacls", [target, "/deny", "*S-1-1-0:(R)"], { stdio: "ignore" });
    releases.push(() => { try { execFileSync("icacls", [target, "/remove:d", "*S-1-1-0"], { stdio: "ignore" }); } catch {} });
  } else {
    const mode = fs.statSync(target).mode & 0o777;
    fs.chmodSync(target, 0);
    releases.push(() => { try { fs.chmodSync(target, mode); } catch {} });
  }
  return { ok: null };
}
async function hold(kind, target, holders) {
  if (process.platform !== "win32") throw new Error(`${kind} is a win32-only fixture`);
  const proc = spawn("powershell", ["-NoProfile", "-Command", HOLD[kind](target)], { stdio: ["ignore", "pipe", "ignore"] });
  holders.push(() => proc.kill());
  // Fail closed: only the holder's exact "ready" line (printed after its handle is verified) counts;
  // any other output or an early exit is not readiness.
  let seen = "";
  const ready = await Promise.race([new Promise((r) => {
    proc.stdout.on("data", (b) => { seen += b; if (/^ready\r?$/m.test(seen)) r(true); });
    proc.once("exit", () => r(false));
  }),
    new Promise((r) => setTimeout(() => r(false), 20000))]);
  if (!ready) throw new Error(`${kind} holder not ready`);
  return { ok: null };
}

async function run(env, cwd, step, holders) {
  const p = text(step.path.utf16);
  const target = assertInside(cwd, p);
  if (step.to) {
    // A rename destination resolves from the case directory; a symlink's text from the link's own
    // directory. Both must stay inside the case directory, through every link.
    assertInside(cwd, text(step.to.utf16), step.op === "make_symlink" ? path.dirname(target) : cwd);
  }
  switch (step.op) {
    case "make_symlink": fs.symlinkSync(text(step.to.utf16), target); return { ok: null };
    case "hold_exclusive": case "lock_range": return hold(step.op, target, holders);
    case "deny_access": return denyAccess(target, holders);
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
  const cwd = assertInside(root, String(n));
  fs.mkdirSync(cwd);
  const env = new NodeExecutionEnv({ cwd });
  const holders = [];
  const observed = [];
  try {
    for (const step of c.steps) observed.push(await run(env, cwd, step, holders));
  } finally {
    for (const release of holders.reverse()) release();
  }
  results.push({ id: c.id, observed });
}
await new Promise((r) => setTimeout(r, 500)); // let killed holders release their handles
assertInside(path.dirname(root), path.basename(root)); // the guard refuses absolute raw targets
// A deny_access fixture whose entry the operation under test MOVED (rename) is not undone by its
// case-end release; restore access across this run's own sandbox only, then remove it. Failures
// leave the sandbox in place (it is under the project's .tmp) rather than losing the results.
try {
  if (process.platform === "win32") execFileSync("icacls", [root, "/reset", "/T", "/C", "/Q"], { stdio: "ignore" });
  else {
    const open = (p) => { fs.chmodSync(p, 0o700); if (fs.lstatSync(p).isDirectory()) for (const e of fs.readdirSync(p)) { const q = assertInside(root, path.relative(root, path.join(p, e))); if (!fs.lstatSync(q).isSymbolicLink()) open(q); } };
    open(root);
  }
  fs.rmSync(root, { recursive: true, force: true });
} catch (e) {
  console.error(`sandbox left in place (${e.code ?? e.message}): ${root}`);
}
fs.writeFileSync(assertOutput(outPath), JSON.stringify({ platform, node: process.versions.node, uv: process.versions.uv,
  pi: "b7bb00b936dbe21b8e160b3e89efdec361846699", results }, null, 1) + "\n");
console.log(`l12-d007 oracle (${platform}): ${results.length} cases`);
