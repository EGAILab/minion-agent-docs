// WP-14.2 HAR-018 shared evidence helpers, used by tools-oracle.mjs and gen-canonical.mjs.
// - collect(): _rebuildSystemPrompt's per-tool collection loop (asserted present verbatim by
//   tools-oracle.mjs), over the snapshot in order.
// - blocks(): Pi's "Available tools:" and "Guidelines:" regions of a rendered default prompt,
//   delimited by the fixed text around each region, never by blank lines (WP142-R002).
// - minionSection(): the Minion tools section from the Minion model's rendering.
const NL = String.fromCharCode(10);
const TOOLS_START = "Available tools:" + NL;
const TOOLS_END = NL + NL + "In addition to the tools above, you may have access to other custom tools";
const GUIDE_START = NL + NL + "Guidelines:" + NL;
const GUIDE_END = NL + NL + "Pi documentation (read only when the user asks about pi itself";

export function collect(tools, normalizeSnippet, normalizeGuidelines) {
	const toolSnippets = {};
	const promptGuidelines = [];
	for (const t of tools) {
		const s = normalizeSnippet(t.snippet);
		if (s) toolSnippets[t.name] = s;
		const g = normalizeGuidelines(t.guidelines);
		if (g.length > 0) promptGuidelines.push(...g);
	}
	return { toolSnippets, promptGuidelines };
}

function region(prompt, start, end) {
	const i = prompt.indexOf(start);
	const j = prompt.lastIndexOf(end);
	if (i < 0 || j < i) throw new Error(`rendered prompt lacks the expected ${JSON.stringify(start.trim())} region`);
	return prompt.slice(i, j).replace(/^\n\n/, "");
}

export function blocks(prompt) {
	return {
		tools: region(prompt, TOOLS_START, TOOLS_END).replace(/\n$/, ""),
		guidelines: region(prompt, GUIDE_START, GUIDE_END).replace(/\n$/, ""),
	};
}

// The superseded extractor, kept only as the negative control the multi-paragraph witnesses must kill.
export function naiveBlocks(prompt) {
	const tools = prompt.split(NL + NL).find((b) => b.startsWith("Available tools:")) ?? null;
	const guide = prompt.split(NL + NL).find((b) => b.startsWith("Guidelines:")) ?? null;
	return { tools, guidelines: guide };
}

// A region whose list rendered empty is its bare header line: absent in the Minion section.
export function minionSection(modelPrompt) {
	const { tools, guidelines } = blocks(modelPrompt);
	const parts = [];
	if (tools !== "Available tools:") parts.push(tools);
	if (guidelines !== "Guidelines:") parts.push(guidelines);
	return parts.join(NL + NL);
}

export function renderOptions(tools, normalizeSnippet, normalizeGuidelines) {
	const { toolSnippets, promptGuidelines } = collect(tools, normalizeSnippet, normalizeGuidelines);
	return { selectedTools: tools.map((t) => t.name), toolSnippets, promptGuidelines, cwd: "/" };
}
