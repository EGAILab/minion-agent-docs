// L05-D001 characterization: pinned Pi b7bb00b9's validateToolArguments (typebox 1.3.7, Node 22.15.1) over JavaScript
// strings in the SCHEMA, per schema-string role (Owner decision #99 comment 5926416181 sections 2-4). For each role, a
// schema member S (BMP, ascii, valid pair, lone high, lone low, mixed pair+lone high, U+FFFD) and an instance member I
// (same set) are combined; the observation is the verdict (and the failing-keyword message line). Strings are written
// as UTF-16 code units in cases.json.
import { readFileSync, writeFileSync } from "node:fs";
import { validateToolArguments } from "./pi/ai/src/utils/validation.ts";

const S = (units) => String.fromCharCode(...units);
const ROLES = {
  // property name + required: the instance supplies key I
  "properties-required": (s) => ({ schema: { type: "object", properties: { [s]: { type: "string" } }, required: [s] },
                                   instance: (i) => ({ [i]: "x" }) }),
  // a declared property under additionalProperties: false
  "additional-properties-false": (s) => ({ schema: { type: "object", properties: { [s]: { type: "string" } },
                                                     additionalProperties: false },
                                           instance: (i) => ({ [i]: "x" }) }),
  "const": (s) => ({ schema: { type: "object", properties: { t: { const: s } } }, instance: (i) => ({ t: i }) }),
  "enum": (s) => ({ schema: { type: "object", properties: { t: { enum: [s] } } }, instance: (i) => ({ t: i }) }),
  // pattern built from the member's characters (anchored, Unicode-mode compilation is Pi's/TypeBox's)
  "pattern": (s) => ({ schema: { type: "object", properties: { t: { type: "string", pattern: "^" + s + "$" } } },
                       instance: (i) => ({ t: i }) }),
  // unanchored: a substring search in the instance (u-mode: the halves of a pair are not substrings of the pair)
  "pattern-unanchored": (s) => ({ schema: { type: "object", properties: { t: { type: "string", pattern: s } } },
                                  instance: (i) => ({ t: i }) }),
  // a key matching the pattern-property must be a number; a string value under a matching key is rejected
  "pattern-properties": (s) => ({ schema: { type: "object", patternProperties: { ["^" + s + "$"]: { type: "number" } } },
                                  instance: (i) => ({ [i]: "x" }) }),
  // L05-D001-R001: an unanchored patternProperties key is a Unicode-mode RegExp SEARCH over instance keys
  "pattern-properties-unanchored": (s) => ({ schema: { type: "object", patternProperties: { [s]: { type: "number" } } },
                                             instance: (i) => ({ [i]: "x" }) }),
  "property-names-const": (s) => ({ schema: { type: "object", propertyNames: { const: s } }, instance: (i) => ({ [i]: 1 }) }),
  "dependent-required": (s) => ({ schema: { type: "object", dependentRequired: { [s]: ["a"] } }, instance: (i) => ({ [i]: 1 }) }),
};

const cases = JSON.parse(readFileSync(process.argv[2], "utf8"));
const results = cases.map((c) => {
  const role = ROLES[c.role](S(c.schema_units));
  const tool = { name: "p", parameters: role.schema };
  let schemaError = null;
  try {
    const args = validateToolArguments(tool, { type: "toolCall", id: "c", name: "p", arguments: role.instance(S(c.instance_units)) });
    return { id: c.id, verdict: "accept", keys: Object.keys(args).map((k) => Array.from({ length: k.length }, (_, n) => k.charCodeAt(n))) };
  } catch (error) {
    schemaError = String(error && error.message);
    const line = schemaError.split("\n")[1]?.trim() ?? schemaError.split("\n")[0];
    return { id: c.id, verdict: schemaError.startsWith("Validation failed") ? "reject" : "error",
             message: line.replace(/[\ud800-\udfff]/g, (ch) => "\\u" + ch.charCodeAt(0).toString(16)) };
  }
});
writeFileSync(process.argv[3], JSON.stringify({ node: process.versions.node, results }, null, 1) + "\n");
const tally = {};
for (const r of results) tally[r.verdict] = (tally[r.verdict] ?? 0) + 1;
console.log(`schema probe: ${results.length} results`, JSON.stringify(tally));
