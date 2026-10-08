// Negative controls on the Minion MODEL (canonical-expectation derivation), WP141-C002. Each control
// mutates model/skills.ts; the canonical corpus must catch it, and the intended witness must be among
// the scenarios that catch it. POSIX-only rows matter, so run this on Linux:
//   node --experimental-strip-types --no-warnings model-controls.mjs
import { execFileSync } from "node:child_process";
import { cpSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { norm } from "./compare.mjs";

const model = readFileSync("model/skills.ts", "utf8");
const push = 'diagnostics.push({ type: "warning", code: "invalid_path", message: "entry path cannot be matched against ignore rules", path: fullPath });';
const guard = `${push} continue; }`;
const controls = {
	// the approved model continues; this stops walking the current directory after the diagnostic
	"invalid-entry-stops-the-directory": {
		source: model.split(guard).join(`${push} return { skills, diagnostics }; }`),
		intended: "r05-skills-before-and-after-invalid-entry",
	},
	// skips the entry but never reports it
	"invalid-entry-without-diagnostic": {
		source: model.split(guard).join("continue; }"),
		intended: "r01-leading-backslash-rejects-after-collected-sibling",
	},
};
const expected = new Map(JSON.parse(readFileSync("model-linux.json", "utf8")).results.map((r) => [r.id, r]));
const report = {};
for (const [name, { source, intended }] of Object.entries(controls)) {
	if (source === model || source.split(guard).length > 1) {
		report[name] = { applied: false };
		continue;
	}
	rmSync("model-ctl", { recursive: true, force: true });
	cpSync("model", "model-ctl", { recursive: true });
	writeFileSync("model-ctl/skills.ts", source);
	execFileSync("node", ["--experimental-strip-types", "--no-warnings", "run.mjs", "ctl-out.json"], { env: { ...process.env, WP141_LOADER: "model-ctl" }, stdio: "ignore" });
	const got = JSON.parse(readFileSync("ctl-out.json", "utf8")).results;
	const killedBy = got.filter((r) => JSON.stringify(norm(r)) !== JSON.stringify(norm(expected.get(r.id)))).map((r) => r.id);
	report[name] = { applied: true, intended, killedBy, killedByIntended: killedBy.includes(intended) };
}
rmSync("model-ctl", { recursive: true, force: true });
rmSync("ctl-out.json", { force: true });
writeFileSync("model-controls.json", `${JSON.stringify({ platform: process.platform, report }, null, 1)}\n`);
for (const [k, v] of Object.entries(report)) {
	console.log(`${v.killedByIntended ? "KILLED  " : "SURVIVED"} ${k}: ${v.applied ? `killed by [${v.killedBy.join(", ")}]` : "MUTATION DID NOT APPLY"}`);
}
