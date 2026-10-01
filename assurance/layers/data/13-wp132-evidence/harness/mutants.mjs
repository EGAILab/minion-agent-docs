// WP-13.2 corpus discrimination: each single-point mutant of the pinned Pi edit-diff.ts or diff@8.0.4 source, run
// through the SAME corpus, must change at least one authority result. Run inside the authority container after
// run_authority.sh (uses $STAGE_DIR/a as the pristine authority tree and $OUT_DIR/authority.json as the baseline;
// defaults /tmp/s and /out, the container layout).
import { cpSync, readFileSync, writeFileSync, rmSync } from "node:fs";
import { execFileSync } from "node:child_process";

const STAGE = process.env.STAGE_DIR || "/tmp/s";
const OUT = process.env.OUT_DIR || "/out";
const ROOT = `${STAGE}/a`;
const baseline = JSON.parse(readFileSync(`${OUT}/authority.json`, "utf8")).results;
const M = [
  ["exact-only uniqueness counting", "pi/core/tools/edit-diff.ts",
   "const fuzzyContent = normalizeForFuzzyMatch(content);\n\tconst fuzzyOldText = normalizeForFuzzyMatch(oldText);\n\treturn fuzzyContent.split(fuzzyOldText).length - 1;",
   "return content.split(oldText).length - 1;"],
  ["fuzzy only when every edit needs it (not per call)", "pi/core/tools/edit-diff.ts",
   "const usedFuzzyMatch = initialMatches.some((match) => match.usedFuzzyMatch);",
   "const usedFuzzyMatch = initialMatches.every((match) => match.usedFuzzyMatch);"],
  ["trailing-whitespace trim of space/tab only", "pi/core/tools/edit-diff.ts",
   ".map((line) => line.trimEnd())", ".map((line) => line.replace(/[ \\t]+$/, \"\"))"],
  ["NFC instead of NFKC", "pi/core/tools/edit-diff.ts", '.normalize("NFKC")', '.normalize("NFC")'],
  ["line endings never restored", "pi/core/tools/edit-diff.ts",
   'return ending === "\\r\\n" ? text.replace(/\\n/g, "\\r\\n") : text;', "return text;"],
  ["lone CR not normalized", "pi/core/tools/edit-diff.ts",
   'return text.replace(/\\r\\n/g, "\\n").replace(/\\r/g, "\\n");', 'return text.replace(/\\r\\n/g, "\\n");'],
  ["unchanged lines not preserved under fuzzy", "pi/core/tools/edit-diff.ts",
   "? applyReplacementsPreservingUnchangedLines(normalizedContent, replacementBaseContent, matchedEdits)",
   "? applyReplacements(replacementBaseContent, matchedEdits)"],
  ["adjacent edits treated as overlapping", "pi/core/tools/edit-diff.ts",
   "if (previous.matchIndex + previous.matchLength > current.matchIndex) {",
   "if (previous.matchIndex + previous.matchLength >= current.matchIndex) {"],
  ["BOM dropped on write", "edit_authority.mjs", "const finalContent = bom + restoreLineEndings", "const finalContent = restoreLineEndings"],
  ["write reports UTF-8 bytes", "edit_authority.mjs",
   "text: `Successfully wrote ${c.content.length} bytes to ${c.path}`",
   "text: `Successfully wrote ${Buffer.byteLength(c.content)} bytes to ${c.path}`"],
  ["Myers tie-break <=", "node_modules/diff/libesm/diff/base.js",
   "if (!canRemove || (canAdd && removePath.oldPos < addPath.oldPos)) {",
   "if (!canRemove || (canAdd && removePath.oldPos <= addPath.oldPos)) {"],
  ["patch context joining at < 2*context", "node_modules/diff/libesm/patch/create.js",
   "if (lines.length <= context * 2 && i < diff.length - 2) {", "if (lines.length < context * 2 && i < diff.length - 2) {"],
  ["no 'No newline at end of file' marker", "node_modules/diff/libesm/patch/create.js",
   "hunk.lines.splice(i + 1, 0, '\\\\ No newline at end of file');\n                    i++; // Skip the line we just added, then continue iterating",
   "// marker removed"],
];
const out = [];
for (const [name, file, from, to] of M) {
  const dir = `${STAGE}/mut`;
  rmSync(dir, { recursive: true, force: true });
  cpSync(ROOT, dir, { recursive: true });
  const path = `${dir}/${file}`;
  const src = readFileSync(path, "utf8");
  const count = src.split(from).length - 1;
  if (count !== 1) { out.push({ name, error: `anchor count ${count}` }); continue; }
  writeFileSync(path, src.replace(from, to));
  execFileSync("node", ["--experimental-strip-types", "--no-warnings", "edit_authority.mjs", `${STAGE}/cases.json`, `${STAGE}/mut.json`], { cwd: dir });
  const mutated = JSON.parse(readFileSync(`${STAGE}/mut.json`, "utf8")).results;
  const changed = mutated.filter((r, i) => JSON.stringify(r) !== JSON.stringify(baseline[i])).map((r) => r.id);
  out.push({ name, file, killed: changed.length > 0, changed_cases: changed.length, examples: changed.slice(0, 5) });
}
writeFileSync(`${OUT}/mutants.json`, JSON.stringify(out, null, 1));
for (const r of out) console.log(r.error ? `ERROR | ${r.name}: ${r.error}` : `${r.killed ? "KILLED" : "SURVIVED"} | ${r.name} (${r.changed_cases} cases: ${r.examples.join(", ")})`);
