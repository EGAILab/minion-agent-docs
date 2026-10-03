// WP-12.E5: what Node's direct-child termination observably does (Pi's lookup interruption, spawn_sync Kill(), and
// ChildProcess.kill() all call uv_process_kill(process, SIGTERM)).
//   node kill_probe.mjs <out.json>        (run on Windows natively and on Linux in node:22.15.1-bookworm-slim)
// Each row spawns a controlled Node child, requests termination once it is ready, and records the final outcome.
// Descendant survival is observed through a marker file the descendant writes after the parent was terminated.
// POSIX: the descendant stays in the child's process group, so its survival shows the signal went to the PID only.
// Windows: a Node child puts its own children in a kill-on-close job object, so the descendant is spawned detached
// (outside that job) to observe TerminateProcess itself rather than the job's cleanup.
import { spawn, spawnSync } from "node:child_process";
import { existsSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
const [outPath] = process.argv.slice(2);
const T = mkdtempSync(join(tmpdir(), "e5-kill-"));
const marker = (name) => join(T, name);

// child programs: print "ready" once their SIGTERM disposition is installed
const CHILD = {
  default: `process.stdout.write("ready\\n"); setInterval(() => {}, 1000);`,
  handledExit0: `process.on("SIGTERM", () => process.exit(0)); process.stdout.write("ready\\n"); setInterval(() => {}, 1000);`,
  handledExit7: `process.on("SIGTERM", () => process.exit(7)); process.stdout.write("ready\\n"); setInterval(() => {}, 1000);`,
  handledDelayedExit0: `process.on("SIGTERM", () => setTimeout(() => process.exit(0), 500)); process.stdout.write("ready\\n"); setInterval(() => {}, 1000);`,
  ignoredThenSelfExit0: `process.on("SIGTERM", () => setTimeout(() => process.exit(0), 800)); process.stdout.write("ready\\n"); setInterval(() => {}, 1000);`,
  withDescendant: (m) => `require("node:child_process").spawn(process.execPath, ["-e", ${JSON.stringify(`setTimeout(() => require("node:fs").writeFileSync(${JSON.stringify(m)}, "alive"), 700)`)}], { stdio: "ignore", detached: process.platform === "win32" }); process.stdout.write("ready\\n"); setInterval(() => {}, 1000);`,
};

const run = (program, { killAfterExit = false } = {}) => new Promise((resolve) => {
  const c = spawn(process.execPath, ["-e", program], { stdio: ["ignore", "pipe", "ignore"] });
  const t0 = Date.now();
  let killedAt = null, firstKill = null, secondKill = null;
  c.stdout.once("data", () => {
    if (killAfterExit) return;
    killedAt = Date.now(); firstKill = c.kill(); secondKill = c.kill();
  });
  c.on("exit", (code, signal) => {
    const exitAt = Date.now();
    let afterExitKill = null;
    if (killAfterExit) afterExitKill = c.kill();
    resolve({ code, signal, firstKillReturned: firstKill, secondKillReturned: secondKill, killAfterExitReturned: afterExitKill,
      exitMsAfterKill: killedAt === null ? null : exitAt - killedAt >= 400 ? ">=400" : "<400" });
  });
});

const out = { node: process.version, platform: process.platform, uv: process.versions.uv, rows: {} };
for (const name of ["default", "handledExit0", "handledExit7", "handledDelayedExit0", "ignoredThenSelfExit0"]) out.rows[name] = await run(CHILD[name]);
{
  const m = marker("descendant");
  const r = await run(CHILD.withDescendant(m));
  await new Promise((res) => setTimeout(res, 1200));
  out.rows.descendantNotTargeted = { ...r, descendantWroteMarker: existsSync(m) };
}
out.rows.alreadyExited = await run(`process.exit(3)`, { killAfterExit: true });
// the lookup discriminator (Pi's own options; a child that prints a path, catches SIGTERM and exits 0)
{
  const r = spawnSync(process.execPath, ["-e", `process.on("SIGTERM", () => process.exit(0)); process.stdout.write("/valid/bash\\n"); setTimeout(() => {}, 8000);`],
    { encoding: "utf-8", timeout: 1000 });
  out.rows.spawnSyncTimeoutHandledExit0 = { status: r.status, signal: r.signal, error: r.error?.code ?? null, stdout: r.stdout };
}
writeFileSync(outPath, JSON.stringify(out, null, 1) + "\n");
console.log(JSON.stringify(out, null, 1));
