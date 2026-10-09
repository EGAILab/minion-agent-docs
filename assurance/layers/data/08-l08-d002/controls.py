"""L08-D002 kill controls over the Python driver: each mutant edits a disposable copy of
agent_loop/driver.py; the request-header canonical scenarios must fail. Run from a copy's
minion-agent-python/ with: python controls.py <python> <basetemp>.

Anchors start at a line start; every mutant must change the source and compile; only pytest exit
status 0 (survived) or 1 (killed) counts -- anything else is INVALID and fails the run."""

import os
import pathlib
import py_compile
import subprocess
import sys

PY, BASETEMP = sys.argv[1], sys.argv[2]
DRIVER = pathlib.Path("src/minion_agent/agent_loop/driver.py")
ORIGINAL = DRIVER.read_text(encoding="utf-8")
TESTS = ["tests/conformance/test_agent_conformance.py", "-k", "request-header"]

RECORD = (
    "\n        record_header(\n"
    "            log,\n"
    "            self.artifacts,\n"
    "            components,\n"
    "            model=config.model.model,\n"
    "            tools=schemas,\n"
    "        )\n"
)
TRANSFORM = "\n        transformed_history = await self._transform_context(tuple(history))\n"
COMPONENTS = '\n        components = {"system_base": self._system_text(decision, context)}\n'
SENT = "\n            tools=schemas,\n            signal=self.instance.signal,\n"

MUTANTS = {
    "header after transformContext": [
        (RECORD, "\n"),
        (TRANSFORM, TRANSFORM + RECORD.replace("\n        ", "\n        ", 1)),
    ],
    "no header": [(RECORD, "\n")],
    "duplicate header": [(RECORD, RECORD + RECORD.lstrip("\n"))],
    "stored prompt instead of the override": [
        (COMPONENTS, '\n        components = {"system_base": context.system_prompt}\n')
    ],
    "provider-qualified model": [
        (RECORD, RECORD.replace("model=config.model.model", 'model=f"{config.model.provider}/{config.model.model}"'))
    ],
    # Remediation 1 (L08D002-R001): the header must carry the complete schemas the request sent.
    "header-only schema corruption (Codex R001 control)": [
        (RECORD, RECORD.replace(
            "tools=schemas,",
            'tools=tuple(type(s)(name=s.name, description="CORRUPTED HEADER", parameters={"type": "null"}) '
            "for s in schemas),"))
    ],
    "header drops constrained_sampling": [
        (RECORD, RECORD.replace(
            "tools=schemas,",
            "tools=tuple(type(s)(name=s.name, description=s.description, parameters=s.parameters) for s in schemas),"))
    ],
    "request tools reordered": [(SENT, SENT.replace("tools=schemas,", "tools=schemas[::-1],"))],
}

results: dict[str, list[str] | str] = {}
for label, edits in MUTANTS.items():
    text = ORIGINAL
    for old, new in edits:
        assert text.count(old) == 1, f"{label}: anchor not found exactly once: {old[:50]!r}"
        text = text.replace(old, new)
    assert text != ORIGINAL, f"{label}: mutant did not change the source"
    DRIVER.write_text(text, encoding="utf-8")
    try:
        try:
            py_compile.compile(str(DRIVER), doraise=True)
        except py_compile.PyCompileError as error:
            results[label] = f"INVALID (does not compile: {error.msg.strip().splitlines()[-1]})"
            continue
        run = subprocess.run(
            [PY, "-m", "pytest", "-p", "no:cacheprovider", "--no-cov", "-q",
             f"--basetemp={BASETEMP}/{abs(hash(label))}", *TESTS],
            capture_output=True, text=True, env={**os.environ, "PYTHONPATH": "src"},
        )
        if run.returncode not in (0, 1):
            results[label] = f"INVALID (pytest exit status {run.returncode})"
            continue
        results[label] = [
            line.split("[", 1)[1].split("]", 1)[0] for line in run.stdout.splitlines() if line.startswith("FAILED")
        ]
    finally:
        DRIVER.write_text(ORIGINAL, encoding="utf-8")

ok = True
for label, outcome in results.items():
    if isinstance(outcome, str):
        print("INVALID ", label, "->", outcome)
        ok = False
    elif outcome:
        print("KILLED  ", label, "->", outcome)
    else:
        print("SURVIVED", label, "-> []")
        ok = False
sys.exit(0 if ok else 1)
