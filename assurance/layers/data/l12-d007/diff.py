"""Compare two L12-D007 probe JSONs (Pi vs a binding) cell by cell."""
import collections
import json
import sys


def load(p):
    out = {}
    for r in json.load(open(p, encoding="utf-8"))["results"]:
        o = r.get("observed") or {}
        if "setup_failed" in r or "setup_failed" in o:
            v = "SETUP"
        elif "error" in o:
            v = o["error"]
        elif "node_error" in o:
            v = {"ENOENT": "not_found", "ENOTDIR": "not_directory", "EBUSY": "unknown", "ELOOP": "unknown",
                 "EACCES": "permission_denied", "EPERM": "permission_denied", "EISDIR": "is_directory",
                 "EINVAL": "invalid"}.get(o["node_error"], "unknown") + "*"
        elif "threw" in o:
            v = "THREW:" + o["threw"][:60]
        else:
            v = "ok"
        out[(r["condition"], r["op"])] = v
    return out


pi, other = load(sys.argv[1]), load(sys.argv[2])
by_cond = collections.defaultdict(list)
for k in pi:
    a, b = pi[k], other.get(k, "-")
    if a.rstrip("*") != b:
        by_cond[k[0]].append(f"{k[1]}: pi={a} binding={b}")
total = sum(len(v) for v in by_cond.values())
print(f"{total} differing cells of {len(pi)}  (* = Minion-only primitive, Pi code via toFileError of Node's raw errno)")
for c, rows in by_cond.items():
    print(f"\n[{c}] {len(rows)}")
    for r in rows:
        print("  ", r)
