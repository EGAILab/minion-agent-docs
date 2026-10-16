// #235 CE-L12D013-01 read-domain launcher (for Codex's paper check). It runs the two stdout-only probes and then the
// comparator. Containment through the reviewed fs-guard (l12-d007, sha256 9f9d933b...) ONLY:
//   - the run name is one plain component, and its run directory (under i235/ce01) must NOT exist; makeSandbox
//     proves the ancestry before each mkdir (run/ and run/tmp/);
//   - every input (both probes, the comparator, the Python interpreter, the Pi checkout, the candidate src) is
//     proven a plain existing file or directory before mkdir; the code candidate must be the expected clean HEAD;
//   - every capture (<label>.out, .err, .exit) is opened "wx" right after its assertOutput proof and receives the
//     child's stream directly. There are no shell redirects, nothing is truncated or deleted, and no replaced entry
//     is followed;
//   - no automatic termination: no timeout, killSignal or bounded buffer (NO_KILL);
//   - the comparator runs only when both probes exited 0; otherwise the run is a SETUP FAILURE and stops.
//   node run-ce01.mjs <run name> <expected 40-hex code HEAD>
import fsReal from "node:fs";
import path from "node:path";
import { spawnSync as spawnReal } from "node:child_process";
import { fileURLToPath, pathToFileURL } from "node:url";

export const GUARD_PATH = "E:/AI/Projects/OpenMinds/Minions/Minion-Agent/review-worktrees/sync2-d012-docs/assurance/layers/data/l12-d007/fs-guard/fs-guard.mjs";
export const RUN_NAME = /^[a-z0-9][a-z0-9-]{0,40}$/;
export const NO_KILL = Object.freeze({ maxBuffer: Infinity });
const SHA = /^[0-9a-f]{40}$/;

export function config(root) {
  const p = (...parts) => path.join(root, ...parts);
  const here = p(".tmp", "claude-scratch", "i235", "ce01");
  return {
    here,
    inputs: {
      nodeProbe: { src: path.join(here, "read_domain_node.mjs"), kind: "file" },
      pyProbe: { src: path.join(here, "read_domain_python.py"), kind: "file" },
      compare: { src: path.join(here, "compare_read_domain.py"), kind: "file" },
      python: { src: p("review-worktrees", "ri001-code", "minion-agent-python", ".venv", "Scripts", "python.exe"), kind: "file" },
      pi: { src: p("ref-repos", "pi"), kind: "dir" },
      code: { src: p("review-worktrees", "d013-code"), kind: "dir" },
      src: { src: p("review-worktrees", "d013-code", "minion-agent-python", "src"), kind: "dir" },
    },
  };
}

function prove(deps, input) {
  const abs = deps.guard.proveReferentAbs(input.src);
  const st = deps.fs.lstatSync(abs); // throws on any inspection failure, including ENOENT
  if (st.isSymbolicLink() || (input.kind === "dir" ? !st.isDirectory() : !st.isFile())) {
    throw new Error(`input ${abs} is not a plain ${input.kind}`);
  }
  return abs;
}

function capture(deps, what, cmd, args) {
  const r = deps.spawnSync(cmd, args, { encoding: "utf8", ...NO_KILL });
  if (r.error) throw new Error(`${what}: ${r.error.message}`);
  if (r.status !== 0) throw new Error(`${what} exited ${r.status}: ${String(r.stderr).slice(-400)}`);
  return r.stdout;
}

export function launch(name, expectHead, deps, root, cfg = config(root)) {
  if (typeof name !== "string" || !RUN_NAME.test(name)) throw new Error(`run name must be one plain component: ${name}`);
  if (typeof expectHead !== "string" || !SHA.test(expectHead)) throw new Error(`expected HEAD must be 40 hex: ${expectHead}`);
  if (deps.nodeVersion !== "v22.15.1") throw new Error(`host Node is ${deps.nodeVersion}, not v22.15.1`);
  const abs = Object.fromEntries(Object.entries(cfg.inputs).map(([k, v]) => [k, prove(deps, v)]));
  const head = capture(deps, "git rev-parse", "git", ["-C", abs.code, "rev-parse", "HEAD"]).trim();
  if (head !== expectHead) throw new Error(`candidate HEAD ${head} is not the expected ${expectHead}`);
  if (capture(deps, "git status", "git", ["-C", abs.code, "status", "--porcelain"]).trim() !== "") throw new Error("candidate worktree is dirty");

  const run = path.join(cfg.here, name);
  let exists = true;
  try { deps.fs.lstatSync(run); } catch (e) { if (e?.code === "ENOENT") exists = false; else throw e; }
  if (exists) throw new Error(`run directory exists: ${run}`);
  deps.guard.makeSandbox(run);
  const tmp = deps.guard.makeSandbox(path.join(run, "tmp"));
  const env = { ...deps.env, TMP: tmp, TEMP: tmp, TMPDIR: tmp, PYTHONDONTWRITEBYTECODE: "1" };

  const child = (label, cmd, args) => {
    const out = deps.fs.openSync(deps.guard.assertOutput(path.join(run, `${label}.out`)), "wx");
    let err;
    let r;
    try {
      err = deps.fs.openSync(deps.guard.assertOutput(path.join(run, `${label}.err`)), "wx");
      r = deps.spawnSync(cmd, args, { env, stdio: ["ignore", out, err], ...NO_KILL });
    } finally {
      deps.fs.closeSync(out);
      if (err !== undefined) deps.fs.closeSync(err);
    }
    const exit = r.error ? `spawn-error ${r.error.message}` : String(r.status);
    deps.fs.writeFileSync(deps.guard.assertOutput(path.join(run, `${label}.exit`)), exit + "\n", { flag: "wx" });
    return exit;
  };

  const nodeExit = child("node", deps.nodePath, ["--no-warnings", abs.nodeProbe, abs.pi]);
  const pyExit = child("python", abs.python, ["-I", "-B", abs.pyProbe, abs.src]);
  if (nodeExit !== "0" || pyExit !== "0") {
    return { run, head, setupFailure: true, nodeExit, pyExit };
  }
  const compareExit = child("compare", abs.python, ["-I", "-B", abs.compare,
    deps.guard.assertOutput(path.join(run, "node.out")), deps.guard.assertOutput(path.join(run, "python.out"))]);
  return { run, head, setupFailure: compareExit !== "0", nodeExit, pyExit, compareExit };
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const guard = await import(pathToFileURL(GUARD_PATH).href);
  const deps = { guard, fs: fsReal, spawnSync: spawnReal, env: process.env, nodePath: process.execPath, nodeVersion: process.version };
  console.log(JSON.stringify(launch(process.argv[2], process.argv[3], deps, guard.PROJECT_ROOT)));
}
