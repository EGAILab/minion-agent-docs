import io
import os

# Expects node_corpus_results_22.19.0.txt, python_corpus_results.txt, and
# rust_corpus_results.txt (each "input\toutput" per line, produced by node_probe.mjs,
# python_probe.py, and rust_oracle_probe respectively) alongside this script -- see README.md
# in this same directory for exact reproduction commands.
base = os.path.dirname(os.path.abspath(__file__)) + os.sep


def load(path):
    d = {}
    with io.open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n").rstrip("\r")
            if "\t" not in line:
                continue
            k, v = line.split("\t", 1)
            d[k] = v
    return d


node = load(base + "node_corpus_results_22.19.0.txt")
python = load(base + "python_corpus_results.txt")
rust = load(base + "rust_corpus_results.txt")

# platform-dependent / not meaningful for comparison
skip = {"/already/absolute.txt", "~", "~/x.txt"}

rows = []
py_mismatches = []
rs_mismatches = []
for case in node:
    if case in skip:
        continue
    n = node[case]
    p = python.get(case, "<MISSING>")
    r = rust.get(case, "<MISSING>")
    py_ok = p == n
    rs_ok = r == n
    rows.append((case, n, p, r, py_ok, rs_ok))
    if not py_ok:
        py_mismatches.append((case, n, p))
    if not rs_ok:
        rs_mismatches.append((case, n, r))

print(f"TOTAL CASES (excluding platform-dependent): {len(rows)}")
print(f"PYTHON MATCHES NODE: {len(rows) - len(py_mismatches)}/{len(rows)}")
print(f"RUST MATCHES NODE:   {len(rows) - len(rs_mismatches)}/{len(rows)}")
print()
print("=== PYTHON MISMATCHES ===")
for case, n, p in py_mismatches:
    print(f"  input:    {case}")
    print(f"    node:   {n!r}")
    print(f"    python: {p!r}")
print()
print("=== RUST MISMATCHES ===")
for case, n, r in rs_mismatches:
    print(f"  input:    {case}")
    print(f"    node:   {n!r}")
    print(f"    rust:   {r!r}")

with io.open(base + "matrix_full.tsv", "w", encoding="utf-8") as out:
    out.write("input\tnode\tpython\trust\tpy_match\trust_match\n")
    for case, n, p, r, py_ok, rs_ok in rows:
        out.write(f"{case}\t{n}\t{p}\t{r}\t{py_ok}\t{rs_ok}\n")
