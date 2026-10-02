// CE-L12-D001-01 error-origin convergence probe (minion-agent#123): the origin sites the r001 neighborhood did not
// reach, executed through pinned Pi's REAL NodeExecutionEnv (imported unmodified) under Node v22.15.1.
//   entry-vanish:   listDir's per-entry lstat fails (the entry is removed after readdir returns: a controlled
//                   interleaving through node:fs/promises.readdir, the binding Pi imports; no errno is fabricated)
//   rm-inner:       remove(recursive) failing on an entry INSIDE the tree (POSIX: a mode-555 subdirectory as a
//                   non-root user; Windows: a read-only file)
//   fifo-file-info: fileInfo of an unsupported file type (POSIX only: a FIFO)
//   node --experimental-strip-types ce.mjs <pi checkout> <out.json>
import fsp from "node:fs/promises";
import { chmodSync, mkdtempSync, realpathSync, writeFileSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { syncBuiltinESMExports } from "node:module";
import { tmpdir } from "node:os";
import * as path from "node:path";
import { pathToFileURL } from "node:url";

const [piDir, outPath] = process.argv.slice(2);
let afterReaddir = null;
const readdir = fsp.readdir;
fsp.readdir = async (...args) => { const entries = await readdir(...args); if (afterReaddir) await afterReaddir(); return entries; };
syncBuiltinESMExports();
const { NodeExecutionEnv } = await import(pathToFileURL(`${piDir}/packages/agent/src/harness/env/nodejs.ts`).href);

const U = (s) => Array.from({ length: s.length }, (_, i) => s.charCodeAt(i));
const rel = (cwd, v) => (typeof v === "string" ? path.relative(cwd, v).split(path.sep).map(U) : null);
const observe = (cwd, r) => (r.ok ? { ok: true } : { error: r.error.code, path: rel(cwd, r.error.path) });
const NAMES = { scalar: "b", lone: "a\ud800" };
const results = [];
for (const [variant, name] of Object.entries(NAMES)) {
  const native = name.replace("\ud800", "\ufffd");
  {
    const cwd = realpathSync(mkdtempSync(path.join(tmpdir(), "l12ce-")));
    const env = new NodeExecutionEnv({ cwd });
    await env.writeFile(`${name}/child.txt`, "x");
    afterReaddir = async () => { afterReaddir = null; await fsp.unlink(path.join(cwd, native, "child.txt")); };
    results.push({ id: `${variant}/entry-vanish`, observed: observe(cwd, await env.listDir(name)) });
  }
  // rm shapes: [id, mode changes applied (POSIX) after creating <name>/sub/f]
  const SHAPES = process.platform === "win32"
    ? [["rm-readonly-file", (n) => chmodSync(path.join(n, "sub", "f"), 0o444), (n) => {}]]
    : [["rm-inner", (n) => chmodSync(path.join(n, "sub"), 0o555), (n) => chmodSync(path.join(n, "sub"), 0o755)],
       ["rm-unreadable-dir", (n) => chmodSync(path.join(n, "sub"), 0o333), (n) => chmodSync(path.join(n, "sub"), 0o755)],
       ["rm-readonly-parent", (n) => chmodSync(n, 0o555), (n) => chmodSync(n, 0o755)]];
  for (const [shape, lock, unlock] of SHAPES) {
    const cwd = realpathSync(mkdtempSync(path.join(tmpdir(), "l12ce-")));
    const env = new NodeExecutionEnv({ cwd });
    await env.writeFile(`${name}/sub/f`, "x");
    const top = path.join(cwd, native);
    lock(top);
    results.push({ id: `${variant}/${shape}`, observed: observe(cwd, await env.remove(name, { recursive: true })) });
    try { unlock(top); } catch {}
  }
  if (process.platform !== "win32") {
    const cwd = realpathSync(mkdtempSync(path.join(tmpdir(), "l12ce-")));
    const env = new NodeExecutionEnv({ cwd });
    execFileSync("mkfifo", [path.join(cwd, native)]);
    results.push({ id: `${variant}/fifo-file-info`, observed: observe(cwd, await env.fileInfo(name)) });
  }
}
writeFileSync(outPath, JSON.stringify({ platform: process.platform, node: process.versions.node, uid: process.getuid?.() ?? null, results }, null, 1) + "\n");
console.log(`ce probe: ${process.platform}, ${results.length} cases`);
