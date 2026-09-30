// WP-13.2 TOOL-032/TOOL-033 authority: pinned Pi b7bb00b9 file-mutation-queue.ts, executed UNMODIFIED under Node
// 22.15.1 (run with `--import ./loader.mjs`). Each scenario scripts realpath answers per invocation (in invocation
// order) and gates each critical section, then records the exact event trace pinned Pi produces.
import { writeFileSync } from "node:fs";
import { withFileMutationQueue } from "./pi/core/tools/file-mutation-queue.ts";

const flush = async () => { for (let i = 0; i < 20; i++) await new Promise((r) => setImmediate(r)); };
const deferred = () => { let resolve, reject; const p = new Promise((a, b) => { resolve = a; reject = b; }); return { p, resolve, reject }; };
const fsError = (code) => Object.assign(new Error(code), { code });

async function scenario(name, calls, driver) {
  // calls: [{id, path, realpath: {ok: "/x"} | {err: "ENOENT"} | {gate: true}, fn: "gate" | "throw" | "ok"}]
  const trace = [];
  const realpathPlans = calls.map((c) => c.realpath);
  const gates = {};
  let invocation = 0;
  globalThis.__queueHarness = {
    trace,
    realpath: async () => {
      const call = calls[invocation];
      const plan = realpathPlans[invocation];
      invocation++;
      trace.push(`realpath:start ${call.id}`);
      let outcome = plan;
      if (plan.gate) {
        const d = deferred();
        gates[`realpath:${call.id}`] = d;
        outcome = await d.p;
      }
      if (outcome.err) { trace.push(`realpath:err ${call.id} ${outcome.err}`); throw fsError(outcome.err); }
      trace.push(`realpath:ok ${call.id} ${outcome.ok}`);
      return outcome.ok;
    },
  };
  const promises = calls.map((c) => {
    const run = withFileMutationQueue(c.path, async () => {
      trace.push(`fn:start ${c.id}`);
      if (c.fn === "gate") {
        const d = deferred();
        gates[`fn:${c.id}`] = d;
        await d.p;
      }
      if (c.fn === "throw") {
        trace.push(`fn:throw ${c.id}`);
        throw new Error(`fn ${c.id} failed`);
      }
      trace.push(`fn:end ${c.id}`);
      return c.id;
    });
    return run.then(
      (v) => { trace.push(`call:ok ${c.id}`); return v; },
      (e) => { trace.push(`call:err ${c.id} ${e.code ?? e.message}`); },
    );
  });
  await flush();
  await driver({ gates, flush, trace });
  await flush();
  await Promise.all(promises);
  return { name, calls: calls.map(({ id, path, realpath, fn }) => ({ id, path, realpath, fn })), trace };
}

const results = [];
results.push(await scenario("same-target-registration-in-call-order",
  [{ id: "A", path: "/w/f.txt", realpath: { gate: true }, fn: "gate" },
   { id: "B", path: "/w/f.txt", realpath: { ok: "/w/f.txt" }, fn: "ok" }],
  async ({ gates, flush }) => {
    await flush(); gates["realpath:A"].resolve({ ok: "/w/f.txt" });
    await flush(); gates["fn:A"].resolve();
  }));
results.push(await scenario("slow-failing-registration-delays-later-registration-until-it-settles",
  [{ id: "A", path: "/w/a.txt", realpath: { gate: true }, fn: "ok" },
   { id: "B", path: "/w/b.txt", realpath: { ok: "/w/b.txt" }, fn: "ok" }],
  async ({ gates, flush }) => { await flush(); gates["realpath:A"].resolve({ err: "EACCES" }); }));
results.push(await scenario("different-keys-run-concurrently",
  [{ id: "A", path: "/w/a.txt", realpath: { ok: "/w/a.txt" }, fn: "gate" },
   { id: "B", path: "/w/b.txt", realpath: { ok: "/w/b.txt" }, fn: "ok" }],
  async ({ gates, flush }) => { await flush(); gates["fn:A"].resolve(); }));
results.push(await scenario("same-key-waits-and-is-released-after-an-error",
  [{ id: "A", path: "/w/f.txt", realpath: { ok: "/w/f.txt" }, fn: "throw" },
   { id: "B", path: "/w/f.txt", realpath: { ok: "/w/f.txt" }, fn: "ok" }],
  async () => {}));
results.push(await scenario("enoent-fallback-key-serializes-creates",
  [{ id: "A", path: "/w/new.txt", realpath: { err: "ENOENT" }, fn: "gate" },
   { id: "B", path: "/w/new.txt", realpath: { err: "ENOENT" }, fn: "ok" }],
  async ({ gates, flush }) => { await flush(); gates["fn:A"].resolve(); }));
results.push(await scenario("enotdir-fallback-key-serializes",
  [{ id: "A", path: "/w/notes.txt/child.md", realpath: { err: "ENOTDIR" }, fn: "gate" },
   { id: "B", path: "/w/notes.txt/child.md", realpath: { err: "ENOTDIR" }, fn: "ok" }],
  async ({ gates, flush }) => { await flush(); gates["fn:A"].resolve(); }));
results.push(await scenario("other-realpath-error-fails-registration-and-leaves-no-entry",
  [{ id: "A", path: "/w/locked/f.txt", realpath: { err: "EACCES" }, fn: "ok" },
   { id: "B", path: "/w/locked/f.txt", realpath: { ok: "/w/locked/f.txt" }, fn: "ok" }],
  async () => {}));
results.push(await scenario("symlink-and-target-share-one-queue",
  [{ id: "A", path: "/w/link.txt", realpath: { ok: "/w/target.txt" }, fn: "gate" },
   { id: "B", path: "/w/target.txt", realpath: { ok: "/w/target.txt" }, fn: "ok" }],
  async ({ gates, flush }) => { await flush(); gates["fn:A"].resolve(); }));
results.push(await scenario("fifo-of-three-on-one-key",
  [{ id: "A", path: "/w/f.txt", realpath: { ok: "/w/f.txt" }, fn: "gate" },
   { id: "B", path: "/w/f.txt", realpath: { ok: "/w/f.txt" }, fn: "gate" },
   { id: "C", path: "/w/f.txt", realpath: { ok: "/w/f.txt" }, fn: "ok" }],
  async ({ gates, flush }) => { await flush(); gates["fn:A"].resolve(); await flush(); gates["fn:B"].resolve(); }));

writeFileSync(process.argv[2], JSON.stringify({ engine: "node+pi-file-mutation-queue", node: process.versions.node, results }, null, 1));
console.log(`queue authority: ${results.length} scenarios`);
