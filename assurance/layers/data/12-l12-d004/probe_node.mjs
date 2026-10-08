// Node side: the byte-copied pinned NodeExecutionEnv.canonicalPath (Pi's resolvePath, then
// fs/promises realpath). Usage: node --experimental-strip-types probe_node.mjs <base> <cases.json> <out.json>
import { readFileSync, writeFileSync } from "node:fs";
import { NodeExecutionEnv } from "../wp141-char/pinned/env/nodejs.ts";

const [base, casesPath, out] = process.argv.slice(2);
const env = new NodeExecutionEnv({ cwd: base });
const rows = [];
for (const c of JSON.parse(readFileSync(casesPath, "utf8"))) {
	const r = await env.canonicalPath(c.rel);
	rows.push({ rel: c.rel, node: r.ok ? { ok: r.value } : { error: r.error.code, cause: r.error.cause?.code ?? null } });
}
writeFileSync(out, JSON.stringify(rows, null, 1));
