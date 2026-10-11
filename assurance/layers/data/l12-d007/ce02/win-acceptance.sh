#!/bin/bash
# CE-L12D007-02 acceptance on Windows: the implementation (code worktree HEAD) over the three agreed matrices,
# compared with the committed pinned-Pi outputs; the outputs are saved into the docs evidence directory.
set -u
ROOT=/e/AI/Projects/OpenMinds/Minions/Minion-Agent
source "$ROOT/.tmp/claude-env.sh"
CE02=$ROOT/review-worktrees/l12d007-docs/assurance/layers/data/l12-d007/ce02
CODE=$ROOT/review-worktrees/l12d007-code
if [ -n "$(git -C "$CODE" status --porcelain -- minion-agent-python)" ]; then
  echo "refused: the code worktree has uncommitted changes, so its outputs cannot be labelled with a SHA" >&2
  exit 1
fi
SHA=$(git -C "$CODE" rev-parse --short=8 HEAD)
P=$ROOT/review-worktrees/ri001-code/minion-agent-python/.venv/Scripts/python.exe
S=E:/AI/Projects/OpenMinds/Minions/Minion-Agent/.tmp/claude-scratch/l12d007/probe-scratch
cd "$CE02"
"$P" ce02_py_probe.py "$CODE" "$S" > "ce02-py-impl-$SHA-win32.jsonl"
"$P" ce02_recovery_py_probe.py "$CODE" "$S" > "ce02-recovery-py-impl-$SHA-win32.jsonl"
"$P" ce02_recovery_py_probe.py "$CODE" "$S" ce02-validation-matrix.json > "ce02-validation-py-impl-$SHA-win32.jsonl"
for m in core recovery validation; do
  if [ $m = core ]; then pi=ce02-pi-win32.jsonl; py=ce02-py-impl-$SHA-win32.jsonl
  else pi=ce02-$m-pi-win32.jsonl; py=ce02-$m-py-impl-$SHA-win32.jsonl; fi
  out=$("$P" ce02_compare.py "$pi" "$py"); rc=$?
  echo "$m ($SHA) compare exit $rc -- MATCH $(echo "$out" | grep -c '^MATCH'), other $(echo "$out" | grep -v '^MATCH' | grep -vc '^    ')"
done
