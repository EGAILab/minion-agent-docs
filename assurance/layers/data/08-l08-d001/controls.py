"""L08-D001 kill controls: each mutant edits a disposable copy of driver.py; the witness suite must
fail. Run from a copy's minion-agent-python/ with: python controls.py <python> <basetemp>.

Every anchor starts at a line start (a leading newline), so a match can never land on a suffix of
a more-indented line (L08D001-R002). Every mutant must compile and must change the source; a mutant
that does not is reported INVALID and fails the run -- a syntax or collection failure is never
counted as a kill."""

import os
import pathlib
import py_compile
import subprocess
import sys

PY, BASETEMP = sys.argv[1], sys.argv[2]
DRIVER = pathlib.Path("src/minion_agent/agent_loop/driver.py")
ORIGINAL = DRIVER.read_text(encoding="utf-8")

CALL = "self.prompt_assembler(context.system_prompt, context.tools)"
ASSEMBLE = f"\n            text = {CALL}\n"
OVERRIDE = (
    "\n        if decision.system_override is not None:\n"
    "            return decision.system_override\n"
    "        if self.prompt_assembler is None:\n"
)
HEADER_BLOCK = '\n        components = {"system_base": self._system_text(decision, context)}\n'

MUTANTS = {
    "live-registry assembly": [
        (
            ASSEMBLE,
            "\n            text = self.prompt_assembler("
            "context.system_prompt, self.tools.visible_from(self.instance.scope))\n",
        )
    ],
    "reversed snapshot order": [
        (
            ASSEMBLE,
            "\n            text = self.prompt_assembler("
            "context.system_prompt, tuple(reversed(context.tools)))\n",
        )
    ],
    "override reassembled": [
        (
            OVERRIDE,
            "\n        if decision.system_override is not None and self.prompt_assembler is None:\n"
            "            return decision.system_override\n"
            "        if self.prompt_assembler is None:\n",
        )
    ],
    # reuse the first non-empty assembled text on later requests; error-origin handling unchanged
    "stale assembled text (first request only)": [
        (
            ASSEMBLE,
            f"\n            text = getattr(self, '_stale', None) or {CALL}\n"
            "            self._stale = text\n",
        )
    ],
    "header published before assembly": [
        (
            HEADER_BLOCK,
            "\n        record_header(self.instance.log, self.artifacts, "
            '{"system_base": context.system_prompt}, model=config.model.model)' + HEADER_BLOCK,
        )
    ],
}

results: dict[str, list[str] | str] = {}
for label, edits in MUTANTS.items():
    text = ORIGINAL
    for old, new in edits:
        assert text.count(old) == 1, f"{label}: anchor not found exactly once"
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
             f"--basetemp={BASETEMP}/{abs(hash(label))}", "tests/agent_loop/test_prompt_assembler.py"],
            capture_output=True, text=True, env={**os.environ, "PYTHONPATH": "src"},
        )
        # pytest exit status: 0 = every test passed (survived), 1 = some tests failed (a kill),
        # anything else = interrupted / internal / usage / collection error (never a kill)
        if run.returncode not in (0, 1):
            results[label] = f"INVALID (pytest exit status {run.returncode})"
            continue
        results[label] = [
            line.split("::")[1].split(" ")[0] for line in run.stdout.splitlines() if line.startswith("FAILED")
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
