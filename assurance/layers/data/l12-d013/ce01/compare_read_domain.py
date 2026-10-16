"""CE-L12D013-01: validate and join the Node and Python read-domain captures. Reads two JSON files, prints a report
on stdout and writes nothing.
- Both captures must cover EXACTLY the expected row keys, each once: 336 win32 rows each, plus 24 Node POSIX
  rows. Every row must be well formed: a string value or a string error, an integer cwd-read count, and a list of
  "=X:" reads.
- Any shape violation is a SETUP FAILURE (exit 2), never a parity observation.
- Per win32 row it compares the value, the cwd-read count and the inherited-entry read SEQUENCE, case-normalized
  (the Windows environment block is case-insensitive).

    python -I -B compare_read_domain.py <node.json> <python.json>
"""

import sys

sys.dont_write_bytecode = True
import json  # noqa: E402
from collections import Counter  # noqa: E402
from itertools import product  # noqa: E402

W_PROVIDERS = ["C:\\base", "\\base", "C:base", "base", "", "\\\\srv\\share\\base", "\\\\?\\C:\\base"]
W_INPUTS = ["C:\\x", "\\\\srv\\share\\x", "\\leaf", "/leaf", "\\\\leaf", "\\\\srv\\", "a:leaf", "c:leaf", "leaf", "",
            "file:///C:/x", "file://srv/share/x"]
W_ENTRIES = ["absent", "empty", "same", "other"]
P_PROVIDERS = ["/base", "base", "", "//base"]
P_INPUTS = ["/x", "//x", "x", "", "\\leaf", "file:///x"]
EXPECTED = {
    "node": {("win32", *k) for k in product(W_PROVIDERS, W_INPUTS, W_ENTRIES)}
    | {("posix", p, i, "n/a") for p, i in product(P_PROVIDERS, P_INPUTS)},
    "python": {("win32", *k) for k in product(W_PROVIDERS, W_INPUTS, W_ENTRIES)},
}


def setup_failure(why: str) -> None:
    print(f"SETUP FAILURE: {why}")
    sys.exit(2)


def rows_of(name: str, path: str) -> dict:
    try:
        doc = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError) as exc:
        setup_failure(f"{name} capture unreadable: {exc}")
    rows: dict = {}
    for r in doc.get("rows", []):
        k = (r.get("platform"), r.get("provider"), r.get("input"), r.get("entries"))
        if k in rows:
            setup_failure(f"{name} duplicate row {k}")
        ok = (isinstance(r.get("value"), str)) != (isinstance(r.get("error"), str))
        ok = ok and isinstance(r.get("cwdReads"), int) and isinstance(r.get("envReads"), list)
        ok = ok and all(isinstance(e, str) and e.startswith("=") for e in r["envReads"])
        if not ok:
            setup_failure(f"{name} malformed row {k}: {r}")
        rows[k] = r
    if set(rows) != EXPECTED[name]:
        missing, extra = EXPECTED[name] - set(rows), set(rows) - EXPECTED[name]
        setup_failure(f"{name} key coverage: {len(missing)} missing, {len(extra)} extra")
    return rows


node = rows_of("node", sys.argv[1])
py = rows_of("python", sys.argv[2])
norm = lambda reads: [e.upper() for e in reads]  # noqa: E731
classes: Counter = Counter()
diffs = []
for k in sorted(EXPECTED["python"]):
    n, p = node[k], py[k]
    same = (n.get("value"), n.get("error") is None, n["cwdReads"], norm(n["envReads"])) == (
        p.get("value"), p.get("error") is None, p["cwdReads"], norm(p["envReads"]))
    classes[("equal" if same else "differs", "node-reads" if n["cwdReads"] else "node-no-read")] += 1
    if not same:
        diffs.append({"provider": k[1], "input": k[2], "entries": k[3],
                      "node": [n.get("value", n.get("error")), n["cwdReads"], norm(n["envReads"])],
                      "python": [p.get("value", p.get("error")), p["cwdReads"], norm(p["envReads"])]})
print("coverage: node", len(node), "python", len(py), "(exact key sets verified)")
print("win32 classes:", {f"{a}/{b}": c for (a, b), c in sorted(classes.items())})
print("win32 Node rows reading the cwd:", sum(1 for k in EXPECTED["python"] if node[k]["cwdReads"]))
print("win32 Python rows reading the cwd:", sum(1 for k in EXPECTED["python"] if py[k]["cwdReads"]))
print("posix Node rows reading the cwd:", sorted((k[1], k[2], node[k]["cwdReads"]) for k in node
                                                 if k[0] == "posix" and node[k]["cwdReads"]))
print(json.dumps(diffs, indent=1))
