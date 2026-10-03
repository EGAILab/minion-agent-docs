// WP-12.E4 (WP12E4-CON-R002), Windows: pinned Node v22.15.1's duplicate arbitration for an EXPLICIT env object (what
// Pi's bash passes), for names whose case equivalence is non-ASCII. Both insertion orders.
//   node unicode_names.mjs <out.json>
import { spawnSync } from "node:child_process";
import { writeFileSync } from "node:fs";

const units = (s) => [...Array(s.length).keys()].map((i) => s.charCodeAt(i).toString(16).padStart(4, "0"));
const child = ["-e", "process.stdout.write(JSON.stringify(Object.keys(process.env).filter(k=>/^q/i.test(k)).map(k=>[k,process.env[k]])))"];
const run = (pairs) => {
  const env = { SystemRoot: process.env.SystemRoot };
  for (const [k, v] of pairs) env[k] = v;
  return JSON.parse(spawnSync(process.execPath, child, { env, encoding: "utf8" }).stdout);
};
const cases = {
  sharpS: [["Qß", "sharp"], ["Qss", "ss"]],
  sharpSReversed: [["Qss", "ss"], ["Qß", "sharp"]],
  dotlessI: [["Qı", "dotless"], ["QI", "ascii"]],
  dotlessIReversed: [["QI", "ascii"], ["Qı", "dotless"]],
};
const out = { runtime: process.version, platform: process.platform, upper: {}, cases: {} };
for (const name of ["Qß", "Qss", "Qı", "QI"]) out.upper[units(name).join(" ")] = name.toUpperCase();
for (const [n, pairs] of Object.entries(cases)) out.cases[n] = run(pairs).map(([k, v]) => [units(k).join(" "), v]);
writeFileSync(process.argv[2], JSON.stringify(out, null, 1) + "\n");
console.log(JSON.stringify(out));
