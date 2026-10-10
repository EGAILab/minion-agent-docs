// L12-D006 canonical authority (minion-agent#65 + #133-F1): gen/cases.json (fs_path_domain steps) through pinned Pi
// b7bb00b9 -- packages/agent/src/harness/env/nodejs.ts NodeExecutionEnv (imported unmodified) and
// coding-agent core/tools/file-mutation-queue.ts getMutationQueueKey (sliced unmodified, for target_key).
// Minion-only operations have no NodeExecutionEnv method; their authority is the pinned Node primitive they map
// (list_dir_raw: readdir; probe_dir_entry: lstat; check_readable: access R_OK; check_read_write: access R_OK|W_OK).
// The oracle REQUIRES that primitive to reject with ERR_INVALID_ARG_VALUE (no err.path), which Pi's toFileError
// classifies `unknown` with the logical fallback path; anything else fails the run.
//   node --experimental-strip-types pi_oracle.mjs <pi checkout> <cases.json> <out.json>
// Observations follow the fs_path_domain runner grammar (paths as UTF-16 components relative to the case dir).
import fs from "node:fs";
import { access, constants, lstat, readdir, realpath } from "node:fs/promises";
import { tmpdir } from "node:os";
import * as path from "node:path";
import { resolve } from "node:path";
import { stripTypeScriptTypes } from "node:module";
import { pathToFileURL } from "node:url";

const [piDir, casesPath, outPath] = process.argv.slice(2);
const { NodeExecutionEnv } = await import(pathToFileURL(`${piDir}/packages/agent/src/harness/env/nodejs.ts`).href);
const queueSource = fs.readFileSync(`${piDir}/packages/coding-agent/src/core/tools/file-mutation-queue.ts`, "utf8");
const slice = (from, to) => { const a = queueSource.indexOf(from), b = queueSource.indexOf(to, a);
  if (a < 0 || b < 0) throw new Error(`slice ${from}`); return queueSource.slice(a, b); };
const getMutationQueueKey = new Function("realpath", "resolve", stripTypeScriptTypes(
  slice("function isMissingPathError(", "async function getMutationQueueKey(") +
  slice("async function getMutationQueueKey(", "/**")) + "\nreturn getMutationQueueKey;")(realpath, resolve);

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
const aborted = (step) => { if (!step.aborted) return undefined; const c = new AbortController(); c.abort(); return c.signal; };

async function primitive(cwd, logical, call) {
  try { await call(logical); } catch (e) {
    if (e?.code !== "ERR_INVALID_ARG_VALUE" || e.path !== undefined) throw new Error(`unexpected primitive rejection ${e?.code}`);
    return { error: "unknown", path: observePath(cwd, logical) };
  }
  throw new Error("primitive accepted a NUL path");
}

async function run(env, cwd, step) {
  const p = text(step.path.utf16);
  const resolved = path.resolve(cwd, p);
  switch (step.op) {
    case "write_file": return okOr(cwd, await env.writeFile(p, text(step.content), aborted(step)), () => ({ ok: null }));
    case "append_file": return okOr(cwd, await env.appendFile(p, text(step.content)), () => ({ ok: null }));
    case "read_text_file": return okOr(cwd, await env.readTextFile(p, aborted(step)), (v) => ({ ok: units(v) }));
    case "read_text_lines": return okOr(cwd, await env.readTextLines(p, { maxLines: step.max_lines, abortSignal: aborted(step) }), (v) => ({ ok: v.map(units) }));
    case "read_binary_file": return okOr(cwd, await env.readBinaryFile(p, aborted(step)), (v) => ({ ok: Array.from(v) }));
    case "rename_file": return okOr(cwd, await env.renameFile(p, text(step.to.utf16), aborted(step)), () => ({ ok: null }));
    case "file_info": return okOr(cwd, await env.fileInfo(p), (v) => ({ kind: v.kind, name: units(v.name) }));
    case "exists": return okOr(cwd, await env.exists(p), (v) => ({ ok: v }));
    case "list_dir": return okOr(cwd, await env.listDir(p, aborted(step)), (v) => ({ names: v.map((i) => units(i.name)).sort() }));
    case "canonical_path": return okOr(cwd, await env.canonicalPath(p), (v) => observePath(cwd, v));
    case "absolute_path": return okOr(cwd, await env.absolutePath(p), (v) => observePath(cwd, v));
    case "create_dir": return okOr(cwd, await env.createDir(p, { recursive: step.recursive }), () => ({ ok: null }));
    case "remove": return okOr(cwd, await env.remove(p, { recursive: step.recursive ?? false, force: step.force ?? false }), () => ({ ok: null }));
    case "target_key":
      try { return observePath(cwd, await getMutationQueueKey(resolved)); } catch (e) {
        if (e?.code !== "ERR_INVALID_ARG_VALUE") throw e;
        return { error: "unknown", path: observePath(cwd, resolved) };
      }
    case "list_dir_raw": return primitive(cwd, resolved, (q) => readdir(q));
    case "probe_dir_entry": return primitive(cwd, resolved, (q) => lstat(q));
    case "check_readable": return primitive(cwd, resolved, (q) => access(q, constants.R_OK));
    case "check_read_write": return primitive(cwd, resolved, (q) => access(q, constants.R_OK | constants.W_OK));
    default: throw new Error(`op ${step.op}`);
  }
}

const cases = JSON.parse(fs.readFileSync(casesPath, "utf8")).cases;
const root = fs.realpathSync(fs.mkdtempSync(path.join(tmpdir(), "l12d006-oracle-")));
const results = [];
for (const [n, c] of cases.entries()) {
  const cwd = path.join(root, String(n));
  fs.mkdirSync(cwd);
  const env = new NodeExecutionEnv({ cwd });
  const observed = [];
  for (const step of c.steps) observed.push(await run(env, cwd, step));
  results.push({ id: c.id, observed });
}
fs.rmSync(root, { recursive: true, force: true });
fs.writeFileSync(outPath, JSON.stringify({ platform: process.platform, node: process.versions.node, pi: "b7bb00b936dbe21b8e160b3e89efdec361846699", results }, null, 1) + "\n");
console.log(`l12-d006 oracle (${process.platform}): ${results.length} cases`);
