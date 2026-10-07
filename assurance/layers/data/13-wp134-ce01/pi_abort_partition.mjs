// CE-L13-WP134-01: pinned Pi find/grep abort partition. Runs the unmodified pinned execute bodies
// (sliced by the committed harness prefix) with a scripted child process; the call's signal is
// aborted at one point of the child's life. Points mirror the Python probe:
//   spawn        - inside spawn(), before it returns (grep registers its listener after spawn)
//   stdout_data  - after the result line is delivered
//   stdout_eof   - after stdout ends
//   stderr_eof   - after stderr ends (both stdio ends reached, process not yet exited)
//   wait         - after 'exit', before 'close'
//   stdout_close / stderr_close - after 'close' (Node emits close after exit AND stdio end)
//   node ce01_pi_abort_partition.mjs <harness search_probe.mjs> <pi> <engines> <scratch>
import { mkdirSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const [harnessPath, pi, engines, scratch] = process.argv.slice(2);
const harness = readFileSync(harnessPath, "utf8");
const prefix = harness.slice(0, harness.indexOf("// ---------------------------------------------------------------- corpus"));
process.argv = [process.argv[0], harnessPath, pi, engines, scratch, join(scratch, "unused.json")];
const root = mkdtempSync(join(scratch, "ce01-pi-"));
writeFileSync(join(root, "a.ts"), "x\n");
const tail = `
const { EventEmitter } = await import("node:events");
const { PassThrough } = await import("node:stream");
const ROOT = ${JSON.stringify(root)};
const POINTS = ["spawn", "stdout_data", "stdout_eof", "stderr_eof", "wait", "stdout_close", "stderr_close"];
const tick = () => new Promise((r) => setImmediate(r));
function scripted(point, controller, line) {
  return () => {
    const child = new EventEmitter();
    child.stdout = new PassThrough(); child.stderr = new PassThrough(); child.killed = false;
    child.kill = () => { child.killed = true; return true; };
    const at = (p) => { if (p === point) controller.abort(); };
    at("spawn");
    (async () => {
      await tick(); child.stdout.write(line); await tick(); at("stdout_data");
      child.stdout.end(); await tick(); await tick(); at("stdout_eof");
      child.stderr.end(); await tick(); await tick(); at("stderr_eof");
      child.emit("exit", 0); await tick(); at("wait");
      child.emit("close", 0); at("stdout_close"); await tick(); at("stderr_close");
    })();
    return child;
  };
}
const out = {};
for (const tool of ["find", "grep"]) {
  for (const point of POINTS) {
    const controller = new AbortController();
    let execute;
    if (tool === "find") {
      execute = findExecute(path, scripted(point, controller, path.join(ROOT, "a.ts") + "\\n"), createInterface, ensureTool,
        pathExists, resolveToCwd, truncateHead, formatSize, DEFAULT_MAX_BYTES, ROOT);
    } else {
      const ev = JSON.stringify({ type: "match", data: { path: { text: path.join(ROOT, "a.ts") }, line_number: 1, lines: { text: "x\\n" } } });
      execute = grepExecute(path, scripted(point, controller, ev + "\\n"), createInterface, ensureTool, resolveToCwd, truncateHead,
        truncateLine, formatSize, DEFAULT_MAX_BYTES, GREP_MAX_LINE_LENGTH, fsStat, fsReadFile, ROOT);
    }
    const args = tool === "find" ? { pattern: "*" } : { pattern: "x" };
    try { const r = await execute("c", args, controller.signal); out[tool + "/" + point] = r.content[0].text; }
    catch (e) { out[tool + "/" + point] = "ERR " + e.message; }
  }
}
console.log(JSON.stringify(out, null, 1));
`;
await import("data:text/javascript;base64," + Buffer.from(prefix + tail).toString("base64"));
