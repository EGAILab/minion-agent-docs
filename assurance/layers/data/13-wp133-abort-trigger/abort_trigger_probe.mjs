// WP-13.3 (bash, minion-agent#50) pinned-Pi characterization probe. Pinned Pi b7bb00b9's own code under Node v22.15.1:
//   core/tools/truncate.ts, core/tools/output-accumulator.ts  imported whole (Node built-ins only)
//   utils/shell.ts      getShellConfig/getBashShellConfig/isLegacyWslBashPath/findBashOnPath/getShellEnv/killProcessTree/
//                       track/untrack, sliced unmodified; the only non-built-in import, getBinDir (config.ts), stubbed
//   utils/child-process.ts  waitForChildProcess, sliced unmodified
//   core/tools/bash.ts  resolveTimeoutMs, createLocalBashOperations, resolveSpawnContext and the tool's execute body,
//                       sliced unmodified (the TUI render functions are not reached by execute)
// Each case runs the real tool execute in a fresh working directory; observations: the result (or thrown error) text
// with the temp path normalized, details, the temp file's bytes (sha256/size) when present, and the update sequence.
// Derived for TEST-BASH-ABORT-TIMING (minion-agent#197): only the abort cases, with the output-event trigger
// `abortOnOutput` beside the original timer; sandboxes inside the project root through the reviewed fs-guard.
//   node --experimental-strip-types abort_trigger_probe.mjs <pi checkout> <scratch dir in the project> <out.json> [repeat]
import { createHash } from "node:crypto";
import { existsSync, mkdtempSync, readFileSync, realpathSync, writeFileSync } from "node:fs";
import { access } from "node:fs/promises";
import { constants } from "node:fs";
import { makeSandbox, cleanupSandbox } from "../l12-d007/fs-guard/fs-guard.mjs";
import { delimiter, join } from "node:path";
import { spawn, spawnSync } from "node:child_process";
import { stripTypeScriptTypes } from "node:module";
import { pathToFileURL } from "node:url";

const [piDir, scratch, outPath, repeatArg = "5"] = process.argv.slice(2);
const REPEAT = Number(repeatArg);
const SRC = `${piDir}/packages/coding-agent/src`;
const { DEFAULT_MAX_BYTES, DEFAULT_MAX_LINES, formatSize } = await import(pathToFileURL(`${SRC}/core/tools/truncate.ts`).href);
const { OutputAccumulator } = await import(pathToFileURL(`${SRC}/core/tools/output-accumulator.ts`).href);
const slice = (src, from, to) => { const a = src.indexOf(from), b = to ? src.indexOf(to, a) : src.length;
  if (a < 0 || b < 0) throw new Error(`slice ${from}`); return src.slice(a, b); };
const ts = (code) => stripTypeScriptTypes(code.replace(/^export /gm, ""));

const PI_BIN = "/pi-bin-stub";
const shellSrc = readFileSync(`${SRC}/utils/shell.ts`, "utf8");
const shell = new Function("existsSync", "delimiter", "spawn", "spawnSync", "getBinDir", ts(
  slice(shellSrc, "function isLegacyWslBashPath(", "/**\n * Sanitize binary output") +
  slice(shellSrc, "const trackedDetachedChildPids", null)) +
  "\nreturn { getShellConfig, getShellEnv, killProcessTree, trackDetachedChildPid, untrackDetachedChildPid };")(
  existsSync, delimiter, spawn, spawnSync, () => PI_BIN);
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
// The tool's execute body (an object-literal method) as a standalone function over the factory's closure variables.
const executeBody = slice(bashSrc, "async execute(", "renderCall(args").replace(/\},\s*$/, "}");
const makeExecute = new Function("cwd", "ops", "commandPrefix", "exposeSessionEnvironment", "spawnHook", "resolveSpawnContext",
  "OutputAccumulator", "formatSize", "DEFAULT_MAX_BYTES", "BASH_UPDATE_THROTTLE_MS",
  "return " + ts(`(async function ${executeBody.replace(/^async /, "")})`));
const BASH_UPDATE_THROTTLE_MS = Number(/const BASH_UPDATE_THROTTLE_MS = (\d+);/.exec(bashSrc)[1]);

const U = (s) => Array.from({ length: s.length }, (_, i) => s.charCodeAt(i));
const CASES = [
  ["abort/during-timer-400ms", "printf 'before\\n'; sleep 5", { abortAfterMs: 400 }],
  ["abort/during-on-output", "printf 'before\\n'; sleep 5", { abortOnOutput: "before" }],
];

const results = [];
for (const [id, command, opt = {}] of CASES) for (let run = 1; run <= REPEAT; run++) {
  const base = realpathSync(makeSandbox(join(scratch, `wp133-abort-${process.pid}-${id.replace('/', '-')}-${run}`)));
  const cwd = opt.missingCwd ? join(base, "missing") : base;
  const ops = bash.createLocalBashOperations({});
  const execute = makeExecute(cwd, ops, undefined, false, undefined, bash.resolveSpawnContext,
    OutputAccumulator, formatSize, DEFAULT_MAX_BYTES, BASH_UPDATE_THROTTLE_MS);
  const controller = new AbortController();
  if (opt.preAbort) controller.abort();
  if (opt.abortAfterMs) setTimeout(() => controller.abort(), opt.abortAfterMs);
  const updates = [];
  const onUpdate = (u) => {
    updates.push({ text: u.content[0]?.text ?? null, hasDetails: u.details !== undefined });
    if (opt.abortOnOutput && (u.content[0]?.text ?? "").includes(opt.abortOnOutput)) controller.abort();
  };
  const args = { command, ...(opt.timeout !== undefined ? { timeout: opt.timeout } : {}) };
  const out = { id, run, command, timeout: opt.timeout === Infinity ? "Infinity" : opt.timeout ?? null };
  let text, details, isError;
  try {
    const r = await execute("call", args, controller.signal, onUpdate, undefined);
    text = r.content[0].text; details = r.details; isError = false;
  } catch (e) { text = e.message; isError = true; }
  const fullPath = details?.fullOutputPath ?? (/Full output: ([^\]]+)\]/.exec(text) ?? [])[1];
  if (fullPath) {
    const bytes = readFileSync(fullPath);
    out.full_output = { size: bytes.length, sha256: createHash("sha256").update(bytes).digest("hex"),
                        name_pattern: /^pi-bash-[0-9a-f]{16}\.log$/.test(fullPath.split(/[\\/]/).pop()) };
    text = text.split(fullPath).join("<FULL_OUTPUT>");
  }
  out.is_error = isError;
  out.text = text.length > 4000 ? { head: U(text.slice(0, 200)), tail: U(text.slice(-400)), length: text.length } : U(text);
  out.details = details ? { truncation: details.truncation && Object.fromEntries(Object.entries(details.truncation)
    .filter(([k]) => k !== "content")), full_output_path: details.fullOutputPath ? "<FULL_OUTPUT>" : null } : null;
  out.update_count = updates.length;
  out.first_update = updates[0] ?? null;
  if (opt.observeUpdates) out.updates = updates.map((u) => ({ text: u.text === null ? null : U(u.text), hasDetails: u.hasDetails }));
  results.push(out);
  if (!cleanupSandbox(base)) process.exitCode = 1;
}
const shellConfig = shell.getShellConfig(undefined);
writeFileSync(outPath, JSON.stringify({ platform: process.platform, node: process.versions.node,
  shell: shellConfig, results }, null, 1) + "\n");
console.log(`bash probe: ${process.platform}, ${results.length} cases, shell ${shellConfig.shell}`);
