// WP-14.2 HAR-018 oracle: Pi's tool snippet/guideline normalization and rendering, from pinned sources.
// - The normalizers are sliced byte-for-byte from coding-agent agent-session.ts (asserted exact slices).
// - Rendering is pinned coding-agent buildSystemPrompt itself; only its two unrelated imports are stubbed.
// - The Minion model applies EXACTLY the non-adopted-text removals as asserted patches (HAR-018):
//   the "(none)" fallback, the bash-only bullet and the two fixed bullets.
// Output: per case, Pi's "Available tools:" and "Guidelines:" blocks and the Minion tools section.
// Run (Node v22.15.1): node --experimental-strip-types --no-warnings tools-oracle.mjs <pi-src-dir> <out.json>
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
import { blocks, minionSection, naiveBlocks, renderOptions } from "./tools-model.mjs";

const [piCore, out] = process.argv.slice(2);
const work = join(import.meta.dirname, "gen");
mkdirSync(work, { recursive: true });
const NL = String.fromCharCode(10);

function once(text, needle, label) {
	const n = text.split(needle).length - 1;
	if (n !== 1) throw new Error(`${label}: expected exactly one match, found ${n}`);
}
function slice(text, start, end, label) {
	once(text, start, label);
	const i = text.indexOf(start);
	const j = text.indexOf(end, i);
	if (j < 0) throw new Error(`${label}: end not found`);
	return text.slice(i, j + end.length);
}

// 1. normalizers, sliced from the pinned private methods
const session = readFileSync(join(piCore, "agent-session.ts"), "utf8");
const snippet = slice(session, "\tprivate _normalizePromptSnippet(", NL + "\t}" + NL, "snippet");
const guidelines = slice(session, "\tprivate _normalizePromptGuidelines(", NL + "\t}" + NL, "guidelines");
// The collection loop of _rebuildSystemPrompt, asserted present verbatim; mirrored below as collect().
for (const line of [
	"const validToolNames = toolNames.filter((name) => this._toolRegistry.has(name));",
	"const snippet = this._toolPromptSnippets.get(name);",
	"toolSnippets[name] = snippet;",
	"const toolGuidelines = this._toolPromptGuidelines.get(name);",
	"promptGuidelines.push(...toolGuidelines);",
]) once(session, line, `collection loop: ${line}`);
const normalizers = [snippet, guidelines]
	.map((m) => m.replace("\tprivate _normalizePromptSnippet(", "export function normalizeSnippet(").replace("\tprivate _normalizePromptGuidelines(", "export function normalizeGuidelines("))
	.join(NL);
writeFileSync(join(work, "normalize.ts"), normalizers);

// 2. rendering: pinned buildSystemPrompt, unrelated imports stubbed
const sp = readFileSync(join(piCore, "system-prompt.ts"), "utf8");
const imp1 = 'import { getDocsPath, getExamplesPath, getReadmePath } from "../config.ts";';
const imp2 = 'import { formatSkillsForPrompt, type Skill } from "./skills.ts";';
once(sp, imp1, "config import");
once(sp, imp2, "skills import");
const stubbed = sp
	.replace(imp1, 'const getDocsPath = () => "<docs>"; const getExamplesPath = () => "<examples>"; const getReadmePath = () => "<readme>";')
	.replace(imp2, 'type Skill = never; const formatSkillsForPrompt = (_: unknown[]) => "";');
writeFileSync(join(work, "pi-system-prompt.ts"), stubbed);

// 3. Minion model: the non-adopted text removed, each patch asserted
const patches = [
	['visibleTools.length > 0 ? visibleTools.map((name) => `- ${name}: ${toolSnippets![name]}`).join("\\n") : "(none)";',
	 'visibleTools.length > 0 ? visibleTools.map((name) => `- ${name}: ${toolSnippets![name]}`).join("\\n") : "";'],
	['addGuideline("Use bash for file operations like ls, rg, find");', "/* not adopted */"],
	['addGuideline("Be concise in your responses");', "/* not adopted */"],
	['addGuideline("Show file paths clearly when working with files");', "/* not adopted */"],
];
let model = stubbed;
for (const [a, b] of patches) {
	once(model, a, `model patch: ${a.slice(0, 40)}`);
	model = model.replace(a, b);
}
writeFileSync(join(work, "model-system-prompt.ts"), model);

const { normalizeSnippet, normalizeGuidelines } = await import(pathToFileURL(join(work, "normalize.ts")).href);
const pi = await import(pathToFileURL(join(work, "pi-system-prompt.ts")).href);
const mo = await import(pathToFileURL(join(work, "model-system-prompt.ts")).href);

const ws = (cps) => cps.map((c) => String.fromCodePoint(c)).join("");
const CR = String.fromCharCode(13);
const cases = [
	{ id: "t01-none", tools: [{ name: "read" }, { name: "bash" }] },
	{ id: "t02-snippet-only", tools: [{ name: "read", snippet: "Read a file" }] },
	{ id: "t03-guidelines-only", tools: [{ name: "read", guidelines: ["Prefer read over cat"] }] },
	{ id: "t04-both-order", tools: [{ name: "zeta", snippet: "Z", guidelines: ["gz"] }, { name: "alpha", snippet: "A", guidelines: ["ga"] }] },
	{ id: "t05-snippet-newlines", tools: [{ name: "t", snippet: `line1${CR}${NL}line2${NL}${NL}line3` }] },
	{ id: "t06-snippet-js-whitespace", tools: [{ name: "t", snippet: `${ws([0xfeff])}a${ws([0xa0, 0x3000, 0x2028])}b${ws([0x9, 0xb, 0xc, 0x20, 0x1680])}` }] },
	{ id: "t07-snippet-empty-after-trim", tools: [{ name: "t", snippet: ws([0x20, 0xa0, 0xfeff]) }, { name: "u", snippet: "" }] },
	{ id: "t08-guidelines-trim-drop-dedupe", tools: [{ name: "t", guidelines: [" g1 ", "", "  ", "g1", "g2", `${ws([0xfeff])}g2${ws([0x3000])}`] }] },
	{ id: "t09-cross-tool-dedupe", tools: [{ name: "a", guidelines: ["shared", "only-a"] }, { name: "b", guidelines: ["only-b", "shared"] }] },
	{ id: "t10-guideline-equals-fixed-bullet", tools: [{ name: "a", guidelines: ["Be concise in your responses", "x"] }] },
	{ id: "t11-bash-without-search-tools", tools: [{ name: "bash", snippet: "Run" }] },
	{ id: "t12-inner-whitespace-kept-in-guideline", tools: [{ name: "a", guidelines: [`a${NL}b  c`] }] },
	{ id: "t13-mixed", tools: [{ name: "read", snippet: "Read" }, { name: "x" }, { name: "edit", guidelines: ["Edit carefully"] }] },
	// WP142-R002: guidelines whose text holds blank lines (trim-only normalization preserves them)
	{ id: "t14-guideline-with-blank-lines", tools: [{ name: "a", guidelines: [`first${NL}${NL}second`] }] },
	{ id: "t15-multiline-dedupe-per-tool", tools: [{ name: "a", guidelines: [`p1${NL}${NL}p2`, `p1${NL}${NL}p2`, "other"] }] },
	{
		id: "t16-multiline-dedupe-cross-tool",
		tools: [{ name: "a", snippet: "A", guidelines: [`x${NL}${NL}y`] }, { name: "b", guidelines: [`x${NL}${NL}y`, "z"] }],
	},
];
const rows = cases.map((c) => {
	const opts = renderOptions(c.tools, normalizeSnippet, normalizeGuidelines);
	const piPrompt = pi.buildSystemPrompt(opts);
	return { ...c, pi: blocks(piPrompt), minion_tools_section: minionSection(mo.buildSystemPrompt(opts)) };
});
// Negative control (WP142-R002): the superseded blank-line extractor must disagree on every
// multi-paragraph witness, and agree everywhere else.
for (const c of cases) {
	const opts = renderOptions(c.tools, normalizeSnippet, normalizeGuidelines);
	const piPrompt = pi.buildSystemPrompt(opts);
	const same = JSON.stringify(naiveBlocks(piPrompt).guidelines) === JSON.stringify(blocks(piPrompt).guidelines);
	const multiline = /^t1[4-6]-/.test(c.id);
	if (multiline === same) throw new Error(`negative control: naive extractor ${same ? "survived" : "broke"} on ${c.id}`);
}
console.log("negative control: naive blank-line extractor killed by t14, t15, t16 only");
writeFileSync(out, JSON.stringify(rows, null, 1));
console.log(`${rows.length} tool-metadata cases -> ${out}`);
