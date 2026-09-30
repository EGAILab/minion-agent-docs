// L0506-D001 authority: pinned Pi b7bb00b9's Layer-05/06 preparation + validation boundary, under Node 22.15.1.
// For each case: prepare (edit.ts prepareEditArguments, or a custom prepare that sets a value) -> Pi's own
// validateToolArguments (packages/ai/src/utils/validation.ts, unmodified, typebox 1.3.7) -> the value
// agent-loop.ts hands to beforeToolCall as `args` and, unchanged, to execute. Observed values are rendered as
// tokens: "+Infinity", "-Infinity", "-0", "NaN", or Number::toString of a finite number.
import { readFileSync, writeFileSync } from "node:fs";
import { Type } from "typebox";
import { validateToolArguments } from "./pi/ai/src/utils/validation.ts";

// ---- edit.ts:34-55 (editSchema), sliced from the pinned source at run time and evaluated with typebox's Type
const editSource = readFileSync("./pi/coding-agent/src/core/tools/edit.ts", "utf8").split("\n").slice(33, 55).join("\n");
const editSchema = new Function("Type", editSource + "\nreturn editSchema;")(Type);

// ---- edit.ts:74-81 and 116-147, verbatim (types removed) -- the same copy the WP-13.2 authority uses
function isSingleEditInput(value) {
	if (!value || typeof value !== "object" || Array.isArray(value)) {
		return false;
	}

	const edit = value;
	return typeof edit.oldText === "string" && typeof edit.newText === "string";
}
function prepareEditArguments(input) {
	if (!input || typeof input !== "object") {
		return input;
	}

	const args = input;

	// Some models (Opus 4.6, GLM-5.1) send edits as a JSON string instead of an array.
	// Others send a single edit object instead of a one-element edits array.
	if (typeof args.edits === "string") {
		try {
			const parsed = JSON.parse(args.edits);
			if (Array.isArray(parsed)) {
				args.edits = parsed;
			} else if (isSingleEditInput(parsed)) {
				args.edits = [parsed];
			}
		} catch {}
	} else if (isSingleEditInput(args.edits)) {
		args.edits = [args.edits];
	}

	const legacy = args;
	if (typeof legacy.oldText !== "string" || typeof legacy.newText !== "string") {
		return args;
	}

	const edits = Array.isArray(legacy.edits) ? [...legacy.edits] : [];
	edits.push({ oldText: legacy.oldText, newText: legacy.newText });
	const { oldText: _oldText, newText: _newText, ...rest } = legacy;
	return { ...rest, edits };
}

const SCHEMAS = {
  number: { type: "object", properties: { limit: { type: "number" } }, required: ["limit"] },
  integer: { type: "object", properties: { limit: { type: "integer" } }, required: ["limit"] },
  open: { type: "object", properties: {} },
};
const decode = (t) => ({ "+Infinity": Infinity, "-Infinity": -Infinity, "-0": -0, NaN: NaN })[t] ?? Number(t);
const token = (v) =>
  typeof v !== "number" ? JSON.stringify(v)
  : Number.isNaN(v) ? "NaN" : v === Infinity ? "+Infinity" : v === -Infinity ? "-Infinity"
  : Object.is(v, -0) ? "-0" : String(v);
const at = (obj, pointer) => pointer.split("/").slice(1).reduce((o, k) => (o == null ? undefined : o[k]), obj);

// agent-loop.ts prepareToolCallArguments + prepareToolCall's validateToolArguments, as Pi runs them
function preflight(tool, rawArguments) {
  const toolCall = { type: "toolCall", id: "call-1", name: tool.name, arguments: rawArguments };
  const prepared = tool.prepareArguments ? tool.prepareArguments(toolCall.arguments) : toolCall.arguments;
  const preparedToolCall = prepared === toolCall.arguments ? toolCall : { ...toolCall, arguments: prepared };
  return validateToolArguments(tool, preparedToolCall);
}

const cases = JSON.parse(readFileSync(process.argv[2], "utf8"));
const results = cases.map((c) => {
  const raw = JSON.parse(JSON.stringify(c.arguments));
  const tool = c.tool === "edit"
    ? { name: "edit", parameters: editSchema, prepareArguments: prepareEditArguments }
    : { name: "probe", parameters: SCHEMAS[c.schema],
        prepareArguments: (args) => ({ ...args, ...Object.fromEntries(Object.entries(c.prepare_set).map(([k, t]) => [k, decode(t)])) }) };
  try {
    const args = preflight(tool, raw);
    return { id: c.id, outcome: "prepared", observed: Object.fromEntries(c.observe.map((p) => [p, token(at(args, p))])) };
  } catch (error) {
    return { id: c.id, outcome: "argument_validation_failure", message: String(error.message).split("\n")[1]?.trim() };
  }
});
writeFileSync(process.argv[3], JSON.stringify({ node: process.versions.node, results }, null, 1) + "\n");
console.log(`authority: ${results.length} results`);
for (const r of results) console.log(r.id.padEnd(40), r.outcome, JSON.stringify(r.observed ?? r.message));
