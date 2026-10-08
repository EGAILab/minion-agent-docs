// Differential check of the proposed Minion frontmatter subset against pinned yaml@2.9.0.
// SOUNDNESS invariant (must hold for every input): if the subset reader accepts T, then
// yaml@2.9.0 accepts T and yields an identical value tree. Inputs the subset rejects are DIV-004;
// those Pi accepts are tallied by rejection reason for the realism review.
// Run: node --no-warnings subset-diff.mjs [iterations] [seed]
import { writeFileSync } from "node:fs";
import { parse } from "yaml";
import { fromYaml, normalizeSubset, readSubset } from "./subset-reader.mjs";
import { makeGenerator } from "./subset-gen.mjs";

const iterations = Number(process.argv[2] ?? 200000);
const seedArg = Number(process.argv[3] ?? 1);
const gen = makeGenerator(seedArg);

const violations = [];
const piOnly = {};
let accepted = 0;
let bothReject = 0;
for (let it = 0; it < iterations; it++) {
	const text = gen.document();
	const minion = readSubset(text);
	let pi;
	try {
		pi = { ok: true, value: fromYaml(parse(text) ?? null) };
	} catch (e) {
		pi = { ok: false, message: e.message.split("\n")[0] };
	}
	if (minion.ok) {
		accepted++;
		const mine = minion.value === null ? null : normalizeSubset(minion.value);
		if (!pi.ok || JSON.stringify(mine) !== JSON.stringify(pi.value)) {
			if (violations.length < 50) violations.push({ text, minion: mine, pi });
			else violations.length++;
		}
	} else if (pi.ok) {
		piOnly[minion.why] = (piOnly[minion.why] ?? 0) + 1;
	} else bothReject++;
}
const report = { iterations, seed: seedArg, accepted, bothReject, violations: violations.length, examples: violations.slice(0, 50), piAcceptsMinionRejects: piOnly };
writeFileSync(`subset-diff-${report.seed}.json`, `${JSON.stringify(report, null, 1)}\n`);
console.log(`iterations=${iterations} accepted=${accepted} bothReject=${bothReject} VIOLATIONS=${violations.length}`);
for (const v of violations.slice(0, 8)) console.log(JSON.stringify(v));
