"""Summarize a home_probe_linux container capture. Read-only. Parity counts exclude SETUP_FAILURE rows."""
import json
import sys

d = json.load(open(sys.argv[1], encoding="utf-8"))
inputs = d["inputs"]
verbose = len(sys.argv) > 2


def t(v):
    if "error" in v:
        return "ERR:" + v["error"]
    return b"".join(u.to_bytes(2, "little") for u in v["value"]).decode("utf-16-le", "surrogatepass").encode(
        "unicode_escape").decode()


totals = {}
for r in d["report"]:
    head = f"uid={r['uid']:<4} HOME={r['home']:<11} UP={r['userprofile']:<5}"
    if r["status"] != "COMPLETE":
        print(head, "SETUP_FAILURE", r["setup_failures"])
        continue
    eqs = {k[:-6]: v for k, v in r.items() if k.endswith("_equal")}
    for k, v in eqs.items():
        totals.setdefault(k, [0, 0])
        totals[k][0] += len(v)
        totals[k][1] += len(v) - sum(v)
    print(head, "node homedir:", t(r["node"]["home"]), "|", {k: f"{sum(v)}/{len(v)}" for k, v in eqs.items()})
    if verbose:
        for i, row in enumerate(r["node"]["rows"]):
            others = {k: t(r[k]["rows"][i]) for k in eqs if r[k]["rows"][i] != row}
            if others:
                print("    ", repr(inputs[i]).ljust(12), "node", t(row), "|", others)
print("observations/mismatches (complete rows only):", totals)
