// WP141-R002 cross-check on the byte-copied pinned loader: deep nesting, declared and undeclared.
import { mkdirSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { NodeExecutionEnv } from "./pinned/env/nodejs.ts";
import { loadSkills } from "./pinned/skills.ts";

const NL = String.fromCharCode(10);
const nested = (name, depth) => {
	let body = "";
	for (let i = 0; i < depth; i++) body += "  ".repeat(i) + "k:" + NL;
	body += "  ".repeat(depth) + "leaf: value" + NL;
	return `---${NL}name: ${name}${NL}description: Example.${NL}${body}---${NL}Body.`;
};
for (const depth of [500, 1200]) {
	const base = mkdtempSync(join(process.env.WP141_WORK ?? tmpdir(), "r002-"));
	mkdirSync(join(base, "root", "ok"), { recursive: true });
	writeFileSync(join(base, "root", "deep.md"), nested("deep", depth));
	writeFileSync(join(base, "root", "ok", "SKILL.md"), `---${NL}name: ok${NL}description: Use ok.${NL}---${NL}Body.`);
	mkdirSync(join(base, "bad", "bad"), { recursive: true });
	writeFileSync(join(base, "bad", "bad", "SKILL.md"), nested("bad", depth));
	const env = new NodeExecutionEnv({ cwd: base });
	const r = await loadSkills(env, [join(base, "bad"), join(base, "root")]);
	console.log(depth, JSON.stringify({ skills: r.skills.map((s) => s.name), diagnostics: r.diagnostics.map((d) => `${d.code}@${d.path.slice(base.length)}`) }));
}
