// Intercepted refusal controls for run-ce01.mjs. Every fs write and capture open, sandbox creation and spawn is
// counted and NEVER reaches the OS. Only the reviewed fs-guard's real proofs run, plus this script's own contained
// setup (one control sandbox and C3's junction to the drive root, created through assertEntry).
//   P1  all succeed: node, python, compare in order; 9 captures, all "wx", all inside the run dir.
//   C1  bad run names -> refused, 0 mkdir, 0 spawn of a probe, 0 writes.
//   C2  the run directory exists -> refused before mkdir.
//   C3  outward output entry: node.out is a junction to the drive root -> refused at that open, no probe started.
//   C4  a probe exits nonzero -> SETUP FAILURE, and the comparator is never started.
//   C5  wrong HEAD or a dirty tree -> refused before mkdir.
//   C6  every intercepted spawn above has no timeout, no killSignal and an unbounded maxBuffer.
//   node run-ce01-controls.mjs
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { GUARD_PATH, launch } from "./run-ce01.mjs";

const guard = await import(pathToFileURL(GUARD_PATH).href);
const ROOT = guard.PROJECT_ROOT;
const HEAD = "1".repeat(40); // git is faked
const HERE = path.join(ROOT, ".tmp", "claude-scratch", "i235", "ce01");
const work = guard.makeSandbox(path.join(HERE, `controls-${Date.now()}`));
let failed = 0;
const KILLABLE = [];
const verdict = (ok, label, detail) => { if (!ok) failed++; console.log(ok ? "PASS" : "FAIL", label, JSON.stringify(detail)); };

function fakes({ head = HEAD, dirty = "", status = () => 0, existing = () => false, guardOverride = {} } = {}) {
  const counts = { writes: [], mkdirs: [], probes: [], flags: [] };
  const g = {
    ...guard,
    makeSandbox: (dir) => { guard.proveReferentAbs(dir); counts.mkdirs.push(dir); return path.resolve(dir); },
    ...guardOverride,
  };
  const fsFake = {
    lstatSync: (p) => {
      const abs = path.resolve(p);
      if (abs.startsWith(path.join(HERE, "ctl-"))) {
        if (existing(abs)) return { isSymbolicLink: () => false, isDirectory: () => true, isFile: () => false };
        const e = new Error("ENOENT (control)"); e.code = "ENOENT"; throw e;
      }
      return fs.lstatSync(p);
    },
    openSync: (p, flags) => { counts.writes.push(p); counts.flags.push(flags); return 3000 + counts.writes.length; },
    closeSync: () => {},
    writeFileSync: (p, _d, o) => { counts.writes.push(p); counts.flags.push(o?.flag); },
  };
  const spawnSync = (cmd, args, opts = {}) => {
    if ("timeout" in opts || "killSignal" in opts || opts.maxBuffer !== Infinity) KILLABLE.push({ cmd, opts: Object.keys(opts) });
    if (cmd === "git" && args.includes("rev-parse")) return { status: 0, stdout: head + "\n", stderr: "" };
    if (cmd === "git" && args.includes("status")) return { status: 0, stdout: dirty, stderr: "" };
    const label = args.some((a) => String(a).endsWith("read_domain_node.mjs")) ? "node"
      : args.some((a) => String(a).endsWith("read_domain_python.py")) ? "python"
      : args.some((a) => String(a).endsWith("compare_read_domain.py")) ? "compare" : `?${cmd}`;
    counts.probes.push(label);
    return { status: status(label) };
  };
  const deps = { guard: g, fs: fsFake, spawnSync, env: {}, nodePath: "node", nodeVersion: "v22.15.1" };
  return { deps, counts };
}

const attempt = (name, deps) => { try { return { ok: true, value: launch(name, HEAD, deps, ROOT) }; } catch (e) { return { ok: false, message: e.message }; } };

{
  const { deps, counts } = fakes();
  const r = attempt("ctl-p1", deps);
  const run = path.join(HERE, "ctl-p1");
  verdict(r.ok && !r.value.setupFailure && counts.probes.join() === "node,python,compare" && counts.writes.length === 9
    && counts.flags.every((f) => f === "wx") && counts.writes.every((w) => path.dirname(w) === run) && counts.mkdirs.length === 2,
  "P1 node, python, compare; 9 exclusive captures inside the run dir", { r, counts });
}
for (const bad of ["", "..", "a/b", "C:x", "x\\y", "../x", "A", "-x"]) {
  const { deps, counts } = fakes();
  const r = attempt(bad, deps);
  verdict(!r.ok && /plain component/.test(r.message) && counts.mkdirs.length === 0 && counts.probes.length === 0 && counts.writes.length === 0,
    `C1 bad run name ${JSON.stringify(bad)} refused`, { message: r.message });
}
{
  const { deps, counts } = fakes({ existing: (abs) => abs.endsWith(`${path.sep}ctl-c2`) });
  const r = attempt("ctl-c2", deps);
  verdict(!r.ok && /run directory exists/.test(r.message) && counts.mkdirs.length === 0 && counts.writes.length === 0,
    "C2 existing run directory refused", { message: r.message });
}
{
  const runDir = path.join(HERE, "ctl-c3");
  const sandbox = guard.makeSandbox(path.join(work, "c3"));
  fs.symlinkSync(process.platform === "win32" ? "C:\\" : "/", guard.assertEntry(sandbox, "node.out"), "junction");
  const { deps, counts } = fakes({ guardOverride: {
    makeSandbox: (dir) => { counts.mkdirs.push(dir); return path.resolve(dir); },
    assertOutput: (file) => guard.assertOutput(path.join(sandbox, path.relative(runDir, file))),
  } });
  const r = attempt("ctl-c3", deps);
  verdict(!r.ok && /fs-guard/.test(r.message) && counts.writes.length === 0 && counts.probes.length === 0,
    "C3 outward output entry refused at the first capture open, no probe started", { message: r.message });
}
{
  const { deps, counts } = fakes({ status: (label) => (label === "python" ? 1 : 0) });
  const r = attempt("ctl-c4", deps);
  verdict(r.ok && r.value.setupFailure && counts.probes.join() === "node,python",
    "C4 a nonzero probe is a setup failure; the comparator never starts", { r, probes: counts.probes });
}
for (const [label, opts] of [["head", { head: "0".repeat(40) }], ["dirty", { dirty: " M x\n" }]]) {
  const { deps, counts } = fakes(opts);
  const r = attempt("ctl-c5", deps);
  verdict(!r.ok && /(is not the expected|dirty)/.test(r.message) && counts.mkdirs.length === 0 && counts.probes.length === 0,
    `C5 ${label} refused before mkdir`, { message: r.message });
}
verdict(KILLABLE.length === 0, "C6 no launch is configured for automatic termination", { KILLABLE });
console.log(failed ? `${failed} FAILED` : "ALL PASS");
process.exit(failed ? 1 : 0);
