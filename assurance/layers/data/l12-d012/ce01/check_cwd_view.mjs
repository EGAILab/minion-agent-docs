// For each lone-surrogate cwd row: Node's process.cwd() view of the crafted directory NAME, as UTF-16 units, and
// whether it equals the section 15 decode (generalized UTF-8 of the units, then WHATWG UTF-8 decode).
import { readFileSync } from "node:fs";

const d = JSON.parse(readFileSync(new URL("./cwd-partition-win32.json", import.meta.url), "utf8"));
const wtf8 = (units) => {
  const out = [];
  for (let i = 0; i < units.length; i++) {
    let c = units[i];
    if (c >= 0xd800 && c <= 0xdbff && i + 1 < units.length && units[i + 1] >= 0xdc00 && units[i + 1] <= 0xdfff) {
      c = 0x10000 + ((c - 0xd800) << 10) + (units[++i] - 0xdc00);
    }
    if (c < 0x80) out.push(c);
    else if (c < 0x800) out.push(0xc0 | (c >> 6), 0x80 | (c & 63));
    else if (c < 0x10000) out.push(0xe0 | (c >> 12), 0x80 | ((c >> 6) & 63), 0x80 | (c & 63));
    else out.push(0xf0 | (c >> 18), 0x80 | ((c >> 12) & 63), 0x80 | ((c >> 6) & 63), 0x80 | (c & 63));
  }
  return Buffer.from(out);
};
const seen = new Set();
for (const r of d.rows) {
  if (seen.has(r.cwd_label)) continue;
  seen.add(r.cwd_label);
  const view = new TextDecoder("utf-8").decode(wtf8(r.binding_cwd));
  const viewUnits = Array.from(view, (ch) => ch).join("");
  const nodeCwd = String.fromCharCode(...r.node_cwd);
  const name = String.fromCharCode(...r.binding_cwd).split("\\").pop();
  const nodeName = nodeCwd.split("\\").pop();
  console.log(r.cwd_label.padEnd(22), "name units", JSON.stringify(Array.from({ length: name.length }, (_, i) => name.charCodeAt(i))),
    "node view units", JSON.stringify(Array.from({ length: nodeName.length }, (_, i) => nodeName.charCodeAt(i))),
    "== section-15 decode:", viewUnits === nodeCwd);
}
