"""CE-L12D007-01 negative control 7 (runner-skips-provider-target), for the code repository's
canonical runner. Run from minion-agent-python with PYTHONPATH="src;." (or "src:."):
    python <this file>
With the runner's R5 proof (`_provider_target`) replaced by a no-op, the run-level control
`test_runner_refuses_a_provider_step_through_an_outward_link_before_the_provider_runs` must FAIL
(the provider is reached). Everything runs on synthetic link metadata; nothing is written."""
import subprocess
import sys

WITNESS = "test_runner_refuses_a_provider_step_through_an_outward_link_before_the_provider_runs"
code = (
    "import tests.conformance.fs_path_runner as r\n"
    "r._provider_target = lambda *a, **k: None\n"
    "import pytest, sys\n"
    "sys.exit(pytest.main(['-p', 'no:cacheprovider', '--no-cov', '-q', '-rf',\n"
    "    '--basetemp=E:/AI/Projects/OpenMinds/Minions/Minion-Agent/.tmp/pytest-l12d007m',\n"
    f"    'tests/conformance/test_fs_path_runner_containment.py', '-k', '{WITNESS}']))\n"
)
p = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
killed = p.returncode != 0 and f"FAILED tests/conformance/test_fs_path_runner_containment.py::{WITNESS}" in p.stdout
print(("KILLED" if killed else "NOT KILLED") + f" 7 runner-skips-provider-target by {WITNESS}")
sys.exit(0 if killed else 1)
