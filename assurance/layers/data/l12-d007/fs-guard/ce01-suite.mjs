// CE-L12D007-01 synthetic control suite. Runs in a child: node --import ./synthetic.mjs [--import <intercept>]
// ce01-suite.mjs <guard module> [intercept]. Prints one JSON object { control: true|false } -- true when
// the control's expected outcome held. Everything below SYN_ROOT is virtual; nothing reaches the OS.
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

const g = await import(pathToFileURL(path.resolve(process.argv[2])).href);
const withIntercept = process.argv[3] === "intercept";
const S = globalThis.__syn;
const VR = S.root;
const OUT = process.platform === "win32" ? "C:\\" : "/";
const OUT_FILE = process.platform === "win32" ? "C:\\ce01-never-created" : "/ce01-never-created";
const refused = (f) => { try { f(); return false; } catch { return true; } };
const allowed = (f) => !refused(f);
const touchesOutside = () => S.calls.some((c) => (c.paths ?? []).some((p) => p && !p.toLowerCase().startsWith(VR.toLowerCase()))
  || (c.args ?? []).some((a) => a.toLowerCase() === OUT.toLowerCase() || a.toLowerCase().startsWith(OUT_FILE.toLowerCase())));
const chain = (n, last) => Object.fromEntries(Array.from({ length: n }, (_, i) => [`c${i}`, { type: "link", text: i + 1 < n ? `c${i + 1}` : last }]));
const quiet = () => {};
const r = {};

S.set(chain(42, OUT_FILE)); r.chain42_outward_refused = refused(() => g.assertInside(VR, "c0"));
S.set(chain(g.BUDGET + 1, "missing")); r.budget_plus_one_contained_refused = refused(() => g.assertInside(VR, "c0"));
S.set(chain(g.BUDGET, OUT_FILE)); r.last_hop_outward_refused = refused(() => g.assertInside(VR, "c0"));
S.set({ a: { type: "link", text: "b" }, b: { type: "link", text: "a" } }); r.cycle2_allowed = allowed(() => g.assertInside(VR, "a"));
S.set(Object.fromEntries(Array.from({ length: 10 }, (_, i) => [`k${i}`, { type: "link", text: `k${(i + 1) % 10}` }]))); r.cycle10_allowed = allowed(() => g.assertInside(VR, "k0"));
for (const code of ["EACCES", "EPERM", "EBUSY"]) {
  S.set({ d: { type: "dir", err: code } }); r[`ancestor_${code}_refused`] = refused(() => g.assertInside(VR, "d/x"));
  S.set({ f: { type: "file", err: code } }); r[`leaf_${code}_refused`] = refused(() => g.assertInside(VR, "f"));
}
S.set({ l: { type: "link", text: "x", readlinkErr: "EACCES" } }); r.readlink_failure_refused = refused(() => g.assertInside(VR, "l"));
S.set({}); r.missing_allowed = allowed(() => g.assertInside(VR, "nothing/here"));
S.set({ f: { type: "file" } }); r.enotdir_allowed = allowed(() => g.assertInside(VR, "f/x"));
S.set({ d: { type: "dir" }, "d/f": { type: "file" } }); r.ordinary_existing_allowed = allowed(() => g.assertInside(VR, "d/f"));

// Paired controls on the SAME outward final link `j`.
S.set({ j: { type: "link", text: OUT } });
r.a_referent_through_outward_link_refused = refused(() => g.assertInside(VR, "j")) && refused(() => g.assertInside(VR, "j/x"));
r.b_entry_on_outward_link_allowed = allowed(() => g.assertEntry(VR, "j"));
r.d_entry_under_outward_ancestor_refused = refused(() => g.assertEntry(VR, "j/x"));
S.set({ j: { type: "link", text: OUT }, d: { type: "dir" }, "d/f": { type: "file" } });
const cleaned = g.cleanupSandbox(VR, quiet);
r.c_cleanup_removes_link_as_entry_only = cleaned
  && S.calls.some((c) => /unlinkSync|rmdirSync/.test(c.op) && c.paths[0] === path.join(VR, "j"))
  && !S.calls.some((c) => c.op === "readdir" && c.paths[0] === path.join(VR, "j"))
  && !S.calls.some((c) => c.op.startsWith("exec:") && (c.args.includes("/T") || c.args.includes(path.join(VR, "j"))))
  && !touchesOutside();
S.set({ "a\uFFFD": { type: "link", text: OUT_FILE } }); r.e_projection_alias_refused = refused(() => g.assertInside(VR, "a\uD800")) && refused(() => g.assertInside(VR, "a\uDC00"));
let restored = 0; const count = () => { restored++; };
S.set({}); r.f_restore_missing_skipped = !g.restoreAccess(VR, "gone", "file", count, quiet) && restored === 0;
S.set({ l: { type: "link", text: "x" } }); r.f_restore_link_skipped = !g.restoreAccess(VR, "l", "file", count, quiet) && restored === 0;
S.set({ f: { type: "file" } }); r.f_restore_existing_done = g.restoreAccess(VR, "f", "file", count, quiet) && restored === 1;

if (withIntercept) {
  // R8 backstop: the intercept wraps the synthetic stubs; a refused call never reaches them.
  S.set({ j: { type: "link", text: OUT } });
  const reached = (op, p) => S.calls.some((c) => c.op === op && c.paths[0] === p);
  let threw = refused(() => fs.writeFileSync(path.join(VR, "j", "x"), "x"));
  r.intercept_write_through_outward_ancestor_refused = threw && !reached("writeFileSync", path.join(VR, "j", "x"));
  threw = refused(() => fs.writeFileSync(path.join(VR, "j"), "x"));
  r.intercept_write_to_outward_final_link_refused = threw && !reached("writeFileSync", path.join(VR, "j"));
  threw = refused(() => fs.chmodSync(path.join(VR, "j"), 0o600));
  r.intercept_chmod_outward_final_link_refused = threw && !reached("chmodSync", path.join(VR, "j"));
  r.intercept_entry_unlink_allowed_and_confined = allowed(() => fs.unlinkSync(path.join(VR, "j"))) && reached("unlinkSync", path.join(VR, "j")) && !touchesOutside();
}
console.log(JSON.stringify(r));
