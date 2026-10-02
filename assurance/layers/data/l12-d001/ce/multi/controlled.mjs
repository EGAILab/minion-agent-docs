// CE-L12-D001-01-C001 scope-boundary witness (minion-agent#123): pinned Pi's recursive remove with TWO failing
// children reports the FIRST FAILURE TO SETTLE (Node rimraf _rmchildren, blob 24bf3f46: children start together; the
// first error callback wins, guarded by `done`). Adapted from Codex's reviewer probe: callback instrumentation
// controls ONLY the completion order of the two unlink failures; EACCES is injected for scheduling control, not as
// host-error characterization. Real pinned NodeExecutionEnv + Node's real rimraf.
//   node --experimental-strip-types controlled.mjs <pi checkout> <out.json>
import fs from "node:fs";
import fsp from "node:fs/promises";
import path from "node:path";
import { tmpdir } from "node:os";
import { pathToFileURL } from "node:url";
const [piDir, outPath] = process.argv.slice(2);
const original = fs.unlink;
let control = null;
fs.unlink = (p, cb) => (control ? control(p, cb) : original(p, cb));
const { NodeExecutionEnv } = await import(pathToFileURL(`${piDir}/packages/agent/src/harness/env/nodejs.ts`).href);
const U = (s) => Array.from({ length: s.length }, (_, i) => s.charCodeAt(i));
const results = [];
for (const [variant, name] of Object.entries({ scalar: "tree", lone: "t\ud800" })) {
  for (const settle of [["a", "b"], ["b", "a"]]) {
    const root = fs.realpathSync(fs.mkdtempSync(path.join(tmpdir(), "l12mf-")));
    const env = new NodeExecutionEnv({ cwd: root });
    await env.writeFile(`${name}/a`, "a"); await env.writeFile(`${name}/b`, "b");
    const entered = [], settled = [], pending = {};
    control = (p, cb) => {
      const child = path.basename(p.toString());
      entered.push(child);
      pending[child] = () => { settled.push(child);
        cb(Object.assign(new Error("controlled unlink failure"), { code: "EACCES", path: p.toString() })); };
      if (pending.a && pending.b) for (const c of settle) pending[c]();
    };
    const r = await env.remove(name, { recursive: true });
    control = null;
    results.push({ id: `${variant}/settle-${settle.join("-")}`, entered, settled,
      observed: { error: r.error?.code, path: path.relative(root, r.error.path).split(path.sep).map(U) } });
  }
}
fs.unlink = original;
fs.writeFileSync(outPath, JSON.stringify({ platform: process.platform, node: process.versions.node, results }, null, 1) + "\n");
console.log(`controlled: ${results.length} cases`);
