// L12D011-C001 containment controls. The ACTUAL mutation statements (io.mjs makeRun / writeOutput, used by the
// launcher, the generator and the merge) run with every mutation INTERCEPTED (mkdirSync, writeFileSync record an
// attempt and do nothing) and the reviewed guard's inspections STEERED in memory (lstatSync / readlinkSync answer for
// chosen paths). No outward link is ever created and nothing is written. Each unsafe case must be REFUSED with ZERO
// mutation attempts; the legitimate case makes exactly one attempt; each proof-removed mutant of io.mjs is CAUGHT
// (it makes an attempt where the real one refuses).
//   node containment-controls.mjs
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
delete process.env.FS_GUARD_ROOT;
const guard = await import(pathToFileURL(path.join(here, "../../l12-d007/fs-guard/fs-guard.mjs")).href);
const ROOT = guard.PROJECT_ROOT;
const SCRATCH = path.join(ROOT, ".tmp", "claude-scratch", "i195");
const ioSource = fs.readFileSync(path.join(here, "io.mjs"), "utf8");
const load = async (src, tag) => import(`data:text/javascript;base64,${Buffer.from(src).toString("base64")}#${tag}`);
const io = await load(ioSource, "real");

let failed = 0;
const report = (ok, text) => { failed += !ok; console.log(`${ok ? "PASS" : "FAIL"} ${text}`); };
const eq = (a, b) => path.resolve(a).toLowerCase() === path.resolve(b).toLowerCase();

function intercepted(steer, body) {
  const saved = { mkdirSync: fs.mkdirSync, writeFileSync: fs.writeFileSync, lstatSync: fs.lstatSync, readlinkSync: fs.readlinkSync };
  const attempts = [];
  fs.mkdirSync = (p) => { attempts.push(`mkdir ${p}`); };
  fs.writeFileSync = (p) => { attempts.push(`write ${p}`); };
  fs.lstatSync = (p, ...rest) => { for (const s of steer) if (eq(p, s.path)) return s.lstat(); return saved.lstatSync(p, ...rest); };
  fs.readlinkSync = (p, ...rest) => { for (const s of steer) if (eq(p, s.path) && s.readlink) return s.readlink(); return saved.readlinkSync(p, ...rest); };
  let refused = null;
  try { body(); } catch (e) { refused = e.message; }
  Object.assign(fs, saved);
  return { attempts, refused };
}
const outward = (p) => ({ path: p, lstat: () => ({ isSymbolicLink: () => true, isDirectory: () => false }),
  readlink: () => (process.platform === "win32" ? "C:\\outside-the-project-never-touched" : "/outside-never-touched") });
const eacces = (p) => ({ path: p, lstat: () => { throw Object.assign(new Error("EACCES: permission denied"), { code: "EACCES" }); } });
const refusedNone = (r) => r.refused !== null && r.attempts.length === 0;

// makeRun: a run name is one plain component; the ancestry is proven before any mkdir.
for (const name of ["../escape", "a/../../b", "/abs", "C:x", "\\\\srv\\share", "a\\b", "", "UPPER"]) {
  const r = intercepted([], () => io.makeRun(guard, SCRATCH, name));
  report(refusedNone(r), `makeRun refuses name ${JSON.stringify(name)} with zero mutations (attempts=${r.attempts.length})`);
}
for (const [label, steer] of [["outward-link ancestor", outward(path.join(ROOT, ".tmp", "claude-scratch"))],
                              ["inspection-failure ancestor", eacces(path.join(ROOT, ".tmp", "claude-scratch"))]]) {
  const r = intercepted([steer], () => io.makeRun(guard, SCRATCH, "controls-run"));
  report(refusedNone(r), `makeRun refuses an ${label} with zero mutations (attempts=${r.attempts.length})`);
}

// writeOutput: the final output entry is proven immediately before the write.
const legit = path.join(SCRATCH, "controls-never-written.json");
for (const [label, file, steer] of [
  ["an escaping relative tail", path.join(SCRATCH, "..", "..", "..", "..", "escape.json"), []],
  ["a foreign absolute path", process.platform === "win32" ? "C:/Windows/Temp/d011-never.json" : "/etc/d011-never.json", []],
  ["an outward final output entry", path.join(SCRATCH, "final-link.json"), [outward(path.join(SCRATCH, "final-link.json"))]],
  ["an inspection-failure parent", path.join(SCRATCH, "denied", "out.json"), [eacces(path.join(SCRATCH, "denied"))]],
]) {
  const r = intercepted(steer, () => io.writeOutput(guard, file, "x"));
  report(refusedNone(r), `writeOutput refuses ${label} with zero mutations (attempts=${r.attempts.length})`);
}
const ok = intercepted([], () => io.writeOutput(guard, legit, "x"));
report(ok.refused === null && ok.attempts.length === 1, `writeOutput legitimate output: one attempt, nothing written natively`);

// Proof-removed mutants of the ACTUAL statements are caught.
const noOutputProof = await load(ioSource.replace("fs.writeFileSync(guard.assertOutput(file), data);", "fs.writeFileSync(file, data);"), "m1");
const m1 = intercepted([outward(path.join(SCRATCH, "final-link.json"))], () => noOutputProof.writeOutput(guard, path.join(SCRATCH, "final-link.json"), "x"));
report(m1.attempts.length === 1, `control: writeOutput without its proof is caught (attempts=${m1.attempts.length})`);
const noRunProof = await load(ioSource
  .replace("if (typeof name !== \"string\" || !RUN_NAME.test(name)) throw", "if (false) throw")
  .replace("const run = guard.makeSandbox(path.join(scratchBase, name));", "const run = path.join(scratchBase, name); fs.mkdirSync(run, { recursive: true });"), "m2");
const m2 = intercepted([], () => noRunProof.makeRun(guard, SCRATCH, "../escape"));
report(m2.attempts.length >= 1, `control: makeRun without its proofs is caught (attempts=${m2.attempts.length})`);
if (!ioSource.includes("fs.writeFileSync(guard.assertOutput(file), data);") || !ioSource.includes("guard.makeSandbox(path.join(scratchBase, name))")) {
  report(false, "the mutated statements were not found in io.mjs (INVALID controls)");
}
// Every writer goes through io.mjs: no direct write or mkdir elsewhere in the generation scripts.
for (const f of ["gen_spawn_nul.mjs", "merge_spawn_nul.mjs", "run-gen.mjs"]) {
  const s = fs.readFileSync(path.join(here, f), "utf8");
  report(!/\b(writeFileSync|mkdirSync|appendFileSync|rmSync|unlinkSync|renameSync|copyFileSync)\s*\(/.test(s),
    `${f}: no direct filesystem mutation outside io.mjs`);
}
console.log(failed ? `CONTAINMENT CONTROLS FAILED (${failed})` : "CONTAINMENT CONTROLS PASSED");
process.exitCode = failed ? 1 : 0;
