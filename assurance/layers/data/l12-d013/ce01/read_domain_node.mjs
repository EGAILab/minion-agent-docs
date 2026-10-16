// CE-L12D013-01 read-domain characterization, pinned Pi side. Pure and in-memory: no filesystem access, no child.
// The exact pinned resolvePath slice (packages/agent/src/harness/env/nodejs.ts:51-65, blob verified against
// b7bb00b9) runs with its imports bound to Node v22.15.1's own path.win32 or path.posix (and fileURLToPath in that
// platform's mode). For every row it counts the process.cwd() calls and records every "=X:" entry the resolver
// reads from process.env. The process cwd is injected (win32 "E:\proc", posix "/proc"), and so is each inherited
// entry state. Output: JSON on stdout.
//   node read_domain_node.mjs <pi checkout>
import { readFileSync } from "node:fs";
import { execFileSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const pi = process.argv[2];
const PI_COMMIT = "b7bb00b936dbe21b8e160b3e89efdec361846699";
const FILE = "packages/agent/src/harness/env/nodejs.ts";
// No automatic termination: unbounded capture, no timeout or killSignal.
const NO_KILL = { encoding: "utf8", maxBuffer: Infinity };
const pinned = execFileSync("git", ["-C", pi, "rev-parse", `${PI_COMMIT}:${FILE}`], NO_KILL).trim();
const actual = execFileSync("git", ["-C", pi, "hash-object", "--no-filters", FILE], NO_KILL).trim();
if (pinned !== actual || process.version !== "v22.15.1") throw new Error(`premise: blob ${actual} vs ${pinned}, node ${process.version}`);
const lines = readFileSync(path.join(pi, FILE), "utf8").split(/\r?\n/).slice(50, 65);
if (!lines[0].startsWith("function resolvePath(cwd: string, path: string): string {") || lines[14] !== "}") throw new Error("slice moved");
const body = lines.join("\n").replace("function resolvePath(cwd: string, path: string): string {", "function resolvePath(cwd, path) {");

function build(mod, windows) {
  const fileURL = (u) => fileURLToPath(u, { windows });
  const homedir = () => { throw new Error("home is out of scope (#236)"); };
  const platform = windows ? "win32" : "linux";
  // `process.platform` inside the slice is read from this shadow object, never mutated globally.
  return new Function("isAbsolute", "resolve", "join", "homedir", "fileURLToPath", "process",
    `${body}\nreturn resolvePath;`)(mod.isAbsolute, mod.resolve, mod.join, homedir, fileURL, { platform });
}

function observe(resolvePath, provider, input, entries, procCwd, windows) {
  const realCwd = process.cwd;
  const realEnv = process.env;
  const reads = [];
  const envReads = [];
  process.cwd = () => { reads.push(1); return procCwd; };
  // The Windows environment block is case-insensitive (Node reads "=a:" for the device "a:").
  const lookup = (k) => (windows ? entries[k.toUpperCase()] : entries[k]);
  process.env = new Proxy({}, { get: (_, k) => { if (typeof k !== "string") return undefined; if (k.startsWith("=")) envReads.push(k); return lookup(k); } });
  try {
    return { value: resolvePath(provider, input), cwdReads: reads.length, envReads };
  } catch (e) {
    return { error: String(e?.message ?? e), cwdReads: reads.length, envReads };
  } finally {
    process.cwd = realCwd;
    process.env = realEnv;
  }
}

const W = {
  providers: ["C:\\base", "\\base", "C:base", "base", "", "\\\\srv\\share\\base", "\\\\?\\C:\\base"],
  inputs: ["C:\\x", "\\\\srv\\share\\x", "\\leaf", "/leaf", "\\\\leaf", "\\\\srv\\", "a:leaf", "c:leaf", "leaf", "", "file:///C:/x", "file://srv/share/x"],
  entries: { absent: {}, empty: { "=A:": "", "=C:": "" }, same: { "=A:": "A:\\deep", "=C:": "C:\\deep" }, other: { "=A:": "X:\\other", "=C:": "X:\\other" } },
};
const P = {
  providers: ["/base", "base", "", "//base"],
  inputs: ["/x", "//x", "x", "", "\\leaf", "file:///x"],
};
const win = build(path.win32, true);
const posix = build(path.posix, false);
const rows = [];
for (const provider of W.providers) for (const input of W.inputs) for (const [state, entries] of Object.entries(W.entries)) {
  rows.push({ platform: "win32", provider, input, entries: state, ...observe(win, provider, input, entries, "E:\\proc", true) });
}
for (const provider of P.providers) for (const input of P.inputs) {
  rows.push({ platform: "posix", provider, input, entries: "n/a", ...observe(posix, provider, input, {}, "/proc", false) });
}
console.log(JSON.stringify({ node: process.version, pi: PI_COMMIT, blob: actual, procCwd: { win32: "E:\\proc", posix: "/proc" }, rows }, null, 1));
