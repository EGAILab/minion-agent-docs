// L12-D001-R001 error-origin characterization: which path does pinned Pi's NodeExecutionEnv report on each
// OS-originated failure? node --experimental-strip-types probe.mjs <pi> <out.json>
import { mkdtempSync, realpathSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import * as path from "node:path";
import { pathToFileURL } from "node:url";
const [piDir, outPath] = process.argv.slice(2);
const { NodeExecutionEnv } = await import(pathToFileURL(`${piDir}/packages/agent/src/harness/env/nodejs.ts`).href);
const U = (s) => Array.from({ length: s.length }, (_, i) => s.charCodeAt(i));
const rel = (cwd, v) => { if (typeof v !== "string") return null; const r = path.relative(cwd, v);
  return r === "" ? [] : r.split(path.sep).map(U); };
const NAMES = { scalar: "b", lone: "a\ud800" };
const results = [];
for (const [variant, N] of Object.entries(NAMES)) {
  const P = (...xs) => xs.join("/");
  const CASES = {
    "parent-file/write": [["w", N], ["w", P(N, "child")]],
    "parent-file/append": [["w", N], ["a", P(N, "child")]],
    "grandparent-file/write": [["w", N], ["w", P(N, "x", "child")]],
    "grandparent-file/append": [["w", N], ["a", P(N, "x", "child")]],
    "parent-file/create-dir": [["w", N], ["mk", P(N, "x")]],
    "grandparent-file/create-dir": [["w", N], ["mk", P(N, "x", "y")]],
    "self-file/create-dir": [["w", N], ["mk", N]],
    "parent-file/create-dir-nonrecursive": [["w", N], ["mk1", P(N, "x")]],
    "parent-file/read": [["w", N], ["r", P(N, "child")]],
    "parent-file/read-lines": [["w", N], ["rl", P(N, "child")]],
    "parent-file/read-binary": [["w", N], ["rb", P(N, "child")]],
    "parent-file/file-info": [["w", N], ["fi", P(N, "child")]],
    "parent-file/exists": [["w", N], ["ex", P(N, "child")]],
    "self-file/list-dir": [["w", N], ["ls", N]],
    "parent-file/canonical": [["w", N], ["cp", P(N, "child")]],
    "parent-file/remove": [["w", N], ["rm", P(N, "child")]],
    "self-dir/write": [["mk", N], ["w", N]],
    "self-dir/append": [["mk", N], ["a", N]],
    "self-dir/read": [["mk", N], ["r", N]],
    "self-dir/read-lines": [["mk", N], ["rl", N]],
    "self-dir/read-binary": [["mk", N], ["rb", N]],
    "self-dir/remove": [["mk", N], ["rm", N]],
    "self-dir-nonempty/remove": [["w", P(N, "f")], ["rm", N]],
    "missing/read": [["r", N]],
    "missing/read-lines": [["rl", N]],
    "missing/read-binary": [["rb", N]],
    "missing/file-info": [["fi", N]],
    "missing/list-dir": [["ls", N]],
    "missing/canonical": [["cp", N]],
    "missing/remove": [["rm", N]],
    "missing-parent/create-dir-nonrecursive": [["mk1", P(N, "x")]],
    "missing-parent/canonical": [["cp", P(N, "x")]],
    "rename/missing-source": [["mv", N, "dst"]],
    "rename/missing-source-lone-dst": [["mv", "src", N]],
    "rename/dest-parent-file": [["w", "src"], ["w", N], ["mv", "src", P(N, "child")]],
    "rename/dest-parent-missing": [["w", "src"], ["mv", "src", P(N, "child")]],
    "rename/source-parent-file": [["w", N], ["mv", P(N, "child"), "dst"]],
    "rename/dest-nonempty-dir": [["w", "src"], ["w", P(N, "f")], ["mv", "src", N]],
    "rename/source-in-lone-dir-dest-missing": [["w", P(N, "s")], ["mv", P(N, "s"), P("q", "child")]],
  };
  for (const [id, steps] of Object.entries(CASES)) {
    const cwd = realpathSync(mkdtempSync(path.join(tmpdir(), "l12r-")));
    const env = new NodeExecutionEnv({ cwd });
    const observed = [];
    for (const [op, a, b] of steps) {
      let r;
      switch (op) {
        case "w": r = await env.writeFile(a, "c"); break;
        case "a": r = await env.appendFile(a, "c"); break;
        case "mk": r = await env.createDir(a); break;
        case "mk1": r = await env.createDir(a, { recursive: false }); break;
        case "r": r = await env.readTextFile(a); break;
        case "rl": r = await env.readTextLines(a); break;
        case "rb": r = await env.readBinaryFile(a); break;
        case "fi": r = await env.fileInfo(a); break;
        case "ex": r = await env.exists(a); break;
        case "ls": r = await env.listDir(a); break;
        case "cp": r = await env.canonicalPath(a); break;
        case "rm": r = await env.remove(a); break;
        case "mv": r = await env.renameFile(a, b); break;
      }
      observed.push(r.ok ? { ok: true } : { error: r.error.code, path: rel(cwd, r.error.path),
        node_code: r.error.cause?.code ?? null, node_has_path: typeof r.error.cause?.path === "string",
        node_dest: rel(cwd, r.error.cause?.dest) });
    }
    results.push({ id: `${variant}/${id}`, observed });
  }
}
writeFileSync(outPath, JSON.stringify({ platform: process.platform, node: process.versions.node, results }, null, 1) + "\n");
console.log(`${process.platform}: ${results.length} cases`);
