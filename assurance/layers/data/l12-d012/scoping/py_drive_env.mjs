// L12-D012 C001 feasibility: can a Python child see an inherited per-drive cwd entry (=A:)? Launches the given
// Python with a crafted environment block; the child only reads (os.environ, GetEnvironmentVariableW). No files.
import { spawnSync } from "node:child_process";

const py = process.argv[2];
const code = [
  "import os, ctypes",
  "buf = ctypes.create_unicode_buffer(260)",
  "n = ctypes.windll.kernel32.GetEnvironmentVariableW('=A:', buf, 260)",
  "print({'in_os_environ': '=A:' in os.environ, 'getenv': os.getenv('=A:'), 'GetEnvironmentVariableW': buf.value if n else None})",
].join("\n");
const base = Object.fromEntries(Object.entries(process.env).filter(([k]) => !k.startsWith("=")));
const out = spawnSync(py, ["-c", code], { env: { ...base, "=A:": "A:\\deep" }, encoding: "utf8" });
console.log(out.status, out.stdout.trim(), out.stderr.trim());
