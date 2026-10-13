// L12-D011 (minion-agent#224) canonical generator, one platform per run. Authority: Node v22.15.1 child_process.spawn
// (normalizeSpawnArguments) and pinned Pi b7bb00b9's real find/bash execute bodies (sliced unmodified, as the WP-13.4
// and WP-13.3 probes do; the only substitutions are ensureTool -> the pinned fd and the stubbed getBinDir).
// Every NUL case is rejected by Node before a process exists; the controls spawn a NONEXISTENT binary (async
// ENOENT), so no process ever starts. Writes one partial JSON (proven inside the given out dir); no deletes.
//   node --experimental-strip-types --no-warnings gen_spawn_nul.mjs <pi checkout> <fd binary> <rg binary> <work dir> <out.json>
// <work dir> must exist and contain an empty, .git-free `cwd/` directory (the find tool's working directory).
import { existsSync, readFileSync, realpathSync, statSync, writeFileSync, constants } from "node:fs";
import { access } from "node:fs/promises";
import { homedir } from "node:os";
import path, { delimiter, isAbsolute, join, relative, resolve as nodeResolvePath, sep } from "node:path";
import { spawn, spawnSync } from "node:child_process";
import { createInterface } from "node:readline";
import { stripTypeScriptTypes } from "node:module";
import { fileURLToPath, pathToFileURL } from "node:url";
import { CASES, TOOL_CASES } from "./spawn_nul_cases.mjs";

const [piDir, fdExe, rgExe, workArg, outPath] = process.argv.slice(2);
const work = realpathSync(workArg);
const cwd = realpathSync(join(work, "cwd"));
const SRC = `${piDir}/packages/coding-agent/src`;
const slice = (src, from, to) => { const a = src.indexOf(from), b = to ? src.indexOf(to, a) : src.length;
  if (a < 0 || b < 0) throw new Error(`slice ${from}`); return src.slice(a, b); };
const ts = (code) => stripTypeScriptTypes(code.replace(/^export /gm, ""));
const { DEFAULT_MAX_BYTES, formatSize, truncateHead } = await import(pathToFileURL(`${SRC}/core/tools/truncate.ts`).href);
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
const { truncateLine, GREP_MAX_LINE_LENGTH } = await import(pathToFileURL(`${SRC}/core/tools/truncate.ts`).href);
const { stat: fsStat, readFile: fsReadFile } = await import("node:fs/promises");
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

const PLATFORM = process.platform === "win32" ? "win32" : "linux";
const U = (s) => Array.from({ length: s.length }, (_, i) => s.charCodeAt(i));

// Node's view of one ctx.subprocess.spawn input. argv[0] -> file, argv[1..] -> args; env pairs inserted in order into
// a fresh object (inherit: process.env's entries first, then the overlay, as Minion's effective env is composed).
async function nodeSpawn(c) {
  const [file, ...args] = c.argv;
  const options = { stdio: "ignore", windowsHide: true };
  if (c.cwd !== null) options.cwd = c.cwd;
  if (c.env !== null) {
    const env = c.inherit_env ? { ...process.env } : {};
    for (const [k, v] of c.env) env[k] = v;
    options.env = env;
  }
  try {
    const child = spawn(file, args, options);
    const err = await new Promise((res) => { child.once("error", res); child.once("spawn", () => res(null)); });
    if (err === null) { child.kill(); throw new Error(`a process STARTED for ${c.id}: generator invariant broken`); }
    return { outcome: "async_error", code: err.code ?? null };
  } catch (e) {
    if (e.code !== "ERR_INVALID_ARG_VALUE") throw e;
    return { outcome: "nul_diagnostic", message: U(e.message) };
  }
}

const out = { platform: PLATFORM, node: process.versions.node, shell: shell.getShellConfig(undefined).shell, cases: {}, tools: {} };
for (const c of CASES) {
  if (c.platforms && !c.platforms.includes(PLATFORM)) continue;
  const node = c.pre_aborted ? null : await nodeSpawn(c);
  // Minion's raw-subprocess exception (Owner decision #224 issuecomment-6137796390): the diagnostic of the single
  // retained offending entry, as Node words it for that entry alone.
  const minion = c.minion_offending_entry ? await nodeSpawn({ ...c, env: [c.minion_offending_entry], inherit_env: false }) : null;
  out.cases[c.id] = { node, minion_entry_diagnostic: minion };
}
const pre = () => { const a = new AbortController(); a.abort(); return a.signal; };
for (const t of TOOL_CASES) {
  if (t.platforms && !t.platforms.includes(PLATFORM)) continue;
  if (t.pre_aborted) { out.tools[t.id] = { derived: "pipeline-pre-abort" }; continue; }
  try {
    const r = t.tool === "find"
      ? await findExecute("c", t.arguments[PLATFORM] ?? t.arguments.any, undefined)
      : t.tool === "grep"
      ? await grepExecute("c", t.arguments[PLATFORM] ?? t.arguments.any, undefined)
      : await makeExecute(cwd, bash.createLocalBashOperations({}), undefined, false, undefined, bash.resolveSpawnContext,
          OutputAccumulator, formatSize, DEFAULT_MAX_BYTES, THROTTLE)("c", t.arguments.any, undefined, () => {}, undefined);
    out.tools[t.id] = { outcome: "result", text: U(r.content.map((x) => x.text).join("")) };
  } catch (e) {
    out.tools[t.id] = { outcome: "error", code: e?.code ?? null, text: U(String(e?.message ?? e)) };
  }
}
const dest = path.resolve(outPath);
if (realpathSync(path.dirname(dest)) !== work) throw new Error(`output must be directly inside the work dir: ${dest}`);
writeFileSync(dest, JSON.stringify(out) + "\n");
console.log(`gen_spawn_nul: ${PLATFORM}, ${Object.keys(out.cases).length} cases, ${Object.keys(out.tools).length} tool cases`);
