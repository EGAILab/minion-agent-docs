// Refusal controls for run-win-gates.mjs (for Codex's paper check). Each runs launch() with INTERCEPTED
// dependencies: every fs write, every sandbox creation and every spawn is counted and NEVER reaches the OS. Only the
// reviewed fs-guard's real proofs run, plus this script's own contained setup (one control sandbox; C4's junction).
//   P1  all dependencies succeed: every gate runs in order; pytest gets run/basetemp; every write is counted.
//   C1  bad run names ("", "..", "a/b", "C:x", "x\\y", "../x", "A") -> refused, 0 mkdir, 0 spawn of a gate, 0 writes.
//   C2  the run directory already exists -> refused, 0 mkdir, 0 writes.
//   C3  pytest's basetemp exists when pytest is due -> refused; pytest never spawned.
//   C4  outward output entry: the first log is a junction to the drive root -> refused at that write, 0 writes.
//   C5  an input's ancestor cannot be inspected -> refused before mkdir, 0 spawns of a gate, 0 writes.
//   C6  the memory preflight fails -> its log/exit are published (counted), no later gate is spawned.
//   C7  candidate HEAD differs, or the tree is dirty -> refused before mkdir.
//   C8  an ICU env line that is not a plain export -> refused before mkdir.
//   C9  every intercepted launch in every control above has no timeout, no killSignal and an unbounded maxBuffer.
//   node win-controls.mjs
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { GUARD_PATH, config, launch } from "./run-win-gates.mjs";

const guard = await import(pathToFileURL(GUARD_PATH).href);
const ROOT = guard.PROJECT_ROOT;
const HEAD = "8348102000000000000000000000000000000000"; // any 40-hex value: git is faked
const work = guard.makeSandbox(path.join(ROOT, ".tmp", "claude-scratch", "i235", `win-controls-${Date.now()}`));
let failed = 0;
const verdict = (ok, label, detail) => { if (!ok) failed++; console.log(ok ? "PASS" : "FAIL", label, JSON.stringify(detail)); };
const GATES = ["preflight", "icu", "ruff", "format-changed", "format-tree", "mypy", "pytest", "node-posix"];
const KILLABLE = []; // every intercepted spawn whose options could terminate it automatically

function fakes({ head = HEAD, dirty = "", icuEnv = "export MINION_AGENT_ICU_BIN='E:\\x'\nexport ICU_VERSION=78.3\n",
  status = () => 0, guardOverride = {}, existing = () => false } = {}) {
  const counts = { writes: [], mkdirs: [], gates: [], spawnArgs: {} };
  const g = {
    ...guard,
    makeSandbox: (dir) => { guard.proveReferentAbs(dir); counts.mkdirs.push(dir); return path.resolve(dir); },
    ...guardOverride,
  };
  const scratch = path.join(ROOT, ".tmp", "claude-scratch", "i235");
  const fsFake = {
    lstatSync: (p) => {
      const abs = path.resolve(p);
      if (abs.startsWith(path.join(scratch, "ctl-"))) {
        if (existing(abs)) return { isSymbolicLink: () => false, isDirectory: () => true, isFile: () => false };
        const e = new Error("ENOENT (control: not created)"); e.code = "ENOENT"; throw e;
      }
      return fs.lstatSync(p);
    },
    writeFileSync: (p) => { counts.writes.push(p); },
    openSync: (p, flags) => {
      if (flags !== "wx") throw new Error(`log ${p} opened with ${flags}, not wx`);
      counts.writes.push(p);
      return 1000 + counts.writes.length;
    },
    closeSync: () => {},
  };
  const spawnSync = (cmd, args, opts = {}) => {
    // Every production launch is checked: no automatic termination may be configured.
    if ("timeout" in opts || "killSignal" in opts || opts.maxBuffer !== Infinity) {
      KILLABLE.push({ cmd, timeout: opts.timeout, killSignal: opts.killSignal, maxBuffer: opts.maxBuffer });
    }
    if (cmd === "git" && args.includes("rev-parse")) return { status: 0, stdout: head + "\n", stderr: "" };
    if (cmd === "git" && args.includes("status")) return { status: 0, stdout: dirty, stderr: "" };
    if (cmd === "git" && args.includes("diff")) return { status: 0, stdout: "minion-agent-python/src/a.py\n", stderr: "" };
    if (cmd === "bash") return { status: 0, stdout: icuEnv, stderr: "" };
    const label = cmd === "powershell" ? "preflight"
      : args.includes("import icu") || String(args[1] ?? "").includes("import icu") ? "icu"
      : args[0] === "check" ? "ruff"
      : args[0] === "format" ? (args.includes("src") && args.includes("tests") ? "format-tree" : "format-changed")
      : args.includes("mypy") ? "mypy" : args.includes("pytest") ? "pytest" : args[0] === "-p" ? "node-posix" : `?${cmd}`;
    counts.gates.push(label);
    counts.spawnArgs[label] = { args, cwd: opts.cwd, tmp: opts.env?.TMP };
    return { status: status(label), stdout: "", stderr: "" };
  };
  const deps = { guard: g, fs: fsFake, spawnSync, env: { PATH: "x" }, nodePath: "node", nodeVersion: "v22.15.1" };
  return { deps, counts };
}

function attempt(name, deps, head = HEAD, cfg = config(ROOT)) {
  try { return { ok: true, value: launch(name, head, deps, ROOT, cfg) }; } catch (e) { return { ok: false, message: e.message }; }
}

// P1 positive.
{
  const { deps, counts } = fakes();
  const r = attempt("ctl-p1", deps);
  const run = path.join(ROOT, ".tmp", "claude-scratch", "i235", "ctl-p1");
  const bt = counts.spawnArgs.pytest?.args.find((a) => a.startsWith("--basetemp="));
  verdict(r.ok && counts.gates.join() === GATES.join() && counts.writes.length === GATES.length * 2 + 1
    && counts.mkdirs.length === 4 && bt === `--basetemp=${path.join(run, "basetemp")}`
    && counts.writes.every((w) => path.dirname(w) === run) && counts.spawnArgs.pytest.tmp === path.join(run, "tmp"),
    "P1 every gate in order, contained basetemp/TMP, every write counted inside the run dir", { r, counts });
}

// C1 bad run names.
for (const bad of ["", "..", "a/b", "C:x", "x\\y", "../x", "A", "-x"]) {
  const { deps, counts } = fakes();
  const r = attempt(bad, deps);
  verdict(!r.ok && /plain component/.test(r.message) && counts.mkdirs.length === 0 && counts.gates.length === 0
    && counts.writes.length === 0, `C1 bad run name ${JSON.stringify(bad)} refused`, { message: r.message, counts });
}

// C2 the run directory exists.
{
  const { deps, counts } = fakes({ existing: (abs) => abs.endsWith(`${path.sep}ctl-c2`) });
  const r = attempt("ctl-c2", deps);
  verdict(!r.ok && /run directory exists/.test(r.message) && counts.mkdirs.length === 0 && counts.gates.length === 0
    && counts.writes.length === 0, "C2 existing run directory refused", { message: r.message, counts });
}

// C3 basetemp exists when pytest is due.
{
  const { deps, counts } = fakes({ existing: (abs) => abs.endsWith(`${path.sep}ctl-c3${path.sep}basetemp`) });
  const r = attempt("ctl-c3", deps);
  verdict(!r.ok && /basetemp exists/.test(r.message) && !counts.gates.includes("pytest")
    && counts.gates.join() === GATES.slice(0, 6).join(), "C3 existing basetemp refused; pytest never spawned", { message: r.message, counts });
}

// C4 outward output entry: the first published file is a junction to the drive root.
{
  const runDir = path.join(ROOT, ".tmp", "claude-scratch", "i235", "ctl-c4");
  const sandbox = guard.makeSandbox(path.join(work, "c4"));
  fs.symlinkSync(process.platform === "win32" ? "C:\\" : "/", guard.assertEntry(sandbox, "preflight.log"), "junction");
  const { deps, counts } = fakes({ guardOverride: {
    makeSandbox: (dir) => { counts.mkdirs.push(dir); return path.resolve(dir); },
    assertOutput: (file) => guard.assertOutput(path.join(sandbox, path.relative(runDir, file))),
  } });
  const r = attempt("ctl-c4", deps);
  verdict(!r.ok && /fs-guard/.test(r.message) && counts.writes.length === 0 && counts.gates.length === 0,
    "C4 outward output entry refused at the first log open, nothing written, no gate started", { message: r.message, counts });
}

// C5 an input's ancestor cannot be inspected.
{
  const cfg = config(ROOT);
  const { deps, counts } = fakes({ guardOverride: {
    proveReferentAbs: (abs) => {
      if (path.resolve(abs) === path.resolve(cfg.icu.src)) throw new Error(`fs-guard: cannot inspect ${path.dirname(abs)} (EACCES); refused`);
      return guard.proveReferentAbs(abs);
    },
  } });
  const r = attempt("ctl-c5", deps, HEAD, cfg);
  verdict(!r.ok && /cannot inspect/.test(r.message) && counts.mkdirs.length === 0 && counts.gates.length === 0
    && counts.writes.length === 0, "C5 inspection failure refused before mkdir/gates/writes", { message: r.message, counts });
}

// C6 the memory preflight fails.
{
  const { deps, counts } = fakes({ status: (label) => (label === "preflight" ? 2 : 0) });
  const r = attempt("ctl-c6", deps);
  verdict(!r.ok && /preflight failed/.test(r.message) && counts.gates.join() === "preflight" && counts.writes.length === 2,
    "C6 failed preflight: its log/exit published, no gate started", { message: r.message, counts });
}

// C7 wrong HEAD / dirty tree.
for (const [label, opts] of [["head", { head: "0".repeat(40) }], ["dirty", { dirty: " M x.py\n" }]]) {
  const { deps, counts } = fakes(opts);
  const r = attempt("ctl-c7", deps);
  verdict(!r.ok && /(is not the expected|dirty)/.test(r.message) && counts.mkdirs.length === 0 && counts.gates.length === 0
    && counts.writes.length === 0, `C7 ${label} refused before mkdir`, { message: r.message, counts });
}

// C8 an unexpected ICU env line.
{
  const { deps, counts } = fakes({ icuEnv: "export MINION_AGENT_ICU_BIN='E:\\x'\nrm -rf /\n" });
  const r = attempt("ctl-c8", deps);
  verdict(!r.ok && /unexpected ICU env line/.test(r.message) && counts.mkdirs.length === 0 && counts.writes.length === 0,
    "C8 unexpected ICU env line refused before mkdir", { message: r.message, counts });
}

// C9: across EVERY intercepted launch above (git, ICU env, preflight and every gate), none was configured for
// automatic termination; reintroducing a timeout, killSignal or bounded maxBuffer fails this control.
verdict(KILLABLE.length === 0, "C9 no launch is configured for automatic termination", { KILLABLE });

console.log(failed ? `${failed} FAILED` : "ALL PASS");
process.exit(failed ? 1 : 0);
