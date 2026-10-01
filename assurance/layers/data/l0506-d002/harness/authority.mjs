// L0506-D002 authority: pinned Pi b7bb00b9's prepared JavaScript STRING domain through its own Layer-05/06 path,
// under Node 22.15.1 + typebox 1.3.7. Unlike the L0506-D001 authority, the agent-loop steps are not paraphrased:
// agent-loop.ts' prepareToolCallArguments, prepareToolCall, executePreparedToolCall, finalizeExecutedToolCall and
// createErrorToolResult are sliced from the pinned source at run time (erasable TypeScript annotations stripped by
// node:module stripTypeScriptTypes) and run with Pi's unmodified validateToolArguments. For each case:
//   prepareToolCall (prepareArguments -> validateToolArguments -> config.beforeToolCall)
//   -> executePreparedToolCall (tool.execute) -> finalizeExecutedToolCall (config.afterToolCall)
// Observed: the UTF-16 code units at each `observe` pointer as beforeToolCall's `args`, execute's arguments and
// afterToolCall's `args` see them (and whether the three are the same object), object keys at each `observe_keys`
// pointer, and, SEPARATELY, the projections: UTF-8 bytes (Buffer.from(s, "utf8"), which is fs.writeFile(p, s,
// "utf-8")) and JSON.stringify. On a validation failure: Pi's diagnostic text and the untouched prepared values.
import { readFileSync, writeFileSync } from "node:fs";
import { stripTypeScriptTypes } from "node:module";
import { Type } from "typebox";
import { validateToolArguments } from "./pi/ai/src/utils/validation.ts";

const slice = (source, from, to) => {
  const start = source.indexOf(from);
  const end = source.indexOf(to, start);
  if (start < 0 || end < 0) throw new Error(`slice ${from}`);
  return source.slice(start, end);
};

const loopSource = readFileSync("./pi/agent/src/agent-loop.ts", "utf8");
const loop = new Function(
  "validateToolArguments",
  stripTypeScriptTypes(slice(loopSource, "function prepareToolCallArguments(", "async function emitToolExecutionEnd(")) +
    "\nreturn { prepareToolCall, executePreparedToolCall, finalizeExecutedToolCall };",
)(validateToolArguments);

const editSource = readFileSync("./pi/coding-agent/src/core/tools/edit.ts", "utf8");
const editSchema = new Function("Type", slice(editSource, "const replaceEditSchema", "export const editToolSystemPromptContribution") +
  "\nreturn editSchema;")(Type);
const prepareEditArguments = new Function(stripTypeScriptTypes(
  slice(editSource, "function isSingleEditInput(", "export interface EditToolDetails") +
  slice(editSource, "function prepareEditArguments(", "function validateEditInput(")) +
  "\nreturn prepareEditArguments;")();

const S = (units) => String.fromCharCode(...units);
const U = (s) => Array.from({ length: s.length }, (_, i) => s.charCodeAt(i));
const SCHEMAS = {
  open: { type: "object", properties: {} },
  string: { type: "object", properties: { text: { type: "string" } }, required: ["text"] },
  "min-length-2": { type: "object", properties: { text: { type: "string", minLength: 2 } } },
  "max-length-1": { type: "object", properties: { text: { type: "string", maxLength: 1 } } },
  "pattern-one-char": { type: "object", properties: { text: { type: "string", pattern: "^.$" } } },
  "pattern-two-chars": { type: "object", properties: { text: { type: "string", pattern: "^..$" } } },
  "const-pair": { type: "object", properties: { text: { const: S([0xd83d, 0xde00]) } } },
  // L0506-D002-R001: scalar schema literals only (a lone surrogate in the schema is L05-D001's domain)
  "enum-fffd": { type: "object", properties: { text: { enum: [S([0xfffd])] } } },
};

// a prepare_set value: {"utf16": [...]} is a string; {"$key": [...], "value": v} an object with that one key
const decode = (v) =>
  Array.isArray(v) ? v.map(decode)
  : v && typeof v === "object"
    ? ("utf16" in v ? S(v.utf16)
      : "$key" in v ? { [S(v.$key)]: decode(v.value) }
      : Object.fromEntries(Object.entries(v).map(([k, x]) => [k, decode(x)])))
  : v;
const at = (obj, pointer) => pointer.split("/").slice(1).reduce((o, k) => (o == null ? undefined : o[k]), obj);
const observe = (c, args) => ({
  values: Object.fromEntries(c.observe.map((p) => {
    const v = at(args, p);
    return [p, typeof v === "string" ? U(v) : { non_string: JSON.stringify(v) }];
  })),
  keys: Object.fromEntries((c.observe_keys ?? []).map((p) => [p, Object.keys(at(args, p)).map(U)])),
});
const projections = (c, args) => Object.fromEntries(c.observe.map((p) => {
  const v = at(args, p);
  return [p, { utf8_hex: Buffer.from(v, "utf8").toString("hex"), json: JSON.stringify(v) }];
}));

const cases = JSON.parse(readFileSync(process.argv[2], "utf8"));
const results = [];
for (const c of cases) {
  const seen = {};
  let prepared;
  const tool = c.tool === "edit"
    ? { name: "edit", parameters: editSchema,
        prepareArguments: (a) => (prepared = prepareEditArguments(a)),
        execute: async (_id, args) => { seen.execute = args; return { content: [{ type: "text", text: "ok" }], details: {} }; } }
    : { name: "probe", parameters: SCHEMAS[c.schema],
        prepareArguments: (a) => (prepared = { ...a, ...Object.fromEntries(Object.entries(c.prepare_set).map(([p, v]) => [p.slice(1), decode(v)])) }),
        execute: async (_id, args) => { seen.execute = args; return { content: [{ type: "text", text: "ok" }], details: {} }; } };
  const config = {
    beforeToolCall: async ({ args }) => { seen.before = args; return undefined; },
    afterToolCall: async ({ args }) => { seen.after = args; return undefined; },
  };
  const raw = JSON.parse(JSON.stringify(c.arguments));
  const toolCall = { type: "toolCall", id: "call-1", name: tool.name, arguments: raw };
  const context = { systemPrompt: "", messages: [], tools: [tool] };
  const preparation = await loop.prepareToolCall(context, {}, toolCall, config, undefined);
  if (preparation.kind === "prepared") {
    const executed = await loop.executePreparedToolCall(preparation, undefined, async () => {});
    await loop.finalizeExecutedToolCall(context, {}, preparation, executed, config, undefined);
    results.push({
      id: c.id, outcome: "prepared",
      hook: observe(c, seen.before), execute: observe(c, seen.execute), after: observe(c, seen.after),
      same_object: seen.before === seen.execute && seen.execute === seen.after,
      projections: projections(c, seen.execute),
      raw_unchanged: JSON.stringify(raw) === JSON.stringify(c.arguments),
    });
  } else {
    const text = preparation.result.content[0].text;
    const marker = "Received arguments:\n";
    results.push({
      id: c.id, outcome: "argument_validation_failure", message: text.split("\n")[1]?.trim(),
      hook_ran: "before" in seen, execute_ran: "execute" in seen,
      diagnostic_arguments_text: text.slice(text.indexOf(marker) + marker.length),
      runtime_after_failure: observe(c, prepared),
    });
  }
}
writeFileSync(process.argv[3], JSON.stringify({ node: process.versions.node, results }, null, 1) + "\n");
console.log(`authority: ${results.length} results`);
for (const r of results) console.log(r.id.padEnd(36), r.outcome, r.outcome === "prepared" ? r.same_object : r.message);
