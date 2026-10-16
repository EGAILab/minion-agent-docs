"""Summarize rooted-probe output. Read-only.  python summarize.py <rooted-probe.json> [cwd_form entries provider]"""
import json
import sys

d = json.load(open(sys.argv[1], encoding="utf-8"))
inputs = d["inputs"]
for r in d["report"]:
    n, p = r["node"], r["python"]
    if "rows" not in n or "rows" not in p:
        print("ERR", r["cwd_form"], r["entries"], r["provider"], n if "rows" not in n else "", p if "rows" not in p else "")
        continue
    print("==", r["cwd_form"], r["entries"], r["provider"].ljust(16), "| node cwd", n["cwd_text"][-24:],
          "| equal", sum(r["equal"]), "/", len(inputs))
if len(sys.argv) > 2:
    form, entries, provider = sys.argv[2:5]
    for r in d["report"]:
        if (r["cwd_form"], r["entries"], r["provider"]) == (form, entries, provider):
            for i, a, b in zip(inputs, r["node"]["rows"], r["python"]["rows"]):
                print(repr(i).ljust(16), str(a.get("abs")).ljust(5), repr(a.get("text", a.get("error"))).ljust(34),
                      repr(b.get("text", b.get("error"))))
