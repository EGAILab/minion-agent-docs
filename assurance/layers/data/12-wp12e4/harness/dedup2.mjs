import { spawnSync } from "node:child_process";
const child = ["-e", "console.log(JSON.stringify(Object.keys(process.env).filter(k=>/^xk$/i.test(k)).map(k=>[k,process.env[k]])))"];
const run = (pairs) => { const env = { SystemRoot: process.env.SystemRoot }; for (const [k,v] of pairs) env[k]=v;
  return JSON.parse(spawnSync(process.execPath, child, { env, encoding: "utf8" }).stdout); };
console.log(JSON.stringify({ lowerThenxK: run([["xk","l"],["xK","m"]]), xKThenLower: run([["xK","m"],["xk","l"]]), XkThenxK: run([["xK","m"],["Xk","n"]]) }));
