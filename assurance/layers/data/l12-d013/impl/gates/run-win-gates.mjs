// #235 L12-D013 Python implementation: full WINDOWS Python gates (replaces i235/win-gates.sh after Codex's
// 2026-10-16 paper check). Containment through the reviewed fs-guard (l12-d007, sha256 9f9d933b...) ONLY:
//   - the run name is one plain component, and its run directory must NOT exist; makeSandbox proves the ancestry
//     before each mkdir (the run directory and its tmp/, pycache/ and mypy-cache/ subdirectories);
//   - every input path (code worktree, venv tools, ICU, search artifacts, preflight script, ICU env script) is
//     proven inside the root through every ancestor and link, existing and of the expected kind, before mkdir;
//   - the candidate HEAD must equal the expected sha and the tree must be clean, else REFUSE before mkdir;
//   - the memory preflight must exit 0, else REFUSE before any gate runs (its log is still published);
//   - pytest's --basetemp (which pytest may remove) is run/basetemp, proven inside the root and proven MISSING
//     immediately before pytest starts; every tool cache, coverage file and TMP/TEMP/TMPDIR is inside the run dir;
//   - every log and exit file is written by assertOutput immediately before its write (a log is opened "wx" and
//     receives the gate's output directly); nothing is redirected by a shell, nothing is deleted, every gate's exit
//     code is recorded as-is;
//   - nothing is ever terminated automatically: no spawn timeout, and no bounded capture (see NO_KILL).
//   node run-win-gates.mjs <run name> <expected 40-hex code HEAD>
import fsReal from "node:fs";
import path from "node:path";
import { spawnSync as spawnReal } from "node:child_process";
import { fileURLToPath, pathToFileURL } from "node:url";

export const GUARD_PATH = "E:/AI/Projects/OpenMinds/Minions/Minion-Agent/review-worktrees/sync2-d012-docs/assurance/layers/data/l12-d007/fs-guard/fs-guard.mjs";
export const RUN_NAME = /^[a-z0-9][a-z0-9-]{0,40}$/;
const SHA = /^[0-9a-f]{40}$/;
const NODE_VERSION = "v22.15.1";

export function config(root) {
  const p = (...parts) => path.join(root, ...parts);
  const venv = p("review-worktrees", "ri001-code", "minion-agent-python", ".venv", "Scripts");
  return {
    code: { src: p("review-worktrees", "d013-code"), kind: "dir" },
    py: { src: p("review-worktrees", "d013-code", "minion-agent-python"), kind: "dir" },
    python: { src: path.join(venv, "python.exe"), kind: "file" },
    ruff: { src: path.join(venv, "ruff.exe"), kind: "file" },
    icuEnv: { src: p("review-worktrees", "ri001-code", "minion-agent-python", "scripts", "pinned-icu", "build.sh"), kind: "file" },
    icu: { src: p(".toolchain", "icu-78.3-src"), kind: "dir" },
    artifacts: { src: p(".toolchain", "search-engines", "dl"), kind: "dir" },
    preflight: { src: p(".agents", "gate-preflight.ps1"), kind: "file" },
    scratch: p(".tmp", "claude-scratch", "i235"),
  };
}

// Proven NOW: inside the root through every ancestor and link, existing, of the expected kind, not itself a link.
export function proveInput(deps, input) {
  const abs = deps.guard.proveReferentAbs(input.src);
  const st = deps.fs.lstatSync(abs); // throws on any inspection failure, including ENOENT
  if (st.isSymbolicLink() || (input.kind === "dir" ? !st.isDirectory() : !st.isFile())) {
    throw new Error(`input ${abs} is not a plain ${input.kind}`);
  }
  return abs;
}

function missing(deps, abs) {
  try { deps.fs.lstatSync(abs); } catch (e) { if (e?.code === "ENOENT") return true; throw e; }
  return false;
}

function write(deps, file, data) {
  deps.fs.writeFileSync(deps.guard.assertOutput(file), data); // proven immediately before the write
}

// No automatic termination anywhere (Owner never-kill rule): no spawn has a timeout, and a captured stream is
// unbounded (maxBuffer Infinity), so neither a deadline nor a buffer overflow can signal a child. A gate's own
// output goes straight to its guarded log file descriptor, never through a buffer. A long gate is reported and an
// extension requested at a safe boundary instead.
export const NO_KILL = Object.freeze({ maxBuffer: Infinity });

function capture(deps, what, cmd, args, opts = {}) {
  const r = deps.spawnSync(cmd, args, { encoding: "utf8", ...opts, ...NO_KILL });
  if (r.error) throw new Error(`${what}: ${r.error.message}`);
  if (r.status !== 0) throw new Error(`${what} exited ${r.status}: ${String(r.stderr).slice(-400)}`);
  return r.stdout;
}

// `build.sh --env` prints only `export NAME='value'` lines (plus comments); anything else REFUSES.
export function parseIcuEnv(text) {
  const env = {};
  for (const raw of text.split(/\r?\n/)) {
    const line = raw.replace(/\s+#.*$/, "").trim();
    if (line === "" || line.startsWith("#")) continue;
    const m = /^export ([A-Z_][A-Z0-9_]*)=(?:'([^']*)'|([^\s'"]*))$/.exec(line);
    if (!m) throw new Error(`unexpected ICU env line: ${raw}`);
    env[m[1]] = m[2] ?? m[3];
  }
  if (!env.MINION_AGENT_ICU_BIN) throw new Error("ICU env has no MINION_AGENT_ICU_BIN");
  return env;
}

export function launch(name, expectHead, deps, root, cfg = config(root)) {
  if (typeof name !== "string" || !RUN_NAME.test(name)) throw new Error(`run name must be one plain component: ${name}`);
  if (typeof expectHead !== "string" || !SHA.test(expectHead)) throw new Error(`expected HEAD must be 40 hex: ${expectHead}`);
  // No-write preflights: input proofs, candidate identity, ICU env. Nothing has been created yet.
  const abs = {};
  for (const [k, v] of Object.entries(cfg)) if (k !== "scratch") abs[k] = proveInput(deps, v);
  const head = capture(deps, "git rev-parse", "git", ["-C", abs.code, "rev-parse", "HEAD"]).trim();
  if (head !== expectHead) throw new Error(`candidate HEAD ${head} is not the expected ${expectHead}`);
  const dirty = capture(deps, "git status", "git", ["-C", abs.code, "status", "--porcelain"]);
  if (dirty.trim() !== "") throw new Error(`candidate worktree is dirty: ${dirty.slice(0, 200)}`);
  const changed = capture(deps, "git diff", "git", ["-C", abs.code, "diff", "--name-only", "origin/main...HEAD", "--", "minion-agent-python"])
    .split(/\r?\n/).filter((f) => f.endsWith(".py")).map((f) => f.replace(/^minion-agent-python\//, ""));
  for (const f of changed) if (!/^(src|tests)\/[A-Za-z0-9_./-]+\.py$/.test(f) || f.split("/").includes("..")) throw new Error(`bad changed path ${f}`);
  const icuEnv = parseIcuEnv(capture(deps, "ICU env", "bash", [abs.icuEnv, abs.icu, "--env"], { cwd: abs.py }));
  if (deps.nodeVersion !== NODE_VERSION) throw new Error(`host Node is ${deps.nodeVersion}, not ${NODE_VERSION}`);

  const run = path.join(cfg.scratch, name);
  if (!missing(deps, run)) throw new Error(`run directory exists: ${run}`);
  deps.guard.makeSandbox(run);
  const tmp = deps.guard.makeSandbox(path.join(run, "tmp"));
  const pycache = deps.guard.makeSandbox(path.join(run, "pycache"));
  const mypyCache = deps.guard.makeSandbox(path.join(run, "mypy-cache"));
  const coverageFile = deps.guard.assertOutput(path.join(run, "coverage.data"));
  const env = {
    ...deps.env, ...icuEnv,
    TMP: tmp, TEMP: tmp, TMPDIR: tmp, PYTHONPYCACHEPREFIX: pycache, COVERAGE_FILE: coverageFile,
    MINION_SEARCH_ENGINE_ARTIFACTS: abs.artifacts, PYTHONPATH: "src;.", PIP_NO_INDEX: "1",
    PATH: `C:\\Program Files\\Git\\usr\\bin;${deps.env.PATH ?? deps.env.Path ?? ""}`,
  };
  delete env.Path;
  const results = [];
  const gate = (label, cmd, args) => {
    // The log is opened exclusively ("wx": a fresh file, never an existing one) right after its guard proof, and
    // receives the gate's stdout and stderr directly.
    const fd = deps.fs.openSync(deps.guard.assertOutput(path.join(run, `${label}.log`)), "wx");
    let r;
    try {
      r = deps.spawnSync(cmd, args, { cwd: abs.py, env, stdio: ["ignore", fd, fd], ...NO_KILL });
    } finally {
      deps.fs.closeSync(fd);
    }
    const exit = r.error ? `spawn-error ${r.error.message}` : String(r.status);
    write(deps, path.join(run, `${label}.exit`), exit + "\n");
    results.push({ label, exit });
    return exit;
  };

  if (gate("preflight", "powershell", ["-NoProfile", "-File", abs.preflight]) !== "0") {
    throw new Error("memory preflight failed; refusing to start the gates");
  }
  gate("icu", abs.python, ["-c", "import os; os.add_dll_directory(os.environ['MINION_AGENT_ICU_BIN']); import icu; print('icu', icu.ICU_VERSION)"]);
  gate("ruff", abs.ruff, ["check", "--no-cache", "src", "tests"]);
  gate("format-changed", abs.ruff, ["format", "--check", "--no-cache", ...changed]);
  gate("format-tree", abs.ruff, ["format", "--check", "--no-cache", "src", "tests"]); // informational
  gate("mypy", abs.python, ["-m", "mypy", "--cache-dir", mypyCache, "src"]);
  const basetemp = deps.guard.proveReferentAbs(path.join(run, "basetemp"));
  if (!missing(deps, basetemp)) throw new Error(`basetemp exists: ${basetemp}; refusing to hand it to pytest`);
  gate("pytest", abs.python, ["-m", "pytest", "-p", "no:cacheprovider", `--basetemp=${basetemp}`]);
  // L12-D013 M4, relative branch: pinned Node's own pure path.posix.resolve (no filesystem access).
  gate("node-posix", deps.nodePath, ["-p", "const p=require('path').posix; JSON.stringify([p.resolve('//x','a'), p.resolve('/x','//leaf'), p.resolve('//x','..')])"]);
  write(deps, path.join(run, "summary.json"), JSON.stringify({ head, changed, results }, null, 1) + "\n");
  return { run, head, results };
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const guard = await import(pathToFileURL(GUARD_PATH).href);
  const deps = { guard, fs: fsReal, spawnSync: spawnReal, env: process.env, nodePath: process.execPath, nodeVersion: process.version };
  console.log(JSON.stringify(launch(process.argv[2], process.argv[3], deps, guard.PROJECT_ROOT)));
}
