// L14-SCOPE-R001/R002 remediation probes. ignore@7.0.5 trailing-space semantics, and invalid relative
// paths reaching the byte-copied pinned harness loader (pinned/skills.ts, pinned/types.ts) through a
// scripted POSIX-style ExecutionEnv. Run: node --experimental-strip-types remediation1_probe.mjs
import ignore from "ignore";
import { loadSkills } from "./pinned/skills.ts";

for (const [patterns, paths] of [
	[["foo "], ["foo", "foo "]],
	[["foo\\ "], ["foo", "foo "]],
	[["foo\\  "], ["foo", "foo ", "foo  "]],
	[["foo \\ "], ["foo", "foo ", "foo  "]],
]) {
	const m = ignore().add(patterns);
	for (const p of paths) console.log(`ignore ${JSON.stringify(patterns)} ${JSON.stringify(p)} -> ${m.ignores(p)}`);
}

const ok = (value) => ({ ok: true, value });
const notFound = (path) => ({ ok: false, error: { code: "not_found", message: `ENOENT ${path}`, path } });

// tree: { "/root": { kind: "directory", children: [...] }, "/root/x": { kind: "file", content } }
function env(tree) {
	const info = (path) => {
		const node = tree[path];
		if (!node) return notFound(path);
		const name = path.slice(path.lastIndexOf("/") + 1);
		return ok({ name, path, kind: node.kind, size: 0, mtimeMs: 0 });
	};
	return {
		cwd: "/",
		fileInfo: async (path) => info(path),
		joinPath: async (parts) => ok(parts.join("/")),
		listDir: async (path) => ok(tree[path].children.map((c) => info(`${path}/${c}`).value)),
		readTextFile: async (path) => (tree[path]?.kind === "file" ? ok(tree[path].content) : notFound(path)),
		canonicalPath: async (path) => ok(path),
	};
}

const skill = "---\nname: x\ndescription: d\n---\nbody";
const cases = {
	"leading-backslash file": { "/root": { kind: "directory", children: ["\\x.md"] }, "/root/\\x.md": { kind: "file", content: skill } },
	"leading-backslash dir": {
		"/root": { kind: "directory", children: ["\\d"] },
		"/root/\\d": { kind: "directory", children: ["SKILL.md"] },
		"/root/\\d/SKILL.md": { kind: "file", content: skill },
	},
	"bare-backslash file": { "/root": { kind: "directory", children: ["\\"] }, "/root/\\": { kind: "file", content: skill } },
	"bare-backslash dir": { "/root": { kind: "directory", children: ["\\"] }, "/root/\\": { kind: "directory", children: [] } },
	"inner-backslash file (control)": { "/root": { kind: "directory", children: ["a\\b.md"] }, "/root/a\\b.md": { kind: "file", content: skill } },
	"dot-backslash file (dotfile skip)": { "/root": { kind: "directory", children: [".\\x.md"] }, "/root/.\\x.md": { kind: "file", content: skill } },
	"sibling before bad name": {
		"/root": { kind: "directory", children: ["\\x.md", "a.md"] },
		"/root/a.md": { kind: "file", content: skill },
		"/root/\\x.md": { kind: "file", content: skill },
	},
};
for (const [label, tree] of Object.entries(cases)) {
	try {
		const r = await loadSkills(env(tree), "/root");
		console.log(`loader ${label}: resolved skills=${JSON.stringify(r.skills.map((s) => s.filePath))} diagnostics=${r.diagnostics.length}`);
	} catch (e) {
		console.log(`loader ${label}: REJECTS ${e.name}: ${e.message}`);
	}
}
