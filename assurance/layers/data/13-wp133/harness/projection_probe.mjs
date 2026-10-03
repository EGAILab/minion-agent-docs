// WP-13.3 audit 1 (R001, R002): child-observed command projection and pinned OutputAccumulator BOM handling.
//   node --experimental-strip-types projection_probe.mjs <pi checkout> <out.json>
import { spawnSync } from "node:child_process";
import { pathToFileURL } from "node:url";
import { writeFileSync } from "node:fs";
const [piDir, outPath] = process.argv.slice(2);
const units = (s) => [...Array(s.length).keys()].map((i) => s.charCodeAt(i).toString(16).toUpperCase().padStart(4, "0"));
const inputs = { loneHigh: "a\uD800b", loneLow: "a\uDC80b", pair: "a\uD83D\uDE00b", reversed: "a\uDE00\uD83Db" };
const out = { node: process.version, platform: process.platform, argvToNode: {}, argvToBashBytes: {}, stdinToBashBytes: {} };
for (const [name, s] of Object.entries(inputs)) {
  const r = spawnSync(process.execPath, ["-e", "process.stdout.write(JSON.stringify([...Array(process.argv[1].length).keys()].map(i=>process.argv[1].charCodeAt(i).toString(16).toUpperCase().padStart(4,'0'))))", s], { encoding: "utf8" });
  out.argvToNode[name] = { sent: units(s), childArgv: JSON.parse(r.stdout) };
}
const bash = process.platform === "win32" ? "C:/Program Files/Git/bin/bash.exe" : "/bin/bash";
for (const [name, s] of Object.entries(inputs)) {
  const cmd = `printf %s '${s}' | od -An -tx1 | tr -d ' \n'`;
  const a = spawnSync(bash, ["-c", cmd], { encoding: "utf8" });
  out.argvToBashBytes[name] = a.stdout.trim();
  const b = spawnSync(bash, ["-s"], { input: cmd, encoding: "utf8" });
  out.stdinToBashBytes[name] = b.stdout.trim();
}
const { OutputAccumulator } = await import(pathToFileURL(`${piDir}/packages/coding-agent/src/core/tools/output-accumulator.ts`).href);
const acc = (chunks) => { const a = new OutputAccumulator(); for (const c of chunks) a.append(Buffer.from(c, "hex")); a.finish();
  const s = a.snapshot(); return { content: units(s.content), totalBytes: s.truncation.totalBytes, outputBytes: s.truncation.outputBytes }; };
out.bom = {
  initial: acc(["efbbbf61"]),
  splitInitial: acc(["ef", "bbbf61"]),
  splitThree: acc(["ef", "bb", "bf", "61"]),
  nonInitial: acc(["78", "efbbbf61"]),
  doubleInitial: acc(["efbbbfefbbbf61"]),
  initialOnly: acc(["efbbbf"]),
  partialBomThenOther: acc(["efbb", "61"]),
};
writeFileSync(outPath, JSON.stringify(out, null, 1) + "\n");
console.log(JSON.stringify(out));
