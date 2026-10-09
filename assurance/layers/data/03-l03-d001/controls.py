"""L03-D001 negative controls: each mutant edits one disposable copy of `minion-agent-python`.

Every mutant must change the source, compile, and be killed by its intended witness: the pytest run of
that witness exits 1. Exit 0 means the mutant SURVIVED; any other exit, an anchor that does not match
exactly once, or a mutant that does not import, is INVALID. The script exits non-zero unless every
control is KILLED.

Usage (from anywhere; Windows needs the scratch directory on E:):
    python controls.py PYTHON_EXE MINION_AGENT_PYTHON_DIR SCRATCH_DIR [--only NAME]

MINION_AGENT_PYTHON_DIR must contain the L03-D001 correction. At the contract stage that is a scratch
copy with the planned correction applied; at the implementation stage it is the candidate itself.
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
UNIT = "tests/session/test_request_header_tools.py"
INTEGRATION = "tests/agent_loop/test_request_tools.py"

# (name, file, old, new, witness node ids, implementation-stage only)
CONTROLS = [
    ("field-dropped", HEADER,
     "            constrained_sampling=_constrained_sampling(entry.get(\"constrained_sampling\")),\n",
     "",
     [STATES], False),
    ("false-read-as-absent", HEADER,
     "    if value is None or value is False:\n        return value\n",
     "    if value is None or value is False:\n        return None\n",
     [FALSE_CASE], False),
    ("absent-read-as-false", HEADER,
     "    if value is None or value is False:\n        return value\n",
     "    if value is None or value is False:\n        return False\n",
     [STATES], False),
    ("strict-prefer-replaced", HEADER,
     "                return JsonSchemaConstrainedSampling(strict=\"prefer\")\n",
     "                return JsonSchemaConstrainedSampling(strict=\"require\")\n",
     [STATES], False),
    ("grammar-formats-swapped", HEADER,
     "                    openai_lark=variants.get(\"openai_lark\"),\n",
     "                    openai_lark=variants.get(\"openai_regex\"),\n",
     [STATES], False),
    ("grammar-format-dropped", HEADER,
     "                    openai_regex=variants.get(\"openai_regex\"),\n",
     "                    openai_regex=None,\n",
     [STATES], False),
    ("tool-order-reversed", HEADER,
     "        for entry in raw\n    )\n",
     "        for entry in reversed(raw)\n    )\n",
     [STATES], False),
    ("historical-entry-rejected", HEADER,
     "_constrained_sampling(entry.get(\"constrained_sampling\"))",
     "_constrained_sampling(entry[\"constrained_sampling\"])",
     [UNIT + "::test_a_header_stored_without_the_field_reconstructs_it_as_absent"], True),
    ("malformed-read-as-absent", HEADER,
     "    raise ValueError(f\"stored constrained_sampling is not a certified state: {value!r}\")\n",
     "    return None\n",
     [UNIT + "::test_a_stored_value_outside_the_four_states_fails_reconstruction"], True),
    ("request-witness-blind", HEADER,
     "            constrained_sampling=_constrained_sampling(entry.get(\"constrained_sampling\")),\n",
     "",
     [INTEGRATION + "::test_the_logged_header_reconstructs_every_sampling_state_dispatched"], True),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("python", type=Path)
    parser.add_argument("source", type=Path)
    parser.add_argument("scratch", type=Path)
    parser.add_argument("--only")
    parser.add_argument("--contract-stage", action="store_true",
                        help="skip controls whose witness only exists in the implementation candidate")
    args = parser.parse_args()
    scratch = args.scratch.resolve()
    if os.name == "nt" and scratch.drive.upper() != "E:":
        raise SystemExit("scratch must stay on E:")
    scratch.mkdir(parents=True, exist_ok=True)
    source = args.source.resolve()
    failures = 0
    with tempfile.TemporaryDirectory(prefix="l03d001-controls-", dir=scratch) as directory:
        root = Path(directory)
        python_dir = root / "minion-agent-python"
        shutil.copytree(source, python_dir, ignore=shutil.ignore_patterns(".venv", "__pycache__", ".pytest_cache"))
        shutil.copytree(source.parent / "conformance", root / "conformance")
        shutil.copy2(source.parent / "pi-parity-manifest.yaml", root / "pi-parity-manifest.yaml")
        env = {**os.environ, "PYTHONPATH": "src", "PYTHONIOENCODING": "utf-8", "TMP": str(root), "TEMP": str(root)}
        for name, filename, old, new, witnesses, implementation_only in CONTROLS:
            if args.only and name != args.only:
                continue
            if implementation_only and args.contract_stage:
                print(f"DEFERRED {name}: implementation-stage witness", flush=True)
                continue
            path = python_dir / filename
            original = path.read_text(encoding="utf-8")
            if original.count(old) != 1:
                print(f"INVALID  {name}: anchor count {original.count(old)}", flush=True)
                failures += 1
                continue
            mutated = original.replace(old, new)
            path.write_text(mutated, encoding="utf-8")
            try:
                compiled = subprocess.run([str(args.python), "-c", "import minion_agent.session"], cwd=python_dir,
                                          env=env, capture_output=True, text=True)
                if compiled.returncode != 0:
                    print(f"INVALID  {name}: mutant does not import", flush=True)
                    failures += 1
                    continue
                run = subprocess.run(
                    [str(args.python), "-m", "pytest", "--no-cov", "-q", "-p", "no:cacheprovider",
                     "--basetemp", str(root / f"bt-{name}"), *witnesses],
                    cwd=python_dir, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace",
                )
            finally:
                path.write_text(original, encoding="utf-8")
            (scratch / f"{name}.log").write_text(run.stdout + run.stderr, encoding="utf-8")
            if run.returncode == 1:
                print(f"KILLED   {name}", flush=True)
            elif run.returncode == 0:
                print(f"SURVIVED {name}", flush=True)
                failures += 1
            else:
                print(f"INVALID  {name}: pytest exit {run.returncode}", flush=True)
                failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
