"""L08-D002 kill controls over the Python driver: each mutant edits a disposable copy of
agent_loop/driver.py; the request-header canonical scenarios must fail. Run from a copy's
minion-agent-python/ with: python controls.py <python> <basetemp>.

Anchors start at a line start; every mutant must change the source and compile.

Validity (remediation 1, carrying over the L03D001-R001 lesson):
- before any mutant, the selected witnesses must all pass unmutated (positive baseline), and every mutant's
  intended case must be among the PASSED nodes -- proving it was selected at all -- else the run stops;
- KILLED needs pytest exit 1, no ERROR line and no XPASS, and every one of the mutant's INTENDED cases among
  the failures; exit 0 is SURVIVED; anything else (another exit status, an error, or failures that miss an
  intended case) is INVALID. The run exits non-zero unless every mutant is KILLED."""

import os
import pathlib
import py_compile
import subprocess
import sys

PY, BASETEMP = sys.argv[1], sys.argv[2]
DRIVER = pathlib.Path("src/minion_agent/agent_loop/driver.py")
ORIGINAL = DRIVER.read_text(encoding="utf-8")
TESTS = ["tests/conformance/test_agent_conformance.py", "-k", "request-header or request_schema_snapshot"]

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
SNAPSHOT = "\n        schemas = tuple(_schema_snapshot(definition.schema()) for definition in context.tools)\n"
SNAPSHOT_WITNESS = "tests/agent_loop/test_request_schema_snapshot.py"

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
    # Implementation stage (L08D002-R003): the request's schemas alias application state again.
    "no value snapshot": [
        (SNAPSHOT, SNAPSHOT.replace("_schema_snapshot(definition.schema())", "definition.schema()"))
    ],
}

# The case(s) each mutant must fail, at minimum.
INTENDED = {
    "header after transformContext": {"request-header-transform-failure-first-request",
                                      "request-header-transform-failure-later-request"},
    "no header": {"request-header-single-request"},
    "duplicate header": {"request-header-single-request"},
    "stored prompt instead of the override": {"request-header-records-the-literal-override"},
    "provider-qualified model": {"request-header-single-request"},
    "header-only schema corruption (Codex R001 control)": {"request-header-full-schema-identity",
                                                           "request-header-one-per-request-in-order"},
    "header drops constrained_sampling": {"request-header-full-schema-identity"},
    "request tools reordered": {"request-header-full-schema-identity"},
    "no value snapshot": {"test_a_transform_time_mutation_reaches_neither_the_published_header_nor_its_request"},
}
assert set(INTENDED) == set(MUTANTS)


def _run(tag: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [PY, "-m", "pytest", "-p", "no:cacheprovider", "--no-cov", "-q", "-rfEX",
         f"--basetemp={BASETEMP}/{tag}", *TESTS, SNAPSHOT_WITNESS],
        capture_output=True, text=True, env={**os.environ, "PYTHONPATH": "src"},
    )


baseline = subprocess.run(
    [PY, "-m", "pytest", "-p", "no:cacheprovider", "--no-cov", "-q", "-rA",
     f"--basetemp={BASETEMP}/baseline", *TESTS, SNAPSHOT_WITNESS],
    capture_output=True, text=True, env={**os.environ, "PYTHONPATH": "src"},
)
passed = [line.split()[1] for line in baseline.stdout.splitlines() if line.startswith("PASSED")]
unselected = sorted(
    case for cases in INTENDED.values() for case in cases if not any(case in node for node in passed)
)
if baseline.returncode != 0 or "ERROR" in baseline.stdout or "XPASS" in baseline.stdout or unselected:
    # An intended witness that did not run and pass unmutated can never kill its mutant: a
    # selection mistake would otherwise read as a survivor, or worse, as a kill by another case.
    print("INVALID  baseline: not green unmutated, or intended witnesses not selected:", unselected)
    print(baseline.stdout[-2000:])
    sys.exit(1)
print(f"BASELINE {len(passed)} passed; every intended witness selected and green")

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
        run = _run(str(abs(hash(label))))
        if run.returncode not in (0, 1) or "ERROR" in run.stdout or "XPASS" in run.stdout:
            results[label] = f"INVALID (pytest exit status {run.returncode}, or an error/XPASS)"
            continue
        failed = [line.split()[1] for line in run.stdout.splitlines() if line.startswith("FAILED")]
        missing = {case for case in INTENDED[label] if not any(case in node for node in failed)}
        results[label] = f"INVALID (intended case(s) not failed: {sorted(missing)})" if failed and missing else failed
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
