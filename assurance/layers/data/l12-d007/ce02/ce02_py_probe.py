"""CE-L12D007-02: the Python candidate's real `LocalFileSystem.remove('tree', recursive=True)` over
ce02-matrix.json, with ONE injected native failure per row, at the calls the walk makes: `os.lstat`,
`os.stat`, `os.scandir` (readdir), the provider's rmdir (`_node_rmdir`) and unlink (Windows `_libuv_unlink`,
POSIX `os.unlink`). Every other call is real. Output: one JSON line per row, the same shape as the Pi probe.

Usage: python ce02_py_probe.py <code worktree> <scratch dir inside the project>"""

from __future__ import annotations

import asyncio
import errno
import json
import os
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "fs-guard"))
code_root, scratch = sys.argv[1], sys.argv[2]
sys.path.insert(0, str(Path(code_root) / "minion-agent-python" / "src"))

import fs_guard  # noqa: E402
from minion_agent.execution import Ok  # noqa: E402
from minion_agent.execution import LocalFileSystem  # noqa: E402
from minion_agent.execution import filesystem as fs_module  # noqa: E402

WIN32 = {"EIO": 1117, "EACCES": 1920, "EBUSY": 32, "ENOENT": 2, "EPERM": 5}
row: dict[str, Any] | None = None


def _error(code: str, path: str) -> OSError:
    if sys.platform == "win32":
        return OSError(0, f"injected {code}", path, WIN32[code])
    return OSError(getattr(errno, code), f"injected {code}", path)


def _rel(p: Any) -> str:
    assert row is not None
    return os.path.relpath(os.fspath(p), row["root"]).replace(os.sep, "/")


def _wrap(op: str, real: Any) -> Any:
    def call(p: Any, *args: Any, **kwargs: Any) -> Any:
        if row is not None and not isinstance(p, int):
            rel = _rel(p)
            if rel.startswith("tree"):
                key = f"{op} {rel}"
                row["calls"][key] = row["calls"].get(key, 0) + 1
                plan = row["plan"]
                if plan and (plan["op"], plan["rel"], plan["nth"]) == (op, rel, row["calls"][key]):
                    raise _error(plan["code"], os.fspath(p))
        return real(p, *args, **kwargs)

    return call


os.lstat = _wrap("lstat", os.lstat)
os.stat = _wrap("stat", os.stat)
os.scandir = _wrap("readdir", os.scandir)
fs_module._node_rmdir = _wrap("rmdir", fs_module._node_rmdir)
if sys.platform == "win32":
    fs_module._libuv_unlink = _wrap("unlink", fs_module._libuv_unlink)
else:
    os.unlink = _wrap("unlink", os.unlink)


def _remaining(root: str) -> list[str]:
    out: list[str] = []

    def walk(rel: str) -> None:
        p = fs_guard.assert_inside(root, rel)
        is_dir = os.path.isdir(p) and not os.path.islink(p)
        out.append(rel + "/" if is_dir else rel)
        if is_dir:
            for name in sorted(os.listdir(p)):
                walk(f"{rel}/{name}")

    if os.path.lexists(os.path.join(root, "tree")):
        walk("tree")
    return out


async def main() -> None:
    global row
    matrix = json.loads((HERE / "ce02-matrix.json").read_text(encoding="utf-8"))
    for spec in matrix["rows"]:
        root = fs_guard.make_sandbox(os.path.join(scratch, f"ce02-py-{spec['id']}-{os.getpid()}"))
        for entry in spec["fixture"]:
            if entry.endswith("/"):
                os.mkdir(fs_guard.assert_inside(root, entry[:-1]))
            else:
                Path(fs_guard.assert_inside(root, entry)).write_text("x")
        row = {"root": root, "plan": spec["inject"], "calls": {}}
        result = await LocalFileSystem(root).remove("tree", recursive=True)
        calls = row["calls"]
        row = None
        path = None
        if not isinstance(result, Ok) and result.error.path:
            path = os.path.relpath(result.error.path, root).replace(os.sep, "/")
        print(json.dumps({
            "platform": sys.platform, "id": spec["id"],
            "result": "ok" if isinstance(result, Ok) else str(result.error.code), "path": path,
            "calls": dict(sorted(calls.items())), "remains": _remaining(root),
        }), flush=True)
        if not fs_guard.cleanup_sandbox(root):
            sys.exit(1)


asyncio.run(main())
