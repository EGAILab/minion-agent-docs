// L12-D011 generation launcher (replaces run-gen.ps1; L12D011-C001). Sequential: the Windows half natively, the Linux
// half in ONE private container, then the merge into the code worktree's canonical file. Containment, through the
// reviewed fs-guard only (CE-L12D007-01), immediately before each operation:
//   - the run directory and its cwd/: io.makeRun (one plain name component; REFERENT ancestry proof before mkdir);
//   - every Docker bind source: proveReferentAbs (read-only ones and the writable run directory);
//   - every output file (generator partials, the canonical file): io.writeOutput (assertOutput) inside the writer.
// A code worktree is named by one plain component under review-worktrees/. Nothing is deleted.
//   node run-gen.mjs <run name> <code worktree name>
import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { makeRun } from "./io.mjs";

const here = path.dirname(fileURLToPath(import.meta.url));
const guard = await import(pathToFileURL(path.join(here, "../../l12-d007/fs-guard/fs-guard.mjs")).href);
const ROOT = guard.PROJECT_ROOT;
const [runName, codeName] = process.argv.slice(2);
if (!/^[A-Za-z0-9][A-Za-z0-9._-]{0,60}$/.test(codeName ?? "") || codeName.includes("..")) throw new Error("code worktree name must be one plain component");

const run = makeRun(guard, path.join(ROOT, ".tmp", "claude-scratch", "i195"), runName);
const code = guard.proveReferentAbs(path.join(ROOT, "review-worktrees", codeName));
const pi = guard.proveReferentAbs(path.join(ROOT, "ref-repos", "pi"));
const engines = guard.proveReferentAbs(path.join(ROOT, ".tmp", "wp134-engines-05jabsn8"));
const step = (what, cmd, args) => {
  const r = spawnSync(cmd, args, { stdio: "inherit" });
  if (r.status !== 0) throw new Error(`${what} failed (${r.status ?? r.error})`);
};

step("windows generation", process.execPath, ["--experimental-strip-types", "--no-warnings", path.join(here, "gen_spawn_nul.mjs"),
  pi, path.join(engines, "fd.exe"), path.join(engines, "rg.exe"), run, path.join(run, "win32-partial.json")]);

const bind = (src, dst, ro) => ["--mount", `type=bind,source=${guard.proveReferentAbs(src).replaceAll("\\", "/")},target=${dst}${ro ? ",readonly" : ""}`];
step("linux generation", "docker", ["run", "--rm", "--read-only", "--tmpfs", "/tmp:exec,size=2g",
  ...bind(pi, "/pi", true),
  ...bind(path.join(ROOT, ".tmp", "cache", "node-22.15.1-linux", "node"), "/node", true),
  ...bind(path.join(ROOT, ".toolchain", "search-engines", "dl"), "/artifacts", true),
  ...bind(path.join(here, "..", ".."), "/data", true),
  ...bind(run, "/out", false),
  "python:3.13", "sh", "-c", "tr -d '\\r' < /data/l12-d011/gen/gen-linux.sh > /tmp/gen.sh && sh /tmp/gen.sh"]);

step("merge", process.execPath, [path.join(here, "merge_spawn_nul.mjs"), path.join(run, "win32-partial.json"),
  path.join(run, "linux-partial.json"), path.join(code, "conformance", "agent", "spawn-nul", "spawn-nul.json")]);
console.log(`GENERATION COMPLETE (run ${run})`);
