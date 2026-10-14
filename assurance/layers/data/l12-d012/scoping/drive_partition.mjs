// L12-D012 C001 revision 2: the native inherited-value partition of Node v22.15.1 win32.resolve's drive-relative
// branch, through pinned Pi resolvePath (sliced unmodified), in REAL child processes whose environment block
// carries the crafted =D: entry. Lexical only: the values are strings; nothing is accessed, created or used as a
// cwd. The children's cwd is this process's cwd (the project root, on E:). Output: stdout JSON only.
import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { homedir } from "node:os";
import path from "node:path";
import { stripTypeScriptTypes } from "node:module";
import { fileURLToPath } from "node:url";

const [mode, piDir, drive, value] = process.argv.slice(2);
const branch = path.win32.resolve.toString();
if (mode === "child") {
  const src = readFileSync(`${piDir}/packages/agent/src/harness/env/nodejs.ts`, "utf8");
  const body = stripTypeScriptTypes(src.slice(src.indexOf("function resolvePath(cwd: string, path: string): string {"),
    src.indexOf("function fileKindFromStats("))) + "\nreturn resolvePath;";
  const resolvePath = new Function("homedir", "join", "fileURLToPath", "isAbsolute", "resolve", "process", body)(
    homedir, path.join, fileURLToPath, path.isAbsolute, path.resolve, process);
  console.log(JSON.stringify({ entry: process.env[`=${drive}:`] ?? null, cwd: process.cwd(),
    out: resolvePath("C:\\x", `${drive.toLowerCase()}:leaf`) }));
} else {
  if (process.platform !== "win32") throw new Error("win32 only");
  const VALUES = [null, "", "D:\\deep", "d:\\deep", "D:/deep", "D:rel", "D:", "X:\\other", "X:/other", "X:other",
    "X:", "relative", "\\deep", "/deep", "\\\\srv\\share", "r"];
  const base = Object.fromEntries(Object.entries(process.env).filter(([k]) => !k.startsWith("=")));
  const rows = [];
  for (const d of ["E", "A"]) {
    for (const v of VALUES) {
      const val = v === null ? null : v.replaceAll("D:", `${d}:`).replaceAll("d:", `${d.toLowerCase()}:`);
      const env = val === null ? base : { ...base, [`=${d}:`]: val };
      const r = spawnSync(process.execPath, ["--no-warnings", process.argv[1], "child", piDir, d], { env, encoding: "utf8" });
      if (r.status !== 0) throw new Error(`child failed: ${r.stderr}`);
      rows.push({ drive: d, value: val, ...JSON.parse(r.stdout) });
    }
  }
  const at = branch.indexOf("path = process.env[");
  console.log(JSON.stringify({ node: process.version, pi: "b7bb00b9", branch_source: branch.slice(at, at + 520), rows }, null, 1));
}
