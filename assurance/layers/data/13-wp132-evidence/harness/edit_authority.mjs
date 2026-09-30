// WP-13.2 authority: pinned Pi b7bb00b9 edit-diff.ts + utils/text.ts (unmodified) with diff 8.0.4, under Node 22.15.1.
// The glue below is edit.ts's execute (lines 332-386) and write.ts's execute (lines 201-233) VERBATIM apart from I/O:
// file bytes come from the case, the "written" bytes are returned instead of written, and no queue/abort is modeled
// (those are witnessed by the language runners). prepareEditArguments/validateEditInput are copied verbatim from
// edit.ts:74-81 and 116-154 because edit.ts itself imports the TUI.
import { readFileSync, writeFileSync } from "node:fs";
import { createHash } from "node:crypto";
import {
  applyEditsToNormalizedContent, detectLineEnding, generateDiffString, generateUnifiedPatch,
  normalizeForFuzzyMatch, normalizeToLF, restoreLineEndings,
} from "./pi/core/tools/edit-diff.ts";
import { splitBom } from "./pi/utils/text.ts";

// ---- edit.ts:74-81, verbatim
function isSingleEditInput(value) {
	if (!value || typeof value !== "object" || Array.isArray(value)) {
		return false;
	}

	const edit = value;
	return typeof edit.oldText === "string" && typeof edit.newText === "string";
}
// ---- edit.ts:116-147, verbatim (types removed)
function prepareEditArguments(input) {
	if (!input || typeof input !== "object") {
		return input;
	}

	const args = input;

	// Some models (Opus 4.6, GLM-5.1) send edits as a JSON string instead of an array.
	// Others send a single edit object instead of a one-element edits array.
	if (typeof args.edits === "string") {
		try {
			const parsed = JSON.parse(args.edits);
			if (Array.isArray(parsed)) {
				args.edits = parsed;
			} else if (isSingleEditInput(parsed)) {
				args.edits = [parsed];
			}
		} catch {}
	} else if (isSingleEditInput(args.edits)) {
		args.edits = [args.edits];
	}

	const legacy = args;
	if (typeof legacy.oldText !== "string" || typeof legacy.newText !== "string") {
		return args;
	}

	const edits = Array.isArray(legacy.edits) ? [...legacy.edits] : [];
	edits.push({ oldText: legacy.oldText, newText: legacy.newText });
	const { oldText: _oldText, newText: _newText, ...rest } = legacy;
	return { ...rest, edits };
}
// ---- edit.ts:149-154, verbatim
function validateEditInput(input) {
	if (!Array.isArray(input.edits) || input.edits.length === 0) {
		throw new Error("Edit tool input is invalid. edits must contain at least one replacement.");
	}
	return { path: input.path, edits: input.edits };
}

const sha = (b) => createHash("sha256").update(b).digest("hex");
const b64 = (b) => Buffer.from(b).toString("base64");

// edit.ts:34-54's TypeBox schema (object; path string; edits array of objects with string oldText/newText; no
// additionalProperties restriction, no minItems). Pi's validateToolArguments rejects anything else before execute;
// the rejection TEXT is Layer 06's, so only the verdict is recorded.
function matchesEditSchema(v) {
  const obj = (o) => o !== null && typeof o === "object" && !Array.isArray(o);
  return obj(v) && typeof v.path === "string" && Array.isArray(v.edits) &&
    v.edits.every((e) => obj(e) && typeof e.oldText === "string" && typeof e.newText === "string");
}

function runEdit(c) {
  // edit.ts: validateEditInput first; then (after access/read) the pure pipeline below.
  let input = c.prepare ? prepareEditArguments(JSON.parse(JSON.stringify(c.raw_args))) : c.args;
  if (c.prepare) {
    const schema_valid = matchesEditSchema(input);
    const result = schema_valid ? runEdit({ id: c.id, args: input, file_b64: c.file_b64 }) : null;
    return { id: c.id, kind: "prepare", prepared: input, schema_valid, result };
  }
  try {
    const { path, edits } = validateEditInput(input);
    const buffer = Buffer.from(c.file_b64, "base64");
    const rawContent = buffer.toString("utf-8");
    const { bom, text: content } = splitBom(rawContent);
    const originalEnding = detectLineEnding(content);
    const normalizedContent = normalizeToLF(content);
    const { baseContent, newContent } = applyEditsToNormalizedContent(normalizedContent, edits, path);
    const finalContent = bom + restoreLineEndings(newContent, originalEnding);
    const written = Buffer.from(finalContent, "utf-8");
    const diffResult = generateDiffString(baseContent, newContent);
    const patch = generateUnifiedPatch(path, baseContent, newContent);
    return {
      id: c.id, kind: "edit", is_error: false,
      text: `Successfully replaced ${edits.length} block(s) in ${path}.`,
      written_b64: b64(written), written_sha256: sha(written),
      details: { diff: diffResult.diff, patch, firstChangedLine: diffResult.firstChangedLine ?? null },
    };
  } catch (e) {
    return { id: c.id, kind: "edit", is_error: true, text: e instanceof Error ? e.message : String(e) };
  }
}

function runWrite(c) {
  // write.ts:201-233: the reported count is content.length; the file bytes are writeFile(..., "utf-8").
  const written = Buffer.from(c.content, "utf-8");
  return { id: c.id, kind: "write", is_error: false,
           text: `Successfully wrote ${c.content.length} bytes to ${c.path}`,
           written_b64: b64(written), written_sha256: sha(written) };
}

const [casesPath, outPath] = process.argv.slice(2);
const cases = JSON.parse(readFileSync(casesPath, "utf8"));
const results = cases.map((c) => (c.kind === "write" ? runWrite(c) : c.kind === "fuzzy" ?
  { id: c.id, kind: "fuzzy", normalized: normalizeForFuzzyMatch(c.text) } : runEdit(c)));
writeFileSync(outPath, JSON.stringify({ engine: "node+pi-edit-diff+diff-8.0.4", node: process.versions.node,
  v8: process.versions.v8, icu: process.versions.icu, unicode: process.versions.unicode, results }, null, 1));
console.log(`authority: ${results.length} results`);
