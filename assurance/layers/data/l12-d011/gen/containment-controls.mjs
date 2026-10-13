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
// ---- The container's host-bound transfer (review 2): io.transfer, the ONE write to /out ----------------------------
// A second guard instance with the container's two roots emulated inside the project (FS_GUARD_ROOT, FS_GUARD_OUTPUT).
// The emulated roots exist, as /tmp/guard-root and /out do in the container: an empty fixture made ONLY through the
// reviewed guard (makeSandbox: ancestry proven before mkdir) and removed by cleanupSandbox at the end.
const FIXTURE = guard.makeSandbox(path.join(SCRATCH, `transfer-controls-${process.pid}`));
const CTL_ROOT = guard.makeSandbox(path.join(FIXTURE, "root"));
const CTL_OUT = guard.makeSandbox(path.join(FIXTURE, "out"));
process.env.FS_GUARD_ROOT = CTL_ROOT;
process.env.FS_GUARD_OUTPUT = CTL_OUT;
const tguard = await import(pathToFileURL(path.join(here, "../../l12-d007/fs-guard/fs-guard.mjs")).href + "?transfer");
delete process.env.FS_GUARD_ROOT;
delete process.env.FS_GUARD_OUTPUT;
const SRC = path.join(CTL_ROOT, "w", "linux-partial.json");
const DST = path.join(CTL_OUT, "linux-partial.json");
const outDir = { path: path.join(CTL_OUT, ".unused"), lstat: () => ({ isSymbolicLink: () => false, isDirectory: () => true }) };
function transferCase(steer, mod = io) {
  const savedRead = fs.readFileSync;
  fs.readFileSync = (p, ...rest) => (eq(p, SRC) ? Buffer.from("partial") : savedRead(p, ...rest));
  try { return intercepted(steer, () => mod.transfer(tguard, SRC, DST)); } finally { fs.readFileSync = savedRead; }
}
const legitT = transferCase([outDir]);
report(legitT.refused === null && legitT.attempts.length === 1 && eq(legitT.attempts[0].slice(6), DST),
  `transfer: legitimate /out destination: one attempt (${legitT.attempts.length}), nothing written natively`);
for (const [label, steer] of [
  ["an outward final /out entry", [outDir, outward(DST)]],
  ["an outward /out ancestor", [outward(CTL_OUT)]],
  ["an inspection-failure /out ancestor", [eacces(CTL_OUT)]],
]) {
  const r = transferCase(steer);
  report(refusedNone(r), `transfer refuses ${label} with zero mutations (attempts=${r.attempts.length})`);
}
const noTransferProof = await load(ioSource.replace("writeOutput(guard, destination, fs.readFileSync(source));",
  "fs.writeFileSync(destination, fs.readFileSync(source));"), "m3");
const m3 = transferCase([outDir, outward(DST)], noTransferProof);
report(m3.attempts.length === 1, `control: transfer without its proof is caught (attempts=${m3.attempts.length})`);
if (!ioSource.includes("writeOutput(guard, destination, fs.readFileSync(source));")) report(false, "transfer statement not found (INVALID control)");

// ---- Complete writer inventory of gen/ (review 2: the shell recipe included) --------------------------------------
// JavaScript: no filesystem mutation outside io.mjs. containment-controls.mjs itself is excluded: its only mutation
// texts are the interceptors' assignments and the mutants' source-string replacements, never a native call.
const JS_WRITE = /\b(writeFileSync|mkdirSync|appendFileSync|rmSync|rmdirSync|unlinkSync|renameSync|copyFileSync|symlinkSync|cpSync|writeFile|mkdir|appendFile|rm|rmdir|unlink|rename|copyFile|symlink|cp)\s*\(/;
const files = fs.readdirSync(here).filter((f) => !fs.lstatSync(path.join(here, f)).isDirectory());
for (const f of files.filter((f) => f.endsWith(".mjs") && f !== "io.mjs" && f !== "containment-controls.mjs")) {
  report(!JS_WRITE.test(fs.readFileSync(path.join(here, f), "utf8")), `inventory: ${f} makes no filesystem mutation outside io.mjs`);
}
// Shell: every write target is a fixed literal under /tmp/; /out appears only as transfer.mjs's argument.
export function shellViolations(text) {
  const lines = text.replace(/\\\r?\n/g, " ").split(/\r?\n/).map((l) => l.replace(/#.*$/, "").trim()).filter(Boolean);
  const bad = [];
  for (const line of lines) {
    for (const cmd of line.split(/&&|;|\|/).map((c) => c.trim()).filter(Boolean)) {
      const t = cmd.split(/\s+/);
      const targets = [];
      if (t[0] === "mkdir" || t[0] === "chmod" || t[0] === "chown") targets.push(...t.slice(1).filter((x) => x.startsWith("/")));
      if (t[0] === "tar") { const i = t.indexOf("-C"); targets.push(i >= 0 ? t[i + 1] : "<cwd>"); }
      if (["cp", "mv", "install", "ln", "tee", "dd", "rsync"].includes(t[0])) targets.push(t[t.length - 1]);
      for (const m of cmd.matchAll(/(?:^|[^0-9&])>>?\s*(\S+)/g)) targets.push(m[1]);
      for (const x of targets) if (!x.startsWith("/tmp/") && x !== "/dev/null") bad.push(`${t[0]} -> ${x}`);
    }
    if (line.includes("/out") && !/\/data\/l12-d011\/gen\/transfer\.mjs/.test(line)) bad.push(`/out outside the transfer: ${line.slice(0, 80)}`);
  }
  return bad;
}
for (const f of files.filter((f) => f.endsWith(".sh"))) {
  const v = shellViolations(fs.readFileSync(path.join(here, f), "utf8"));
  report(v.length === 0, `inventory: ${f} writes only private /tmp literals and /out only via transfer.mjs${v.length ? ` (${v.join("; ")})` : ""}`);
}
const oldRecipe = "cp /tmp/guard-root/w/linux-partial.json /out/linux-partial.json\n";
report(shellViolations(oldRecipe).length > 0, "control: the review-2 bare cp to /out is flagged by the inventory");
report(shellViolations("echo x > /out/f\n").length > 0 && shellViolations("tar -xzf a.tgz -C /out\n").length > 0,
  "control: a redirect or extraction into /out is flagged");
report(files.includes("gen-linux.sh") && files.includes("transfer.mjs"), "inventory covers gen-linux.sh and transfer.mjs");
report(guard.cleanupSandbox(FIXTURE), "transfer fixture removed by cleanupSandbox (two empty directories)");
console.log(failed ? `CONTAINMENT CONTROLS FAILED (${failed})` : "CONTAINMENT CONTROLS PASSED");
process.exitCode = failed ? 1 : 0;
