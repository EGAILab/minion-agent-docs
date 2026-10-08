// Frontmatter-subset corpus for the Python/Rust readers (HAR-010): generated documents (the fuzzer's
// generator, fresh seeds) plus the oracle and realistic sources, each with the REVIEWED reference
// reader's result (subset-reader.mjs; sound against yaml@2.9.0 -- characterization section 8).
// Values: strings, booleans, null, {"$number": text}, {"$map": [[k, v]...]}, {"$seq": [...]}.
// Run: node frontmatter-corpus.mjs <count> <out.json>
import { writeFileSync } from "node:fs";
import { makeGenerator } from "./subset-gen.mjs";
import { realistic } from "./subset-realistic.mjs";
import { readSubset } from "./subset-reader.mjs";
import { corpus as oracle } from "./yaml-oracle.mjs";

const count = Number(process.argv[2] ?? 8000);
function encode(v) {
	if (v === null || typeof v === "string" || typeof v === "boolean") return v;
	if ("number" in v) return { $number: v.number };
	if ("seq" in v) return { $seq: v.seq.map(encode) };
	return { $map: v.map.map(([k, x]) => [k, encode(x)]) };
}
const sources = [...oracle, ...realistic];
const gen = makeGenerator(41);
const seen = new Set(sources);
while (sources.length < count) {
	const d = gen.document();
	if (!seen.has(d)) {
		seen.add(d);
		sources.push(d);
	}
}
const cases = sources.map((src) => {
	const r = readSubset(src);
	return r.ok ? { src, ok: true, value: r.value === null ? { $map: [] } : encode(r.value) } : { src, ok: false };
});
writeFileSync(process.argv[3] ?? "frontmatter-corpus.json", `${JSON.stringify({ reader: "subset-reader.mjs", cases })}\n`);
console.log(`${cases.length} cases, ${cases.filter((c) => c.ok).length} accepted`);
