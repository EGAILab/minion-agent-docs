// WP-13.3 (bash, minion-agent#50) pinned-Pi characterization probe. Pinned Pi b7bb00b9's own code under Node v22.15.1:
//   core/tools/truncate.ts, core/tools/output-accumulator.ts  imported whole (Node built-ins only)
//   utils/shell.ts      getShellConfig/getBashShellConfig/isLegacyWslBashPath/findBashOnPath/getShellEnv/killProcessTree/
//                       track/untrack, sliced unmodified; the only non-built-in import, getBinDir (config.ts), stubbed
//   utils/child-process.ts  waitForChildProcess, sliced unmodified
//   core/tools/bash.ts  resolveTimeoutMs, createLocalBashOperations, resolveSpawnContext and the tool's execute body,
//                       sliced unmodified (the TUI render functions are not reached by execute)
// Each case runs the real tool execute in a fresh working directory; observations: the result (or thrown error) text
// with the temp path normalized, details, the temp file's bytes (sha256/size) when present, and the update sequence.
//   node --experimental-strip-types bash_probe.mjs <pi checkout> <out.json>
import { createHash } from "node:crypto";
import { existsSync, mkdtempSync, readFileSync, realpathSync, writeFileSync } from "node:fs";
import { access } from "node:fs/promises";
import { constants } from "node:fs";
import { tmpdir } from "node:os";
import { delimiter, join } from "node:path";
import { spawn, spawnSync } from "node:child_process";
import { stripTypeScriptTypes } from "node:module";
import { pathToFileURL } from "node:url";

const [piDir, outPath] = process.argv.slice(2);
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
  ["output/plain", "printf 'hello\\n'"],
  ["output/no-trailing-newline", "printf 'hello'"],
  ["output/empty", "true"],
  ["output/crlf", "printf 'a\\r\\nb\\r\\n'"],
  ["output/stderr-only", "printf 'err\\n' >&2"],
  ["output/interleaved", "printf 'a'; sleep 0.3; printf 'b' >&2; sleep 0.3; printf 'c'"],
  ["utf8/invalid-byte", "printf 'x\\377y'"],
  ["utf8/split-across-writes", "printf '\\342\\202'; sleep 0.3; printf '\\254'"],
  ["utf8/split-interrupted-by-stderr", "printf '\\342'; sleep 0.3; printf 'x' >&2; sleep 0.3; printf '\\202\\254'"],
  ["utf8/truncated-at-end", "printf 'ok\\342\\202'"],
  ["exit/one", "printf 'x\\n'; exit 1"],
  ["exit/255-no-output", "exit 255"],
  ["exit/one-no-output", "exit 1"],
  ["truncate/lines-2000", "seq 1 2000"],
  ["truncate/lines-2001", "seq 1 2001"],
  ["truncate/lines-2001-no-trailing-newline", "seq 1 2001 | head -c -1"],
  ["truncate/bytes-51200", "head -c 51200 /dev/zero | tr '\\0' 'a'"],
  ["truncate/bytes-51201-one-line", "head -c 51201 /dev/zero | tr '\\0' 'a'"],
  ["truncate/bytes-many-lines", "yes abcdefghij | head -n 5000"],
  ["truncate/rolling-tail", "yes 0123456789012345678901234567890123456789 | head -n 9000"],
  ["truncate/multibyte-partial-line", "head -c 60000 /dev/zero | tr '\\0' 'a'; printf '\\342\\202\\254%.0s' $(seq 1 30000)"],
  ["truncate/error-with-truncation", "seq 1 2500; exit 3"],
  ["timeout/fires", "printf 'before\\n'; sleep 5", { timeout: 0.5 }],
  ["timeout/fires-no-output", "sleep 5", { timeout: 0.5 }],
  ["timeout/not-reached", "printf 'done'", { timeout: 10 }],
  ["timeout/invalid-zero", "true", { timeout: 0 }],
  ["timeout/invalid-negative", "true", { timeout: -1 }],
  ["timeout/invalid-infinity", "true", { timeout: Infinity }],
  ["timeout/invalid-above-max", "true", { timeout: 2147483.648 }],
  ["timeout/max-accepted", "printf 'ok'", { timeout: 2147483.647 }],
  ["timeout/fractional-message", "sleep 5", { timeout: 0.25 }],
  ["abort/before-spawn", "printf 'never'", { preAbort: true }],
  ["abort/during", "printf 'before\\n'; sleep 5", { abortAfterMs: 400 }],
  ["cwd/missing", "true", { missingCwd: true }],
  ["kill/external-sigkill", "kill -9 $$"],
  ["updates/two-chunks", "printf 'a'; sleep 0.4; printf 'b'", { observeUpdates: true }],
];

const results = [];
for (const [id, command, opt = {}] of CASES) {
  const base = realpathSync(mkdtempSync(join(tmpdir(), "wp133-")));
  const cwd = opt.missingCwd ? join(base, "missing") : base;
  const ops = bash.createLocalBashOperations({});
  const execute = makeExecute(cwd, ops, undefined, false, undefined, bash.resolveSpawnContext,
    OutputAccumulator, formatSize, DEFAULT_MAX_BYTES, BASH_UPDATE_THROTTLE_MS);
  const controller = new AbortController();
  if (opt.preAbort) controller.abort();
  if (opt.abortAfterMs) setTimeout(() => controller.abort(), opt.abortAfterMs);
  const updates = [];
  const onUpdate = (u) => updates.push({ text: u.content[0]?.text ?? null, hasDetails: u.details !== undefined });
  const args = { command, ...(opt.timeout !== undefined ? { timeout: opt.timeout } : {}) };
  const out = { id, command, timeout: opt.timeout === Infinity ? "Infinity" : opt.timeout ?? null };
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
}
const shellConfig = shell.getShellConfig(undefined);
writeFileSync(outPath, JSON.stringify({ platform: process.platform, node: process.versions.node,
  shell: shellConfig, results }, null, 1) + "\n");
console.log(`bash probe: ${process.platform}, ${results.length} cases, shell ${shellConfig.shell}`);
