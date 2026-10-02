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

const obs = (v) => Array.isArray(v) ? { a: v.map(obs) } : v && typeof v === "object"
  ? { o: Object.keys(v).map((k) => [k, obs(v[k])]) } : v;

const cases = JSON.parse(readFileSync(process.argv[2], "utf8"));
const results = [];
for (const c of cases) {
  const raw = JSON.parse(c.provider_text);
  const out = { id: c.id, raw: obs(raw) };
  const persisted = JSON.stringify(raw);
  out.persisted = persisted;
  out.replay = obs(JSON.parse(persisted));
  const seen = {};
  const tool = { name: "probe", parameters: c.schema === "edit" ? EDIT_SCHEMA : c.schema,
    ...(c.prepare === "edit" ? { prepareArguments: prepareEditArguments } : {}),
    execute: async (_id, args) => { seen.execute = obs(args); return { content: [], details: {} }; } };
  const config = { beforeToolCall: async ({ args }) => {
    seen.hook = obs(args);
    for (const [k, v] of c.mutate ?? []) args[k] = v;
    return undefined; } };
  const call = { type: "toolCall", id: "c1", name: "probe", arguments: raw };
  const prep = await loop.prepareToolCall({ systemPrompt: "", messages: [], tools: [tool] }, {}, call, config, undefined);
  if (prep.kind !== "prepared") throw new Error(`${c.id}: not prepared: ${JSON.stringify(prep.result?.content)}`);
  await loop.executePreparedToolCall(prep, undefined, async () => {});
  out.hook = seen.hook;
  out.execute = seen.execute;
  out.raw_unchanged_by_preparation = JSON.stringify(obs(call.arguments)) === JSON.stringify(out.raw);
  if (c.replace_text) out.replacement = obs(JSON.parse(c.replace_text));
  results.push(out);
}
writeFileSync(process.argv[3], JSON.stringify({ node: process.versions.node, results }, null, 1) + "\n");
console.log(`k1 boundaries: ${results.length} cases`);
