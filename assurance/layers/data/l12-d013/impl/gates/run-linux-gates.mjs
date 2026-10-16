// #235 L12-D013 Python implementation: full LINUX Python gates in python:3.13 (replaces run-py-linux-gates.ps1 after
// Codex's 2026-10-16 paper checks). There is NO writable host bind: every bind is read-only (the candidate tree, the
// ICU source tarball, the search artifacts, the PyICU sdist, the gate script). The container works only in its
// private tmpfs /tmp and prints one nonce-delimited bundle on stdout, which goes straight to the guarded raw capture
// container.out. The launcher then parses that capture COMPLETELY (every byte consumed; no gap, separator or trailing
// material) and only then publishes each entry under a FIXED name, each through the reviewed fs-guard's assertOutput
// immediately before its write. Containment otherwise as run-win-gates.mjs: plain new run name, inputs proven before
// mkdir and RE-PROVEN immediately before docker, expected clean HEAD, memory preflight must pass, nothing deleted,
// exits kept as-is, and nothing is ever terminated automatically (no timeout, no bounded capture: NO_KILL).
//   node run-linux-gates.mjs <run name> <expected 40-hex code HEAD>
import fsReal from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { spawnSync as spawnReal } from "node:child_process";
import { fileURLToPath, pathToFileURL } from "node:url";

export const GUARD_PATH = "E:/AI/Projects/OpenMinds/Minions/Minion-Agent/review-worktrees/sync2-d012-docs/assurance/layers/data/l12-d007/fs-guard/fs-guard.mjs";
export const PY_IMAGE = "sha256:5b6557f37abf12bfc64315bba192b342aec6dbf367aed30b7db51082aec73a1e";
export const RUN_NAME = /^[a-z0-9][a-z0-9-]{0,40}$/;
export const LABELS = ["icu-build", "pip", "versions", "pytest", "mypy", "ruff"];
export const NO_KILL = Object.freeze({ maxBuffer: Infinity });
const SHA = /^[0-9a-f]{40}$/;

export function config(root) {
  const p = (...parts) => path.join(root, ...parts);
  return {
    binds: {
      src: { src: p("review-worktrees", "d013-code"), kind: "dir", target: "/src" },
      icu: { src: p(".toolchain", "icu-78.3-src", "icu4c-78.3-sources.tgz"), kind: "file", target: "/icu-src/icu4c-78.3-sources.tgz" },
      artifacts: { src: p(".toolchain", "search-engines", "dl"), kind: "dir", target: "/artifacts" },
      pyicu: { src: p(".tmp", "pip-cache", "sdist", "pyicu-2.16.2.tar.gz"), kind: "file", target: "/sdist/pyicu-2.16.2.tar.gz" },
      script: { src: p(".tmp", "claude-scratch", "i235", "gates", "py-linux-gates.sh"), kind: "file", target: "/gates.sh" },
    },
    preflight: { src: p(".agents", "gate-preflight.ps1"), kind: "file" },
    scratch: p(".tmp", "claude-scratch", "i235"),
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

const mount = (abs, b) => ["--mount", `type=bind,source=${abs.replaceAll("\\", "/")},target=${b.target},readonly`];

function write(deps, file, data) {
  deps.fs.writeFileSync(deps.guard.assertOutput(file), data); // proven immediately before the write
}

// A fresh ("wx") guarded output file receiving a child's stream directly (no buffer, so nothing can overflow).
function openOutput(deps, file) {
  return deps.fs.openSync(deps.guard.assertOutput(file), "wx");
}

function capture(deps, what, cmd, args) {
  const r = deps.spawnSync(cmd, args, { encoding: "utf8", ...NO_KILL });
  if (r.error) throw new Error(`${what}: ${r.error.message}`);
  if (r.status !== 0) throw new Error(`${what} exited ${r.status}: ${String(r.stderr).slice(-400)}`);
  return r.stdout;
}

// The COMPLETE serialization, consumed sequentially: exactly the LABELS records, in order, each
//   "@@BEGIN <nonce> <label> <exit>@@\n" <log> "\n@@END <nonce> <label>@@\n"
// back to back, starting at byte 0 and ending at the last byte. Any other byte anywhere -- a prefix, material between
// records, an extra record of any label or nonce, trailing material -- REFUSES the whole bundle.
export function parseBundle(text, nonce) {
  if (!/^[0-9a-f]{32}$/.test(nonce)) throw new Error("bundle: bad nonce");
  const entries = [];
  let pos = 0;
  for (const label of LABELS) {
    const head = new RegExp(`@@BEGIN ${nonce} ${label} (-?\\d{1,9})@@\\n`, "y");
    head.lastIndex = pos;
    const m = head.exec(text);
    if (!m) throw new Error(`bundle: no ${label} record header at byte ${pos}`);
    const end = `\n@@END ${nonce} ${label}@@\n`;
    const stop = text.indexOf(end, head.lastIndex);
    if (stop < 0) throw new Error(`bundle: ${label} record is not terminated`);
    entries.push({ label, exit: m[1], log: text.slice(head.lastIndex, stop) });
    pos = stop + end.length;
  }
  if (pos !== text.length) throw new Error(`bundle: ${text.length - pos} trailing bytes after the last record`);
  return entries;
}

export function launch(name, expectHead, deps, root, cfg = config(root)) {
  if (typeof name !== "string" || !RUN_NAME.test(name)) throw new Error(`run name must be one plain component: ${name}`);
  if (typeof expectHead !== "string" || !SHA.test(expectHead)) throw new Error(`expected HEAD must be 40 hex: ${expectHead}`);
  const abs = Object.fromEntries(Object.entries(cfg.binds).map(([k, b]) => [k, prove(deps, b)]));
  const preflight = prove(deps, cfg.preflight);
  const head = capture(deps, "git rev-parse", "git", ["-C", abs.src, "rev-parse", "HEAD"]).trim();
  if (head !== expectHead) throw new Error(`candidate HEAD ${head} is not the expected ${expectHead}`);
  if (capture(deps, "git status", "git", ["-C", abs.src, "status", "--porcelain"]).trim() !== "") throw new Error("candidate worktree is dirty");
  if (capture(deps, "image inspect", "docker", ["image", "inspect", PY_IMAGE, "--format", "{{.Id}}"]).trim() !== PY_IMAGE) {
    throw new Error(`image ${PY_IMAGE} is not provisioned`);
  }
  const run = path.join(cfg.scratch, name);
  let exists = true;
  try { deps.fs.lstatSync(run); } catch (e) { if (e?.code === "ENOENT") exists = false; else throw e; }
  if (exists) throw new Error(`run directory exists: ${run}`);
  deps.guard.makeSandbox(run);

  const child = (label, cmd, args) => { // stdout -> <label>.out, stderr -> <label>.err, exit -> <label>.exit
    const out = openOutput(deps, path.join(run, `${label}.out`));
    let err;
    let r;
    try {
      err = openOutput(deps, path.join(run, `${label}.err`));
      r = deps.spawnSync(cmd, args, { stdio: ["ignore", out, err], ...NO_KILL });
    } finally {
      deps.fs.closeSync(out);
      if (err !== undefined) deps.fs.closeSync(err);
    }
    const exit = r.error ? `spawn-error ${r.error.message}` : String(r.status);
    write(deps, path.join(run, `${label}.exit`), exit + "\n");
    return exit;
  };

  if (child("preflight", "powershell", ["-NoProfile", "-File", preflight]) !== "0") {
    throw new Error("memory preflight failed; refusing to start the container");
  }
  const nonce = deps.nonce();
  if (!/^[0-9a-f]{32}$/.test(nonce)) throw new Error("bad nonce");
  // Re-proven immediately before docker (a bind replaced since the first proof refuses here).
  const mounts = Object.entries(cfg.binds).flatMap(([k, b]) => {
    const now = prove(deps, b);
    if (now !== abs[k]) throw new Error(`bind ${k} moved from ${abs[k]} to ${now}`);
    return mount(now, b);
  });
  const dockerExit = child("container", "docker", ["run", "--rm", "--pull", "never", "--tmpfs", "/tmp:exec,size=6g",
    ...mounts, "-e", `GATE_NONCE=${nonce}`, PY_IMAGE, "sh", "-c", "tr -d '\\r' < /gates.sh > /tmp/gates.sh && sh /tmp/gates.sh"]);
  const raw = deps.fs.readFileSync(deps.guard.assertOutput(path.join(run, "container.out")), "utf8");
  const entries = parseBundle(raw, nonce); // refuses on ANY unexpected byte; nothing extracted is published before
  for (const e of entries) {
    write(deps, path.join(run, `${e.label}.log`), e.log);
    write(deps, path.join(run, `${e.label}.exit`), e.exit + "\n");
  }
  const results = entries.map(({ label, exit }) => ({ label, exit }));
  write(deps, path.join(run, "summary.json"), JSON.stringify({ head, dockerExit, results }, null, 1) + "\n");
  return { run, head, dockerExit, results };
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const guard = await import(pathToFileURL(GUARD_PATH).href);
  const deps = { guard, fs: fsReal, spawnSync: spawnReal, nonce: () => crypto.randomBytes(16).toString("hex") };
  console.log(JSON.stringify(launch(process.argv[2], process.argv[3], deps, guard.PROJECT_ROOT)));
}
