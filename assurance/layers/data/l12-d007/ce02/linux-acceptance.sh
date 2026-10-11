#!/bin/bash
# CE-L12D007-02 acceptance on Linux: replay pinned Pi and the implementation over the three agreed matrices
# (run-linux-ce02.sh), then compare. Pinned Pi's replay must be identical to the committed outputs.
set -u
ROOT=/e/AI/Projects/OpenMinds/Minions/Minion-Agent
CE02=$ROOT/review-worktrees/l12d007-docs/assurance/layers/data/l12-d007/ce02
OUT=$ROOT/.tmp/claude-scratch/l12d007/impl-linux
P=$ROOT/review-worktrees/ri001-code/minion-agent-python/.venv/Scripts/python.exe
mkdir -p "$OUT"
cd "$CE02"
bash run-linux-ce02.sh l12d007-code > "$OUT/run.out" 2>&1
echo "run rc=$?; rows $(grep -c '"id"' "$OUT/run.out")"
for s in pi py pi-recovery py-recovery pi-validation py-validation; do
  awk -v s="== $s" '$0==s{f=1;next}/^== /{f=0}f' "$OUT/run.out" > "$OUT/$s.jsonl"
done
for m in core recovery validation; do
  if [ $m = core ]; then pi=ce02-pi-linux.jsonl; rp=pi; py=py; else pi=ce02-$m-pi-linux.jsonl; rp=pi-$m; py=py-$m; fi
  if cmp -s <(tr -d '\r' < "$pi") "$OUT/$rp.jsonl"; then echo "$m pinned Pi replay identical"; else echo "$m pinned Pi replay DIFFERS"; fi
  "$P" ce02_compare.py "$pi" "$OUT/$py.jsonl" > "$OUT/compare-$m.txt"
  echo "$m compare exit $? -- MATCH $(grep -c '^MATCH' "$OUT/compare-$m.txt"), other $(grep -v '^MATCH' "$OUT/compare-$m.txt" | grep -vc '^    ')"
done
