"""CE-L12D007-01 negative controls for the code repository's canonical runner. Run from
minion-agent-python with PYTHONPATH="src;." (or "src:."):  python <this file>

Each mutant is applied to the runner in a child process, before pytest imports it (an in-memory
module built from the mutated source -- the runner file is never modified), and its intended witness
must FAIL. Everything runs on synthetic link metadata; nothing is written outside pytest's basetemp."""
import subprocess
import sys

BASETEMP = "E:/AI/Projects/OpenMinds/Minions/Minion-Agent/.tmp/pytest-l12d007-mutants"
MUTANTS = [
    ("7 runner-skips-provider-target", "attr", "_provider_target = lambda *a, **k: None",
     "test_runner_refuses_a_provider_step_through_an_outward_link_before_the_provider_runs"),
    ("21 runner-lexical-dotdot-link-text", "source",
     "                if \"..\" in text.replace(\"\\\\\", \"/\").split(\"/\"):\n"
     "                    raise AssertionError(f\"containment: link {current!r} text has '..'; refused\")\n",
     "test_dotdot_link_text_does_not_erase_an_unchecked_link"),
]
CHILD = r'''
import importlib.util, sys, types, pytest
name = "tests.conformance.fs_path_runner"
path = "tests/conformance/fs_path_runner.py"
kind, payload, witness, basetemp = sys.argv[1:5]
if kind == "attr":
    import tests.conformance.fs_path_runner as r
    exec("r." + payload)
else:
    src = open(path, encoding="utf-8").read()
    if src.count(payload) != 1:
        sys.exit(f"mutant anchor count {src.count(payload)}")  # an anchor failure is never a kill
    module = types.ModuleType(name)
    module.__file__ = path
    sys.modules[name] = module
    exec(compile(src.replace(payload, ""), path, "exec"), module.__dict__)
sys.exit(pytest.main(["-p", "no:cacheprovider", "--no-cov", "-q", "-rf", "--basetemp=" + basetemp,
                      "tests/conformance/test_fs_path_runner_containment.py", "-k", witness]))
'''
bad = 0
for label, kind, payload, witness in MUTANTS:
    p = subprocess.run([sys.executable, "-c", CHILD, kind, payload, witness, BASETEMP], capture_output=True, text=True)
    killed = p.returncode == 1 and f"FAILED tests/conformance/test_fs_path_runner_containment.py::{witness}" in p.stdout
    bad += not killed
    print(("KILLED" if killed else "NOT KILLED") + f" {label} by {witness}" + ("" if killed else f" ({p.returncode} {p.stdout[-300:]} {p.stderr[-300:]})"))
print(f"{bad} FAILED" if bad else "ALL PASS")
sys.exit(1 if bad else 0)
