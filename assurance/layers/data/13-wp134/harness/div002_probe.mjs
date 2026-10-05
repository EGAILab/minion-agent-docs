// WP-13.4 DIV-002 feasibility evidence (minion-agent#51, Owner Q1). Windows only, pinned fd 10.4.2.
// For every full-path find pattern of the characterization corpus, run fd exactly as pinned Pi's find.ts builds the
// command on Windows (Pi's "/" -> "[/\\]" rewrite) and with ONE candidate normalization that keeps the zero-directory
// meaning of each "**/" component ("/**/" -> "{sep,sep**sep}" before the rewrite). Results are relativized as Pi does
// and compared with pinned Pi's Linux output for the same case (out/search-linux.json). This file is evidence that
// a correction exists; it is NOT the normative algorithm (the contract specifies only the observable behaviour).
//   node div002_probe.mjs <fd.exe> <scratch dir> <out/search-linux.json> <out.json>
import { spawnSync } from "node:child_process";
import { mkdirSync, mkdtempSync, readFileSync, realpathSync, rmSync, writeFileSync } from "node:fs";
import path, { join } from "node:path";

const [fd, scratch, linuxPath, outPath] = process.argv.slice(2);
const linux = JSON.parse(readFileSync(linuxPath, "utf8"));
const root = realpathSync(mkdtempSync(join(scratch, "div002-")));
const files = ["src/a.ts", "src/b.spec.ts", "src/sub/c.ts", "src/sub/d.spec.ts", "src/sub/deep/er/e.spec.ts",
  "src/.hidden.ts", "space dir/f.ts", "ünïcode/文件.ts"];
for (const f of files) { const p = join(root, ...f.split("/")); mkdirSync(path.dirname(p), { recursive: true }); writeFileSync(p, "x\n"); }
const S = String.raw`[/\\]`;
const piEffective = (pattern) => (pattern.startsWith("/") || pattern.startsWith("**/") || pattern === "**") ? pattern : `**/${pattern}`;
const forms = {
  pi: (e) => e.replaceAll("/", S),
  candidate: (e) => e.replaceAll("/**/", "\u0000").replaceAll("/", S).replaceAll("\u0000", `{${S},${S}**${S}}`),
};
const cases = ["full-path-spec", "full-path-star", "full-path-star-sub", "full-path-deep", "full-path-question",
  "full-path-two-doublestar", "full-path-trailing-doublestar", "space-dir", "unicode-dir-fullpath"];
const out = { fd: spawnSync(fd, ["--version"]).stdout.toString().trim(), cases: {} };
for (const name of cases) {
  const pattern = linux.find[`plain/${name}`].args.pattern;
  const linuxSet = linux.find[`plain/${name}`].text.split("\n").filter((l) => !l.startsWith("No files")).sort();
  const row = { pattern, linux: linuxSet };
  for (const [form, f] of Object.entries(forms)) {
    const r = spawnSync(fd, ["--glob", "--color=never", "--hidden", "--no-require-git", "--max-results", "1000",
      "--full-path", "--", f(piEffective(pattern)), root]);
    const got = r.stdout.toString().split(/\r?\n/).map((l) => l.trim()).filter(Boolean)
      .map((l) => path.relative(root, l).split(path.sep).join("/") + (l.endsWith(path.sep) || l.endsWith("/") ? "/" : "")).sort();
    // compare only within the files this smaller tree contains
    const expected = linuxSet.filter((p) => files.includes(p) || files.some((f) => f.startsWith(p)));
    row[form] = { pattern: f(piEffective(pattern)), results: got, equalsLinux: JSON.stringify(got) === JSON.stringify(expected) };
  }
  out.cases[name] = row;
}
rmSync(root, { recursive: true, force: true });
writeFileSync(outPath, JSON.stringify(out, null, 1) + "\n");
for (const [k, v] of Object.entries(out.cases)) console.log(k.padEnd(30), "pi==linux:", v.pi.equalsLinux, " candidate==linux:", v.candidate.equalsLinux);
