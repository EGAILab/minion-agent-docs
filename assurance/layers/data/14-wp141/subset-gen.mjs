// Document generator for the WP-14.1 differential fuzzer (subset-diff.mjs) and the canonical
// boundary sample (scenarios.mjs y03). Deterministic for a given seed.
export function makeGenerator(initialSeed) {
	let seed = initialSeed;
	const rand = () => {
		seed = (seed * 1103515245 + 12345) & 0x7fffffff;
		return seed / 0x7fffffff;
	};
	const pick = (xs) => xs[Math.floor(rand() * xs.length)];
	const chance = (p) => rand() < p;

	const KEYS = ["name", "description", "disable-model-invocation", "license", "metadata", "allowed-tools", "tags", "x_y", "a.b", "__proto__", "Name", "k-1", "true", "1", "~", "a b", "'q'", "<<"];
	const WORDS = ["skill", "Use it", "a#b", "a # c", "x:y", "a: b", "-x", "- x", "?x", ":x", "café", "\u{1F600} ok", "1", "017", "0o17", "0x1F", "1e3", "1_000", ".inf", "-.Inf", ".nan", "1.5", "+1", "true", "True", "TRUE", "yes", "on", "no", "off", "null", "Null", "~", "", "x\ty", "trailing  ", "@x", "`x", "%x", "&a x", "*a", "!t x", "[a]", "{a: 1}", "a,b", "a]b", "a}b", "x # y # z", "'", "\"", "a'b", "a\"b", "#x"];
	const DQ = ["plain", "a\\tb", "a\\nb", "\\u00e9", "\\U0001F600", "\\x41", "\\x07", "\\ud800", "\\\\", "\\\"", "\\/", "\\r", "\\0", "\\e", "\\N", "\\_", "\\ ", "  pad  ", "a#b", "", "q\\"];
	const SQ = ["plain", "it''s", "  pad  ", "a\\nb", "#", "", "a\"b"];

	function scalar(indent) {
		const r = rand();
		if (r < 0.45) {
			let v = pick(WORDS);
			if (chance(0.15)) v += ` ${pick(WORDS)}`;
			if (chance(0.1)) v += ` # ${pick(WORDS)}`;
			if (chance(0.15)) {
				// multi-line plain continuation
				const cont = " ".repeat(indent + 1 + Math.floor(rand() * 3));
				if (chance(0.25)) v += " # first-line comment";
				v += `\n${chance(0.2) ? "" : cont}${pick(WORDS)}`;
				if (chance(0.3)) v += `\n\n${cont}${pick(WORDS)}`;
			}
			return v;
		}
		if (r < 0.6) return `"${pick(DQ)}${chance(0.2) ? pick(DQ) : ""}"${chance(0.1) ? " # c" : ""}${chance(0.05) ? "x" : ""}`;
		if (r < 0.72) return `'${pick(SQ)}'${chance(0.1) ? " # c" : ""}${chance(0.05) ? "x" : ""}`;
		// block scalar
		const head = pick(["|", ">", "|-", ">-", "|+", ">+", "|2", "> # c", "|-  # c"]);
		const ci = indent + 1 + Math.floor(rand() * 3);
		const lines = [];
		const n = 1 + Math.floor(rand() * 4);
		for (let i = 0; i < n; i++) {
			const kind = rand();
			if (kind < 0.15) lines.push("");
			else if (kind < 0.2) lines.push(" ".repeat(Math.floor(rand() * (ci + 2))));
			else if (kind < 0.27) lines.push(`${" ".repeat(ci + 1 + Math.floor(rand() * 2))}${pick(WORDS) || "w"}`);
			else lines.push(`${" ".repeat(ci)}${pick(WORDS) || "w"}`);
		}
		if (chance(0.3)) lines.push("");
		return `${head}\n${lines.join("\n")}`;
	}

	function value(indent, depth) {
		const r = rand();
		if (depth < 2 && r < 0.1) {
			const ci = indent + 1 + Math.floor(rand() * 2);
			return `\n${mapping(ci, depth + 1)}`;
		}
		if (depth < 2 && r < 0.18) {
			const si = chance(0.5) ? indent : indent + 2;
			const items = [];
			for (let i = 0, n = 1 + Math.floor(rand() * 3); i < n; i++) items.push(`${" ".repeat(si)}- ${scalar(si).split("\n")[0]}`);
			return `\n${items.join("\n")}`;
		}
		if (r < 0.22) return "";
		return ` ${scalar(indent)}`;
	}

	function mapping(indent, depth) {
		const out = [];
		for (let i = 0, n = 1 + Math.floor(rand() * 4); i < n; i++) {
			if (chance(0.1)) out.push(pick(["", "# comment", `${" ".repeat(indent)}# c`, "   ", "\t# tabbed comment"]));
			const key = chance(0.85) ? pick(KEYS.slice(0, 12)) : pick(KEYS);
			out.push(`${" ".repeat(indent)}${key}:${value(indent, depth)}`);
		}
		return out.join("\n");
	}

	const PALETTE = [" ", "\t", ":", "-", "#", "'", '"', "\\", "|", ">", "\n", "&", "*", "!", "[", "]", "{", "}", ",", "?", "%", "@", "`", "~", "\u0085", " ", "\u0007", " ", "x", "0"];
	function mutate(text) {
		const ops = Math.floor(rand() * 3);
		for (let i = 0; i < ops; i++) {
			const pos = Math.floor(rand() * (text.length + 1));
			const r = rand();
			if (r < 0.5) text = text.slice(0, pos) + pick(PALETTE) + text.slice(pos);
			else if (r < 0.8) text = text.slice(0, pos) + text.slice(pos + 1);
			else {
				const lines = text.split("\n");
				const li = Math.floor(rand() * lines.length);
				lines.splice(li, 0, lines[li]);
				text = lines.join("\n");
			}
		}
		return text;
	}


	return {
		document: () => {
			let text = mapping(0, 0);
			if (chance(0.5)) text = mutate(text);
			return text;
		},
	};
}
