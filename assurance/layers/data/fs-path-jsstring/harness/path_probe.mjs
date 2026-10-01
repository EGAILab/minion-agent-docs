// FS-PATH-JSSTRING characterization (minion-agent#123): what pinned Pi b7bb00b9 does with a filesystem path whose
// JavaScript String holds unpaired UTF-16 surrogates, on THIS platform. Pi's own path helpers (utils/paths.ts
// normalizePath/resolvePath, sliced unmodified) produce the path; Node's fs then performs exactly the operations Pi's
// tools perform (write: mkdir(dirname)+writeFile; read: access+readFile; ls: readdir; queue key: realpath(resolve(p))
// falling back to resolve(p)). Strings render as UTF-16 code units.
//   node path_probe.mjs <pi checkout> <out.json>
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import * as fsp from "node:fs/promises";
import { homedir, tmpdir } from "node:os";
import * as path from "node:path";
import { fileURLToPath } from "node:url";
import { stripTypeScriptTypes } from "node:module";

const [piDir, outPath] = process.argv.slice(2);
const src = readFileSync(`${piDir}/packages/coding-agent/src/utils/paths.ts`, "utf8");
const from = src.indexOf("const UNICODE_SPACES");
const to = src.indexOf("export function getCwdRelativePath(");
const sliced = stripTypeScriptTypes(src.slice(from, to).replace(/^export /gm, ""));
// The slice contains interface PathInputOptions/canonicalizePath/getFileRevision/isLocalPath too; inject their deps.
const { resolvePath } = new Function(
  "isAbsolute", "join", "nodeResolvePath", "homedir", "fileURLToPath", "sep", "realpathSync", "statSync",
  sliced + "\nreturn { resolvePath, normalizePath };",
)(path.isAbsolute, path.join, path.resolve, homedir, fileURLToPath, path.sep, () => { throw new Error(); }, () => {});
const resolveToCwd = (p, cwd) => resolvePath(p, cwd, { normalizeUnicodeSpaces: true, stripAtPrefix: true });

const U = (s) => Array.from({ length: s.length }, (_, i) => s.charCodeAt(i));
const S = (u) => String.fromCharCode(...u);
const fffd = (s) => s.replace(/[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]/g, "�");
const attempt = async (f) => { try { return { ok: true, value: await f() }; } catch (e) {
  return { ok: false, code: e.code ?? null, message: U(String(e.message)), errPath: e.path === undefined ? null : U(e.path) }; } };

const NAMES = {
  "bmp": [0xE9],
  "pair": [0xD83D, 0xDE00],
  "lone-high-start": [0xD800, 0x61],
  "lone-high-middle": [0x61, 0xD800, 0x62],
  "lone-high-end": [0x61, 0xD800],
  "lone-low-start": [0xDC00, 0x61],
  "lone-low-middle": [0x61, 0xDC00, 0x62],
  "lone-low-end": [0x61, 0xDC00],
  "mixed-pair-then-lone": [0xD83D, 0xDE00, 0xD800],
  "low-then-high": [0xDC00, 0xD800],
};

const root = mkdtempSync(path.join(tmpdir(), "fs-path-"));
const results = [];
let n = 0;
for (const [name, units] of Object.entries(NAMES)) {
  for (const position of ["file", "dir"]) {
    const cwd = path.join(root, `c${n++}`);
    await fsp.mkdir(cwd);
    const component = S(units);
    const rel = position === "file" ? `f${component}.txt` : `d${component}/f.txt`;
    const resolved = resolveToCwd(rel, cwd);
    const r = { id: `${position}/${name}`, input: U(rel), resolved_relative: U(path.relative(cwd, resolved)),
                resolved_unchanged: resolved === path.resolve(cwd, rel) };
    r.write = await attempt(async () => { await fsp.mkdir(path.dirname(resolved), { recursive: true });
                                          await fsp.writeFile(resolved, "content"); return null; });
    r.listing = (await fsp.readdir(cwd)).map(U);
    if (position === "dir") {
      const dirs = await fsp.readdir(cwd);
      r.listing_inner = dirs.length ? (await fsp.readdir(path.join(cwd, dirs[0]))).map(U) : [];
    }
    r.read_same_string = await attempt(async () => (await fsp.readFile(resolved, "utf8")) === "content");
    r.read_fffd_variant = await attempt(async () => (await fsp.readFile(fffd(resolved), "utf8")) === "content");
    r.realpath_relative = await attempt(async () => U(path.relative(cwd, await fsp.realpath(resolved))));
    r.queue_key_equals_resolved = await attempt(async () => (await fsp.realpath(resolved)) === resolved);
    const missing = path.join(cwd, `missing${component}.txt`);
    const err = await attempt(() => fsp.readFile(missing));
    r.missing_error = { code: err.code, errPath_relative_equal: err.errPath ? S(err.errPath) === missing : null,
                        errPath_has_fffd: err.errPath ? S(err.errPath).includes("�") : null,
                        message_has_input_units: err.message ? S(err.message).includes(component) : null };
    results.push(r);
  }
}
// Collision: two distinct JS names that project to the same filesystem name.
const cwd = path.join(root, "collision");
await fsp.mkdir(cwd);
const a = path.join(cwd, "a\uD800"), b = path.join(cwd, "a\uDC00");
await fsp.writeFile(a, "A");
await fsp.writeFile(b, "B");
const collision = { listing: (await fsp.readdir(cwd)).map(U),
                    read_a: (await attempt(() => fsp.readFile(a, "utf8"))).value ?? null,
                    realpath_a_equals_realpath_b: (await fsp.realpath(a)) === (await fsp.realpath(b)),
                    resolve_a_equals_resolve_b: path.resolve(a) === path.resolve(b) };
writeFileSync(outPath, JSON.stringify({ platform: process.platform, node: process.versions.node,
  icu: process.versions.icu, results, collision }, null, 1) + "\n");
console.log(`path probe: ${process.platform} node ${process.versions.node}, ${results.length} results`);
