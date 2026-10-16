// L12-D012 generation launcher. Sequential: the missing-precondition refusal controls, the Windows half natively, the
// Linux half in ONE read-only container, then the merge into the code worktree's canonical file. Containment through
// the reviewed fs-guard only, immediately before each operation: the run directory and its two child cwds
// (io.makeRun), every Docker bind source (proveReferentAbs), every written file (io.writeOutput). The generator itself
// writes nothing (stdout only). Nothing is deleted.
//   node run-gen.mjs <run name> <code worktree name>
import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { makeRun, writeOutput } from "./io.mjs";

const here = path.dirname(fileURLToPath(import.meta.url));
const guard = await import(pathToFileURL(path.join(here, "../../l12-d007/fs-guard/fs-guard.mjs")).href);
const ROOT = guard.PROJECT_ROOT;
const [runName, codeName] = process.argv.slice(2);
if (!/^[A-Za-z0-9][A-Za-z0-9._-]{0,60}$/.test(codeName ?? "") || codeName.includes("..")) throw new Error("code worktree name must be one plain component");

const run = makeRun(guard, path.join(ROOT, ".tmp", "claude-scratch", "i229"), runName);
const code = guard.proveReferentAbs(path.join(ROOT, "review-worktrees", codeName));
const pi = guard.proveReferentAbs(path.join(ROOT, "ref-repos", "pi"));
const gen = path.join(here, "gen_path_resolution.mjs");
const cwdA = path.join(run, "cwd-a"), cwdB = path.join(run, "cwd-b");
const base = Object.fromEntries(Object.entries(process.env).filter(([k]) => !k.startsWith("=")));
const capture = (what, cmd, args, opts = {}) => {
  const r = spawnSync(cmd, args, { encoding: "utf8", maxBuffer: 64 << 20, ...opts });
  if (r.status !== 0) throw new Error(`${what} failed (${r.status ?? r.error}): ${r.stderr}`);
  return r.stdout;
};

// Missing-precondition controls: an inherited =A: / =X: entry must make the generator REFUSE (exit 3), writing nothing.
const controls = [];
for (const d of ["A", "X"]) {
  const r = spawnSync(process.execPath, ["--no-warnings", gen, "generate", pi, cwdA, cwdB],
    { env: { ...base, [`=${d}:`]: `${d}:\\deep` }, cwd: ROOT, encoding: "utf8" });
  const ok = r.status === 3 && r.stderr.includes(`PRECONDITION REFUSED: inherited =${d}: entry is present`) && r.stdout === "";
  controls.push({ control: `inherited =${d}: entry`, exit: r.status, stderr: r.stderr.trim(), refused: ok });
  if (!ok) throw new Error(`precondition control for =${d}: did not refuse: ${JSON.stringify(controls.at(-1))}`);
}
writeOutput(guard, path.join(run, "precondition-controls.json"), JSON.stringify(controls, null, 1) + "\n");

const win = capture("windows generation", process.execPath, ["--no-warnings", gen, "generate", pi, cwdA, cwdB], { env: base, cwd: ROOT });
writeOutput(guard, path.join(run, "win32-partial.json"), win);

const bind = (src, dst) => ["--mount", `type=bind,source=${guard.proveReferentAbs(src).replaceAll("\\", "/")},target=${dst},readonly`];
const lin = capture("linux generation", "docker", ["run", "--rm", "--read-only", "--tmpfs", "/tmp:exec,size=256m", "-w", "/tmp",
  ...bind(pi, "/pi"), ...bind(here, "/gen"),
  "node:22.15.1-bookworm-slim", "node", "--no-warnings", "/gen/gen_path_resolution.mjs", "generate", "/pi", "/tmp", "/tmp"]);
writeOutput(guard, path.join(run, "linux-partial.json"), lin);

const out = capture("merge", process.execPath, ["--no-warnings", path.join(here, "merge_path_resolution.mjs"),
  path.join(run, "win32-partial.json"), path.join(run, "linux-partial.json")]);
writeOutput(guard, path.join(code, "conformance", "agent", "path-resolution", "path-resolution.json"), out);
console.log(`generated: ${JSON.parse(out).path_resolution.cases.length} cases; controls ${controls.map((c) => c.refused).join(",")}`);
