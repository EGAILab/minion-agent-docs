// CE-L0506-D001-I001-01: pinned Pi's validateToolArguments (unmodified, typebox 1.3.7) over each case's JSON schema.
import { readFileSync, writeFileSync } from "node:fs";
import { validateToolArguments } from "./pi/ai/src/utils/validation.ts";

const decode = (v) => Array.isArray(v) ? v.map(decode)
  : v && typeof v === "object" ? ("$num" in v ? ({ "+Infinity": Infinity, "-Infinity": -Infinity, NaN: NaN, "-0": -0 })[v.$num]
    : Object.fromEntries(Object.entries(v).map(([k, x]) => [k, decode(x)]))) : v;
const cases = JSON.parse(readFileSync(process.argv[2], "utf8"));
const out = {};
for (const c of cases) {
  try {
    validateToolArguments({ name: "probe", parameters: c.schema }, { type: "toolCall", id: "c", name: "probe", arguments: decode(c.arguments) });
    out[c.id] = "accept";
  } catch { out[c.id] = "reject"; }
}
writeFileSync(process.argv[3], JSON.stringify(out, null, 1) + "\n");
console.log(Object.keys(out).length, "Pi verdicts");
