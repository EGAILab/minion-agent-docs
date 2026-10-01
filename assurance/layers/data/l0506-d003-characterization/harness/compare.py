"""Compare certified Python (py.json) with the pinned-Pi authority (result.json), boundary by boundary.
   python compare.py out/result.json out/py.json"""
import sys
import json
pi = {x["id"]: x for x in json.load(open(sys.argv[1]))["results"]}
py = {x["id"]: x for x in json.load(open(sys.argv[2]))["results"]}
mism = {}
for cid, p in py.items():
    q = pi[cid]
    if "python" in p:
        mism.setdefault("unrepresentable", []).append(cid); continue
    for b in ("hook", "end", "message"):
        if p[b] is None and q[b] is None: continue
        for f in ("content", "details", "isError"):
            if (p[b] or {}).get(f) != (q[b] or {}).get(f):
                mism.setdefault(f"{b}.{f}", []).append(cid)
    if isinstance(p["session"], str):
        mism.setdefault("session-error", []).append((cid, p["session"]))
    else:
        if p["session"]["details"] != q["message"]["details"] or p["session"]["content"] != q["message"]["content"]:
            mism.setdefault("session-replay!=pi-memory", []).append(cid)
for k, v in mism.items(): print(k, len(v), v[:12])
