#!/bin/sh
# L12-D012 native Linux characterization, part 2 (python:3.13): Python's certified resolve_local_path against the
# pinned-Pi native Linux column produced by part 1. Pure computation. Read-only binds: /src (minion-agent-python),
# /probe (scripts + node output). Writable: /pipcache, /out (inside the project root). Work in private /tmp.
set -eu
PIP_CACHE_DIR=/pipcache pip install -q --root-user-action=ignore "ada-url==1.15.3" "url-py>=2026.5.1" "pydantic>=2.7" \
  "pyyaml>=6.0" "httpx>=0.27" "jsonschema>=4.22" > /out/pip.log 2>&1
cd /tmp
PYTHONPATH=/src/src PYTHONDONTWRITEBYTECODE=1 python - <<'PY' | tee /out/py-linux.txt
import json
from minion_agent.execution.filesystem import resolve_local_path
d = json.load(open("/out/native-linux.json", encoding="utf-8"))
assert d["platform"] == "linux", d["platform"]
diff = 0
for row in d["rows"]:
    got = resolve_local_path("/x", row["input"])
    ok = got == row["native"]
    diff += not ok
    print("OK  " if ok else "DIFF", repr(row["input"]), repr(got), "" if ok else f"(pi {row['native']!r})")
print(f"{len(d['rows']) - diff}/{len(d['rows'])} equal on linux; native==posix(provisional): "
      f"{sum(r['native'] == r['posix'] for r in d['rows'])}/{len(d['rows'])}")
PY
