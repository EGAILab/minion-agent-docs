// L12-D013 generator: the rooted drive-less / UNC-root cases from pinned Pi resolvePath (packages/agent/src/harness/
// env/nodejs.ts, sliced unmodified) on native Node v22.15.1, on the platform it runs on. Pure computation; it WRITES
// NOTHING (the JSON partial goes to stdout; the launcher writes it through io.writeOutput).
//
//   node gen_rooted.mjs generate <piDir> <cwdA> <cwdB>       -> partial JSON on stdout
//   node gen_rooted.mjs child <piDir> <inputJSON>            (internal: one row in a child with a chosen cwd)
//
// win32 (record 12-l12-d013-rooted.md section 5):
//   baseline R3 -- complete-UNC inputs, independent of every cwd: computed in-process;
//   host R1/R2  -- device-less rooted inputs in REAL child processes whose cwd is an ordinary sandbox directory;
//   host R4     -- the same in children whose cwd is the extended spelling \\?\ + that sandbox directory.
//   Every host row runs from TWO different child cwds on the same drive, so the cwd dependence is proven as a
//   template (cwd_drive parts) rather than a host constant. The child environment carries NO '='-prefixed entry.
// linux: POSIX no-regression baseline rows (a leading / is absolute and used as-is; a leading \ is relative).
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
const EXTENDED = "\\\\?\\";

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

const WIN_BASELINE = ["\\\\srv\\share\\leaf", "\\\\srv\\share", "\\\\srv\\\\share", "//srv/share/leaf"];  // R3
const LINUX_BASELINE = ["/leaf", "//leaf", "\\leaf", "\\\\srv\\share"];
const R1 = ["\\leaf", "/leaf", "\\", "\\..\\leaf", "\\a\\b\\..\\c"];
const R2 = ["\\\\leaf", "//leaf", "\\\\srv\\", "\\\\\\leaf"];
const R4 = ["\\leaf", "\\\\leaf"];

// A cwd-dependent output becomes parts: its device, when it is the child cwd's drive (optionally behind the
// extended prefix), becomes a cwd_drive part. Everything else is literal. The template is PROVEN against a second,
// different cwd by the caller; an output containing the cwd's own tail would fail that proof.
function templateOf(out, ordinaryCwd) {
  const letter = ordinaryCwd[0];
  const at = out.startsWith(EXTENDED) ? EXTENDED.length : 0;
  if (out.length < at + 2 || out[at + 1] !== ":" || out[at].toLowerCase() !== letter.toLowerCase()) return [text(out)];
  const parts = [];
  if (at) parts.push(text(EXTENDED));
  parts.push({ cwd_drive: out[at] === out[at].toUpperCase() ? "upper" : "lower" });
  parts.push(text(out.slice(at + 1)));
  return parts;
}

function instantiate(parts, ordinaryCwd) {
  return parts.map((p) => ("utf16" in p ? String.fromCharCode(...p.utf16)
    : p.cwd_drive === "upper" ? ordinaryCwd[0].toUpperCase() : ordinaryCwd[0].toLowerCase())).join("");
}

function refuse(why) {
  console.error(`PRECONDITION REFUSED: ${why}`);
  process.exit(3);
}

if (mode === "child") {
  const [inputJson] = rest;
  const leaked = Object.keys(process.env).filter((k) => k.startsWith("="));
  console.log(JSON.stringify({ cwd: process.cwd(), leaked, out: piResolvePath()(PROVIDER_CWD, JSON.parse(inputJson)) }));
} else if (mode === "generate") {
  const [cwdA, cwdB] = rest;
  const resolvePath = piResolvePath();
  const cases = [];
  if (WIN) {
    for (const c of [cwdA, cwdB]) {
      if (!/^[A-Za-z]:\\/.test(c)) refuse(`child cwd ${c} is not an ordinary drive path`);
      if (c[0].toUpperCase() === "C") refuse(`child cwd ${c} is on the provider's drive C:`);
    }
    if (cwdA[0].toUpperCase() !== cwdB[0].toUpperCase() || cwdA === cwdB) refuse("two different child cwds on one drive");
  }
  (WIN ? WIN_BASELINE : LINUX_BASELINE).forEach((input, n) => {
    cases.push({ id: `baseline/rooted-${String(n + 1).padStart(2, "0")}`, platform: WIN ? "win32" : "linux",
      provider_cwd: text(PROVIDER_CWD), input: text(input), host: null, preconditions: {},
      expect: text(resolvePath(PROVIDER_CWD, input)) });
  });
  if (WIN) {
    const env = Object.fromEntries(Object.entries(process.env).filter(([k]) => !k.startsWith("=")));
    const groups = [["rooted", "ordinary", [...R1, ...R2]], ["rooted-extended", "extended", R4]];
    for (const [group, form, inputs] of groups) {
      inputs.forEach((input, n) => {
        const runs = [cwdA, cwdB].map((ordinary) => {
          const cwd = form === "extended" ? EXTENDED + ordinary : ordinary;
          const r = spawnSync(process.execPath, ["--no-warnings", process.argv[1], "child", piDir, JSON.stringify(input)],
            { env, cwd, encoding: "utf8" });
          if (r.status !== 0) throw new Error(`child failed: ${r.stderr}`);
          const o = JSON.parse(r.stdout);
          if (o.leaked.length) throw new Error(`child saw '='-prefixed entries ${o.leaked}`);
          if (o.cwd !== cwd) throw new Error(`child cwd ${JSON.stringify(o.cwd)} is not the crafted ${JSON.stringify(cwd)}`);
          return { ordinary, out: o.out };
        });
        const expect = templateOf(runs[0].out, runs[0].ordinary);
        for (const r of runs) {
          if (instantiate(expect, r.ordinary) !== r.out) {
            throw new Error(`template ${JSON.stringify(expect)} does not reproduce ${r.out} under ${r.ordinary}`);
          }
        }
        cases.push({
          id: `host/${group}/${String(n + 1).padStart(2, "0")}`,
          platform: "win32", provider_cwd: text(PROVIDER_CWD), input: text(input),
          host: { drive: "cwd", entry: null, cwd_form: form },
          preconditions: { process_cwd_drive_not: ["C"] },
          expect: { parts: expect },
        });
      });
    }
  }
  console.log(JSON.stringify({ platform: WIN ? "win32" : "linux", node: process.version, pi: PI, cases }));
} else {
  throw new Error("usage: generate <piDir> <cwdA> <cwdB> | child <piDir> <inputJSON>");
}
