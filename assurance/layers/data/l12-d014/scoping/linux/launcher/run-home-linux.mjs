// #236 L12-D014 POSIX characterization launcher (replaces run-home-linux.ps1 after Codex's paper check).
// Two containers, strictly sequential; container A failing stops the run before B.
//   A: rust:1.97.1-trixie (pinned id), --network none: pinned Node + the Linux Rust observer built at 666e7365.
//   B: python:3.13 (pinned id): pinned Node + merged Python; one pip install of ada-url into the private /tmp.
// Containment through the reviewed fs-guard (l12-d007, sha256 9f9d933b...) ONLY, immediately before each mutation
// or mount: makeSandbox for the NEW run directory (ancestry proven before its mkdir); proveReferentAbs + an
// existence/kind check for EVERY bind source, re-proven immediately before EACH docker invocation; assertOutput for
// EVERY written file (stdout, stderr and exit captures), immediately before its write. Nothing is redirected by a
// shell and nothing is deleted. Inspection failures throw. The probe itself writes nothing (stdout only).
//   node run-home-linux.mjs <run name>
import fsReal from "node:fs";
import path from "node:path";
import { spawnSync as spawnReal } from "node:child_process";
import { fileURLToPath, pathToFileURL } from "node:url";

export const GUARD_PATH = "E:/AI/Projects/OpenMinds/Minions/Minion-Agent/review-worktrees/sync2-d012-docs/assurance/layers/data/l12-d007/fs-guard/fs-guard.mjs";
export const RUST_IMAGE = "sha256:b1b3c9c0d921d7fa0a6d1f9ec7e4eab87f8c8ec97644c3d791450f131dec813f";
export const PY_IMAGE = "sha256:5b6557f37abf12bfc64315bba192b342aec6dbf367aed30b7db51082aec73a1e";
const PI_COMMIT = "b7bb00b936dbe21b8e160b3e89efdec361846699";
const PI_FILE = "packages/agent/src/harness/env/nodejs.ts";
const RUN_NAME = /^[a-z0-9][a-z0-9-]{0,40}$/;

export function sources(root) {
  const p = (...parts) => path.join(root, ...parts);
  return {
    pi: { src: p("ref-repos", "pi"), kind: "dir", target: "/pi", rw: false },
    // The Linux node binary itself, bound as a file at /node (the reviewed L12-D012 launcher pattern).
    node: { src: p(".tmp", "cache", "node-22.15.1-linux", "node"), kind: "file", target: "/node", rw: false },
    icu: { src: p(".toolchain", "icu-78.3-linux"), kind: "dir", target: "/build", rw: false },
    observer: { src: p(".tmp", "claude-linux-target", "debug", "deps", "minion_agent-30f01ba75be520f5"), kind: "file", target: "/observer", rw: false },
    probe: { src: p(".tmp", "claude-scratch", "i236", "linux-launcher", "home_probe_linux.py"), kind: "file", target: "/probe.py", rw: false },
    pysrc: { src: p("review-worktrees", "claude-d011-py", "minion-agent-python", "src"), kind: "dir", target: "/src", rw: false },
    pipcache: { src: p(".tmp", "pip-cache"), kind: "dir", target: "/pipcache", rw: true },
  };
}

// Proven NOW: inside the root through every ancestor and link, existing, of the expected kind, not itself a link.
function proveBind(deps, b) {
  const abs = deps.guard.proveReferentAbs(b.src);
  const st = deps.fs.lstatSync(abs); // throws on any inspection failure, including ENOENT: a bind must exist
  if (st.isSymbolicLink() || (b.kind === "dir" ? !st.isDirectory() : !st.isFile())) {
    throw new Error(`bind source ${abs} is not a plain ${b.kind}`);
  }
  return ["--mount", `type=bind,source=${abs.replaceAll("\\", "/")},target=${b.target}${b.rw ? "" : ",readonly"}`];
}

function write(deps, file, data) {
  deps.fs.writeFileSync(deps.guard.assertOutput(file), data); // proven immediately before the write
}

function capture(deps, what, cmd, args) {
  const r = deps.spawnSync(cmd, args, { encoding: "utf8", maxBuffer: 256 << 20 });
  if (r.error) throw new Error(`${what}: ${r.error.message}`);
  if (r.status !== 0) throw new Error(`${what} exited ${r.status}: ${String(r.stderr).slice(-400)}`);
  return r.stdout;
}

export function launch(name, deps, root, binds = sources(root)) {
  if (typeof name !== "string" || !RUN_NAME.test(name)) throw new Error(`run name must be one plain component: ${name}`);
  // No-write preflights. Command failures throw; mismatches throw. Nothing has been created yet.
  for (const b of Object.values(binds)) proveBind(deps, b);
  const pinned = capture(deps, "pinned blob", "git", ["-C", binds.pi.src, "rev-parse", `${PI_COMMIT}:${PI_FILE}`]).trim();
  const actual = capture(deps, "working blob", "git", ["-C", binds.pi.src, "hash-object", "--no-filters", PI_FILE]).trim();
  if (!/^[0-9a-f]{40}$/.test(pinned) || pinned !== actual) throw new Error(`nodejs.ts blob ${actual} is not pinned ${pinned}`);
  for (const id of [RUST_IMAGE, PY_IMAGE]) {
    if (capture(deps, "image inspect", "docker", ["image", "inspect", id, "--format", "{{.Id}}"]).trim() !== id) {
      throw new Error(`image ${id} is not provisioned`);
    }
  }
  const scratch = path.join(root, ".tmp", "claude-scratch", "i236");
  const run = path.join(scratch, name);
  let exists = true;
  try { deps.fs.lstatSync(run); } catch (e) { if (e?.code === "ENOENT") exists = false; else throw e; }
  if (exists) throw new Error(`run directory exists: ${run}`);
  deps.guard.makeSandbox(run); // REFERENT proof of the ancestry, then mkdir

  const containers = [
    { tag: "a-rust", image: RUST_IMAGE, network: ["--network", "none"], uses: ["pi", "node", "icu", "observer", "probe"],
      env: ["-e", "LD_LIBRARY_PATH=/build/icu/lib", "-e", "TMPDIR=/tmp"],
      // As the reviewed L12-D012 gates do: the bound node binary is copied into the private tmpfs and made
      // executable there (also readable/executable for the uid-1000 children).
      cmd: ["sh", "-c", "cp /node /tmp/node && chmod 755 /tmp/node && "
        + "python3 -B /probe.py --node /tmp/node --pi /pi --rust /observer"] },
    { tag: "b-python", image: PY_IMAGE, network: [], uses: ["pi", "node", "pysrc", "probe", "pipcache"],
      env: ["-e", "TMPDIR=/tmp", "-e", "PIP_CACHE_DIR=/pipcache", "-e", "PYTHONPATH=/tmp/site"],
      // The third-party import closure of minion_agent.execution.filesystem (measured: ada_url, pydantic and their
      // dependencies), pinned to the reference venv's versions. Setup is verified before the probe: an import
      // failure exits 9 and the probe never starts.
      cmd: ["sh", "-c", "pip install -q --root-user-action=ignore --target /tmp/site ada-url==1.15.3 cffi==2.1.1 "
        + "pycparser==3.0 pydantic==2.13.4 pydantic-core==2.46.4 typing-extensions==4.16.0 typing-inspection==0.4.4 "
        + "annotated-types==0.8.0 >/tmp/pip.log 2>&1 || { cat /tmp/pip.log >&2; exit 9; }; chmod -R a+rX /tmp/site; "
        + "PYTHONPATH=/tmp/site:/src python -B -c 'import minion_agent.execution.filesystem' || exit 9; "
        + "cp /node /tmp/node && chmod 755 /tmp/node && python -B /probe.py --node /tmp/node --pi /pi --pysrc /src"] },
  ];
  const results = [];
  for (const c of containers) {
    const mounts = c.uses.flatMap((k) => proveBind(deps, binds[k])); // re-proven immediately before THIS docker run
    const r = deps.spawnSync("docker", ["run", "--rm", "--read-only", "--pull", "never", ...c.network,
      "--tmpfs", "/tmp:exec,size=1g", ...mounts, ...c.env, c.image, ...c.cmd], { encoding: "utf8", maxBuffer: 256 << 20 });
    const exit = r.error ? `spawn-error ${r.error.message}` : String(r.status);
    write(deps, path.join(run, `${c.tag}.exit`), exit + "\n");
    write(deps, path.join(run, `${c.tag}.json`), r.stdout ?? "");
    write(deps, path.join(run, `${c.tag}.err`), r.stderr ?? "");
    results.push({ tag: c.tag, exit });
    if (exit !== "0") throw new Error(`container ${c.tag} failed (${exit}); stopping before any later container`);
  }
  return { run, results };
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const guard = await import(pathToFileURL(GUARD_PATH).href);
  const out = launch(process.argv[2], { guard, fs: fsReal, spawnSync: spawnReal }, guard.PROJECT_ROOT);
  console.log(JSON.stringify(out));
}
