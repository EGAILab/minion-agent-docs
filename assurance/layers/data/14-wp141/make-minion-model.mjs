// Derive the WP-14.1 "Minion model" (DIV-004, DIV-005, DIV-006, PP-14-1) from the byte-copied pinned loader by applying EXACTLY the
// Owner-approved divergences as asserted string patches (each must match once):
//   DIV-004 / PP-14-1: frontmatter is read by the Minion subset reader; outside the subset, or on a
//            subset error, parse fails with the Minion-defined message.
//   DIV-005: an entry whose root-relative ignore path is empty or starts with "/" emits one
//            `invalid_path` diagnostic and is skipped, instead of rejecting the whole discovery.
//   DIV-006: an ignore pattern whose pinned-ignore RegExp is invalid is dropped with one
//            `invalid_ignore_pattern` diagnostic (in line order); valid patterns keep their order.
// The model is derivation evidence for canonical expectations, not an implementation.
// Run: node make-minion-model.mjs  -> writes model/skills.ts (+ copies types.ts, env/)
import { copyFileSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";

export const PARSE_FAILED_MESSAGE = "frontmatter is not valid in the supported YAML subset";
export const INVALID_PATH_MESSAGE = "entry path cannot be matched against ignore rules";
export const INVALID_IGNORE_PATTERN_MESSAGE = "ignore pattern is not valid and was dropped";

let source = readFileSync("pinned/skills.ts", "utf8");
function patch(from, to) {
	const count = source.split(from).length - 1;
	if (count !== 1) throw new Error(`patch target found ${count} times: ${from}`);
	source = source.replace(from, to);
}

// DIV-004 / PP-14-1
patch('import { parse } from "yaml";', 'import { readSubsetAsObject } from "../subset-object.mjs";');
patch(
	"return { ok: true, value: { frontmatter: (parse(yamlString) ?? {}) as T, body } };",
	`const subset = readSubsetAsObject(yamlString);
		if (!subset.ok) throw new Error(${JSON.stringify(PARSE_FAILED_MESSAGE)});
		return { ok: true, value: { frontmatter: (subset.value ?? {}) as T, body } };`,
);

// DIV-005: both ignore checks go through one guard.
patch(
	"if (ignoreMatcher.ignores(relPath)) continue;",
	`if (invalidIgnorePath(relPath)) { diagnostics.push({ type: "warning", code: "invalid_path", message: ${JSON.stringify(INVALID_PATH_MESSAGE)}, path: fullPath }); continue; }
		if (ignoreMatcher.ignores(relPath)) continue;`,
);
patch(
	"if (ignoreMatcher.ignores(ignorePath)) continue;",
	`if (invalidIgnorePath(ignorePath)) { diagnostics.push({ type: "warning", code: "invalid_path", message: ${JSON.stringify(INVALID_PATH_MESSAGE)}, path: fullPath }); continue; }
		if (ignoreMatcher.ignores(ignorePath)) continue;`,
);
// DIV-006: a pattern whose RegExp pinned ignore rejects is dropped with one diagnostic, in order.
patch(
	"if (patterns.length > 0) ig.add(patterns);",
	`for (const pattern of patterns) {
			if (validIgnorePattern(pattern)) ig.add([pattern]);
			else diagnostics.push({ type: "warning", code: "invalid_ignore_pattern", message: ${JSON.stringify(INVALID_IGNORE_PATTERN_MESSAGE)}, path: ignorePath });
		}`,
);
source += `
// DIV-006: pinned ignore builds a rule's RegExp lazily; test() (checkUnignored = true) evaluates every
// rule, so a pattern whose RegExp is invalid throws here. Skipped patterns (blank, comment) add no rule.
function validIgnorePattern(pattern: string): boolean {
	try {
		ignore().add([pattern]).test("a");
		return true;
	} catch (error) {
		if (error instanceof SyntaxError) return false;
		throw error;
	}
}
`;
source += `
// DIV-005: the root-relative paths ignore@7.0.5 refuses that the loader can actually produce.
function invalidIgnorePath(path: string): boolean {
	return path.length === 0 || path.startsWith("/");
}
`;

mkdirSync("model/env", { recursive: true });
writeFileSync("model/skills.ts", source);
copyFileSync("pinned/types.ts", "model/types.ts");
copyFileSync("pinned/env/nodejs.ts", "model/env/nodejs.ts");
writeFileSync("model/package.json", '{"type":"module"}\n');
console.log("model/skills.ts written");
