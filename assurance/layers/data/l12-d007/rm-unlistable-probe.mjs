// L12-D007 implementation-stage witness: pinned Node v22.15.1 (Pi's runtime) `fs.promises.rm(d, {recursive:
// true})` -- the call Pi's `remove` makes -- of an EMPTY directory whose listing is denied, and of a NON-EMPTY
// one. Windows: a deny-(RD) ACE (FILE_LIST_DIRECTORY only); POSIX: mode 000. Shows rimraf's rmdir-first order.
// Usage: node rm-unlistable-probe.mjs <scratch dir inside the project root>
import fs from "node:fs";
import * as path from "node:path";
import { execFileSync } from "node:child_process";
import { makeSandbox, assertInside, assertEntry, restoreAccess, cleanupSandbox } from "./fs-guard/fs-guard.mjs";

const [scratch] = process.argv.slice(2);
const box = makeSandbox(path.join(scratch, `rm-unlistable-${Date.now()}`));
const win = process.platform === "win32";
const deny = (p) => (win ? execFileSync("icacls", [p, "/deny", `${process.env.USERNAME}:(RD)`, "/L"]) : fs.chmodSync(p, 0));
const allow = (p) => (win ? execFileSync("icacls", [p, "/reset", "/L"]) : fs.chmodSync(p, 0o700));

for (const [name, child] of [["empty", null], ["nonempty", "f"]]) {
  const d = assertInside(box, name);
  fs.mkdirSync(d);
  if (child) fs.writeFileSync(assertInside(box, path.join(name, child)), "x");
  deny(d);
  try {
    await fs.promises.rm(assertEntry(box, name), { recursive: true });
    console.log(JSON.stringify({ platform: process.platform, case: name, result: "ok", exists: fs.existsSync(d) }));
  } catch (err) {
    console.log(JSON.stringify({ platform: process.platform, case: name, result: err.code, path: err.path === d ? name : err.path }));
  } finally {
    restoreAccess(box, name, "directory", allow);
  }
}
if (!cleanupSandbox(box)) process.exitCode = 1;
