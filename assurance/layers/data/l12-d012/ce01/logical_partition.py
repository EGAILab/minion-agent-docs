"""CE-L12D012-01 revision 2 (checkpoint review 2, #229 issuecomment-6178582084): LOGICAL caller input crossed
with the other-drive branch. A non-scalar logical path argument must stay raw (spec section 14.1's logical domain)
when it reaches the drive-relative selection branch, while the NATIVE selected value takes Node's section 15 view.

A Python parent (it can place a lone surrogate in a child's block) launches, per row, a NODE child (pinned Pi
resolvePath, sliced unmodified; the oracle) and a PYTHON child (the real LocalFileSystem.absolute_path) with
IDENTICAL environment blocks (ordinary variables, no `=`-entry, plus exactly the row's `=E:`). The LOGICAL input is
passed to both children as a JSON array of UTF-16 code units and rebuilt INSIDE each child (String.fromCharCode
in Node; surrogatepass decoding in Python), so no OS argv conversion touches it. Each child reports its view of
`=E:` and the result as UTF-16 units; the binding's native read must equal the crafted entry. Provider cwd C:\\x.
Pure computation; no filesystem operation on any case value; stdout only. Runs from the project root (E:).

    python logical_partition.py <node.exe> <pinned Pi checkout> <candidate src>
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

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
const units = (s) => (s === undefined ? null : Array.from({ length: s.length }, (_, i) => s.charCodeAt(i)));
const input = String.fromCharCode(...JSON.parse(process.argv[2]));
console.log(JSON.stringify({ entry: units(process.env["=E:"]), out: units(resolvePath("C:\\x", input)) }));
"""

PY_CHILD = r"""
import asyncio, ctypes, json, sys
from ctypes import wintypes
sys.path.insert(0, sys.argv[1])
from minion_agent.execution.filesystem import LocalFileSystem
k32 = ctypes.WinDLL("kernel32", use_last_error=True)
k32.GetEnvironmentVariableW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
buf = ctypes.create_unicode_buffer(4096)
n = k32.GetEnvironmentVariableW("=E:", buf, 4096)
entry = ctypes.wstring_at(ctypes.addressof(buf), n) if n else (None if ctypes.get_last_error() == 203 else "")
def units(s):
    return None if s is None else list(memoryview(s.encode("utf-16-le", "surrogatepass")).cast("H"))
data = b"".join(u.to_bytes(2, "little") for u in json.loads(sys.argv[2]))
logical = data.decode("utf-16-le", "surrogatepass")
out = asyncio.run(LocalFileSystem("C:\\x").absolute_path(logical)).value
print(json.dumps({"entry": units(entry), "out": units(out)}))
"""

# (label, native =E: entry, logical input). The predicted Pi value is in the record (section 8); a disagreeing
# Node observation stops the implementation pass.
ROWS = [
    ("scalar-positive", "E:\\deep", "e:leaf"),
    ("logical-lone-high", "E:\\deep", "e:leaf\ud800"),
    ("logical-lone-low", "E:\\deep", "e:leaf\ude00"),
    ("logical-pair", "E:\\deep", "e:leaf\U0001f600"),
    ("native-and-logical-nonscalar", "E:\\de\ud83dp", "e:leaf\ud800"),
]


def units(text: str | None) -> list[int] | None:
    return None if text is None else list(memoryview(text.encode("utf-16-le", "surrogatepass")).cast("H"))


PI_COMMIT = "b7bb00b936dbe21b8e160b3e89efdec361846699"
PI_FILE = "packages/agent/src/harness/env/nodejs.ts"


def text(units_: list[int]) -> str:
    return b"".join(u.to_bytes(2, "little") for u in units_).decode("utf-16-le", "surrogatepass")


# The record's source predictions (section 8): checked explicitly after the run; any disagreement stops.
PREDICTED = {
    "scalar-positive": "e:\\deep\\leaf",
    "logical-lone-high": "e:\\deep\\leaf\ud800",
    "logical-lone-low": "e:\\deep\\leaf\ude00",
    "logical-pair": "e:\\deep\\leaf\U0001f600",
    "native-and-logical-nonscalar": "e:\\de\ufffd\ufffd\ufffdp\\leaf\ud800",
}


def main(node: str, pi: str, src: str) -> None:
    if sys.platform != "win32":
        raise SystemExit("win32 only")
    version = subprocess.run([node, "--version"], capture_output=True, text=True, check=True).stdout.strip()
    if version != "v22.15.1":
        raise SystemExit(f"node is {version}, not v22.15.1")
    pinned = subprocess.run(["git", "-C", pi, "rev-parse", f"{PI_COMMIT}:{PI_FILE}"],
                            capture_output=True, text=True, check=True).stdout.strip()
    actual = subprocess.run(["git", "-C", pi, "hash-object", PI_FILE],
                            capture_output=True, text=True, check=True).stdout.strip()
    if pinned != actual:
        raise SystemExit(f"{PI_FILE} is not the pinned blob ({actual} != {pinned})")
    base = {k: v for k, v in os.environ.items() if not k.startswith("=")}
    base["PYTHONDONTWRITEBYTECODE"] = "1"
    rows = []
    for label, entry, logical in ROWS:
        env = {**base, "=E:": entry}
        arg = json.dumps(units(logical))
        oracle = json.loads(subprocess.run([node, "--no-warnings", "--input-type=module", "-e", NODE_CHILD, pi, arg],
                                           env=env, capture_output=True, encoding="utf-8", check=True).stdout)
        binding = json.loads(subprocess.run([sys.executable, "-c", PY_CHILD, src, arg],
                                            env=env, capture_output=True, encoding="utf-8", check=True).stdout)
        if binding["entry"] != units(entry):
            raise SystemExit(f"{label}: the binding child's =E: entry is not the crafted one")
        rows.append({"label": label, "entry": units(entry), "node_entry": oracle["entry"], "logical": units(logical),
                     "node": oracle["out"], "binding": binding["out"], "match": oracle["out"] == binding["out"],
                     "node_equals_prediction": text(oracle["out"]) == PREDICTED[label]})
    print(json.dumps({"platform": sys.platform, "node": version, "pi_blob_verified": True,
                      "all_predictions_confirmed": all(r["node_equals_prediction"] for r in rows), "rows": rows},
                     indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:])
