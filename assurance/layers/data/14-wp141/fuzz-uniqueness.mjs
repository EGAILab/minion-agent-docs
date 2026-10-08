// Distinct generated documents per fuzz seed (the evidence's real input-space size).
import { writeFileSync } from "node:fs";
import { makeGenerator } from "./subset-gen.mjs";
const rows = [1, 2, 3, 4, 5].map((seed) => {
	const g = makeGenerator(seed);
	const set = new Set();
	for (let i = 0; i < 300000; i++) set.add(g.document());
	return { seed, generated: 300000, distinct: set.size };
});
const total = new Set();
for (const seed of [1, 2, 3, 4, 5]) {
	const g = makeGenerator(seed);
	for (let i = 0; i < 300000; i++) total.add(g.document());
}
writeFileSync("fuzz-uniqueness.json", `${JSON.stringify({ rows, distinctAcrossSeeds: total.size }, null, 1)}\n`);
console.log(JSON.stringify({ rows, distinctAcrossSeeds: total.size }));
