"""L12-D005 (#126) characterization: the certified Python LocalFileSystem.remove on the same cases as
pi-probe.mjs (minus the chmod-interleaving hook, which is Node-internal).
   PYTHONPATH=<minion-agent-python>/src python py-probe.py <out.json>"""

import asyncio
import getpass
import json
import os
import pathlib
import stat
import subprocess
import sys
import tempfile

from minion_agent.execution import LocalFileSystem, is_ok

WIN = sys.platform == "win32"
USER = getpass.getuser() if WIN else str(os.getuid())


def icacls(p, *args):
    subprocess.run(["icacls", str(p), *args], check=True, capture_output=True)


def deny(p, rights):
    icacls(p, "/deny", f"{USER}:({rights})")


def undeny(p):
    subprocess.run(["icacls", str(p), "/remove:d", USER], capture_output=True)


def readonly(p):
    os.chmod(p, stat.S_IREAD)


def file(p, text="x"):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


def left(d, base=None):
    base = base or d
    out = []
    try:
        names = sorted(os.listdir(d))
    except OSError:
        return out
    for n in names:
        p = d / n
        rel = p.relative_to(base).as_posix()
        if p.is_symlink():
            out.append(rel + "@")
        elif p.is_dir():
            out.append(rel + "/")
            out.extend(left(p, base))
        else:
            out.append(rel)
    return out


def attrib_readonly(p):
    r = subprocess.run(["attrib", str(p)], capture_output=True, text=True)
    return "R" in r.stdout[:12]


def state(p):
    if not os.path.exists(p):
        return {"exists": False}
    return {"exists": True, "readonly": attrib_readonly(p) if WIN else not (os.stat(p).st_mode & 0o200)}


def observe(cwd, r):
    if is_ok(r):
        return {"ok": True}
    e = r.error
    path = os.path.relpath(e.path, cwd).replace(os.sep, "/") if e.path else None
    return {"code": e.code.value, "path": path}


def c_child_readonly(cwd, ext):
    file(cwd / "t/sub/f"); readonly(cwd / "t/sub/f"); return "t", True, None, None


def c_target_ro_rec(cwd, ext):
    file(cwd / "f"); readonly(cwd / "f"); return "f", True, None, None


def c_target_ro_nonrec(cwd, ext):
    file(cwd / "f"); readonly(cwd / "f"); return "f", False, None, None


def c_nested(cwd, ext):
    for f in ("t/a", "t/s/b", "t/s/u/c", "t/z"):
        file(cwd / f); readonly(cwd / f)
    return "t", True, None, None


def c_ro_dir_attr(cwd, ext):
    file(cwd / "t/d/f"); subprocess.run(["attrib", "+R", str(cwd / "t/d")], check=True)
    return "t", True, None, lambda: subprocess.run(["attrib", "-R", str(cwd / "t/d")], capture_output=True)


def c_chmod_denied(cwd, ext):
    f = cwd / "t/f"; file(f); readonly(f); deny(f, "WA"); return "t", True, None, lambda: undeny(f)


def c_retry_fails(cwd, ext):
    d = cwd / "t"; f = d / "f"; file(f); readonly(f); deny(f, "D"); deny(d, "DC")
    return "t", True, None, lambda: (undeny(d), undeny(f))


def c_acl_file(cwd, ext):
    d = cwd / "t"; f = d / "f"; file(f); deny(f, "D"); deny(d, "DC")
    return "t", True, None, lambda: (undeny(d), undeny(f))


def c_acl_dir(cwd, ext):
    t = cwd / "t"; d = t / "d"; d.mkdir(parents=True); deny(d, "D"); deny(t, "DC")
    return "t", True, None, lambda: (undeny(t), undeny(d))


def c_acl_top(cwd, ext):
    f = cwd / "f"; file(f); deny(f, "D"); deny(cwd, "DC")
    return "f", True, None, lambda: (undeny(cwd), undeny(f))


def c_link_file(cwd, ext):
    target = ext / "protected.txt"; file(target, "keep"); readonly(target)
    (cwd / "t").mkdir(); os.symlink(target, cwd / "t/link")
    return "t", True, target, lambda: os.chmod(target, 0o666)


def c_link_dir(cwd, ext):
    target = ext / "pdir"; file(target / "inner.txt", "keep")
    if WIN:
        subprocess.run(["attrib", "+R", str(target)], check=True)
    else:
        os.chmod(target, 0o555)
    (cwd / "t").mkdir(); os.symlink(target, cwd / "t/dlink", target_is_directory=True)

    def cleanup():
        if WIN:
            subprocess.run(["attrib", "-R", str(target)], capture_output=True)
        else:
            os.chmod(target, 0o755)
    return "t", True, target, cleanup


def c_posix_ro_subdir(cwd, ext):
    file(cwd / "t/sub/f"); os.chmod(cwd / "t/sub", 0o555)
    return "t", True, None, lambda: os.chmod(cwd / "t/sub", 0o755)



def _attrib(flag, p):
    subprocess.run(["attrib", flag, str(p)], capture_output=True)


def c_ro_empty_dir_rec(cwd, ext):
    (cwd / "d").mkdir(); _attrib("+R", cwd / "d"); return "d", True, None, lambda: _attrib("-R", cwd / "d")


def c_ro_nonempty_dir_rec(cwd, ext):
    file(cwd / "d/f"); readonly(cwd / "d/f"); _attrib("+R", cwd / "d"); return "d", True, None, lambda: _attrib("-R", cwd / "d")


def c_ro_dir_nonrec(cwd, ext):
    (cwd / "d").mkdir(); _attrib("+R", cwd / "d"); return "d", False, None, lambda: _attrib("-R", cwd / "d")


def c_mixed(cwd, ext):
    for f in ("t/a", "t/x/b", "t/x/y/c"):
        file(cwd / f)
    readonly(cwd / "t/x/b"); _attrib("+R", cwd / "t/x"); _attrib("+R", cwd / "t/x/y")
    return "t", True, None, None


def c_ro_link_itself(cwd, ext):
    target = ext / "plain.txt"; file(target, "keep")
    (cwd / "t").mkdir(); os.symlink(target, cwd / "t/link"); subprocess.run(["attrib", "+R", "/L", str(cwd / "t/link")], capture_output=True)
    return "t", True, target, None


def c_ro_link_target_nonrec(cwd, ext):
    target = ext / "protected.txt"; file(target, "keep"); readonly(target)
    os.symlink(target, cwd / "link")
    return "link", False, target, lambda: os.chmod(target, 0o666)


VANISH = {}


def c_vanish(cwd, ext):
    for f in ("t/a", "t/b", "t/c"):
        file(cwd / f)
        if WIN:
            readonly(cwd / f)
    VANISH["victim"] = cwd / "t/b"
    return "t", True, None, None

CASES = [
    ("child-readonly-file", "both", c_child_readonly),
    ("target-readonly-file-recursive", "both", c_target_ro_rec),
    ("target-readonly-file-nonrecursive", "both", c_target_ro_nonrec),
    ("nested-readonly-files", "both", c_nested),
    ("readonly-directory-attribute", "win32", c_ro_dir_attr),
    ("chmod-denied-readonly-file", "win32", c_chmod_denied),
    ("retry-fails-readonly-file", "win32", c_retry_fails),
    ("acl-denied-file", "win32", c_acl_file),
    ("acl-denied-directory", "win32", c_acl_dir),
    ("acl-denied-top-level-file", "win32", c_acl_top),
    ("symlink-to-external-readonly-file", "both", c_link_file),
    ("symlink-to-external-readonly-dir", "both", c_link_dir),
    ("readonly-empty-dir-target-recursive", "win32", c_ro_empty_dir_rec),
    ("readonly-nonempty-dir-target-recursive", "win32", c_ro_nonempty_dir_rec),
    ("readonly-dir-target-nonrecursive", "win32", c_ro_dir_nonrec),
    ("mixed-readonly-tree", "win32", c_mixed),
    ("readonly-symlink-itself", "win32", c_ro_link_itself),
    ("readonly-symlink-target-nonrecursive", "both", c_ro_link_target_nonrec),
    ("entry-vanishes-during-recursive", "both", c_vanish),
    ("posix-readonly-subdir", "linux", c_posix_ro_subdir),
]

_real_scandir = os.scandir


def _scandir_hook(path=None):
    # Interleaving hook (mirrors the Node readdir hook): list first, then delete the victim, then yield.
    victim = VANISH.pop("victim", None)
    it = _real_scandir(path) if path is not None else _real_scandir()
    if victim is None:
        return it
    entries = list(it)
    it.close()
    try:
        os.chmod(victim, 0o666)
    except OSError:
        pass
    os.unlink(victim)
    VANISH["fired"] = True

    class _It:
        def __init__(self):
            self._inner = iter(entries)

        def __iter__(self):
            return self

        def __next__(self):
            return next(self._inner)

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def close(self):
            pass
    return _It()


os.scandir = _scandir_hook


async def main(out):
    results = []
    for cid, where, setup in CASES:
        if where not in ("both", sys.platform):
            continue
        root = pathlib.Path(tempfile.mkdtemp(prefix="l12d005-py-")).resolve()
        cwd, ext = root / "cwd", root / "external"
        cwd.mkdir(); ext.mkdir()
        target, recursive, external, cleanup = setup(cwd, ext)
        fs = LocalFileSystem(str(cwd))
        r = await fs.remove(target, recursive=recursive)
        rec = {"id": cid, "call": {"target": target, "recursive": recursive}, "observed": observe(cwd, r), "left": left(cwd),
               "hook_fired": VANISH.pop("fired", False)}
        VANISH.pop("victim", None)
        if external is not None:
            rec["external"] = {**state(external), "inner": "inner.txt present" if (external / "inner.txt").exists() else "no inner.txt"} \
                if external.is_dir() else state(external)
        results.append(rec)
        if cleanup:
            try:
                cleanup()
            except Exception:
                pass
    pathlib.Path(out).write_text(json.dumps({"platform": sys.platform, "python": sys.version.split()[0], "results": results}, indent=1) + "\n")
    for r in results:
        print(f"{r['id']}: {json.dumps(r['observed'])} left={json.dumps(r['left'])}" + (f" ext={json.dumps(r['external'])}" if "external" in r else ""))


asyncio.run(main(sys.argv[1]))
