// L12-D011 (minion-agent#224) canonical generator, one platform per run. Authority:
//   - Node v22.15.1 child_process.spawn (normalizeSpawnArguments / ERR_INVALID_ARG_VALUE / util.inspect): the literal
//     diagnostic of each NUL-bearing input, obtained IN ISOLATION (only that input invalid), plus Node's own
//     whole-call outcome as contrast evidence;
//   - pinned Pi b7bb00b9 agent/src/harness/env/nodejs.ts resolvePath (sliced unmodified): the certified effective-cwd
//     resolution (spec section 6: ctx.subprocess cwd uses ctx.fs absolute_path's rule);
//   - pinned Pi coding-agent find/grep/bash execute bodies (sliced unmodified; ensureTool -> the pinned engines).
// Selection among several invalid inputs is NOT done here: merge_spawn_nul.mjs applies the contract's order.
// Every spawn either throws ERR_INVALID_ARG_VALUE before a process exists or targets a NONEXISTENT executable (async
// ENOENT); a process that starts aborts the run. The ONE write is io.writeOutput (fs-guard assertOutput first).
//   node --experimental-strip-types --no-warnings gen_spawn_nul.mjs <pi checkout> <fd> <rg> <work dir> <out.json>
// <work dir> contains an empty, .git-free `cwd/` (the tools' working directory).
import { existsSync, readFileSync, realpathSync, statSync, constants } from "node:fs";
import { access, stat as fsStat, readFile as fsReadFile } from "node:fs/promises";
import { homedir } from "node:os";
import path, { delimiter, isAbsolute, join, relative, resolve, resolve as nodeResolvePath, sep } from "node:path";
import { spawn, spawnSync } from "node:child_process";
import { createInterface } from "node:readline";
import { stripTypeScriptTypes } from "node:module";
import { fileURLToPath, pathToFileURL } from "node:url";
import { CASES, TOOL_CASES, pick } from "./spawn_nul_cases.mjs";
import { writeOutput } from "./io.mjs";

const here = path.dirname(fileURLToPath(import.meta.url));
const guard = await import(pathToFileURL(path.join(here, "../../l12-d007/fs-guard/fs-guard.mjs")).href);
const [piDir, fdExe, rgExe, workArg, outPath] = process.argv.slice(2);
const cwd = realpathSync(join(workArg, "cwd"));
const SRC = `${piDir}/packages/coding-agent/src`;
const slice = (src, from, to) => { const a = src.indexOf(from), b = to ? src.indexOf(to, a) : src.length;
  if (a < 0 || b < 0) throw new Error(`slice ${from}`); return src.slice(a, b); };
const ts = (code) => stripTypeScriptTypes(code.replace(/^export /gm, ""));
const PLATFORM = process.platform === "win32" ? "win32" : "linux";
const U = (s) => Array.from({ length: s.length }, (_, i) => s.charCodeAt(i));
const N = "\u0000";

// ---- certified cwd resolution: Pi nodejs.ts resolvePath(cwd, path) ----
const harnessSrc = readFileSync(`${piDir}/packages/agent/src/harness/env/nodejs.ts`, "utf8");
const resolveCwd = new Function("homedir", "join", "fileURLToPath", "isAbsolute", "resolve", "process",
  ts(slice(harnessSrc, "function resolvePath(cwd: string, path: string): string {", "function fileKindFromStats(")) +
  "\nreturn resolvePath;")(homedir, join, fileURLToPath, isAbsolute, resolve, process);

// ---- Pi tools (as the WP-13.4 / WP-13.3 probes) ----
const { DEFAULT_MAX_BYTES, formatSize, truncateHead, truncateLine, GREP_MAX_LINE_LENGTH } =
  await import(pathToFileURL(`${SRC}/core/tools/truncate.ts`).href);
const { OutputAccumulator } = await import(pathToFileURL(`${SRC}/core/tools/output-accumulator.ts`).href);
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
const grepSrc = readFileSync(`${SRC}/core/tools/grep.ts`, "utf8");
const grepExecute = new Function("path", "spawn", "createInterface", "ensureTool", "resolveToCwd", "truncateHead", "truncateLine",
  "formatSize", "DEFAULT_MAX_BYTES", "GREP_MAX_LINE_LENGTH", "fsStat", "fsReadFile", "cwd", ts(
    "const DEFAULT_LIMIT = 100;\n" +
    slice(grepSrc, "const defaultGrepOperations", "export interface GrepToolOptions") + "const customOps = undefined;\n") +
  `\nreturn (${ts(method(grepSrc))});`)(path, spawn, createInterface, async () => rgExe, resolveToCwd, truncateHead,
  truncateLine, formatSize, DEFAULT_MAX_BYTES, GREP_MAX_LINE_LENGTH, fsStat, fsReadFile, cwd);
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

// ---- Node spawn observations ----
const X = "minion-d011-nonexistent";
// An env object of OWN, enumerable properties in the given order (a name such as __proto__ is an own property).
function envObject(pairs) {
  const o = Object.create(null);
  for (const [k, v] of pairs) Object.defineProperty(o, k, { value: v, enumerable: true, writable: true, configurable: true });
  return o;
}
async function nodeSpawn(file, args, options) {
  try {
    const child = spawn(file, args, { stdio: "ignore", windowsHide: true, ...options });
    const err = await new Promise((res) => { child.once("error", res); child.once("spawn", () => res(null)); });
    if (err === null) { child.kill(); throw new Error(`INVARIANT: a process started (${file})`); }
    if (typeof err.code !== "string") throw new Error(`INVARIANT: async error without a code (${file})`);
    return { outcome: "async_error", code: err.code };
  } catch (e) {
    if (e.code !== "ERR_INVALID_ARG_VALUE") throw e;
    return { outcome: "nul_diagnostic", message: U(e.message) };
  }
}
const diag = async (file, args, options) => {
  const r = await nodeSpawn(file, args, options);
  if (r.outcome !== "nul_diagnostic") throw new Error(`INVARIANT: an isolated NUL input produced ${JSON.stringify(r)}`);
  return r.message;
};
// The effective environment's ENTRIES (values after the overlay), with ownership; selection order is the merge's.
function effectiveEntries(c) {
  const out = new Map();
  if (c.inherit_env && c.baseline) for (const [k, v] of c.baseline) out.set(k, { value: v, owner: "baseline" });
  if (c.env) for (const [k, v] of c.env) out.set(k, { value: v, owner: "overlay" });
  return out;
}

const result = { platform: PLATFORM, node: process.versions.node, shell: shell.getShellConfig(undefined).shell, cases: {}, tools: {} };
for (const c of CASES) {
  const argv = c.argv.map((v) => pick(v, PLATFORM));
  const provider = pick(c.provider_cwd, PLATFORM);
  const supplied = c.cwd === null ? null : pick(c.cwd, PLATFORM);
  const effectiveCwd = supplied === null ? provider : resolveCwd(provider, supplied);
  // env: an ORDERED list of [name, diagnostic] pairs, never a plain object (a name such as __proto__ is data).
  const rec = { effective_cwd: U(effectiveCwd), file: null, args: {}, cwd: null, env: [] };
  if (argv[0].includes(N)) rec.file = await diag(argv[0], []);
  for (let j = 1; j < argv.length; j++) {
    if (argv[j].includes(N)) rec.args[j] = await diag(X, [...Array(j - 1).fill("ok"), argv[j]]);
  }
  if (effectiveCwd.includes(N)) rec.cwd = await diag(X, [], { cwd: effectiveCwd });
  for (const [name, { value }] of effectiveEntries(c)) {
    if (name.includes(N) || value.includes(N)) rec.env.push([name, await diag(X, [], { env: envObject([[name, value]]) })]);
  }
  // Node's own whole call (contrast only): raw supplied cwd (a string, not a URL object) or the provider cwd;
  // env composed as JavaScript object assignment would (baseline / process.env first, then the overlay).
  if (!c.pre_aborted) {
    const options = { cwd: supplied ?? provider };
    if (c.env !== null || c.baseline !== null || !c.inherit_env) {
      const base = c.inherit_env ? (c.baseline ?? Object.entries(process.env)) : [];
      const merged = new Map(base);
      for (const [k, v] of c.env ?? []) merged.set(k, v);
      options.env = envObject([...merged]);
    }
    rec.node_whole_call = await nodeSpawn(argv[0], argv.slice(1), options);
  }
  result.cases[c.id] = rec;
}
for (const t of TOOL_CASES) {
  if (t.pre_aborted) { result.tools[t.id] = { derived: "pipeline-pre-abort" }; continue; }
  const args = t.arguments[PLATFORM] ?? t.arguments.any;
  try {
    const r = t.tool === "find" ? await findExecute("c", args, undefined)
      : t.tool === "grep" ? await grepExecute("c", args, undefined)
      : await makeExecute(cwd, bash.createLocalBashOperations({}), undefined, false, undefined, bash.resolveSpawnContext,
          OutputAccumulator, formatSize, DEFAULT_MAX_BYTES, THROTTLE)("c", args, undefined, () => {}, undefined);
    result.tools[t.id] = { outcome: "result", text: U(r.content.map((x) => x.text).join("")) };
  } catch (e) {
    result.tools[t.id] = { outcome: "error", code: e?.code ?? null, text: U(String(e?.message ?? e)) };
  }
}
writeOutput(guard, outPath, JSON.stringify(result) + "\n");
console.log(`gen_spawn_nul: ${PLATFORM}, ${Object.keys(result.cases).length} cases, ${Object.keys(result.tools).length} tool cases`);
