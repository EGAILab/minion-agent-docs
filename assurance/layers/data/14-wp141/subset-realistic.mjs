// Realistic skill frontmatter shapes: the subset must ACCEPT each with a value tree identical to
// pinned yaml@2.9.0. Run: node --no-warnings subset-realistic.mjs
import { writeFileSync } from "node:fs";
import { parse } from "yaml";
import { fromYaml, normalizeSubset, readSubset } from "./subset-reader.mjs";

export const realistic = [
	"name: pdf\ndescription: Extract text and tables from PDF files. Use when working with PDFs.",
	"name: pdf\ndescription: Extract text, fill forms, and merge PDFs. Use when the user mentions PDFs, forms, or document extraction.\nlicense: Proprietary. LICENSE.txt has complete terms",
	"name: brand-guidelines\ndescription: >\n  Applies the company's official brand colors and typography.\n  Use when producing branded documents.",
	"name: brand-guidelines\ndescription: >-\n  Applies the company's official brand colors and typography.\n  Use when producing branded documents.",
	"name: changelog\ndescription: |\n  Generates changelog entries.\n\n  Use after merging a release branch.",
	"name: review\ndescription: \"Reviews code: style, correctness, and tests.\"",
	"name: review\ndescription: 'Reviews code: style, correctness, and tests.'",
	"name: deploy\ndescription: Deploys the service\ndisable-model-invocation: true",
	"name: deploy\ndescription: Deploys the service\ndisable-model-invocation: false",
	"name: data-viz\ndescription: Builds charts from CSV data\nmetadata:\n  author: Data Team\n  version: \"1.2\"",
	"name: data-viz\ndescription: Builds charts\nmetadata:\n  author: Data Team\n  version: 1.2",
	"name: git-helper\ndescription: Git workflows\nallowed-tools: Bash(git:*) Read Grep",
	"name: helper\ndescription: Helps with tasks\ncompatibility: Requires Python 3.11+ and network access",
	"# Skill frontmatter\nname: commented\ndescription: Has comments # trailing comment\n# end",
	"name: tags\ndescription: Uses a tag list\ntags:\n  - writing\n  - editing",
	"name: tags\ndescription: Uses a tag list\ntags:\n- writing\n- editing",
	"name: long\ndescription: A long description that wraps\n  onto a second line without quotes\n  and a third.",
	"name: unicode\ndescription: Handles café menus and \u{1F600} emoji",
	"name: url\ndescription: Fetches https://example.com/docs#section pages",
	"name: colon\ndescription: \"Note: quoted because it has a colon-space\"",
	"name: escape\ndescription: \"Tab\\tseparated and \\u00e9 escaped\"",
	"name: empty-meta\ndescription: Something\nmetadata:",
	"name: version\ndescription: Something\nversion: 1.0.0",
	"name: trailing-space   \ndescription: Something   ",
	"\nname: leading-blank\ndescription: Something\n",
];

import { pathToFileURL } from "node:url";
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
const rows = realistic.map((src) => {
	const minion = readSubset(src);
	const pi = fromYaml(parse(src) ?? null);
	const mine = minion.ok ? (minion.value === null ? null : normalizeSubset(minion.value)) : null;
	return { src, accepted: minion.ok, why: minion.why, equal: minion.ok && JSON.stringify(mine) === JSON.stringify(pi) };
});
writeFileSync("subset-realistic.json", `${JSON.stringify(rows, null, 1)}\n`);
for (const r of rows) console.log(`${r.accepted ? (r.equal ? "OK      " : "MISMATCH") : "REJECTED"} ${JSON.stringify(r.src).slice(0, 80)}${r.why ? `  (${r.why})` : ""}`);
console.log(`accepted ${rows.filter((r) => r.accepted).length}/${rows.length}; mismatches ${rows.filter((r) => r.accepted && !r.equal).length}`);
}
