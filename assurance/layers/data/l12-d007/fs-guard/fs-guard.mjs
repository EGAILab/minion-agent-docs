// Filesystem containment guard for probes, oracles and controls (Owner rule 2026-10-10; convergence
// episode CE-L12D007-01, AGREED FOR IMPLEMENTATION at revision 3). The proof is chosen by the
// OPERATION CLASS, never per call site:
//   REFERENT  (assertInside / makeSandbox / assertOutput): anything that follows the final link --
//             the whole effective path is proven; an outward final link is refused.
//   ENTRY     (assertEntry): a verified no-follow operation on an entry itself (link creation,
//             unlink of a link): the containing directory is proven, the entry is one R1-clean
//             component and is NOT dereferenced.
//   TRAVERSAL (cleanupSandbox): children are classified as entries first; links are never descended.
// The proof (R2) succeeds only at (i) a completed traversal, (ii) a proven-missing component (R3),
// or (iii) a repeated, fully checked state (a contained cycle). Budget exhaustion, an outward hop, an
// unknown inspection outcome or a readlink failure REFUSE.
import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";

// FS_GUARD_ROOT is only for inside a container (a private tmpfs root such as /tmp/guard-root).
export const PROJECT_ROOT = path.resolve(process.env.FS_GUARD_ROOT ?? "E:/AI/Projects/OpenMinds/Minions/Minion-Agent");
// FS_GUARD_OUTPUT optionally names one more directory outputs may be written to (a container's /out).
const OUTPUT_ROOT = process.env.FS_GUARD_OUTPUT ? path.resolve(process.env.FS_GUARD_OUTPUT) : null;

export const BUDGET = 64;
const fold = (p) => (process.platform === "win32" ? p.toLowerCase() : p);

function within(parent, child) {
  const rel = path.relative(fold(parent), fold(child));
  return rel === "" || (!rel.startsWith("..") && !path.isAbsolute(rel));
}

// R3: the only inspection outcomes that prove a component MISSING. Node reports Win32 2/3/123/161/267
// (not found, invalid or over-long name, stream syntax, a prefix that is not a directory) as
// ENOENT / ENOTDIR through libuv. Everything else -- EACCES, EPERM, EBUSY, ELOOP, ... -- refuses.
const MISSING = new Set(["ENOENT", "ENOTDIR"]);
function inspect(p) {
  try {
    return fs.lstatSync(p);
  } catch (e) {
    if (MISSING.has(e?.code)) return null;
    throw new Error(`fs-guard: cannot inspect ${p} (${e?.code ?? e?.message}); refused`);
  }
}

function realRoot(p) {
  return fs.realpathSync.native(p);
}

// R2: prove that `target` resolves inside `boundary` (as written, or as the boundary's real path).
function prove(target, boundary, what) {
  const bounds = [path.resolve(boundary), realRoot(boundary)];
  const inside = (p) => bounds.some((b) => within(b, p));
  let pending = path.resolve(target);
  const seen = new Set();
  for (let hop = 0; hop < BUDGET; hop++) {
    if (!inside(pending)) throw new Error(`fs-guard: ${what} reaches ${pending}, outside ${boundary}`);
    if (seen.has(fold(pending))) return pending; // (iii) a repeated, fully checked state
    seen.add(fold(pending));
    const root = path.parse(pending).root;
    const parts = pending.slice(root.length).split(path.sep).filter(Boolean);
    let cur = root.replace(/[\\/]+$/, "");
    let redirected = null;
    for (let i = 0; i < parts.length; i++) {
      cur = `${cur}${path.sep}${parts[i]}`;
      const st = inspect(cur);
      if (st === null) break; // (ii) proven missing: nothing below it exists to redirect
      if (st.isSymbolicLink()) {
        let text;
        try { text = fs.readlinkSync(cur); } catch (e) { throw new Error(`fs-guard: cannot read link ${cur} (${e?.code}); refused`); }
        const base = path.isAbsolute(text) ? text : `${path.dirname(cur)}${path.sep}${text}`;
        redirected = path.resolve([base, ...parts.slice(i + 1)].join(path.sep));
        break;
      }
    }
    if (redirected === null) return pending; // (i) completed traversal, or (ii)
    if (!inside(redirected)) throw new Error(`fs-guard: ${what} reaches ${redirected} through a link, outside ${boundary}`);
    pending = redirected;
  }
  throw new Error(`fs-guard: ${what}: ${BUDGET}-hop budget exhausted without a repeated state; refused`);
}

// R1: the Owner's prohibited raw target forms, refused BEFORE any normalization.
function assertRawForm(target) {
  if (typeof target !== "string" || target === "") throw new Error(`fs-guard: empty target`);
  if (/^[a-zA-Z]:/.test(target)) throw new Error(`fs-guard: ${target} is a drive form`);
  if (/^[\\/]/.test(target)) throw new Error(`fs-guard: ${target} is absolute, UNC or a device path`);
  if (target.split(/[\\/]/).includes("..")) throw new Error(`fs-guard: ${target} has a ".." segment`);
}

function lexicalInside(sandbox, target, cwd) {
  assertRawForm(target);
  const lexical = path.resolve(cwd, target);
  if (!within(sandbox, lexical)) throw new Error(`fs-guard: ${target} resolves to ${lexical}, outside sandbox ${sandbox}`);
  if (fold(lexical) === fold(path.resolve(sandbox))) throw new Error(`fs-guard: ${target} is the sandbox root itself`);
  return lexical;
}

// REFERENT: the whole effective path, through the final component.
export function assertInside(sandbox, target, cwd = sandbox) {
  const lexical = lexicalInside(sandbox, target, cwd);
  prove(lexical, sandbox, target);
  return lexical;
}

// ENTRY: for a verified no-follow operation on the entry itself. The containing directory gets the
// full REFERENT proof (it may be the sandbox itself); the final component is never dereferenced.
export function assertEntry(sandbox, target, cwd = sandbox) {
  const lexical = lexicalInside(sandbox, target, cwd);
  const parent = path.dirname(lexical);
  if (fold(parent) !== fold(path.resolve(sandbox))) prove(parent, sandbox, `parent of ${target}`);
  else prove(parent, path.dirname(path.resolve(sandbox)), `sandbox ${sandbox}`);
  return lexical;
}

// Absolute-path proofs for the intercept backstop (R8), which sees the native call's own argument.
// REFERENT: the path itself; ENTRY: its containing directory (the final component not followed).
export function proveReferentAbs(abs, boundary = PROJECT_ROOT) {
  const p = path.resolve(abs);
  if (!within(boundary, p) || fold(p) === fold(path.resolve(boundary))) throw new Error(`fs-guard: ${p} is not strictly inside ${boundary}`);
  return prove(p, boundary, p);
}
export function proveEntryAbs(abs, boundary = PROJECT_ROOT) {
  const p = path.resolve(abs);
  if (!within(boundary, p) || fold(p) === fold(path.resolve(boundary))) throw new Error(`fs-guard: ${p} is not strictly inside ${boundary}`);
  const parent = path.dirname(p);
  if (fold(parent) !== fold(path.resolve(boundary))) prove(parent, boundary, `parent of ${p}`);
  return p;
}

export function makeSandbox(dir) {
  const abs = path.resolve(dir);
  if (!within(PROJECT_ROOT, abs) || fold(abs) === fold(PROJECT_ROOT)) {
    throw new Error(`fs-guard: sandbox ${abs} is not strictly inside ${PROJECT_ROOT}`);
  }
  prove(abs, PROJECT_ROOT, `sandbox ${abs}`); // the ancestry, BEFORE any mkdir
  fs.mkdirSync(abs, { recursive: true });
  const real = realRoot(abs);
  if (!within(realRoot(PROJECT_ROOT), real) || fold(real) === fold(realRoot(PROJECT_ROOT))) {
    throw new Error(`fs-guard: sandbox ${abs} really resolves to ${real}, outside ${PROJECT_ROOT}`);
  }
  return abs;
}

// REFERENT for an output file: inside the project root, or inside FS_GUARD_OUTPUT.
export function assertOutput(file) {
  const abs = path.resolve(file);
  for (const r of [PROJECT_ROOT, OUTPUT_ROOT].filter(Boolean)) {
    if (!within(r, abs) || fold(abs) === fold(r)) continue;
    try { prove(abs, r, `output ${abs}`); return abs; } catch { /* try the next root */ }
  }
  throw new Error(`fs-guard: output ${abs} is outside ${[PROJECT_ROOT, OUTPUT_ROOT].filter(Boolean).join(" / ")}`);
}

// R6: undo a deny_access only on an EXISTING, NON-LINK entry of the recorded kind, re-proven now.
export function restoreAccess(sandbox, rel, kind, restore, log = console.error) {
  try {
    const target = assertInside(sandbox, rel);
    const st = inspect(target);
    if (st === null) return log(`fs-guard: restore skipped, ${rel} is missing`), false;
    if (st.isSymbolicLink()) return log(`fs-guard: restore skipped, ${rel} is now a link`), false;
    if ((kind === "directory") !== st.isDirectory()) return log(`fs-guard: restore skipped, ${rel} changed kind`), false;
    restore(target);
    return true;
  } catch (e) {
    log(`fs-guard: restore skipped (${e.message})`);
    return false;
  }
}

// ENTRY removal of a link or junction AS ITSELF. Node's unlink / rmdir act on the entry, never on its
// referent; a directory link (junction / directory symlink) is removed with rmdir.
function removeLinkEntry(p) {
  try { fs.unlinkSync(p); } catch { fs.rmdirSync(p); }
}

// R7: TRAVERSAL cleanup of a sandbox the caller made. Links and junctions are removed as entries and
// never descended into; ordinary children are re-proven before they are visited; each ordinary entry
// gets its own access reset (Windows `icacls <entry> /reset /L`; POSIX chmod on non-links only); then
// ordinary entries are removed bottom-up. Any refusal or failure leaves the sandbox in place.
export function cleanupSandbox(root, log = console.error) {
  try {
    const sandboxParent = path.dirname(path.resolve(root));
    assertInside(sandboxParent, path.basename(root));
    walkClean(path.resolve(root), path.resolve(root));
    fs.rmdirSync(path.resolve(root));
    return true;
  } catch (e) {
    log(`fs-guard: sandbox left in place (${e.message}): ${root}`);
    return false;
  }
}

// Called only on an ordinary (non-link) entry that was just proven. Windows: the ACL is reset on the
// entry itself (/L) and the read-only attribute cleared; POSIX: owner access restored.
function resetEntry(p, isDirectory) {
  if (process.platform === "win32") {
    execFileSync("icacls", [p, "/reset", "/L", "/Q"], { stdio: "ignore" });
    fs.chmodSync(p, 0o666);
  } else fs.chmodSync(p, isDirectory ? 0o700 : 0o600);
}

function walkClean(root, dir) {
  resetEntry(dir, true);
  for (const name of fs.readdirSync(dir)) {
    const child = assertEntry(root, path.relative(root, `${dir}${path.sep}${name}`));
    const st = inspect(child);
    if (st === null) continue; // vanished
    if (st.isSymbolicLink()) { removeLinkEntry(child); continue; } // as itself; never descended
    assertInside(root, path.relative(root, child)); // ordinary: re-proven before it is visited
    if (st.isDirectory()) {
      walkClean(root, child);
      fs.rmdirSync(child);
    } else {
      resetEntry(child, false);
      fs.unlinkSync(child);
    }
  }
}
