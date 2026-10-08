// PP-14-3 characterization: a directory symlink cycle (skills/a/loop -> ..) through the byte-copied
// pinned loader over pinned NodeExecutionEnv. Records termination, diagnostics and the loop depth
// at which the host stops. Run: node --experimental-strip-types --no-warnings cycle.mjs
import { mkdirSync, mkdtempSync, rmSync, symlinkSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { NodeExecutionEnv } from "./pinned/env/nodejs.ts";
import { loadSkills } from "./pinned/skills.ts";

const work = resolve(process.env.WP141_WORK ?? "work");
mkdirSync(work, { recursive: true });
const loopDepth = (path) => path.split(/[/\\]/).filter((segment) => segment === "loop").length;

for (const withSkill of [false, true]) {
	const base = mkdtempSync(join(work, "cyc-"));
	mkdirSync(join(base, "skills", "a"), { recursive: true });
	if (withSkill) writeFileSync(join(base, "skills", "b.md"), "---\nname: skills\ndescription: d\n---\nx");
	writeFileSync(join(base, "skills", "a", "note.md"), "plain");
	symlinkSync("..", join(base, "skills", "a", "loop"), "dir");
	try {
		const r = await loadSkills(new NodeExecutionEnv({ cwd: base }), [join(base, "skills")]);
		console.log(
			JSON.stringify({
				platform: process.platform,
				withSkill,
				skills: r.skills.map((s) => s.filePath.slice(base.length)),
				diagnostics: r.diagnostics.map((d) => ({ code: d.code, loopDepth: loopDepth(d.path), messagePrefix: d.message.split(",")[0] })),
			}),
		);
	} catch (e) {
		console.log(JSON.stringify({ platform: process.platform, withSkill, rejects: e.name, message: String(e.message).slice(0, 120) }));
	}
	rmSync(base, { recursive: true, force: true });
}
