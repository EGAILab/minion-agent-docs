"""#235 L12-D013 scoping probe: win32 rooted drive-less inputs under pinned Pi resolvePath vs merged Python.

Read-only: every child runs with cwd set to an EXISTING directory; nothing is created, written, renamed or
deleted; results go to stdout only. Children:
  node   -- pinned Pi resolvePath, sliced unmodified from the verified pinned blob (the oracle)
  python -- merged Python LocalFileSystem.absolute_path (observation, not an oracle)
Partition: process-cwd form x provider cwd x inherited `=X:` entries x input. Inputs are rooted without a
device (leading \\ or /), plus non-UNC double-separator forms, dot segments and a non-ASCII leaf.

    python rooted_probe.py <node.exe> <pinned Pi checkout> <python src> <existing dir on a non-C: drive>
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

PI_COMMIT = "b7bb00b936dbe21b8e160b3e89efdec361846699"
PI_FILE = "packages/agent/src/harness/env/nodejs.ts"

NODE_CHILD = r"""
import { readFileSync } from "node:fs";
import { homedir } from "node:os";
import path from "node:path";
import { stripTypeScriptTypes } from "node:module";
import { fileURLToPath } from "node:url";
const src = readFileSync(`${process.argv[1]}/packages/agent/src/harness/env/nodejs.ts`, "utf8");
const body = stripTypeScriptTypes(src.slice(src.indexOf("function resolvePath(cwd: string, path: string): string {"),
  src.indexOf("function fileKindFromStats("))) + "\nreturn resolvePath;";
const resolvePath = new Function("homedir", "join", "fileURLToPath", "isAbsolute", "resolve", "process", body)(
  homedir, path.join, fileURLToPath, path.isAbsolute, path.resolve, process);
const units = (s) => Array.from({ length: s.length }, (_, i) => s.charCodeAt(i));
const text = (u) => String.fromCharCode(...u);
const provider = text(JSON.parse(process.argv[2]));
const inputs = JSON.parse(process.argv[3]).map(text);
console.log(JSON.stringify({ cwd: units(process.cwd()), rows: inputs.map((i) => {
  try { return { abs: path.isAbsolute(i), value: units(resolvePath(provider, i)) }; }
  catch (e) { return { error: String(e && e.code || e) }; } }) }));
"""

PY_CHILD = r"""
import asyncio, json, os, sys
sys.path.insert(0, sys.argv[1])
from minion_agent.execution.filesystem import LocalFileSystem
def units(s):
    return list(memoryview(s.encode("utf-16-le", "surrogatepass")).cast("H"))
def text(u):
    return b"".join(x.to_bytes(2, "little") for x in u).decode("utf-16-le", "surrogatepass")
fs = LocalFileSystem(text(json.loads(sys.argv[2])))
rows = []
for u in json.loads(sys.argv[3]):
    try:
        rows.append({"value": units(asyncio.run(fs.absolute_path(text(u))).value)})
    except Exception as e:
        rows.append({"error": type(e).__name__})
print(json.dumps({"cwd": units(os.getcwd()), "rows": rows}))
"""

INPUTS = ["\\leaf", "/leaf", "\\", "/", "\\a\\b\\..\\c", "/a/./b", "\\.\\leaf", "\\..\\leaf", "\\..",
          "\\leaf\\", "/leaf/", "\\\\leaf", "//leaf", "\\/leaf", "/\\leaf", "\\\\\\leaf", "\\caf\u00e9",
          "\\leaf.", "\\a\\\\b"]


def units(value: str) -> list[int]:
    return list(memoryview(value.encode("utf-16-le", "surrogatepass")).cast("H"))


def text(value: list[int]) -> str:
    return b"".join(u.to_bytes(2, "little") for u in value).decode("utf-16-le", "surrogatepass")


def run_json(argv: list[str], cwd: str, env: dict[str, str]) -> dict[str, object]:
    try:
        out = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, encoding="utf-8", timeout=60)
    except OSError as error:
        return {"spawn_error": repr(error)}
    if out.returncode != 0:
        return {"exit": out.returncode, "stderr": out.stderr[-400:]}
    return json.loads(out.stdout)


def main(node: str, pi: str, pysrc: str, directory: str) -> None:
    if sys.platform != "win32":
        raise SystemExit("win32 only")
    if subprocess.run([node, "--version"], capture_output=True, text=True, check=True).stdout.strip() != "v22.15.1":
        raise SystemExit("node is not v22.15.1")
    pinned = subprocess.run(["git", "-C", pi, "rev-parse", f"{PI_COMMIT}:{PI_FILE}"],
                            capture_output=True, text=True, check=True).stdout.strip()
    actual = subprocess.run(["git", "-C", pi, "hash-object", PI_FILE], capture_output=True, text=True,
                            check=True).stdout.strip()
    if pinned != actual:
        raise SystemExit("nodejs.ts is not the pinned blob")
    if not (os.path.isabs(directory) and os.path.isdir(directory)) or directory.startswith("\\\\"):
        raise SystemExit("an existing absolute drive-letter directory is required")
    drive = directory[0].upper()
    if drive in ("A", "C"):
        raise SystemExit("the directory must not be on A: or C:")
    root = drive + ":\\"
    cwd_forms = [("plain", directory), ("drive_root", root), ("extended", "\\\\?\\" + directory)]
    providers = ["C:\\x", drive + ":\\y", "\\\\srv\\share\\x", "\\\\?\\C:\\x"]
    # Inherited drive-cwd entries: absent, or present for both drives at unrelated directories.
    entry_sets = [("absent", {}), ("present", {"=C:": "C:\\envc", "=" + drive + ":": drive + ":\\envd"})]
    inputs = [units(i) for i in INPUTS]
    base = {k: v for k, v in os.environ.items() if not k.startswith("=")}
    base["PYTHONDONTWRITEBYTECODE"] = "1"
    report = []
    for form, cwd in cwd_forms:
        for entry_name, entries in entry_sets:
            env = {**base, **entries}
            for provider in providers:
                row: dict[str, object] = {"cwd_form": form, "entries": entry_name, "provider": provider}
                row["node"] = run_json([node, "--no-warnings", "--input-type=module", "-e", NODE_CHILD, pi,
                                        json.dumps(units(provider)), json.dumps(inputs)], cwd, env)
                row["python"] = run_json([sys.executable, "-c", PY_CHILD, pysrc, json.dumps(units(provider)),
                                          json.dumps(inputs)], cwd, env)
                for name in ("node", "python"):
                    value = row[name]
                    if isinstance(value, dict) and "rows" in value:
                        value["cwd_text"] = text(value["cwd"])
                        for r in value["rows"]:
                            if "value" in r:
                                r["text"] = text(r["value"])
                n, p = row["node"], row["python"]
                if isinstance(n, dict) and isinstance(p, dict) and "rows" in n and "rows" in p:
                    row["equal"] = [a.get("value") == b.get("value") and a.get("error") == b.get("error")
                                    for a, b in zip(n["rows"], p["rows"])]
                report.append(row)
    print(json.dumps({"inputs": INPUTS, "report": report}, indent=1, ensure_ascii=True))


if __name__ == "__main__":
    main(*sys.argv[1:])
