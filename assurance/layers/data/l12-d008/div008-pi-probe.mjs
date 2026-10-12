// L12-D008 / DIV-008 (minion-agent#215, provenance #127): pinned Pi's real NodeExecutionEnv.remove (recursive) with
// SEVERAL failing children. Node v22.15.1 rimraf (_rmchildren, blob 24bf3f46) starts every child removal at once and
// forwards the FIRST child error to settle (the `done` guard). This probe controls only the SETTLEMENT ORDER of the
// injected failures and measures, for each row:
//   - result / path: what Pi reports;
//   - seq: every intercepted call below `tree`, in call order, with each injected failure's settlement ("settle ...");
//   - at_settle: the calls made and the entries remaining at the moment remove() settles;
//   - after_drain: the same once every intercepted operation still in flight has completed (Pi does not wait for
//     siblings after the first error), and late_calls, the calls made after settlement.
// Injection: {op, rel, nth, code[, hold]}. A row's `settle` lists the held failures' rels in the order their error
// callbacks are delivered; held failures are released, in that order, once all of them are pending (or after 1 s,
// flagged settle_incomplete). Without `settle`, failures are delivered on the next microtask (as CE-02).
// Natural rows (`natural`, Linux only) use real host failures: a directory chmod 0555 makes unlinking its children
// fail with EACCES for a non-root user; they run `repeat` times and report each run.
// Every fixture write, chmod and cleanup goes through the reviewed fs-guard (CE-L12D007-01). Usage:
//   node --experimental-strip-types --no-warnings div008-pi-probe.mjs <pi> <scratch dir in the project> [matrix]
import fs from "node:fs";
import * as path from "node:path";
import { pathToFileURL } from "node:url";
import { syncBuiltinESMExports } from "node:module";
import { makeSandbox, assertInside, assertEntry, cleanupSandbox } from "../l12-d007/fs-guard/fs-guard.mjs";

const [piDir, scratch, matrixName = "div008-matrix.json"] = process.argv.slice(2);
const matrix = JSON.parse(fs.readFileSync(new URL(`./${matrixName}`, import.meta.url), "utf8"));
const OPS = ["lstat", "stat", "unlink", "rmdir", "readdir", "chmod"];
let row = null; // { root, plans, calls, seq, held, inflight }

const relOf = (p) => path.relative(row.root, String(p).replace(/^\\\\\?\\/, "")).split(path.sep).join("/");

function releaseHeld(r) {
  // Deliver the held failures in the row's settle order, one macrotask apart, so each settles separately. `r` is
  // the row object itself: the global `row` is cleared as soon as remove() settles, while later deliveries run on.
  if (r.released) return;
  r.released = true;
  const order = r.settle.filter((rel) => r.held[rel]);
  const deliver = (i) => {
    if (i >= order.length) return;
    const h = r.held[order[i]];
    delete r.held[order[i]];
    r.seq.push(`settle ${h.key} ${h.error.code}`);
    h.callback(h.error);
    setImmediate(() => deliver(i + 1));
  };
  deliver(0);
}

for (const op of OPS) {
  const real = fs[op];
  fs[op] = function (p, ...args) {
    if (row) {
      const rel = relOf(p);
      if (rel === "tree" || rel.startsWith("tree/")) {
        const key = `${op} ${rel}`;
        row.calls[key] = (row.calls[key] ?? 0) + 1;
        row.seq.push(key);
        const plan = row.plans.find((q) => q.op === op && q.rel === rel && q.nth === row.calls[key]);
        const callback = args.at(-1);
        if (plan) {
          plan.fired = true;
          const error = Object.assign(new Error(`injected ${plan.code}`), { code: plan.code, syscall: op, path: String(p) });
          if (row.settle && row.settle.includes(rel)) {
            row.held[rel] = { key, error, callback };
            if (row.settle.every((s) => row.held[s])) releaseHeld(row);
            return;
          }
          queueMicrotask(() => { row.seq.push(`settle ${key} ${plan.code}`); callback(error); });
          return;
        }
        if (typeof callback === "function") {
          row.inflight++;
          const r = row;
          args[args.length - 1] = function (...cbArgs) {
            r.inflight--;
            // A NATIVE failure (not injected): recorded with its code, so a natural row's origin is observed at
            // the real call rather than inferred from what remains (CE-L12D008-01).
            if (cbArgs[0]) r.seq.push(`fail ${key} ${cbArgs[0].code}`);
            return callback.apply(this, cbArgs);
          };
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
  const walk = (rel) => {
    const abs = assertEntry(root, rel);
    const st = fs.lstatSync(abs);
    remains.push(st.isSymbolicLink() ? `${rel}@` : st.isDirectory() ? `${rel}/` : rel);
    if (st.isDirectory() && !st.isSymbolicLink()) for (const name of fs.readdirSync(abs).sort()) walk(`${rel}/${name}`);
  };
  for (const name of fs.readdirSync(root).sort()) walk(name);
  return remains;
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const sortedCalls = (c) => Object.fromEntries(Object.entries(c).sort());

async function runOnce(spec, run) {
  const root = makeSandbox(path.join(scratch, `div008-pi-${spec.id}-${run}-${Date.now()}`));
  const roDirs = [];
  for (const entry of spec.fixture) {
    if (typeof entry === "string") {
      if (entry.endsWith("/")) fs.mkdirSync(assertInside(root, entry.slice(0, -1)));
      else fs.writeFileSync(assertInside(root, entry), "x");
    } else if (entry.ro_dir) {
      roDirs.push(entry.ro_dir);
    }
  }
  for (const rel of roDirs) fs.chmodSync(assertInside(root, rel), 0o555);
  row = { root, plans: (spec.inject ?? []).map((q) => ({ ...q })), calls: {}, seq: [], held: {}, inflight: 0,
    settle: spec.settle ?? null };
  const current = row;
  let settleTimer = null;
  if (current.settle) {
    settleTimer = setTimeout(() => { current.settleIncomplete = true; releaseHeld(current); }, 1000);
  }
  const result = await new NodeExecutionEnv({ cwd: root }).remove("tree", { recursive: true, force: false });
  if (settleTimer) clearTimeout(settleTimer);
  const atSettle = { calls: sortedCalls(current.calls), remains: state(root) };
  const settleIndex = current.seq.length;
  // Drain: wait for every intercepted operation still in flight, and any held failure, to complete.
  for (let waited = 0; waited < 3000 && (current.inflight > 0 || Object.keys(current.held).length > 0); waited += 10) await sleep(10);
  await sleep(50);
  const drained = current.inflight === 0 && Object.keys(current.held).length === 0;
  row = null;
  const afterDrain = { calls: sortedCalls(current.calls), remains: state(root) };
  for (const rel of roDirs) {
    const p = path.join(root, rel);
    if (fs.existsSync(p)) fs.chmodSync(assertInside(root, rel), 0o755);
  }
  const errorPath = result.ok || !result.error.path ? null
    : path.relative(root, String(result.error.path).replace(/^\\\\\?\\/, "")).split(path.sep).join("/");
  const out = {
    platform: process.platform, id: spec.id, run, result: result.ok ? "ok" : result.error.code, path: errorPath,
    seq: current.seq, at_settle: atSettle, after_drain: afterDrain, late_calls: current.seq.slice(settleIndex),
    drained, settle_incomplete: current.settleIncomplete === true,
    unfired: current.plans.filter((q) => !q.fired).map((q) => `${q.op} ${q.rel} #${q.nth}`),
  };
  if (!cleanupSandbox(root)) process.exitCode = 1;
  return out;
}

for (const spec of matrix.rows) {
  if (spec.platforms && !spec.platforms.includes(process.platform)) continue;
  const repeat = spec.repeat ?? 1;
  for (let run = 1; run <= repeat; run++) console.log(JSON.stringify(await runOnce(spec, run)));
}
