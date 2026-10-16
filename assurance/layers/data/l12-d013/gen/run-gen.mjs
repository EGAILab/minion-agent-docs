// L12-D013 generation launcher. Sequential: the Windows partial natively, the Linux partial in ONE read-only
// container, then the merge into the code worktree's canonical file. Containment through the reviewed fs-guard only,
// immediately before each operation: the run directory and its two child cwds (io.makeRun), every Docker bind
// source (proveReferentAbs), every written file (io.writeOutput). The generator itself writes nothing (stdout
// only). Nothing is deleted. The extended child cwd is a read-only SPELLING of an ordinary contained directory.
//   node run-gen.mjs <run name> <code worktree name>
import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const guard = await import(pathToFileURL(path.join(here, "../../l12-d007/fs-guard/fs-guard.mjs")).href);
const { makeRun, writeOutput } = await import(pathToFileURL(path.join(here, "../../l12-d012/gen/io.mjs")).href);
const ROOT = guard.PROJECT_ROOT;
const [runName, codeName] = process.argv.slice(2);
if (!/^[A-Za-z0-9][A-Za-z0-9._-]{0,60}$/.test(codeName ?? "") || codeName.includes("..")) throw new Error("code worktree name must be one plain component");

const code = guard.proveReferentAbs(path.join(ROOT, "review-worktrees", codeName));
const pi = guard.proveReferentAbs(path.join(ROOT, "ref-repos", "pi"));
const gen = path.join(here, "gen_rooted.mjs");
const base = Object.fromEntries(Object.entries(process.env).filter(([k]) => !k.startsWith("=")));
const capture = (what, cmd, args, opts = {}) => {
  const r = spawnSync(cmd, args, { encoding: "utf8", maxBuffer: 64 << 20, ...opts });
  if (r.status !== 0) throw new Error(`${what} failed (${r.status ?? r.error}): ${r.stderr}`);
  return r.stdout;
};

// No-write preflights, ALL before the first mutation (makeRun). Any mismatch REFUSES with nothing written.
const PI_COMMIT = "b7bb00b936dbe21b8e160b3e89efdec361846699";
const PI_FILE = "packages/agent/src/harness/env/nodejs.ts";
const NODE_IMAGE = "node:22.15.1-bookworm-slim";
const NODE_IMAGE_ID = "sha256:ec318fe0dc46b56bcc1ca42a202738aeb4f3e347a7b4dd9f9f1df12ea7aa385a";
const refuse = (why) => { console.error(`PREFLIGHT REFUSED: ${why}`); process.exit(3); };
if (process.version !== "v22.15.1") refuse(`host Node is ${process.version}, not v22.15.1`);
const pinnedBlob = capture("pinned blob", "git", ["-C", pi, "rev-parse", `${PI_COMMIT}:${PI_FILE}`]).trim();
const actualBlob = capture("working blob", "git", ["-C", pi, "hash-object", "--no-filters", PI_FILE]).trim();
if (!/^[0-9a-f]{40}$/.test(pinnedBlob) || pinnedBlob !== actualBlob) {
  refuse(`ref-repos/pi ${PI_FILE} blob ${actualBlob} is not the pinned ${PI_COMMIT}:${PI_FILE} blob ${pinnedBlob}`);
}
// The image must already be provisioned (inspect only; never pulled or installed here).
const imageId = capture("image inspect", "docker", ["image", "inspect", NODE_IMAGE, "--format", "{{.Id}}"]).trim();
if (imageId !== NODE_IMAGE_ID) refuse(`${NODE_IMAGE} is ${imageId}, not the provisioned ${NODE_IMAGE_ID}`);
const containerNode = capture("container node version", "docker", ["run", "--rm", "--read-only", "--network", "none",
  "--pull", "never", NODE_IMAGE_ID, "node", "--version"]).trim();
if (containerNode !== "v22.15.1") refuse(`container Node is ${containerNode}, not v22.15.1`);

const run = makeRun(guard, path.join(ROOT, ".tmp", "claude-scratch", "i235"), runName);
const cwdA = path.join(run, "cwd-a"), cwdB = path.join(run, "cwd-b");

const win = capture("windows generation", process.execPath, ["--no-warnings", gen, "generate", pi, cwdA, cwdB], { env: base, cwd: ROOT });
writeOutput(guard, path.join(run, "win32-partial.json"), win);

const bind = (src, dst) => ["--mount", `type=bind,source=${guard.proveReferentAbs(src).replaceAll("\\", "/")},target=${dst},readonly`];
const lin = capture("linux generation", "docker", ["run", "--rm", "--read-only", "--network", "none", "--pull", "never",
  "--tmpfs", "/tmp:exec,size=256m", "-w", "/tmp", ...bind(pi, "/pi"), ...bind(here, "/gen"),
  NODE_IMAGE_ID, "node", "--no-warnings", "/gen/gen_rooted.mjs", "generate", "/pi", "/tmp", "/tmp"]);
writeOutput(guard, path.join(run, "linux-partial.json"), lin);

const corpus = path.join(code, "conformance", "agent", "path-resolution", "path-resolution.json");
const out = capture("merge", process.execPath, ["--no-warnings", path.join(here, "merge_rooted.mjs"), corpus,
  path.join(run, "win32-partial.json"), path.join(run, "linux-partial.json")]);
writeOutput(guard, corpus, out);
console.log(`generated: ${JSON.parse(out).path_resolution.cases.length} cases`);
