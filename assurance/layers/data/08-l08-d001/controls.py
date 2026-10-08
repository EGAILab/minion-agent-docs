"""L08-D001 kill controls: each mutant edits a disposable copy of driver.py; the witness suite must
fail. Run from a copy's minion-agent-python/ with: python l08d001-controls.py <python> <basetemp>."""

import pathlib
import shutil
import subprocess
import sys

PY, BASETEMP = sys.argv[1], sys.argv[2]
DRIVER = pathlib.Path("src/minion_agent/agent_loop/driver.py")
ORIGINAL = DRIVER.read_text(encoding="utf-8")

ASSEMBLE = "        text = self.prompt_assembler(context.system_prompt, context.tools)\n"
OVERRIDE = "        if decision.system_override is not None:\n            return decision.system_override\n        if self.prompt_assembler is None:\n"
HEADER_BLOCK = '        components = {"system_base": self._system_text(decision, context)}\n'

MUTANTS = {
    "live-registry assembly": [
        (ASSEMBLE, "        text = self.prompt_assembler(context.system_prompt, self.tools.visible_from(self.instance.scope))\n")
    ],
    "reversed snapshot order": [
        (ASSEMBLE, "        text = self.prompt_assembler(context.system_prompt, tuple(reversed(context.tools)))\n")
    ],
    "override reassembled": [
        (OVERRIDE, "        if decision.system_override is not None and self.prompt_assembler is None:\n            return decision.system_override\n        if self.prompt_assembler is None:\n")
    ],
    "stale assembled text (first request only)": [
        (ASSEMBLE, "        text = getattr(self, '_stale', None) or self.prompt_assembler(context.system_prompt, context.tools)\n        self._stale = text\n")
    ],
    "header published before assembly": [
        (HEADER_BLOCK, '        record_header(self.instance.log, self.artifacts, {"system_base": context.system_prompt}, model=config.model.model)\n' + HEADER_BLOCK)
    ],
}

results = {}
for label, edits in MUTANTS.items():
    text = ORIGINAL
    for old, new in edits:
        assert text.count(old) == 1, f"{label}: anchor not found"
        text = text.replace(old, new)
    DRIVER.write_text(text, encoding="utf-8")
    run = subprocess.run(
        [PY, "-m", "pytest", "-p", "no:cacheprovider", "--no-cov", "-q",
         f"--basetemp={BASETEMP}/{abs(hash(label))}", "tests/agent_loop/test_prompt_assembler.py"],
        capture_output=True, text=True, env={**__import__("os").environ, "PYTHONPATH": "src"},
    )
    failed = [line.split("::")[1].split(" ")[0] for line in run.stdout.splitlines() if line.startswith("FAILED")]
    results[label] = failed
    DRIVER.write_text(ORIGINAL, encoding="utf-8")

for label, failed in results.items():
    print(("KILLED  " if failed else "SURVIVED"), label, "->", failed)
sys.exit(0 if all(results.values()) else 1)
