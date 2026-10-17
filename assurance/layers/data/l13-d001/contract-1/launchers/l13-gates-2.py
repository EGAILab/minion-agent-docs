"""L13-D001 contract candidate 1: focused Windows gates and negative controls at the exact code head (one run, no retry).

Run with: <ri001 venv python> -I -B l13-gates-1.py <expected 40-hex code head>

Revision 3 (a new file and a new run directory, gate-2; gate-1 is kept as evidence). After the revision-2 window
stopped at the candidate gates, it:
- sets the pinned ICU 78.3 Windows runtime the collation loader documents (MINION_AGENT_ICU_BIN and
  MINION_AGENT_ICU_IDENTITY);
- proves the pinned collation loads before any gate;
- runs the repository's configured gates (ruff check and format over the project, and mypy as pyproject.toml
  configures it), not ad-hoc single-file runs;
- records the focused pytest totals from a junit file.
Everything below, from revision 2 (Codex paper recheck passed, sha256 6790c5ac...), is unchanged.

Containment (guard pattern of the reviewed i235/sync-check.py, `prove`):
- No '..' segment, normal form, lexically inside and not equal to the root.
- Every ancestor is a plain directory with no reparse point.
- The real path equals the literal path.
- An existing target is plain and of the expected kind; a must-be-missing target refuses if present.

Rules:
- Every created path is proven missing immediately before its own exclusive mkdir or open("x"/"xb").
- Every path given to a subprocess is re-proven immediately before that subprocess: cwd, interpreter, executable,
  import root, caches, and basetemp, which must be missing.
- The control copy is a walker. Each source entry is lstat-ed and refused if it is a link or reparse point; links are
  never followed. Each output is proven before its own creation. The bound source is only read, never written.
- Nothing is deleted.

Phases:
1. ruff check and ruff format --check, mypy, focused pytest (no coverage). If any of them fails, the run stops
   before the controls.
2. Each control:
   a. baseline: its exact witnesses on the unmodified bound source, each green, with import origin proven = SRC;
   b. mutated: the witnesses on a walker copy with exactly one mutation, import origin proven = the copy. Each
      witness must report exactly 1 test, 1 failure, 0 errors and 0 skips (junit XML), and its failure text must
      contain the control's intended observable. Collection, setup, import or unrelated errors earn no credit;
   c. restored: the witnesses on the unmodified bound source again, each green.
   Only a+b+c together count as KILLED. Import-origin proofs and per-witness junit files are kept under the run
   directory.
"""

import json
import ntpath
import os
import stat
import subprocess
import sys
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True

ROOT = r"E:\AI\Projects\OpenMinds\Minions\Minion-Agent"
CODE = r"E:\AI\Projects\OpenMinds\Minions\Minion-Agent\review-worktrees\claude-l13d001-code"
PY_DIR = CODE + r"\minion-agent-python"
SRC = PY_DIR + r"\src"
VENV = r"E:\AI\Projects\OpenMinds\Minions\Minion-Agent\review-worktrees\ri001-code\minion-agent-python\.venv"
PYTHON = VENV + r"\Scripts\python.exe"
RUFF = VENV + r"\Scripts\ruff.exe"
RUN = r"E:\AI\Projects\OpenMinds\Minions\Minion-Agent\.tmp\claude-scratch\l13\gate-2"
# The pinned ICU 78.3 Windows build (scripts/pinned-icu/build.sh); collation.py reads both (CE-L13-WP131-03).
ICU_BIN = r"E:\AI\Projects\OpenMinds\Minions\Minion-Agent\.toolchain\icu-78.3-src\icu\bin64"
ICU_IDENTITY = r"E:\AI\Projects\OpenMinds\Minions\Minion-Agent\.toolchain\icu-78.3-src\pinned-icu-identity.txt"
EXPECTED = sys.argv[1] if len(sys.argv) > 1 else ""
REPARSE = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
SKIP_DIRS = {"__pycache__"}
SKIP_SUFFIXES = (".pyc", ".pyo")

S13 = "tests/tools/builtin/test_tools.py::test_ls_falls_back_to_the_pipeline_path_when_absolute_path_fails"
SCN = "tests/conformance/test_builtin_tool_conformance.py::test_builtin_tool_scenario[{}]"
LS_FALLBACK = "    directory = working if isinstance(resolved, Err) else resolved.value\n"
# (id, file under src, module, anchor, replacement, witnesses, intended observable in the failure text)
CONTROLS = [
    ("K1-ls-fallback-uses-caller-raw-path", r"minion_agent\tools\builtin\ls.py", "minion_agent.tools.builtin.ls",
     LS_FALLBACK, "    directory = path if isinstance(resolved, Err) else resolved.value\n",
     [S13], "Path not found: @no"),
    ("K2-ls-fallback-fabricates-an-absolute-path", r"minion_agent\tools\builtin\ls.py", "minion_agent.tools.builtin.ls",
     LS_FALLBACK, '    directory = "/" + working if isinstance(resolved, Err) else resolved.value\n',
     [S13], "Path not found: /no such"),
    ("K3-read-step4-converts-bare-file-colon", r"minion_agent\tools\builtin\paths.py", "minion_agent.tools.builtin.paths",
     '    if working.startswith("file://"):\n', '    if working.startswith("file:"):\n',
     [SCN.format("builtin-read-bare-file-colon-input-reaches-the-resolver-unconverted")], "bare-file-colon: "),
    ("K3-ls-step4-converts-bare-file-colon", r"minion_agent\tools\builtin\paths.py", "minion_agent.tools.builtin.paths",
     '    if working.startswith("file://"):\n', '    if working.startswith("file:"):\n',
     [SCN.format("builtin-ls-bare-file-colon-input-reaches-the-resolver-unconverted")], "bare-file-colon: "),
    ("K4-win-directory-read-reverts-to-permission-denied", r"minion_agent\execution\_libuv_win32.py",
     "minion_agent.execution._libuv_win32",
     "        raise IsADirectoryError(_errno.EISDIR, os.strerror(_errno.EISDIR))\n",
     "        raise PermissionError(_errno.EACCES, os.strerror(_errno.EACCES))\n",
     [SCN.format("builtin-read-real-directory-fails-the-read-as-is-a-directory")], "real-directory: text"),
]


def refuse(msg):
    print("L13-GATES-REFUSED: " + msg, flush=True)
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


def mkdir(p):
    os.mkdir(prove(p, "dir", "missing"))
    return p


def write_new(p, text):
    with open(prove(p, "file", "missing"), "x", encoding="utf-8") as f:
        f.write(text)


def copy_tree(src, dst, mutate=None):
    """Walker copy: each source entry lstat-ed (a link or reparse point refuses; never followed), each output proven
    missing immediately before its own exclusive creation. The source is only read. `mutate` is
    (source file, anchor, replacement): that one file is written with the anchor replaced, which must match once."""
    prove(src, "dir", "exists")
    mkdir(dst)
    with os.scandir(src) as it:
        entries = sorted(it, key=lambda e: e.name)
    for entry in entries:
        s = src + "\\" + entry.name
        d = dst + "\\" + entry.name
        st = os.lstat(s)
        plain_kind = "dir" if stat.S_ISDIR(st.st_mode) else "file"
        plain(st, f"source {s}", plain_kind)
        if plain_kind == "dir":
            if entry.name in SKIP_DIRS:
                continue
            copy_tree(s, d, mutate)
        else:
            if entry.name.endswith(SKIP_SUFFIXES):
                continue
            with open(prove(s, "file", "exists"), "rb") as f:
                data = f.read()
            if mutate is not None and norm(s) == norm(mutate[0]):
                anchor, replacement = mutate[1].encode("utf-8"), mutate[2].encode("utf-8")
                if data.count(anchor) != 1:
                    refuse(f"mutation anchor matched {data.count(anchor)} times in {s}")
                data = data.replace(anchor, replacement)
                MUTATED.append(d)
            with open(prove(d, "file", "missing"), "xb") as f:
                f.write(data)


MUTATED: list[str] = []


for p, kind in ((CODE, "dir"), (PY_DIR, "dir"), (SRC, "dir"), (PYTHON, "file"), (RUFF, "file")):
    prove(p, kind, "exists")
head = subprocess.run(["git", "-C", CODE, "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
dirty = subprocess.run(["git", "-C", CODE, "status", "--porcelain"], capture_output=True, text=True, check=True).stdout
if not EXPECTED or head != EXPECTED or dirty.strip():
    refuse(f"head {head} (expected {EXPECTED!r}) / dirty {dirty!r}")

mkdir(RUN)
TMP = mkdir(RUN + r"\tmp")
PYCACHE = mkdir(RUN + r"\pycache")
MYPYCACHE = mkdir(RUN + r"\mypycache")
CONTROL_ROOT = mkdir(RUN + r"\controls")
base_env = dict(os.environ)
base_env.update({"PYTHONDONTWRITEBYTECODE": "1", "PYTHONPYCACHEPREFIX": PYCACHE, "TMP": TMP, "TEMP": TMP,
                 "TMPDIR": TMP, "PIP_NO_INDEX": "1", "MYPY_CACHE_DIR": MYPYCACHE,
                 "MINION_AGENT_ICU_BIN": prove(ICU_BIN, "dir", "exists"),
                 "MINION_AGENT_ICU_IDENTITY": prove(ICU_IDENTITY, "file", "exists")})


def preflight(exe, import_root, basetemp, also_missing=()):
    """Re-proven immediately before each subprocess: cwd, executable, import root, caches; basetemp and any
    output the subprocess will create must be missing."""
    prove(PY_DIR, "dir", "exists")
    prove(exe, "file", "exists")
    prove(import_root, "dir", "exists")
    for p in (TMP, PYCACHE, MYPYCACHE, ICU_BIN):
        prove(p, "dir", "exists")
    prove(ICU_IDENTITY, "file", "exists")
    if basetemp is not None:
        prove(basetemp, "dir", "missing")
    for p in also_missing:
        prove(p, "file", "missing")


def run(name, args, import_root, basetemp=None, also_missing=()):
    log_path = prove(RUN + "\\" + name + ".log", "file", "missing")
    with open(log_path, "x", encoding="utf-8") as log:
        preflight(args[0], import_root, basetemp, also_missing)
        rc = subprocess.run(args, cwd=PY_DIR, env=dict(base_env, PYTHONPATH=import_root + ";."),
                            stdout=log, stderr=subprocess.STDOUT).returncode
    write_new(RUN + "\\" + name + ".exit", f"{rc}\n")
    print(f"L13-GATES: {name} exit {rc}", flush=True)
    return rc


def origin(name, module, import_root, expected_file):
    """Proves which file the interpreter imports for `module` under this import root; the proof is kept."""
    preflight(PYTHON, import_root, None)
    probe = subprocess.run([PYTHON, "-B", "-c", f"import {module} as m; print(m.__file__)"], cwd=PY_DIR,
                           env=dict(base_env, PYTHONPATH=import_root + ";."), capture_output=True, text=True)
    imported = probe.stdout.strip()
    record = {"module": module, "import_root": import_root, "imported": imported, "expected": expected_file,
              "exit": probe.returncode, "stderr_tail": probe.stderr[-500:]}
    write_new(RUN + "\\" + name + ".origin.json", json.dumps(record, indent=2))
    if probe.returncode != 0 or norm(imported) != norm(expected_file):
        refuse(f"{name}: import origin {imported!r} is not {expected_file!r}")


def pytest_witness(name, target, import_root):
    """One exact witness; returns (exit, junit summary)."""
    basetemp = RUN + "\\" + name + ".basetemp"
    junit = RUN + "\\" + name + ".junit.xml"
    rc = run(name, [PYTHON, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "--no-cov",
                    f"--basetemp={basetemp}", f"--junitxml={junit}", target], import_root, basetemp, (junit,))
    try:
        suite = ET.parse(prove(junit, "file", "exists")).getroot()
        suite = suite if suite.tag == "testsuite" else suite.find("testsuite")
        cases = suite.findall("testcase")
        failures = [f for c in cases for f in c.findall("failure")]
        summary = {"tests": int(suite.get("tests", 0)), "failures": int(suite.get("failures", 0)),
                   "errors": int(suite.get("errors", 0)), "skipped": int(suite.get("skipped", 0)),
                   "failure_text": "\n".join((f.get("message") or "") + "\n" + (f.text or "") for f in failures)}
    except (ET.ParseError, AttributeError, OSError) as exc:
        summary = {"tests": 0, "failures": 0, "errors": 1, "skipped": 0, "failure_text": f"junit unreadable: {exc}"}
    return rc, summary


print("L13-GATES: head " + head + " clean", flush=True)
results = {"head": head}
# Revision 3: the pinned collation must load under the pinned ICU before any gate (a load failure stops the run).
results["icu-load"] = run("icu-load", [PYTHON, "-B", "-c",
                                       "from minion_agent.tools.builtin.collation import pinned_collation; "
                                       "pinned_collation(); print('pinned collation loaded')"], SRC)
if results["icu-load"] != 0:
    write_new(RUN + r"\summary.json", json.dumps(results, indent=2))
    print("L13-GATES: icu-load RED; no later gate or control run", flush=True)
    sys.exit(1)
# The repository's configured gates: ruff over the project, and mypy as pyproject.toml configures it
# (files = src/minion_agent; tests are not in the configured mypy gate).
results["ruff-check"] = run("ruff-check", [RUFF, "check", "--no-cache", "."], SRC)
# Whole-project format is reported as-is. The prior baseline has known inherited drift in 7 files, which this
# candidate neither fixes nor waives. The candidate's own format gate is the one Python file it changes.
results["ruff-format-project"] = run("ruff-format-project", [RUFF, "format", "--check", "--no-cache", "."], SRC)
results["ruff-format"] = run("ruff-format", [RUFF, "format", "--check", "--no-cache",
                                             "tests/tools/builtin/test_tools.py"], SRC)
results["mypy"] = run("mypy", [PYTHON, "-B", "-m", "mypy", "--cache-dir", MYPYCACHE], SRC)
FOCUSED_JUNIT = RUN + r"\pytest-focused.junit.xml"
results["pytest-focused"] = run("pytest-focused", [
    PYTHON, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "--no-cov", f"--basetemp={RUN}\\basetemp-focused",
    f"--junitxml={FOCUSED_JUNIT}",
    "tests/tools/builtin/test_tools.py", "tests/tools/builtin/test_read_access_and_abort_order.py",
    "tests/conformance/test_builtin_tool_conformance.py", "tests/conformance/test_manifest_validation.py",
    "tests/conformance/test_schema_validation.py"], SRC, RUN + r"\basetemp-focused", (FOCUSED_JUNIT,))
try:
    _suite = ET.parse(prove(FOCUSED_JUNIT, "file", "exists")).getroot()
    _suite = _suite if _suite.tag == "testsuite" else _suite.find("testsuite")
    results["pytest-focused-totals"] = {k: int(_suite.get(k, 0)) for k in ("tests", "failures", "errors", "skipped")}
except (ET.ParseError, AttributeError, OSError) as exc:
    results["pytest-focused-totals"] = f"junit unreadable: {exc}"
gates_ok = all(results[k] == 0 for k in ("icu-load", "ruff-check", "ruff-format", "mypy", "pytest-focused"))
if not gates_ok:
    write_new(RUN + r"\summary.json", json.dumps(results, indent=2))
    print("L13-GATES: candidate gates RED; controls not run", flush=True)
    sys.exit(1)

controls = []
for index, (cid, rel, module, old, new, targets, observable) in enumerate(CONTROLS, 1):
    tag = f"k{index}"
    record = {"id": cid, "file": rel, "observable": observable, "witnesses": []}
    origin(f"{tag}-baseline", module, SRC, SRC + "\\" + rel)
    box = mkdir(CONTROL_ROOT + "\\" + tag)
    copy_src = box + r"\src"
    MUTATED.clear()
    copy_tree(SRC, copy_src, (SRC + "\\" + rel, old, new))
    target_file = prove(copy_src + "\\" + rel, "file", "exists")
    if [norm(m) for m in MUTATED] != [norm(target_file)]:
        refuse(f"{cid}: expected exactly one mutated file, got {MUTATED}")
    origin(f"{tag}-mutated", module, copy_src, target_file)
    killed = True
    for w_index, witness in enumerate(targets, 1):
        base_rc, base = pytest_witness(f"{tag}-w{w_index}-baseline", witness, SRC)
        mut_rc, mut = pytest_witness(f"{tag}-w{w_index}-mutated", witness, copy_src)
        rest_rc, rest = pytest_witness(f"{tag}-w{w_index}-restored", witness, SRC)
        base_green = base_rc == 0 and base["tests"] == 1 and base["failures"] == base["errors"] == base["skipped"] == 0
        rest_green = rest_rc == 0 and rest["tests"] == 1 and rest["failures"] == rest["errors"] == rest["skipped"] == 0
        intended = (mut_rc == 1 and mut["tests"] == 1 and mut["failures"] == 1 and mut["errors"] == 0
                    and mut["skipped"] == 0 and observable in mut["failure_text"])
        killed = killed and base_green and intended and rest_green
        record["witnesses"].append({"witness": witness, "baseline_green": base_green, "mutated": {
            "exit": mut_rc, **{k: mut[k] for k in ("tests", "failures", "errors", "skipped")},
            "observable_found": observable in mut["failure_text"]}, "intended_failure": intended,
            "restored_green": rest_green})
    record["status"] = "KILLED" if killed else "NOT_KILLED"
    controls.append(record)
results["controls"] = controls
write_new(RUN + r"\summary.json", json.dumps(results, indent=2))
n_killed = sum(c["status"] == "KILLED" for c in controls)
print(f"L13-GATES: gates GREEN; controls {n_killed}/{len(controls)} KILLED", flush=True)
sys.exit(0 if n_killed == len(controls) else 1)
