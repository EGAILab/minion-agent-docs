import json, sys
a = {r["id"]: r["observed"] for r in json.load(open(sys.argv[1], encoding="utf-8"))["results"]}
b = {r["id"]: r["observed"] for r in json.load(open(sys.argv[2], encoding="utf-8"))["results"]}
for k in a: print(("SAME " if a[k] == b[k] else "DIFF ") + k, "" if a[k] == b[k] else f"pi={a[k]} py={b[k]}")
