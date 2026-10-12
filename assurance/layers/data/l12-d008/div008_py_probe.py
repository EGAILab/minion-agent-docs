"""L12-D008 / DIV-008 (minion-agent#215, provenance #127): the Python binding's real `LocalFileSystem.remove`
(recursive) over div008-matrix.json, with the same injection seams as CE-L12D007-02 (ce02_recovery_py_probe.py).
Python removes sequentially, so a row's `settle` order does not apply: the probe records the ACTUAL traversal
(`seq`, every intercepted call below `tree` in call order) and what the binding reports, and the comparator
(div008_compare.py) checks the rule against it: the reported failure is the first failure encountered in the
traversal, with that failure's code (DIV-008), and the remaining siblings are still removed after a failure, so what
remains equals pinned Pi's drained state (Owner decision #215 issuecomment-6118734550; spec section 19.5 rule 4 as
amended). Python has nothing in flight when remove() returns, so `at_settle`
and `after_drain` are the same snapshot and `late_calls` is empty by construction; both are emitted so Pi's and
Python's rows have one shape. Natural rows (Linux) use real host failures from a directory chmod 0555.
Every fixture write, chmod and cleanup goes through the reviewed fs-guard (CE-L12D007-01).

Usage: python div008_py_probe.py <code worktree> <scratch dir inside the project> [matrix]"""

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
sys.path.insert(0, str(HERE.parent / "l12-d007" / "fs-guard"))
code_root, scratch = sys.argv[1], sys.argv[2]
MATRIX = sys.argv[3] if len(sys.argv) > 3 else "div008-matrix.json"
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
                row["seq"].append(key)
                for plan in row["plans"]:
                    if (plan["op"], plan["rel"], plan["nth"]) == (op, rel, row["calls"][key]):
                        plan["fired"] = True
                        row["seq"].append(f"settle {key} {plan['code']}")
                        raise _error(plan["code"], os.fspath(p))
                try:
                    return real(p, *args, **kwargs)
                except OSError as exc:
                    # A NATIVE failure (not injected), recorded with its errno name so a natural row's origin is
                    # observed at the real call (CE-L12D008-01); the exception propagates unchanged.
                    row["seq"].append(f"fail {key} {errno.errorcode.get(exc.errno or 0, 'E?')}")
                    raise
        return real(p, *args, **kwargs)

    return call


os.lstat = _wrap("lstat", os.lstat)
os.stat = _wrap("stat", os.stat)
os.scandir = _wrap("readdir", os.scandir)
fs_module._node_rmdir = _wrap("rmdir", fs_module._node_rmdir)
if hasattr(fs_module, "_correct_own_attribute"):
    fs_module._correct_own_attribute = _wrap("chmod", fs_module._correct_own_attribute)
if sys.platform == "win32":
    fs_module._libuv_unlink = _wrap("unlink", fs_module._libuv_unlink)
else:
    os.unlink = _wrap("unlink", os.unlink)


def _remains(root: str) -> list[str]:
    remains: list[str] = []

    def walk(rel: str) -> None:
        p = fs_guard.assert_entry(root, rel)
        is_link = os.path.islink(p)
        is_dir = os.path.isdir(p) and not is_link
        remains.append(rel + "@" if is_link else rel + "/" if is_dir else rel)
        if is_dir:
            for name in sorted(os.listdir(p)):
                walk(f"{rel}/{name}")

    for name in sorted(os.listdir(root)):
        walk(name)
    return remains


async def run_once(spec: dict[str, Any], run: int) -> dict[str, Any]:
    global row
    root = fs_guard.make_sandbox(os.path.join(scratch, f"div008-py-{spec['id']}-{run}-{os.getpid()}"))
    ro_dirs: list[str] = []
    for entry in spec["fixture"]:
        if isinstance(entry, str):
            if entry.endswith("/"):
                os.mkdir(fs_guard.assert_inside(root, entry[:-1]))
            else:
                Path(fs_guard.assert_inside(root, entry)).write_text("x")
        else:
            ro_dirs.append(entry["ro_dir"])
    for rel in ro_dirs:
        os.chmod(fs_guard.assert_inside(root, rel), 0o555)
    row = {"root": root, "plans": [dict(q) for q in spec.get("inject", [])], "calls": {}, "seq": []}
    current = row
    result = await LocalFileSystem(root).remove("tree", recursive=True, force=False)
    row = None
    calls = dict(sorted(current["calls"].items()))
    snapshot = {"calls": calls, "remains": _remains(root)}
    for rel in ro_dirs:
        p = os.path.join(root, rel)
        if os.path.exists(p):
            os.chmod(fs_guard.assert_inside(root, rel), 0o755)
    error_path = None
    if not isinstance(result, Ok) and result.error.path:
        error_path = os.path.relpath(result.error.path, root).replace(os.sep, "/")
    out = {
        "platform": sys.platform, "id": spec["id"], "run": run,
        "result": "ok" if isinstance(result, Ok) else str(result.error.code), "path": error_path,
        "seq": current["seq"], "at_settle": snapshot, "after_drain": snapshot, "late_calls": [],
        "drained": True, "settle_incomplete": False,
        "unfired": [f"{q['op']} {q['rel']} #{q['nth']}" for q in current["plans"] if not q.get("fired")],
    }
    if not fs_guard.cleanup_sandbox(root, log=lambda m: print(m, file=sys.stderr)):
        raise SystemExit(f"cleanup refused for {root}")
    return out


async def main() -> None:
    matrix = json.loads((HERE / MATRIX).read_text(encoding="utf-8"))
    for spec in matrix["rows"]:
        platforms = spec.get("platforms")
        if platforms and sys.platform not in platforms:
            continue
        for run in range(1, spec.get("repeat", 1) + 1):
            print(json.dumps(await run_once(spec, run)), flush=True)


asyncio.run(main())
