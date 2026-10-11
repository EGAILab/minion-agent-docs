// L12-D007 remediation 1 (L12D007-I002) witness: pinned Pi's real NodeExecutionEnv.remove(tree, {recursive})
// when tree's child is REPLACED after enumeration, before child handling. The real fs.readdir runs; its
// completion callback performs the replacement, then delivers the names (Codex's review-1 interception).
// Scenarios: dir-to-file, file-to-dir, dir-to-link (a directory link to a directory OUTSIDE the tree).
// Usage: node --experimental-strip-types --no-warnings rm-replace-probe.mjs <pi checkout> <scratch dir in the project>
import fs from "node:fs";
import * as path from "node:path";
import { pathToFileURL } from "node:url";
import { syncBuiltinESMExports } from "node:module";
import { makeSandbox, assertInside, cleanupSandbox } from "./fs-guard/fs-guard.mjs";

const [piDir, scratch] = process.argv.slice(2);
const SCENARIOS = {
  "dir-to-file": {
    setup: (t) => fs.mkdirSync(t("tree/child"), { recursive: true }),
    replace: (t) => { fs.rmdirSync(t("tree/child")); fs.writeFileSync(t("tree/child"), "replaced"); },
  },
  "file-to-dir": {
    setup: (t) => { fs.mkdirSync(t("tree")); fs.writeFileSync(t("tree/child"), "x"); },
    replace: (t) => { fs.unlinkSync(t("tree/child")); fs.mkdirSync(t("tree/child")); fs.writeFileSync(t("tree/child/inner"), "y"); },
  },
  "dir-to-link": {
    setup: (t) => { fs.mkdirSync(t("tree/child"), { recursive: true }); fs.mkdirSync(t("outside")); fs.writeFileSync(t("outside/keep"), "k"); },
    replace: (t) => { fs.rmdirSync(t("tree/child")); fs.symlinkSync(t("outside"), t("tree/child"), "dir"); },
  },
};

const realReaddir = fs.readdir;
let armed = null;
fs.readdir = function (p, opts, cb) {
  if (typeof opts === "function") { cb = opts; opts = undefined; }
  return realReaddir.call(this, p, opts, (err, entries) => {
    if (!err && armed && path.resolve(String(p)) === armed.tree) { const fire = armed.fire; armed = null; fire(); }
    cb(err, entries);
  });
};
syncBuiltinESMExports();
const { NodeExecutionEnv } = await import(pathToFileURL(`${piDir}/packages/agent/src/harness/env/nodejs.ts`).href);

for (const [name, { setup, replace }] of Object.entries(SCENARIOS)) {
  const root = makeSandbox(path.join(scratch, `rm-replace-${name}-${Date.now()}`));
  const t = (rel) => assertInside(root, rel);
  setup(t);
  let fired = false;
  armed = { tree: path.resolve(root, "tree"), fire: () => { replace(t); fired = true; } };
  const result = await new NodeExecutionEnv({ cwd: root }).remove("tree", { recursive: true });
  const out = { platform: process.platform, scenario: name, result: result.ok ? "ok" : result.error.code, fired, treeRemains: fs.existsSync(path.join(root, "tree")) };
  if (name === "dir-to-link") out.outsideKeep = fs.readFileSync(t("outside/keep"), "utf8");
  console.log(JSON.stringify(out));
  if (!cleanupSandbox(root)) process.exitCode = 1;
}
