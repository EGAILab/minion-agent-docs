// L12-D005 (#126) characterization: pinned Pi's REAL NodeExecutionEnv.remove under Node v22.15.1.
//   node --experimental-strip-types pi-probe.mjs <pi checkout> <out.json>
// Every case builds a fresh tree under os.tmpdir() (set TMP/TEMP to the project root on E:).
// Observation per case: the Result (ok, or code + path relative to cwd), the entries left under cwd,
// and, where a case has an external target, that target's existence and read-only state.
// The only interleaving hook is `vanish`: node:fs.chmod is wrapped BEFORE the first recursive rm, which
// lazily loads lib/internal/fs/rimraf.js and captures fs.chmod at that point (no errno is fabricated:
// the file is really deleted just before the real chmod runs).
import fs from "node:fs";
import { execFileSync } from "node:child_process";
import { tmpdir, userInfo } from "node:os";
import * as path from "node:path";
import { pathToFileURL } from "node:url";

const [piDir, outPath] = process.argv.slice(2);
const win = process.platform === "win32";
let afterReaddir = null;
const realReaddir = fs.readdir;
fs.readdir = (p, opts, cb) => {
  if (typeof opts === "function") { cb = opts; opts = undefined; }
  return realReaddir(p, opts, (err, files) => {
    if (!err && afterReaddir) { const hook = afterReaddir; afterReaddir = null; globalThis.vanishFired = true; Promise.resolve(hook()).then(() => cb(err, files), () => cb(err, files)); return; }
    cb(err, files);
  });
};
let beforeChmod = null;
let chmodCalls = [];
const realChmod = fs.chmod;
fs.chmod = (p, mode, cb) => {
  chmodCalls.push({ path: String(p), mode: mode.toString(8) });
  if (beforeChmod) { const hook = beforeChmod; beforeChmod = null; hook(String(p)); }
  return realChmod(p, mode, cb);
};
const { NodeExecutionEnv } = await import(pathToFileURL(`${piDir}/packages/agent/src/harness/env/nodejs.ts`).href);

const user = win ? userInfo().username : String(process.getuid?.());
const icacls = (p, ...args) => execFileSync("icacls", [p, ...args], { stdio: "ignore" });
const deny = (p, rights) => icacls(p, "/deny", `${user}:(${rights})`);
const undeny = (p) => { try { icacls(p, "/remove:d", user); } catch {} };
const readonly = (p) => fs.chmodSync(p, 0o444);
const rel = (cwd, v) => (typeof v === "string" ? path.relative(cwd, v).split(path.sep).join("/") : v);
const observe = (cwd, r) => (r.ok ? { ok: true } : { code: r.error.code, path: rel(cwd, r.error.path) });
function left(dir, base = dir) {
  const out = [];
  let names;
  try { names = fs.readdirSync(dir).sort(); } catch { return out; }
  for (const n of names) {
    const p = path.join(dir, n);
    const st = fs.lstatSync(p);
    out.push(path.relative(base, p).split(path.sep).join("/") + (st.isSymbolicLink() ? "@" : st.isDirectory() ? "/" : ""));
    if (st.isDirectory() && !st.isSymbolicLink()) out.push(...left(p, base));
  }
  return out;
}
const attrib = (p) => { try { return execFileSync("attrib", [p], { encoding: "utf8" }).slice(0, 12).includes("R"); } catch { return null; } };
const state = (p) => { try { const st = fs.statSync(p); return { exists: true, readonly: win ? attrib(p) : (st.mode & 0o200) === 0 }; } catch { return { exists: false }; } };

function fresh() {
  const root = fs.realpathSync(fs.mkdtempSync(path.join(tmpdir(), "l12d005-")));
  const cwd = path.join(root, "cwd"); fs.mkdirSync(cwd);
  const ext = path.join(root, "external"); fs.mkdirSync(ext);
  return { root, cwd, ext };
}
const file = (p, text = "x") => { fs.mkdirSync(path.dirname(p), { recursive: true }); fs.writeFileSync(p, text); };

// [id, platforms, setup(ctx) -> {target, options, cleanup?, external?}]
const CASES = [
  ["child-readonly-file", "both", ({ cwd }) => { file(path.join(cwd, "t/sub/f")); readonly(path.join(cwd, "t/sub/f")); return { target: "t", options: { recursive: true } }; }],
  ["target-readonly-file-recursive", "both", ({ cwd }) => { file(path.join(cwd, "f")); readonly(path.join(cwd, "f")); return { target: "f", options: { recursive: true } }; }],
  ["target-readonly-file-nonrecursive", "both", ({ cwd }) => { file(path.join(cwd, "f")); readonly(path.join(cwd, "f")); return { target: "f", options: {} }; }],
  ["nested-readonly-files", "both", ({ cwd }) => {
    for (const f of ["t/a", "t/s/b", "t/s/u/c", "t/z"]) { file(path.join(cwd, f)); readonly(path.join(cwd, f)); }
    return { target: "t", options: { recursive: true } };
  }],
  ["readonly-directory-attribute", "win32", ({ cwd }) => {
    file(path.join(cwd, "t/d/f")); execFileSync("attrib", ["+R", path.join(cwd, "t/d")]);
    return { target: "t", options: { recursive: true }, cleanup: () => { try { execFileSync("attrib", ["-R", path.join(cwd, "t/d")]); } catch {} } };
  }],
  ["chmod-denied-readonly-file", "win32", ({ cwd }) => {
    const f = path.join(cwd, "t/f"); file(f); readonly(f); deny(f, "WA");
    return { target: "t", options: { recursive: true }, cleanup: () => undeny(f) };
  }],
  ["retry-fails-readonly-file", "win32", ({ cwd }) => {
    const d = path.join(cwd, "t"); const f = path.join(d, "f"); file(f); readonly(f); deny(f, "D"); deny(d, "DC");
    return { target: "t", options: { recursive: true }, cleanup: () => { undeny(d); undeny(f); } };
  }],
  ["acl-denied-file", "win32", ({ cwd }) => {
    const d = path.join(cwd, "t"); const f = path.join(d, "f"); file(f); deny(f, "D"); deny(d, "DC");
    return { target: "t", options: { recursive: true }, cleanup: () => { undeny(d); undeny(f); } };
  }],
  ["acl-denied-directory", "win32", ({ cwd }) => {
    const t = path.join(cwd, "t"); const d = path.join(t, "d"); fs.mkdirSync(d, { recursive: true }); deny(d, "D"); deny(t, "DC");
    return { target: "t", options: { recursive: true }, cleanup: () => { undeny(t); undeny(d); } };
  }],
  ["acl-denied-top-level-file", "win32", ({ cwd }) => {
    const f = path.join(cwd, "f"); file(f); deny(f, "D"); deny(cwd, "DC");
    return { target: "f", options: { recursive: true }, cleanup: () => { undeny(cwd); undeny(f); } };
  }],
  ["vanish-during-recovery", "win32", ({ cwd }) => {
    const f = path.join(cwd, "t/f"); file(f); readonly(f);
    beforeChmod = (p) => { if (p === f || p.endsWith(`${path.sep}f`)) { fs.chmodSync(p, 0o666); fs.unlinkSync(p); } };
    return { target: "t", options: { recursive: true }, cleanup: () => { beforeChmod = null; } };
  }],
  ["symlink-to-external-readonly-file", "both", ({ cwd, ext }) => {
    const target = path.join(ext, "protected.txt"); file(target, "keep"); readonly(target);
    fs.mkdirSync(path.join(cwd, "t")); fs.symlinkSync(target, path.join(cwd, "t/link"), "file");
    return { target: "t", options: { recursive: true }, external: target, cleanup: () => fs.chmodSync(target, 0o666) };
  }],
  ["symlink-to-external-readonly-dir", "both", ({ cwd, ext }) => {
    const target = path.join(ext, "pdir"); file(path.join(target, "inner.txt"), "keep");
    if (win) execFileSync("attrib", ["+R", target]); else fs.chmodSync(target, 0o555);
    fs.mkdirSync(path.join(cwd, "t")); fs.symlinkSync(target, path.join(cwd, "t/dlink"), "dir");
    return { target: "t", options: { recursive: true }, external: target,
             cleanup: () => { if (win) execFileSync("attrib", ["-R", target]); else fs.chmodSync(target, 0o755); } };
  }],
  ["readonly-empty-dir-target-recursive", "win32", ({ cwd }) => {
    fs.mkdirSync(path.join(cwd, "d")); execFileSync("attrib", ["+R", path.join(cwd, "d")]);
    return { target: "d", options: { recursive: true }, cleanup: () => { try { execFileSync("attrib", ["-R", path.join(cwd, "d")]); } catch {} } };
  }],
  ["readonly-nonempty-dir-target-recursive", "win32", ({ cwd }) => {
    file(path.join(cwd, "d/f")); readonly(path.join(cwd, "d/f")); execFileSync("attrib", ["+R", path.join(cwd, "d")]);
    return { target: "d", options: { recursive: true }, cleanup: () => { try { execFileSync("attrib", ["-R", path.join(cwd, "d")]); } catch {} } };
  }],
  ["readonly-dir-target-nonrecursive", "win32", ({ cwd }) => {
    fs.mkdirSync(path.join(cwd, "d")); execFileSync("attrib", ["+R", path.join(cwd, "d")]);
    return { target: "d", options: {}, cleanup: () => { try { execFileSync("attrib", ["-R", path.join(cwd, "d")]); } catch {} } };
  }],
  ["mixed-readonly-tree", "win32", ({ cwd }) => {
    for (const f of ["t/a", "t/x/b", "t/x/y/c"]) file(path.join(cwd, f));
    readonly(path.join(cwd, "t/x/b")); execFileSync("attrib", ["+R", path.join(cwd, "t/x")]); execFileSync("attrib", ["+R", path.join(cwd, "t/x/y")]);
    return { target: "t", options: { recursive: true } };
  }],
  ["readonly-symlink-itself", "win32", ({ cwd, ext }) => {
    const target = path.join(ext, "plain.txt"); file(target, "keep");
    fs.mkdirSync(path.join(cwd, "t")); fs.symlinkSync(target, path.join(cwd, "t/link"), "file");
    execFileSync("attrib", ["+R", "/L", path.join(cwd, "t/link")]);
    return { target: "t", options: { recursive: true }, external: target };
  }],
  ["readonly-symlink-target-nonrecursive", "both", ({ cwd, ext }) => {
    const target = path.join(ext, "protected.txt"); file(target, "keep"); readonly(target);
    fs.symlinkSync(target, path.join(cwd, "link"), "file");
    return { target: "link", options: {}, external: target, cleanup: () => fs.chmodSync(target, 0o666) };
  }],
  ["entry-vanishes-during-recursive", "both", ({ cwd }) => {
    for (const f of ["t/a", "t/b", "t/c"]) { file(path.join(cwd, f)); if (win) readonly(path.join(cwd, f)); }
    afterReaddir = async () => { afterReaddir = null; const v = path.join(cwd, "t/b"); try { fs.chmodSync(v, 0o666); } catch {} fs.unlinkSync(v); };
    return { target: "t", options: { recursive: true }, cleanup: () => { afterReaddir = null; } };
  }],
  ["posix-readonly-subdir", "linux", ({ cwd }) => {
    file(path.join(cwd, "t/sub/f")); fs.chmodSync(path.join(cwd, "t/sub"), 0o555);
    return { target: "t", options: { recursive: true }, cleanup: () => fs.chmodSync(path.join(cwd, "t/sub"), 0o755) };
  }],
];

const results = [];
for (const [id, where, setup] of CASES) {
  if (where !== "both" && where !== process.platform) continue;
  const ctx = fresh();
  const c = setup(ctx);
  const env = new NodeExecutionEnv({ cwd: ctx.cwd });
  chmodCalls = [];
  const r = await env.remove(c.target, c.options);
  const chmods = chmodCalls.map((x) => ({ path: rel(ctx.cwd, x.path), mode: x.mode }));
  const extState = c.external ? state(c.external) : undefined;
  const extInner = c.external && fs.existsSync(path.join(c.external, "inner.txt")) ? "inner.txt present" : c.external ? "no inner.txt" : undefined;
  const hookFired = globalThis.vanishFired === true; globalThis.vanishFired = false;
  results.push({ id, call: { target: c.target, options: c.options }, observed: observe(ctx.cwd, r), chmods, hookFired, left: left(ctx.cwd),
                 ...(c.external ? { external: { ...extState, inner: extInner } } : {}) });
  try { c.cleanup?.(); } catch {}
}
fs.writeFileSync(outPath, JSON.stringify({ platform: process.platform, node: process.versions.node, user, results }, null, 1) + "\n");
console.log(results.map((r) => `${r.id}: ${JSON.stringify(r.observed)} chmod=${JSON.stringify(r.chmods)} left=${JSON.stringify(r.left)}${r.external ? " ext=" + JSON.stringify(r.external) : ""}`).join("\n"));
