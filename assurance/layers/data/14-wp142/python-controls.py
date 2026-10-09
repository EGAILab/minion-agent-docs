"""WP-14.2 Python kill controls: each mutant edits a disposable copy of the system_prompt package;
the witness suite (formatting, integration, canonical) must fail. Run from a copy's
minion-agent-python/ with: python python-controls.py <python> <basetemp>.

Anchors start at a line start; every mutant must change the source and compile; only pytest exit
status 0 (survived) or 1 (killed) counts -- anything else is INVALID and fails the run."""

import os
import pathlib
import py_compile
import subprocess
import sys

PY, BASETEMP = sys.argv[1], sys.argv[2]
FORMATTING = pathlib.Path("src/minion_agent/system_prompt/formatting.py")
COMPOSER = pathlib.Path("src/minion_agent/system_prompt/composer.py")
TESTS = [
    "tests/system_prompt",
    "tests/conformance/test_prompt_assembly_conformance.py",
]

MUTANTS = {
    "escape & last": (
        FORMATTING,
        '\n        value.replace("&", "&amp;")\n        .replace("<", "&lt;")\n',
        '\n        value.replace("<", "&lt;")\n        .replace("&", "&amp;")\n',
    ),
    "read gate case-insensitive": (
        COMPOSER,
        '\n    if any(tool.name == "read" for tool in tools):\n',
        '\n    if any(tool.name.lower() == "read" for tool in tools):\n',
    ),
    "guidelines deduplicated per tool only": (
        FORMATTING,
        "\n        for guideline in normalize_guidelines(tool.prompt_guidelines):\n"
        "            guidelines.setdefault(guideline, None)\n",
        "\n        for guideline in normalize_guidelines(tool.prompt_guidelines):\n"
        "            guidelines[guideline + chr(0) * len(guidelines)] = None\n",
    ),
    "dirname on code points": (
        FORMATTING,
        '\n    units = to_units(path).rstrip("/\\\\")\n',
        '\n    units = path.rstrip("/\\\\")\n',
    ),
    "empty sections kept": (
        COMPOSER,
        '\n    return "\\n\\n".join(part for part in parts if part)\n',
        '\n    return "\\n\\n".join(parts)\n',
    ),
    "Pi (none) line rendered": (
        FORMATTING,
        "\n    if snippet_lines:\n"
        '        blocks.append("Available tools:\\n" + "\\n".join(snippet_lines))\n',
        "\n    if snippet_lines or guidelines:\n"
        '        blocks.append("Available tools:\\n" + ("\\n".join(snippet_lines) or "(none)"))\n',
    ),
    "configuration read once": (
        COMPOSER,
        "\n        configuration = self.configuration\n",
        # the first configuration ever read is reused by every later assembly
        "\n        configuration = getattr(PromptComposer, '_first', None) or self.configuration\n"
        "        PromptComposer._first = configuration\n",
    ),
    "skill records copied": (
        COMPOSER,
        "\n        return cls(skills=tuple(skills), tools_section=tools_section, sections=tuple(sections))\n",
        "\n        import copy\n\n"
        "        return cls(skills=tuple(copy.copy(s) for s in skills), tools_section=tools_section, "
        "sections=tuple(sections))\n",
    ),
}

originals = {p: p.read_text(encoding="utf-8") for p in (FORMATTING, COMPOSER)}
results: dict[str, list[str] | str] = {}
for label, (target, old, new) in MUTANTS.items():
    text = originals[target]
    assert text.count(old) == 1, f"{label}: anchor not found exactly once"
    mutated = text.replace(old, new)
    assert mutated != text, f"{label}: mutant did not change the source"
    target.write_text(mutated, encoding="utf-8")
    try:
        try:
            py_compile.compile(str(target), doraise=True)
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
            line.split("::", 1)[1].split(" ")[0] for line in run.stdout.splitlines() if line.startswith("FAILED")
        ]
    finally:
        for path, original in originals.items():
            path.write_text(original, encoding="utf-8")

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
