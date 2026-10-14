// L12-D012 generator: the shared fs-path-resolution cases from pinned Pi resolvePath (packages/agent/src/harness/env/
// nodejs.ts, sliced unmodified) on native Node v22.15.1, on the platform it runs on. Pure computation; it WRITES
// NOTHING (the JSON partial goes to stdout; the launcher writes it through io.writeOutput).
//
//   node gen_path_resolution.mjs generate <piDir> <cwdA> <cwdB>     -> partial JSON on stdout
//   node gen_path_resolution.mjs child <piDir> <driveLetter> <inputJSON>   (internal: one controlled host-state row)
//
// win32: the 23 baseline inputs (record section 2) in-process, under VERIFIED host preconditions (no inherited =A:/=X:
// entry, process cwd not on A:/X:/C:) -- otherwise it REFUSES with exit 3 and writes nothing; plus the controlled
// host-state partition (record section 3.2: 16 inherited-entry values on the child cwd's own drive and on A:), each in
// REAL child processes launched with a crafted environment block, run from TWO different child cwds so that each
// cwd-dependent expectation is proven as a template (cwd_drive / cwd_tail parts) rather than a host constant.
// linux: the 23 baseline inputs plus two ordinary drive-looking spellings; no host-state cases (NOT_APPLICABLE).
import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { homedir } from "node:os";
import path from "node:path";
import { stripTypeScriptTypes } from "node:module";
import { fileURLToPath } from "node:url";

const PI = "b7bb00b936dbe21b8e160b3e89efdec361846699";
const [mode, piDir, ...rest] = process.argv.slice(2);
const WIN = process.platform === "win32";
const PROVIDER_CWD = WIN ? "C:\\x" : "/x";

function piResolvePath() {
  const src = readFileSync(`${piDir}/packages/agent/src/harness/env/nodejs.ts`, "utf8");
  const start = src.indexOf("function resolvePath(cwd: string, path: string): string {");
  const end = src.indexOf("function fileKindFromStats(");
  if (start < 0 || end < 0) throw new Error("pinned resolvePath not found");
  const body = stripTypeScriptTypes(src.slice(start, end)) + "\nreturn resolvePath;";
  return new Function("homedir", "join", "fileURLToPath", "isAbsolute", "resolve", "process", body)(
    homedir, path.join, fileURLToPath, path.isAbsolute, path.resolve, process);
}

const units = (s) => Array.from({ length: s.length }, (_, i) => s.charCodeAt(i));
const text = (s) => ({ utf16: units(s) });

const BASELINE = [
  "file:///C:/a%2Fb", "file:/C:/a%2Fb", "file:a%2Fb", "file:///tmp/a%2Fb", "file:x/y%2Fz",
  "x/c:/d", "x\\c:\\d", "c:d", "x/c:", "x/c:/", "x/c:d/e", "a::/b", "x/:/y", ":", "x:y:z/w",
  "x/C:/y", "x/C:\\y", "x//C:/y", "a:/b", "C:\\y", "C:y", "file:///C:/a/b", "file:///tmp/a",
];
const LINUX_EXTRA = ["e:leaf", "a:leaf"];
// Inherited =D: entry values (record section 3.2). `D`/`d` stand for the drive letter in upper/lower case.
const VALUES = [null, "", "D:\\deep", "d:\\deep", "D:/deep", "D:rel", "D:", "X:\\other", "X:/other", "X:other",
  "X:", "relative", "\\deep", "/deep", "\\\\srv\\share", "r"];

// Parts: literal text, or the child cwd's drive letter (upper/lower), or the child cwd after its 2-unit device.
function partsOfValue(template, onCwdDrive, letter) {
  if (!onCwdDrive) return [text(template.replaceAll("D:", `${letter}:`).replaceAll("d:", `${letter.toLowerCase()}:`))];
  const out = [];
  let lit = "";
  for (let i = 0; i < template.length; i++) {
    const c = template[i];
    if ((c === "D" || c === "d") && template[i + 1] === ":") {
      if (lit) out.push(text(lit));
      lit = "";
      out.push({ cwd_drive: c === "D" ? "upper" : "lower" });
    } else lit += c;
  }
  if (lit) out.push(text(lit));
  return out;
}

function instantiate(parts, cwd) {
  return parts.map((p) => ("utf16" in p ? String.fromCharCode(...p.utf16)
    : "cwd_drive" in p ? (p.cwd_drive === "upper" ? cwd[0].toUpperCase() : cwd[0].toLowerCase())
    : cwd.slice(2))).join("");
}

// A cwd-dependent observation becomes parts: a leading device equal to the cwd's drive -> cwd_drive; every occurrence
// of the cwd after its device -> cwd_tail. The template is then PROVEN against a second, different cwd (caller).
function templateOf(out, cwd, onCwdDrive) {
  const parts = [];
  let rest = out;
  if (onCwdDrive && rest.length >= 2 && rest[1] === ":" && rest[0].toLowerCase() === cwd[0].toLowerCase()) {
    parts.push({ cwd_drive: rest[0] === rest[0].toUpperCase() ? "upper" : "lower" });
    rest = rest.slice(1);
  }
  const tail = cwd.slice(2);
  let i;
  while ((i = rest.indexOf(tail)) >= 0) {
    if (i > 0) parts.push(text(rest.slice(0, i)));
    parts.push({ cwd_tail: true });
    rest = rest.slice(i + tail.length);
  }
  if (rest) parts.push(text(rest));
  return parts;
}

function refuse(why) {
  console.error(`PRECONDITION REFUSED: ${why}`);
  process.exit(3);
}

if (mode === "child") {
  const [letter, inputJson] = rest;
  const input = JSON.parse(inputJson);
  console.log(JSON.stringify({ cwd: process.cwd(), entry: process.env[`=${letter}:`] ?? null, out: piResolvePath()(PROVIDER_CWD, input) }));
} else if (mode === "generate") {
  const [cwdA, cwdB] = rest;
  const resolvePath = piResolvePath();
  const cases = [];
  const host = process.cwd();
  if (WIN) {
    for (const d of ["A", "X"]) if (process.env[`=${d}:`] !== undefined) refuse(`inherited =${d}: entry is present`);
    for (const d of ["A", "X", "C"]) if (host[0].toUpperCase() === d) refuse(`process cwd is on ${d}:`);
    for (const c of [cwdA, cwdB]) if (c[0].toUpperCase() !== host[0].toUpperCase()) refuse(`child cwd ${c} is not on the process cwd's drive`);
    if (cwdA === cwdB) refuse("the two child cwds must differ");
  }
  const pre = WIN ? { absent_entries: ["A", "X"], process_cwd_drive_not: ["A", "X", "C"] } : {};
  (WIN ? BASELINE : [...BASELINE, ...LINUX_EXTRA]).forEach((input, n) => {
    cases.push({ id: `baseline/${String(n + 1).padStart(2, "0")}`, platform: WIN ? "win32" : "linux", provider_cwd: text(PROVIDER_CWD),
      input: text(input), host: null, preconditions: pre, expect: text(resolvePath(PROVIDER_CWD, input)) });
  });
  if (WIN) {
    const base = Object.fromEntries(Object.entries(process.env).filter(([k]) => !k.startsWith("=")));
    for (const where of ["cwd", "A"]) {
      VALUES.forEach((value, n) => {
        const runs = [cwdA, cwdB].map((cwd) => {
          const letter = where === "cwd" ? cwd[0].toUpperCase() : "A";
          const entry = value === null ? null : instantiate(partsOfValue(value, where === "cwd", letter), cwd);
          const input = `${letter.toLowerCase()}:leaf`;
          const env = entry === null ? base : { ...base, [`=${letter}:`]: entry };
          const r = spawnSync(process.execPath, ["--no-warnings", process.argv[1], "child", piDir, letter, JSON.stringify(input)],
            { env, cwd, encoding: "utf8" });
          if (r.status !== 0) throw new Error(`child failed: ${r.stderr}`);
          const o = JSON.parse(r.stdout);
          if (o.entry !== entry) throw new Error(`child saw entry ${JSON.stringify(o.entry)}, crafted ${JSON.stringify(entry)}`);
          if (path.resolve(o.cwd) !== path.resolve(cwd)) throw new Error(`child cwd ${o.cwd} != ${cwd}`);
          return { cwd, out: o.out };
        });
        const expect = templateOf(runs[0].out, runs[0].cwd, where === "cwd");
        if (instantiate(expect, runs[1].cwd) !== runs[1].out) {
          throw new Error(`template ${JSON.stringify(expect)} does not reproduce ${runs[1].out} under ${runs[1].cwd}`);
        }
        cases.push({
          id: `host/${where === "cwd" ? "cwd-drive" : "a-drive"}/${String(n + 1).padStart(2, "0")}`,
          platform: "win32", provider_cwd: text(PROVIDER_CWD),
          input: where === "cwd" ? { parts: [{ cwd_drive: "lower" }, text(":leaf")] } : text("a:leaf"),
          host: { drive: where === "cwd" ? "cwd" : "A", entry: value === null ? null : { parts: partsOfValue(value, where === "cwd", "A") } },
          preconditions: { process_cwd_drive_not: where === "cwd" ? ["C"] : ["A", "C"] },
          expect: { parts: expect },
        });
      });
    }
  }
  console.log(JSON.stringify({ platform: WIN ? "win32" : "linux", node: process.version, pi: PI, cases }));
} else {
  throw new Error("usage: generate <piDir> <cwdA> <cwdB> | child <piDir> <letter> <inputJSON>");
}
