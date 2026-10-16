"""Read-only: compare frozen rd-1 Node rows for the extended provider against the ordinary C: provider.

Usage: python -I -B ext_rows.py <path to data/l12-d013/ce01/rd-1/node.out>
"""

import json
import sys

rows = json.load(open(sys.argv[1], encoding="utf-8"))["rows"]
EXT, ORD = "\\\\?\\C:\\base", "C:\\base"
ordinary = {(r["input"], r["entries"]): r for r in rows if r["platform"] == "win32" and r["provider"] == ORD}
diff = same = 0
for r in rows:
    if r["platform"] != "win32" or r["provider"] != EXT:
        continue
    o = ordinary[(r["input"], r["entries"])]
    tag = "SAME" if (r["value"], r["cwdReads"], r["envReads"]) == (o["value"], o["cwdReads"], o["envReads"]) else "DIFF"
    same += tag == "SAME"
    diff += tag == "DIFF"
    if tag == "DIFF":
        print(f"{tag} input={r['input']!r:16} entries={r['entries']:6} ext={r['value']!r} reads={r['cwdReads']} env={r['envReads']}"
              f" | ord={o['value']!r} reads={o['cwdReads']} env={o['envReads']}")
print(f"rows: {same} same, {diff} differ")
