// L12-D001 pinned-Pi authority (minion-agent#123; Owner decision FSP-Q001). Executes each case's step program
// against pinned Pi b7bb00b9's REAL harness NodeExecutionEnv (packages/agent/src/harness/env/nodejs.ts, imported
// unmodified; its other imports are type-only) -- the source Layer 12's ctx.fs models -- and computes target_key
// with Pi's coding-agent getMutationQueueKey (core/tools/file-mutation-queue.ts, sliced unmodified) over the
// harness's own absolutePath. Each case runs in a fresh working directory that is already its own realpath, so
// logical and canonical results share one base. Observations are platform-neutral (path components relative to
// that directory, strings as UTF-16 code units).
//   node --experimental-strip-types l12_probe.mjs <pi checkout> <cases.json> <out.json>
import { mkdtempSync, readFileSync, realpathSync, writeFileSync } from "node:fs";
import * as fsp from "node:fs/promises";
import { tmpdir } from "node:os";
import * as path from "node:path";
import { pathToFileURL } from "node:url";
import { stripTypeScriptTypes } from "node:module";

const [piDir, casesPath, outPath] = process.argv.slice(2);
const { NodeExecutionEnv } = await import(pathToFileURL(`${piDir}/packages/agent/src/harness/env/nodejs.ts`).href);
const q = readFileSync(`${piDir}/packages/coding-agent/src/core/tools/file-mutation-queue.ts`, "utf8");
const getMutationQueueKey = new Function("realpath", "resolve", stripTypeScriptTypes(
  q.slice(q.indexOf("function isMissingPathError("), q.indexOf("/**\n * Serialize"))) + "\nreturn getMutationQueueKey;",
)(fsp.realpath, path.resolve);

const U = (s) => Array.from({ length: s.length }, (_, i) => s.charCodeAt(i));
const S = (units) => String.fromCharCode(...units);
const cmp = (a, b) => { for (let i = 0; i < Math.min(a.length, b.length); i++) if (a[i] !== b[i]) return a[i] - b[i];
                        return a.length - b.length; };

function observePath(cwd, value) {
  const rel = path.relative(cwd, value);
  if (rel === "") return { components: [] };
  if (rel.startsWith("..") || path.isAbsolute(rel)) return { outside: true };
  return { components: rel.split(path.sep).map(U) };
}
function observeError(cwd, error) {
  return { error: error.code, path: typeof error.path === "string" ? observePath(cwd, error.path) : null };
}

async function run(c) {
  const cwd = realpathSync(mkdtempSync(path.join(tmpdir(), "l12-")));
  const env = new NodeExecutionEnv({ cwd });
  const arg = (p) => "utf16" in p ? S(p.utf16) : `${pathToFileURL(cwd).href}/${S(p.file_url_tail)}`;
  const observed = [];
  for (const s of c.steps) {
    const p = arg(s.path);
    let o;
    switch (s.op) {
      case "write_file": { const r = await env.writeFile(p, S(s.content)); o = r.ok ? { ok: null } : observeError(cwd, r.error); break; }
      case "read_text_file": { const r = await env.readTextFile(p); o = r.ok ? { ok: U(r.value) } : observeError(cwd, r.error); break; }
      case "list_dir": { const r = await env.listDir(p);
        o = r.ok ? { names: r.value.map((i) => U(i.name)).sort(cmp) } : observeError(cwd, r.error); break; }
      case "canonical_path": { const r = await env.canonicalPath(p); o = r.ok ? observePath(cwd, r.value) : observeError(cwd, r.error); break; }
      case "absolute_path": { const r = await env.absolutePath(p);
        o = s.observe === "last_component" ? { last: U(path.basename(r.value)) } : observePath(cwd, r.value); break; }
      case "target_key": { const a = await env.absolutePath(p);
        try { o = observePath(cwd, await getMutationQueueKey(a.value)); } catch (e) { o = { error: e.code ?? "unknown", path: null }; }
        break; }
      case "exists": { const r = await env.exists(p); o = r.ok ? { ok: r.value } : observeError(cwd, r.error); break; }
      case "file_info": { const r = await env.fileInfo(p); o = r.ok ? { kind: r.value.kind, name: U(r.value.name) } : observeError(cwd, r.error); break; }
      default: throw new Error(`unknown op ${s.op}`);
    }
    observed.push(o);
  }
  return { id: c.id, observed };
}

const cases = JSON.parse(readFileSync(casesPath, "utf8"));
const results = [];
for (const c of cases) results.push(await run(c));
writeFileSync(outPath, JSON.stringify({ platform: process.platform, node: process.versions.node, results }, null, 1) + "\n");
console.log(`l12 probe: ${process.platform} node ${process.versions.node}, ${results.length} cases`);
