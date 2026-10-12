// WP133D001-R002 controls: the abort-trigger probe's ONE output write is proven by fs-guard assertOutput
// immediately before it happens. The probe's actual writer statement is extracted from its source and executed
// with writeFileSync INTERCEPTED (no native write ever happens) and the real reviewed assertOutput, under a guard
// boundary narrowed to a fixture directory INSIDE the project (FS_GUARD_ROOT), so "outside" is tested without
// touching anything outside the project root.
//   node abort_trigger_output_controls.mjs
// Cases: a legitimate output (one write attempt); an output outside the boundary, and a foreign absolute path
// (refused, zero attempts); an output under a parent that is a junction leading outside the boundary (refused,
// zero attempts). Control: the statement with the proof removed must fail the outside case for its intended reason
// (a write attempt happens). Fixture paths derive from one literal base; every mutation checks containment first.
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

const PROJECT = "E:/AI/Projects/OpenMinds/Minions/Minion-Agent";
const BASE = path.resolve(`${PROJECT}/.tmp/claude-scratch/wp133d/output-controls-${process.pid}`);
const inside = (p) => {
  const abs = path.resolve(p);
  if (!abs.toLowerCase().startsWith(path.resolve(PROJECT).toLowerCase() + path.sep) || p.includes("..")) {
    throw new Error(`containment: ${abs}`);
  }
  return abs;
};
const boundary = inside(path.join(BASE, "boundary"));
const elsewhere = inside(path.join(BASE, "elsewhere"));
fs.mkdirSync(inside(boundary), { recursive: true });
fs.mkdirSync(inside(elsewhere), { recursive: true });
const link = inside(path.join(boundary, "linkdir"));
fs.symlinkSync(elsewhere, link, "junction");

process.env.FS_GUARD_ROOT = boundary; // the guard reads its root at import
const here = path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1"));
const { assertOutput } = await import(pathToFileURL(path.join(here, "../l12-d007/fs-guard/fs-guard.mjs")).href);

const source = fs.readFileSync(path.join(here, "abort_trigger_probe.mjs"), "utf8");
const start = source.indexOf("\nwriteFileSync(") + 1;
const end = source.indexOf(");\n", start) + 2;
const statement = source.slice(start, end);
if (!statement.startsWith("writeFileSync(assertOutput(outPath),")) throw new Error(`unexpected writer: ${statement.slice(0, 60)}`);

function run(stmt, outPath) {
  const attempts = [];
  const intercept = (p) => { attempts.push(String(p)); };
  let refused = null;
  try {
    new Function("writeFileSync", "assertOutput", "outPath", "process", "shellConfig", "results", stmt)(
      intercept, assertOutput, outPath, { platform: "x", versions: { node: "x" } }, {}, []);
  } catch (e) { refused = e.message; }
  return { attempts, refused };
}

const cases = [
  ["legitimate output inside the boundary", statement, path.join(boundary, "out.json"), 1],
  ["output outside the boundary (inside the project)", statement, path.join(elsewhere, "out.json"), 0],
  ["foreign absolute output", statement, "C:/Windows/Temp/wp133d-never.json", 0],
  ["output under a junction parent leading outside", statement, path.join(link, "out.json"), 0],
];
const control = statement.replace("assertOutput(outPath)", "outPath");
let failed = 0;
for (const [name, stmt, out, want] of cases) {
  const r = run(stmt, out);
  const ok = r.attempts.length === want && (want === 0) === (r.refused !== null);
  failed += !ok;
  console.log(`${ok ? "PASS" : "FAIL"} ${name}: attempts=${r.attempts.length} refused=${r.refused !== null}`);
}
const c = run(control, path.join(elsewhere, "out.json"));
const killed = c.attempts.length === 1 && c.refused === null;
failed += !killed;
console.log(`${killed ? "PASS" : "FAIL"} control (proof removed) is caught: the outside case made ${c.attempts.length} write attempt(s)`);

fs.unlinkSync(inside(link)); // the junction itself, never its target
fs.rmdirSync(inside(boundary));
fs.rmdirSync(inside(elsewhere));
fs.rmdirSync(inside(BASE));
console.log(failed ? `OUTPUT CONTROLS FAILED (${failed})` : "OUTPUT CONTROLS PASSED");
process.exitCode = failed ? 1 : 0;
