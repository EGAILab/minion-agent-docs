// Filesystem containment guard for probes and scripts (Owner rule, 2026-10-10).
// Every destructive or writing operation a script performs on a computed path must first pass
// assertInside(sandbox, target). The sandbox itself must lie under the project root.
import fs from "node:fs";
import path from "node:path";

// FS_GUARD_ROOT is only for inside a container, e.g. a private tmpfs (/tmp) root.
export const PROJECT_ROOT = path.resolve(process.env.FS_GUARD_ROOT ?? "E:/AI/Projects/OpenMinds/Minions/Minion-Agent");

function within(parent, child) {
  const rel = path.relative(parent, child);
  return rel === "" || (!rel.startsWith("..") && !path.isAbsolute(rel));
}

// Resolve through existing symlinks/junctions too, so a link cannot smuggle a target outside.
function real(p) {
  let cur = path.resolve(p);
  const rest = [];
  while (!fs.existsSync(cur)) {
    const parent = path.dirname(cur);
    if (parent === cur) break;
    rest.unshift(path.basename(cur));
    cur = parent;
  }
  return path.join(fs.realpathSync.native(cur), ...rest);
}

export function makeSandbox(dir) {
  const abs = path.resolve(dir);
  if (!within(PROJECT_ROOT, abs) || abs === PROJECT_ROOT) {
    throw new Error(`fs-guard: sandbox ${abs} is not strictly inside ${PROJECT_ROOT}`);
  }
  fs.mkdirSync(abs, { recursive: true });
  return abs;
}

export function assertInside(sandbox, target, cwd = sandbox) {
  const lexical = path.resolve(cwd, target);
  if (!within(sandbox, lexical)) throw new Error(`fs-guard: ${target} resolves to ${lexical}, outside sandbox ${sandbox}`);
  // A path that walks into a link and then out (a\..\..) is caught lexically above; a link pointing
  // outside is caught here. The sandbox root itself may never be the target of a destructive op.
  const resolved = real(lexical);
  if (!within(real(sandbox), resolved)) throw new Error(`fs-guard: ${target} really resolves to ${resolved}, outside sandbox ${sandbox}`);
  if (path.resolve(lexical) === path.resolve(sandbox)) throw new Error(`fs-guard: ${target} is the sandbox root itself`);
  return lexical;
}
