"""Print the L12-D007 Pi per-operation code matrix from a probe JSON (default pi-win32.json)."""
import collections
import json
import sys

d = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "pi-win32.json", encoding="utf-8"))
tab: dict[str, dict[str, str]] = collections.defaultdict(dict)
ops: list[str] = []
for r in d["results"]:
    o = r.get("observed") or {}
    if "setup_failed" in r:
        v = "SETUP"
    elif "error" in o:
        v = o["error"]
    elif "node_error" in o:
        v = "N:" + o["node_error"]
    else:
        v = "ok" if o.get("ok") else "THREW"
    tab[r["condition"]][r["op"]] = v
    if r["op"] not in ops:
        ops.append(r["op"])
ab = ["rTxt", "rLin", "rBin", "wr", "app", "mvSrc", "mvDst", "info", "exist", "ls", "canon",
      "mkdirR", "mkdir", "rm", "rmR", "rmF", "readdir", "lstat", "accR", "accRW"]
sh = {"not_found": "nf", "permission_denied": "pd", "not_directory": "nd", "is_directory": "isd",
      "invalid": "inv", "unknown": "unk", "ok": "ok"}
print(" " * 20 + "".join(a.rjust(7) for a in ab))
for c, row in tab.items():
    print(c[:20].ljust(20) + "".join(sh.get(row.get(o, "-"), row.get(o, "-"))[:6].rjust(7) for o in ops))
