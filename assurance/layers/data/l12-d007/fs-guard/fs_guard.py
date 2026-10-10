"""Filesystem containment guard for Python probes and scripts (Owner rule, 2026-10-10).

Every destructive or writing operation on a computed path must first pass
assert_inside(sandbox, target). The sandbox itself must lie strictly under the project root.
"""

from __future__ import annotations

import os
from pathlib import Path

# FS_GUARD_ROOT is only for inside a container, e.g. a private tmpfs (/tmp) root.
PROJECT_ROOT = os.path.normcase(os.path.abspath(os.environ.get("FS_GUARD_ROOT", "E:/AI/Projects/OpenMinds/Minions/Minion-Agent")))


def _within(parent: str, child: str) -> bool:
    parent, child = os.path.normcase(parent), os.path.normcase(child)
    try:
        return os.path.commonpath([parent, child]) == parent
    except ValueError:  # different drives
        return False


def _real(p: str) -> str:
    cur, rest = os.path.abspath(p), []
    # A final component containing ":" names an NTFS stream of its parent, never a link; realpath
    # mis-parses it as drive-relative. Resolve the parent and re-attach the name.
    if ":" in os.path.basename(cur):
        rest.insert(0, os.path.basename(cur))
        cur = os.path.dirname(cur)
    while not os.path.lexists(cur):
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        rest.insert(0, os.path.basename(cur))
        cur = parent
    try:
        base = os.path.realpath(cur, strict=True)
    except OSError:  # e.g. a link loop: keep the lexical base, already checked
        base = cur
    # Never os.path.join here: it treats a component like "f:x" as drive F: and drops the base.
    return os.sep.join([base.rstrip("\\/"), *rest]) if rest else base


def make_sandbox(directory: str) -> str:
    absolute = os.path.abspath(directory)
    if not _within(PROJECT_ROOT, absolute) or os.path.normcase(absolute) == PROJECT_ROOT:
        raise RuntimeError(f"fs_guard: sandbox {absolute} is not strictly inside {PROJECT_ROOT}")
    Path(absolute).mkdir(parents=True, exist_ok=True)
    return absolute


def assert_inside(sandbox: str, target: str, cwd: str | None = None) -> str:
    if len(target) >= 2 and target[1] == ":" and not (len(target) >= 3 and target[2] in "\\/"):
        raise RuntimeError(f"fs_guard: {target!r} is drive-relative")
    if target.startswith(("\\\\", "//")):
        raise RuntimeError(f"fs_guard: {target!r} is a UNC path")
    # os.path.join would let a "f:x" component (drive F:) replace the base, so concatenate instead.
    base = cwd or sandbox
    lexical = os.path.abspath(target if os.path.isabs(target) else base.rstrip("\\/") + os.sep + target)
    if not _within(sandbox, lexical):
        raise RuntimeError(f"fs_guard: {target!r} resolves to {lexical}, outside {sandbox}")
    if os.path.normcase(lexical) == os.path.normcase(os.path.abspath(sandbox)):
        raise RuntimeError(f"fs_guard: {target!r} is the sandbox root itself")
    resolved = _real(lexical)
    if not _within(_real(sandbox), resolved):
        raise RuntimeError(f"fs_guard: {target!r} really resolves to {resolved}, outside {sandbox}")
    return lexical
