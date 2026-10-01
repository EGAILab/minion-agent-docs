// L0206-D002 (raw string domain, Q001) and L0206-D001 (K1 key order) characterization: pinned Pi b7bb00b9's RAW
// ToolCall.arguments value domain across its boundaries, under Node 22.15.1 + typebox 1.3.7.
//   decode   ai/src/utils/json-parse.ts parseJsonWithRepair (+ repairJson), sliced from source: what a provider's
//            final tool-call argument text becomes (parseStreamingJson tries parseJsonWithRepair first)
//   persist  coding-agent session-manager.ts:1021 `${JSON.stringify(entry)}\n` (a message entry holding the call)
//   replay   session-manager.ts:306 `JSON.parse(line)`
//   pipeline agent-loop.ts prepareToolCall/executePreparedToolCall/finalizeExecutedToolCall, sliced from source,
//            for a tool WITHOUT prepareArguments (open schema): what beforeToolCall / execute observe
// Strings are rendered as UTF-16 code units, numbers as tokens ("+Infinity", "-0", Number::toString ...), and every
// object as its key enumeration order (recursively), so K1 and Q001 read the same observations.
import { readFileSync, writeFileSync } from "node:fs";
import { stripTypeScriptTypes } from "node:module";
import { validateToolArguments } from "./pi/ai/src/utils/validation.ts";

const slice = (source, from, to) => {
  const start = source.indexOf(from);
  const end = source.indexOf(to, start);
  if (start < 0 || end < 0) throw new Error(`slice ${from}`);
  return source.slice(start, end);
};
const jsonSource = readFileSync("./pi/ai/src/utils/json-parse.ts", "utf8");
const { parseJsonWithRepair } = new Function(stripTypeScriptTypes(
  slice(jsonSource, "const VALID_JSON_ESCAPES", "/**\n * Attempts to parse potentially incomplete JSON")
    .replace(/^export /gm, "")) + // module syntax only: `new Function` cannot hold an export
  "\nreturn { parseJsonWithRepair };")();
const loopSource = readFileSync("./pi/agent/src/agent-loop.ts", "utf8");
const loop = new Function("validateToolArguments", stripTypeScriptTypes(
  slice(loopSource, "function prepareToolCallArguments(", "async function emitToolExecutionEnd(")) +
  "\nreturn { prepareToolCall, executePreparedToolCall, finalizeExecutedToolCall };")(validateToolArguments);

const U = (s) => Array.from({ length: s.length }, (_, i) => s.charCodeAt(i));
const token = (v) => Number.isNaN(v) ? "NaN" : v === Infinity ? "+Infinity" : v === -Infinity ? "-Infinity"
  : Object.is(v, -0) ? "-0" : String(v);
// a value as a JSON-safe observation: strings -> {u: units}, numbers -> {n: token}, objects keep enumeration order
const obs = (v) =>
  typeof v === "string" ? { u: U(v) }
  : typeof v === "number" ? { n: token(v) }
  : Array.isArray(v) ? { a: v.map(obs) }
  : v && typeof v === "object" ? { o: Object.keys(v).map((k) => [U(k), obs(v[k])]) }
  : { v };

const cases = JSON.parse(readFileSync(process.argv[2], "utf8"));
const results = [];
for (const c of cases) {
  let raw;
  try {
    raw = parseJsonWithRepair(c.text);
  } catch (error) {
    results.push({ id: c.id, decode: "error", message: String(error.message) });
    continue;
  }
  const call = { type: "toolCall", id: "call-1", name: "probe", arguments: raw };
  const entry = { type: "message", message: { role: "assistant", content: [call] } };
  const line = `${JSON.stringify(entry)}\n`;
  const replayed = JSON.parse(line).message.content[0].arguments;
  const seen = {};
  const tool = { name: "probe", parameters: { type: "object", properties: {} },
                 execute: async (_id, args) => { seen.execute = args; return { content: [], details: {} }; } };
  const config = { beforeToolCall: async ({ args }) => { seen.before = args; return undefined; } };
  const context = { systemPrompt: "", messages: [], tools: [tool] };
  const preparation = await loop.prepareToolCall(context, {}, call, config, undefined);
  let pipeline;
  if (preparation.kind === "prepared") {
    const executed = await loop.executePreparedToolCall(preparation, undefined, async () => {});
    await loop.finalizeExecutedToolCall(context, {}, preparation, executed, config, undefined);
    pipeline = { outcome: "prepared", hook: obs(seen.before), execute: obs(seen.execute),
                 hook_is_raw_object: seen.before === raw, execute_is_hook_object: seen.execute === seen.before };
  } else {
    pipeline = { outcome: "error", message: preparation.result.content[0].text.split("\n")[0] };
  }
  results.push({
    id: c.id, decode: obs(raw),
    persisted_line: line.slice(0, -1),
    persisted_utf8_hex: Buffer.from(line, "utf8").toString("hex"),
    replay: obs(replayed),
    pipeline,
  });
}
writeFileSync(process.argv[3], JSON.stringify({ node: process.versions.node, results }, null, 1) + "\n");
console.log(`raw probe: ${results.length} results`);
