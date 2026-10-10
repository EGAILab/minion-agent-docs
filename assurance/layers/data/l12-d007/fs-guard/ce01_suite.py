"""CE-L12D007-01 synthetic control suite for fs_guard.py. Run in a child:
    python ce01_suite.py <guard dir> <virtual root>
Below the virtual root (inside the project, never created) os.lstat / readlink / realpath / listdir are
answered from an in-memory tree; every mutation (unlink, rmdir, chmod, mkdir, subprocess.run) is
RECORDED and never reaches the OS. Prints one JSON object { control: true|false }."""

import errno
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

guard_dir, VR = sys.argv[1], os.path.abspath(sys.argv[2])
sys.path.insert(0, guard_dir)
WIN = sys.platform == "win32"
OUT = "C:\\" if WIN else "/"
OUT_FILE = "C:\\ce01-never-created" if WIN else "/ce01-never-created"
proj = lambda s: s.encode("utf-16-le", "surrogatepass").decode("utf-16-le", "replace")  # noqa: E731
fold = os.path.normcase
TREE: dict = {}
CALLS: list = []


def _rel(p):
    a = os.path.abspath(str(p))
    if fold(a) == fold(VR):
        return ""
    try:
        if os.path.commonpath([fold(VR), fold(a)]) != fold(VR):
            return None
    except ValueError:
        return None
    # The guard projects before inspecting (section 14.1); the tree is keyed by NATIVE spelling,
    # so an unprojected lookup of a lone surrogate simply misses.
    return os.path.relpath(a, VR).replace("\\", "/")


def _err(code, p):
    exc = {errno.ENOENT: FileNotFoundError, errno.ENOTDIR: NotADirectoryError, errno.EACCES: PermissionError,
           errno.EPERM: PermissionError}.get(code, OSError)
    return exc(code, os.strerror(code), str(p))


def _entry(p):
    r = _rel(p)
    if r is None:
        return None
    if r == "":
        return {"type": "dir"}
    parts = r.split("/")
    for i in range(1, len(parts)):
        pre = TREE.get("/".join(parts[:i]))
        if pre is None:
            raise _err(errno.ENOENT, p)
        if pre.get("err"):
            raise _err(pre["err"], p)
        if pre["type"] == "file":
            raise _err(errno.ENOTDIR, p)
        if pre["type"] == "link":
            raise _err(errno.ENOENT, p)
    e = TREE.get(r)
    if e is None:
        raise _err(errno.ENOENT, p)
    if e.get("err"):
        raise _err(e["err"], p)
    return e


class _St:
    def __init__(self, e):
        self.st_mode = {"link": stat.S_IFLNK, "dir": stat.S_IFDIR, "file": stat.S_IFREG}[e["type"]] | 0o700
        self.st_file_attributes = 0


real = {"lstat": os.lstat, "readlink": os.readlink, "realpath": os.path.realpath, "listdir": os.listdir}
os.lstat = lambda p, *a, **k: (lambda e: real["lstat"](p, *a, **k) if e is None else _St(e))(_entry(p))


def _readlink(p, *a, **k):
    e = _entry(p)
    if e is None:
        return real["readlink"](p, *a, **k)
    if e["type"] != "link":
        raise _err(errno.EINVAL, p)
    if e.get("readlink_err"):
        raise _err(e["readlink_err"], p)
    return e["text"]


os.readlink = _readlink
os.path.realpath = lambda p, *a, **k: os.path.abspath(p) if _rel(p) is not None else real["realpath"](p, *a, **k)


def _listdir(p):
    r = _rel(p)
    if r is None:
        return real["listdir"](p)
    CALLS.append(("listdir", os.path.abspath(p)))
    pre = "" if r == "" else r + "/"
    return [k[len(pre):] for k in TREE if k.startswith(pre) and "/" not in k[len(pre):] and k != r]


os.listdir = _listdir


def _mut(name, drop=False):
    def f(p, *a, **k):
        a_ = os.path.abspath(str(p))
        CALLS.append((name, a_))
        if _rel(a_) is None:
            raise _err(errno.EACCES, a_)
        if drop:
            TREE.pop(_rel(a_), None)
    return f


os.unlink = _mut("unlink", True)
os.rmdir = _mut("rmdir", True)
os.chmod = _mut("chmod")
Path.mkdir = lambda self, *a, **k: CALLS.append(("mkdir", str(self)))
subprocess.run = lambda args, *a, **k: CALLS.append(("exec", " ".join(map(str, args))))

import fs_guard as g  # noqa: E402

g.os = os


def setv(spec):
    TREE.clear()
    TREE.update({proj(k): v for k, v in spec.items()})
    CALLS.clear()


def refused(f):
    try:
        f()
        return False
    except (RuntimeError, OSError):
        return True


chain = lambda n, last: {f"c{i}": {"type": "link", "text": f"c{i + 1}" if i + 1 < n else last} for i in range(n)}  # noqa: E731
quiet = lambda *_: None  # noqa: E731
r = {}
setv(chain(42, OUT_FILE)); r["chain42_outward_refused"] = refused(lambda: g.assert_inside(VR, "c0"))  # noqa: E702
setv(chain(g.BUDGET + 1, "missing")); r["budget_plus_one_contained_refused"] = refused(lambda: g.assert_inside(VR, "c0"))  # noqa: E702
setv(chain(g.BUDGET, OUT_FILE)); r["last_hop_outward_refused"] = refused(lambda: g.assert_inside(VR, "c0"))  # noqa: E702
setv({"a": {"type": "link", "text": "b"}, "b": {"type": "link", "text": "a"}}); r["cycle2_allowed"] = not refused(lambda: g.assert_inside(VR, "a"))  # noqa: E702
setv({f"k{i}": {"type": "link", "text": f"k{(i + 1) % 10}"} for i in range(10)}); r["cycle10_allowed"] = not refused(lambda: g.assert_inside(VR, "k0"))  # noqa: E702
for code, name in ((errno.EACCES, "EACCES"), (errno.EPERM, "EPERM"), (errno.EBUSY, "EBUSY")):
    setv({"d": {"type": "dir", "err": code}}); r[f"ancestor_{name}_refused"] = refused(lambda: g.assert_inside(VR, "d/x"))  # noqa: E702
    setv({"f": {"type": "file", "err": code}}); r[f"leaf_{name}_refused"] = refused(lambda: g.assert_inside(VR, "f"))  # noqa: E702
setv({"l": {"type": "link", "text": "x", "readlink_err": errno.EACCES}}); r["readlink_failure_refused"] = refused(lambda: g.assert_inside(VR, "l"))  # noqa: E702
setv({}); r["missing_allowed"] = not refused(lambda: g.assert_inside(VR, "nothing/here"))  # noqa: E702
setv({"f": {"type": "file"}}); r["enotdir_allowed"] = not refused(lambda: g.assert_inside(VR, "f/x"))  # noqa: E702
setv({"j": {"type": "link", "text": OUT}})
r["a_referent_through_outward_link_refused"] = refused(lambda: g.assert_inside(VR, "j")) and refused(lambda: g.assert_inside(VR, "j/x"))
r["b_entry_on_outward_link_allowed"] = not refused(lambda: g.assert_entry(VR, "j"))
r["d_entry_under_outward_ancestor_refused"] = refused(lambda: g.assert_entry(VR, "j/x"))
setv({"j": {"type": "link", "text": OUT}, "d": {"type": "dir"}, "d/f": {"type": "file"}})
ok = g.cleanup_sandbox(VR, quiet)
jp = os.path.join(VR, "j")
r["c_cleanup_removes_link_as_entry_only"] = (
    ok and any(c[0] in ("unlink", "rmdir") and c[1] == jp for c in CALLS)
    and not any(c[0] == "listdir" and c[1] == jp for c in CALLS)
    and not any(c[0] == "exec" and ("/T" in c[1].split() or jp in c[1]) for c in CALLS)
    and not any(c[0] != "exec" and _rel(c[1]) is None for c in CALLS))
setv({"a\uFFFD": {"type": "link", "text": OUT_FILE}})
r["e_projection_alias_refused"] = refused(lambda: g.assert_inside(VR, "a\uD800")) and refused(lambda: g.assert_inside(VR, "a\uDC00"))
done = []
setv({}); r["f_restore_missing_skipped"] = not g.restore_access(VR, "gone", "file", done.append, quiet) and not done  # noqa: E702
setv({"l": {"type": "link", "text": "x"}}); r["f_restore_link_skipped"] = not g.restore_access(VR, "l", "file", done.append, quiet) and not done  # noqa: E702
setv({"f": {"type": "file"}}); r["f_restore_existing_done"] = g.restore_access(VR, "f", "file", done.append, quiet) and len(done) == 1  # noqa: E702
print(json.dumps(r))
