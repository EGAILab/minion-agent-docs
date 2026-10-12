// WP133D001-R002 controls (remediation 2): the abort-trigger probe's ONE output write is proven by fs-guard
// assertOutput immediately before it happens, and this script's OWN fixture writes are proven by the reviewed
// fs-guard operations (CE-L12D007-01) immediately before each one: makeSandbox (REFERENT ancestry before its mkdir),
// assertInside (REFERENT) for each directory and the junction's target, assertEntry (ENTRY) for the junction
// itself, cleanupSandbox (TRAVERSAL: a junction is removed as an entry, never followed). There is no ad-hoc
// lexical check anywhere. The guard is imported relative to this file (the candidate's own copy).
//   node abort_trigger_output_controls.mjs
//
// Part A -- the writer. The probe's actual writer statement is extracted from its source and executed with
// writeFileSync INTERCEPTED (no native write) and the real assertOutput of a second guard instance whose boundary
// is narrowed (FS_GUARD_ROOT) to a fixture directory INSIDE the project: a legitimate output (one attempt); an
// output outside the boundary, a foreign absolute path, and an output under a junction parent leading outside
// (refused, zero attempts). Control: the statement with the proof removed is caught (a write attempt happens).
//
// Part B -- the fixture's own safety. The fixture setup is executed with EVERY mutation intercepted (mkdir,
// symlink) and the guard's inspections steered in memory: (1) an ancestor that is a link leading outside the
// project, (2) an ancestor whose inspection fails (EACCES). Each must be refused before any mutation attempt.
// Control: the pre-remediation lexical-only setup, under (1), makes mutation attempts -- killed by the
// zero-attempt assertion. No outward link is ever created on disk.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const guardUrl = pathToFileURL(path.join(here, "../l12-d007/fs-guard/fs-guard.mjs")).href;
delete process.env.FS_GUARD_ROOT; // the fixture guard uses the project root
const guard = await import(`${guardUrl}?fixture`);
const PROJECT = guard.PROJECT_ROOT;
const BASE = path.join(PROJECT, ".tmp", "claude-scratch", "wp133d", `output-controls-${process.pid}`);

// The fixture, through the reviewed guard only. `g` is a guard instance; every mutation goes through `fs`.
function setupFixture(g) {
  const base = g.makeSandbox(BASE);
  fs.mkdirSync(g.assertInside(base, "boundary"));
  fs.mkdirSync(g.assertInside(base, "elsewhere"));
  fs.symlinkSync(g.assertInside(base, "elsewhere"), g.assertEntry(base, "boundary/linkdir"), "junction");
  return { base, boundary: path.join(base, "boundary"), elsewhere: path.join(base, "elsewhere"),
           link: path.join(base, "boundary", "linkdir") };
}

// The pre-remediation (review 2) setup: a lexical-only check. Kept ONLY as the Part B regression control.
function lexicalOnlySetup() {
  const inside = (p) => {
    const abs = path.resolve(p);
    if (!abs.toLowerCase().startsWith(path.resolve(PROJECT).toLowerCase() + path.sep) || p.includes("..")) {
      throw new Error(`containment: ${abs}`);
    }
    return abs;
  };
  fs.mkdirSync(inside(path.join(BASE, "boundary")), { recursive: true });
  fs.mkdirSync(inside(path.join(BASE, "elsewhere")), { recursive: true });
  fs.symlinkSync(path.join(BASE, "elsewhere"), inside(path.join(BASE, "boundary", "linkdir")), "junction");
}

let failed = 0;
const report = (ok, text) => { failed += !ok; console.log(`${ok ? "PASS" : "FAIL"} ${text}`); };

// ---- Part B first: nothing native happens here --------------------------------------------------------------
function intercepted(world, body) {
  const saved = { mkdirSync: fs.mkdirSync, symlinkSync: fs.symlinkSync, lstatSync: fs.lstatSync,
                  readlinkSync: fs.readlinkSync };
  const attempts = [];
  fs.mkdirSync = (p) => { attempts.push(`mkdir ${p}`); };
  fs.symlinkSync = (t, p) => { attempts.push(`symlink ${p}`); };
  const ancestor = path.join(PROJECT, ".tmp", "claude-scratch", "wp133d");
  fs.lstatSync = (p, ...rest) => {
    if (path.resolve(String(p)).toLowerCase() === ancestor.toLowerCase()) return world.ancestor();
    return saved.lstatSync(p, ...rest);
  };
  fs.readlinkSync = (p, ...rest) =>
    (path.resolve(String(p)).toLowerCase() === ancestor.toLowerCase() ? world.readlink() : saved.readlinkSync(p, ...rest));
  let refused = null;
  try { body(); } catch (e) { refused = e.message; }
  Object.assign(fs, saved);
  return { attempts, refused };
}
const outwardLink = {
  ancestor: () => ({ isSymbolicLink: () => true, isDirectory: () => false }),
  readlink: () => "C:\\outside-the-project-never-touched",
};
const inspectionFails = {
  ancestor: () => { throw Object.assign(new Error("EACCES: permission denied"), { code: "EACCES" }); },
  readlink: () => "unused",
};
for (const [name, world] of [["outward-link ancestor", outwardLink], ["inspection-failure ancestor", inspectionFails]]) {
  const r = intercepted(world, () => setupFixture(guard));
  report(r.attempts.length === 0 && r.refused !== null,
    `B: guarded fixture setup refuses a ${name} before any mutation (attempts=${r.attempts.length})`);
}
const lex = intercepted(outwardLink, lexicalOnlySetup);
report(lex.attempts.length > 0,
  `B: control (lexical-only setup) is caught: under an outward-link ancestor it made ${lex.attempts.length} mutation attempt(s)`);

// ---- Part A: the real fixture (guarded), then the writer cases --------------------------------------------
const fx = setupFixture(guard);
process.env.FS_GUARD_ROOT = fx.boundary;
const narrow = await import(`${guardUrl}?narrow`);
delete process.env.FS_GUARD_ROOT;

const source = fs.readFileSync(path.join(here, "abort_trigger_probe.mjs"), "utf8");
const start = source.indexOf("\nwriteFileSync(") + 1;
const end = source.indexOf(");\n", start) + 2;
const statement = source.slice(start, end);
if (!statement.startsWith("writeFileSync(assertOutput(outPath),")) throw new Error(`unexpected writer: ${statement.slice(0, 60)}`);

function runWriter(stmt, outPath) {
  const attempts = [];
  let refused = null;
  try {
    new Function("writeFileSync", "assertOutput", "outPath", "process", "shellConfig", "results", stmt)(
      (p) => { attempts.push(String(p)); }, narrow.assertOutput, outPath, { platform: "x", versions: { node: "x" } }, {}, []);
  } catch (e) { refused = e.message; }
  return { attempts, refused };
}
for (const [name, out, want] of [
  ["legitimate output inside the boundary", path.join(fx.boundary, "out.json"), 1],
  ["output outside the boundary (inside the project)", path.join(fx.elsewhere, "out.json"), 0],
  ["foreign absolute output", "C:/Windows/Temp/wp133d-never.json", 0],
  ["output under a junction parent leading outside", path.join(fx.link, "out.json"), 0],
]) {
  const r = runWriter(statement, out);
  report(r.attempts.length === want && (want === 0) === (r.refused !== null),
    `A: ${name}: attempts=${r.attempts.length} refused=${r.refused !== null}`);
}
const c = runWriter(statement.replace("assertOutput(outPath)", "outPath"), path.join(fx.elsewhere, "out.json"));
report(c.attempts.length === 1 && c.refused === null,
  `A: control (proof removed) is caught: the outside case made ${c.attempts.length} write attempt(s)`);

const cleaned = guard.cleanupSandbox(fx.base);
report(cleaned, "fixture removed by cleanupSandbox (the junction as an entry, never its target)");
console.log(failed ? `OUTPUT CONTROLS FAILED (${failed})` : "OUTPUT CONTROLS PASSED");
process.exitCode = failed ? 1 : 0;
