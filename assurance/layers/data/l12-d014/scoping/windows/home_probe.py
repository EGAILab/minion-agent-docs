"""#236 L12-D014 scoping probe: where `~` gets its home directory, pinned Pi vs merged Python vs Rust.

Read-only: every child runs with cwd set to one EXISTING directory and a crafted environment; nothing is created,
written, renamed or deleted; results go to stdout only. Home values are strings handed to children, never paths
this probe touches. Children:
  node   -- pinned Pi resolvePath, sliced unmodified from the verified pinned blob (the oracle); os.homedir() too
  python -- merged Python LocalFileSystem.absolute_path (observation)
  rust   -- the ignored native_observer test of a Rust test binary (observation)
Partition (win32): USERPROFILE x HOME x HOMEDRIVE/HOMEPATH x input, provider cwd C:\\x.

    python home_probe.py <node.exe> <pinned Pi checkout> <python src> <existing dir> <rust test binary>
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
let home;
try { home = { value: units(homedir()) }; } catch (e) { home = { error: String(e && e.code || e) }; }
console.log(JSON.stringify({ home, rows: inputs.map((i) => {
  try { return { value: units(resolvePath(provider, i)) }; }
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
        result = asyncio.run(fs.absolute_path(text(u)))
        if hasattr(result, "value"):
            rows.append({"value": units(result.value)})
        else:
            rows.append({"error": str(getattr(result.error, "code", result.error))})
    except Exception as e:
        rows.append({"error": type(e).__name__})
print(json.dumps({"home": {"value": units(os.path.expanduser("~"))}, "rows": rows}))
"""

INPUTS = ["~", "~/a", "~\\a", "~/", "~/..", "~/a/../b", "~a", "a~"]
LONE = "\ud800"


def units(value: str) -> list[int]:
    return list(memoryview(value.encode("utf-16-le", "surrogatepass")).cast("H"))


def text(value: list[int]) -> str:
    return b"".join(u.to_bytes(2, "little") for u in value).decode("utf-16-le", "surrogatepass")


def run_json(argv: list[str], cwd: str, env: dict[str, str]) -> dict[str, object]:
    try:
        out = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, encoding="utf-8", timeout=60)
    except (OSError, ValueError) as error:
        return {"spawn_error": repr(error)}
    if out.returncode != 0:
        return {"exit": out.returncode, "stderr": out.stderr[-400:]}
    return json.loads(out.stdout)


def run_rust(binary: str, provider: str, inputs: list[list[int]], cwd: str, env: dict[str, str]) -> dict[str, object]:
    payload = {"provider_cwd": units(provider), "inputs": inputs, "absent_entries": [], "process_cwd_drive_not": []}
    try:
        out = subprocess.run([binary, "execution::path::tests::native_observer", "--exact", "--ignored", "--nocapture"],
                             cwd=cwd, env={**env, "MINION_PATH_PROBE": json.dumps(payload)}, capture_output=True,
                             timeout=90)
    except (OSError, ValueError) as error:
        return {"spawn_error": repr(error)}
    lines = [x for x in out.stdout.decode("utf-8", "replace").splitlines() if x.startswith("PATH_PROBE ")]
    if out.returncode != 0 or len(lines) != 1:
        return {"exit": out.returncode, "tail": (out.stdout + out.stderr).decode("utf-8", "replace")[-600:]}
    record = json.loads(lines[0][len("PATH_PROBE "):])
    return {"rows": [{"value": r["absolute_path"]} for r in record["rows"]]}


def main(node: str, pi: str, pysrc: str, directory: str, rust: str) -> None:
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
    if not (os.path.isabs(directory) and os.path.isdir(directory)):
        raise SystemExit("an existing absolute directory is required")
    provider = "C:\\x"
    profiles = [
        ("unset", None), ("empty", ""), ("two-byte", "C:"), ("drive-root", "C:\\"), ("ordinary", "C:\\Users\\px"),
        ("trailing", "C:\\Users\\px\\"), ("forward", "C:/Users/px"), ("extended", "\\\\?\\C:\\Users\\px"),
        ("unc", "\\\\srv\\share\\px"), ("relative", "rel\\px"), ("lone-high", "C:\\Users\\p" + LONE),
        ("long-300", "C:\\" + "p" * 297),
    ]
    homes = [("unset", None), ("set", "D:\\hx"), ("empty", "")]
    homepaths = [("unset", None, None), ("set", "F:", "\\hp")]
    inputs = [units(i) for i in INPUTS]
    base = {k: v for k, v in os.environ.items()
            if not k.startswith("=") and k.upper() not in ("USERPROFILE", "HOME", "HOMEDRIVE", "HOMEPATH")}
    base["PYTHONDONTWRITEBYTECODE"] = "1"
    report = []
    for pname, pvalue in profiles:
        for hname, hvalue in homes:
            for hpname, hdrive, hpath in homepaths:
                if hpname == "set" and pname != "unset":
                    continue  # HOMEDRIVE/HOMEPATH only matter to Python when USERPROFILE is unset
                env = dict(base)
                for key, value in (("USERPROFILE", pvalue), ("HOME", hvalue), ("HOMEDRIVE", hdrive),
                                   ("HOMEPATH", hpath)):
                    if value is not None:
                        env[key] = value
                row: dict[str, object] = {"userprofile": pname, "home": hname, "homepath": hpname}
                row["node"] = run_json([node, "--no-warnings", "--input-type=module", "-e", NODE_CHILD, pi,
                                        json.dumps(units(provider)), json.dumps(inputs)], directory, env)
                row["python"] = run_json([sys.executable, "-c", PY_CHILD, pysrc, json.dumps(units(provider)),
                                          json.dumps(inputs)], directory, env)
                row["rust"] = run_rust(rust, provider, inputs, directory, env)
                n = row["node"]
                for name in ("python", "rust"):
                    p = row[name]
                    if isinstance(n, dict) and isinstance(p, dict) and "rows" in n and "rows" in p:
                        row[name + "_equal"] = [a == b for a, b in zip(n["rows"], p["rows"])]
                report.append(row)
    print(json.dumps({"inputs": INPUTS, "provider": provider, "report": report}, indent=1, ensure_ascii=True))


if __name__ == "__main__":
    main(*sys.argv[1:])
