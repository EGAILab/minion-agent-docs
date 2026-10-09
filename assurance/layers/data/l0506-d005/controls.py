"""L0506-D005 negative controls (minion-agent#129): each mutant edits one disposable copy of
`minion-agent-python` that carries the L0506-D005 correction, and must be killed by its intended
canonical witness (process section 9.7).

Usage (Windows; scratch on E:):
    python controls.py PYTHON_EXE MINION_AGENT_PYTHON_DIR SCRATCH_DIR

MINION_AGENT_PYTHON_DIR must contain the correction:
- contract stage: a scratch copy of the contract candidate with gen/planned_fix.py applied (the
  candidate's strict xfail markers stay; every run passes --runxfail and clears PYTEST_ADDOPTS);
- implementation stage: the implementation candidate itself (anchors re-pointed if its code differs).

Validity: before any mutant, every intended witness must be selected and PASS unmutated (-rA PASSED
lines). A kill needs pytest exit 1, failures without errors, no XPASS, exactly the intended witnesses
failing, and a canonical assertion `assert observed[...] == expect[...]` in the output. Exit 0 is
SURVIVED; anything else is INVALID. Non-zero exit unless all are KILLED.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

EXECUTE = "src/minion_agent/tools/execute.py"
JS_OBJECT = "src/minion_agent/llm/js_object.py"
TEST = "tests/conformance/test_arg_isolation_conformance.py::test_arg_isolation_case"
SIGNATURES = tuple(
    f'assert observed["{key}"] == expect["{key}"]'
    for key in ("outcome", "hook_entries", "facts", "execute", "updates", "raw_after")
)


def node(name: str) -> str:
    return f"{TEST}[arg-isolation-{name}]"


# (name, file, old, new, intended witnesses)
CONTROLS = [
    ("shallow-copy-restored", EXECUTE,
     "        validated: dict[str, Any] = structured_clone(arguments)\n",
     "        validated: dict[str, Any] = order_in_place(JsObject(arguments))\n",
     [node("hook-sets-into-nested-object"), node("hook-pushes-object-into-nested-array")]),
    ("clone-forgets-aliases", JS_OBJECT,
     "                if id(child) not in memo:\n",
     "                if id(child) not in memo or child is not value:\n",
     [node("prepared-alias-stays-shared-in-clone")]),
    ("clone-keeps-pipeline-containers", JS_OBJECT,
     "            if isinstance(child, (dict, list)):\n",
     "            if isinstance(child, (dict, list)) and not isinstance(child, (JsObject, JsArray)):\n",
     [node("prepared-reused-raw-child-is-isolated"), node("hook-sets-into-nested-object")]),
    ("clone-per-listener", EXECUTE,
     "        order_in_place(current[2])\n        return (*current[:3], signal)\n",
     "        return (current[0], current[1], structured_clone(current[2]), signal)\n",
     [node("two-hooks-share-the-validated-graph")]),
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
    with tempfile.TemporaryDirectory(prefix="l0506d005-controls-", dir=scratch) as directory:
        root = Path(directory)
        copy = root / "minion-agent-python"
        shutil.copytree(source, copy, ignore=shutil.ignore_patterns(".venv", "__pycache__", ".pytest_cache"))
        shutil.copytree(source.parent / "conformance", root / "conformance")
        shutil.copy2(source.parent / "pi-parity-manifest.yaml", root / "pi-parity-manifest.yaml")
        env = {**os.environ, "PYTHONPATH": "src;." if os.name == "nt" else "src:.", "PYTHONIOENCODING": "utf-8", "TMP": str(root), "TEMP": str(root)}
        env.pop("PYTEST_ADDOPTS", None)
        witnesses = sorted({n for c in CONTROLS for n in c[4]})
        baseline = pytest(python, copy, env, root / "bt-baseline", witnesses, "-rA")
        (scratch / "baseline.log").write_text(baseline.stdout + baseline.stderr, encoding="utf-8")
        passed = {line.split()[1] for line in baseline.stdout.splitlines() if line.startswith("PASSED")}
        missing = [w for w in witnesses if w not in passed]
        if baseline.returncode != 0 or missing or "XPASS" in baseline.stdout:
            print(f"INVALID  baseline: exit {baseline.returncode}; not selected/green: {missing}")
            return 1
        print(f"BASELINE {len(passed)} intended witnesses selected and PASS")
        failures = 0
        for name, relative, old, new, nodes in CONTROLS:
            fs_path = copy / relative
            original = fs_path.read_text(encoding="utf-8")
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
