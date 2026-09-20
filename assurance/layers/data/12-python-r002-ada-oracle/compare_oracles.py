import json
import io
import os

SCRATCH = os.path.dirname(os.path.abspath(__file__))


def load_node(path):
    d = {}
    with io.open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n").rstrip("\r")
            if "\t" not in line:
                continue
            url, val = line.split("\t", 1)
            if val == "PARSE_ERROR":
                d[url] = None
            else:
                path_str = json.loads(val)
                body = path_str.lstrip("\\")
                suffix = "\\share"
                host = body[: -len(suffix)] if body.endswith(suffix) else body
                d[url] = host
    return d


def load_bare(path):
    d = {}
    with io.open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n").rstrip("\r")
            if "\t" not in line:
                continue
            url, val = line.split("\t", 1)
            d[url] = None if val == "PARSE_ERROR" else val
    return d


node19 = load_node(os.path.join(SCRATCH, "systematic_node_22190.txt"))
node23 = load_node(os.path.join(SCRATCH, "systematic_node_22232.txt"))
ada292 = load_bare(os.path.join(SCRATCH, "systematic_ada292.txt"))
pyada = load_bare(os.path.join(SCRATCH, "systematic_pyada_400_full.txt"))

urls = list(node19.keys())
print("total cases:", len(urls))


def compare(a, b, name):
    accept_mismatch = 0
    output_mismatch = 0
    examples = []
    for u in urls:
        va, vb = a.get(u), b.get(u)
        if (va is None) != (vb is None):
            accept_mismatch += 1
            if len(examples) < 20:
                examples.append((u, va, vb))
        elif va is not None and vb is not None and va != vb:
            output_mismatch += 1
            if len(examples) < 20:
                examples.append((u, va, vb))
    print(f"--- {name} --- accept_mismatch={accept_mismatch} output_mismatch={output_mismatch}")
    for u, va, vb in examples:
        print(f"  {u}\t{va!r}\tvs\t{vb!r}")
    return examples


prototype = load_bare(os.path.join(SCRATCH, "systematic_prototype.txt"))

compare(node19, node23, "node19 vs node23 (drift)")
ex1 = compare(node19, ada292, "node19 vs ada292 (DIRECT ORACLE FIDELITY)")
ex2 = compare(node19, pyada, "node19 vs python-ada-url-4.0.0 (CURRENT DEP)")
ex3 = compare(ada292, pyada, "ada292 vs python-ada-url-4.0.0")
ex4 = compare(ada292, prototype, "ada292 vs REJECTED PROTOTYPE (idna.uts46data + unicodedata)")

with open(os.path.join(SCRATCH, "prototype_mismatches_full.txt"), "w", encoding="utf-8") as f:
    for u, va, vb in ex4:
        f.write(f"{u}\t{va!r}\t{vb!r}\n")
print("prototype mismatch count:", len(ex4), "(capped display at 20; see full list logic below)")

# full, uncapped prototype mismatch dump
full_mismatches = []
for u in urls:
    va, vb = ada292.get(u), prototype.get(u)
    if (va is None) != (vb is None) or (va is not None and vb is not None and va != vb):
        full_mismatches.append((u, va, vb))
print("prototype TOTAL mismatches (uncapped):", len(full_mismatches))
with open(os.path.join(SCRATCH, "prototype_mismatches_all.txt"), "w", encoding="utf-8") as f:
    for u, va, vb in full_mismatches:
        f.write(f"{u}\t{va!r}\t{vb!r}\n")
