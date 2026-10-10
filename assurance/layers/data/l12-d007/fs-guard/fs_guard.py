"""Filesystem containment guard for Python probes and scripts (Owner rule, 2026-10-10).

Every destructive or writing operation on a computed path must first pass
assert_inside(sandbox, target); every output file must pass assert_output(path). A sandbox must
lie strictly inside the project root, both lexically and through every link. Mirrors fs-guard.mjs.
"""

from __future__ import annotations

import os
from pathlib import Path

# FS_GUARD_ROOT is only for inside a container (a private tmpfs root such as /tmp/guard-root).
PROJECT_ROOT = os.path.abspath(os.environ.get("FS_GUARD_ROOT", "E:/AI/Projects/OpenMinds/Minions/Minion-Agent"))
# FS_GUARD_OUTPUT optionally names one more directory outputs may be written to (a container's /out).
_OUTPUT_ROOT = os.path.abspath(os.environ["FS_GUARD_OUTPUT"]) if os.environ.get("FS_GUARD_OUTPUT") else None
_MAX_HOPS = 40


def _within(parent: str, child: str) -> bool:
    parent, child = os.path.normcase(os.path.abspath(parent)), os.path.normcase(child)
    try:
        return os.path.commonpath([parent, child]) == parent
    except ValueError:  # different drives
        return False


def _concat(base: str, *parts: str) -> str:
    # Never os.path.join: it treats a component like "f:x" as drive F: and drops the base.
    return os.sep.join([base.rstrip("\\/"), *parts]) if parts else base


def _walk(target: str, boundary: str, what: str) -> str:
    """Follow `target` component by component; every link met (existing, dangling or looping) has
    its text resolved and that hop checked against `boundary`, as written or as its real path."""
    bounds = [os.path.abspath(boundary), os.path.realpath(boundary)]
    pending = os.path.abspath(target)
    for _ in range(_MAX_HOPS + 1):
        if not any(_within(b, pending) for b in bounds):
            raise RuntimeError(f"fs_guard: {what} reaches {pending}, outside {boundary}")
        drive, rest = os.path.splitdrive(pending)
        parts = [p for p in rest.replace("/", os.sep).split(os.sep) if p]
        cur = drive
        redirected = None
        for i, part in enumerate(parts):
            cur = cur + os.sep + part
            if not os.path.lexists(cur):
                break
            if os.path.islink(cur) or (hasattr(os.path, "isjunction") and os.path.isjunction(cur)):
                text = os.readlink(cur)
                base = text if os.path.isabs(text) else _concat(os.path.dirname(cur), text)
                redirected = os.path.abspath(_concat(base, *parts[i + 1:]))
                break
        if redirected is None:
            return pending
        pending = redirected
    return pending  # a loop whose every hop was checked inside the boundary


def make_sandbox(directory: str) -> str:
    absolute = os.path.abspath(directory)
    if not _within(PROJECT_ROOT, absolute) or os.path.normcase(absolute) == os.path.normcase(PROJECT_ROOT):
        raise RuntimeError(f"fs_guard: sandbox {absolute} is not strictly inside {PROJECT_ROOT}")
    _walk(absolute, PROJECT_ROOT, f"sandbox {absolute}")
    Path(absolute).mkdir(parents=True, exist_ok=True)
    real = os.path.realpath(absolute)
    root = os.path.realpath(PROJECT_ROOT)
    if not _within(root, real) or os.path.normcase(real) == os.path.normcase(root):
        raise RuntimeError(f"fs_guard: sandbox {absolute} really resolves to {real}, outside {PROJECT_ROOT}")
    return absolute


def _assert_raw_form(target: str) -> None:
    """The Owner's prohibited raw target forms, refused BEFORE any normalization: a ".." segment,
    a drive form ("X:", "X:foo", "X:\\"), an absolute / UNC / device path, an empty name."""
    if not isinstance(target, str) or target == "":
        raise RuntimeError("fs_guard: empty target")
    if len(target) >= 2 and target[0].isalpha() and target[1] == ":":
        raise RuntimeError(f"fs_guard: {target!r} is a drive form")
    if target[0] in "\\/":
        raise RuntimeError(f"fs_guard: {target!r} is absolute, UNC or a device path")
    if ".." in target.replace("\\", "/").split("/"):
        raise RuntimeError(f"fs_guard: {target!r} has a '..' segment")


def assert_inside(sandbox: str, target: str, cwd: str | None = None) -> str:
    _assert_raw_form(target)
    base = cwd or sandbox
    lexical = os.path.abspath(target if os.path.isabs(target) else _concat(base, target))
    if not _within(sandbox, lexical):
        raise RuntimeError(f"fs_guard: {target!r} resolves to {lexical}, outside {sandbox}")
    if os.path.normcase(lexical) == os.path.normcase(os.path.abspath(sandbox)):
        raise RuntimeError(f"fs_guard: {target!r} is the sandbox root itself")
    _walk(lexical, sandbox, repr(target))
    return lexical


def assert_output(file: str) -> str:
    absolute = os.path.abspath(file)
    for root in (r for r in (PROJECT_ROOT, _OUTPUT_ROOT) if r):
        if _within(root, absolute) and os.path.normcase(absolute) != os.path.normcase(root):
            try:
                _walk(absolute, root, f"output {absolute}")
                return absolute
            except RuntimeError:
                pass
    raise RuntimeError(f"fs_guard: output {absolute} is outside the project root")
