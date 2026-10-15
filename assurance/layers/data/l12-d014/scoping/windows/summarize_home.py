"""Summarize home-probe output: per environment row, Node's homedir() and rows vs Python/Rust. Read-only."""
import json
import sys

d = json.load(open(sys.argv[1], encoding="utf-8"))
inputs = d["inputs"]


def t(v):
    if v is None:
        return None
    if "error" in v:
        return "ERR:" + v["error"]
    return b"".join(u.to_bytes(2, "little") for u in v["value"]).decode("utf-16-le", "surrogatepass").encode(
        "unicode_escape").decode()


for r in d["report"]:
    n, p, s = r["node"], r["python"], r["rust"]
    head = f"UP={r['userprofile']:<10} HOME={r['home']:<6} HP={r['homepath']:<6}"
    if "rows" not in n or "rows" not in p or "rows" not in s:
        print(head, "INCOMPLETE", {k: str(v)[:200] for k, v in (("node", n), ("python", p), ("rust", s)) if "rows" not in v})
        continue
    print(head, "node homedir:", t(n["home"]), "| py ~:", t(p["home"]), "| py eq", sum(r["python_equal"]),
          "rust eq", sum(r["rust_equal"]), "/", len(inputs))
    if len(sys.argv) > 2 and sys.argv[2] == "-v":
        for i, a, b, c in zip(inputs, n["rows"], p["rows"], s["rows"]):
            if not (a == b == c):
                print("    ", repr(i).ljust(12), "node", t(a), "| py", t(b), "| rust", t(c))
