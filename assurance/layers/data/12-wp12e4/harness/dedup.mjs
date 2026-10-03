import { spawnSync } from "node:child_process";
const child = ["-e", "console.log(JSON.stringify(Object.keys(process.env).filter(k=>/^(xk|zz_k|aa_k)/i.test(k)).map(k=>[k,process.env[k]])))"];
const run = (pairs) => { const env = { SystemRoot: process.env.SystemRoot }; for (const [k,v] of pairs) env[k]=v;
  return JSON.parse(spawnSync(process.execPath, child, { env, encoding: "utf8" }).stdout); };
const cases = {
  upperFirst: [["XK","upper"],["xk","lower"]],
  lowerFirst: [["xk","lower"],["XK","upper"]],
  mixedThenUpper: [["Xk","mixed"],["XK","upper"]],
  upperThenMixed: [["XK","upper"],["Xk","mixed"]],
  three: [["xK","a"],["Xk","b"],["XK","c"]],
};
const out = {}; for (const [n,p] of Object.entries(cases)) out[n]=run(p);
// parent-side: case-insensitivity of process.env and of a {...} copy, with an exact-case key set in a controlled parent
out.parentView = JSON.parse(spawnSync(process.execPath, ["-e",
  "const c={...process.env};console.log(JSON.stringify({keys:Object.keys(process.env).filter(k=>/programfiles/i.test(k)),penvUpper:process.env.PROGRAMFILES??null,copyUpper:c.PROGRAMFILES??null,copyExact:c.ProgramFiles??null, inOp:'PROGRAMFILES' in c}))"],
  { env: { SystemRoot: process.env.SystemRoot, ProgramFiles: "C:/PF" }, encoding: "utf8" }).stdout);
console.log(JSON.stringify(out));
