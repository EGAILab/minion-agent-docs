// WP-13.3 CE-WP133-01 (R003), Windows: Node existsSync/access(F_OK)/realpath vs the EXEC-007 probe_dir_entry OS
// sequence (lstat; stat if a symlink), run by CPython on the same fixtures.  node existence_probe_win.mjs <python> <out>
import fs from "node:fs"; import os from "node:os"; import path from "node:path"; import { spawnSync } from "node:child_process";
const [py, outPath] = process.argv.slice(2);
const T = fs.mkdtempSync(path.join(os.tmpdir(), "wp133-exist-")); const j = (...p) => path.join(T, ...p);
fs.writeFileSync(j("file"), "x"); fs.mkdirSync(j("dir"));
const links = {};
for (const [name, target, type] of [["l_file", "file", "file"], ["l_dir", "dir", "dir"], ["l_dangling", "missing", "file"], ["j_dir", j("dir"), "junction"]]) {
  try { fs.symlinkSync(target, j(name), type); links[name] = "created"; } catch (e) { links[name] = e.code; }
}
const paths = [["file"], ["dir"], ["dir", ""], ["l_file"], ["l_dir"], ["l_dangling"], ["j_dir"], ["missing"], ["file", "child"]]
  .map((p) => j(...p)).map((p, i) => (i === 2 ? p + path.sep : p));
const ok = (f) => { try { f(); return true; } catch (e) { return e.code; } };
const node = paths.map((p) => ({ existsSync: fs.existsSync(p), accessF_OK: ok(() => fs.accessSync(p, fs.constants.F_OK)), realpath: ok(() => fs.realpathSync(p)) }));
const pyCode = "import os,stat,json,sys,errno\nout=[]\nfor p in json.loads(sys.argv[1]):\n try:\n  st=os.lstat(p)\n  if stat.S_ISLNK(st.st_mode) or getattr(st,'st_reparse_tag',0): os.stat(p)\n  out.append(True)\n except OSError as e: out.append(errno.errorcode.get(e.errno,str(e.errno)))\nprint(json.dumps(out))";
const pyOut = JSON.parse(spawnSync(py, ["-c", pyCode, JSON.stringify(paths)], { encoding: "utf8" }).stdout);
const cases = paths.map((p, i) => ({ path: p.replace(T, "$T"), ...node[i], probe_dir_entry_ok: pyOut[i] }));
fs.writeFileSync(outPath, JSON.stringify({ runtime: process.version, links, cases }, null, 1) + "\n");
console.log(JSON.stringify({ links, cases }));
