// L12-D012: merge the Windows and Linux partials into the canonical fs-path-resolution document (stdout only; the
// launcher writes it). Each partial must come from pinned Pi on native Node v22.15.1 of its own platform.
import { readFileSync } from "node:fs";

const [winPath, linPath] = process.argv.slice(2);
const win = JSON.parse(readFileSync(winPath, "utf8"));
const lin = JSON.parse(readFileSync(linPath, "utf8"));
const PI = "b7bb00b936dbe21b8e160b3e89efdec361846699";
for (const [p, want] of [[win, "win32"], [lin, "linux"]]) {
  if (p.platform !== want || p.node !== "v22.15.1" || p.pi !== PI) throw new Error(`bad partial: ${p.platform} ${p.node} ${p.pi}`);
}
if (win.cases.filter((c) => c.id.startsWith("baseline/")).length !== 23) throw new Error("win32 baseline must have 23 cases");
if (win.cases.filter((c) => c.id.startsWith("host/")).length !== 32) throw new Error("win32 host-state must have 32 cases");
if (lin.cases.length !== 25 || lin.cases.some((c) => c.host !== null)) throw new Error("linux must have 25 baseline cases");
const cases = [...win.cases.map((c) => ({ ...c, id: `win32/${c.id}` })), ...lin.cases.map((c) => ({ ...c, id: `linux/${c.id}` }))];
const doc = {
  name: "path-resolution",
  family: "agent",
  authority: "pinned Pi b7bb00b9 packages/agent/src/harness/env/nodejs.ts:51-65 resolvePath (sliced unmodified) on native "
    + "Node v22.15.1 path.resolve / fileURLToPath, generated natively on Windows 11 and on Linux (node:22.15.1-bookworm-slim) "
    + "by minion-agent-docs assurance/layers/data/l12-d012/gen (L12-D012, minion-agent#229)",
  pi_revision: PI,
  requirements: ["EXEC-002", "EXEC-005"],
  witnesses: ["fs_path_resolution_colon_and_drive_relative"],
  platforms: ["linux", "win32"],
  notes: "spec/execution.md section 3.2 (DIRECT_PI_PARITY), unchanged; record 12-l12-d012-path-colon.md. Lexical "
    + "ctx.fs.absolute_path only: never create, write or use as a cwd any of these paths. baseline cases run in-process "
    + "under VERIFIED preconditions (absent per-drive entries, process cwd drive) and REFUSE otherwise; host cases run the "
    + "real resolver seam in a CHILD process whose environment block carries exactly the case's per-drive entry (and no "
    + "other '='-prefixed entry) and whose cwd is a contained sandbox directory; cwd_drive / cwd_tail parts are filled "
    + "from that child cwd.",
  path_resolution: { cases },
};
console.log(JSON.stringify(doc, null, 1));
