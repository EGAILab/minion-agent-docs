// Filesystem containment guard for probes and scripts (Owner rule, 2026-10-10).
// Every destructive or writing operation a script performs on a computed path must first pass
// assertInside(sandbox, target); every output file must pass assertOutput(path). A sandbox must lie
// strictly inside the project root, both lexically and through every link.
import fs from "node:fs";
import path from "node:path";

// FS_GUARD_ROOT is only for inside a container (a private tmpfs root such as /tmp/guard-root).
export const PROJECT_ROOT = path.resolve(process.env.FS_GUARD_ROOT ?? "E:/AI/Projects/OpenMinds/Minions/Minion-Agent");
// FS_GUARD_OUTPUT optionally names one more directory outputs may be written to (a container's /out).
const OUTPUT_ROOT = process.env.FS_GUARD_OUTPUT ? path.resolve(process.env.FS_GUARD_OUTPUT) : null;

const MAX_HOPS = 40;
const fold = (p) => (process.platform === "win32" ? p.toLowerCase() : p);

function within(parent, child) {
  const rel = path.relative(fold(parent), fold(child));
  return rel === "" || (!rel.startsWith("..") && !path.isAbsolute(rel));
}

function lstatOrNull(p) {
  try {
    return fs.lstatSync(p);
  } catch {
    return null;
  }
}

// Follow `target` component by component. Every link met -- existing, dangling or looping -- has
// its text resolved and that hop checked against `boundary`; a missing component ends the walk
// (nothing below it exists to redirect anything). Never path.join: an "x:" component would be a drive.
// `boundary` is a directory; a hop is inside when it is under it as written OR under its real path
// (the project root itself may sit below a junction).
function walk(target, boundary, what) {
  const bounds = [path.resolve(boundary), realRoot(boundary)];
  let pending = path.resolve(target);
  for (let hop = 0; hop <= MAX_HOPS; hop++) {
    if (!bounds.some((b) => within(b, pending))) throw new Error(`fs-guard: ${what} reaches ${pending}, outside ${boundary}`);
    const root = path.parse(pending).root;
    const parts = pending.slice(root.length).split(path.sep).filter(Boolean);
    let cur = root.replace(/[\\/]+$/, "");
    let redirected = null;
    for (let i = 0; i < parts.length; i++) {
      cur = `${cur}${path.sep}${parts[i]}`;
      const st = lstatOrNull(cur);
      if (st === null) break;
      if (st.isSymbolicLink()) {
        const text = fs.readlinkSync(cur);
        const base = path.isAbsolute(text) ? text : `${path.dirname(cur)}${path.sep}${text}`;
        redirected = path.resolve([base, ...parts.slice(i + 1)].join(path.sep));
        break;
      }
    }
    if (redirected === null) return pending;
    pending = redirected;
  }
  // A link loop: every hop above was already inside the boundary, so the loop cannot leave it.
  return pending;
}

function realRoot(p) {
  return fs.realpathSync.native(p);
}

export function makeSandbox(dir) {
  const abs = path.resolve(dir);
  if (!within(PROJECT_ROOT, abs) || fold(abs) === fold(PROJECT_ROOT)) {
    throw new Error(`fs-guard: sandbox ${abs} is not strictly inside ${PROJECT_ROOT}`);
  }
  walk(abs, PROJECT_ROOT, `sandbox ${abs}`);
  fs.mkdirSync(abs, { recursive: true });
  const real = realRoot(abs);
  if (!within(realRoot(PROJECT_ROOT), real) || fold(real) === fold(realRoot(PROJECT_ROOT))) {
    throw new Error(`fs-guard: sandbox ${abs} really resolves to ${real}, outside ${PROJECT_ROOT}`);
  }
  return abs;
}

// The Owner's prohibited raw target forms, refused BEFORE any normalization: a ".." segment,
// a drive-relative or bare drive ("X:", "X:foo"), an absolute path, a UNC / device path, an empty name.
function assertRawForm(target) {
  if (typeof target !== "string" || target === "") throw new Error(`fs-guard: empty target`);
  if (/^[a-zA-Z]:/.test(target)) throw new Error(`fs-guard: ${target} is a drive form`);
  if (/^[\\/]/.test(target)) throw new Error(`fs-guard: ${target} is absolute, UNC or a device path`);
  if (target.split(/[\\/]/).includes("..")) throw new Error(`fs-guard: ${target} has a ".." segment`);
}

export function assertInside(sandbox, target, cwd = sandbox) {
  assertRawForm(target);
  const lexical = path.resolve(cwd, target);
  if (!within(sandbox, lexical)) throw new Error(`fs-guard: ${target} resolves to ${lexical}, outside sandbox ${sandbox}`);
  if (fold(lexical) === fold(path.resolve(sandbox))) throw new Error(`fs-guard: ${target} is the sandbox root itself`);
  walk(lexical, sandbox, target);
  return lexical;
}

export function assertOutput(file) {
  const abs = path.resolve(file);
  const roots = [PROJECT_ROOT, OUTPUT_ROOT].filter(Boolean);
  const ok = roots.some((r) => {
    if (!within(r, abs) || fold(abs) === fold(r)) return false;
    try {
      walk(abs, r, `output ${abs}`);
      return true;
    } catch {
      return false;
    }
  });
  if (!ok) throw new Error(`fs-guard: output ${abs} is outside ${roots.join(" / ")}`);
  return abs;
}
