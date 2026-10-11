#!/bin/bash
# CE-L12D007-02 directory-link rows on Windows (status sync, minion-agent#199): pinned Pi and the implementation
# (code worktree HEAD) over ce02-dirlink-matrix.json, compared. Pinned Pi's run must be identical to the committed
# output; the implementation's output is saved under its SHA.
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
node --experimental-strip-types --no-warnings ce02-recovery-pi-probe.mjs E:/AI/Projects/OpenMinds/Minions/Minion-Agent/ref-repos/pi "$S" ce02-dirlink-matrix.json > "$S/dirlink-pi-win32.jsonl"
echo "pi rc=$?"
if [ -f ce02-dirlink-pi-win32.jsonl ]; then
  if cmp -s <(tr -d '\r' < ce02-dirlink-pi-win32.jsonl) <(tr -d '\r' < "$S/dirlink-pi-win32.jsonl"); then echo "pinned Pi run identical to committed"
  else echo "pinned Pi run DIFFERS from committed"; fi
else
  cp "$S/dirlink-pi-win32.jsonl" ce02-dirlink-pi-win32.jsonl && echo "pinned Pi output committed (first run)"
fi
"$P" ce02_recovery_py_probe.py "$CODE" "$S" ce02-dirlink-matrix.json > "ce02-dirlink-py-impl-$SHA-win32.jsonl"
echo "py rc=$?"
out=$("$P" ce02_compare.py ce02-dirlink-pi-win32.jsonl "ce02-dirlink-py-impl-$SHA-win32.jsonl"); rc=$?
echo "$out"
echo "dirlink ($SHA) compare exit $rc -- MATCH $(echo "$out" | grep -c '^MATCH'), other $(echo "$out" | grep -v '^MATCH' | grep -vc '^    ')"
