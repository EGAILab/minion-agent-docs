"""L12-D005 negative controls (minion-agent#188): each mutant edits one disposable copy of
`minion-agent-python` that carries the L12-D005 correction, and must be killed by its intended canonical
witness (process section 9.7).

Usage (Windows; scratch on E:):
    python controls.py PYTHON_EXE MINION_AGENT_PYTHON_DIR SCRATCH_DIR

MINION_AGENT_PYTHON_DIR must contain the correction:
- contract stage: a scratch copy of the contract candidate with gen/planned_fix.py applied (the
  candidate's strict xfail markers stay; every run passes --runxfail and clears PYTEST_ADDOPTS);
- implementation stage: the implementation candidate itself (anchors are then re-pointed at its code).

Validity: before any mutant, every intended witness must be selected and PASS unmutated (-rA PASSED
lines). A kill needs pytest exit 1, failures without errors, no XPASS, and the canonical assertion
`assert observed["expect"] == case["expect"]` or `assert observed["expect_left"] == case["expect_left"]`
in the output. Exit 0 is SURVIVED; anything else is INVALID. Non-zero exit unless all are KILLED.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

FS = "src/minion_agent/execution/filesystem.py"
TEST = "tests/conformance/test_fs_remove_readonly_conformance.py::test_fs_remove_readonly_case"
SIGNATURES = ('assert observed["expect"] == case["expect"]', 'assert observed["expect_left"] == case["expect_left"]')


def node(name: str) -> str:
    return f"{TEST}[fs-remove-readonly-{name}]"


# (name, old, new, intended witnesses)
CONTROLS = [
    ("top-level-delete-not-retried",
     "    _delete_ignoring_readonly(os.remove, path)\n\n\nclass FileSystem",
     "    os.remove(path)\n\n\nclass FileSystem",
     [node("nonrec-readonly-target-file"), node("rec-readonly-target-file")]),
    ("tree-entries-not-retried",
     '        and getattr(function, "__name__", "") in ("unlink", "remove", "rmdir")\n',
     '        and getattr(function, "__name__", "") in ()\n',
     [node("rec-readonly-child-file"), node("rec-nested-readonly-files")]),
    ("directories-not-retried",
     '        and getattr(function, "__name__", "") in ("unlink", "remove", "rmdir")\n',
     '        and getattr(function, "__name__", "") in ("unlink", "remove")\n',
     [node("rec-readonly-empty-dir-target"), node("rec-readonly-dir-attribute-in-tree")]),
    ("attribute-cleared-on-the-link-target",
     "        os.chmod(path, _stat.S_IWRITE, follow_symlinks=False)\n",
     "        os.chmod(os.path.realpath(path), _stat.S_IWRITE)\n",
     [node("rec-readonly-symlink-itself"), node("rec-readonly-symlink-to-readonly-external-file")]),
    ("acl-denial-swallowed",
     "    except PermissionError:\n        if not _clear_readonly(path):\n            raise\n",
     "    except PermissionError:\n        if not _clear_readonly(path):\n            return\n",
     [node("rec-acl-denied-target-file"), node("nonrec-acl-denied-target-file")]),
]


def pytest(python: str, cwd: Path, env: dict[str, str], basetemp: Path, nodes: list[str], *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [python, "-m", "pytest", "--no-cov", "-p", "no:cacheprovider", "--runxfail", "-q", "--basetemp", str(basetemp), *extra, *nodes],
        cwd=cwd, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )


def main() -> int:
    python, source, scratch = sys.argv[1], Path(sys.argv[2]).resolve(), Path(sys.argv[3]).resolve()
    if os.name == "nt" and scratch.drive.upper() != "E:":
        raise SystemExit("scratch must stay on E:")
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="l12d005-controls-", dir=scratch) as directory:
        root = Path(directory)
        copy = root / "minion-agent-python"
        shutil.copytree(source, copy, ignore=shutil.ignore_patterns(".venv", "__pycache__", ".pytest_cache"))
        shutil.copytree(source.parent / "conformance", root / "conformance")
        shutil.copy2(source.parent / "pi-parity-manifest.yaml", root / "pi-parity-manifest.yaml")
        env = {**os.environ, "PYTHONPATH": "src;." if os.name == "nt" else "src:.", "PYTHONIOENCODING": "utf-8", "TMP": str(root), "TEMP": str(root)}
        env.pop("PYTEST_ADDOPTS", None)
        witnesses = sorted({n for c in CONTROLS for n in c[3]})
        baseline = pytest(python, copy, env, root / "bt-baseline", witnesses, "-rA")
        (scratch / "baseline.log").write_text(baseline.stdout + baseline.stderr, encoding="utf-8")
        passed = {line.split()[1] for line in baseline.stdout.splitlines() if line.startswith("PASSED")}
        missing = [w for w in witnesses if w not in passed]
        if baseline.returncode != 0 or missing or "XPASS" in baseline.stdout:
            print(f"INVALID  baseline: exit {baseline.returncode}; not selected/green: {missing}")
            return 1
        print(f"BASELINE {len(passed)} intended witnesses selected and PASS")
        fs_path = copy / FS
        original = fs_path.read_text(encoding="utf-8")
        failures = 0
        for name, old, new, nodes in CONTROLS:
            if original.count(old) != 1:
                print(f"INVALID  {name}: anchor count {original.count(old)}")
                failures += 1
                continue
            fs_path.write_text(original.replace(old, new), encoding="utf-8")
            try:
                imported = subprocess.run([python, "-c", "import minion_agent.execution"], cwd=copy, env=env, capture_output=True)
                if imported.returncode != 0:
                    print(f"INVALID  {name}: mutant does not import")
                    failures += 1
                    continue
                run = pytest(python, copy, env, root / f"bt-{name}", nodes, "-rfE")
            finally:
                fs_path.write_text(original, encoding="utf-8")
            out = run.stdout + run.stderr
            (scratch / f"{name}.log").write_text(out, encoding="utf-8")
            failed = [line.split()[1] for line in run.stdout.splitlines() if line.startswith("FAILED")]
            summary = run.stdout.strip().splitlines()[-1] if run.stdout.strip() else ""
            if run.returncode == 0:
                print(f"SURVIVED {name}")
                failures += 1
            elif (run.returncode == 1 and " error" not in summary and "XPASS" not in out
                  and any(s in out for s in SIGNATURES) and set(failed) == set(nodes)):
                print(f"KILLED   {name} ({len(failed)} intended witnesses failed)")
            else:
                print(f"INVALID  {name}: exit {run.returncode}; failed={failed}; summary={summary!r}")
                failures += 1
        return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
