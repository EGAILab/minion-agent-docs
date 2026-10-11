#!/bin/bash
# L12-D007 Python implementation: full Windows gates (all temp/cache under the project root on E:).
set -u
T=/e/AI/Projects/OpenMinds/Minions/Minion-Agent
source $T/.tmp/claude-env.sh
eval "$(cd $T/review-worktrees/ri001-code/minion-agent-python && bash scripts/pinned-icu/build.sh $T/.toolchain/icu-78.3-src --env 2>/dev/null)"
export MINION_SEARCH_ENGINE_ARTIFACTS=E:/AI/Projects/OpenMinds/Minions/Minion-Agent/.toolchain/search-engines/dl
export PATH="/c/Program Files/Git/usr/bin:$PATH"
V=$T/review-worktrees/ri001-code/minion-agent-python/.venv/Scripts
L=$T/.tmp/claude-scratch/l12d007/py-win-gates
mkdir -p $L
cd $T/review-worktrees/l12d007-code/minion-agent-python
$V/ruff.exe check src tests > $L/ruff.log 2>&1; echo "ruff $?"
$V/ruff.exe format --check src/minion_agent/execution tests/execution tests/conformance/fs_path_runner.py tests/conformance/test_fs_path_runner_containment.py tests/conformance/test_fs_path_conformance.py > $L/format.log 2>&1; echo "format(changed files) $?"
PYTHONPATH=src $V/python.exe -m mypy src > $L/mypy.log 2>&1; echo "mypy $?"; tail -1 $L/mypy.log
PYTHONPATH="src;." $V/python.exe -m pytest -p no:cacheprovider --basetemp=E:/AI/Projects/OpenMinds/Minions/Minion-Agent/.tmp/pytest-l12d007-gate > $L/pytest.log 2>&1; echo "pytest $?"
grep -E "passed|failed" $L/pytest.log | tail -1
grep -E "^TOTAL|Required test coverage|FAIL Required" $L/pytest.log | tail -3
