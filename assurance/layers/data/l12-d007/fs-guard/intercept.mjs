// Preload (node --import ./intercept.mjs ...): every filesystem MUTATION whose path is outside the
// project root is recorded to FS_INTERCEPT_LOG (inside the project) and REFUSED -- it never reaches
// the OS. Inside-root mutations proceed. Used by containment-controls.mjs to prove the guard fails
// closed without ever risking an outside write.
import fs from "node:fs";
import path from "node:path";

const ROOT = path.resolve("E:/AI/Projects/OpenMinds/Minions/Minion-Agent").toLowerCase();
const LOG = process.env.FS_INTERCEPT_LOG;
const original = { appendFileSync: fs.appendFileSync };
const inside = (p) => {
  const abs = path.resolve(String(p)).toLowerCase();
  return abs === ROOT || abs.startsWith(ROOT + path.sep);
};
function guard(name, fn, argIndexes) {
  return function (...args) {
    for (const i of argIndexes) {
      if (args[i] !== undefined && !inside(args[i])) {
        if (LOG) original.appendFileSync(LOG, `${name} ${path.resolve(String(args[i]))}\n`);
        throw new Error(`intercepted outside-root ${name}: ${args[i]}`);
      }
    }
    return fn.apply(this, args);
  };
}
const SYNC = { writeFileSync: [0], appendFileSync: [0], mkdirSync: [0], rmSync: [0], rmdirSync: [0], unlinkSync: [0],
  renameSync: [0, 1], copyFileSync: [1], symlinkSync: [1], linkSync: [1], openSync: [0], truncateSync: [0], chmodSync: [0] };
for (const [name, idx] of Object.entries(SYNC)) fs[name] = guard(name, fs[name], idx);
const ASYNC = { writeFile: [0], appendFile: [0], mkdir: [0], rm: [0], rmdir: [0], unlink: [0], rename: [0, 1],
  copyFile: [1], symlink: [1], link: [1], open: [0], truncate: [0], chmod: [0] };
for (const [name, idx] of Object.entries(ASYNC)) fs.promises[name] = guard(`promises.${name}`, fs.promises[name], idx);
