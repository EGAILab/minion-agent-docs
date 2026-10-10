// L12-D006 characterization (minion-agent#65 + #133-F1): every pinned-Pi NodeExecutionEnv filesystem operation
// with a NUL-containing path, through the REAL class (b7bb00b9 packages/agent/src/harness/env/nodejs.ts).
//   node --experimental-strip-types pi-nul-probe.mjs <pi checkout> <out.json>
// Set TMPDIR / TMP / TEMP inside the project root. Each case runs in a fresh directory holding file `f` (text "x")
// and directory `d`; it records the Result (ok value, or error code + path as UTF-16 code units relative to the
// case directory) and the entries left afterwards (side effects such as parent creation).
import fs from "node:fs";
import { tmpdir } from "node:os";
import * as path from "node:path";
import { pathToFileURL } from "node:url";

const [piDir, outPath] = process.argv.slice(2);
const { NodeExecutionEnv } = await import(pathToFileURL(`${piDir}/packages/agent/src/harness/env/nodejs.ts`).href);

const units = (s) => Array.from({ length: s.length }, (_, i) => s.charCodeAt(i));
const NUL = "\u0000";
const PATHS = {
  begin: `${NUL}f`,
  middle: `f${NUL}x`,
  end: `f${NUL}`,
  last_component_under_new_parent: `new/a${NUL}b`,
  parent_component: `p${NUL}q/child`,
  lone_surrogate_and_nul: `\ud800${NUL}z`,
};
const aborted = () => { const c = new AbortController(); c.abort(); return c.signal; };

function left(dir, base = dir) {
  const out = [];
  for (const name of fs.readdirSync(dir).sort()) {
    const p = path.join(dir, name);
    const rel = path.relative(base, p).split(path.sep).join("/");
    if (fs.lstatSync(p).isDirectory()) { out.push(rel + "/"); out.push(...left(p, base)); } else out.push(rel);
  }
  return out;
}

function observe(cwd, result) {
  if (result.ok) {
    const v = result.value;
    if (typeof v === "string") return { ok: { string: units(path.isAbsolute(v) && v.startsWith(cwd) ? path.relative(cwd, v) : v) } };
    if (Array.isArray(v)) return { ok: { array: v.length } };
    if (v instanceof Uint8Array) return { ok: { bytes: v.length } };
    if (v && typeof v === "object") return { ok: { info: v.kind ?? Object.keys(v).sort() } };
    return { ok: v === undefined ? null : v };
  }
  const e = result.error;
  return { error: e.code, path: e.path === undefined ? null : units(path.isAbsolute(e.path) ? path.relative(cwd, e.path) : e.path),
           message_has_null_byte_text: /null bytes/.test(e.message) };
}

const OPS = [];
for (const [where, p] of Object.entries(PATHS)) {
  OPS.push([`absolutePath/${where}`, (env) => env.absolutePath(p)]);
  OPS.push([`joinPath/${where}`, (env) => env.joinPath(["d", p])]);
  OPS.push([`readTextFile/${where}`, (env) => env.readTextFile(p)]);
  OPS.push([`readTextLines/${where}`, (env) => env.readTextLines(p)]);
  OPS.push([`readTextLines-max0/${where}`, (env) => env.readTextLines(p, { maxLines: 0 })]);
  OPS.push([`readBinaryFile/${where}`, (env) => env.readBinaryFile(p)]);
  OPS.push([`writeFile/${where}`, (env) => env.writeFile(p, "w")]);
  OPS.push([`appendFile/${where}`, (env) => env.appendFile(p, "w")]);
  OPS.push([`renameFile-source/${where}`, (env) => env.renameFile(p, "g")]);
  OPS.push([`renameFile-destination/${where}`, (env) => env.renameFile("f", p)]);
  OPS.push([`renameFile-both/${where}`, (env) => env.renameFile(p, p)]);
  OPS.push([`fileInfo/${where}`, (env) => env.fileInfo(p)]);
  OPS.push([`listDir/${where}`, (env) => env.listDir(p)]);
  OPS.push([`canonicalPath/${where}`, (env) => env.canonicalPath(p)]);
  OPS.push([`exists/${where}`, (env) => env.exists(p)]);
  OPS.push([`createDir/${where}`, (env) => env.createDir(p)]);
  OPS.push([`createDir-nonrecursive/${where}`, (env) => env.createDir(p, { recursive: false })]);
  OPS.push([`remove/${where}`, (env) => env.remove(p)]);
  OPS.push([`remove-recursive/${where}`, (env) => env.remove(p, { recursive: true })]);
  OPS.push([`remove-force/${where}`, (env) => env.remove(p, { force: true })]);
  OPS.push([`remove-recursive-force/${where}`, (env) => env.remove(p, { recursive: true, force: true })]);
}
// Abort precedence (aborted before any filesystem access), for the operations that take a signal.
OPS.push(["readTextFile-aborted/middle", (env) => env.readTextFile(PATHS.middle, aborted())]);
OPS.push(["readTextLines-aborted/middle", (env) => env.readTextLines(PATHS.middle, { abortSignal: aborted() })]);
OPS.push(["readTextLines-aborted-max0/middle", (env) => env.readTextLines(PATHS.middle, { abortSignal: aborted(), maxLines: 0 })]);
OPS.push(["readBinaryFile-aborted/middle", (env) => env.readBinaryFile(PATHS.middle, aborted())]);
OPS.push(["writeFile-aborted/last_component_under_new_parent", (env) => env.writeFile(PATHS.last_component_under_new_parent, "w", aborted())]);
OPS.push(["renameFile-aborted-source/middle", (env) => env.renameFile(PATHS.middle, "g", aborted())]);
OPS.push(["renameFile-aborted-destination/middle", (env) => env.renameFile("f", PATHS.middle, aborted())]);
OPS.push(["listDir-aborted/middle", (env) => env.listDir(PATHS.middle, aborted())]);
// Temp creation: the prefix / suffix carry the NUL (no fallback path in Pi).
OPS.push(["createTempDir-prefix/middle", (env) => env.createTempDir(`t${NUL}x`)]);
OPS.push(["createTempFile-prefix/middle", (env) => env.createTempFile({ prefix: `t${NUL}x` })]);
OPS.push(["createTempFile-suffix/middle", (env) => env.createTempFile({ suffix: `t${NUL}x` })]);

const root = fs.realpathSync(fs.mkdtempSync(path.join(tmpdir(), "l12d006-pi-")));
const results = [];
let n = 0;
for (const [id, run] of OPS) {
  const cwd = path.join(root, String(n++));
  fs.mkdirSync(path.join(cwd, "d"), { recursive: true });
  fs.writeFileSync(path.join(cwd, "f"), "x");
  const env = new NodeExecutionEnv({ cwd });
  let observed;
  try { observed = observe(cwd, await run(env)); } catch (e) { observed = { threw: `${e?.constructor?.name}: ${e?.code ?? ""} ${e?.message}` }; }
  results.push({ id, observed, left: left(cwd) });
}
fs.rmSync(root, { recursive: true, force: true });
fs.writeFileSync(outPath, JSON.stringify({ platform: process.platform, node: process.versions.node, pi: "b7bb00b936dbe21b8e160b3e89efdec361846699", results }, null, 1) + "\n");
console.log(`l12-d006 pi probe (${process.platform}): ${results.length} cases`);
