// WP-14.1 characterization corpus. Each scenario is a fixture tree (relative to a fresh base
// directory) plus the loadSkills roots (relative to the base). The runner executes the byte-copied
// pinned harness loader through pinned NodeExecutionEnv on the real filesystem.
//
// Fixture entries: {path, text} file; {path, dir: true} directory; {path, symlink: target, dir?}.
// `posixOnly` marks scenarios whose names Windows cannot create.

const fm = (lines, body = "Body.") => `---\n${lines.join("\n")}\n---\n${body}`;
const skill = (name, description = `Use ${name}.`) => fm([`name: ${name}`, `description: ${description}`]);
const astral = "\u{1F600}";

export const scenarios = [
	// ---- discovery and traversal -------------------------------------------------------------
	{ id: "d01-single-skill-dir", fixture: [{ path: "skills/alpha/SKILL.md", text: skill("alpha") }], roots: ["skills"] },
	{
		id: "d02-root-skill-md-short-circuits",
		fixture: [
			{ path: "skills/SKILL.md", text: skill("skills") },
			{ path: "skills/beta/SKILL.md", text: skill("beta") },
			{ path: "skills/gamma.md", text: skill("gamma") },
		],
		roots: ["skills"],
	},
	{
		id: "d03-invalid-skill-md-still-short-circuits",
		fixture: [
			{ path: "skills/alpha/SKILL.md", text: fm(["name: alpha"]) },
			{ path: "skills/alpha/inner/SKILL.md", text: skill("inner") },
		],
		roots: ["skills"],
	},
	{
		id: "d04-ignored-skill-md-does-not-short-circuit",
		fixture: [
			{ path: "skills/.gitignore", text: "alpha/SKILL.md\n" },
			{ path: "skills/alpha/SKILL.md", text: skill("alpha") },
			{ path: "skills/alpha/inner/SKILL.md", text: skill("inner") },
		],
		roots: ["skills"],
	},
	{
		id: "d05-sorted-traversal-order",
		fixture: ["b", "a", "_x", "-y", "e", "\u00e9", "Z", "a10", "a9", "a-b", "a_b"].map((n) => ({
			path: `skills/${n}/SKILL.md`,
			text: fm([`description: Skill in ${n}.`]),
		})),
		roots: ["skills"],
	},
	{
		id: "d06-dotfiles-and-node-modules-skipped",
		fixture: [
			{ path: "skills/.hidden/SKILL.md", text: skill("hidden") },
			{ path: "skills/node_modules/dep/SKILL.md", text: skill("dep") },
			{ path: "skills/.root.md", text: skill("root") },
			{ path: "skills/visible/SKILL.md", text: skill("visible") },
		],
		roots: ["skills"],
	},
	{
		id: "d05p-case-variant-order",
		posixOnly: true,
		fixture: ["b", "B", "a", "A", "é", "É", "e", "E"].map((n) => ({ path: `skills/${n}/SKILL.md`, text: fm([`description: Skill in ${n}.`]) })),
		roots: ["skills"],
	},
	{
		id: "d06p-node-modules-exact-name",
		posixOnly: true,
		fixture: [
			{ path: "skills/node_modules/dep/SKILL.md", text: skill("dep") },
			{ path: "skills/Node_Modules/dep2/SKILL.md", text: skill("dep2") },
		],
		roots: ["skills"],
	},
	{
		id: "d07-root-markdown-only-at-root",
		fixture: [
			{ path: "skills/direct.md", text: skill("direct") },
			{ path: "skills/sub/nested.md", text: skill("nested") },
			{ path: "skills/sub/deeper/SKILL.md", text: skill("deeper") },
		],
		roots: ["skills"],
	},
	{
		id: "d08-root-markdown-filters",
		fixture: [
			{ path: "skills/README.md", text: "# Readme\nNo frontmatter." },
			{ path: "skills/blank.md", text: fm(["name: blank", "description: '   '"]) },
			{ path: "skills/upper.MD", text: skill("upper") },
			{ path: "skills/notes.txt", text: skill("notes") },
			{ path: "skills/broken.md", text: fm(["name: broken", "name: twice"]) },
			{ path: "skills/ok.md", text: skill("skills") },
		],
		roots: ["skills"],
	},
	{
		id: "d09-root-markdown-name-mismatch-quirk",
		fixture: [
			{ path: "skills/other.md", text: skill("other") },
			{ path: "skills/noname.md", text: fm(["description: No name."]) },
		],
		roots: ["skills"],
	},
	{
		id: "d10-roots-missing-file-duplicate-order",
		fixture: [
			{ path: "one/a/SKILL.md", text: skill("a") },
			{ path: "two/b/SKILL.md", text: skill("b") },
			{ path: "afile.md", text: skill("afile") },
		],
		roots: ["two", "missing", "afile.md", "one", "two"],
	},
	{
		id: "d11-nested-depth",
		fixture: [
			{ path: "skills/a/b/c/SKILL.md", text: skill("c") },
			{ path: "skills/x/SKILL.md", text: skill("x") },
			{ path: "skills/x/y/SKILL.md", text: skill("y") },
		],
		roots: ["skills"],
	},
	{
		id: "d12-symlinks",
		fixture: [
			{ path: "real/linked/SKILL.md", text: skill("linked") },
			{ path: "real/file-target.md", text: skill("viafile") },
			{ path: "skills/linked", symlink: "../real/linked", dir: true },
			{ path: "skills/viafile/SKILL.md", symlink: "../../real/file-target.md" },
			{ path: "skills/dangling", symlink: "../nowhere", dir: true },
			{ path: "skills/plain/SKILL.md", text: skill("plain") },
		],
		roots: ["skills"],
	},
	{
		id: "d13-root-is-symlink",
		fixture: [
			{ path: "real/s/SKILL.md", text: skill("s") },
			{ path: "rootlink", symlink: "real", dir: true },
		],
		roots: ["rootlink"],
	},
	{
		id: "d14-duplicate-names-kept",
		fixture: [
			{ path: "skills/dup/SKILL.md", text: skill("dup", "First.") },
			{ path: "skills/other/dup/SKILL.md", text: skill("dup", "Second.") },
		],
		roots: ["skills"],
	},

	// ---- validation and diagnostics -----------------------------------------------------------
	{ id: "v01-invalid-name-loads-with-warnings", fixture: [{ path: "skills/Bad_Name/SKILL.md", text: fm(["description: d"]) }], roots: ["skills"] },
	{
		id: "v02-all-name-messages-in-order",
		fixture: [{ path: "skills/dir/SKILL.md", text: fm([`name: -A--${"x".repeat(70)}-`, "description: d"]) }],
		roots: ["skills"],
	},
	{
		id: "v03-description-length-utf16",
		fixture: [
			{ path: "skills/exact/SKILL.md", text: fm(["name: exact", `description: ${"a".repeat(1024)}`]) },
			{ path: "skills/over/SKILL.md", text: fm(["name: over", `description: ${"a".repeat(1023)}${astral}`]) },
			{ path: "skills/astral-ok/SKILL.md", text: fm(["name: astral-ok", `description: ${astral.repeat(512)}`]) },
		],
		roots: ["skills"],
	},
	{
		id: "v04-description-required-cases",
		fixture: [
			{ path: "skills/ws/SKILL.md", text: fm(["name: ws", "description: \"  \\t \""]) },
			{ path: "skills/num/SKILL.md", text: fm(["name: num", "description: 42"]) },
			{ path: "skills/none/SKILL.md", text: fm(["name: none"]) },
			{ path: "skills/nul/SKILL.md", text: fm(["name: nul", "description: ~"]) },
			{ path: "skills/list/SKILL.md", text: fm(["name: list", "description: [a, b]"]) },
			{ path: "skills/ideo/SKILL.md", text: fm(["name: ideo", "description: \"\\u3000\""]) },
			{ path: "skills/bomws/SKILL.md", text: fm(["name: bomws", "description: \"\\uFEFF\""]) },
		],
		roots: ["skills"],
	},
	{
		id: "v05-name-fallbacks",
		fixture: [
			{ path: "skills/numname/SKILL.md", text: fm(["name: 123", "description: d"]) },
			{ path: "skills/emptyname/SKILL.md", text: fm(["name: ''", "description: d"]) },
			{ path: "skills/boolname/SKILL.md", text: fm(["name: true", "description: d"]) },
		],
		roots: ["skills"],
	},
	{
		id: "v06-disable-model-invocation-values",
		fixture: [
			["t-true", "true"], ["t-cap", "True"], ["t-upper", "TRUE"], ["t-yes", "yes"], ["t-on", "on"],
			["t-str", "'true'"], ["t-one", "1"], ["t-false", "false"],
		].map(([n, v]) => ({ path: `skills/${n}/SKILL.md`, text: fm([`name: ${n}`, "description: d", `disable-model-invocation: ${v}`]) })),
		roots: ["skills"],
	},
	{
		id: "v07-description-not-trimmed-in-record",
		fixture: [{ path: "skills/pad/SKILL.md", text: fm(["name: pad", "description: '  padded  '"]) }],
		roots: ["skills"],
	},

	// ---- frontmatter extraction and YAML ------------------------------------------------------
	{
		id: "f01-line-endings",
		fixture: [
			{ path: "skills/crlf/SKILL.md", text: "---\r\nname: crlf\r\ndescription: d\r\n---\r\nLine 1\r\nLine 2\r\n" },
			{ path: "skills/cr/SKILL.md", text: "---\rname: cr\rdescription: d\r---\rBody\r" },
		],
		roots: ["skills"],
	},
	{
		// WP141-C001: non-SP whitespace at the start of a plain continuation line is content
		id: "f07-unicode-whitespace-in-continuation",
		fixture: [
			{ path: "skills/nbsp/SKILL.md", text: fm(["name: nbsp", "description: a", "   b"]) },
			{ path: "skills/emsp/SKILL.md", text: fm(["name: emsp", "description: a", "   b"]) },
			{ path: "skills/ideosp/SKILL.md", text: fm(["name: ideosp", "description: a", "  　b"]) },
			{ path: "skills/leadnbsp/SKILL.md", text: fm(["name: leadnbsp", "description:  x", "  y "]) },
		],
		roots: ["skills"],
	},
	{
		// block-scalar chomping at the end of T: a whitespace-only last line (unterminated in T) adds no
		// line break; a blank line before the closer does (T then ends with LF)
		id: "f08-block-chomping-at-frontmatter-end",
		fixture: [
			{ path: "skills/keep-ws/SKILL.md", text: "---\nname: keep-ws\ndescription: |+\n  x\n  \n---\nBody" },
			{ path: "skills/keep-blank/SKILL.md", text: "---\nname: keep-blank\ndescription: |+\n  x\n\n---\nBody" },
			{ path: "skills/keep-both/SKILL.md", text: "---\nname: keep-both\ndescription: >+\n  x\n\n  \n---\nBody" },
			{ path: "skills/clip-ws/SKILL.md", text: "---\nname: clip-ws\ndescription: |\n  x\n  \n---\nBody" },
			{ path: "skills/strip-ws/SKILL.md", text: "---\nname: strip-ws\ndescription: >-\n  x\n  \n---\nBody" },
		],
		roots: ["skills"],
	},
	{ id: "f02-bom-means-no-frontmatter", fixture: [{ path: "skills/bom/SKILL.md", text: `\uFEFF${skill("bom")}` }], roots: ["skills"] },
	{
		id: "f03-delimiter-edges",
		fixture: [
			{ path: "skills/unclosed/SKILL.md", text: "---\nname: unclosed\ndescription: d\nBody" },
			{ path: "skills/opener-x/SKILL.md", text: "---x\nname: opener-x\ndescription: d\n---\nBody" },
			{ path: "skills/close4/SKILL.md", text: "---\nname: close4\ndescription: d\n----\nBody" },
			{ path: "skills/closefoo/SKILL.md", text: "---\nname: closefoo\ndescription: d\n---foo\nBody" },
			{ path: "skills/empty-fm/SKILL.md", text: "---\n---\nBody" },
			{ path: "skills/body-trim/SKILL.md", text: `${fm(["name: body-trim", "description: d"], "\n\n  Body text  \n\n")}` },
			{ path: "skills/no-body/SKILL.md", text: "---\nname: no-body\ndescription: d\n---" },
			{ path: "skills/indented/SKILL.md", text: " ---\nname: indented\ndescription: d\n---\nBody" },
		],
		roots: ["skills"],
	},
	{
		id: "f04-yaml-rejections",
		fixture: [
			{ path: "skills/dupkey/SKILL.md", text: fm(["name: dupkey", "description: a", "description: b"]) },
			{ path: "skills/tabs/SKILL.md", text: fm(["name: tabs", "\tdescription: d"]) },
			{ path: "skills/docend/SKILL.md", text: fm(["name: docend", "description: d", "...", "x: 1"]) },
			{ path: "skills/badindent/SKILL.md", text: fm(["name: badindent", "description: d", "  - x"]) },
			{ path: "skills/unterminated/SKILL.md", text: fm(["name: unterminated", "description: \"open"]) },
			{ path: "skills/directive/SKILL.md", text: fm(["%YAML 1.1", "---", "name: directive", "description: d"]) },
		],
		roots: ["skills"],
	},
	{
		id: "f05-yaml-value-semantics",
		fixture: [
			{ path: "skills/date/SKILL.md", text: fm(["name: date", "description: 2001-12-14"]) },
			{ path: "skills/tagged/SKILL.md", text: fm(["name: tagged", "description: !!str 123"]) },
			{ path: "skills/alias/SKILL.md", text: fm(["base: &d Aliased.", "name: alias", "description: *d"]) },
			{ path: "skills/merge/SKILL.md", text: fm(["base: &b {description: Merged.}", "name: merge", "<<: *b"]) },
			{ path: "skills/flow/SKILL.md", text: fm(["{name: flow, description: Flow.}"]) },
			{ path: "skills/scalar/SKILL.md", text: fm(["just a scalar"]) },
			{ path: "skills/folded/SKILL.md", text: fm(["name: folded", "description: >", "  one", "  two"]) },
			{ path: "skills/literal/SKILL.md", text: fm(["name: literal", "description: |", "  one", "  two"]) },
			{ path: "skills/quoted/SKILL.md", text: fm(["name: quoted", "description: \"a\\tb \\u00e9 \\x41\""]) },
			{ path: "skills/octal/SKILL.md", text: fm(["name: octal", "description: 0o17"]) },
			{ path: "skills/complexkey/SKILL.md", text: fm(["? [a, b]", ": c", "name: complexkey", "description: d"]) },
			{ path: "skills/proto/SKILL.md", text: fm(["name: proto", "description: d", "__proto__: {x: 1}"]) },
		],
		roots: ["skills"],
	},
	{
		id: "f06-non-declared-parse-error-silent",
		fixture: [{ path: "skills/bad.md", text: fm(["name: a", "name: b"]) }],
		roots: ["skills"],
	},

	// ---- ignore files ---------------------------------------------------------------------------
	{
		id: "i01-dir-pattern-and-negation",
		fixture: [
			{ path: "skills/.gitignore", text: "build/\n*-tmp\n!keep-tmp\n" },
			{ path: "skills/build/SKILL.md", text: skill("build") },
			{ path: "skills/drop-tmp/SKILL.md", text: skill("drop-tmp") },
			{ path: "skills/keep-tmp/SKILL.md", text: skill("keep-tmp") },
			{ path: "skills/ok/SKILL.md", text: skill("ok") },
		],
		roots: ["skills"],
	},
	{
		id: "i02-nested-ignore-prefixing",
		fixture: [
			{ path: "skills/group/.gitignore", text: "inner\n/anchored\n" },
			{ path: "skills/group/inner/SKILL.md", text: skill("inner") },
			{ path: "skills/group/anchored/SKILL.md", text: skill("anchored") },
			{ path: "skills/group/deep/anchored/SKILL.md", text: skill("anchored") },
			{ path: "skills/inner/SKILL.md", text: skill("inner") },
		],
		roots: ["skills"],
	},
	{
		id: "i03-comments-escapes-blank",
		fixture: [
			{ path: "skills/.gitignore", text: "# comment\n\n   \n\\#hash\n\\!bang\n" },
			{ path: "skills/#hash/SKILL.md", text: fm(["description: Hash dir."]) },
			{ path: "skills/!bang/SKILL.md", text: fm(["description: Bang dir."]) },
			{ path: "skills/comment/SKILL.md", text: skill("comment") },
		],
		roots: ["skills"],
	},
	{
		id: "i04-case-insensitive",
		fixture: [
			{ path: "skills/.gitignore", text: "Secret\n" },
			{ path: "skills/secret/SKILL.md", text: skill("secret") },
			{ path: "skills/public/SKILL.md", text: skill("public") },
		],
		roots: ["skills"],
	},
	{
		id: "i05-all-three-ignore-files",
		fixture: [
			{ path: "skills/.gitignore", text: "a\nc\n" },
			{ path: "skills/.ignore", text: "b\n!c\n" },
			{ path: "skills/.fdignore", text: "d\n" },
			...["a", "b", "c", "d", "e"].map((n) => ({ path: `skills/${n}/SKILL.md`, text: skill(n) })),
		],
		roots: ["skills"],
	},
	{
		id: "i06-ignore-file-is-directory-or-symlink",
		fixture: [
			{ path: "skills/.gitignore", dir: true },
			{ path: "real-ignore", text: "a\n" },
			{ path: "skills/.ignore", symlink: "../real-ignore" },
			{ path: "skills/a/SKILL.md", text: skill("a") },
		],
		roots: ["skills"],
	},
	{
		id: "i07-globstar-and-root-file-patterns",
		fixture: [
			{ path: "skills/.gitignore", text: "**/drop\n*.md\n!keep.md\n" },
			{ path: "skills/x/drop/SKILL.md", text: skill("drop") },
			{ path: "skills/x/kept/SKILL.md", text: skill("kept") },
			{ path: "skills/gone.md", text: skill("gone") },
			{ path: "skills/keep.md", text: skill("skills") },
		],
		roots: ["skills"],
	},
	{
		id: "i08-crlf-ignore-file",
		fixture: [
			{ path: "skills/.gitignore", text: "a\r\nb\r\n" },
			...["a", "b", "c"].map((n) => ({ path: `skills/${n}/SKILL.md`, text: skill(n) })),
		],
		roots: ["skills"],
	},
	{
		id: "i09-trailing-spaces",
		posixOnly: true,
		fixture: [
			{ path: "skills/.gitignore", text: "plain \nesc\\ \n" },
			{ path: "skills/plain/SKILL.md", text: fm(["description: Plain."]) },
			{ path: "skills/plain /SKILL.md", text: fm(["description: Plain with space."]) },
			{ path: "skills/esc/SKILL.md", text: fm(["description: Esc."]) },
			{ path: "skills/esc /SKILL.md", text: fm(["description: Esc with space."]) },
		],
		roots: ["skills"],
	},

	// ---- S-33 whole-discovery rejection (POSIX names) -------------------------------------------
	{
		id: "r01-leading-backslash-rejects-after-collected-sibling",
		posixOnly: true,
		fixture: [
			{ path: "skills/-a/SKILL.md", text: fm(["description: Collected first."]) },
			{ path: "skills/\\x.md", text: skill("x") },
		],
		roots: ["skills"],
	},
	{
		id: "r02-leading-backslash-dir-rejects",
		posixOnly: true,
		fixture: [{ path: "skills/\\d/SKILL.md", text: skill("d") }],
		roots: ["skills"],
	},
	{
		id: "r03-earlier-root-lost",
		posixOnly: true,
		fixture: [
			{ path: "first/a/SKILL.md", text: skill("a") },
			{ path: "second/\\bad.md", text: skill("bad") },
		],
		roots: ["first", "second"],
	},
	{
		// WP141-C002: a successful sibling AFTER the offending entry -- discovery must continue past it
		id: "r05-skills-before-and-after-invalid-entry",
		posixOnly: true,
		fixture: [
			{ path: "skills/-a/SKILL.md", text: fm(["description: Before the invalid entry."]) },
			{ path: "skills/\\x.md", text: skill("x") },
			{ path: "skills/z/SKILL.md", text: skill("z", "After the invalid entry.") },
		],
		roots: ["skills"],
	},
	{
		id: "r04-inner-backslash-loads",
		posixOnly: true,
		fixture: [{ path: "skills/a\\b.md", text: skill("skills") }],
		roots: ["skills"],
	},
];

// ---- generated corpora (deterministic) ----------------------------------------------------------
import { corpus as yamlOracle } from "./yaml-oracle.mjs";
import { realistic } from "./subset-realistic.mjs";

// mulberry32 (exact 32-bit arithmetic); see subset-gen.mjs for why the earlier LCG was replaced
function seeded(seed) {
	let s = seed >>> 0;
	return () => {
		s = (s + 0x6d2b79f5) >>> 0;
		let t = s;
		t = Math.imul(t ^ (t >>> 15), t | 1);
		t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
		return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
	};
}
const asSkill = (src) => `---\n${src}\n---\nBody.`;
const usable = (src) => !src.includes("\n---") && !src.includes("\r");

function frontmatterScenario(id, sources) {
	return {
		id,
		fixture: sources.filter(usable).map((src, i) => ({ path: `skills/y${String(i).padStart(3, "0")}/SKILL.md`, text: asSkill(src) })),
		roots: ["skills"],
	};
}
scenarios.push(frontmatterScenario("y01-yaml-oracle-sources", yamlOracle));
scenarios.push(frontmatterScenario("y02-realistic-frontmatter", realistic));

// boundary sample: the fuzzer's own generator, first 300 inputs of seed 7
import { generateSample } from "./subset-sample.mjs";
scenarios.push(frontmatterScenario("y03-fuzz-boundary-sample", generateSample(7, 300)));

// ignore pattern x path corpus
const PATTERNS = ["a", "a/", "/a", "*.md", "!a", "a/**", "**/b", "a*", "?b", "[ab]", "[!a]*", "\#x", "# c", "", "   ", "sub/b", "**", "*", "!*.md", "B", "a/b/", "x[", "\*", "!keep", "keep", "*/b", "a/*", "**/c/", "/sub/", "!/a", "d?", "*-x", "a b", "b/"];
const ENTRIES = ["a", "b", "c", "B", "ab", "keep", "a-x", "sub/b", "sub/c", "a/b", "a/c", "x/b", "d1", "#x", "!keep"];
const rnd = seeded(14);
for (let n = 0; n < 40; n++) {
	const patterns = Array.from({ length: 1 + Math.floor(rnd() * 4) }, () => PATTERNS[Math.floor(rnd() * PATTERNS.length)]);
	const entries = [...new Set(Array.from({ length: 2 + Math.floor(rnd() * 5) }, () => ENTRIES[Math.floor(rnd() * ENTRIES.length)]))];
	const nested = rnd() < 0.3;
	const fixture = [{ path: "skills/.gitignore", text: `${patterns.join("\n")}\n` }];
	if (nested) fixture.push({ path: "skills/sub/.gitignore", text: `${PATTERNS[Math.floor(rnd() * PATTERNS.length)]}\n` });
	for (const e of entries) fixture.push({ path: `skills/${e}/SKILL.md`, text: fm([`description: In ${e}.`]) });
	if (rnd() < 0.5) fixture.push({ path: "skills/root.md", text: fm(["name: skills", "description: Root."]) });
	if (rnd() < 0.3) fixture.push({ path: "skills/keep.md", text: fm(["name: skills", "description: Keep."]) });
	scenarios.push({ id: `g${String(n).padStart(2, "0")}-ignore-corpus`, posixOnly: entries.some((e) => /[A-Z]/.test(e)) && entries.some((e) => /[a-z]/.test(e) && e.toLowerCase() === e && entries.includes(e.toUpperCase())), fixture, roots: ["skills"] });
}

// symlink cycle (PP-14-3): shape only
scenarios.push({
	id: "c01-symlink-cycle",
	fixture: [
		{ path: "skills/a/note.md", text: "plain" },
		{ path: "skills/a/loop", symlink: "..", dir: true },
		{ path: "skills/b.md", text: fm(["name: skills", "description: Kept."]) },
	],
	roots: ["skills"],
});
