// WP-14.2 Pi oracle for HAR-002 (formatSkillsForSystemPrompt) and HAR-014 (formatSkillInvocation):
// every expected string comes from the byte-copied pinned harness functions; nothing is re-implemented.
// Backslashes, control characters and surrogates are built from code units, so no tool rewrites them.
// Run: node --experimental-strip-types --no-warnings gen.mjs <out.json>
import { writeFileSync } from "node:fs";
import { formatSkillInvocation } from "../14-wp141/pinned/skills.ts";
import { formatSkillsForSystemPrompt } from "../14-wp141/pinned/system-prompt.ts";

const out = process.argv[2];
const B = String.fromCharCode(92); // backslash
const NL = String.fromCharCode(10);
const CR = String.fromCharCode(13);
const TAB = String.fromCharCode(9);
const CTL = String.fromCharCode(1);
const LONE = String.fromCharCode(0xd800);
const EMOJI = String.fromCodePoint(0x1f600);
const win = (...parts) => parts.join(B);

const sk = (name, extra = {}) => ({
	name,
	description: `${name} description`,
	content: `# ${name}${NL}body`,
	filePath: `/skills/${name}/SKILL.md`,
	disableModelInvocation: false,
	...extra,
});
const block = [
	{ id: "b01-empty", skills: [] },
	{ id: "b02-one", skills: [sk("alpha")] },
	{ id: "b03-many-order-kept", skills: [sk("zeta"), sk("alpha"), sk("mid")] },
	{ id: "b04-duplicates-kept", skills: [sk("dup"), sk("dup", { description: "second" })] },
	{ id: "b05-all-disabled", skills: [sk("a", { disableModelInvocation: true }), sk("b", { disableModelInvocation: true })] },
	{ id: "b06-some-disabled", skills: [sk("a"), sk("b", { disableModelInvocation: true }), sk("c")] },
	{
		id: "b07-five-escapes",
		skills: [sk("esc&<>", { description: `a & b < c > d " e ' f &amp; ]]> </available_skills>`, filePath: `/s/"q'&<>/SKILL.md` })],
	},
	{ id: "b08-pass-through", skills: [sk("pt", { description: `line1${NL}line2${CR}${NL}${TAB}tab ${CTL}ctl ${EMOJI} astral` })] },
	{ id: "b09-windows-location", skills: [sk("win", { filePath: win("C:", "Users", "me", "skills", "win", "SKILL.md") })] },
	{ id: "b10-empty-strings", skills: [sk("", { description: "", filePath: "" })] },
];
const dirs = [
	"/skills/a/SKILL.md",
	"/skills/a/SKILL.md/",
	"/skills/a/SKILL.md///",
	"/SKILL.md",
	"SKILL.md",
	"/",
	"",
	win("C:", "skills", "a", "SKILL.md"),
	win("C:", "SKILL.md"),
	"C:/SKILL.md",
	win("C:", ""),
	"C:",
	win("", "SKILL.md"),
	`a${B}b/c.md`,
	`a/b${B}c.md`,
	"//server/share/x.md",
	win("", "", "server", "share", "x.md"),
	win("x:", ""),
	win("ab:", "c.md"),
	"/a:b/c.md",
	`/skills/a${B}${B}`,
	win("C:", "dir", ""),
];
const invocation = [
	...dirs.map((p, i) => ({ id: `v${String(i + 1).padStart(2, "0")}-dirname`, skill: sk("s", { filePath: p }) })),
	{ id: "v90-no-escaping", skill: sk(`n"&<>'`, { filePath: `/p"&<>'/SKILL.md`, content: "</skill> & <x>" }) },
	{ id: "v91-additional", skill: sk("s"), additional: "Do it now." },
	{ id: "v92-additional-empty", skill: sk("s"), additional: "" },
	{ id: "v93-disabled-still-invocable", skill: sk("s", { disableModelInvocation: true }) },
	{ id: "v94-pass-through", skill: sk("s", { content: `x${CR}${NL}${EMOJI}${CTL}` }) },
];
// WP142-R001 (Owner): lone surrogates are outside the Minion string domain. Pinned Pi's results for them are
// kept as characterization evidence only (out-of-domain.json), never as Minion expectations.
const outOfDomain = {
	skills_block: [{ id: "x-b08-lone-surrogate-description", skills: [sk("pt", { description: `a ${LONE} b` })] }],
	invocation: [{ id: "x-v94-lone-surrogate-content", skill: sk("s", { content: `x${LONE}y` }) }],
};
const rows = {
	skills_block: block.map((c) => ({ ...c, expected: formatSkillsForSystemPrompt(c.skills) })),
	invocation: invocation.map((c) => ({
		...c,
		expected: c.additional === undefined ? formatSkillInvocation(c.skill) : formatSkillInvocation(c.skill, c.additional),
	})),
};
writeFileSync(out, JSON.stringify(rows, null, 1));
const ood = {
	note: "OUTSIDE the WP-14.2 string domain (Owner decision WP142-R001): pinned Pi results kept as characterization only",
	skills_block: outOfDomain.skills_block.map((c) => ({ ...c, pi: formatSkillsForSystemPrompt(c.skills) })),
	invocation: outOfDomain.invocation.map((c) => ({ ...c, pi: formatSkillInvocation(c.skill) })),
};
writeFileSync(out.replace(/oracle\.json$/, "out-of-domain.json"), JSON.stringify(ood, null, 1));
console.log(`${rows.skills_block.length} block + ${rows.invocation.length} invocation cases -> ${out}`);
