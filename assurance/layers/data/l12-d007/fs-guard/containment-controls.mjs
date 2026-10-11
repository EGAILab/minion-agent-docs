// L12D007-C001 permanent rejecting controls (run: node containment-controls.mjs <pi checkout>).
// Every outside-root mutation in the child processes is intercepted by intercept.mjs (refused and
// logged), so a broken guard is detected WITHOUT any outside write ever reaching the OS.
//   1. the real oracle, given an outside output path, must refuse with NO outside mutation attempted;
//   2. a mutant oracle (its output guard removed) must be CAUGHT: an attempted outside write logged;
//   3. makeSandbox through a junction that points outside must refuse before any mkdir is reached.
import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath, pathToFileURL } from "node:url";
import { PROJECT_ROOT, makeSandbox } from "./fs-guard.mjs";

const here = path.dirname(fileURLToPath(import.meta.url));
const gen = path.join(here, "..", "gen");
const piDir = process.argv[2];
const work = makeSandbox(path.join(PROJECT_ROOT, ".tmp", "fs-guard-controls", `run-${Date.now()}`));
const emptyCases = path.join(work, "empty-cases.json");
fs.writeFileSync(emptyCases, JSON.stringify({ cases: [] }));
const OUTSIDE = process.platform === "win32" ? "C:/outside-owner-root/authority.json" : "/outside-owner-root/authority.json";
let bad = 0;
const verdict = (ok, label) => { if (!ok) bad++; console.log(ok ? "PASS" : "FAIL", label); };

function runOracle(script, tag) {
  const log = path.join(work, `${tag}.intercepts`);
  fs.writeFileSync(log, "");
  const r = spawnSync(process.execPath, ["--experimental-strip-types", "--no-warnings", "--import", pathToFileURL(path.join(here, "intercept.mjs")).href,
    script, piDir, emptyCases, OUTSIDE], { encoding: "utf8", env: { ...process.env, FS_INTERCEPT_LOG: log }, cwd: gen });
  return { status: r.status, stderr: r.stderr, attempted: fs.readFileSync(log, "utf8").trim() };
}

// 1. the real oracle.
const real = runOracle(path.join(gen, "pi_oracle.mjs"), "real");
verdict(real.status !== 0 && /fs-guard: output/.test(real.stderr) && real.attempted === "",
  `real oracle refuses an outside output before any outside mutation (exit ${real.status}; attempted: ${real.attempted || "none"})`);

// 2. the mutant: assertOutput removed from the final write. Placed next to the real oracle so its imports resolve.
const src = fs.readFileSync(path.join(gen, "pi_oracle.mjs"), "utf8");
if (src.split("fs.writeFileSync(assertOutput(outPath),").length !== 2) throw new Error("mutant anchor");
const mutantPath = path.join(gen, `.mutant-no-output-guard-${process.pid}.mjs`);
fs.writeFileSync(mutantPath, src.replace("fs.writeFileSync(assertOutput(outPath),", "fs.writeFileSync(outPath,"));
let mutant;
try { mutant = runOracle(mutantPath, "mutant"); } finally { fs.unlinkSync(mutantPath); }
verdict(mutant.attempted.includes("outside-owner-root"),
  `mutant oracle (no output guard) is caught by the intercept (attempted: ${mutant.attempted || "none"})`);

// 3. makeSandbox through an outward junction: mkdirSync must not be reached.
const jdir = path.join(work, "j-out");
fs.symlinkSync(process.platform === "win32" ? "C:\\" : "/", jdir, process.platform === "win32" ? "junction" : "dir");
const realMkdir = fs.mkdirSync;
let mkdirCalls = 0;
fs.mkdirSync = (...a) => { mkdirCalls++; throw new Error("intercepted mkdir"); };
let refused = false;
try { makeSandbox(path.join(jdir, "sandbox")); } catch (e) { refused = /fs-guard/.test(e.message); }
fs.mkdirSync = realMkdir;
verdict(refused && mkdirCalls === 0, `makeSandbox through an outward junction refuses before mkdir (mkdir calls: ${mkdirCalls})`);

// No cleanup of the junction (never risk a removal through it); the work dir stays under .tmp.
console.log(bad ? `${bad} FAILED` : "ALL PASS");
process.exit(bad ? 1 : 0);
