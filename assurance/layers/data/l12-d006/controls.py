"""L12-D006 negative controls (minion-agent#194): each mutant edits one disposable copy of
`minion-agent-python` that carries the L12-D006 correction, and must be killed by its intended
witnesses (process section 9.7). These are the Owner's required controls, in their Python form:
an escaped ValueError, an `invalid` code, premature path validation, logical-path fallback
corruption, and catching every ValueError (Python's analogue of a global InvalidInput remap).

Usage (Windows scratch on E:, or Linux):
    python controls.py PYTHON_EXE MINION_AGENT_PYTHON_DIR SCRATCH_DIR

MINION_AGENT_PYTHON_DIR must contain the correction:
- contract stage: a scratch copy of the contract candidate with gen/planned_fix.py applied (the
  strict xfail markers stay; every run passes --runxfail and clears PYTEST_ADDOPTS);
- implementation stage: the implementation candidate itself.

A control lists the platforms where its witnesses can observe it. Elsewhere it is reported as
NOT RUN, never as killed. The canonical_path whole-argument check is observable on Linux only:
the Windows realpath rejects the NUL itself.

Validity: before any mutant, every intended witness of the active controls must be selected and
PASS unmutated (-rA). A kill needs pytest exit 1, failures without errors, no XPASS, exactly the
intended witnesses failing, and an intended assertion in the output. Exit 0 is SURVIVED; anything
else is INVALID. Non-zero exit unless every active control is KILLED.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

FS = "src/minion_agent/execution/filesystem.py"
CANON = "tests/conformance/test_fs_path_conformance.py::test_fs_path_domain_case"
BINDING = "tests/execution/test_filesystem_nul.py::"
SIGNATURES = ("assert got == want", "assert isinstance(result, Err)", "assert result.error",
              "assert await _tool", "DID NOT RAISE", "ValueError",
              "TypeError: LocalFileSystem.")  # L12D006-I001: a call form the wrapper rejects
PLATFORM = "win32" if sys.platform == "win32" else "linux"
BOTH = ("win32", "linux")


def node(case_id: str) -> str:
    return f"{CANON}[{case_id}]"


# (name, file, old, new, intended witnesses, platforms)
CONTROLS_ALL = [
    ("nul-value-error-escapes", FS,
     "            if not _nul_rejected(exc, *resolved):\n                raise\n",
     "            raise\n",
     [node("nul/middle/read_text_file"), node("nul/middle/file_info")], BOTH),
    ("nul-mapped-to-invalid", FS,
     "    return FsError(FsErrorCode.UNKNOWN, str(exc), logical, exc)\n",
     "    return FsError(FsErrorCode.INVALID, str(exc), logical, exc)\n",
     [node("nul/middle/read_text_file"), node("nul/middle/file_info")], BOTH),
    ("premature-nul-validation", FS,
     "        try:\n            return await method(*args, **kwargs)\n",
     "        early = signature.bind(*args, **kwargs).arguments\n"
     "        if _NUL in str(early.get(\"path\", \"\")):\n"
     "            return Err(_nul_failure(ValueError(\"embedded null\"), resolve_local_path(early[\"self\"].cwd, early[\"path\"])))\n"
     "        try:\n            return await method(*args, **kwargs)\n",
     [node("nul/under-new-parent/write_file"), node("nul/middle/read_text_lines-max0"),
      node("nul/aborted/read_text_file")], BOTH),
    ("projected-fallback-path", FS,
     "            return Err(_nul_failure(exc, logical))\n",
     "            return Err(_nul_failure(exc, native_path(logical)))\n",
     [node("nul/lone-surrogate-and-nul/read_text_file")], BOTH),
    ("rename-names-the-destination", FS,
     "            return Err(_nul_failure(exc, logical))\n",
     "            return Err(_nul_failure(exc, resolved[-1]))\n",
     [node("nul/middle/rename_file-destination")], BOTH),
    ("every-value-error-contained", FS,
     '    return "embedded null" in str(exc) and any(\n',
     "    return True or any(\n",
     [BINDING + "test_an_unrelated_value_error_still_raises"], BOTH),
    # L12D006-C001: containment that tests the caller's RAW arguments misses a `file://` URL whose
    # `%00` decodes to the NUL the native call rejects.
    ("argument-only-containment", FS,
     "            if not _nul_rejected(exc, *resolved):\n",
     "            if not _nul_rejected(exc, path, *args, *kwargs.values()):\n",
     [node("nul/url-final/read_text_file"), node("nul/url-final/exists"),
      node("nul/url-control/rename_file-to-url-nul")], BOTH),
    # L12D006-I001: a wrapper that takes the path positionally only breaks every keyword call.
    ("positional-only-wrapper", FS,
     "    async def contained(*args: P.args, **kwargs: P.kwargs) -> Result[T, FsError]:\n"
     "        try:\n            return await method(*args, **kwargs)\n",
     "    async def contained(self: Any, path: str, /, *args: Any, **kwargs: Any) -> Any:\n"
     "        args = (self, path, *args)\n"
     "        try:\n            return await method(*args, **kwargs)\n",
     [BINDING + "test_a_keyword_call_behaves_exactly_like_the_positional_call[read_text_file]",
      BINDING + "test_a_keyword_call_behaves_exactly_like_the_positional_call[rename_file]"], BOTH),
    ("canonical-path-walks-first", FS,
     "        if _NUL in resolved:\n            return Err(_nul_failure(ValueError(\"embedded null character in path\"), resolved))\n",
     "",
     [node("nul/under-new-parent/canonical_path")], ("linux",)),
]
ACTIVE = [c[:5] for c in CONTROLS_ALL if PLATFORM in c[5]]
for c in CONTROLS_ALL:
    if PLATFORM not in c[5]:
        print(f"NOT RUN  {c[0]} (observable on {', '.join(c[5])} only)")


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
    with tempfile.TemporaryDirectory(prefix="l12d006-controls-", dir=scratch) as directory:
        root = Path(directory)
        copy = root / "minion-agent-python"
        shutil.copytree(source, copy, ignore=shutil.ignore_patterns(".venv", "__pycache__", ".pytest_cache"))
        shutil.copytree(source.parent / "conformance", root / "conformance")
        shutil.copy2(source.parent / "pi-parity-manifest.yaml", root / "pi-parity-manifest.yaml")
        env = {**os.environ, "PYTHONPATH": "src;." if os.name == "nt" else "src:.", "PYTHONIOENCODING": "utf-8", "TMP": str(root), "TEMP": str(root)}
        env.pop("PYTEST_ADDOPTS", None)
        witnesses = sorted({n for c in ACTIVE for n in c[4]})
        baseline = pytest(python, copy, env, root / "bt-baseline", witnesses, "-rA")
        (scratch / "baseline.log").write_text(baseline.stdout + baseline.stderr, encoding="utf-8")
        passed = {line.split()[1] for line in baseline.stdout.splitlines() if line.startswith("PASSED")}
        missing = [w for w in witnesses if w not in passed]
        if baseline.returncode != 0 or missing or "XPASS" in baseline.stdout:
            print(f"INVALID  baseline: exit {baseline.returncode}; not selected/green: {missing}")
            return 1
        print(f"BASELINE {len(passed)} intended witnesses selected and PASS")
        failures = 0
        for name, relative, old, new, nodes in ACTIVE:
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
