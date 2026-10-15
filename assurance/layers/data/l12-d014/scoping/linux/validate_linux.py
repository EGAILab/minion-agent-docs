"""Independent revalidation of a home_probe_linux capture: recompute shapes, counts and parity from the raw child
results, ignoring the probe's own status/equal fields. Read-only."""
import json
import sys

EXPECTED_ROWS = 26


def well_formed(row):
    if not isinstance(row, dict) or set(row) not in ({"value"}, {"error"}):
        return False
    if "error" in row:
        return isinstance(row["error"], str) and row["error"] != ""
    return isinstance(row["value"], list) and all(type(u) is int and 0 <= u <= 0xFFFF for u in row["value"])


for path in sys.argv[1:]:
    d = json.load(open(path, encoding="utf-8"))
    n = len(d["inputs"])
    rows = d["report"]
    keys = {(r["uid"], r["home"], r["userprofile"]) for r in rows}
    children = [k for k in ("python", "rust") if k in rows[0]]
    setup = {"node": 0, **{k: 0 for k in children}}
    obs = {k: 0 for k in children}
    mism = {k: 0 for k in children}
    for r in rows:
        ok = {}
        for k in ["node", *children]:
            v = r[k]
            ok[k] = isinstance(v, dict) and isinstance(v.get("rows"), list) and len(v["rows"]) == n \
                and all(well_formed(x) for x in v["rows"])
            if not ok[k]:
                setup[k] += 1
        for k in children:
            if ok["node"] and ok[k]:
                obs[k] += n
                mism[k] += sum(a != b for a, b in zip(r["node"]["rows"], r[k]["rows"], strict=True))
    print(path, {"rows": len(rows), "unique_partition_rows": len(keys), "expected": EXPECTED_ROWS,
                 "setup_failures": setup, "observations": obs, "mismatches": mism,
                 "probe_reported_setup_failures": d["setup_failures"]})
