// WP-14.2 canonical scenarios (conformance/agent/prompt-assembly/), one document per case.
// - skills_block / invocation: expected = the pinned harness functions (oracle.json, DIRECT_PI_PARITY).
// - tools_section: expected = the Minion model of pinned buildSystemPrompt (tools-oracle.json), with
//   Pi's own blocks recorded as `pi_reference`.
// - compose: expected = the HAR-015 mapping over the same pinned functions (the join rule below is the
//   Minion mapping itself, PP-14-4; it is the only rule written here).
// Strings: a plain JSON string, or {"utf16": [units]} when the text holds a lone surrogate.
// Run (Node v22.15.1): node --experimental-strip-types --no-warnings gen-canonical.mjs <out dir>
// (after tools-oracle.mjs, which writes gen/model-system-prompt.ts and gen/normalize.ts)
import { mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
import { formatSkillsForSystemPrompt } from "../14-wp141/pinned/system-prompt.ts";

const outDir = process.argv[2];
const here = import.meta.dirname;
const PI_REVISION = "b7bb00b936dbe21b8e160b3e89efdec361846699";
const NL = String.fromCharCode(10);
const LONE = String.fromCharCode(0xd800);

// true when s holds an unpaired surrogate, which a plain JSON string cannot carry portably
function hasLoneSurrogate(s) {
	for (let i = 0; i < s.length; i++) {
		const c = s.charCodeAt(i);
		if (c >= 0xd800 && c <= 0xdbff) {
			const d = i + 1 < s.length ? s.charCodeAt(i + 1) : 0;
			if (d >= 0xdc00 && d <= 0xdfff) i++;
			else return true;
		} else if (c >= 0xdc00 && c <= 0xdfff) return true;
	}
	return false;
}
function units(s) {
	const out = [];
	for (let i = 0; i < s.length; i++) out.push(s.charCodeAt(i));
	return out;
}
const jsx = (s) => (hasLoneSurrogate(s) ? { utf16: units(s) } : s);
const skill = (k) => ({
	name: jsx(k.name),
	description: jsx(k.description),
	content: jsx(k.content),
	file_path: jsx(k.filePath),
	disable_model_invocation: k.disableModelInvocation === true,
});
const tool = (t) => {
	const o = { name: t.name };
	if (t.snippet !== undefined) o.snippet = jsx(t.snippet);
	if (t.guidelines !== undefined) o.guidelines = t.guidelines.map(jsx);
	return o;
};

const oracle = JSON.parse(readFileSync(join(here, "oracle.json"), "utf8"));
const tools = JSON.parse(readFileSync(join(here, "tools-oracle.json"), "utf8"));
const model = await import(pathToFileURL(join(here, "gen", "model-system-prompt.ts")).href);
const { normalizeSnippet, normalizeGuidelines } = await import(pathToFileURL(join(here, "gen", "normalize.ts")).href);

const docs = [];
const doc = (id, requirements, authority, kind, input, expected, extra = {}) =>
	docs.push({
		name: `prompt-${id}`,
		family: "agent",
		authority,
		pi_revision: PI_REVISION,
		requirements,
		prompt_assembly: { kind, input, expected: jsx(expected), ...extra },
	});

const PI_HARNESS = "pinned Pi packages/agent/src/harness (system-prompt.ts formatSkillsForSystemPrompt, skills.ts formatSkillInvocation), byte-copied; DIRECT_PI_PARITY";
for (const r of oracle.skills_block) doc(r.id, ["HAR-002"], PI_HARNESS, "skills_block", { skills: r.skills.map(skill) }, r.expected);
for (const r of oracle.invocation) {
	const input = { skill: skill(r.skill) };
	if (r.additional !== undefined) input.additional_instructions = jsx(r.additional);
	doc(r.id, ["HAR-014"], PI_HARNESS, "invocation", input, r.expected);
}
const PI_TOOLS = "Minion model of pinned Pi coding-agent buildSystemPrompt + agent-session normalizers (tools-oracle.mjs; asserted removals of non-adopted text); MINION_EXTENSION, PP-14-5 Option B";
for (const r of tools)
	doc(r.id, ["HAR-018"], PI_TOOLS, "tools_section", { tools: r.tools.map(tool) }, r.minion_tools_section, {
		pi_reference: { available_tools: r.pi.tools, guidelines: r.pi.guidelines },
	});

// HAR-015 compose: the mapping (PP-14-4) over pinned functions
function toolsSection(ts) {
	const toolSnippets = {};
	const promptGuidelines = [];
	for (const t of ts) {
		const s = normalizeSnippet(t.snippet);
		if (s) toolSnippets[t.name] = s;
		const g = normalizeGuidelines(t.guidelines);
		if (g.length > 0) promptGuidelines.push(...g);
	}
	const p = model.buildSystemPrompt({ selectedTools: ts.map((t) => t.name), toolSnippets, promptGuidelines, cwd: "/" });
	const parts = p.split(NL + NL).filter((b) => (b.startsWith("Available tools:") && b !== "Available tools:") || (b.startsWith("Guidelines:") && b !== "Guidelines:"));
	return parts.join(NL + NL);
}
function compose({ base, tools: ts, tools_section, sections, skills }) {
	const list = [base, tools_section ? toolsSection(ts) : "", ...sections];
	if (ts.some((t) => t.name === "read")) list.push(formatSkillsForSystemPrompt(skills));
	return list.filter((s) => s !== "").join(NL + NL);
}
const sk = (name, extra = {}) => ({ name, description: `${name} description`, content: `# ${name}`, filePath: `/skills/${name}/SKILL.md`, disableModelInvocation: false, ...extra });
const read = { name: "read", snippet: "Read a file", guidelines: ["Read before editing"] };
const bash = { name: "bash", snippet: "Run a command" };
const composeCases = [
	{ id: "c01-base-only", base: "You are helpful.", tools: [], tools_section: false, sections: [], skills: [] },
	{ id: "c02-everything", base: "BASE", tools: [read, bash], tools_section: true, sections: ["APPEND-1", "APPEND-2"], skills: [sk("alpha"), sk("beta")] },
	{ id: "c03-read-gate-closed", base: "BASE", tools: [bash], tools_section: true, sections: [], skills: [sk("alpha")] },
	{ id: "c04-read-gate-open-no-snippet", base: "BASE", tools: [{ name: "read" }], tools_section: false, sections: [], skills: [sk("alpha")] },
	{ id: "c05-tools-section-disabled", base: "BASE", tools: [read], tools_section: false, sections: [], skills: [] },
	{ id: "c06-tools-section-enabled-no-metadata", base: "BASE", tools: [{ name: "read" }, { name: "x" }], tools_section: true, sections: [], skills: [] },
	{ id: "c07-empty-base", base: "", tools: [read], tools_section: true, sections: ["S"], skills: [sk("alpha")] },
	{ id: "c08-empty-sections-skipped", base: "BASE", tools: [], tools_section: false, sections: ["", "S", ""], skills: [] },
	{ id: "c09-all-skills-disabled", base: "BASE", tools: [read], tools_section: false, sections: [], skills: [sk("a", { disableModelInvocation: true })] },
	{ id: "c10-all-empty", base: "", tools: [], tools_section: true, sections: [""], skills: [] },
	{ id: "c11-section-with-blank-lines", base: `B${NL}`, tools: [], tools_section: false, sections: [`${NL}S${NL}${NL}`], skills: [] },
	{ id: "c12-read-named-exactly", base: "BASE", tools: [{ name: "Read" }, { name: "read_file" }], tools_section: false, sections: [], skills: [sk("alpha")] },
	{ id: "c13-lone-surrogate-base", base: `x${LONE}y`, tools: [], tools_section: false, sections: [], skills: [] },
];
const MAPPING = "MINION_ARCHITECTURAL_MAPPING (PP-14-4, HAR-015 order and join) over the pinned harness skills block and the HAR-018 Minion model";
for (const c of composeCases)
	doc(c.id, ["HAR-015", "HAR-002", "HAR-018"], MAPPING, "compose", {
		base: jsx(c.base),
		tools: c.tools.map(tool),
		tools_section: c.tools_section,
		sections: c.sections.map(jsx),
		skills: c.skills.map(skill),
	}, compose(c));

mkdirSync(outDir, { recursive: true });
for (const f of readdirSync(outDir)) if (f.endsWith(".json")) rmSync(join(outDir, f));
for (const d of docs) writeFileSync(join(outDir, `${d.name}.json`), JSON.stringify(d, null, 1) + NL);
console.log(`${docs.length} canonical scenarios -> ${outDir}`);
