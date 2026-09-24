"""Compare a candidate host's results with the Node/Pi authority, field by field."""

import json
import sys

FIELDS = ("input_sha256", "sniffed_mime", "ok", "mime", "hints", "message", "data_sha256", "data_bytes", "data_base64_len")
authority, candidate = (json.load(open(p, encoding="utf-8")) for p in sys.argv[1:3])
label = sys.argv[3] if len(sys.argv) > 3 else candidate.get("engine", "candidate")
problems = []
a_read = {r["file"]: r for r in authority["read_level"]}
c_read = {r["file"]: r for r in candidate["read_level"]}
if set(a_read) != set(c_read):
    problems.append(f"read-level file sets differ: {sorted(set(a_read) ^ set(c_read))}")
branches = {"ok": 0, "failed": 0, "not_sniffed": 0}
for f, a in a_read.items():
    c = c_read.get(f, {})
    for k in FIELDS:
        if a.get(k) != c.get(k):
            problems.append(f"read {f}: {k}: authority={a.get(k)!r} {label}={c.get(k)!r}")
    branches["not_sniffed" if not a["sniffed_mime"] else "ok" if a.get("ok") else "failed"] += 1
a_core = {r["id"]: r for r in authority["core_level"]}
c_core = {r["id"]: r for r in candidate["core_level"]}
if set(a_core) != set(c_core):
    problems.append(f"core-level case sets differ: {sorted(set(a_core) ^ set(c_core))}")
for i, a in a_core.items():
    if a["result"] != c_core.get(i, {}).get("result"):
        problems.append(f"core {i}: authority={a['result']} {label}={c_core.get(i, {}).get('result')}")
if candidate.get("unexpected_imports"):
    problems.append(f"{label} reached unexpected imports: {candidate['unexpected_imports']}")
print(f"{label}: {len(a_read)} read-level ({branches}), {len(a_core)} core-level")
for p in problems[:40]:
    print("  MISMATCH", p)
print(f"VERDICT {label}: {'IDENTICAL to authority' if not problems else f'{len(problems)} mismatch(es)'}")
sys.exit(1 if problems else 0)
