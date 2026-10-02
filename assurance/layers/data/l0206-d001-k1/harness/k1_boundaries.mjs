// L0206-D001 (K1, minion-agent#100) canonical authority: for each make_cases.py case, the recursive key enumeration
// order pinned Pi b7bb00b9 exposes at every argument boundary. Pi's own code, sliced unmodified (pi_sources.sha256):
//   agent-loop.ts prepareToolCall/executePreparedToolCall/finalizeExecutedToolCall, validation.ts
//   validateToolArguments (typebox 1.3.7), edit.ts prepareEditArguments + its schema.
// Boundaries observed: raw (JSON.parse of the provider text, as parseJsonWithRepair yields for valid JSON),
// persisted (JSON.stringify text) and replay (JSON.parse of it), hook (beforeToolCall entry), execute (the object
// execute receives, after any in-place hook mutation). A `replace` case has no Pi boundary (Pi's beforeToolCall
// cannot replace arguments): its `replacement` observation is ECMAScript's own order for the replacement object,
// the expectation for Minion's replacement mapping.
//   node --experimental-strip-types k1_boundaries.mjs <cases.json> <out.json>
import { readFileSync, writeFileSync } from "node:fs";
import { stripTypeScriptTypes } from "node:module";
import { validateToolArguments } from "./pi/ai/src/utils/validation.ts";

const slice = (src, from, to) => { const a = src.indexOf(from), b = src.indexOf(to, a);
  if (a < 0 || b < 0) throw new Error(`slice ${from}`); return src.slice(a, b); };
const loopSource = readFileSync("./pi/agent/src/agent-loop.ts", "utf8");
const loop = new Function("validateToolArguments", stripTypeScriptTypes(
  slice(loopSource, "function prepareToolCallArguments(", "async function emitToolExecutionEnd(")) +
  "\nreturn { prepareToolCall, executePreparedToolCall, finalizeExecutedToolCall };")(validateToolArguments);
const editSource = readFileSync("./pi/coding-agent/src/core/tools/edit.ts", "utf8");
const prepareEditArguments = new Function(stripTypeScriptTypes(
  slice(editSource, "function isSingleEditInput(", "export interface EditToolDetails") +
  slice(editSource, "function prepareEditArguments(", "function validateEditInput(")) + "\nreturn prepareEditArguments;")();
const S = { type: "string" };
const EDIT_SCHEMA = { type: "object", required: ["path", "edits"], properties: { path: S, edits: { type: "array",
  items: { type: "object", required: ["oldText", "newText"], properties: { oldText: S, newText: S } } } } };

// A case value in the insertion grammar ({"$o": [[k, v], ...]}) as a JavaScript value, objects built by assignment.
const build = (v) => Array.isArray(v) ? v.map(build) : v && typeof v === "object"
  ? v.$o.reduce((acc, [k, x]) => { acc[k] = build(x); return acc; }, {}) : v;
// The mutation program (make_cases.py): ops on the real arguments object, by target handle.
function runProgram(args, program, reads = []) {
  const handles = { args };
  for (const op of program ?? []) {
    if (op.op === "read") { reads.push(obs(op.path.reduce((value, k) => value[k], args))); continue; }
    const target = handles[op.target];
    if (op.op === "extend") { target[op.key].push(...op.values.map(build)); continue; }
    const value = "ref" in op ? handles[op.ref] : build(op.value);
    if (op.op === "set") target[op.key] = value;
    else if (op.op === "push") target[op.key].push(value);
    else if (op.op === "insert") target[op.key].splice(op.index, 0, value);
    else if (op.op === "replace") target[op.key][op.index] = value;
    else if (op.op === "get") { handles[op.as] = target[op.key]; continue; }
    else throw new Error(`op ${op.op}`);
    if (op.as) handles[op.as] = value;
  }
}

const obs = (v) => Array.isArray(v) ? { a: v.map(obs) } : v && typeof v === "object"
  ? { o: Object.keys(v).map((k) => [k, obs(v[k])]) } : v;

const cases = JSON.parse(readFileSync(process.argv[2], "utf8"));
const results = [];
for (const c of cases) {
  const raw = JSON.parse(c.provider_text);
  const out = { id: c.id, raw: obs(raw) };
  runProgram(raw, c.raw_program);  // L0206-D001-R004: the raw object mutated after construction
  const persisted = JSON.stringify(raw);
  out.persisted = persisted;
  out.replay = obs(JSON.parse(persisted));
  const seen = {};
  const tool = { name: "probe", parameters: c.schema === "edit" ? EDIT_SCHEMA : c.schema,
    ...(c.prepare === "edit" ? { prepareArguments: prepareEditArguments } : {}),
    execute: async (_id, args) => { seen.execute = obs(args);
                                     runProgram(seen.prepared.toolCall.arguments, c.update_program);
                                     seen.update = obs(seen.prepared.toolCall.arguments);
                                     return { content: [], details: {} }; } };
  const config = { beforeToolCall: async ({ args }) => {
    seen.hook = obs(args);
    for (const [k, v] of c.mutate ?? []) args[k] = v;
    seen.reads = [];
    runProgram(args, c.program, seen.reads);
    if (c.observe_second) seen.second = obs(args);
    return undefined; } };
  const call = { type: "toolCall", id: "c1", name: "probe", arguments: raw };
  runProgram(call.arguments, c.start_program);  // a tool_execution_start listener's mutation of the raw object
  out.start = obs(call.arguments);  // tool_execution_start args: the raw object (agent-loop emits toolCall.arguments)
  const prep = await loop.prepareToolCall({ systemPrompt: "", messages: [], tools: [tool] }, {}, call, config, undefined);
  seen.prepared = prep;  // tool_execution_update args: prepared.toolCall.arguments
  if (prep.kind !== "prepared") throw new Error(`${c.id}: not prepared: ${JSON.stringify(prep.result?.content)}`);
  await loop.executePreparedToolCall(prep, undefined, async () => {});
  out.hook = seen.hook;
  out.execute = seen.execute;
  out.update = seen.update;
  if (c.observe_second) out.second = seen.second;
  if (seen.reads.length) out.hook_reads = seen.reads;
  out.raw_unchanged_by_preparation = JSON.stringify(obs(call.arguments)) === JSON.stringify(out.raw);
  if (c.replace_text) out.replacement = obs(JSON.parse(c.replace_text));
  results.push(out);
}
writeFileSync(process.argv[3], JSON.stringify({ node: process.versions.node, results }, null, 1) + "\n");
console.log(`k1 boundaries: ${results.length} cases`);
