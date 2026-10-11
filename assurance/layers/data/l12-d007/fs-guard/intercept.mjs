// Preload backstop (node --import ./intercept.mjs ...), CE-L12D007-01 R8. Every filesystem MUTATION is
// classified by its OPERATION and admitted only when that class's proof places its target inside the
// project root:
//   REFERENT (follows the final link): write/append/truncate/open/chmod/mkdir/copy destination;
//   ENTRY    (no-follow on the entry itself): unlink, rmdir, rm, rename (both ends), symlink/link path.
// An ENTRY proof never authorizes a REFERENT operation on the same path. A refused call is logged to
// FS_INTERCEPT_LOG -- whose own destination is REFERENT-proven before every append -- and thrown; it
// never reaches the OS.
import fs from "node:fs";
import path from "node:path";
import { syncBuiltinESMExports } from "node:module";
import { proveReferentAbs, proveEntryAbs, assertOutput } from "./fs-guard.mjs";

const LOG = process.env.FS_INTERCEPT_LOG ? path.resolve(process.env.FS_INTERCEPT_LOG) : null;
const appendOriginal = fs.appendFileSync;
function record(line) {
  if (!LOG) return;
  appendOriginal(assertOutput(LOG), line + "\n"); // the log destination is proven too
}
const isFd = (v) => typeof v === "number";

function guard(name, fn, checks) {
  return function (...args) {
    for (const [index, cls] of checks) {
      const arg = args[index];
      if (arg === undefined || isFd(arg)) continue;
      const target = path.resolve(String(arg));
      try {
        if (cls === "REFERENT") proveReferentAbs(target);
        else proveEntryAbs(target);
      } catch (e) {
        record(`${cls} ${name} ${target}`);
        throw new Error(`intercepted ${cls} ${name} refused: ${target} (${e.message})`);
      }
    }
    return fn.apply(this, args);
  };
}

const R = "REFERENT", E = "ENTRY";
const SYNC = {
  writeFileSync: [[0, R]], appendFileSync: [[0, R]], truncateSync: [[0, R]], openSync: [[0, R]], chmodSync: [[0, R]],
  mkdirSync: [[0, R]], copyFileSync: [[1, R]], cpSync: [[1, R]],
  unlinkSync: [[0, E]], rmdirSync: [[0, E]], rmSync: [[0, E]], renameSync: [[0, E], [1, E]],
  symlinkSync: [[1, E]], linkSync: [[1, E]],
};
for (const [name, checks] of Object.entries(SYNC)) if (fs[name]) fs[name] = guard(name, fs[name], checks);
const ASYNC = {
  writeFile: [[0, R]], appendFile: [[0, R]], truncate: [[0, R]], open: [[0, R]], chmod: [[0, R]], mkdir: [[0, R]],
  copyFile: [[1, R]], cp: [[1, R]], unlink: [[0, E]], rmdir: [[0, E]], rm: [[0, E]], rename: [[0, E], [1, E]],
  symlink: [[1, E]], link: [[1, E]],
};
for (const [name, checks] of Object.entries(ASYNC)) if (fs.promises[name]) fs.promises[name] = guard(`promises.${name}`, fs.promises[name], checks);
// Named ESM imports of the built-ins (Pi's `import { writeFile } from "node:fs/promises"`) do not see
// patches to the module objects until they are synced.
syncBuiltinESMExports();
