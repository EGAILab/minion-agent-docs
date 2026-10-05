// WP-13.4 (find, grep; minion-agent#51) pinned-Pi characterization probe. Pinned Pi b7bb00b9's own code under Node v22.15.1:
//   core/tools/truncate.ts                 imported whole (Node built-ins only)
//   core/tools/path-utils.ts pathExists, resolveToCwd and utils/paths.ts normalizePath/resolvePath, sliced unmodified
//                                          (utils/paths.ts imports child-process.ts -> cross-spawn, which these never reach)
//   core/tools/find.ts relativizeFindResultPath and the tool's execute body, sliced unmodified
//   core/tools/grep.ts the default operations and the tool's execute body, sliced unmodified
// The ONLY substitution is utils/tools-manager.ts ensureTool: it returns the exact pinned engine binary (TOOL-038,
// EXACT_MINION_PINNED_ENGINES) instead of Pi's cache -> PATH -> latest-download acquisition.
// Each case runs the real tool execute against a freshly built corpus; observations: the result text (or thrown error
// message) and details, with the corpus root normalized to <ROOT>.
//   node --experimental-strip-types search_probe.mjs <pi checkout> <engine dir with fd[.exe], rg[.exe]> <scratch dir> <out.json>
import { spawn, spawnSync } from "node:child_process";
import { accessSync, constants, mkdirSync, mkdtempSync, realpathSync, rmSync, statSync, symlinkSync, writeFileSync, readFileSync } from "node:fs";
import { access, readFile as fsReadFile, stat as fsStat } from "node:fs/promises";
import { homedir } from "node:os";
import path, { isAbsolute, join, relative, resolve as nodeResolvePath, sep } from "node:path";
import { createInterface } from "node:readline";
import { stripTypeScriptTypes } from "node:module";
import { fileURLToPath, pathToFileURL } from "node:url";

const [piDir, engineDir, scratchDir, outPath] = process.argv.slice(2);
const SRC = `${piDir}/packages/coding-agent/src`;
const EXE = process.platform === "win32" ? ".exe" : "";
const ENGINES = { fd: join(engineDir, `fd${EXE}`), rg: join(engineDir, `rg${EXE}`) };
const { DEFAULT_MAX_BYTES, GREP_MAX_LINE_LENGTH, formatSize, truncateHead, truncateLine } =
  await import(pathToFileURL(`${SRC}/core/tools/truncate.ts`).href);
const slice = (src, from, to) => { const a = src.indexOf(from), b = to ? src.indexOf(to, a) : src.length;
  if (a < 0 || b < 0) throw new Error(`slice ${from}`); return src.slice(a, b); };
const ts = (code) => stripTypeScriptTypes(code.replace(/^export /gm, ""));

const pathsSrc = readFileSync(`${SRC}/utils/paths.ts`, "utf8");
const { resolvePath } = new Function("realpathSync", "statSync", "homedir", "isAbsolute", "join", "nodeResolvePath",
  "relative", "sep", "fileURLToPath", ts(slice(pathsSrc, "const UNICODE_SPACES", "export function getCwdRelativePath(")) +
  "\nreturn { resolvePath };")(realpathSync, statSync, homedir, isAbsolute, join, nodeResolvePath, relative, sep, fileURLToPath);
const puSrc = readFileSync(`${SRC}/core/tools/path-utils.ts`, "utf8");
const { pathExists, resolveToCwd } = new Function("access", "constants", "resolvePath", ts(
  slice(puSrc, "export async function pathExists(", "export function expandPath(") +
  slice(puSrc, "export function resolveToCwd(", "export function resolveReadPath(")) +
  "\nreturn { pathExists, resolveToCwd };")(access, constants, resolvePath);
const ensureTool = async (tool) => ENGINES[tool];

const method = (src) => slice(src, "async execute(", "renderCall(args").replace(/\},\s*$/, "}").replace(/^async execute/, "async function execute");
const findSrc = readFileSync(`${SRC}/core/tools/find.ts`, "utf8");
const findExecute = new Function("path", "spawn", "createInterface", "ensureTool", "pathExists", "resolveToCwd", "truncateHead",
  "formatSize", "DEFAULT_MAX_BYTES", "cwd", ts(
    slice(findSrc, "export function relativizeFindResultPath(", "const findSchema") +
    "const DEFAULT_LIMIT = 1000;\n" +
    slice(findSrc, "const defaultFindOperations", "export interface FindToolOptions") +
    "const customOps = undefined;\n") + `\nreturn (${ts(method(findSrc))});`);
const grepSrc = readFileSync(`${SRC}/core/tools/grep.ts`, "utf8");
const grepExecute = new Function("path", "spawn", "createInterface", "ensureTool", "resolveToCwd", "truncateHead", "truncateLine",
  "formatSize", "DEFAULT_MAX_BYTES", "GREP_MAX_LINE_LENGTH", "fsStat", "fsReadFile", "cwd", ts(
    "const DEFAULT_LIMIT = 100;\n" +
    slice(grepSrc, "const defaultGrepOperations", "export interface GrepToolOptions") +
    "const customOps = undefined;\n") + `\nreturn (${ts(method(grepSrc))});`);

// ---------------------------------------------------------------- corpus
function file(root, rel, content) {
  const p = join(root, ...rel.split("/")); mkdirSync(path.dirname(p), { recursive: true }); writeFileSync(p, content);
}
function build(kind) {
  const root = realpathSync(mkdtempSync(join(scratchDir, `wp134-${kind}-`)));
  const links = {};
  if (kind === "repo") mkdirSync(join(root, ".git"));
  file(root, ".gitignore", "ignored/\n*.log\nkeep.ts\n");
  file(root, "src/a.ts", "alpha\nBeta\nfoo bar\nfoo.bar\nlast\n");
  file(root, "src/b.spec.ts", "describe foo\n");
  file(root, "src/sub/c.ts", "const foo = 1;\n");
  file(root, "src/sub/d.spec.ts", "it foo\n");
  file(root, "src/.hidden.ts", "hidden foo\n");
  file(root, ".hiddendir/e.ts", "hidden dir foo\n");
  file(root, "data/x.json", "{\"foo\": 1}\n");
  file(root, "data/y.JSON", "{\"FOO\": 2}\n");
  file(root, "ünïcode/文件.ts", "naïve 日本語 foo\n");
  file(root, "space dir/f.ts", "space foo\n");
  file(root, "ignored/g.ts", "ignored foo\n");
  file(root, "z.log", "log foo\n");
  file(root, "keep.ts", "root keep foo\n");
  file(root, "node_modules/pkg/index.ts", "module foo\n");
  file(root, "nested/.gitignore", "inner.ts\n");
  mkdirSync(join(root, "nested", ".git"), { recursive: true });
  file(root, "nested/inner.ts", "inner foo\n");
  file(root, "nested/keep.ts", "nested keep foo\n");
  file(root, "text/crlf.txt", "one\r\ntwo match\r\nthree\r\n");
  file(root, "text/cr.txt", "x\ry match\rz");
  file(root, "text/long.txt", "a".repeat(600) + " needle " + "b".repeat(10) + "\nshort needle\n");
  file(root, "text/unicode.txt", "café\nnaïve match\n日本語 match\nCAFÉ\n");
  file(root, "text/bin.dat", Buffer.concat([Buffer.from("match\n"), Buffer.from([0, 0, 1]), Buffer.from("binary match\n")]));
  file(root, "text/many.txt", Array.from({ length: 10 }, (_, i) => `hit ${i + 1}`).join("\n") + "\n");
  file(root, "text/ctx.txt", Array.from({ length: 10 }, (_, i) => (i === 1 || i === 2 ? `L${i + 1} MATCH` : `L${i + 1}`)).join("\n") + "\n");
  file(root, "text/edge.txt", "MATCH first\nmiddle\n\nlast MATCH\n");
  file(root, "text/dash.txt", "-v option\nplain\n");
  file(root, "text/multi.txt", "x x x\n");
  file(root, "text/bom.txt", Buffer.concat([Buffer.from([0xef, 0xbb, 0xbf]), Buffer.from("first match\nsecond\n")]));
  file(root, "text/badutf8.txt", Buffer.concat([Buffer.from("ok line\nbad "), Buffer.from([0xff, 0xfe]), Buffer.from(" match\nafter\n")]));
  file(root, " lead.ts", "leading space name\n");
  if (process.platform !== "win32") {
    try {
      writeFileSync(Buffer.concat([Buffer.from(join(root, "text") + "/raw-"), Buffer.from([0xff]), Buffer.from(".txt")]), "rawname match\n");
      links["raw-name"] = "created";
    } catch (e) { links["raw-name"] = `unsupported: ${e.code}`; }
  }
  for (const [name, target, type] of [["link-file.ts", "src/a.ts", "file"], ["link-dir", "src/sub", "dir"]]) {
    try {
      symlinkSync(join(root, ...target.split("/")), join(root, name), type === "dir" && process.platform === "win32" ? "junction" : type);
      links[name] = "created";
    } catch (e) { links[name] = `unsupported: ${e.code}`; }
  }
  return { root, links };
}

const norm = (root) => (value) => {
  if (typeof value === "string") {
    let v = value;
    for (const r of [root, root.replaceAll("\\", "/")]) v = v.split(r).join("<ROOT>");
    return v;
  }
  if (Array.isArray(value)) return value.map(norm(root));
  if (value && typeof value === "object") return Object.fromEntries(Object.entries(value).map(([k, v]) => [k, norm(root)(v)]));
  return value;
};

async function run(tool, root, rawArgs, { preAborted = false } = {}) {
  const args = Object.fromEntries(Object.entries(rawArgs).map(([k, v]) => [k, typeof v === "string" ? v.replace("<ROOT>", root) : v]));
  const execute = tool === "find"
    ? findExecute(path, spawn, createInterface, ensureTool, pathExists, resolveToCwd, truncateHead, formatSize, DEFAULT_MAX_BYTES, root)
    : grepExecute(path, spawn, createInterface, ensureTool, resolveToCwd, truncateHead, truncateLine, formatSize,
      DEFAULT_MAX_BYTES, GREP_MAX_LINE_LENGTH, fsStat, fsReadFile, root);
  const controller = new AbortController();
  if (preAborted) controller.abort();
  try {
    const result = await execute("c", args, controller.signal);
    return norm(root)({ ok: true, text: result.content[0].text, details: result.details ?? null });
  } catch (e) {
    return norm(root)({ ok: false, error: e.message });
  }
}

const FIND = [
  ["ts-basename", { pattern: "*.ts" }],
  ["recursive-json", { pattern: "**/*.json" }],
  ["case-json-lower", { pattern: "*.json" }],
  ["case-json-upper", { pattern: "*.JSON" }],
  ["full-path-spec", { pattern: "src/**/*.spec.ts" }],
  ["any-depth-spec", { pattern: "**/*.spec.ts" }],
  ["hidden-glob", { pattern: ".hidden*" }],
  ["keep-boundary", { pattern: "keep.ts" }],
  ["inner-nested-ignore", { pattern: "inner.ts" }],
  ["log-ignored", { pattern: "*.log" }],
  ["git-dir-contents", { pattern: "*", path: ".git" }],
  ["double-star", { pattern: "**" }],
  ["limit-2", { pattern: "*.ts", limit: 2 }],
  ["limit-exact", { pattern: "*.json", limit: 1 }],
  ["limit-zero", { pattern: "*.ts", limit: 0 }],
  ["path-sub", { pattern: "*.ts", path: "src" }],
  ["path-sub-fullpath", { pattern: "sub/*.ts", path: "src" }],
  ["path-missing", { pattern: "*.ts", path: "missing" }],
  ["path-is-file", { pattern: "*.ts", path: "src/a.ts" }],
  ["no-match", { pattern: "*.nothing" }],
  ["unicode-name", { pattern: "文件.ts" }],
  ["unicode-dir-fullpath", { pattern: "ünïcode/*.ts" }],
  ["space-dir", { pattern: "space dir/*.ts" }],
  ["symlinks", { pattern: "link*" }],
  ["through-dir-link", { pattern: "link-dir/*.ts" }],
  ["absolute-pattern", { pattern: "/src/*.ts" }],
  ["node-modules", { pattern: "index.ts" }],
  ["dot-path", { pattern: "*.ts", path: "." }],
  ["at-prefix-path", { pattern: "*.ts", path: "@src" }],
  ["brace-alternation", { pattern: "*.{json,JSON}" }],
  ["char-class", { pattern: "[ab].ts" }],
  ["question-mark", { pattern: "?.ts" }],
  ["limit-negative", { pattern: "*.ts", limit: -1 }],
  ["limit-fraction", { pattern: "*.ts", limit: 2.5 }],
  ["dir-name", { pattern: "sub" }],
  ["trailing-slash", { pattern: "src/" }],
  ["leading-space-name", { pattern: "*lead.ts" }],
  ["absolute-path-arg", { pattern: "*.ts", path: "<ROOT>/src" }],
  ["raw-name", { pattern: "raw-*" }],
];
const GREP = [
  ["regex-foo", { pattern: "foo" }],
  ["regex-dot", { pattern: "foo.bar" }],
  ["literal-dot", { pattern: "foo.bar", literal: true }],
  ["case-sensitive", { pattern: "beta" }],
  ["ignore-case", { pattern: "beta", ignoreCase: true }],
  ["glob-ts", { pattern: "foo", glob: "*.ts" }],
  ["glob-spec-fullpath", { pattern: "foo", glob: "**/*.spec.ts" }],
  ["glob-negated", { pattern: "foo", glob: "!*.ts" }],
  ["hidden", { pattern: "hidden" }],
  ["gitignored", { pattern: "ignored" }],
  ["nested-keep", { pattern: "keep" }],
  ["unicode", { pattern: "naïve|日本語" }],
  ["unicode-ignore-case", { pattern: "café", ignoreCase: true }],
  ["binary", { pattern: "match", path: "text/bin.dat" }],
  ["binary-in-dir", { pattern: "binary" }],
  ["crlf-no-context", { pattern: "match", path: "text/crlf.txt" }],
  ["crlf-context-1", { pattern: "match", path: "text/crlf.txt", context: 1 }],
  ["cr-only", { pattern: "match", path: "text/cr.txt" }],
  ["cr-only-context", { pattern: "match", path: "text/cr.txt", context: 1 }],
  ["context-overlap", { pattern: "MATCH", path: "text/ctx.txt", context: 2 }],
  ["context-clamp", { pattern: "MATCH", path: "text/edge.txt", context: 3 }],
  ["context-negative", { pattern: "MATCH", path: "text/ctx.txt", context: -1 }],
  ["context-fraction", { pattern: "MATCH", path: "text/ctx.txt", context: 1.5 }],
  ["long-line", { pattern: "needle", path: "text/long.txt" }],
  ["long-line-context", { pattern: "short", path: "text/long.txt", context: 1 }],
  ["limit-3", { pattern: "hit", path: "text/many.txt", limit: 3 }],
  ["limit-zero", { pattern: "hit", path: "text/many.txt", limit: 0 }],
  ["limit-fraction", { pattern: "hit", path: "text/many.txt", limit: 2.5 }],
  ["no-match", { pattern: "zzzznothing" }],
  ["path-file", { pattern: "alpha", path: "src/a.ts" }],
  ["path-dir", { pattern: "foo", path: "src" }],
  ["path-missing", { pattern: "foo", path: "missing" }],
  ["invalid-regex", { pattern: "(" }],
  ["empty-line", { pattern: "^$", path: "text/edge.txt" }],
  ["multi-per-line", { pattern: "x", path: "text/multi.txt" }],
  ["dash-pattern", { pattern: "-v", path: "text/dash.txt" }],
  ["symlink-file", { pattern: "alpha" }],
  ["node-modules", { pattern: "module" }],
  ["limit-negative", { pattern: "hit", path: "text/many.txt", limit: -1 }],
  ["bom-no-context", { pattern: "match", path: "text/bom.txt" }],
  ["bom-context", { pattern: "second", path: "text/bom.txt", context: 1 }],
  ["bad-utf8-no-context", { pattern: "match", path: "text/badutf8.txt" }],
  ["bad-utf8-context", { pattern: "match", path: "text/badutf8.txt", context: 1 }],
  ["raw-name", { pattern: "rawname" }],
  ["absolute-path-arg", { pattern: "alpha", path: "<ROOT>/src" }],
  ["dot-path", { pattern: "alpha", path: "." }],
];

function summary(r) {
  if (!r.ok) return r;
  const [body, ...notice] = r.text.split("\n\n[");
  const lines = body.split("\n");
  return { ok: true, lines: lines.length, bodyBytes: Buffer.byteLength(body), lastLine: lines.at(-1),
    notice: notice.length ? "[" + notice.join("\n\n[") : null, details: r.details };
}
async function bulk() {
  const root = realpathSync(mkdtempSync(join(scratchDir, "wp134-bulk-")));
  const pad = "p".repeat(48);
  for (let i = 0; i < 1200; i++) file(root, `many/f${String(i).padStart(4, "0")}-${pad}.txt`, "x\n");
  file(root, "wide/w.txt", Array.from({ length: 120 }, (_, i) => `hit ${String(i).padStart(3, "0")} ` + "w".repeat(490)).join("\n") + "\n");
  const r = {
    "find/default-limit-and-bytes": summary(await run("find", root, { pattern: "*.txt", path: "many" })),
    "find/limit-1200-bytes-only": summary(await run("find", root, { pattern: "*.txt", path: "many", limit: 1200 })),
    "grep/default-limit-and-bytes": summary(await run("grep", root, { pattern: "hit", path: "wide/w.txt" })),
  };
  rmSync(root, { recursive: true, force: true });
  return r;
}

const out = { pi: "b7bb00b936dbe21b8e160b3e89efdec361846699", node: process.version, platform: process.platform,
  engines: Object.fromEntries(Object.entries(ENGINES).map(([k, p]) => [k, spawnSync(p, ["--version"]).stdout.toString().split("\n")[0]])),
  corpora: {}, find: {}, grep: {} };
for (const kind of ["plain", "repo"]) {
  const { root, links } = build(kind);
  out.corpora[kind] = { links };
  for (const [name, args] of FIND) out.find[`${kind}/${name}`] = { args, ...(await run("find", root, args)) };
  for (const [name, args] of GREP) out.grep[`${kind}/${name}`] = { args, ...(await run("grep", root, args)) };
  if (kind === "plain") {
    out.find["plain/pre-aborted"] = { args: { pattern: "*.ts" }, ...(await run("find", root, { pattern: "*.ts" }, { preAborted: true })) };
    out.grep["plain/pre-aborted"] = { args: { pattern: "foo" }, ...(await run("grep", root, { pattern: "foo" }, { preAborted: true })) };
  }
  rmSync(root, { recursive: true, force: true });
}
out.bulk = await bulk();
writeFileSync(outPath, JSON.stringify(out, null, 1) + "\n");
console.log(`wrote ${Object.keys(out.find).length} find + ${Object.keys(out.grep).length} grep observations`);
