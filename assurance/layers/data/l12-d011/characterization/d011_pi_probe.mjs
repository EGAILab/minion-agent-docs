// HISTORICAL (L12D011-C001, #224 issuecomment-6139260011): this characterization script ran once, in a contained scratch run directory, and its outputs here are its record. Its computed writes were not proven per operation, so it is disabled. The guarded, reproducible evidence is gen/ (run-gen.mjs, gen_spawn_nul.mjs, merge_spawn_nul.mjs, containment-controls.mjs).
throw new Error('historical characterization script: disabled (L12D011-C001); use ../gen');
// L12-D011 (#224) characterization, pinned side: Node v22.15.1 child_process.spawn (the authority for the message)
// and pinned Pi b7bb00b9's real find and bash tool execute bodies (sliced unmodified, exactly as the WP-13.4 search
// probe and the WP-13.3 bash probe do; ensureTool -> the pinned fd 10.4.2, getBinDir stubbed).
// Every NUL case is rejected by Node before a process exists. The only spawns that start a process are none:
// the non-NUL control spawns a nonexistent binary (async ENOENT). No deletes; the only write is the output file,
// proven inside the run dir. cwd must be an existing directory inside the run dir.
//   node --experimental-strip-types d011_pi_probe.mjs <pi checkout> <fd binary> <run dir> <out.json>
import { existsSync, readFileSync, realpathSync, statSync, writeFileSync, constants } from "node:fs";
import { access } from "node:fs/promises";
import { homedir } from "node:os";
import path, { delimiter, isAbsolute, join, relative, resolve as nodeResolvePath, sep } from "node:path";
import { spawn, spawnSync } from "node:child_process";
import { createInterface } from "node:readline";
import { stripTypeScriptTypes } from "node:module";
import { fileURLToPath, pathToFileURL } from "node:url";

const [piDir, fdExe, runDirArg, outPath] = process.argv.slice(2);
const runDir = realpathSync(runDirArg);
const cwd = realpathSync(join(runDir, "cwd"));
const SRC = `${piDir}/packages/coding-agent/src`;
const slice = (src, from, to) => { const a = src.indexOf(from), b = to ? src.indexOf(to, a) : src.length;
  if (a < 0 || b < 0) throw new Error(`slice ${from}`); return src.slice(a, b); };
const ts = (code) => stripTypeScriptTypes(code.replace(/^export /gm, ""));
const { DEFAULT_MAX_BYTES, formatSize, truncateHead } = await import(pathToFileURL(`${SRC}/core/tools/truncate.ts`).href);
const { OutputAccumulator } = await import(pathToFileURL(`${SRC}/core/tools/output-accumulator.ts`).href);

// ---- find (as the WP-13.4 probe) ----
const pathsSrc = readFileSync(`${SRC}/utils/paths.ts`, "utf8");
const { resolvePath } = new Function("realpathSync", "statSync", "homedir", "isAbsolute", "join", "nodeResolvePath",
  "relative", "sep", "fileURLToPath", ts(slice(pathsSrc, "const UNICODE_SPACES", "export function getCwdRelativePath(")) +
  "\nreturn { resolvePath };")(realpathSync, statSync, homedir, isAbsolute, join, nodeResolvePath, relative, sep, fileURLToPath);
const puSrc = readFileSync(`${SRC}/core/tools/path-utils.ts`, "utf8");
const { pathExists, resolveToCwd } = new Function("access", "constants", "resolvePath", ts(
  slice(puSrc, "export async function pathExists(", "export function expandPath(") +
  slice(puSrc, "export function resolveToCwd(", "export function resolveReadPath(")) +
  "\nreturn { pathExists, resolveToCwd };")(access, constants, resolvePath);
const method = (src) => slice(src, "async execute(", "renderCall(args").replace(/\},\s*$/, "}").replace(/^async execute/, "async function execute");
const findSrc = readFileSync(`${SRC}/core/tools/find.ts`, "utf8");
const findExecute = new Function("path", "spawn", "createInterface", "ensureTool", "pathExists", "resolveToCwd", "truncateHead",
  "formatSize", "DEFAULT_MAX_BYTES", "cwd", ts(
    slice(findSrc, "export function relativizeFindResultPath(", "const findSchema") + "const DEFAULT_LIMIT = 1000;\n" +
    slice(findSrc, "const defaultFindOperations", "export interface FindToolOptions") + "const customOps = undefined;\n") +
  `\nreturn (${ts(method(findSrc))});`)(path, spawn, createInterface, async () => fdExe, pathExists, resolveToCwd,
  truncateHead, formatSize, DEFAULT_MAX_BYTES, cwd);

// ---- bash (as the WP-13.3 probe) ----
const shellSrc = readFileSync(`${SRC}/utils/shell.ts`, "utf8");
const shell = new Function("existsSync", "delimiter", "spawn", "spawnSync", "getBinDir", ts(
  slice(shellSrc, "function isLegacyWslBashPath(", "/**\n * Sanitize binary output") +
  slice(shellSrc, "const trackedDetachedChildPids", null)) +
  "\nreturn { getShellConfig, getShellEnv, killProcessTree, trackDetachedChildPid, untrackDetachedChildPid };")(
  existsSync, delimiter, spawn, spawnSync, () => "/pi-bin-stub");
const cpSrc = readFileSync(`${SRC}/utils/child-process.ts`, "utf8");
const { waitForChildProcess } = new Function(ts(slice(cpSrc, "const EXIT_STDIO_GRACE_MS", "export function spawnProcess(") +
  slice(cpSrc, "export function waitForChildProcess(", null)) + "\nreturn { waitForChildProcess };")();
const bashSrc = readFileSync(`${SRC}/core/tools/bash.ts`, "utf8");
const bash = new Function("fsAccess", "constants", "spawn", "getShellConfig", "getShellEnv", "killProcessTree",
  "trackDetachedChildPid", "untrackDetachedChildPid", "waitForChildProcess", ts(
    slice(bashSrc, "const MAX_TIMEOUT_MS", "const bashSchema") +
    slice(bashSrc, "export function createLocalBashOperations(", "export interface BashSpawnContext") +
    slice(bashSrc, "function resolveSpawnContext(", "export interface BashToolOptions")) +
  "\nreturn { resolveTimeoutMs, createLocalBashOperations, resolveSpawnContext };")(
  access, constants, spawn, shell.getShellConfig, shell.getShellEnv, shell.killProcessTree,
  shell.trackDetachedChildPid, shell.untrackDetachedChildPid, waitForChildProcess);
const executeBody = slice(bashSrc, "async execute(", "renderCall(args").replace(/\},\s*$/, "}");
const makeExecute = new Function("cwd", "ops", "commandPrefix", "exposeSessionEnvironment", "spawnHook", "resolveSpawnContext",
  "OutputAccumulator", "formatSize", "DEFAULT_MAX_BYTES", "BASH_UPDATE_THROTTLE_MS",
  "return " + ts(`(async function ${executeBody.replace(/^async /, "")})`));
const THROTTLE = Number(/const BASH_UPDATE_THROTTLE_MS = (\d+);/.exec(bashSrc)[1]);

const rows = [];
const units = (s) => s.length;
const record = (id, kind, f) => rows.push({ id, kind, ...f });

// ---- 1. direct spawn: the authority. file, args, cwd, env; precedence; formatting ----
async function direct(id, file, args, options = {}) {
  try {
    const child = spawn(file, args, { stdio: "ignore", windowsHide: true, ...options });
    const err = await new Promise((res) => { child.once("error", res); child.once("spawn", () => res(null)); });
    if (err === null) { child.kill(); record(id, "direct", { outcome: "STARTED_UNEXPECTEDLY" }); return; }
    record(id, "direct", { outcome: "async_error", code: err.code ?? null, message: err.message });
  } catch (e) {
    record(id, "direct", { outcome: "sync_throw", code: e.code ?? null, name: e.name, message: e.message,
                          message_units: units(e.message) });
  }
}
const N = "\u0000";
const A = (k) => "a".repeat(k);
const env0 = { PATH: process.env.PATH ?? "" };
const D = [
  ["file", "x" + N + "y", []],
  ["args0", "node", ["a" + N]],
  ["args-first-vs-later", "node", ["ok", "b" + N, "c" + N]],
  ["file-and-args", "x" + N, ["a" + N]],
  ["cwd", "node", ["ok"], { cwd: "d" + N }],
  ["args-and-cwd", "node", ["a" + N], { cwd: "d" + N }],
  ["env-value", "node", ["ok"], { env: { ...env0, K: "v" + N } }],
  ["env-name", "node", ["ok"], { env: { ...env0, ["A" + N + "B"]: "v" } }],
  ["env-two-insertion-Z-then-A", "node", ["ok"], { env: { ...env0, Z: "z" + N, A: "a" + N } }],
  ["env-case-dupe-win", "node", ["ok"], { env: { ...env0, k: "lower" + N, K: "upper" + N } }],
  ["env-integer-like-keys", "node", ["ok"], { env: { ...env0, Z: "z" + N, "10": "ten" + N, "2": "two" + N } }],  ["args-and-env", "node", ["a" + N], { env: { ...env0, K: "v" + N } }],
  ["cwd-and-env", "node", ["ok"], { cwd: "d" + N, env: { ...env0, K: "v" + N } }],
  ["argv0", "node", ["ok"], { argv0: "z" + N }],
  // formatting of the inspected value
  ["fmt-single-quote", "node", ["it's" + N]],
  ["fmt-single-and-double", "node", ["it's \"q\"" + N]],
  ["fmt-single-double-backtick", "node", ["it's \"q\" `b`" + N]],
  ["fmt-single-double-dollarbrace", "node", ["it's \"q\" ${x}" + N]],
  ["fmt-backslash", "node", ["C:\\dir\\f" + N]],
  ["fmt-controls", "node", ["\b\t\n\v\f\r\x01\x1f\x7f\x80\x9f\u00a0" + N]],
  ["fmt-lone-high", "node", ["\ud800" + N]],
  ["fmt-lone-low", "node", ["\udc00" + N]],
  ["fmt-pair-and-bmp", "node", ["\u{1F600}\u00e9\u4e2d" + N]],
  ["fmt-regex-path-over-100", "node", ["\t" + "z".repeat(99) + N]],
  ["fmt-quote-in-regex-path", "node", ["'" + "z".repeat(105) + N]],
  ["len-inspected-127", "node", [A(121) + N]],
  ["len-inspected-128", "node", [A(122) + N]],
  ["len-inspected-129", "node", [A(123) + N]],
  ["len-surrogate-straddles-128", "node", [A(126) + "\u{1F600}" + N]],
  ["len-newline-split-over-76", "node", ["line1\n" + "x".repeat(80) + N]],
  ["len-newline-under-77", "node", ["l\n" + "x".repeat(10) + N]],
  ["len-over-maxStringLength", "node", ["y".repeat(10001) + N]],
];
for (const [id, file, args, options] of D) await direct(id, file, args, options);
await direct("control-nonexistent-binary", "minion-d011-nonexistent-binary", ["ok"]);

// ---- 2. Pi tools ----
async function tool(id, run) {
  try { const r = await run(); record(id, "tool", { outcome: "result", text: r.content.map((c) => c.text).join("") }); }
  catch (e) { record(id, "tool", { outcome: "error", code: e?.code ?? null, message: String(e?.message ?? e) }); }
}
const nulPath = cwd.replaceAll("\\", "/") + "/x" + N + "y";
const pre = () => { const c = new AbortController(); c.abort(); return c.signal; };
await tool("pi-find-nul-search-path", () => findExecute("c", { pattern: "*.ts", path: nulPath }, undefined));
await tool("pi-find-nul-pattern", () => findExecute("c", { pattern: "a" + N + "b" }, undefined));
await tool("pi-find-nul-pattern-pre-aborted", () => findExecute("c", { pattern: "a" + N + "b" }, pre()));
const bashExec = () => makeExecute(cwd, bash.createLocalBashOperations({}), undefined, false, undefined,
  bash.resolveSpawnContext, OutputAccumulator, formatSize, DEFAULT_MAX_BYTES, THROTTLE);
await tool("pi-bash-nul-command", () => bashExec()("c", { command: "echo a" + N + "b" }, undefined, () => {}, undefined));
await tool("pi-bash-nul-command-pre-aborted", () => bashExec()("c", { command: "echo a" + N + "b" }, pre(), () => {}, undefined));

// ---- output ----
const out = path.resolve(outPath);
if (!out.startsWith(runDir + path.sep) || realpathSync(path.dirname(out)) !== runDir) throw new Error(`output outside run dir: ${out}`);
const norm = (s) => typeof s === "string" ? s.split(cwd).join("<CWD>").split(cwd.replaceAll("\\", "/")).join("<CWD>") : s;
const shellConfig = shell.getShellConfig(undefined);
writeFileSync(out, JSON.stringify({ platform: process.platform, node: process.versions.node, shell: shellConfig.shell,
  transport: shellConfig.commandTransport ?? "argv", rows: rows.map((r) => ({ ...r, message: norm(r.message), text: norm(r.text) })) }, null, 1) + "\n");
console.log(`d011 pi probe: ${process.platform}, ${rows.length} rows, shell ${shellConfig.shell}`);
