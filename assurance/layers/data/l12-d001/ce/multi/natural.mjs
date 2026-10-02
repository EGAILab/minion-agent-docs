import { chmodSync, mkdtempSync, realpathSync } from "node:fs";
import { tmpdir } from "node:os";
import * as path from "node:path";
import { pathToFileURL } from "node:url";
const { NodeExecutionEnv } = await import(pathToFileURL(`${process.argv[2]}/packages/agent/src/harness/env/nodejs.ts`).href);
const tally = {};
for (let run = 0; run < 20; run++) {
  const cwd = realpathSync(mkdtempSync(path.join(tmpdir(), "l12two-"))); const env = new NodeExecutionEnv({ cwd });
  for (const d of ["a", "b"]) { await env.writeFile(`t/${d}/locked`, "x"); chmodSync(path.join(cwd, "t", d), 0o555); }
  const r = await env.remove("t", { recursive: true });
  const k = path.relative(cwd, r.error.path); tally[k] = (tally[k] ?? 0) + 1;
  for (const d of ["a", "b"]) chmodSync(path.join(cwd, "t", d), 0o755);
}
console.log("pi", JSON.stringify(tally));
