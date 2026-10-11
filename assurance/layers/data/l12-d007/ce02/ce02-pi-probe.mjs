// CE-L12D007-02: pinned Pi's real NodeExecutionEnv.remove(tree, {recursive: true}) over ce02-matrix.json. Each row
// injects ONE failure of one native call (op, child rel path, nth call on it); every other call is real. The
// callback-API fs functions rimraf uses are wrapped ONCE, before rimraf is lazily loaded (it destructures them),
// and consult the current row's plan. Output: one JSON line per row (result, error path, per-path call counts,
// what remains). Usage: node --experimental-strip-types --no-warnings ce02-pi-probe.mjs <pi> <scratch in project>
import fs from "node:fs";
import * as path from "node:path";
import { pathToFileURL } from "node:url";
import { syncBuiltinESMExports } from "node:module";
import { makeSandbox, assertInside, cleanupSandbox } from "../fs-guard/fs-guard.mjs";

const [piDir, scratch] = process.argv.slice(2);
const matrix = JSON.parse(fs.readFileSync(new URL("./ce02-matrix.json", import.meta.url), "utf8"));
const OPS = ["lstat", "stat", "unlink", "rmdir", "readdir", "chmod"];
let row = null; // { root, plan, calls }

const relOf = (p) => {
  const s = String(p).replace(/^\\\\\?\\/, "");
  return path.relative(row.root, s).split(path.sep).join("/");
};
for (const op of OPS) {
  const real = fs[op];
  fs[op] = function (p, ...args) {
    if (row) {
      const rel = relOf(p);
      if (rel.startsWith("tree")) {
        const key = `${op} ${rel}`;
        row.calls[key] = (row.calls[key] ?? 0) + 1;
        const plan = row.plan;
        if (plan && plan.op === op && plan.rel === rel && plan.nth === row.calls[key]) {
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

function remaining(root) {
  const out = [];
  const walk = (rel) => {
    const abs = assertInside(root, rel);
    const st = fs.lstatSync(abs);
    out.push(st.isDirectory() ? `${rel}/` : rel);
    if (st.isDirectory()) for (const name of fs.readdirSync(abs).sort()) walk(`${rel}/${name}`);
  };
  if (fs.existsSync(path.join(root, "tree"))) walk("tree");
  return out;
}

for (const spec of matrix.rows) {
  const root = makeSandbox(path.join(scratch, `ce02-pi-${spec.id}-${Date.now()}`));
  for (const entry of spec.fixture) {
    if (entry.endsWith("/")) fs.mkdirSync(assertInside(root, entry.slice(0, -1)));
    else fs.writeFileSync(assertInside(root, entry), "x");
  }
  row = { root, plan: spec.inject, calls: {} };
  const result = await new NodeExecutionEnv({ cwd: root }).remove("tree", { recursive: true });
  const calls = row.calls;
  row = null;
  const errorPath = result.ok ? null : result.error.path ? path.relative(root, String(result.error.path).replace(/^\\\\\?\\/, "")).split(path.sep).join("/") : null;
  console.log(JSON.stringify({
    platform: process.platform, id: spec.id, result: result.ok ? "ok" : result.error.code, path: errorPath,
    calls: Object.fromEntries(Object.entries(calls).sort()), remains: remaining(root),
  }));
  if (!cleanupSandbox(root)) process.exitCode = 1;
}
