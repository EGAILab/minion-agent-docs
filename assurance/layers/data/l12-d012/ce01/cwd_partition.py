"""CE-L12D012-01 characterization, revision 1 (checkpoint review 1, #229 issuecomment-6178272131): the OTHER
selected-value source of Node's drive-relative branch, `process.env['=D:'] || process.cwd()` -- the native
PROCESS CWD, read by Node through libuv `uv_cwd` (GetCurrentDirectoryW -> uv__copy_utf16_to_utf8) and V8
`String::NewFromUtf8`, versus the binding's `os.getcwd()`.

FIXTURE (the only filesystem changes; every one proven before it happens):
  - a NEW sandbox directory  <project root>\\.tmp\\claude-scratch\\i229\\<run name>  (one plain component);
  - inside it, one EMPTY directory per row in CWD_DIRS (names: ASCII; a valid surrogate pair; lone high;
    lone low; a lone high followed by ASCII), created with os.mkdir.
  Before EACH mkdir: the target is lexically inside the sandbox (no '..', no drive-relative or UNC form, no
  absolute override), it does not exist, no existing ancestor up to the project root is a symlink or reparse
  point, and the parent's real path is inside the project root. After each mkdir the real path of the new
  directory is re-proven inside the sandbox. Nothing is ever deleted, renamed or written inside these
  directories; they are used ONLY as the children's cwd. A failed proof aborts the whole run (exit 3).

ROWS: for each directory D (on the sandbox's drive, letter d): the input `d:leaf` with provider cwd C:\\x, and
the inherited `=D:` entry absent / empty / a matching-drive non-empty value (`D:\\deep`); plus the different-
drive control input `a:leaf` (entry absent) whose fallback is replaced by the root. The sandbox drive must
not be C: (the provider cwd's drive) or A: -- otherwise the run REFUSES.

CHILDREN, per row, with IDENTICAL environment blocks (the parent's ordinary variables, no `=`-prefixed entry,
plus exactly the row's `=D:` when present) and the SAME cwd D:
  - Node v22.15.1 running pinned Pi resolvePath (sliced unmodified): reports its process.cwd() and the result,
    as UTF-16 units -- the oracle;
  - Python running the real LocalFileSystem.absolute_path of the candidate: reports os.getcwd() and the result.
The parent asserts the binding child's cwd equals the crafted directory exactly. stdout only.

    python cwd_partition.py <node.exe> <pinned Pi checkout> <candidate src> <run name>
"""

from __future__ import annotations

import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path

PROJECT = Path(os.environ.get("MINION_PROJECT_ROOT", "E:/AI/Projects/OpenMinds/Minions/Minion-Agent")).resolve()
SCRATCH = PROJECT / ".tmp" / "claude-scratch" / "i229"
CWD_DIRS = [
    ("ascii", "plain"),
    ("pair", "pair-\U0001f600"),
    ("lone-high", "lone-\ud83d"),
    ("lone-low", "lone-\ude00"),
    ("lone-high-then-ascii", "x\ud83dy"),
]

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
const input = process.argv[2];
console.log(JSON.stringify({ node: process.version, cwd: units(process.cwd()), out: units(resolvePath("C:\\x", input)) }));
"""

PY_CHILD = r"""
import asyncio, json, os, sys
sys.path.insert(0, sys.argv[1])
from minion_agent.execution.filesystem import LocalFileSystem
def units(s):
    return list(memoryview(s.encode("utf-16-le", "surrogatepass")).cast("H"))
out = asyncio.run(LocalFileSystem("C:\\x").absolute_path(sys.argv[2])).value
print(json.dumps({"cwd": units(os.getcwd()), "out": units(out)}))
"""


def refuse(why: str) -> None:
    print(f"CONTAINMENT REFUSED: {why}", file=sys.stderr)
    raise SystemExit(3)


def units(text: str) -> list[int]:
    return list(memoryview(text.encode("utf-16-le", "surrogatepass")).cast("H"))


def proven_new_dir(parent: Path, name: str, boundary: Path) -> Path:
    """mkdir parent/name, only after every proof holds; returns the new directory."""
    if not name or name in (".", "..") or any(c in name for c in "\\/:") or re.match(r"^[A-Za-z]:", name):
        refuse(f"name is not one plain component: {name!r}")
    target = parent / name
    lexical = Path(os.path.abspath(target))
    if ".." in lexical.parts or not lexical.is_relative_to(boundary) or lexical == boundary:
        refuse(f"not lexically inside {boundary}: {lexical!r}")
    if os.path.lexists(lexical):
        refuse(f"already exists: {lexical!r}")
    entry = lexical.parent
    while True:
        meta = entry.lstat()
        if stat.S_ISLNK(meta.st_mode) or getattr(meta, "st_file_attributes", 0) & 0x400:
            refuse(f"link or reparse point at {entry!r}")
        if entry == PROJECT:
            break
        if not entry.is_relative_to(PROJECT):
            refuse(f"ancestor outside the project root: {entry!r}")
        entry = entry.parent
    if not Path(os.path.realpath(lexical.parent)).is_relative_to(PROJECT):
        refuse(f"parent really outside the project root: {lexical.parent!r}")
    os.mkdir(lexical)
    if not Path(os.path.realpath(lexical)).is_relative_to(boundary):
        refuse(f"created directory really outside {boundary}: {lexical!r}")
    return lexical


def main(node: str, pi: str, src: str, run: str) -> None:
    if sys.platform != "win32":
        refuse("win32 only")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,40}", run):
        refuse(f"run name must be one plain component: {run!r}")
    sandbox = proven_new_dir(SCRATCH, run, SCRATCH)
    drive = str(sandbox)[0].upper()
    if drive in ("A", "C"):
        refuse(f"the sandbox drive {drive}: must not be the provider cwd's (C:) or the control drive (A:)")
    base = {k: v for k, v in os.environ.items() if not k.startswith("=")}
    rows = []
    for label, name in CWD_DIRS:
        cwd = proven_new_dir(sandbox, name, sandbox)
        cases = [(f"{drive.lower()}:leaf", None), (f"{drive.lower()}:leaf", ""), (f"{drive.lower()}:leaf", f"{drive}:\\deep"),
                 ("a:leaf", None)]
        for input_path, entry in cases:
            env = dict(base) if entry is None else {**base, f"={drive}:": entry}
            oracle = json.loads(subprocess.run(
                [node, "--no-warnings", "--input-type=module", "-e", NODE_CHILD, pi, input_path],
                env=env, cwd=cwd, capture_output=True, encoding="utf-8", check=True).stdout)
            binding = json.loads(subprocess.run(
                [sys.executable, "-c", PY_CHILD, src, input_path],
                env=env, cwd=cwd, capture_output=True, encoding="utf-8", check=True).stdout)
            if binding["cwd"] != units(str(cwd)):
                refuse(f"{label}: the binding child's cwd is not the crafted directory")
            rows.append({"cwd_label": label, "input": input_path,
                         "entry": None if entry is None else units(entry),
                         "binding_cwd": binding["cwd"], "node_cwd": oracle["cwd"],
                         "node_cwd_equals_native": oracle["cwd"] == binding["cwd"],
                         "node": oracle["out"], "binding": binding["out"], "match": oracle["out"] == binding["out"]})
    print(json.dumps({"node": oracle["node"], "sandbox": units(str(sandbox)), "rows": rows}, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:])
