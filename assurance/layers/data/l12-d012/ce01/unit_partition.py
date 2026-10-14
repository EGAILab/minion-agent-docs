"""CE-L12D012-01 characterization (L12D012-PY-I002): UTF-16 code-unit versus Python-character indexing in
the win32 drive-relative selection branch, over inherited `=A:` values that differ between the two indexings.

A Python parent launches, for each crafted entry, (1) a NODE child running pinned Pi `resolvePath` (sliced
unmodified from packages/agent/src/harness/env/nodejs.ts, native Node v22.15.1) -- the oracle -- and (2) a
PYTHON child calling the real `LocalFileSystem.absolute_path` of the candidate binding -- the observation --
with IDENTICAL environment blocks: the parent's ordinary variables plus exactly `=A:`. A Python parent is
used because it can place a lone surrogate in a child's environment block (Node's own spawn converts strings
through UTF-8, replacing lone surrogates). Each child reports the entry it actually received, as UTF-16 code
units, and the parent asserts it equals the crafted one before accepting a row. Provider cwd C:\\x, input
a:leaf. Pure computation in the children; no case value is ever accessed, created or used as a cwd. The parent
writes nothing (stdout only).

    python unit_partition.py <node.exe> <pinned Pi checkout> <candidate minion-agent-python/src>
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
console.log(JSON.stringify({ node: process.version, entry: units(process.env["=A:"]), out: units(resolvePath("C:\\x", "a:leaf")) }));
"""

PY_CHILD = r"""
import asyncio, ctypes, json, sys
from ctypes import wintypes
sys.path.insert(0, sys.argv[1])
from minion_agent.execution.filesystem import LocalFileSystem
k32 = ctypes.WinDLL("kernel32", use_last_error=True)
k32.GetEnvironmentVariableW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
buf = ctypes.create_unicode_buffer(4096)
n = k32.GetEnvironmentVariableW("=A:", buf, 4096)
raw = ctypes.wstring_at(ctypes.addressof(buf), n) if n else (None if ctypes.get_last_error() == 203 else "")
def units(s):
    return None if s is None else list(memoryview(s.encode("utf-16-le", "surrogatepass")).cast("H"))
out = asyncio.run(LocalFileSystem("C:\\x").absolute_path("a:leaf")).value
print(json.dumps({"entry": units(raw), "out": units(out)}))
"""

# (label, entry) -- None means absent. Each differs, or is the nearest control, between unit and character
# positions 0-2 of the selected value.
ENTRIES: list[tuple[str, str | None]] = [
    ("absent", None),
    ("empty", ""),
    ("ascii-match", "A:\\deep"),
    ("bmp-1", "\u00e9\\deep"),
    ("astral-backslash", "\U0001f600\\deep"),
    ("astral-slash", "\U0001f600/deep"),
    ("x-astral-backslash", "x\U0001f600\\deep"),
    ("astral-x-backslash", "\U0001f600x\\deep"),
    ("astral-only", "\U0001f600"),
    ("x-astral", "x\U0001f600"),
    ("device-astral-backslash", "A:\U0001f600\\deep"),
    ("lone-high-backslash", "\ud83d\\deep"),
    ("x-lone-high-backslash", "x\ud83d\\deep"),
    ("lone-low-x-backslash", "\ude00x\\deep"),
    ("bmp-bmp-backslash", "\u00e9\u00e9\\deep"),
]


def main(node: str, pi: str, src: str) -> None:
    if sys.platform != "win32":
        raise SystemExit("win32 only")
    base = {k: v for k, v in os.environ.items() if not k.startswith("=")}
    rows = []
    for label, entry in ENTRIES:
        env = dict(base) if entry is None else {**base, "=A:": entry}
        node_run = subprocess.run([node, "--no-warnings", "--input-type=module", "-e", NODE_CHILD, pi],
                                  env=env, capture_output=True, encoding="utf-8", check=True)
        py_run = subprocess.run([sys.executable, "-c", PY_CHILD, src],
                                env=env, capture_output=True, encoding="utf-8", check=True)
        oracle, binding = json.loads(node_run.stdout), json.loads(py_run.stdout)
        crafted = None if entry is None else list(memoryview(entry.encode("utf-16-le", "surrogatepass")).cast("H"))
        if binding["entry"] != crafted:
            raise SystemExit(f"{label}: entry not delivered to the binding as crafted: {binding['entry']}")
        # Node reads the block through UTF-8: a lone surrogate is NOT representable in its process.env, so its
        # view of the entry is recorded separately (it is the oracle's actual input).
        rows.append({"label": label, "entry": crafted, "node_entry": oracle["entry"],
                     "node_entry_equals_crafted": oracle["entry"] == crafted,
                     "node": oracle["out"], "binding": binding["out"], "match": oracle["out"] == binding["out"]})
    print(json.dumps({"node": oracle["node"], "platform": sys.platform, "rows": rows}, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:])
