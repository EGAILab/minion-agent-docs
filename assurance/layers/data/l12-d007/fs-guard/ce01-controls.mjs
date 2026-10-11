// CE-L12D007-01 permanent rejecting controls (node ce01-controls.mjs).
// Runs ce01-suite.mjs against the REAL guard/intercept and against each negative-control MUTANT, in
// child processes under synthetic.mjs (virtual link metadata; every mutation recorded, none reaches
// the OS). The real variant must pass every control; each mutant must be KILLED by its intended
// control(s). The driver's own writes (variant copies) are REFERENT-guarded under a makeSandbox root.
import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath, pathToFileURL } from "node:url";
import { PROJECT_ROOT, makeSandbox, assertInside } from "./fs-guard.mjs";

const here = path.dirname(fileURLToPath(import.meta.url));
const FILES = ["fs-guard.mjs", "intercept.mjs", "synthetic.mjs", "ce01-suite.mjs"];
// Normalized to LF so the mutant anchors match on a CRLF (core.autocrlf) checkout too; a failed anchor
// is an error, never a kill.
const src = Object.fromEntries(FILES.map((f) => [f, fs.readFileSync(path.join(here, f), "utf8").replace(/\r\n/g, "\n")]));
const work = makeSandbox(path.join(PROJECT_ROOT, ".tmp", "ce01-controls", `run-${Date.now()}`));

// [name, file, old, new, the control(s) that must fail]
const MUTANTS = [
  ["1 budget-accept", "fs-guard.mjs", "  throw new Error(`fs-guard: ${what}: ${BUDGET}-hop budget exhausted without a repeated state; refused`);", "  return pending;", ["budget_plus_one_contained_refused"]],
  ["2 catch-all-missing", "fs-guard.mjs", "    if (MISSING.has(e?.code)) return null;", "    return null;", ["ancestor_EACCES_refused"]],
  ["3 unchecked-last-hop", "fs-guard.mjs", "    if (!inside(redirected)) throw new Error(`fs-guard: ${what} reaches ${redirected} through a link, outside ${boundary}`);\n    pending = redirected;\n  }\n  throw new Error(`fs-guard: ${what}: ${BUDGET}-hop budget exhausted without a repeated state; refused`);",
    "    pending = redirected;\n  }\n  return pending;", ["last_hop_outward_refused"]],
  ["4 lexical-intercept", "intercept.mjs", "        if (cls === \"REFERENT\") proveReferentAbs(target);\n        else proveEntryAbs(target);", "        void cls;", ["intercept_write_through_outward_ancestor_refused"]],
  ["5 restore-without-proof", "fs-guard.mjs", "  let target;\n  try {\n    target = assertInside(sandbox, rel);", "  restore(path.resolve(sandbox, rel)); return true;\n  let target;\n  try {\n    target = assertInside(sandbox, rel);", ["f_restore_missing_skipped"]],
  ["22 swallow-restore-failure", "fs-guard.mjs", "  restore(target); // a restore that runs and fails propagates", "  try { restore(target); } catch { return false; }", ["f_restore_failure_propagates"]],
  ["6 tool-traversal-cleanup", "fs-guard.mjs", "    walkClean(path.resolve(root), path.resolve(root));", "    execFileSync(\"icacls\", [path.resolve(root), \"/reset\", \"/T\", \"/C\", \"/Q\"]);", ["c_cleanup_removes_link_as_entry_only"]],
  ["8 parent-only-everywhere", "fs-guard.mjs", "  const lexical = lexicalInside(sandbox, target, cwd);\n  prove(lexical, sandbox, target);\n  return lexical;", "  return assertEntry(sandbox, target, cwd);", ["a_referent_through_outward_link_refused"]],
  ["9 follow-final-in-cleanup", "fs-guard.mjs", "    if (st.isSymbolicLink()) { removeLinkEntry(child); continue; } // as itself; never descended", "    if (st.isSymbolicLink()) { walkClean(root, child); removeLinkEntry(child); continue; }", ["c_cleanup_removes_link_as_entry_only"]],
  ["10 entry-proof-authorizes-write", "intercept.mjs", "  writeFileSync: [[0, R]],", "  writeFileSync: [[0, E]],", ["intercept_write_to_outward_final_link_refused"]],
  ["14 blanket-ENAMETOOLONG-is-missing", "fs-guard.mjs", "    if (e?.code === \"ENAMETOOLONG\" && overlongComponent(path.dirname(p), path.basename(p), p)) return null;", "    if (e?.code === \"ENAMETOOLONG\") return null;", ["W2_path_max_overflow_refused", "W3_at_limit_component_refused", "W5_under_limit_component_refused"]],
  ["15 refuse-every-overlong", "fs-guard.mjs", "  const nameMax = queryLimit(\"NAME_MAX\", dir);", "  return false;\n  const nameMax = queryLimit(\"NAME_MAX\", dir);", ["W1_overlong_component_admitted", "W4_bytes_not_characters_admitted"]],
  ["16 assume-255", "fs-guard.mjs", "  const nameMax = queryLimit(\"NAME_MAX\", dir);", "  const nameMax = queryLimit(\"NAME_MAX\", dir) ?? 255;", ["W6_name_max_unavailable_refused"]],
  ["17 assume-default-PATH_MAX", "fs-guard.mjs", "  const pathMax = queryLimit(\"PATH_MAX\", dir);", "  const pathMax = queryLimit(\"PATH_MAX\", dir) ?? 1048576;", ["W7_path_max_unavailable_refused"]],
  ["18 character-count", "fs-guard.mjs", "  if (nameMax === null || nativeBytes(name) <= nameMax) return false;", "  if (nameMax === null || name.length <= nameMax) return false;", ["W4_bytes_not_characters_admitted"]],
  ["19 skip-path-max", "fs-guard.mjs", "  return pathMax !== null && nativeBytes(full) + 1 <= pathMax;", "  return true;", ["W2_path_max_overflow_refused"]],
  ["20 omit-NUL", "fs-guard.mjs", "  return pathMax !== null && nativeBytes(full) + 1 <= pathMax;", "  return pathMax !== null && nativeBytes(full) <= pathMax;", ["W9b_path_max_terminator_refused"]],
  ["21 lexical-dotdot-link-text", "fs-guard.mjs", "        if (String(text).split(/[\\\\/]/).includes(\"..\")) throw new Error(`fs-guard: link ${cur} text ${text} has a \"..\" segment; refused`);\n", "", ["dotdot_referent_refused", "dotdot_entry_below_refused"]],
  ["12 restore-on-absence", "fs-guard.mjs", "    if (st === null) return log(`fs-guard: restore skipped, ${rel} is missing`), false;", "    if (st === null) { restore(target); return true; }", ["f_restore_missing_skipped"]],
];

function variant(name, file, oldText, newText) {
  const dir = assertInside(work, name.replace(/[^a-z0-9]+/gi, "-"));
  fs.mkdirSync(dir);
  for (const f of FILES) {
    let text = src[f];
    if (f === file) {
      if (text.split(oldText).length !== 2) throw new Error(`mutant anchor: ${name}`);
      text = text.replace(oldText, newText);
    }
    fs.writeFileSync(assertInside(work, path.relative(work, path.join(dir, f))), text);
  }
  return dir;
}

function run(dir) {
  const results = {};
  for (const intercept of [false, true]) {
    const args = ["--import", pathToFileURL(path.join(dir, "synthetic.mjs")).href];
    if (intercept) args.push("--import", pathToFileURL(path.join(dir, "intercept.mjs")).href);
    args.push(path.join(dir, "ce01-suite.mjs"), path.join(dir, "fs-guard.mjs"), intercept ? "intercept" : "");
    const p = spawnSync(process.execPath, args, { encoding: "utf8", env: { ...process.env, SYN_ROOT: path.join(dir, "virtual") } });
    const line = p.stdout.trim().split("\n").pop();
    if (p.status !== 0 || !line?.startsWith("{")) return { __crash: `${p.status} ${p.stderr.slice(0, 300)}` };
    Object.assign(results, JSON.parse(line));
  }
  return results;
}

let bad = 0;
const realDir = variant("real", null, "", "");
const real = run(realDir);
const failing = Object.entries(real).filter(([, ok]) => ok !== true).map(([k]) => k);
console.log(failing.length ? `FAIL real guard: ${failing.join(", ")}` : `PASS real guard: all ${Object.keys(real).length} controls hold`);
if (failing.length) bad++;
for (const [name, file, oldText, newText, expect] of MUTANTS) {
  const res = run(variant(name, file, oldText, newText));
  const killed = res.__crash === undefined && expect.every((k) => res[k] === false);
  if (!killed) bad++;
  console.log(`${killed ? "KILLED" : "NOT KILLED"} ${name} by ${expect.join(", ")}${res.__crash ? ` (crash: ${res.__crash})` : ""}`);
}
console.log(bad ? `${bad} FAILED` : "ALL PASS");
process.exit(bad ? 1 : 0);
