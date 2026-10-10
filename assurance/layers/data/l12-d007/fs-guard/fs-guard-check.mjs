// Self-test for fs-guard.mjs: node fs-guard-check.mjs
// Builds links INSIDE its own sandbox (some pointing outside) and only asks the guard about them;
// it never writes, renames or deletes through any link. Exit 1 on any wrong answer.
import fs from "node:fs";
import path from "node:path";
import { PROJECT_ROOT, makeSandbox, assertInside, assertOutput } from "./fs-guard.mjs";

const sb = makeSandbox(path.join(PROJECT_ROOT, ".tmp", "fs-guard-check", `run-${Date.now()}`));
const outside = process.platform === "win32" ? "C:\\fs-guard-check-never-created" : "/fs-guard-check-never-created";
const link = (name, target, dir = false) => fs.symlinkSync(target, path.join(sb, name), dir ? "junction" : undefined);
fs.mkdirSync(path.join(sb, "d"));
link("out-dangling", outside);                    // dangling, outside
link("in-dangling", "nothing-here");              // dangling, inside
link("loop-a", "loop-b");
link("loop-b", "loop-a");                        // a loop that stays inside
link("hop-out", "in-to-out");
link("in-to-out", outside);                       // two hops, the second outside
link("j-out", process.platform === "win32" ? "C:\\" : "/", true); // a directory link to a drive / fs root

const cases = [
  ["a" + "\\..".repeat(17), false], ["f:stream:bad", false], ["./f:stream:bad", true], ["E:", false], ["E:\\", false],
  ["..", false], [".", false], ["sub/x", true], ["n".repeat(300), true], ["x<y", true], ["d/new", true],
  ["out-dangling", false], ["in-dangling", true], ["loop-a", true], ["hop-out", false], ["j-out/x", false],
  ["d/../out-dangling", false],
];
let bad = 0;
for (const [t, want] of cases) {
  let ok;
  try { assertInside(sb, t); ok = true; } catch { ok = false; }
  if (ok !== want) bad++;
  console.log(ok === want ? "PASS" : "FAIL", ok ? "allowed" : "refused", JSON.stringify(t.slice(0, 40)));
}
for (const s of ["E:/", process.platform === "win32" ? "C:/temp/x" : "/tmp/x", PROJECT_ROOT, path.join(sb, "j-out", "x")]) {
  try { makeSandbox(s); bad++; console.log("FAIL sandbox allowed", s); } catch { console.log("PASS sandbox refused", s); }
}
for (const [o, want] of [[path.join(sb, "result.json"), true], [path.join(sb, "out-dangling"), false], [outside, false], [path.join(sb, "j-out", "o.json"), false]]) {
  let ok;
  try { assertOutput(o); ok = true; } catch { ok = false; }
  if (ok !== want) bad++;
  console.log(ok === want ? "PASS" : "FAIL", "output", ok ? "allowed" : "refused", o);
}
// Deliberately NO cleanup: the sandbox (with its links) stays under the project's .tmp. Removing
// link entries -- one of them a junction to a drive root -- is not worth any risk.
console.log(bad ? `${bad} FAILED` : "ALL PASS");
process.exit(bad ? 1 : 0);
