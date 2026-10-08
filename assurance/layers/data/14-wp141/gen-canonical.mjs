// Generate the WP-14.1 canonical scenarios (conformance/agent/skill-discovery/*.json) from the
// characterization corpus (scenarios.mjs), the Minion model's results (model-linux.json, the
// approved-divergence expectations) and pinned Pi's results (out-linux.json, used only to label
// divergences). Linux results are the source because they include the POSIX-only rows; the win32
// results agree structurally on every shared row except the PP-14-3 cycle (compare.mjs).
// Run: node gen-canonical.mjs <output dir>
import { mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { norm } from "./compare.mjs";
import { scenarios } from "./scenarios.mjs";

const outDir = process.argv[2];
if (!outDir) throw new Error("usage: node gen-canonical.mjs <output dir>");
const PI_REVISION = "b7bb00b936dbe21b8e160b3e89efdec361846699";
const NORMATIVE_MESSAGE = new Set(["invalid_metadata", "parse_failed", "invalid_path", "invalid_ignore_pattern"]);
const load = (f) => JSON.parse(readFileSync(f, "utf8")).results;
const model = new Map(load("model-linux.json").map((r) => [r.id, r]));
const pi = new Map(load("out-linux.json").map((r) => [r.id, r]));
const rel = (p) => p.replace(/^<base>\//, "");

function requirements(id) {
	const reqs = new Set(["HAR-001", "HAR-013"]);
	if (/^(f|y|v0[4-7])/.test(id)) reqs.add("HAR-010");
	if (/^(i|g|d04|d06)/.test(id)) reqs.add("HAR-011");
	if (/^(v|d03|d07|d09|y)/.test(id)) reqs.add("HAR-012");
	if (/^r/.test(id)) reqs.add("HAR-011");
	return [...reqs].sort();
}

function divergences(id) {
	const p = pi.get(id);
	const m = model.get(id);
	const mask = (r) => (r.rejects ? r : { ...norm(r), diagnostics: norm(r).diagnostics.map((d) => (d.code === "parse_failed" ? { ...d, message: "<parse>" } : d)) });
	if (JSON.stringify(norm(p)) === JSON.stringify(norm(m))) return [];
	const out = new Set();
	if (!p.rejects && p.diagnostics.some((d) => d.code === "parse_failed")) out.add("PP-14-1");
	if (JSON.stringify(mask(p)) !== JSON.stringify(mask(m))) out.add(id.startsWith("r") ? "DIV-005" : id.startsWith("i1") ? "DIV-006" : "DIV-004");
	return [...out].sort();
}

function expectDiagnostics(id, diagnostics) {
	if (id === "c01-symlink-cycle") {
		if (diagnostics.length !== 1) throw new Error("cycle: expected exactly one diagnostic");
		return [{ code_one_of: ["file_info_failed", "list_failed"], path_within: "skills/a/loop" }];
	}
	return diagnostics.map((d) => {
		const out = { code: d.code, path: rel(d.path) };
		if (NORMATIVE_MESSAGE.has(d.code)) out.message = d.message;
		return out;
	});
}

rmSync(outDir, { recursive: true, force: true });
mkdirSync(outDir, { recursive: true });
let count = 0;
for (const s of scenarios) {
	const m = model.get(s.id);
	if (!m || m.skipped || m.rejects) throw new Error(`no model result for ${s.id}`);
	const name = `skills-${s.id}`;
	const doc = {
		name,
		family: "agent",
		authority: "minion-agent-docs spec/harness.md WP-14.1 (HAR-001, HAR-010..HAR-013); assurance/layers/14-wp141-characterization.md",
		pi_revision: PI_REVISION,
		requirements: requirements(s.id),
		witnesses: [`skill_discovery_${s.id.replace(/-/g, "_")}`],
		...(divergences(s.id).length ? { divergences: divergences(s.id) } : {}),
		skill_discovery: {
			...(s.posixOnly ? { posix_only: true } : {}),
			fixture: s.fixture.map((e) => {
				if (e.symlink !== undefined) return { path: e.path, symlink: e.symlink, symlink_kind: e.dir ? "dir" : "file" };
				if (e.dir) return { path: e.path, dir: true };
				return { path: e.path, text: e.text };
			}),
			roots: s.roots,
			expect: {
				skills: m.skills.map((k) => ({
					name: k.name,
					description: k.description,
					content: k.content,
					path: rel(k.filePath),
					disable_model_invocation: k.disableModelInvocation,
				})),
				diagnostics: expectDiagnostics(s.id, m.diagnostics),
			},
		},
	};
	writeFileSync(join(outDir, `${name}.json`), `${JSON.stringify(doc, null, 2)}\n`);
	count++;
}
console.log(`${count} canonical scenarios -> ${outDir}`);
