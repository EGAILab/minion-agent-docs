// WP-13.3 convergence CE-WP133-02 (CON-R005, CON-R006): the lookup lifecycle.
//   node lookup_lifecycle_probe.mjs <pi checkout> <out.json>
// Authority: the pinned findBashOnPath body (sliced from shell.ts, run unchanged) over Node's real spawnSync. Only the
// lookup program is replaced by a controlled Node parent, which may leave a detached descendant holding the pipes.
// Compared with four asynchronous compositions over child_process.spawn: the contract rule, and three wrong rules.
import * as childProcess from "node:child_process";
import { readFileSync, writeFileSync } from "node:fs";
const [piDir, outPath] = process.argv.slice(2);
const source = readFileSync(`${piDir}/packages/coding-agent/src/utils/shell.ts`, "utf8");
const start = source.indexOf("function findBashOnPath(): string | null {");
let depth = 0, end = start;
for (let i = source.indexOf("{", start); i < source.length; i++) {
  if (source[i] === "{") depth++;
  if (source[i] === "}" && --depth === 0) { end = i + 1; break; }
}
const body = source.slice(start, end).replace("function findBashOnPath(): string | null {", "function findBashOnPath() {");

const BUDGET = 1024 * 1024, LIMIT_MS = 5000, GRACE_MS = 100;
const PATH = process.platform === "win32" ? "C:/valid/bash.exe" : "/valid/bash";
// A parent step list and a descendant step list; each step is [delayMs, action].  Actions: "path" (stdout path line),
// "flood" (2 MiB stderr), "exit:<code>" (parent only).  The descendant inherits the parent's stdout/stderr.
const program = (parent, descendant) => {
  const steps = (list, isParent) => list.map(([ms, a]) => {
    const act = a === "path" ? `process.stdout.write(${JSON.stringify(PATH + "\n")})`
      : a === "flood" ? "process.stderr.write(Buffer.alloc(2 * 1024 * 1024, 0x79))"
      : a.startsWith("exit:") ? `process.exit(${+a.slice(5)})`
      : a === "end" ? "process.exit(0)" : "";
    return `await new Promise((r) => setTimeout(r, ${ms})); ${act};`;
  }).join(" ");
  const desc = descendant ? `require("node:child_process").spawn(process.execPath, ["-e", ${JSON.stringify(`(async () => { ${steps(descendant, false)} })()`)}], { stdio: ["ignore", "inherit", "inherit"], detached: true, windowsHide: true }).unref();` : "";
  return `(async () => { ${desc} ${steps(parent, true)} })()`;
};
const rows = {
  parentPathExit0: program([[0, "path"], [0, "exit:0"]]),
  parentPathExit1: program([[0, "path"], [0, "exit:1"]]),
  descendantPathAfterExit: program([[0, "exit:0"]], [[250, "path"], [0, "end"]]),
  descendantPathAfterExitParentExit1: program([[0, "exit:1"]], [[250, "path"], [0, "end"]]),
  overflowWhileAlive: program([[0, "path"], [0, "flood"], [0, "exit:0"]]),
  overflowAfterExit: program([[0, "path"], [0, "exit:0"]], [[250, "flood"], [0, "end"]]),
  overflowAfterExitParentExit1: program([[0, "path"], [0, "exit:1"]], [[250, "flood"], [0, "end"]]),
  timeoutWhileAlive: program([[0, "path"], [5400, "exit:0"]]),
  timeoutAfterExit: program([[0, "path"], [0, "exit:0"]], [[5400, "end"]]),
  descendantPathAfterTimeout: program([[0, "exit:0"]], [[5400, "path"], [0, "end"]]),
  descendantPathThenOverflow: program([[0, "exit:0"]], [[250, "path"], [100, "flood"], [0, "end"]]),
};

let script = "";
let last = null;
const pinned = new Function("spawnSync", "existsSync", "process", `${body}; return findBashOnPath;`)(
  (_cmd, _args, options) => (last = childProcess.spawnSync(process.execPath, ["-e", script], options)), () => true, process);

// mode: "contract" | "exitOnly" | "idleGrace" | "unconditional"
const compose = (mode) => new Promise((resolve) => {
  const c = childProcess.spawn(process.execPath, ["-e", script], { stdio: ["pipe", "pipe", "pipe"], windowsHide: true });
  c.stdin.end();
  const chunks = [];
  let total = 0, exited = false, status = null, interrupted = false, done = false, idle = null;
  const eof = { stdout: false, stderr: false };
  const finish = () => {
    if (done) return;
    done = true;
    clearTimeout(timer); clearTimeout(idle);
    c.stdout.destroy(); c.stderr.destroy();
    const stdout = Buffer.concat(chunks).toString("utf-8");
    if (mode === "unconditional" && interrupted) return resolve(null);
    if (status === 0 && stdout) { const first = stdout.trim().split(/\r?\n/)[0]; return resolve(first || null); }
    resolve(null);
  };
  const check = () => {
    if (done || !exited) return;
    if (mode === "exitOnly" || interrupted || (eof.stdout && eof.stderr)) return finish();
    if (mode === "idleGrace") { clearTimeout(idle); idle = setTimeout(finish, GRACE_MS); }
  };
  const interrupt = () => {
    if (interrupted || done) return;
    interrupted = true;
    if (!exited) c.kill(); // the direct child only, as Node's Kill()
    c.stdout.destroy(); c.stderr.destroy(); // stop collecting: later chunks are not captured
    check();
  };
  const onData = (stream) => (data) => {
    if (done || interrupted) return;
    if (stream === "stdout") chunks.push(data); // the chunk is kept, then the budget is checked
    total += data.length;
    if (total > BUDGET) return interrupt();
    if (mode === "idleGrace") check();
  };
  c.stdout.on("data", onData("stdout")); c.stderr.on("data", onData("stderr"));
  c.stdout.on("end", () => { eof.stdout = true; check(); }); c.stderr.on("end", () => { eof.stderr = true; check(); });
  c.on("exit", (code, signal) => { exited = true; status = signal === null && !(interrupted && code === null) ? code : null; check(); });
  const timer = setTimeout(interrupt, LIMIT_MS);
});

const out = { node: process.version, platform: process.platform, budget: BUDGET, limitMs: LIMIT_MS, rows: {}, controls: {} };
const modes = ["contract", "exitOnly", "idleGrace", "unconditional"];
const killedBy = Object.fromEntries(modes.map((m) => [m, []]));
for (const [name, s] of Object.entries(rows)) {
  script = s;
  const selected = pinned();
  const row = { status: last.status, signal: last.signal, error: last.error?.code ?? null, selected };
  for (const m of modes) {
    const got = await compose(m);
    if (got !== selected) killedBy[m].push(name);
  }
  out.rows[name] = row;
}
out.contractAgreesOnAllRows = killedBy.contract.length === 0;
out.contractDisagreements = killedBy.contract;
delete killedBy.contract;
out.controls = Object.fromEntries(Object.entries(killedBy).map(([m, k]) => [m, { killedBy: k }]));
writeFileSync(outPath, JSON.stringify(out, null, 1) + "\n");
console.log(JSON.stringify(out, null, 1));
