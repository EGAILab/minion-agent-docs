// Deterministic boundary sample from the fuzzer's own generator (canonical scenario y03).
import { makeGenerator } from "./subset-gen.mjs";
export function generateSample(seed, count) {
	const gen = makeGenerator(seed);
	return Array.from({ length: count }, () => gen.document());
}
