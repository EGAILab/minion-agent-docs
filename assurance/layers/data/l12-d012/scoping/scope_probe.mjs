// L12-D012 scoping characterization: pinned Pi resolvePath (sliced unmodified from
// packages/agent/src/harness/env/nodejs.ts) over the colon-component / malformed file-URL neighborhood.
// win32: native on this Windows host. posix: the same function with Node's path.posix and fileURLToPath
// {windows:false} injected -- PROVISIONAL, to be confirmed by native Linux generation. Pure computation:
// no filesystem access, no process, no writes.
import { readFileSync } from "node:fs";
import { homedir } from "node:os";
import path from "node:path";
import { stripTypeScriptTypes } from "node:module";
import { fileURLToPath } from "node:url";

const piDir = process.argv[2];
const src = readFileSync(`${piDir}/packages/agent/src/harness/env/nodejs.ts`, "utf8");
const start = src.indexOf("function resolvePath(cwd: string, path: string): string {");
const end = src.indexOf("function fileKindFromStats(");
if (start < 0 || end < 0) throw new Error("resolvePath not found");
const body = stripTypeScriptTypes(src.slice(start, end)) + "\nreturn resolvePath;";
const make = (p, windows) =>
  new Function("homedir", "join", "fileURLToPath", "isAbsolute", "resolve", "process", body)(
    homedir, p.join, (u) => fileURLToPath(u, { windows }), p.isAbsolute, p.resolve, process);
const win = make(path.win32, true);
const posix = make(path.posix, false);

const INPUTS = [
  // malformed file URLs (literal fallback)
  "file:///C:/a%2Fb", "file:/C:/a%2Fb", "file:a%2Fb", "file:///tmp/a%2Fb", "file:x/y%2Fz",
  // colon-ending components in relative paths
  "x/c:/d", "x\\c:\\d", "c:d", "x/c:", "x/c:/", "x/c:d/e", "a::/b", "x/:/y", ":", "x:y:z/w",
  // drive-looking components embedded mid-path
  "x/C:/y", "x/C:\\y", "x//C:/y",
  // absolute drive forms (control)
  "a:/b", "C:\\y", "C:y",
  // valid file URLs (control)
  "file:///C:/a/b", "file:///tmp/a",
];
const rows = [];
for (const input of INPUTS) {
  const row = { input };
  try { row.win32 = win("C:\\x", input); } catch (e) { row.win32 = `THROW ${e.code ?? e.name}`; }
  try { row.posix = posix("/x", input); } catch (e) { row.posix = `THROW ${e.code ?? e.name}`; }
  rows.push(row);
}
console.log(JSON.stringify({ node: process.version, pi: "b7bb00b9", rows }, null, 1));
