"""L12-D007: the same Windows condition x operation matrix as pi-error-probe.mjs, through Python's
real LocalFileSystem (origin/main). Every target is containment-checked before every operation.

    python py-error-probe.py <out.json>
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "fs-guard"))
from fs_guard import PROJECT_ROOT, assert_inside, make_sandbox  # noqa: E402

from minion_agent.execution.filesystem import LocalFileSystem  # noqa: E402
from minion_agent.execution.result import Ok  # noqa: E402


def write(p: str, data: str = "x") -> None:
    with open(p, "w", encoding="utf-8") as f:
        f.write(data)


def holder(script: str) -> subprocess.Popen[bytes]:
    proc = subprocess.Popen(["powershell", "-NoProfile", "-Command", script], stdout=subprocess.PIPE)
    assert proc.stdout is not None
    proc.stdout.readline()  # "ready"
    return proc


def setup(condition: str, cwd: str) -> tuple[str, subprocess.Popen[bytes] | None]:
    j = lambda *p: os.path.join(cwd, *p)  # noqa: E731
    if condition == "missing":
        return "missing", None
    if condition == "file":
        write(j("f"))
        return "f", None
    if condition == "directory-empty":
        os.mkdir(j("d"))
        return "d", None
    if condition == "directory-nonempty":
        os.mkdir(j("d"))
        write(j("d", "c"))
        return "d", None
    if condition == "non-directory-component":
        write(j("f"))
        return "f/x", None
    if condition == "symlink-loop":
        os.symlink(j("b"), j("a"))
        os.symlink(j("a"), j("b"))
        return "a", None
    if condition == "name-too-long":
        return "n" * 300, None
    if condition == "invalid-name":
        return "x<y", None
    if condition == "ntfs-stream-syntax":
        write(j("f"))
        return "./f:stream:bad", None
    if condition == "sharing-violation":
        write(j("f"), "0123456789" * 10)
        return "f", holder(f"$s=[IO.File]::Open('{j('f')}','Open','ReadWrite','None'); Write-Output ready; Start-Sleep 120")
    if condition == "lock-violation":
        write(j("f"), "0123456789" * 10)
        return "f", holder(
            f"$s=[IO.File]::Open('{j('f')}','Open','ReadWrite','ReadWrite'); $s.Lock(0,64); Write-Output ready; Start-Sleep 120"
        )
    raise ValueError(condition)


CONDITIONS = ["missing", "file", "directory-empty", "directory-nonempty", "non-directory-component", "symlink-loop",
              "name-too-long", "invalid-name", "ntfs-stream-syntax", "sharing-violation", "lock-violation"]
if sys.platform != "win32":  # the same POSIX subset as pi-error-probe.mjs
    CONDITIONS = CONDITIONS[:7]


def ops(fs: LocalFileSystem, t: str, cwd: str) -> dict[str, object]:
    def onto() -> object:
        write(os.path.join(cwd, "src"), "s")
        return fs.rename_file("src", t)

    return {
        "readTextFile": lambda: fs.read_text_file(t),
        "readTextLines": lambda: fs.read_text_lines(t),
        "readBinaryFile": lambda: fs.read_binary_file(t),
        "writeFile": lambda: fs.write_file(t, "w"),
        "appendFile": lambda: fs.append_file(t, "w"),
        "renameFile-source": lambda: fs.rename_file(t, "renamed"),
        "renameFile-destination-onto": onto,
        "fileInfo": lambda: fs.file_info(t),
        "exists": lambda: fs.exists(t),
        "listDir": lambda: fs.list_dir(t),
        "canonicalPath": lambda: fs.canonical_path(t),
        "createDir-recursive": lambda: fs.create_dir(t, recursive=True),
        "createDir-nonrecursive": lambda: fs.create_dir(t, recursive=False),
        "remove": lambda: fs.remove(t),
        "remove-recursive": lambda: fs.remove(t, recursive=True),
        "remove-force": lambda: fs.remove(t, force=True),
        "list_dir_raw(readdir)": lambda: fs.list_dir_raw(t),
        "probe_dir_entry(lstat)": lambda: fs.probe_dir_entry(t),
        "check_readable(access R)": lambda: fs.check_readable(t),
        "check_read_write(access RW)": lambda: fs.check_read_write(t),
    }


async def main(out: str) -> None:
    root = make_sandbox(os.path.join(PROJECT_ROOT, ".tmp", "claude-scratch", "l12d007", f"py-sandbox-{int(time.time())}"))
    results = []
    n = 0
    for condition in CONDITIONS:
        for op in ops(LocalFileSystem(root), "x", root):
            cwd = os.path.join(root, str(n))
            n += 1
            os.mkdir(cwd)
            target, hold = setup(condition, cwd)
            try:
                for t in (target, "renamed", "src"):
                    assert_inside(cwd, t)
                fs = LocalFileSystem(cwd)
                try:
                    r = await ops(fs, target, cwd)[op]()  # type: ignore[operator]
                    observed = {"ok": True} if isinstance(r, Ok) else {"error": str(r.error.code)}
                except Exception as e:  # noqa: BLE001
                    observed = {"threw": f"{type(e).__name__}: {e}"[:200]}
            except RuntimeError as e:
                observed = {"setup_failed": str(e)}
            finally:
                if hold:
                    hold.kill()
                    hold.wait()
            results.append({"condition": condition, "op": op, "observed": observed})
    assert_inside(os.path.dirname(root), root)
    shutil.rmtree(root, ignore_errors=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"platform": sys.platform, "python": sys.version.split()[0], "results": results}, f, indent=1)
    print(f"l12-d007 python probe: {len(results)} rows")


asyncio.run(main(sys.argv[1]))
