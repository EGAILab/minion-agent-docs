// L0506-D002 characterization: pinned Pi b7bb00b9's prepared JavaScript STRING / KEY domain at the Layer-05/06
// boundary, under Node 22.15.1 + typebox 1.3.7. Strings travel in cases.json as arrays of UTF-16 code units
// (numbers), so lone surrogates survive the JSON case file. For each case:
//   prepare (a custom prepareArguments that sets `text`, or edit.ts prepareEditArguments' JSON.parse)
//   -> Pi's own validateToolArguments (unmodified)
//   -> the value agent-loop.ts hands to beforeToolCall and execute
// Observations: verdict; the prepared value's code units; and the PROJECTION boundaries kept separate:
//   JSON.stringify of the value (Pi's failure diagnostic / any JSON serialization), and UTF-8 bytes
//   (Buffer.from(s, "utf8") == fs.writeFile(path, s, "utf-8"), edit.ts' write path).
import { readFileSync, writeFileSync } from "node:fs";
import { stripTypeScriptTypes } from "node:module";
import { validateToolArguments } from "./pi/ai/src/utils/validation.ts";

const editSource = readFileSync("./pi/coding-agent/src/core/tools/edit.ts", "utf8");
const single = editSource.slice(editSource.indexOf("function isSingleEditInput("), editSource.indexOf("export interface EditToolDetails"));
const prep = editSource.slice(editSource.indexOf("function prepareEditArguments("), editSource.indexOf("function validateEditInput("));
const prepareEditArguments = new Function(stripTypeScriptTypes(single + prep) + "\nreturn prepareEditArguments;")();

const S = (units) => String.fromCharCode(...units);
const U = (s) => Array.from({ length: s.length }, (_, i) => s.charCodeAt(i));
const hex = (s) => Buffer.from(s, "utf8").toString("hex");

const SCHEMAS = {
  open: { type: "object", properties: {} },
  string: { type: "object", properties: { text: { type: "string" } }, required: ["text"] },
  "min-length-2": { type: "object", properties: { text: { type: "string", minLength: 2 } } },
  "max-length-1": { type: "object", properties: { text: { type: "string", maxLength: 1 } } },
  "pattern-one-char": { type: "object", properties: { text: { type: "string", pattern: "^.$" } } },
  "pattern-two-chars": { type: "object", properties: { text: { type: "string", pattern: "^..$" } } },
  "const-pair": { type: "object", properties: { text: { const: S([0xd83d, 0xde00]) } } },
  "enum-lone": { type: "object", properties: { text: { enum: [S([0xd800])] } } },
};

const cases = JSON.parse(readFileSync(process.argv[2], "utf8"));
const out = cases.map((c) => {
  try {
    if (c.kind === "string") {
      const tool = { name: "probe", parameters: SCHEMAS[c.schema], prepareArguments: (a) => ({ ...a, text: S(c.units) }) };
      const prepared = tool.prepareArguments({});
      const args = validateToolArguments(tool, { type: "toolCall", id: "c", name: "probe", arguments: prepared });
      const v = args.text;
      return { id: c.id, verdict: "accept", units: U(v), json: JSON.stringify(v), utf8: hex(v), length: v.length };
    }
    if (c.kind === "edit") {
      // the raw wire text is the edits JSON string as the model sent it (escapes intact)
      const raw = { path: "f.txt", edits: c.edits_json };
      const prepared = prepareEditArguments(JSON.parse(JSON.stringify(raw)));
      const newText = prepared.edits?.[0]?.newText;
      return { id: c.id, verdict: "prepared", units: typeof newText === "string" ? U(newText) : null,
               json: JSON.stringify(newText), utf8: typeof newText === "string" ? hex(newText) : null };
    }
    if (c.kind === "keys") {
      // object key domain: JSON.parse (edit path) and a shim-built object; observe Object.keys order and own props
      const parsed = JSON.parse(c.json_text);
      const prepared = prepareEditArguments({ path: "f.txt", edits: c.json_text });
      const item = Array.isArray(prepared.edits) ? prepared.edits[0] : null;
      return {
        id: c.id, verdict: "observed",
        parsed_keys: Object.keys(Array.isArray(parsed) ? parsed[0] : parsed).map(U),
        prepared_keys: item ? Object.keys(item).map(U) : null,
        own_proto: item ? Object.prototype.hasOwnProperty.call(item, "__proto__") : null,
        json: JSON.stringify(item),
      };
    }
    throw new Error("unknown kind " + c.kind);
  } catch (error) {
    const message = String(error && error.message);
    return { id: c.id, verdict: "reject", message: message.split("\n").slice(0, 3).join(" | ") };
  }
});
writeFileSync(process.argv[3], JSON.stringify(out, null, 1) + "\n");
console.log(out.length, "cases");
