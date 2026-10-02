// FSP-D6: pinned Pi's file:// path conversion (utils/paths.ts normalizePath -> node:url fileURLToPath).
import { fileURLToPath } from "node:url";
import { writeFileSync } from "node:fs";
const U = (s) => Array.from({ length: s.length }, (_, i) => s.charCodeAt(i));
const base = process.platform === "win32" ? "file:///C:/t/" : "file:///t/";
const CASES = {
  "raw-lone-high": "a" + String.fromCharCode(0xd800), "raw-lone-low": "a" + String.fromCharCode(0xdc00),
  "raw-pair": "a" + String.fromCharCode(0xd83d, 0xde00), "raw-mixed": "a" + String.fromCharCode(0xd83d, 0xde00, 0xdc00),
  "pct-lone-high": "a%ED%A0%80", "pct-lone-low": "a%ED%B0%80", "pct-fffd": "a%EF%BF%BD", "pct-astral": "a%F0%9F%98%80",
  "pct-truncated": "a%F0%9F", "pct-overlong": "a%C0%AF",
};
const out = {};
for (const [name, tail] of Object.entries(CASES)) {
  try { const p = fileURLToPath(base + tail); out[name] = { ok: true, tail_units: U(p.slice(p.lastIndexOf(process.platform === "win32" ? "\\" : "/") + 1)) }; }
  catch (e) { out[name] = { ok: false, name: e.name, code: e.code ?? null, message: e.message }; }
}
writeFileSync(process.argv[2], JSON.stringify({ platform: process.platform, node: process.versions.node, cases: out }, null, 1) + "\n");
console.log(JSON.stringify(Object.fromEntries(Object.entries(out).map(([k, v]) => [k, v.ok ? v.tail_units.map((u) => u.toString(16)).join(" ") : `THROWS ${v.name}`]))));
