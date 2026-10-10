// CE-L12D007-02 revision 2: pinned Pi's real NodeExecutionEnv.remove over ce02-recovery-matrix.json (Windows
// fixWinEPERM recovery). As ce02-pi-probe.mjs, but each row may inject several failures, fixtures may hold
// read-only attributes and file symlinks, and the output also lists every entry left read-only (so a recovery that
// clears a link TARGET's attribute is visible). Usage:
//   node --experimental-strip-types --no-warnings ce02-recovery-pi-probe.mjs <pi> <scratch dir in the project>
import fs from "node:fs";
import * as path from "node:path";
import { pathToFileURL } from "node:url";
import { syncBuiltinESMExports } from "node:module";
import { makeSandbox, assertInside, assertEntry, cleanupSandbox } from "../fs-guard/fs-guard.mjs";

const [piDir, scratch] = process.argv.slice(2);
const matrix = JSON.parse(fs.readFileSync(new URL("./ce02-recovery-matrix.json", import.meta.url), "utf8"));
const OPS = ["lstat", "stat", "unlink", "rmdir", "readdir", "chmod"];
let row = null; // { root, plans, calls }

const relOf = (p) => path.relative(row.root, String(p).replace(/^\\\\\?\\/, "")).split(path.sep).join("/");
for (const op of OPS) {
  const real = fs[op];
  fs[op] = function (p, ...args) {
    if (row) {
      const rel = relOf(p);
      if (rel === "tree" || rel.startsWith("tree/")) {
        const key = `${op} ${rel}`;
        row.calls[key] = (row.calls[key] ?? 0) + 1;
        const plan = row.plans.find((q) => q.op === op && q.rel === rel && q.nth === row.calls[key]);
        if (plan) {
          const callback = args.at(-1);
          const error = Object.assign(new Error(`injected ${plan.code}`), { code: plan.code, syscall: op, path: String(p) });
          queueMicrotask(() => callback(error));
          return;
        }
      }
    }
    return real.call(this, p, ...args);
  };
}
syncBuiltinESMExports();
const { NodeExecutionEnv } = await import(pathToFileURL(`${piDir}/packages/agent/src/harness/env/nodejs.ts`).href);

function state(root) {
  const remains = [];
  const readonly = [];
  const walk = (rel) => {
    const abs = assertEntry(root, rel);
    const st = fs.lstatSync(abs);
    remains.push(st.isSymbolicLink() ? `${rel}@` : st.isDirectory() ? `${rel}/` : rel);
    if (!st.isSymbolicLink() && !(st.mode & 0o200)) readonly.push(rel);
    if (st.isDirectory() && !st.isSymbolicLink()) for (const name of fs.readdirSync(abs).sort()) walk(`${rel}/${name}`);
  };
  for (const name of fs.readdirSync(root).sort()) walk(name);
  return { remains, readonly };
}

for (const spec of matrix.rows) {
  const root = makeSandbox(path.join(scratch, `ce02r-pi-${spec.id}-${Date.now()}`));
  const late = [];
  for (const entry of spec.fixture) {
    if (typeof entry === "string") {
      if (entry.endsWith("/")) fs.mkdirSync(assertInside(root, entry.slice(0, -1)));
      else fs.writeFileSync(assertInside(root, entry), "x");
    } else if (entry.link) {
      fs.symlinkSync(assertInside(root, entry.to), assertEntry(root, entry.link), "file");
    } else if (entry.ro) {
      late.push(entry.ro);
    }
  }
  for (const rel of late) fs.chmodSync(assertInside(root, rel), 0o444);
  const remove = spec.remove ?? { path: "tree", recursive: true };
  row = { root, plans: spec.inject, calls: {} };
  const result = await new NodeExecutionEnv({ cwd: root }).remove(remove.path, { recursive: remove.recursive });
  const calls = row.calls;
  row = null;
  const errorPath = result.ok || !result.error.path ? null
    : path.relative(root, String(result.error.path).replace(/^\\\\\?\\/, "")).split(path.sep).join("/");
  console.log(JSON.stringify({
    platform: process.platform, id: spec.id, result: result.ok ? "ok" : result.error.code, path: errorPath,
    calls: Object.fromEntries(Object.entries(calls).sort()), ...state(root),
  }));
  for (const rel of late) {
    const p = path.join(root, rel);
    if (fs.existsSync(p)) fs.chmodSync(assertInside(root, rel), 0o666);
  }
  if (!cleanupSandbox(root)) process.exitCode = 1;
}
