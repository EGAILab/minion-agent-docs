import { validateToolArguments } from "./pi/ai/src/utils/validation.ts";
const show = (v) => typeof v === "string" ? JSON.stringify(v) : Object.is(v, -0) ? "-0" : String(v);
for (const branches of [[{ type: "number" }, { type: "string" }], [{ type: "string" }, { type: "number" }]])
  for (const v of [Infinity, -Infinity, NaN, 5]) {
    const args = validateToolArguments({ name: "p", parameters: { type: "object", properties: { f: { anyOf: branches } }, required: ["f"] } },
      { type: "toolCall", id: "c", name: "p", arguments: { f: v } });
    console.log(JSON.stringify(branches.map((b) => b.type)), show(v), "->", show(args.f), typeof args.f);
  }
for (const v of [Infinity, 5]) {
  const args = validateToolArguments({ name: "p", parameters: { type: "object", properties: { f: { type: "string" } }, required: ["f"] } },
    { type: "toolCall", id: "c", name: "p", arguments: { f: v } });
  console.log('{type: string}', show(v), "->", show(args.f), typeof args.f);
}
