// WP-13.3 final review 1 (CON-R005): pinned findBashOnPath's lookup output budget and stdout decoding.
//   node lookup_probe.mjs <pi checkout> <out.json>
// The function body is sliced from pinned shell.ts and run unchanged. Only the lookup program is substituted: the
// spawnSync it calls runs a controlled Node child instead of `where`/`which`, with Pi's own options passed through.
// existsSync is stubbed true, so the selected path depends only on the lookup itself.
import * as childProcess from "node:child_process";
import { readFileSync, writeFileSync } from "node:fs";
const [piDir, outPath] = process.argv.slice(2);
const source = readFileSync(`${piDir}/packages/coding-agent/src/utils/shell.ts`, "utf8");
const start = source.indexOf("function findBashOnPath(): string | null {");
let depth = 0, end = start;
for (let i = source.indexOf("{", start); i < source.length; i++) {
  if (source[i] === "{") depth++;
  if (source[i] === "}" && --depth === 0) { end = i + 1; break; }
}
const body = source.slice(start, end).replace("function findBashOnPath(): string | null {", "function findBashOnPath() {");

const BUDGET = 1024 * 1024;
const PATH = Buffer.from(process.platform === "win32" ? "C:/valid/bash.exe\n" : "/valid/bash\n");
// The child writes <prefix hex> then <stdout fill> bytes of "x" to stdout, then <stderr fill> bytes of "y" to stderr.
const CHILD = 'const [p, o, e] = process.argv.slice(1); process.stdout.write(Buffer.concat([Buffer.from(p, "hex"), Buffer.alloc(+o, 0x78)])); process.stderr.write(Buffer.alloc(+e, 0x79));';
let row = null;
const run = (options) => {
  const r = childProcess.spawnSync(process.execPath, ["-e", CHILD, row.prefix.toString("hex"), String(row.stdoutFill), String(row.stderrFill)], options);
  if (r.error && r.error.code !== "ENOBUFS") throw new Error(`lookup child failed: ${r.error.code}`);
  return r;
};
const seenOptions = new Set();
const make = (spawn) => new Function("spawnSync", "existsSync", "process", `${body}; return findBashOnPath;`)(spawn, () => true, process);
let last = null;
const pinned = make((_cmd, _args, options) => { seenOptions.add(JSON.stringify(options)); return (last = run(options)); });
// unbounded control: Pi's options, with an output budget far above every row
const unbounded = make((_cmd, _args, options) => run({ ...options, maxBuffer: 64 * BUDGET }));

const p = PATH.length;
const rows = {
  stdoutAtBudget: { prefix: PATH, stdoutFill: BUDGET - p, stderrFill: 0 },
  stdoutOverBudget: { prefix: PATH, stdoutFill: BUDGET - p + 1, stderrFill: 0 },
  stderrAtBudget: { prefix: PATH, stdoutFill: 0, stderrFill: BUDGET - p },
  stderrOverBudget: { prefix: PATH, stdoutFill: 0, stderrFill: BUDGET - p + 1 },
  combinedAtBudget: { prefix: PATH, stdoutFill: BUDGET / 2 - p, stderrFill: BUDGET / 2 },
  combinedOverBudget: { prefix: PATH, stdoutFill: BUDGET / 2 - p + 1, stderrFill: BUDGET / 2 },
  // decoding: a leading BOM is kept by the decoder and removed by trim(); an invalid byte becomes U+FFFD
  bomThenPath: { prefix: Buffer.concat([Buffer.from([0xef, 0xbb, 0xbf]), PATH]), stdoutFill: 0, stderrFill: 0 },
  invalidByteInPath: { prefix: Buffer.concat([PATH.subarray(0, 3), Buffer.from([0xff]), PATH.subarray(3)]), stdoutFill: 0, stderrFill: 0 },
};
const units = (s) => (s === null ? null : [...s].map((c) => c.codePointAt(0).toString(16).toUpperCase().padStart(4, "0")).join(" "));
const out = { node: process.version, platform: process.platform, budget: BUDGET, pathBytes: p, rows: {}, controls: {} };
const killed = { unbounded: [], perStream: [] };
for (const [name, r] of Object.entries(rows)) {
  row = r;
  const selected = units(pinned());
  const stdoutTotal = r.prefix.length + r.stdoutFill;
  out.rows[name] = { stdoutBytes: stdoutTotal, stderrBytes: r.stderrFill, combinedBytes: stdoutTotal + r.stderrFill,
    status: last.status, error: last.error?.code ?? null, selected };
  const unboundedSelected = units(unbounded());
  if (unboundedSelected !== selected) killed.unbounded.push(name);
  // perStream control: a 1 MiB budget per stream instead of one combined budget
  const perStreamSelected = stdoutTotal > BUDGET || r.stderrFill > BUDGET ? null : unboundedSelected;
  if (perStreamSelected !== selected) killed.perStream.push(name);
}
out.piOptions = [...seenOptions];
out.controls = { unbounded: { killedBy: killed.unbounded }, perStream: { killedBy: killed.perStream } };
writeFileSync(outPath, JSON.stringify(out, null, 1) + "\n");
console.log(JSON.stringify(out, null, 1));
