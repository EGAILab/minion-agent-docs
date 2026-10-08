// Adapter for the Minion model: the subset reader's value tree as the plain JS value the pinned
// loader reads (`frontmatter.name`, `.description`, `["disable-model-invocation"]`).
import { readSubset } from "./subset-reader.mjs";

function toObject(v) {
	if (v === null || typeof v === "string" || typeof v === "boolean") return v;
	if ("number" in v) return Number(v.number.replace(/^0o/, "0o")) || 0;
	if ("seq" in v) return v.seq.map(toObject);
	const out = {};
	for (const [k, x] of v.map) Object.defineProperty(out, k, { value: toObject(x), enumerable: true, writable: true, configurable: true });
	return out;
}

export function readSubsetAsObject(text) {
	const r = readSubset(text);
	return r.ok ? { ok: true, value: r.value === null ? null : toObject(r.value) } : r;
}
