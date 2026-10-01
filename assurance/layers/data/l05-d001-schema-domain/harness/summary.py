import json
import sys

r = {x["id"]: x for x in json.load(open(sys.argv[1], encoding="utf-8"))["results"]}
members = ["ascii", "bmp", "pair", "lone-high", "lone-low", "pair-then-lone-high", "fffd", "pair-high-half", "pair-low-half"]
roles = sorted({k.split("/")[0] for k in r}, key=lambda s: list(r).index(next(k for k in r if k.startswith(s + "/"))))
for role in roles:
    print(f"\n{role}  (rows: schema member; cols: instance member; A=accept .=reject E=error)")
    print(" " * 22 + " ".join(m[:6].rjust(6) for m in members))
    for s in members:
        cells = []
        for i in members:
            v = r[f"{role}/{s}/{i}"]["verdict"]
            cells.append({"accept": "A", "reject": ".", "error": "E"}[v].rjust(6))
        print(s.ljust(22) + " ".join(cells))
