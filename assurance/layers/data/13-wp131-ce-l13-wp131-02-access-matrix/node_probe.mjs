// Pinned Pi's read path, operation by operation (read.ts: access(R_OK); mime.ts: open + read 4100;
// read.ts: readFile), plus realpath/lstat/stat for comparison. Prints JSON {case: {op: code|"ok"}}.
import fs from "node:fs";
const root = process.argv[2];
const cases = ["f_ok", "f_000", "d_ok", "d_000", "d_x", "d_r", "d_x/inner", "d_r/inner", "lk_f_ok", "lk_f_000",
  "lk_d_ok", "lk_d_000", "dangling", "loop_a", "f_ok/x", "missing"];
const run = (g) => { try { g(); return "ok"; } catch (e) { return e.code; } };
const out = {};
for (const c of cases) {
  const p = `${root}/${c}`;
  out[c] = {
    access_R_OK: run(() => fs.accessSync(p, fs.constants.R_OK)),
    realpath: run(() => fs.realpathSync(p)),
    lstat: run(() => fs.lstatSync(p)),
    stat: run(() => fs.statSync(p)),
    sniff_open_read: run(() => { const h = fs.openSync(p, "r"); try { fs.readSync(h, Buffer.alloc(4100), 0, 4100, 0); } finally { fs.closeSync(h); } }),
    readFile: run(() => fs.readFileSync(p)),
  };
}
console.log(JSON.stringify({ node: process.version, platform: process.platform, cases: out }));
