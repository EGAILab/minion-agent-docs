// Refusal controls for run-linux-gates.mjs (for Codex's paper check). INTERCEPTED dependencies as in win-controls.mjs:
// every fs write and output open, sandbox creation, preflight and docker run is counted and NEVER reaches the OS (a
// fake docker's stdout is stored in memory under the opened capture's path and read back from there); only the
// reviewed fs-guard's real proofs run, plus this script's own contained setup (one control sandbox; C4's junction).
//   P1  all dependencies succeed: one docker run with ONLY readonly mounts; every bundle entry published under its fixed
//       name inside the run dir (3 preflight + 3 container captures + 12 entries + summary = 19 counted writes).
//   C1  bad run names -> refused, 0 mkdir, 0 docker runs, 0 writes.
//   C2  a foreign bind source (outside the root) -> refused before mkdir, 0 docker runs, 0 writes.
//   C3  an ancestor of a bind source cannot be inspected -> refused before mkdir, 0 docker runs, 0 writes.
//   C4  outward output entry: the first capture is a junction to the drive root -> refused, 0 writes, no container.
//   C5  the memory preflight fails -> its 3 captures published (counted), 0 docker runs.
//   C6  a bind proven at start fails its re-proof immediately before docker -> refused, 0 docker runs.
//   C7  malformed bundles -> refused; ONLY the 6 raw captures exist, no extracted entry is published. Paired cases keep
//       the ENTIRE valid bundle and add one defect: an appended traversal-label record, an appended wrong-nonce
//       record, prefix garbage, interstitial garbage, trailing garbage. Plus: extra label, duplicate, missing,
//       replaced traversal label, wrong nonce throughout.
//   C8  candidate HEAD differs or the tree is dirty -> refused before mkdir.
//   C9  every intercepted launch in every control has no timeout, no killSignal and an unbounded maxBuffer.
//   node linux-controls.mjs
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { GUARD_PATH, LABELS, config, launch, parseBundle } from "./run-linux-gates.mjs";

const guard = await import(pathToFileURL(GUARD_PATH).href);
const ROOT = guard.PROJECT_ROOT;
const HEAD = "8348102000000000000000000000000000000000"; // any 40-hex value: git is faked
const NONCE = "0123456789abcdef0123456789abcdef";
const work = guard.makeSandbox(path.join(ROOT, ".tmp", "claude-scratch", "i235", `linux-controls-${Date.now()}`));
let failed = 0;
const KILLABLE = [];
const verdict = (ok, label, detail) => { if (!ok) failed++; console.log(ok ? "PASS" : "FAIL", label, JSON.stringify(detail)); };
const record = (label, nonce = NONCE, exit = 0) => `@@BEGIN ${nonce} ${label} ${exit}@@\nlog of ${label}\n@@END ${nonce} ${label}@@\n`;
const bundle = (labels = LABELS, nonce = NONCE) => labels.map((l) => record(l, nonce)).join("");
const RAW = ["preflight.out", "preflight.err", "preflight.exit", "container.out", "container.err", "container.exit"];

function fakes({ head = HEAD, dirty = "", preflight = 0, stdout = bundle(), guardOverride = {} } = {}) {
  const counts = { writes: [], mkdirs: [], dockerRuns: 0, preflights: 0, mounts: [] };
  const g = {
    ...guard,
    makeSandbox: (dir) => { guard.proveReferentAbs(dir); counts.mkdirs.push(dir); return path.resolve(dir); },
    ...guardOverride,
  };
  const scratch = path.join(ROOT, ".tmp", "claude-scratch", "i235");
  const fds = new Map();
  const store = new Map();
  const fsFake = {
    lstatSync: (p) => {
      if (path.resolve(p).startsWith(path.join(scratch, "ctl-"))) {
        const e = new Error("ENOENT (control: not created)"); e.code = "ENOENT"; throw e;
      }
      return fs.lstatSync(p);
    },
    writeFileSync: (p) => { counts.writes.push(p); },
    openSync: (p, flags) => {
      if (flags !== "wx") throw new Error(`capture ${p} opened with ${flags}, not wx`);
      counts.writes.push(p);
      const fd = 2000 + fds.size;
      fds.set(fd, p);
      return fd;
    },
    closeSync: () => {},
    readFileSync: (p) => store.get(path.resolve(p)) ?? "",
  };
  const spawnSync = (cmd, args, opts = {}) => {
    if ("timeout" in opts || "killSignal" in opts || opts.maxBuffer !== Infinity) {
      KILLABLE.push({ cmd, timeout: opts.timeout, killSignal: opts.killSignal, maxBuffer: opts.maxBuffer });
    }
    if (cmd === "git" && args.includes("rev-parse")) return { status: 0, stdout: head + "\n", stderr: "" };
    if (cmd === "git" && args.includes("status")) return { status: 0, stdout: dirty, stderr: "" };
    if (cmd === "docker" && args[0] === "image") return { status: 0, stdout: args[2] + "\n", stderr: "" };
    if (cmd === "powershell") { counts.preflights++; return { status: preflight }; }
    if (cmd === "docker" && args[0] === "run") {
      counts.dockerRuns++;
      counts.mounts = args.filter((a) => a.startsWith("type=bind"));
      store.set(path.resolve(fds.get(opts.stdio[1])), stdout); // the container's stdout lands in its capture
      return { status: 0 };
    }
    throw new Error(`unexpected spawn ${cmd}`);
  };
  return { deps: { guard: g, fs: fsFake, spawnSync, nonce: () => NONCE }, counts };
}

function attempt(name, deps, cfg = config(ROOT), head = HEAD) {
  try { return { ok: true, value: launch(name, head, deps, ROOT, cfg) }; } catch (e) { return { ok: false, message: e.message }; }
}

// P1 positive.
{
  const { deps, counts } = fakes();
  const r = attempt("ctl-p1", deps);
  const run = path.join(ROOT, ".tmp", "claude-scratch", "i235", "ctl-p1");
  verdict(r.ok && counts.dockerRuns === 1 && counts.mounts.length === 5 && counts.mounts.every((m) => m.endsWith(",readonly"))
    && counts.writes.length === 19 && counts.writes.every((w) => path.dirname(w) === run) && counts.mkdirs.length === 1
    && r.value.results.map((x) => x.label).join() === LABELS.join(),
    "P1 one container, readonly mounts only, 19 counted writes inside the run dir", { r, counts });
}

// C1 bad run names.
for (const bad of ["", "..", "a/b", "C:x", "x\\y", "../x", "A", "-x"]) {
  const { deps, counts } = fakes();
  const r = attempt(bad, deps);
  verdict(!r.ok && /plain component/.test(r.message) && counts.mkdirs.length === 0 && counts.dockerRuns === 0
    && counts.writes.length === 0, `C1 bad run name ${JSON.stringify(bad)} refused`, { message: r.message });
}

// C2 foreign bind.
{
  const cfg = config(ROOT);
  cfg.binds = { ...cfg.binds, artifacts: { ...cfg.binds.artifacts, src: process.platform === "win32" ? "C:\\Windows" : "/usr" } };
  const { deps, counts } = fakes();
  const r = attempt("ctl-c2", deps, cfg);
  verdict(!r.ok && /fs-guard/.test(r.message) && counts.mkdirs.length === 0 && counts.dockerRuns === 0
    && counts.writes.length === 0, "C2 foreign bind refused before mkdir/docker/write", { message: r.message });
}

// C3 ancestor inspection failure.
{
  const cfg = config(ROOT);
  const { deps, counts } = fakes({ guardOverride: {
    proveReferentAbs: (abs) => {
      if (path.resolve(abs) === path.resolve(cfg.binds.icu.src)) throw new Error(`fs-guard: cannot inspect ${path.dirname(abs)} (EACCES); refused`);
      return guard.proveReferentAbs(abs);
    },
  } });
  const r = attempt("ctl-c3", deps, cfg);
  verdict(!r.ok && /cannot inspect/.test(r.message) && counts.mkdirs.length === 0 && counts.dockerRuns === 0
    && counts.writes.length === 0, "C3 inspection failure refused before mkdir/docker/write", { message: r.message });
}

// C4 outward output entry.
{
  const runDir = path.join(ROOT, ".tmp", "claude-scratch", "i235", "ctl-c4");
  const sandbox = guard.makeSandbox(path.join(work, "c4"));
  fs.symlinkSync(process.platform === "win32" ? "C:\\" : "/", guard.assertEntry(sandbox, "preflight.out"), "junction");
  const { deps, counts } = fakes({ guardOverride: {
    makeSandbox: (dir) => { counts.mkdirs.push(dir); return path.resolve(dir); },
    assertOutput: (file) => guard.assertOutput(path.join(sandbox, path.relative(runDir, file))),
  } });
  const r = attempt("ctl-c4", deps);
  verdict(!r.ok && /fs-guard/.test(r.message) && counts.writes.length === 0 && counts.preflights === 0 && counts.dockerRuns === 0,
    "C4 outward output entry refused at the first capture open, nothing written, nothing started", { message: r.message });
}

// C5 failed preflight.
{
  const { deps, counts } = fakes({ preflight: 2 });
  const r = attempt("ctl-c5", deps);
  verdict(!r.ok && /preflight failed/.test(r.message) && counts.preflights === 1 && counts.dockerRuns === 0
    && counts.writes.map((w) => path.basename(w)).join() === RAW.slice(0, 3).join(),
    "C5 failed preflight: its 3 captures published, no container", { message: r.message });
}

// C6 re-proof immediately before docker fails.
{
  const cfg = config(ROOT);
  let proofs = 0;
  const { deps, counts } = fakes({ guardOverride: {
    proveReferentAbs: (abs) => {
      if (path.resolve(abs) === path.resolve(cfg.binds.src.src) && ++proofs === 2) throw new Error("fs-guard: re-proof refused (control)");
      return guard.proveReferentAbs(abs);
    },
  } });
  const r = attempt("ctl-c6", deps, cfg);
  verdict(!r.ok && /re-proof refused/.test(r.message) && proofs === 2 && counts.dockerRuns === 0,
    "C6 failed re-proof immediately before docker refused, no container", { message: r.message });
}

// C7 malformed bundles: paired cases keep the ENTIRE valid bundle and add exactly one defect.
const VALID = bundle();
const BAD = {
  "valid+appended-traversal-record": VALID + record("../ruff"),
  "valid+appended-wrong-nonce-record": VALID + record("ruff", "f".repeat(32)),
  "prefix-garbage+valid": "garbage\n" + VALID,
  "interstitial-garbage": bundle(LABELS.slice(0, 3)) + "x\n" + bundle(LABELS.slice(3)),
  "valid+trailing-garbage": VALID + "\n",
  "extra-label": bundle([...LABELS, "evil"]),
  "duplicate": bundle([...LABELS.slice(0, 5), "pytest"]),
  "missing": bundle(LABELS.slice(0, 5)),
  "replaced-traversal": bundle(["icu-build", "pip", "versions", "pytest", "mypy", "../ruff"]),
  "wrong-nonce": bundle(LABELS, "f".repeat(32)),
  "empty": "",
};
verdict((() => { try { return parseBundle(VALID, NONCE).length === LABELS.length; } catch { return false; } })(),
  "C7 pair: the complete valid bundle alone parses", {});
for (const [label, stdout] of Object.entries(BAD)) {
  const { deps, counts } = fakes({ stdout });
  const r = attempt("ctl-c7", deps);
  const names = counts.writes.map((w) => path.basename(w));
  verdict(!r.ok && /^bundle: /.test(r.message) && names.join() === RAW.join(),
    `C7 ${label} refused; only the raw captures exist`, { message: r.message, names });
}

// C8 wrong HEAD / dirty tree.
for (const [label, opts] of [["head", { head: "0".repeat(40) }], ["dirty", { dirty: " M x.py\n" }]]) {
  const { deps, counts } = fakes(opts);
  const r = attempt("ctl-c8", deps);
  verdict(!r.ok && /(is not the expected|dirty)/.test(r.message) && counts.mkdirs.length === 0 && counts.dockerRuns === 0
    && counts.writes.length === 0, `C8 ${label} refused before mkdir`, { message: r.message });
}

// C9 across every intercepted launch above.
verdict(KILLABLE.length === 0, "C9 no launch is configured for automatic termination", { KILLABLE });

console.log(failed ? `${failed} FAILED` : "ALL PASS");
process.exit(failed ? 1 : 0);
