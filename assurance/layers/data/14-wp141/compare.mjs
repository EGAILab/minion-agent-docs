// Structured comparisons for the WP-14.1 evidence. Separators are normalized in path fields only
// (never inside messages or names); fs-origin messages are non-normative (PP-14-8) and masked.
// Run: node compare.mjs
import { readFileSync } from "node:fs";

const load = (f) => JSON.parse(readFileSync(f, "utf8")).results;
const posixPath = (p) => (typeof p === "string" ? p.split(String.fromCharCode(92)).join("/") : p);
const FS_CODES = new Set(["file_info_failed", "list_failed", "read_failed"]);

export function norm(r) {
	if (r.skipped || r.rejects) return r;
	return {
		id: r.id,
		skills: r.skills.map((s) => ({ ...s, filePath: posixPath(s.filePath) })),
		diagnostics: r.diagnostics.map((d) => ({ ...d, path: posixPath(d.path), message: FS_CODES.has(d.code) ? "<fs>" : d.message })),
	};
}

import { pathToFileURL } from "node:url";

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
	for (const kind of ["out", "model"]) {
		const w = load(`${kind}-win32.json`);
		const l = load(`${kind}-linux.json`);
		const diffs = w.filter((x, i) => !x.skipped && JSON.stringify(norm(x)) !== JSON.stringify(norm(l[i]))).map((x) => x.id);
		console.log(`${kind}: win32 vs linux structural diffs: ${diffs.length ? diffs.join(", ") : "none"}`);
	}
	const pi = load("out-linux.json");
	const model = load("model-linux.json");
	const divergent = pi.filter((p, i) => JSON.stringify(norm(p)) !== JSON.stringify(norm(model[i]))).map((p) => p.id);
	console.log(`pi vs model (linux): ${divergent.length} scenarios differ: ${divergent.join(", ")}`);
}
