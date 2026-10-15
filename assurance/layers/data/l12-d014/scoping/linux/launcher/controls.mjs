// Refusal controls for run-home-linux.mjs (Codex paper check). Each runs launch() with INTERCEPTED dependencies:
// every fs write, every run-directory creation and every docker run is counted and NEVER reaches the OS (the
// fakes record and refuse). Only real proofs (the reviewed fs-guard) run, plus the control's own contained setup.
//   C1 final-output link: the first capture entry is a junction pointing outside the root -> refused, 0 writes.
//   C2 ancestor inspection failure: the guard cannot inspect an ancestor of a bind source -> refused, 0 mkdir,
//      0 docker runs, 0 writes.
//   C3 foreign bind: a bind source outside the root -> refused, 0 mkdir, 0 docker runs, 0 writes.
//   C4 container A fails -> its captures are written (counted, not performed), B is never started.
// Positive: P1 with every dependency faked to succeed, both containers run and 6 captures are written (counted).
//   node controls.mjs
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { GUARD_PATH, launch, sources } from "./run-home-linux.mjs";

const guard = await import(pathToFileURL(GUARD_PATH).href);
const ROOT = guard.PROJECT_ROOT;
const work = guard.makeSandbox(path.join(ROOT, ".tmp", "claude-scratch", "i236", `controls-${Date.now()}`));
let failed = 0;
const verdict = (ok, label, detail) => { if (!ok) failed++; console.log(ok ? "PASS" : "FAIL", label, JSON.stringify(detail)); };

function fakes({ dockerRunStatus = () => 0, guardOverride = {}, existing = new Set() } = {}) {
  const counts = { writes: [], mkdirs: [], dockerRuns: [] };
  const g = {
    ...guard,
    makeSandbox: (dir) => { guard.proveReferentAbs(dir); counts.mkdirs.push(dir); return path.resolve(dir); },
    ...guardOverride,
  };
  const fsFake = {
    lstatSync: (p) => {
      if (path.resolve(p).startsWith(path.join(ROOT, ".tmp", "claude-scratch", "i236", "ctl-")) && !existing.has(path.resolve(p))) {
        const e = new Error("ENOENT (control: the run directory does not exist yet)"); e.code = "ENOENT"; throw e;
      }
      return fs.lstatSync(p);
    },
    writeFileSync: (p) => { counts.writes.push(p); },
  };
  const spawnSync = (cmd, args) => {
    if (cmd === "git") return { status: 0, stdout: "1225efb92af89ddd67c34d8d2fd0e4a4c2b30645\n", stderr: "" };
    if (cmd === "docker" && args[0] === "image") return { status: 0, stdout: args[2] + "\n", stderr: "" };
    if (cmd === "docker" && args[0] === "run") {
      const tag = args.includes("--network") ? "a-rust" : "b-python";
      counts.dockerRuns.push(tag);
      return { status: dockerRunStatus(tag), stdout: "{}", stderr: "" };
    }
    throw new Error(`unexpected spawn ${cmd}`);
  };
  return { deps: { guard: g, fs: fsFake, spawnSync }, counts };
}

function attempt(name, deps, binds) {
  try { return { ok: true, value: launch(name, deps, ROOT, binds) }; } catch (e) { return { ok: false, message: e.message }; }
}

// P1 positive.
{
  const { deps, counts } = fakes();
  const r = attempt("ctl-p1", deps);
  verdict(r.ok && counts.dockerRuns.join() === "a-rust,b-python" && counts.writes.length === 6 && counts.mkdirs.length === 1,
    "P1 all dependencies succeed: both containers, 6 counted captures", { r, counts });
}

// C1: the real final-output entry is an outward junction.
{
  const runDir = path.join(ROOT, ".tmp", "claude-scratch", "i236", "ctl-c1");
  const sandbox = guard.makeSandbox(path.join(work, "c1"));
  const link = path.join(sandbox, "a-rust.exit");
  fs.symlinkSync(process.platform === "win32" ? "C:\\" : "/", guard.assertEntry(sandbox, "a-rust.exit"), "junction");
  const { deps, counts } = fakes({ guardOverride: {
    makeSandbox: (dir) => { counts.mkdirs.push(dir); return path.resolve(dir); },
    assertOutput: (file) => guard.assertOutput(path.join(sandbox, path.relative(runDir, file))),
  } });
  const r = attempt("ctl-c1", deps);
  verdict(!r.ok && /fs-guard/.test(r.message) && counts.writes.length === 0 && counts.dockerRuns.length === 1,
    "C1 outward final-output link refused before any write", { message: r.message, counts, link });
}

// C2: an ancestor of a bind source cannot be inspected (the guard's own refusal, injected at that source).
{
  const binds = sources(ROOT);
  const { deps, counts } = fakes({ guardOverride: {
    proveReferentAbs: (abs) => {
      if (path.resolve(abs) === path.resolve(binds.icu.src)) {
        throw new Error(`fs-guard: cannot inspect ${path.dirname(path.resolve(abs))} (EACCES); refused`);
      }
      return guard.proveReferentAbs(abs);
    },
  } });
  const r = attempt("ctl-c2", deps, binds);
  verdict(!r.ok && /cannot inspect/.test(r.message) && counts.mkdirs.length === 0 && counts.dockerRuns.length === 0
    && counts.writes.length === 0, "C2 ancestor inspection failure refused before mkdir/mount/write", { message: r.message, counts });
}

// C3: a foreign (outside-root) bind source.
{
  const binds = { ...sources(ROOT), pipcache: { src: process.platform === "win32" ? "C:\\Windows" : "/usr", kind: "dir", target: "/pipcache", rw: true } };
  const { deps, counts } = fakes();
  const r = attempt("ctl-c3", deps, binds);
  verdict(!r.ok && /fs-guard/.test(r.message) && counts.mkdirs.length === 0 && counts.dockerRuns.length === 0
    && counts.writes.length === 0, "C3 foreign bind refused before mkdir/mount/write", { message: r.message, counts });
}

// C4: container A fails -> B never starts.
{
  const { deps, counts } = fakes({ dockerRunStatus: (tag) => (tag === "a-rust" ? 1 : 0) });
  const r = attempt("ctl-c4", deps);
  verdict(!r.ok && /a-rust failed/.test(r.message) && counts.dockerRuns.join() === "a-rust" && counts.writes.length === 3,
    "C4 failed container A stops the run before B", { message: r.message, counts });
}

console.log(failed ? `${failed} FAILED` : "ALL PASS");
process.exit(failed ? 1 : 0);
