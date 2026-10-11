"""CE-L12D007-02 revision 2: the Python candidate's real `LocalFileSystem.remove` over
ce02-recovery-matrix.json (Windows EPERM recovery). As ce02_py_probe.py, but each row may inject several
failures, fixtures may hold read-only attributes and file symlinks, and the output lists every entry left
read-only. The matrix's `chmod` is the binding's own-attribute correction seam (`_correct_own_attribute`,
never a link-following chmod); a candidate without that seam leaves those injections unfired, which the
comparator refuses to credit. The matrix file is the optional third argument (default: the recovery matrix).

Usage: python ce02_recovery_py_probe.py <code worktree> <scratch dir inside the project>"""

from __future__ import annotations

import asyncio
import errno
import json
import os
import stat
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "fs-guard"))
code_root, scratch = sys.argv[1], sys.argv[2]
MATRIX = sys.argv[3] if len(sys.argv) > 3 else "ce02-recovery-matrix.json"
sys.path.insert(0, str(Path(code_root) / "minion-agent-python" / "src"))

import fs_guard  # noqa: E402
from minion_agent.execution import LocalFileSystem, Ok  # noqa: E402
from minion_agent.execution import filesystem as fs_module  # noqa: E402

WIN32 = {"EIO": 1117, "EACCES": 1920, "EBUSY": 32, "ENOENT": 2, "EPERM": 5}
row: dict[str, Any] | None = None


def _error(code: str, path: str) -> OSError:
    if sys.platform == "win32":
        return OSError(0, f"injected {code}", path, WIN32[code])
    return OSError(getattr(errno, code), f"injected {code}", path)


def _wrap(op: str, real: Any) -> Any:
    def call(p: Any, *args: Any, **kwargs: Any) -> Any:
        if row is not None and not isinstance(p, int):
            rel = os.path.relpath(os.fspath(p), row["root"]).replace(os.sep, "/")
            if rel == "tree" or rel.startswith("tree/"):
                key = f"{op} {rel}"
                row["calls"][key] = row["calls"].get(key, 0) + 1
                for plan in row["plans"]:
                    if (plan["op"], plan["rel"], plan["nth"]) == (op, rel, row["calls"][key]):
                        plan["fired"] = True
                        raise _error(plan["code"], os.fspath(p))
        return real(p, *args, **kwargs)

    return call


os.lstat = _wrap("lstat", os.lstat)
os.stat = _wrap("stat", os.stat)
os.scandir = _wrap("readdir", os.scandir)
fs_module._node_rmdir = _wrap("rmdir", fs_module._node_rmdir)
if hasattr(fs_module, "_correct_own_attribute"):
    # The binding's own-attribute correction (fixWinEPERM's `chmod`, done without following links): the
    # matrix's `chmod` injections fire here (CE-L12D007-02 checkpoint review 2 evidence reminder).
    fs_module._correct_own_attribute = _wrap("chmod", fs_module._correct_own_attribute)
if sys.platform == "win32":
    fs_module._libuv_unlink = _wrap("unlink", fs_module._libuv_unlink)
else:
    os.unlink = _wrap("unlink", os.unlink)


def _state(root: str) -> dict[str, list[str]]:
    remains: list[str] = []
    readonly: list[str] = []

    def walk(rel: str) -> None:
        p = fs_guard.assert_entry(root, rel)
        is_link = os.path.islink(p)
        is_dir = os.path.isdir(p) and not is_link
        remains.append(rel + "@" if is_link else rel + "/" if is_dir else rel)
        if not is_link and not os.lstat(p).st_mode & stat.S_IWRITE:
            readonly.append(rel)
        if is_dir:
            for name in sorted(os.listdir(p)):
                walk(f"{rel}/{name}")

    for name in sorted(os.listdir(root)):
        walk(name)
    return {"remains": remains, "readonly": readonly}


async def main() -> None:
    global row
    matrix = json.loads((HERE / MATRIX).read_text(encoding="utf-8"))
    for spec in matrix["rows"]:
        # A junction is a Windows-only fixture: its rows do not apply elsewhere.
        if sys.platform != "win32" and any(isinstance(e, dict) and "junction" in e for e in spec["fixture"]):
            continue
        root = fs_guard.make_sandbox(os.path.join(scratch, f"ce02r-py-{spec['id']}-{os.getpid()}"))
        late: list[str] = []
        for entry in spec["fixture"]:
            if isinstance(entry, str):
                if entry.endswith("/"):
                    os.mkdir(fs_guard.assert_inside(root, entry[:-1]))
                else:
                    Path(fs_guard.assert_inside(root, entry)).write_text("x")
            elif "link" in entry:
                os.symlink(fs_guard.assert_inside(root, entry["to"]), fs_guard.assert_entry(root, entry["link"]))
            elif "dirlink" in entry:
                os.symlink(
                    fs_guard.assert_inside(root, entry["to"]),
                    fs_guard.assert_entry(root, entry["dirlink"]),
                    target_is_directory=True,
                )
            elif "junction" in entry:
                import _winapi  # Windows only; junction rows are skipped elsewhere

                _winapi.CreateJunction(
                    fs_guard.assert_inside(root, entry["to"]), fs_guard.assert_entry(root, entry["junction"])
                )
            else:
                late.append(entry["ro"])
        for rel in late:
            os.chmod(fs_guard.assert_inside(root, rel), stat.S_IREAD)
        remove = spec.get("remove", {"path": "tree", "recursive": True})
        plans = [dict(q) for q in spec["inject"]]
        row = {"root": root, "plans": plans, "calls": {}}
        result = await LocalFileSystem(root).remove(
            remove["path"], recursive=remove["recursive"], force=remove.get("force", False)
        )
        calls = row["calls"]
        row = None
        path = None
        if not isinstance(result, Ok) and result.error.path:
            path = os.path.relpath(result.error.path, root).replace(os.sep, "/")
        print(json.dumps({
            "platform": sys.platform, "id": spec["id"],
            "result": "ok" if isinstance(result, Ok) else str(result.error.code), "path": path,
            "calls": dict(sorted(calls.items())), **_state(root),
            "unfired": [f"{q['op']} {q['rel']} #{q['nth']}" for q in plans if not q.get("fired")],
        }), flush=True)
        for rel in late:
            if os.path.lexists(os.path.join(root, rel)):
                os.chmod(fs_guard.assert_inside(root, rel), stat.S_IREAD | stat.S_IWRITE)
        if not fs_guard.cleanup_sandbox(root):
            sys.exit(1)


asyncio.run(main())
