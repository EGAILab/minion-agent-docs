// CE-L0506-D001-I001-01 rev 2: pinned Pi's validateToolArguments (unmodified, typebox 1.3.7) over each
// case's JSON schema -- verdict AND the returned (validated) arguments, tokenized (+/-Infinity, NaN, -0).
import { readFileSync, writeFileSync } from "node:fs";
import { validateToolArguments } from "./pi/ai/src/utils/validation.ts";

const decode = (v) => Array.isArray(v) ? v.map(decode)
  : v && typeof v === "object" ? ("$num" in v ? ({ "+Infinity": Infinity, "-Infinity": -Infinity, NaN: NaN, "-0": -0 })[v.$num]
    : Object.fromEntries(Object.entries(v).map(([k, x]) => [k, decode(x)]))) : v;
const encode = (v) => Array.isArray(v) ? v.map(encode)
  : typeof v === "number" ? (Number.isNaN(v) ? { $num: "NaN" } : v === Infinity ? { $num: "+Infinity" }
    : v === -Infinity ? { $num: "-Infinity" } : Object.is(v, -0) ? { $num: "-0" } : v)
  : v && typeof v === "object" ? Object.fromEntries(Object.entries(v).map(([k, x]) => [k, encode(x)])) : v;
const cases = JSON.parse(readFileSync(process.argv[2], "utf8"));
const out = {};
for (const c of cases) {
  try {
    const value = validateToolArguments({ name: "probe", parameters: c.schema }, { type: "toolCall", id: "c", name: "probe", arguments: decode(c.arguments) });
    out[c.id] = { verdict: "accept", value: encode(value) };
  } catch { out[c.id] = { verdict: "reject" }; }
}
writeFileSync(process.argv[3], JSON.stringify(out, null, 1) + "\n");
console.log(Object.keys(out).length, "Pi verdicts");
