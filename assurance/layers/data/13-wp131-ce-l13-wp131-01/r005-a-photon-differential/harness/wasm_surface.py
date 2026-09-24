"""Minimal WASM binary section reader: lists imports and exports (no dependencies)."""
import sys


def leb(b, i):
    r = s = 0
    while True:
        x = b[i]; i += 1
        r |= (x & 0x7F) << s; s += 7
        if x < 0x80:
            return r, i


def name(b, i):
    n, i = leb(b, i)
    return b[i:i + n].decode("utf-8"), i + n


b = open(sys.argv[1], "rb").read()
assert b[:4] == b"\0asm", "not wasm"
i = 8
imports, exports = [], []
kinds = {0: "func", 1: "table", 2: "memory", 3: "global"}
while i < len(b):
    sid = b[i]; i += 1
    size, i = leb(b, i)
    end = i + size
    if sid == 2:
        n, j = leb(b, i)
        for _ in range(n):
            mod, j = name(b, j); fld, j = name(b, j); k = b[j]; j += 1
            if k == 0: _, j = leb(b, j)
            elif k == 1: j += 1; fl = b[j]; j += 1; _, j = leb(b, j); j = leb(b, j)[1] if fl & 1 else j
            elif k == 2: fl = b[j]; j += 1; _, j = leb(b, j); j = leb(b, j)[1] if fl & 1 else j
            elif k == 3: j += 2
            imports.append((mod, fld, kinds[k]))
    elif sid == 7:
        n, j = leb(b, i)
        for _ in range(n):
            fld, j = name(b, j); k = b[j]; j += 1; _, j = leb(b, j)
            exports.append((fld, kinds[k]))
    i = end
print(f"imports: {len(imports)}")
for m, f, k in imports:
    print(f"  {k:6} {m}.{f}")
print(f"exports: {len(exports)}")
want = sys.argv[2:] if len(sys.argv) > 2 else []
for f, k in exports:
    if not want or any(w in f for w in want):
        print(f"  {k:6} {f}")
