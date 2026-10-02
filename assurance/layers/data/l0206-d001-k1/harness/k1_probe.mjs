// L0206-D001 (K1, minion-agent#100) boundary characterization beyond the L0206 raw probe: does any boundary of pinned
// Pi b7bb00b9 reorder tool-argument object keys other than by ECMAScript's own rule? Pi's own code, sliced unmodified:
//   validation.ts validateToolArguments (structuredClone + typebox 1.3.7 Value.Convert against the tool's schema)
//   agent-loop.ts prepareToolCall/executePreparedToolCall/finalizeExecutedToolCall (beforeToolCall, execute)
//   edit.ts prepareEditArguments + editSchema (nested `edits` objects re-parsed from a string)
// Observation: every object rendered as its key enumeration order, recursively ({o: [[key, value]...]}).
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

const obs = (v) => Array.isArray(v) ? { a: v.map(obs) } : v && typeof v === "object"
  ? { o: Object.keys(v).map((k) => [k, obs(v[k])]) } : v;
const S = { type: "string" };
const SCHEMAS = {
  open: { type: "object", properties: {} },
  "declared-z-a": { type: "object", properties: { z: S, a: S } },
  "declared-index": { type: "object", properties: { b: S, 1: S } },
  "declared-nested": { type: "object", properties: { o: { type: "object", properties: { z: S, a: S } } } },
  "declared-number": { type: "object", properties: { n: { type: "number" }, a: S } },
  edit: { type: "object", required: ["path", "edits"], properties: { path: S, edits: { type: "array", items: {
    type: "object", required: ["oldText", "newText"], properties: { oldText: S, newText: S } } } } },
};
const CASES = [
  ["open/mixed", "open", '{"b":"x","2":"y","1":"z"}'],
  ["declared-z-a/insertion-a-z", "declared-z-a", '{"a":"x","z":"y"}'],
  ["declared-z-a/insertion-z-a", "declared-z-a", '{"z":"y","a":"x"}'],
  ["declared-z-a/with-extras", "declared-z-a", '{"extra":"e","a":"x","10":"t","z":"y","1":"o"}'],
  ["declared-index/insertion", "declared-index", '{"b":"x","1":"y","c":"z"}'],
  ["declared-nested/inner-reversed", "declared-nested", '{"o":{"a":"x","z":"y","2":"i"}}'],
  ["declared-number/convert", "declared-number", '{"a":"x","n":"5"}'],
  ["invalid/diagnostic", "declared-z-a", '{"b":1,"2":2,"1":3,"z":{"q":1,"0":2}}'],
  ["edit/nested-edits-string", "edit", '{"path":"f.txt","edits":"[{\\"newText\\":\\"b\\",\\"1\\":\\"i\\",\\"oldText\\":\\"a\\"}]"}'],
];

const results = [];
for (const [id, schemaName, text] of CASES) {
  const raw = JSON.parse(text);
  const seen = {};
  const tool = { name: "probe", parameters: SCHEMAS[schemaName],
    ...(schemaName === "edit" ? { prepareArguments: prepareEditArguments } : {}),
    execute: async (_id, args) => { seen.execute = obs(args); seen.execute_is_hook = args === seen.hookObj;
                                     return { content: [], details: {} }; } };
  const config = { beforeToolCall: async ({ args }) => {
    seen.hook = obs(args); seen.hookObj = args;
    if (id === "open/mixed") { args.c = "added"; args["0"] = "added-index"; }   // hook mutation (reachable in Pi)
    return undefined; } };
  const call = { type: "toolCall", id: "c1", name: "probe", arguments: raw };
  const prep = await loop.prepareToolCall({ systemPrompt: "", messages: [], tools: [tool] }, {}, call, config, undefined);
  const out = { id, schema: schemaName, raw: obs(raw), stringify: JSON.stringify(raw) };
  if (prep.kind === "prepared") {
    await loop.executePreparedToolCall(prep, undefined, async () => {});
    Object.assign(out, { hook: seen.hook, execute: seen.execute, execute_is_hook_object: seen.execute_is_hook,
                         validated_is_raw_object: seen.hookObj === raw });
  } else {
    out.error_text = prep.result.content[0].text;
  }
  results.push(out);
}
writeFileSync(process.argv[2], JSON.stringify({ node: process.versions.node, results }, null, 1) + "\n");
console.log(`k1 probe: ${results.length} cases`);
