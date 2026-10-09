// L0506-D005 (minion-agent#129) canonical authority: gen/cases.json through pinned Pi b7bb00b9's own code, sliced
// unmodified on the K1 staging (agent-loop.ts prepareToolCall/executePreparedToolCall; validation.ts
// validateToolArguments = structuredClone + typebox 1.3.7). Staged and run by ../harness/run.sh.
//   node --experimental-strip-types pi_oracle.mjs <cases.json> <out.json>
// Hooks: Pi has one beforeToolCall. A case's `hooks` (a list of programs) run in order inside it, each entry
// observed: the Minion waterfall's listeners map onto that one hook, sharing the arguments object (a mapping,
// labeled as such in spec/tools.md L0506-D005).
// Named shims (prepareArguments), the language-neutral fixture vocabulary:
//   alias           -> x = {k: 1}; return {p: x, q: x}
//   cycle           -> o = {k: 1}; o.self = o; return o
//   non-finite      -> return {...raw, nan: NaN, inf: Infinity, ninf: -Infinity, nz: -0}
//   reuse-raw-child -> return {o: raw.o, extra: 1}   (the raw object itself is not mutated)
import { readFileSync, writeFileSync } from "node:fs";
import { stripTypeScriptTypes } from "node:module";
import { validateToolArguments } from "./pi/ai/src/utils/validation.ts";

const slice = (src, from, to) => { const a = src.indexOf(from), b = src.indexOf(to, a);
  if (a < 0 || b < 0) throw new Error(`slice ${from}`); return src.slice(a, b); };
const loopSource = readFileSync("./pi/agent/src/agent-loop.ts", "utf8");
const loop = new Function("validateToolArguments", stripTypeScriptTypes(
  slice(loopSource, "function prepareToolCallArguments(", "async function emitToolExecutionEnd(")) +
  "\nreturn { prepareToolCall, executePreparedToolCall };")(validateToolArguments);

const obs = (v, stack = []) => {
  if (typeof v === "number") return { n: Object.is(v, -0) ? "-0" : String(v) };
  if (typeof v === "string") return { u: Array.from({ length: v.length }, (_, i) => v.charCodeAt(i)) };
  if (v === null || typeof v !== "object") return v;
  if (stack.includes(v)) return { cycle: stack.length - stack.indexOf(v) };  // levels up to the referenced ancestor
  const next = [...stack, v];
  return Array.isArray(v) ? { a: v.map((x) => obs(x, next)) } : { o: Object.keys(v).map((k) => [k, obs(v[k], next)]) };
};
const build = (g) => {
  if (g === null || typeof g !== "object") return g;
  if ("n" in g) return Number(g.n === "-0" ? "-0" : g.n);
  if ("u" in g) return String.fromCharCode(...g.u);
  if ("a" in g) return g.a.map(build);
  return g.o.reduce((acc, [k, x]) => { acc[k] = build(x); return acc; }, {});
};
const at = (root, path) => path.reduce((value, key) => value?.[key], root);
const run = (args, program) => {
  for (const op of program) {
    const target = at(args, op.path);
    if (op.op === "set") target[op.key] = build(op.value);
    else if (op.op === "push") target.push(build(op.value));
    else if (op.op === "delete") delete target[op.key];
    else throw new Error(`op ${op.op}`);
  }
};
const SHIMS = {
  alias: () => { const x = { k: 1 }; return { p: x, q: x }; },
  cycle: () => { const o = { k: 1 }; o.self = o; return o; },
  "non-finite": (raw) => ({ ...raw, nan: NaN, inf: Infinity, ninf: -Infinity, nz: -0 }),
  "reuse-raw-child": (raw) => ({ o: raw.o, extra: 1 }),
};

const cases = JSON.parse(readFileSync(process.argv[2], "utf8")).cases;
const results = [];
for (const c of cases) {
  const raw = JSON.parse(c.text);
  const seen = { hook_entries: [] };
  const tool = { name: "probe", parameters: c.schema ?? { type: "object", properties: {} },
    ...(c.prepare ? { prepareArguments: SHIMS[c.prepare] } : {}),
    execute: async (_id, args, _signal, onUpdate) => {
      seen.execute = obs(args);
      onUpdate({ content: [], details: {} });
      return { content: [], details: {} }; } };
  const config = { beforeToolCall: async ({ args }) => {
    seen.facts = (c.facts ?? []).map((f) => "same" in f ? at(args, f.same[0]) === at(args, f.same[1])
                                                        : at(args, f.distinct_from_raw) !== at(raw, f.distinct_from_raw));
    for (const program of c.hooks) { seen.hook_entries.push(obs(args)); run(args, program); }
    return c.block ? { block: true, reason: "blocked" } : undefined; } };
  const call = { type: "toolCall", id: "c1", name: "probe", arguments: raw };
  const updates = [];
  const prep = await loop.prepareToolCall({ systemPrompt: "", messages: [], tools: [tool] }, {}, call, config, undefined);
  if (prep.kind === "prepared") {
    await loop.executePreparedToolCall(prep, undefined, async (e) => { if (e.type === "tool_execution_update") updates.push(obs(e.args)); });
  }
  results.push({ id: c.id, outcome: prep.kind === "prepared" ? "executed" : "immediate_error",
    hook_entries: seen.hook_entries, facts: seen.facts ?? null, execute: seen.execute ?? null, updates, raw_after: obs(raw) });
}
writeFileSync(process.argv[3], JSON.stringify({ node: process.versions.node, pi: "b7bb00b936dbe21b8e160b3e89efdec361846699", results }, null, 1) + "\n");
console.log(`l0506-d005 oracle: ${results.length} cases`);
