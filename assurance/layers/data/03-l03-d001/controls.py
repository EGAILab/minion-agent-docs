"""L03-D001 negative controls: each mutant edits one disposable copy of `minion-agent-python`.

Usage (Windows needs the scratch directory on E:):
    python controls.py PYTHON_EXE MINION_AGENT_PYTHON_DIR SCRATCH_DIR [--contract-stage] [--only NAME]

MINION_AGENT_PYTHON_DIR must contain the L03-D001 correction:
- contract stage: a scratch copy of the contract candidate with the planned correction applied to
  `src/minion_agent/session/request_header.py` (the candidate keeps its strict xfail markers; nothing else
  changes). The record (section 9) gives the exact recipe.
- implementation stage: the implementation candidate itself.

Every pytest run passes `--runxfail`, so a pending `xfail(strict=True)` marker can neither hide a witness
failure nor turn a green baseline into a strict XPASS (`L03D001-R001`).

Validity, per control (workflow 9.7):
1. Positive baseline: before any mutant, the control's witnesses must pass unmutated (exit 0, no error).
2. The anchor matches exactly once, and the mutant imports.
3. KILLED only when pytest exits 1, reports failures and no errors, never XPASS, and the output contains the
   control's intended-failure signature -- the witness's own assertion (or the exception the mutant must
   cause). Exit 0 is SURVIVED. Anything else -- another exit status, a collection/setup/import error, or a
   failure without the signature -- is INVALID.
The script exits non-zero unless every selected control is KILLED.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HEADER = "src/minion_agent/session/request_header.py"
CANONICAL = "tests/conformance/test_session_conformance.py"
STATES = CANONICAL + "::test_session_scenario[request-header-tools-constrained-sampling-states]"
FALSE_CASE = CANONICAL + "::test_session_scenario[request-header-tools-sampling-false-is-not-absent]"
CANONICAL_ASSERT = 'assert outcome["reconstructed_header"] == document["expect_reconstructed_header"]'
UNIT = "tests/session/test_request_header_tools.py"
INTEGRATION = "tests/agent_loop/test_request_tools.py"
DECODE = '            constrained_sampling=_constrained_sampling(entry.get("constrained_sampling")),\n'
PASSTHROUGH = "    if value is None or value is False:\n        return value\n"

# (name, old, new, witness node ids, intended-failure signature, implementation stage only)
CONTROLS = [
    ("field-dropped", DECODE, "", [STATES], CANONICAL_ASSERT, False),
    ("false-read-as-absent", PASSTHROUGH, "    if value is None or value is False:\n        return None\n",
     [FALSE_CASE], CANONICAL_ASSERT, False),
    ("absent-read-as-false", PASSTHROUGH, "    if value is None or value is False:\n        return False\n",
     [STATES], CANONICAL_ASSERT, False),
    ("strict-prefer-replaced", '                return JsonSchemaConstrainedSampling(strict="prefer")\n',
     '                return JsonSchemaConstrainedSampling(strict="require")\n', [STATES], CANONICAL_ASSERT, False),
    ("grammar-formats-swapped", '                    openai_lark=variants.get("openai_lark"),\n',
     '                    openai_lark=variants.get("openai_regex"),\n', [STATES], CANONICAL_ASSERT, False),
    ("grammar-format-dropped", '                    openai_regex=variants.get("openai_regex"),\n',
     "                    openai_regex=None,\n", [STATES], CANONICAL_ASSERT, False),
    ("tool-order-reversed", "        for entry in raw\n    )\n", "        for entry in reversed(raw)\n    )\n",
     [STATES], CANONICAL_ASSERT, False),
    ("historical-entry-rejected", '_constrained_sampling(entry.get("constrained_sampling"))',
     '_constrained_sampling(entry["constrained_sampling"])',
     [UNIT + "::test_a_header_stored_without_the_field_reconstructs_it_as_absent"],
     "KeyError: 'constrained_sampling'", True),
    ("malformed-read-as-absent",
     '    raise ValueError(f"stored constrained_sampling is not a certified state: {value!r}")\n',
     "    return None\n",
     [UNIT + "::test_a_stored_value_outside_the_four_states_fails_reconstruction"], "DID NOT RAISE", True),
    ("request-witness-blind", DECODE, "",
     [INTEGRATION + "::test_the_logged_header_reconstructs_every_sampling_state_dispatched"],
     "assert reconstruct_tools(", True),
]


def _pytest(python: Path, cwd: Path, env: dict[str, str], basetemp: Path, nodes: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(python), "-m", "pytest", "--no-cov", "-p", "no:cacheprovider", "--runxfail", "-rfE",
         "--basetemp", str(basetemp), *nodes],
        cwd=cwd, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )


def _summary(output: str) -> str:
    lines = [line for line in output.splitlines() if line.strip()]
    return lines[-1] if lines else ""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("python", type=Path)
    parser.add_argument("source", type=Path)
    parser.add_argument("scratch", type=Path)
    parser.add_argument("--only")
    parser.add_argument("--contract-stage", action="store_true",
                        help="skip controls whose witness exists only in the implementation candidate")
    args = parser.parse_args()
    scratch = args.scratch.resolve()
    if os.name == "nt" and scratch.drive.upper() != "E:":
        raise SystemExit("scratch must stay on E:")
    scratch.mkdir(parents=True, exist_ok=True)
    source = args.source.resolve()
    selected = [c for c in CONTROLS if (not args.only or c[0] == args.only)]
    failures = 0
    with tempfile.TemporaryDirectory(prefix="l03d001-controls-", dir=scratch) as directory:
        root = Path(directory)
        python_dir = root / "minion-agent-python"
        shutil.copytree(source, python_dir, ignore=shutil.ignore_patterns(".venv", "__pycache__", ".pytest_cache"))
        shutil.copytree(source.parent / "conformance", root / "conformance")
        shutil.copy2(source.parent / "pi-parity-manifest.yaml", root / "pi-parity-manifest.yaml")
        env = {**os.environ, "PYTHONPATH": "src", "PYTHONIOENCODING": "utf-8", "TMP": str(root), "TEMP": str(root)}
        env.pop("PYTEST_ADDOPTS", None)
        active = [c for c in selected if not (c[5] and args.contract_stage)]
        for control in selected:
            if control not in active:
                print(f"DEFERRED {control[0]}: implementation-stage witness", flush=True)
        witnesses = sorted({node for control in active for node in control[3]})
        baseline = _pytest(args.python, python_dir, env, root / "bt-baseline", witnesses)
        (scratch / "baseline.log").write_text(baseline.stdout + baseline.stderr, encoding="utf-8")
        if baseline.returncode != 0 or " error" in _summary(baseline.stdout) or "XPASS" in baseline.stdout:
            print(f"INVALID  baseline: witnesses not green unmutated ({_summary(baseline.stdout)})", flush=True)
            return 1
        print(f"BASELINE {_summary(baseline.stdout)}", flush=True)
        header = python_dir / HEADER
        original = header.read_text(encoding="utf-8")
        for name, old, new, nodes, signature, _ in active:
            if original.count(old) != 1:
                print(f"INVALID  {name}: anchor count {original.count(old)}", flush=True)
                failures += 1
                continue
            header.write_text(original.replace(old, new), encoding="utf-8")
            try:
                imported = subprocess.run([str(args.python), "-c", "import minion_agent.session"], cwd=python_dir,
                                          env=env, capture_output=True, text=True)
                if imported.returncode != 0:
                    print(f"INVALID  {name}: mutant does not import", flush=True)
                    failures += 1
                    continue
                run = _pytest(args.python, python_dir, env, root / f"bt-{name}", nodes)
            finally:
                header.write_text(original, encoding="utf-8")
            output = run.stdout + run.stderr
            (scratch / f"{name}.log").write_text(output, encoding="utf-8")
            summary = _summary(run.stdout)
            if run.returncode == 0:
                print(f"SURVIVED {name}", flush=True)
                failures += 1
            elif (run.returncode == 1 and "failed" in summary and " error" not in summary
                  and "XPASS" not in output and signature in output):
                print(f"KILLED   {name} ({summary})", flush=True)
            else:
                print(f"INVALID  {name}: exit {run.returncode}, {summary!r}, signature found: {signature in output}",
                      flush=True)
                failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
