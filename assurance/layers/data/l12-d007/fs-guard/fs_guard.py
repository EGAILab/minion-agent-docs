"""Filesystem containment guard for Python probes and scripts (Owner rule 2026-10-10; convergence
episode CE-L12D007-01, AGREED FOR IMPLEMENTATION at revision 3). Mirrors fs-guard.mjs.

The proof is chosen by the OPERATION CLASS:
- REFERENT (assert_inside / make_sandbox / assert_output): anything that follows the final link; the
  whole effective native path is proven, and an outward final link is refused.
- ENTRY (assert_entry): a verified no-follow operation on the entry itself; the containing directory
  is proven, the entry is one R1-clean component and is NOT dereferenced.
- TRAVERSAL (cleanup_sandbox): children are classified as entries first; links are never descended.

The R2 proof succeeds only at (i) a completed traversal, (ii) a proven-missing component (R3), or
(iii) a repeated, fully checked state. Budget exhaustion, an outward hop, an unknown inspection
outcome or a readlink failure REFUSE. Paths are inspected in their section-14.1 native spelling
(unpaired surrogates -> U+FFFD, identical on Linux and Windows), because CPython on Windows would
otherwise pass a raw lone surrogate to NTFS.
"""

from __future__ import annotations

import errno
import os
import stat
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

# FS_GUARD_ROOT is only for inside a container (a private tmpfs root such as /tmp/guard-root).
PROJECT_ROOT = os.path.abspath(os.environ.get("FS_GUARD_ROOT", "E:/AI/Projects/OpenMinds/Minions/Minion-Agent"))
# FS_GUARD_OUTPUT optionally names one more directory outputs may be written to (a container's /out).
_OUTPUT_ROOT = os.path.abspath(os.environ["FS_GUARD_OUTPUT"]) if os.environ.get("FS_GUARD_OUTPUT") else None
BUDGET = 64
# R3: the only outcomes that prove a component MISSING. Windows 123/161: an invalid or over-long name
# or stream syntax cannot exist; 267: a prefix is not a directory.
_MISSING_WIN32 = frozenset({2, 3, 123, 161, 267})


def project(text: str) -> str:
    """Section 14.1's native projection: a valid pair (also split in two) joins, a lone surrogate
    becomes U+FFFD, everything else is unchanged -- identical on Linux and Windows."""
    return text.encode("utf-16-le", "surrogatepass").decode("utf-16-le", "replace")


def _fold(p: str) -> str:
    return os.path.normcase(p)


def _within(parent: str, child: str) -> bool:
    parent, child = _fold(os.path.abspath(parent)), _fold(child)
    try:
        return os.path.commonpath([parent, child]) == parent
    except ValueError:  # different drives
        return False


def _concat(base: str, *parts: str) -> str:
    # Never os.path.join: it treats a component like "f:x" as drive F: and drops the base.
    return os.sep.join([base.rstrip("\\/"), *parts]) if parts else base


def _inspect(p: str) -> os.stat_result | None:
    """R3: lstat; None only when the component is proven missing, otherwise refuse."""
    try:
        return os.lstat(p)
    except (FileNotFoundError, NotADirectoryError):
        return None
    except OSError as exc:
        if getattr(exc, "winerror", None) in _MISSING_WIN32 or exc.errno in (errno.ENOENT, errno.ENOTDIR):
            return None
        raise RuntimeError(f"fs_guard: cannot inspect {p} ({exc}); refused") from exc


def _is_link(st: os.stat_result) -> bool:
    if stat.S_ISLNK(st.st_mode):
        return True
    attrs = getattr(st, "st_file_attributes", 0)
    return bool(attrs & 0x400) and getattr(st, "st_reparse_tag", 0) in (0xA000000C, 0xA0000003)  # symlink, junction


def _prove(target: str, boundary: str, what: str) -> str:
    """R2: prove that `target` (native spelling) resolves inside `boundary`."""
    bounds = [os.path.abspath(boundary), os.path.realpath(boundary)]
    inside = lambda p: any(_within(b, p) for b in bounds)  # noqa: E731
    pending = os.path.abspath(project(target))
    seen: set[str] = set()
    for _ in range(BUDGET):
        if not inside(pending):
            raise RuntimeError(f"fs_guard: {what} reaches {pending}, outside {boundary}")
        if _fold(pending) in seen:
            return pending  # (iii) a repeated, fully checked state
        seen.add(_fold(pending))
        drive, rest = os.path.splitdrive(pending)
        parts = [p for p in rest.replace("/", os.sep).split(os.sep) if p]
        cur = drive
        redirected = None
        for i, part in enumerate(parts):
            cur = cur + os.sep + part
            st = _inspect(cur)
            if st is None:
                break  # (ii) proven missing
            if _is_link(st):
                try:
                    text = os.readlink(cur)
                except OSError as exc:
                    raise RuntimeError(f"fs_guard: cannot read link {cur} ({exc}); refused") from exc
                if text.startswith("\\\\?\\"):
                    text = text[4:]
                base = text if os.path.isabs(text) else _concat(os.path.dirname(cur), text)
                redirected = os.path.abspath(_concat(base, *parts[i + 1 :]))
                break
        if redirected is None:
            return pending  # (i) completed traversal, or (ii)
        if not inside(redirected):
            raise RuntimeError(f"fs_guard: {what} reaches {redirected} through a link, outside {boundary}")
        pending = redirected
    raise RuntimeError(f"fs_guard: {what}: {BUDGET}-hop budget exhausted without a repeated state; refused")


def _assert_raw_form(target: str) -> None:
    """R1: refused BEFORE any normalization."""
    if not isinstance(target, str) or target == "":
        raise RuntimeError("fs_guard: empty target")
    if len(target) >= 2 and target[0].isalpha() and target[1] == ":":
        raise RuntimeError(f"fs_guard: {target!r} is a drive form")
    if target[0] in "\\/":
        raise RuntimeError(f"fs_guard: {target!r} is absolute, UNC or a device path")
    if ".." in target.replace("\\", "/").split("/"):
        raise RuntimeError(f"fs_guard: {target!r} has a '..' segment")


def _lexical(sandbox: str, target: str, cwd: str | None) -> str:
    _assert_raw_form(target)
    lexical = os.path.abspath(_concat(cwd or sandbox, target))
    if not _within(sandbox, lexical):
        raise RuntimeError(f"fs_guard: {target!r} resolves to {lexical}, outside {sandbox}")
    if _fold(lexical) == _fold(os.path.abspath(sandbox)):
        raise RuntimeError(f"fs_guard: {target!r} is the sandbox root itself")
    return lexical


def assert_inside(sandbox: str, target: str, cwd: str | None = None) -> str:
    """REFERENT: the whole effective native path, through the final component."""
    lexical = _lexical(sandbox, target, cwd)
    _prove(lexical, sandbox, repr(target))
    return lexical


def assert_entry(sandbox: str, target: str, cwd: str | None = None) -> str:
    """ENTRY: for a verified no-follow operation on the entry itself; the final component is not
    dereferenced, the containing directory gets the full REFERENT proof."""
    lexical = _lexical(sandbox, target, cwd)
    parent = os.path.dirname(lexical)
    if _fold(parent) == _fold(os.path.abspath(sandbox)):
        _prove(parent, os.path.dirname(os.path.abspath(sandbox)), f"sandbox {sandbox}")
    else:
        _prove(parent, sandbox, f"parent of {target!r}")
    return lexical


def make_sandbox(directory: str) -> str:
    absolute = os.path.abspath(directory)
    if not _within(PROJECT_ROOT, absolute) or _fold(absolute) == _fold(PROJECT_ROOT):
        raise RuntimeError(f"fs_guard: sandbox {absolute} is not strictly inside {PROJECT_ROOT}")
    _prove(absolute, PROJECT_ROOT, f"sandbox {absolute}")  # the ancestry, BEFORE any mkdir
    Path(absolute).mkdir(parents=True, exist_ok=True)
    real = os.path.realpath(absolute)
    root = os.path.realpath(PROJECT_ROOT)
    if not _within(root, real) or _fold(real) == _fold(root):
        raise RuntimeError(f"fs_guard: sandbox {absolute} really resolves to {real}, outside {PROJECT_ROOT}")
    return absolute


def assert_output(file: str) -> str:
    absolute = os.path.abspath(file)
    for root in (r for r in (PROJECT_ROOT, _OUTPUT_ROOT) if r):
        if _within(root, absolute) and _fold(absolute) != _fold(root):
            try:
                _prove(absolute, root, f"output {absolute}")
                return absolute
            except RuntimeError:
                pass
    raise RuntimeError(f"fs_guard: output {absolute} is outside the project root")


def restore_access(sandbox: str, rel: str, kind: str, restore: Callable[[str], object],
                   log: Callable[[str], object] = print) -> bool:
    """R6: undo a deny only on an EXISTING, NON-LINK entry of the recorded kind, re-proven now."""
    try:
        target = assert_inside(sandbox, rel)
        st = _inspect(target)
        if st is None:
            log(f"fs_guard: restore skipped, {rel!r} is missing")
            return False
        if _is_link(st):
            log(f"fs_guard: restore skipped, {rel!r} is now a link")
            return False
        if (kind == "directory") != stat.S_ISDIR(st.st_mode):
            log(f"fs_guard: restore skipped, {rel!r} changed kind")
            return False
        restore(target)
        return True
    except (RuntimeError, OSError) as exc:
        log(f"fs_guard: restore skipped ({exc})")
        return False


def _reset_entry(p: str, is_dir: bool) -> None:
    """Only on an ordinary (non-link) entry just proven."""
    if sys.platform == "win32":
        subprocess.run(["icacls", p, "/reset", "/L", "/Q"], check=True, capture_output=True)
        os.chmod(p, stat.S_IWRITE | stat.S_IREAD)
    else:
        os.chmod(p, 0o700 if is_dir else 0o600)


def _remove_link_entry(p: str) -> None:
    """ENTRY removal of a link or junction AS ITSELF (unlink / rmdir never follow it)."""
    try:
        os.unlink(p)
    except OSError:
        os.rmdir(p)


def cleanup_sandbox(root: str, log: Callable[[str], object] = print) -> bool:
    """R7: TRAVERSAL; links removed as entries and never descended; ordinary children re-proven
    before they are visited; each entry reset singly; bottom-up removal. A failure leaves it."""
    root = os.path.abspath(root)
    try:
        assert_inside(os.path.dirname(root), os.path.basename(root))

        def clean(directory: str) -> None:
            _reset_entry(directory, True)
            for name in os.listdir(directory):
                child = assert_entry(root, os.path.relpath(_concat(directory, name), root))
                st = _inspect(child)
                if st is None:
                    continue
                if _is_link(st):
                    _remove_link_entry(child)
                    continue
                assert_inside(root, os.path.relpath(child, root))
                if stat.S_ISDIR(st.st_mode):
                    clean(child)
                    os.rmdir(child)
                else:
                    _reset_entry(child, False)
                    os.unlink(child)

        clean(root)
        os.rmdir(root)
        return True
    except (RuntimeError, OSError, subprocess.CalledProcessError) as exc:
        log(f"fs_guard: sandbox left in place ({exc}): {root}")
        return False
