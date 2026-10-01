// L0506-D003 characterization (Owner decision WP132-RUST-C002-Q001): pinned Pi b7bb00b9's TOOL-RESULT runtime value
// domain across its boundaries, under Node 22.15.1 + typebox 1.3.7 + diff 8.0.4.
//   pipeline  agent-loop.ts executeToolCalls/executeToolCallsSequential + shouldTerminateToolBatch ..
//             emitToolResultMessage, sliced from source (toolExecution "sequential"): a custom tool's result, the
//             afterToolCall hook (what it receives; what it may replace), tool_execution_end, the ToolResultMessage
//             and its message_start/message_end events
//   persist   coding-agent session-manager.ts:1021 `${JSON.stringify(entry)}\n` (a message entry holding the result)
//   reload    session-manager.ts parseSessionEntries (sliced from source): `JSON.parse(line)`
//   witness   the WP-13.2 edit witness: edit.ts prepareEditArguments + edit-diff.ts applyEditsToNormalizedContent /
//             generateDiffString / generateUnifiedPatch (sliced), the result in edit.ts:377-383's literal shape,
//             then the same pipeline
// Strings are rendered as UTF-16 code units, numbers as tokens ("+Infinity", "-0", "NaN", Number::toString ...),
// objects as their key enumeration order (recursively), undefined as {undef: true}.
import { readFileSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { stripTypeScriptTypes } from "node:module";
import { validateToolArguments } from "./pi/ai/src/utils/validation.ts";

// Determinism only: createToolResultMessage stamps `timestamp: Date.now()`, which would make the persisted line (and
// so this authority's output) differ per run. No value under characterization depends on the clock.
Date.now = () => 0;

const slice = (source, from, to) => {
  const start = source.indexOf(from);
  const end = to === null ? source.length : source.indexOf(to, start);
  if (start < 0 || end < 0) throw new Error(`slice ${from}`);
  return source.slice(start, end);
};
const strip = (code) => stripTypeScriptTypes(code).replace(/^export /gm, "");

const loopSource = readFileSync("./pi/agent/src/agent-loop.ts", "utf8");
const loop = new Function("validateToolArguments", strip(
  slice(loopSource, "async function executeToolCalls(", "async function executeToolCallsParallel(") +
  slice(loopSource, "function shouldTerminateToolBatch(", null)) +
  "\nreturn { executeToolCalls };")(validateToolArguments);

const sessionSource = readFileSync("./pi/coding-agent/src/core/session-manager.ts", "utf8");
const { parseSessionEntries } = new Function(strip(
  slice(sessionSource, "export function parseSessionEntries(", "export function getLatestCompactionEntry(")) +
  "\nreturn { parseSessionEntries };")();
const persistLine = (entry) => `${JSON.stringify(entry)}\n`; // session-manager.ts:1021, verbatim expression

const require = createRequire(import.meta.url);
const Diff = require("diff");
const editDiffSource = readFileSync("./pi/coding-agent/src/core/tools/edit-diff.ts", "utf8");
const editDiff = new Function("Diff", strip(editDiffSource.replace(/^import .*;\s*$/gm, "")) +
  "\nreturn { applyEditsToNormalizedContent, generateDiffString, generateUnifiedPatch };")(Diff);
const editSource = readFileSync("./pi/coding-agent/src/core/tools/edit.ts", "utf8");
const prepareEditArguments = new Function(strip(
  slice(editSource, "function isSingleEditInput(", "export interface EditToolDetails") +
  slice(editSource, "function prepareEditArguments(", "function validateEditInput(")) +
  "\nreturn prepareEditArguments;")();

// ---- tagged values <-> JavaScript values -------------------------------------------------------------------
const U = (s) => Array.from({ length: s.length }, (_, i) => s.charCodeAt(i));
const S = (units) => String.fromCharCode(...units);
const token = (v) => Number.isNaN(v) ? "NaN" : v === Infinity ? "+Infinity" : v === -Infinity ? "-Infinity"
  : Object.is(v, -0) ? "-0" : String(v);
const number = (t) => t === "NaN" ? NaN : t === "+Infinity" ? Infinity : t === "-Infinity" ? -Infinity
  : t === "-0" ? -0 : Number(t);
const value = (t) =>
  "u" in t ? S(t.u) : "n" in t ? number(t.n) : "a" in t ? t.a.map(value)
  : "o" in t ? Object.fromEntries(t.o.map(([k, v]) => [S(k), value(v)]))
  : "undef" in t ? undefined : t.v;
const obs = (v) =>
  v === undefined ? { undef: true }
  : typeof v === "string" ? { u: U(v) }
  : typeof v === "number" ? { n: token(v) }
  : Array.isArray(v) ? { a: Array.from(v, obs) }
  : v && typeof v === "object" ? { o: Object.keys(v).map((k) => [U(k), obs(v[k])]) }
  : { v };
const text = (content) => (content ?? []).map((c) => obs(c.text));

// ---- one case through the real pipeline ------------------------------------------------------------------
async function run(c, makeResult) {
  const seen = {};
  const tool = {
    name: "probe", label: "probe", description: "probe",
    parameters: { type: "object", properties: {} },
    execute: async () => {
      if (c.tool && "throws" in c.tool) throw new Error(S(c.tool.throws.u));
      const result = makeResult();
      seen.returned = result;
      return result;
    },
  };
  const hook = c.hook ?? { mode: "none" };
  const config = { toolExecution: "sequential" };
  if (hook.mode !== "none") {
    config.afterToolCall = async ({ result, isError }) => {
      seen.hook = { content: text(result.content), details: obs(result.details), isError,
                    same_object_as_returned: Object.is(result, seen.returned) };
      if (hook.mode === "observe") return undefined;
      if (hook.mode === "same") return { content: result.content, details: result.details };
      if (hook.mode === "null") return { details: null };
      if (hook.mode === "throws") throw new Error(S(hook.message.u));
      const replacement = {};
      if (hook.text) replacement.content = [{ type: "text", text: S(hook.text.u) }];
      if (hook.details) replacement.details = value(hook.details);
      return replacement;
    };
  }
  const call = { type: "toolCall", id: "call-1", name: "probe", arguments: {} };
  const assistant = { role: "assistant", content: [call] };
  const events = [];
  const batch = await loop.executeToolCalls({ systemPrompt: "", messages: [], tools: [tool] }, assistant, config,
                                            undefined, async (e) => { events.push(e); });
  const end = events.find((e) => e.type === "tool_execution_end");
  const message = batch.messages[0];
  const messageEnd = events.find((e) => e.type === "message_end");
  const entry = { type: "message", id: "e1", parentId: null, timestamp: "t", message };
  const line = persistLine(entry);
  const reloaded = parseSessionEntries(line)[0].message;
  return {
    id: c.id,
    events: events.map((e) => e.type),
    hook: seen.hook ?? null,
    end: { content: text(end.result.content), details: obs(end.result.details), isError: end.isError,
           has_details_key: "details" in end.result },
    message: { content: text(message.content), details: obs(message.details), isError: message.isError,
               has_details_key: "details" in message,
               details_same_object_as_end: Object.is(message.details, end.result.details),
               message_end_same_object: Object.is(messageEnd.message, message) },
    persisted_line: line.slice(0, -1),
    persisted_utf8_hex: Buffer.from(line, "utf8").toString("hex"),
    reload: { content: text(reloaded.content), details: obs(reloaded.details),
              has_details_key: "details" in reloaded },
  };
}

const cases = JSON.parse(readFileSync(process.argv[2], "utf8"));
const results = [];
for (const c of cases) {
  results.push(await run(c, () => ({
    content: [{ type: "text", text: S(c.tool.text.u) }],
    details: value(c.tool.details),
  })));
}

// the WP-13.2 edit witness: f.txt = "a\n", edits string [{"oldText":"a","newText":"\ud800"}]
const args = prepareEditArguments({ path: "f.txt", edits: '[{"oldText":"a","newText":"\\ud800"}]' });
const { baseContent, newContent } = editDiff.applyEditsToNormalizedContent("a\n", args.edits, "f.txt");
const diffResult = editDiff.generateDiffString(baseContent, newContent);
const patch = editDiff.generateUnifiedPatch("f.txt", baseContent, newContent);
const witness = await run({ id: "edit-witness/lone-high", hook: { mode: "observe" } }, () => ({
  content: [{ type: "text", text: `Successfully replaced ${args.edits.length} block(s) in ${args.path}.` }],
  details: { diff: diffResult.diff, patch, firstChangedLine: diffResult.firstChangedLine },
}));
witness.file_utf8_hex = Buffer.from(newContent, "utf8").toString("hex");
results.push(witness);

writeFileSync(process.argv[3], JSON.stringify({ node: process.versions.node, results }, null, 1) + "\n");
console.log(`result probe: ${results.length} results`);
