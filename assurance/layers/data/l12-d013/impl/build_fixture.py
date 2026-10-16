"""L12-D013: freeze pinned Node's rooted-input observations from the scoping characterization
(`scoping/rooted-probe-2.json`) into the Python port fixture `tests/execution/data/node_rooted_cwd.json`.

Read-only; it prints the fixture to stdout. Node's results depend only on the process-cwd form and
the input (scoping record section 3.1), so the builder REFUSES unless every provider and entry row
of one cwd form agrees exactly, and unless that form's cwd is the same in every row.

    python build_fixture.py <rooted-probe-2.json>
"""

import json
import sys

probe = json.load(open(sys.argv[1], encoding="utf-8"))
inputs = probe["inputs"]
forms: dict[str, dict] = {}
for row in probe["report"]:
    node = row["node"]
    if len(node["rows"]) != len(inputs) or any(not r["abs"] for r in node["rows"]):
        raise SystemExit(f"malformed node row: {row['cwd_form']} {row['provider']} {row['entries']}")
    seen = {"cwd": node["cwd"], "values": [r["value"] for r in node["rows"]]}
    if forms.setdefault(row["cwd_form"], seen) != seen:
        raise SystemExit(f"node result varies within cwd form {row['cwd_form']}")
fixture = {
    "source": "minion-agent-docs assurance/layers/data/l12-d013/scoping/rooted-probe-2.json",
    "inputs": [list(memoryview(i.encode("utf-16-le", "surrogatepass")).cast("H")) for i in inputs],
    "cwd_forms": [{"label": k, "cwd": v["cwd"], "node": v["values"]} for k, v in sorted(forms.items())],
}
print(json.dumps(fixture, indent=1))
