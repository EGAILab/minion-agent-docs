// L0506-D001 characterization: pinned Pi b7bb00b9 packages/ai/src/utils/validation.ts (unmodified) with the
// SRI-checked typebox 1.3.7, under Node 22.15.1. What does validateToolArguments -- the value beforeToolCall
// receives as `args` and execute receives -- do with prepared +/-Infinity, -0 and NaN?
import { Type } from "typebox";
import { validateToolArguments } from "./pi/ai/src/utils/validation.ts";

const show = (v) => (typeof v === "number" ? (Object.is(v, -0) ? "-0" : String(v)) : JSON.stringify(v));
const VALUES = { "+Infinity": Infinity, "-Infinity": -Infinity, "-0": -0, "NaN": NaN, "1e308": 1e308, "0": 0 };

const edit = Type.Object({
  path: Type.String(),
  edits: Type.Array(Type.Object({ oldText: Type.String(), newText: Type.String() })),
});
const numberTypeBox = Type.Object({ limit: Type.Number() });
const numberJsonSchema = { type: "object", properties: { limit: { type: "number" } }, required: ["limit"] };
const integerTypeBox = Type.Object({ limit: Type.Integer() });

function run(label, parameters, build, read) {
  for (const [name, value] of Object.entries(VALUES)) {
    let outcome;
    try {
      const args = validateToolArguments({ name: "t", parameters }, { type: "toolCall", id: "c", name: "t", arguments: build(value) });
      outcome = "ok " + show(read(args));
    } catch (e) {
      outcome = "REJECTED " + String(e.message).split("\n").slice(0, 2).join(" | ");
    }
    console.log(`${label.padEnd(44)} ${name.padEnd(10)} -> ${outcome}`);
  }
}

run("edit schema, undeclared edits[0].extra", edit,
  (v) => ({ path: "f", edits: [{ oldText: "a", newText: "b", extra: v }] }), (a) => a.edits[0].extra);
run("edit schema, undeclared top-level extra", edit,
  (v) => ({ path: "f", edits: [{ oldText: "a", newText: "b" }], extra: v }), (a) => a.extra);
run("TypeBox Type.Number() declared field", numberTypeBox, (v) => ({ limit: v }), (a) => a.limit);
run("TypeBox Type.Integer() declared field", integerTypeBox, (v) => ({ limit: v }), (a) => a.limit);
run("plain JSON Schema {type: number} field", numberJsonSchema, (v) => ({ limit: v }), (a) => a.limit);
// JSON.parse, the only core-Pi preparation path (edit.ts prepareEditArguments) that decodes numbers:
for (const token of ["1e999", "-1e999", "9".repeat(400), "-" + "9".repeat(400), "-0", "0", "1.7976931348623157e308"]) {
  console.log(`JSON.parse ${token.length > 24 ? token.slice(0, 12) + "...(" + token.length + " chars)" : token}`.padEnd(56), "->", show(JSON.parse(token)));
}
console.log("JSON.parse cannot produce NaN:", ["NaN", "nan"].map((t) => { try { JSON.parse(t); return t + " parsed"; } catch { return t + " SyntaxError"; } }).join(", "));
