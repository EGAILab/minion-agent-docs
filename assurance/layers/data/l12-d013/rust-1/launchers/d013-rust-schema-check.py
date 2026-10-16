"""#235 Rust candidate: manifest and schema validation at the exact Rust code head (one run, no retry).

Run with: <ri001 venv python> -I -B sync-check.py
Literal paths only. Guard pattern of the reviewed i222/retain-pycache.py, extended to missing targets:
every path is proven (prove) immediately before each mkdir/open and before pytest receives basetemp:
  - no '..' segment, normal form, lexically inside and not equal to the project root;
  - every ancestor lstat-ed without following links through the drive root: each must be a plain
    directory with no reparse point; an inspection failure refuses;
  - the nearest existing ancestor's (or the existing target's) real path equals its literal path;
  - an existing target is itself not a link or reparse point, of the expected kind; a must-be-missing
    target refuses if present.
Creation is exclusive (mkdir; open "x"). Nothing is deleted. Coverage is off for this focused run.
"""

import ntpath
import os
import stat
import subprocess
import sys

sys.dont_write_bytecode = True

ROOT = r"E:\AI\Projects\OpenMinds\Minions\Minion-Agent"
CODE = r"E:\AI\Projects\OpenMinds\Minions\Minion-Agent\review-worktrees\codex-l12d013-rust-impl"
PY_DIR = r"E:\AI\Projects\OpenMinds\Minions\Minion-Agent\review-worktrees\codex-l12d013-rust-impl\minion-agent-python"
PYTHON = r"E:\AI\Projects\OpenMinds\Minions\Minion-Agent\review-worktrees\ri001-code\minion-agent-python\.venv\Scripts\python.exe"
RUN = r"E:\AI\Projects\OpenMinds\Minions\Minion-Agent\.tmp\codex-scratch\d013-rust-schema1"
TMP = r"E:\AI\Projects\OpenMinds\Minions\Minion-Agent\.tmp\codex-scratch\d013-rust-schema1\tmp"
PYCACHE = r"E:\AI\Projects\OpenMinds\Minions\Minion-Agent\.tmp\codex-scratch\d013-rust-schema1\pycache"
BASETEMP = r"E:\AI\Projects\OpenMinds\Minions\Minion-Agent\.tmp\codex-scratch\d013-rust-schema1\basetemp"
LOG = r"E:\AI\Projects\OpenMinds\Minions\Minion-Agent\.tmp\codex-scratch\d013-rust-schema1\pytest.log"
EXIT = r"E:\AI\Projects\OpenMinds\Minions\Minion-Agent\.tmp\codex-scratch\d013-rust-schema1\pytest.exit"
EXPECTED = "1c0a1783a8109b85d2679eb7a294b1ada640010a"
REPARSE = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


def refuse(msg):
    print("SYNC-CHECK-REFUSED: " + msg, flush=True)
    sys.exit(97)


def norm(p):
    return os.path.normcase(p)


def plain(st, what, kind):
    attrs = getattr(st, "st_file_attributes", 0)
    if stat.S_ISLNK(st.st_mode) or attrs & REPARSE:
        refuse(f"{what} is a link or reparse point")
    if kind == "dir" and not stat.S_ISDIR(st.st_mode):
        refuse(f"{what} is not a plain directory")
    if kind == "file" and not stat.S_ISREG(st.st_mode):
        refuse(f"{what} is not a plain file")


def lstat_or_none(p, what):
    try:
        return os.lstat(p)
    except FileNotFoundError:
        return None
    except OSError as exc:
        refuse(f"cannot inspect {what} {p}: {exc}")


def prove(p, kind, state):
    """kind: 'dir' or 'file'; state: 'exists', 'missing'."""
    if ".." in p.replace("/", "\\").split("\\"):
        refuse(f"'..' segment in {p}")
    if ntpath.normpath(p) != p:
        refuse(f"not in normal form: {p}")
    if os.path.commonpath([norm(p), norm(ROOT)]) != norm(ROOT) or norm(p) == norm(ROOT):
        refuse(f"lexically outside or equal to the root: {p}")
    nearest = None
    cur = ntpath.dirname(p)
    while True:
        st = lstat_or_none(cur, "ancestor")
        if st is None:
            # a missing ancestor is allowed only below the root and below every existing ancestor
            inside = os.path.commonpath([norm(cur), norm(ROOT)]) == norm(ROOT) and norm(cur) != norm(ROOT)
            if nearest is not None or not inside:
                refuse(f"missing ancestor {cur} outside the root or above an existing one")
        else:
            plain(st, f"ancestor {cur}", "dir")
            if nearest is None:
                nearest = cur
        parent = ntpath.dirname(cur)
        if parent == cur:
            break
        cur = parent
    if nearest is None or norm(os.path.realpath(nearest)) != norm(nearest):
        refuse(f"nearest existing ancestor resolves elsewhere: {nearest}")
    st = lstat_or_none(p, "target")
    if state == "missing":
        if st is not None:
            refuse(f"must be missing: {p}")
    else:
        if st is None:
            refuse(f"must exist: {p}")
        plain(st, f"target {p}", kind)
        if norm(os.path.realpath(p)) != norm(p):
            refuse(f"target resolves elsewhere: {p}")
    return p


for p, kind in ((CODE, "dir"), (PY_DIR, "dir"), (PYTHON, "file")):
    prove(p, kind, "exists")
head = subprocess.run(["git", "-C", CODE, "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
dirty = subprocess.run(["git", "-C", CODE, "status", "--porcelain"], capture_output=True, text=True, check=True).stdout
if head != EXPECTED or dirty.strip():
    refuse(f"head {head} / dirty {dirty!r}")

os.mkdir(prove(RUN, "dir", "missing"))
os.mkdir(prove(TMP, "dir", "missing"))
os.mkdir(prove(PYCACHE, "dir", "missing"))
prove(BASETEMP, "dir", "missing")

env = dict(os.environ)
env.update({"PYTHONPATH": "src;.", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPYCACHEPREFIX": PYCACHE,
            "TMP": TMP, "TEMP": TMP, "TMPDIR": TMP, "PIP_NO_INDEX": "1"})
args = [PYTHON, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "--no-cov", f"--basetemp={BASETEMP}",
        "tests/conformance/test_manifest_validation.py", "tests/conformance/test_schema_validation.py"]
print("SYNC-CHECK: head " + head + " clean; running " + " ".join(args[2:]), flush=True)
with open(prove(LOG, "file", "missing"), "x", encoding="utf-8") as log:
    for p, kind in ((PY_DIR, "dir"), (PYTHON, "file"), (TMP, "dir"), (PYCACHE, "dir")):
        prove(p, kind, "exists")
    prove(BASETEMP, "dir", "missing")  # re-proven immediately before pytest, which may remove it
    rc = subprocess.run(args, cwd=PY_DIR, env=env, stdout=log, stderr=subprocess.STDOUT).returncode
with open(prove(EXIT, "file", "missing"), "x", encoding="utf-8") as f:
    f.write(f"{rc}\n")
print(f"SYNC-CHECK: pytest exit {rc}", flush=True)
sys.exit(rc)
