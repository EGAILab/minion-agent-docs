"""CE-L12D012-01 characterization, revision 1 (checkpoint review 1, #229 issuecomment-6178272131; fixture-plan
safety check issuecomment-6178360188): the OTHER selected-value source of Node's drive-relative branch,
`process.env['=D:'] || process.cwd()` -- the native PROCESS CWD, read by Node through libuv `uv_cwd`
(GetCurrentDirectoryW -> uv__copy_utf16_to_utf8) and V8 `String::NewFromUtf8` -- versus the binding's os.getcwd().

AUTHORITY: the FIXED project root `E:\\AI\\Projects\\OpenMinds\\Minions\\Minion-Agent`. MINION_PROJECT_ROOT, when set,
must name exactly that root (refused otherwise; it never becomes the authority). Before ANY creation the root's
whole existing ancestry, up to the drive root, is inspected without following links (lstat); a link, a reparse
point or an inspection failure refuses. The root's real path must then equal the root itself.

PRECONDITIONS, all checked BEFORE the first mkdir: the authority above; the sandbox drive (the root's) is not C:
(the provider cwd's drive) and not A: (the control drive); the run name is one plain component; the sandbox does
not exist; `node --version` is v22.15.1; the pinned Pi source `packages/agent/src/harness/env/nodejs.ts` in the
checkout has the Git blob of commit b7bb00b9.

FIXTURE (the only filesystem changes; every one proven immediately before it happens):
  - a NEW sandbox  <root>\\.tmp\\claude-scratch\\i229\\<run name>;
  - inside it, one EMPTY directory per row of CWD_DIRS (ASCII; a valid surrogate pair; lone high; lone low;
    lone high then ASCII), created with os.mkdir.
  Each mkdir target: one plain component; lexically inside its parent's sandbox boundary; not existing; every
  existing ancestor up to the drive root a plain directory (no link, no reparse point, inspection succeeds); the
  parent's real path inside the root. After each mkdir the new directory's real path is re-proven inside the
  sandbox. Nothing is ever deleted, renamed or written inside these directories; they are only the children's
  cwd. Any failed proof aborts the whole run (exit 3) before further writes. PYTHONDONTWRITEBYTECODE=1 is set for
  this process and both children (no implicit bytecode-cache writes).

ROWS, per directory D (on the sandbox's drive, letter d): input `d:leaf` with provider cwd C:\\x and the inherited
`=D:` entry absent / empty / matching-drive `D:\\deep`; plus the different-drive control `a:leaf` (entry absent).
CHILDREN, per row, with IDENTICAL environment blocks (ordinary variables, no `=`-entry, plus exactly the row's
`=D:` when present) and the SAME cwd D: a Node child (pinned Pi resolvePath, the oracle) reporting process.cwd(),
its process.env view of `=D:` and the result; a Python child (the real LocalFileSystem.absolute_path) reporting
os.getcwd(), its native GetEnvironmentVariableW read of `=D:` and the result -- all as UTF-16 units. The parent
requires the binding's cwd and native entry to equal the crafted ones exactly. stdout only.

    python cwd_partition.py <node.exe> <pinned Pi checkout> <candidate src> <run name>
    python cwd_partition.py --self-test     (intercepted: no filesystem mutation at all)
"""

from __future__ import annotations

import json
import os
import re
import stat
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import PureWindowsPath
from types import SimpleNamespace

ROOT = PureWindowsPath(r"E:\AI\Projects\OpenMinds\Minions\Minion-Agent")
SCRATCH = ROOT / ".tmp" / "claude-scratch" / "i229"
PI_COMMIT = "b7bb00b936dbe21b8e160b3e89efdec361846699"
PI_FILE = "packages/agent/src/harness/env/nodejs.ts"
REPARSE = 0x400
CWD_DIRS = [
    ("ascii", "plain"),
    ("pair", "pair-\U0001f600"),
    ("lone-high", "lone-\ud83d"),
    ("lone-low", "lone-\ude00"),
    ("lone-high-then-ascii", "x\ud83dy"),
]
CHILD_ENV = {"PYTHONDONTWRITEBYTECODE": "1"}

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
const [, , input, letter] = process.argv;
console.log(JSON.stringify({ cwd: units(process.cwd()), entry: units(process.env[`=${letter}:`]),
  out: units(resolvePath("C:\\x", input)) }));
"""

PY_CHILD = r"""
import asyncio, ctypes, json, os, sys
from ctypes import wintypes
sys.path.insert(0, sys.argv[1])
from minion_agent.execution.filesystem import LocalFileSystem
k32 = ctypes.WinDLL("kernel32", use_last_error=True)
k32.GetEnvironmentVariableW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
buf = ctypes.create_unicode_buffer(4096)
n = k32.GetEnvironmentVariableW("=" + sys.argv[3] + ":", buf, 4096)
entry = ctypes.wstring_at(ctypes.addressof(buf), n) if n else (None if ctypes.get_last_error() == 203 else "")
def units(s):
    return None if s is None else list(memoryview(s.encode("utf-16-le", "surrogatepass")).cast("H"))
out = asyncio.run(LocalFileSystem("C:\\x").absolute_path(sys.argv[2])).value
print(json.dumps({"cwd": units(os.getcwd()), "entry": units(entry), "out": units(out)}))
"""


class Refused(Exception):
    pass


@dataclass
class Fs:
    """Every filesystem inspection and the one mutation (mkdir), injectable so --self-test intercepts them."""

    lstat: Callable[[str], os.stat_result] = os.lstat
    lexists: Callable[[str], bool] = os.path.lexists
    realpath: Callable[[str], str] = os.path.realpath
    mkdir: Callable[[str], None] = os.mkdir
    made: list[str] = field(default_factory=list)


def _norm(path: str | PureWindowsPath) -> str:
    return os.path.normcase(os.path.normpath(str(path)))


def _inside(path: str | PureWindowsPath, boundary: PureWindowsPath, *, strict: bool = True) -> bool:
    p, b = _norm(path), _norm(boundary)
    return p.startswith(b + "\\") if strict else (p == b or p.startswith(b + "\\"))


def prove_authority(fs: Fs) -> None:
    """The fixed root: no override, whole existing ancestry plain (no-follow), real path is itself."""
    override = os.environ.get("MINION_PROJECT_ROOT")
    if override is not None and _norm(override.replace("/", "\\")) != _norm(ROOT):
        raise Refused(f"MINION_PROJECT_ROOT names another directory: {override!r}")
    node: PureWindowsPath = ROOT
    while True:
        try:
            meta = fs.lstat(str(node))
        except OSError as error:
            raise Refused(f"cannot inspect {node}: {error}") from error
        if stat.S_ISLNK(meta.st_mode) or (getattr(meta, "st_file_attributes", 0) or 0) & REPARSE:
            raise Refused(f"link or reparse point at {node}")
        if not stat.S_ISDIR(meta.st_mode):
            raise Refused(f"not a directory: {node}")
        if node.parent == node:
            break
        node = node.parent
    if _norm(fs.realpath(str(ROOT))) != _norm(ROOT):
        raise Refused(f"the root's real path is not itself: {fs.realpath(str(ROOT))!r}")


def proven_mkdir(fs: Fs, parent: PureWindowsPath, name: str, boundary: PureWindowsPath) -> PureWindowsPath:
    if not name or name in (".", "..") or any(c in name for c in "\\/:") or re.match(r"^[A-Za-z]:", name):
        raise Refused(f"not one plain component: {name!r}")
    target = parent / name
    if ".." in target.parts or not _inside(target, boundary):
        raise Refused(f"not lexically inside {boundary}: {target!r}")
    if fs.lexists(str(target)):
        raise Refused(f"already exists: {target!r}")
    node = target.parent
    while True:
        try:
            meta = fs.lstat(str(node))
        except OSError as error:
            raise Refused(f"cannot inspect {node}: {error}") from error
        if stat.S_ISLNK(meta.st_mode) or (getattr(meta, "st_file_attributes", 0) or 0) & REPARSE:
            raise Refused(f"link or reparse point at {node}")
        if node.parent == node:
            break
        node = node.parent
    if not _inside(fs.realpath(str(target.parent)), ROOT, strict=False):
        raise Refused(f"parent really outside the root: {target.parent!r}")
    fs.mkdir(str(target))
    fs.made.append(str(target))
    if not _inside(fs.realpath(str(target)), boundary):
        raise Refused(f"created directory really outside {boundary}: {target!r}")
    return target


def preconditions(fs: Fs, node: str, pi: str, run: str) -> PureWindowsPath:
    """Everything checked before the first mkdir; returns the (not yet created) sandbox path."""
    if sys.platform != "win32":
        raise Refused("win32 only")
    prove_authority(fs)
    if ROOT.drive.upper() in ("A:", "C:"):
        raise Refused(f"the sandbox drive {ROOT.drive} must not be C: or A:")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,40}", run):
        raise Refused(f"run name must be one plain component: {run!r}")
    sandbox = SCRATCH / run
    if fs.lexists(str(sandbox)):
        raise Refused(f"sandbox already exists: {sandbox}")
    version = subprocess.run([node, "--version"], capture_output=True, text=True, check=True).stdout.strip()
    if version != "v22.15.1":
        raise Refused(f"node is {version}, not v22.15.1")
    pinned = subprocess.run(["git", "-C", pi, "rev-parse", f"{PI_COMMIT}:{PI_FILE}"],
                            capture_output=True, text=True, check=True).stdout.strip()
    actual = subprocess.run(["git", "-C", pi, "hash-object", PI_FILE],
                            capture_output=True, text=True, check=True).stdout.strip()
    if pinned != actual:
        raise Refused(f"{PI_FILE} is not the pinned blob ({actual} != {pinned})")
    return sandbox


def units(text: str | None) -> list[int] | None:
    return None if text is None else list(memoryview(text.encode("utf-16-le", "surrogatepass")).cast("H"))


def characterize(node: str, pi: str, src: str, run: str) -> None:
    fs = Fs()
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    sandbox = preconditions(fs, node, pi, run)
    proven_mkdir(fs, SCRATCH, run, SCRATCH)
    letter = ROOT.drive[0].upper()
    base = {k: v for k, v in os.environ.items() if not k.startswith("=")}
    base.update(CHILD_ENV)
    rows = []
    for label, name in CWD_DIRS:
        cwd = str(proven_mkdir(fs, sandbox, name, sandbox))
        for input_path, entry in [(f"{letter.lower()}:leaf", None), (f"{letter.lower()}:leaf", ""),
                                  (f"{letter.lower()}:leaf", f"{letter}:\\deep"), ("a:leaf", None)]:
            env = dict(base) if entry is None else {**base, f"={letter}:": entry}
            oracle = json.loads(subprocess.run(
                [node, "--no-warnings", "--input-type=module", "-e", NODE_CHILD, pi, input_path, letter],
                env=env, cwd=cwd, capture_output=True, encoding="utf-8", check=True).stdout)
            binding = json.loads(subprocess.run(
                [sys.executable, "-c", PY_CHILD, src, input_path, letter],
                env=env, cwd=cwd, capture_output=True, encoding="utf-8", check=True).stdout)
            if binding["cwd"] != units(cwd):
                raise Refused(f"{label}: the binding child's cwd is not the crafted directory")
            if binding["entry"] != units(entry):
                raise Refused(f"{label}: the binding child's =D: entry is not the crafted one")
            rows.append({"cwd_label": label, "input": input_path, "entry": units(entry),
                         "binding_cwd": binding["cwd"], "node_cwd": oracle["cwd"],
                         "node_cwd_equals_native": oracle["cwd"] == binding["cwd"],
                         "node_entry": oracle["entry"], "node": oracle["out"], "binding": binding["out"],
                         "match": oracle["out"] == binding["out"]})
    print(json.dumps({"node": "v22.15.1", "pi_blob_verified": True, "sandbox": units(str(sandbox)),
                      "made": len(fs.made), "rows": rows}, indent=1))


def self_test() -> int:
    """Intercepted proofs: NO filesystem mutation (mkdir is a recorder); inspections are scripted."""
    failures = 0

    def check(ok: bool, what: str) -> None:
        nonlocal failures
        failures += not ok
        print(f"{'PASS' if ok else 'FAIL'} {what}")

    def stat_of(mode: int, attrs: int = 0) -> os.stat_result:
        return SimpleNamespace(st_mode=mode, st_file_attributes=attrs)  # type: ignore[return-value]

    plain = stat_of(stat.S_IFDIR)

    def fake(*, reparse_at: str | None = None, fail_at: str | None = None, real: Callable[[str], str] | None = None) -> Fs:
        def lstat(path: str) -> os.stat_result:
            if fail_at and _norm(path) == _norm(fail_at):
                raise PermissionError(13, "denied", path)
            if reparse_at and _norm(path) == _norm(reparse_at):
                return stat_of(stat.S_IFDIR, REPARSE)
            return plain
        return Fs(lstat=lstat, lexists=lambda p: False, realpath=real or (lambda p: p), mkdir=lambda p: None)

    def refused(action: Callable[[], object]) -> bool:
        try:
            action()
        except Refused:
            return True
        return False

    saved = os.environ.get("MINION_PROJECT_ROOT")
    try:
        os.environ["MINION_PROJECT_ROOT"] = r"E:\AI\Projects\OpenMinds\Elsewhere"
        f = fake()
        check(refused(lambda: prove_authority(f)) and not f.made, "a foreign MINION_PROJECT_ROOT refuses")
        os.environ["MINION_PROJECT_ROOT"] = str(ROOT)
        check(not refused(lambda: prove_authority(fake())), "MINION_PROJECT_ROOT naming the fixed root is accepted")
    finally:
        if saved is None:
            os.environ.pop("MINION_PROJECT_ROOT", None)
        else:
            os.environ["MINION_PROJECT_ROOT"] = saved
    for at in (str(ROOT), str(ROOT.parent), "E:\\"):
        f = fake(reparse_at=at)
        check(refused(lambda: prove_authority(f)), f"a reparse point at {at} refuses")
        f = fake(fail_at=at)
        check(refused(lambda: prove_authority(f)), f"an inspection failure at {at} refuses")
    f = fake(real=lambda p: r"E:\Other\Minion-Agent")
    check(refused(lambda: prove_authority(f)), "a root whose real path is elsewhere refuses")
    f = fake()
    target = proven_mkdir(f, SCRATCH, "selftest", SCRATCH)
    check(f.made == [str(target)], "a contained positive reaches mkdir (intercepted)")
    f = fake()
    check(refused(lambda: proven_mkdir(f, SCRATCH, "..", SCRATCH)) and not f.made, "'..' refuses before mkdir")
    check(refused(lambda: proven_mkdir(f, SCRATCH, "c:x", SCRATCH)) and not f.made, "a drive-relative name refuses")
    check(refused(lambda: proven_mkdir(f, SCRATCH, "a\\b", SCRATCH)) and not f.made, "a separator refuses")
    f = fake(reparse_at=str(SCRATCH))
    check(refused(lambda: proven_mkdir(f, SCRATCH, "x", SCRATCH)) and not f.made, "a reparse parent refuses before mkdir")
    f = fake(real=lambda p: r"E:\Other\x" if p.endswith("x\ud83dy") else p)
    check(refused(lambda: proven_mkdir(f, SCRATCH / "s", "x\ud83dy", SCRATCH / "s")),
          "a created directory whose real path escapes refuses")
    f = Fs(lstat=lambda p: plain, lexists=lambda p: True, realpath=lambda p: p, mkdir=lambda p: None)
    check(refused(lambda: proven_mkdir(f, SCRATCH, "x", SCRATCH)) and not f.made, "an existing target refuses")
    print("SELF-TEST " + ("FAILED" if failures else "PASSED"))
    return 1 if failures else 0


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        raise SystemExit(self_test())
    try:
        characterize(*sys.argv[1:])
    except Refused as error:
        print(f"CONTAINMENT REFUSED: {error}", file=sys.stderr)
        raise SystemExit(3) from None
