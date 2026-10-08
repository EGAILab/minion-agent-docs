// Negative controls for the differential fuzzer: each mutation of the reference subset reader must
// produce soundness violations (the fuzzer's oracle comparison must detect it).
// Run: node --no-warnings fuzz-controls.mjs
import { execFileSync } from "node:child_process";
import { readFileSync, rmSync, writeFileSync } from "node:fs";

const reader = readFileSync("subset-reader.mjs", "utf8");
const diff = readFileSync("subset-diff.mjs", "utf8");
// Each mutation replaces exact content that must occur once; a non-applying mutation is reported,
// never silently run as the unmodified reader.
const once = (from, to) => (reader.split(from).length === 2 ? reader.replace(from, to) : reader);
const mutations = {
	"clip-drops-final-newline": once("return [`${body}\\n`, consumed];", "return [body, consumed];"),
	"keep-drops-one-newline": once('return [body + "\\n" + "\\n".repeat(trailing), consumed];', 'return [body + "\\n".repeat(trailing), consumed];'),
	"colon-space-accepted": once('if (/:[ \\t]/.test(text) || text.endsWith(":")) reject', "if (false) reject"),
	"safe-lead-any-indicator": once('const safeLead = "-?:".includes(text[0])', 'const safeLead = true'),
	"duplicate-key-accepted": reader.replace("if (seen.has(key)) reject(`duplicate key ${key}`);", ""),
	"yes-is-boolean": reader.replace("|[Ff]alse|FALSE)$/;", "|[Ff]alse|FALSE|yes|no|on|off)$/;"),
	"comment-allows-continuation": reader.replace("if (!allowContinuation || /[ \\t]#/.test(rest)) {", "if (!allowContinuation) {"),
	"tab-indentation-accepted": reader.replace('for (const line of lines) if (/^ *\\t/.test(line)) reject("tab in leading whitespace");', ""),
	"continuation-strips-unicode-whitespace": once('const stripped = line.replace(/^ +/, "");', "const stripped = line.trimStart();"),
	"unterminated-final-blank-counts": once("if (trailing > 0 && j === lines.length && !lastLineTerminated) trailing--;", ""),
	"folded-joins-with-newline": reader.replace('if (k > 0) body += pendingBlank === 0 ? " " : "\\n".repeat(pendingBlank);', 'if (k > 0) body += pendingBlank === 0 ? "\\n" : "\\n".repeat(pendingBlank);'),
};
const results = {};
for (const [name, source] of Object.entries(mutations)) {
	if (source === reader) {
		results[name] = "MUTATION DID NOT APPLY";
		continue;
	}
	writeFileSync("ctl-reader.mjs", source);
	writeFileSync("ctl-diff.mjs", diff.replace("./subset-reader.mjs", "./ctl-reader.mjs"));
	// Three seeds: a control counts as killed only if EVERY seed finds violations (minimum reported).
	const counts = ["21", "22", "23"].map((seed) => {
		const out = execFileSync("node", ["--no-warnings", "ctl-diff.mjs", "50000", seed], { encoding: "utf8" });
		return Number(/VIOLATIONS=(\d+)/.exec(out)[1]);
	});
	results[name] = Math.min(...counts);
}
for (const f of ["ctl-reader.mjs", "ctl-diff.mjs", "subset-diff-21.json", "subset-diff-22.json", "subset-diff-23.json"]) {
	rmSync(f, { force: true });
}
writeFileSync("fuzz-controls.json", `${JSON.stringify(results, null, 1)}\n`);
for (const [k, v] of Object.entries(results)) console.log(`${typeof v === "number" && v > 0 ? "KILLED " : "SURVIVED"} ${k}: ${v}`);
