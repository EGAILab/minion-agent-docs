import { fileURLToPath } from "node:url";
const U = (s) => Array.from({ length: s.length }, (_, i) => s.charCodeAt(i).toString(16));
const base = process.platform === "win32" ? "file:///C:/t/" : "file:///t/";
for (const [name, tail] of [["raw-lone", "a" + String.fromCharCode(0xd800)], ["pct-lone", "a%ED%A0%80"], ["pct-fffd", "a%EF%BF%BD"], ["pct-pair", "a%F0%9F%98%80"]]) {
  try { const p = fileURLToPath(base + tail); console.log(name, JSON.stringify(U(p.slice(-2)))); }
  catch (e) { console.log(name, "THROWS", e.code); }
}
