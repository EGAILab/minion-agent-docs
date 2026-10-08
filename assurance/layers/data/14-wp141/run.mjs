// WP-14.1 characterization runner: byte-copied pinned harness loader (pinned/skills.ts) over
// pinned NodeExecutionEnv (pinned/env/nodejs.ts) on a real filesystem.
// Run: node --experimental-strip-types --no-warnings run.mjs <out.json>
import { mkdirSync, mkdtempSync, rmSync, symlinkSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";
const loaderDir = process.env.WP141_LOADER ?? "pinned";
const { NodeExecutionEnv } = await import(`./${loaderDir}/env/nodejs.ts`);
const { loadSkills } = await import(`./${loaderDir}/skills.ts`);
import { scenarios } from "./scenarios.mjs";

const out = process.argv[2] ?? "out.json";
const workRoot = resolve(process.env.WP141_WORK ?? "work");
mkdirSync(workRoot, { recursive: true });
const posix = process.platform !== "win32";

function materialize(base, fixture) {
	for (const entry of fixture) {
		const full = join(base, ...entry.path.split("/"));
		mkdirSync(join(full, ".."), { recursive: true });
		if (entry.symlink !== undefined) symlinkSync(entry.symlink, full, entry.dir ? "dir" : "file");
		else if (entry.dir) mkdirSync(full, { recursive: true });
		else writeFileSync(full, entry.text, "utf8");
	}
}

const results = [];
for (const scenario of scenarios) {
	if (scenario.posixOnly && !posix) {
		results.push({ id: scenario.id, skipped: "posixOnly" });
		continue;
	}
	const base = mkdtempSync(join(workRoot, "c-"));
	const rel = (p) => (typeof p === "string" && p.startsWith(base) ? `<base>${p.slice(base.length)}` : p);
	try {
		materialize(base, scenario.fixture);
		const env = new NodeExecutionEnv({ cwd: base });
		const roots = scenario.roots.map((r) => join(base, ...r.split("/")));
		try {
			const r = await loadSkills(env, roots);
			results.push({
				id: scenario.id,
				skills: r.skills.map((s) => ({
					name: s.name,
					description: s.description,
					content: s.content,
					filePath: rel(s.filePath),
					disableModelInvocation: s.disableModelInvocation,
				})),
				diagnostics: r.diagnostics.map((d) => ({ type: d.type, code: d.code, message: d.message.split(base).join("<base>"), path: rel(d.path) })),
			});
		} catch (e) {
			results.push({ id: scenario.id, rejects: { name: e.name, message: String(e.message).split(base).join("<base>") } });
		}
	} finally {
		rmSync(base, { recursive: true, force: true });
	}
}
writeFileSync(out, `${JSON.stringify({ loader: loaderDir, platform: process.platform, node: process.version, icu: process.versions.icu, results }, null, 2)}\n`);
console.log(`${results.length} scenarios -> ${out}`);
