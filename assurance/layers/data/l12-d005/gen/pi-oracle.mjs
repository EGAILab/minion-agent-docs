// L12-D005 oracle: runs gen/cases.json through pinned Pi's REAL NodeExecutionEnv.remove under Node v22.15.1.
//   node --experimental-strip-types pi-oracle.mjs <pi checkout> <cases.json> <out.json>
// Set TMP/TEMP (TMPDIR) inside the project root. Output per case: observed result (ok, or code + path
// components relative to cwd), the entries left under cwd, and each external path's state.
import fs from "node:fs";
import { execFileSync } from "node:child_process";
import { tmpdir, userInfo } from "node:os";
import * as path from "node:path";
import { pathToFileURL } from "node:url";

const [piDir, casesPath, outPath] = process.argv.slice(2);
const { NodeExecutionEnv } = await import(pathToFileURL(`${piDir}/packages/agent/src/harness/env/nodejs.ts`).href);
const win = process.platform === "win32";
const user = win ? userInfo().username : null;
const icacls = (p, ...a) => execFileSync("icacls", [p, ...a], { stdio: "ignore" });
const attrib = (...a) => execFileSync("attrib", a, { stdio: "ignore" });

function apply(cwd, step, cleanups) {
  const p = (rel) => path.join(cwd, ...rel.split("/"));
  if (step.file) { fs.mkdirSync(path.dirname(p(step.file)), { recursive: true }); fs.writeFileSync(p(step.file), step.text ?? "x"); }
  else if (step.dir) fs.mkdirSync(p(step.dir), { recursive: true });
  else if (step.readonly) {
    const t = p(step.readonly);
    if (win) { attrib("+R", t); cleanups.push(() => { try { attrib("-R", t); } catch {} }); }
    else { const dir = fs.statSync(t).isDirectory(); fs.chmodSync(t, dir ? 0o555 : 0o444); cleanups.push(() => { try { fs.chmodSync(t, dir ? 0o755 : 0o644); } catch {} }); }
  } else if (step.readonly_link) { const t = p(step.readonly_link); attrib("+R", "/L", t); cleanups.push(() => { try { attrib("-R", "/L", t); } catch {} }); }
  else if (step.symlink) fs.symlinkSync(p(step.to), p(step.symlink), step.kind);
  else if (step.deny_delete) {
    const t = p(step.deny_delete); const parent = path.dirname(t);
    icacls(t, "/deny", `${user}:(D)`); icacls(parent, "/deny", `${user}:(DC)`);
    cleanups.push(() => { try { icacls(parent, "/remove:d", user); } catch {} try { icacls(t, "/remove:d", user); } catch {} });
  } else if (step.deny_write_attributes) {
    const t = p(step.deny_write_attributes); icacls(t, "/deny", `${user}:(WA)`);
    cleanups.push(() => { try { icacls(t, "/remove:d", user); } catch {} });
  } else throw new Error(`unknown fixture step ${JSON.stringify(step)}`);
}
function left(dir, base = dir) {
  const out = [];
  let names; try { names = fs.readdirSync(dir).sort(); } catch { return out; }
  for (const n of names) {
    const q = path.join(dir, n); const st = fs.lstatSync(q);
    const rel = path.relative(base, q).split(path.sep).join("/");
    if (st.isSymbolicLink()) out.push(rel + "@");
    else if (st.isDirectory()) { out.push(rel + "/"); out.push(...left(q, base)); }
    else out.push(rel);
  }
  return out;
}
function readonlyOf(q) {
  if (win) { try { return execFileSync("attrib", [q], { encoding: "utf8" }).slice(0, 12).includes("R"); } catch { return null; } }
  return (fs.statSync(q).mode & 0o222) === 0;
}
function externalState(cwd, rel) {
  const q = path.join(cwd, ...rel.split("/"));
  if (!fs.existsSync(q)) return { path: rel, exists: false };
  const st = fs.statSync(q);
  return { path: rel, exists: true, readonly: readonlyOf(q), ...(st.isFile() ? { text: fs.readFileSync(q, "utf8") } : {}) };
}
const comps = (cwd, v) => path.relative(cwd, v).split(path.sep);

const { cases } = JSON.parse(fs.readFileSync(casesPath, "utf8"));
const results = [];
for (const c of cases) {
  if (c.platforms && !c.platforms.includes(process.platform)) continue;
  const cwd = fs.realpathSync(fs.mkdtempSync(path.join(tmpdir(), "l12d005-oracle-")));
  const cleanups = [];
  for (const step of c.fixture) apply(cwd, step, cleanups);
  const env = new NodeExecutionEnv({ cwd });
  const r = await env.remove(c.remove.path, { recursive: c.remove.recursive });
  const observed = r.ok ? { ok: true } : { error: r.error.code, path: r.error.path ? comps(cwd, r.error.path) : null };
  results.push({ id: c.id, observed, left: left(cwd), external: (c.external ?? []).map((e) => externalState(cwd, e)) });
  for (const f of cleanups.reverse()) f();
}
fs.writeFileSync(outPath, JSON.stringify({ platform: process.platform, node: process.versions.node, pi: "b7bb00b936dbe21b8e160b3e89efdec361846699", results }, null, 1) + "\n");
for (const r of results) console.log(`${r.id}: ${JSON.stringify(r.observed)} left=${JSON.stringify(r.left)}${r.external.length ? " ext=" + JSON.stringify(r.external) : ""}`);
