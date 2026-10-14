"""CE-L12D011-01 revision characterization: an evidence reporter that records each failed report's ACTUAL
exception identity and raising origin before rendering. Emits one stdout line per failed report in the terminal
summary (after capture ends). No file writes."""

import builtins
import json
import subprocess
from pathlib import Path

import pytest

_ASSERTION, _VALUE = builtins.AssertionError, builtins.ValueError  # identity captured at plugin import
_STDLIB_SUBPROCESS = Path(subprocess.__file__).resolve()
_RECORDS: list[dict] = []


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if not report.failed or call.excinfo is None:
        return
    exc = call.excinfo.value
    frames = [(Path(e.path).resolve(), e.name, e.lineno + 1) for e in call.excinfo.traceback]
    tb = exc.__traceback__
    while tb is not None and tb.tb_next is not None:
        tb = tb.tb_next
    inner = (Path(tb.tb_frame.f_code.co_filename).resolve(), tb.tb_frame.f_code.co_name, tb.tb_lineno) if tb else None
    kind = "ASSERTION" if type(exc) is _ASSERTION else "VALUE_ERROR" if type(exc) is _VALUE else "OTHER"
    _RECORDS.append({
        "node": report.nodeid,
        "when": report.when,
        "kind": kind,
        "type": f"{type(exc).__module__}.{type(exc).__qualname__}",
        "first_line": str(exc).split("\n", 1)[0],
        "inner": None if inner is None else
        ("stdlib:subprocess" if inner[0] == _STDLIB_SUBPROCESS else inner[0].name, inner[1], inner[2]),
        "seam_on_stack": any(p.as_posix().endswith("minion_agent/execution/subprocess.py") and n == "spawn"
                             for p, n, _ in frames),
    })


def pytest_terminal_summary(terminalreporter):
    for record in _RECORDS:
        terminalreporter.write_line("L12D011-EVIDENCE " + json.dumps(record, ensure_ascii=True))
