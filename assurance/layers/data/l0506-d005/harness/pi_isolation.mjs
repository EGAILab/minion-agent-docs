// L0506-D005 (minion-agent#129) characterization: value isolation between a tool call's RAW arguments and the
// VALIDATED arguments that beforeToolCall and execute receive, in pinned Pi b7bb00b9. Pi's own code, sliced unmodified
// (the K1 staging, ../l0206-d001-k1/harness/pi_sources.sha256): agent-loop.ts prepareToolCall/executePreparedToolCall,
// validation.ts validateToolArguments (structuredClone + typebox 1.3.7).
//   node --experimental-strip-types pi_isolation.mjs <out.json>
// Observation: objects as their key enumeration ({o: [[key, value]...]}), arrays ({a: [...]}); numbers as
// {n: String(x)} with -0 marked; strings as their UTF-16 code units; identity facts as booleans.
import { writeFileSync, readFileSync } from "node:fs";
import { stripTypeScriptTypes } from "node:module";
import { validateToolArguments } from "./pi/ai/src/utils/validation.ts";

const slice = (src, from, to) => { const a = src.indexOf(from), b = src.indexOf(to, a);
  if (a < 0 || b < 0) throw new Error(`slice ${from}`); return src.slice(a, b); };
const loopSource = readFileSync("./pi/agent/src/agent-loop.ts", "utf8");
const loop = new Function("validateToolArguments", stripTypeScriptTypes(
  slice(loopSource, "function prepareToolCallArguments(", "async function emitToolExecutionEnd(")) +
  "\nreturn { prepareToolCall, executePreparedToolCall };")(validateToolArguments);

const obs = (v, seen = new Set()) => {
  if (typeof v === "number") return { n: Object.is(v, -0) ? "-0" : String(v) };
  if (typeof v === "string") return { u: Array.from({ length: v.length }, (_, i) => v.charCodeAt(i)) };
  if (v === null || typeof v !== "object") return v;
  if (seen.has(v)) return { cycle: true };
  seen.add(v);
  const out = Array.isArray(v) ? { a: v.map((x) => obs(x, seen)) } : { o: Object.keys(v).map((k) => [k, obs(v[k], seen)]) };
  seen.delete(v);
  return out;
};

const OPEN = { type: "object", properties: {} };
const CASES = [
  // A: a hook mutates a nested object.
  { id: "hook-sets-into-nested-object", text: '{"o":{"z":1}}', hook: (a) => { a.o.y = 2; } },
  // B: a hook pushes an object into a nested array.
  { id: "hook-pushes-object-into-nested-array", text: '{"a":[]}', hook: (a) => { a.a.push({ b: 2, 1: 1 }); } },
  // K1 corpus shape: a nested existing object gains an index key.
  { id: "hook-nested-existing-gains-index", text: '{"o":{"z":1,"y":2}}', hook: (a) => { a.o["0"] = 0; } },
  // A hook replaces a nested value and deletes another.
  { id: "hook-replaces-and-deletes-nested", text: '{"o":{"k":1,"d":2},"l":[1,[2]]}',
    hook: (a) => { a.o.k = 9; delete a.o.d; a.l[1].push(3); } },
  // G: aliases and cycles inside the prepared graph (a shim is the only producer; JSON text has none).
  { id: "prepared-alias-stays-shared-in-clone", text: '{}',
    prepare: () => { const x = { k: 1 }; return { p: x, q: x }; },
    hook: (a) => { a.p.k = 2; }, facts: (a, prepared) => ({ p_is_q: a.p === a.q, p_is_prepared_p: a.p === prepared.p }) },
  { id: "prepared-cycle-survives-clone", text: '{}',
    prepare: () => { const o = { k: 1 }; o.self = o; return o; },
    facts: (a, prepared) => ({ self_is_args: a.self === a, args_is_prepared: a === prepared }) },
  // I: runtime values survive the clone unnormalized.
  { id: "values-survive-clone", text: '{"z":-0,"s":"\\ud800x","t":"\\udc00"}',
    prepare: (raw) => ({ ...raw, nan: NaN, inf: Infinity, ninf: -Infinity, nz: -0 }) },
  // J: validation failure and a blocked call.
  { id: "validation-failure", text: '{"o":{"z":1}}', schema: { type: "object", required: ["missing"], properties: {} },
    hook: (a) => { a.o.y = 2; } },
  { id: "blocked-after-nested-mutation", text: '{"o":{"z":1}}', hook: (a) => { a.o.y = 2; return { block: true, reason: "no" }; } },
  // Adjacent prepareArguments boundary (characterized only): the shim receives the RAW object itself.
  { id: "prepare-receives-raw-object", text: '{"o":{"z":1},"t":1}',
    prepare: (raw) => { raw.o.shim = 1; raw.t = 2; return { o: raw.o, extra: 1 }; } },
];

const results = [];
for (const c of CASES) {
  const raw = JSON.parse(c.text);
  const rawO = raw.o;
  const seen = {};
  let prepared;
  const tool = { name: "probe", parameters: c.schema ?? OPEN,
    ...(c.prepare ? { prepareArguments: (args) => (prepared = c.prepare(args)) } : {}),
    execute: async (_id, args, _signal, onUpdate) => {
      seen.execute = obs(args);
      seen.execute_is_hook = args === seen.hookArgs;
      onUpdate({ content: [], details: {} });
      return { content: [], details: {} }; } };
  const config = { beforeToolCall: async ({ args, toolCall }) => {
    seen.hookArgs = args;
    seen.hook_entry = obs(args);
    seen.hook_args_is_raw = args === raw;
    seen.hook_tool_call_arguments_is_raw = toolCall.arguments === raw;
    seen.hook_o_is_raw_o = rawO !== undefined && args.o === rawO;
    const r = c.hook ? c.hook(args) : undefined;
    if (c.facts) seen.facts = c.facts(args, prepared);
    return r; } };
  const call = { type: "toolCall", id: "c1", name: "probe", arguments: raw };
  const updates = [];
  const prep = await loop.prepareToolCall({ systemPrompt: "", messages: [], tools: [tool] }, {}, call, config, undefined);
  const out = { id: c.id, kind: prep.kind };
  if (prep.kind === "prepared") {
    await loop.executePreparedToolCall(prep, undefined, async (e) => { if (e.type === "tool_execution_update") updates.push(obs(e.args)); });
    out.update_args = updates;
    out.update_args_is_raw = prep.toolCall.arguments === raw;
  } else {
    out.error = prep.result.content.map((p) => p.text).join("");
  }
  Object.assign(out, { hook_entry: seen.hook_entry, execute: seen.execute, execute_is_hook_args: seen.execute_is_hook,
    hook_args_is_raw: seen.hook_args_is_raw, hook_tool_call_arguments_is_raw: seen.hook_tool_call_arguments_is_raw,
    hook_o_is_raw_o: seen.hook_o_is_raw_o, facts: seen.facts, raw_after: obs(raw), raw_text: c.text });
  results.push(out);
}
writeFileSync(process.argv[2], JSON.stringify({ node: process.versions.node, pi: "b7bb00b936dbe21b8e160b3e89efdec361846699", results }, null, 1) + "\n");
console.log(`l0506-d005 isolation: ${results.length} cases`);
