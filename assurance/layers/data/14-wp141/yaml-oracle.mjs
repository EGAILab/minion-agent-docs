// yaml@2.9.0 oracle for the frontmatter YAML engine question (PP-14-1/PP-14-2). Each source is
// what Pi passes to `parse` (normalized.slice(4, endIndex)). Output: accept/reject plus the parsed
// value with JS types preserved (JSON can carry string/number/boolean/null/array/object).
import { writeFileSync } from "node:fs";
import { parse } from "yaml";

export const corpus = [
	"name: a\ndescription: d",
	"", "~", "null", "just a scalar", "42", "- a\n- b",
	"description: true", "description: True", "description: TRUE", "description: yes", "description: no",
	"description: on", "description: off", "description: y", "description: n",
	"description: 0o17", "description: 017", "description: 0x1F", "description: 1_000", "description: 1e3",
	"description: .inf", "description: -.Inf", "description: .nan", "description: 12:30:00", "description: 2001-12-14",
	"description: 2001-12-14t21:59:43.10-05:00", "description: ~", "description: null", "description: Null",
	"description: ''", "description: \"\"", "description: '  x  '",
	"description: !!str 123", "description: !!int '7'", "description: !!binary aGk=", "description: !custom x",
	"a: &x foo\ndescription: *x", "base: &b {description: d}\n<<: *b", "<<: {description: d}",
	"description: d\ndescription: e", "Description: a\ndescription: b",
	"name: a\n\tdescription: d", "description: \"open", "description: 'open", "description: d\n...\nx: 1",
	"%YAML 1.1", "%YAML 1.2\n---\ndescription: d", "description: d\n  - x", "description: [a, b",
	"{description: Flow.}", "? [a, b]\n: c\ndescription: d", "__proto__: {x: 1}\ndescription: d",
	"description: >\n  one\n  two", "description: |\n  one\n  two", "description: |-\n  one", "description: >+\n  one\n\n",
	"description: \"a\\tb \\u00e9 \\x41 \\U0001F600\"", "description: \"\\ud800\"", "description: 'it''s'",
	"description: a # comment", "description: a#b", "description: 'a: b'", "description: a: b",
	"description: -", "description: - x", "description: @x", "description: `x", "description: %x",
	"description: *undefined", "description: &a", "description: d\n'description': e",
	"disable-model-invocation: true", "disable-model-invocation: 'true'", "disable-model-invocation: 1",
	"name:\n  - list\ndescription: d", "name: {a: 1}\ndescription: d", "description:", "description: \t",
	"\uFEFFdescription: d", "description: d\r\nname: n", "description: caf\u00e9", "description: \u0085x",
	"description: a\u2028b", "description: x\u0007", "description: \"x\\0\"", "1: one\ndescription: d",
	"true: t\ndescription: d", "null: n\ndescription: d", "[a]: b\ndescription: d",
	"__proto__: {description: via-proto, name: proto-name}", "__proto__: {disable-model-invocation: true}\ndescription: d",
	"constructor: x\ndescription: d", "description: d\nname: [a]", "? description\n: d",
];

// Pi's observable projection (harness skills.ts loadSkillFromFile): `frontmatter = parse(y) ?? {}`,
// then `typeof fm.name === "string"`, `typeof fm.description === "string"`, `fm["disable-model-invocation"] === true`.
function project(fm) {
	const name = fm.name;
	const description = fm.description;
	return {
		name: typeof name === "string" ? name : null,
		description: typeof description === "string" ? description : null,
		disable: fm["disable-model-invocation"] === true,
	};
}
const results = corpus.map((src) => {
	try {
		return { src, ok: true, observed: project(parse(src) ?? {}) };
	} catch (e) {
		return { src, ok: false, error: e.name, message: e.message.split("\n")[0] };
	}
});
writeFileSync(process.argv[2] ?? "yaml-oracle.json", `${JSON.stringify(results, null, 1)}\n`);
console.log(`${results.length} sources, ${results.filter((r) => !r.ok).length} rejected`);
