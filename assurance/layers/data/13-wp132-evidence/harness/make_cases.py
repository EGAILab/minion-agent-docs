"""WP-13.2 authority corpus: deterministic cases for the pinned-Pi edit/write authority (edit_authority.mjs).

    python make_cases.py <out.json>

Curated cases cover every rule in spec/tools.md WP-13.2; a seeded random set adds differential breadth. Strings may
contain unpaired surrogates; json.dumps writes them as \\uXXXX escapes, which JSON.parse restores exactly.
"""
import base64
import json
import random
import sys

P = "src/app.txt"
cases = []


def enc(text, bom=False):
    data = text.encode("utf-8", "surrogatepass")
    return base64.b64encode((b"\xef\xbb\xbf" if bom else b"") + data).decode()


def edit(cid, text, edits, path=P, bom=False, raw_bytes=None):
    fb = base64.b64encode(raw_bytes).decode() if raw_bytes is not None else enc(text, bom)
    cases.append({"id": cid, "kind": "edit", "args": {"path": path, "edits": [{"oldText": o, "newText": n} for o, n in edits]},
                  "file_b64": fb})


def write(cid, content, path=P):
    cases.append({"id": cid, "kind": "write", "path": path, "content": content})


def prepare(cid, raw_args):
    cases.append({"id": cid, "kind": "edit", "prepare": True, "raw_args": raw_args,
                  "file_b64": base64.b64encode(b"x\na\n").decode()})


def fuzzy(cid, text):
    cases.append({"id": cid, "kind": "fuzzy", "text": text})


# ---- exact matching, multi-edit, diagnostics (TOOL-030)
edit("exact-single", "alpha\nbeta\ngamma\n", [("beta", "BETA")])
edit("exact-multi-out-of-order", "one\ntwo\nthree\nfour\nfive\n", [("four", "4"), ("one", "1"), ("three", "3")])
edit("adjacent-not-overlapping", "abcdef\n", [("abc", "X"), ("def", "Y")])
edit("overlap", "abcdef\n", [("abcd", "X"), ("cdef", "Y")])
edit("overlap-reported-in-sorted-order", "abcdef\n", [("cdef", "Y"), ("abcd", "X")])
edit("not-found-single", "alpha\n", [("zeta", "Z")])
edit("not-found-multi", "alpha\nbeta\n", [("alpha", "A"), ("zeta", "Z")])
edit("empty-old-single", "alpha\n", [("", "x")])
edit("empty-old-multi", "alpha\n", [("alpha", "A"), ("", "x")])
edit("empty-old-after-lf-normalization-is-not-empty", "a\r\nb\n", [("\r\n", "|")])
edit("duplicate-exact-single", "x = 1\nx = 1\n", [("x = 1", "x = 2")])
edit("duplicate-exact-multi", "a\nb\nb\n", [("a", "A"), ("b", "B")])
edit("duplicate-only-in-fuzzy-space", "foo \nfoo\n", [("foo ", "bar")])
edit("no-change-single", "alpha\n", [("alpha", "alpha")])
edit("no-change-multi", "alpha\nbeta\n", [("alpha", "alpha"), ("beta", "beta")])
edit("replace-with-empty", "keep\ndrop me\nkeep\n", [("drop me\n", "")])
edit("multiline-old-and-new", "fn a() {\n  1\n}\n", [("fn a() {\n  1\n}", "fn a() {\n  2\n  3\n}")])
edit("old-text-crlf-normalized", "a\nb\n", [("a\r\nb", "c\r\nd")])

# ---- fuzzy matching, preservation (TOOL-031)
edit("fuzzy-trailing-ws", "keep   \nalpha  \nbeta\t\ntail  \n", [("alpha\nbeta", "ALPHA\nBETA")])
edit("fuzzy-spreads-to-all-edits", "one   \ntwo  \nthree\n", [("three", "3"), ("one\ntwo", "1\n2")])
edit("fuzzy-smart-quotes", "say ‘hi’ and “bye”\n", [("say 'hi' and \"bye\"", "said")])
edit("fuzzy-dashes", "a–b—c−d‐e‑f‒g―h\n", [("a-b-c-d-e-f-g-h", "dashes")])
edit("fuzzy-special-spaces", "x y z w v　u\n", [("x y z w v u", "spaces")])
edit("fuzzy-nfkc-ligature", "a ﬁle here   \n", [("a file here", "ok")])
edit("fuzzy-nfkc-fullwidth", "ＡＢＣ \n", [("ABC", "abc")])
edit("fuzzy-nfkc-unicode16-outlined", "\U0001CCD6 x  \n", [("A x", "hit")])
edit("fuzzy-nfkc-unicode17-new-stays", "꟱ keep  \nzz  \n", [("zz", "ZZ")])
edit("fuzzy-nfkc-unicode17-on-touched-line", "꟱ z’z  \nkeep\n", [("z'z", "ZZ")])
edit("fuzzy-preserves-untouched-lines", "  untouched  \nt’x  \n\ttrail \t\n", [("t'x", "T")])
edit("fuzzy-two-edits-same-line", "ab  cd  ef  \n", [("ab", "1"), ("ef", "3")])
edit("fuzzy-duplicate-normalized-lines", "x  \nx\nx \n", [("x\nx\nx", "y")])
edit("js-whitespace-set", "a\u0085\nb\u001c\nc　\nd﻿\ne \nf \n", [("a\u0085\nb\u001c\nc\nd\ne\nf", "W")])
edit("nel-is-not-js-whitespace", "p\u0085 \nq\n", [("p\nq", "PQ")])
edit("info-separator-is-not-js-whitespace", "p\u001c\nq\n", [("p\nq", "PQ")])
edit("empty-normalized-old-counts-code-units", "ab\U0001F600c\n", [("   ", "X")])
edit("empty-normalized-old-short-content", "a", [("  ", "X")])
edit("empty-normalized-old-empty-file", "", [("  ", "X")])
edit("empty-normalized-old-two-units", "ab", [("\t", "X")])
# INTERNAL (line count): under fuzzy mode a final whitespace-only line without "\n" trims to nothing, so the base
# has one line fewer than the original (lines() drops an empty final segment); a smart quote forces fuzzy mode.
edit("internal-line-count-whitespace-only-last-line", "a’\n   ", [("a'", "b")])
edit("internal-line-count-crlf-whitespace-last-line", "x“\r\ny\r\n\t ", [('x"', "z")])

# ---- BOM and line endings (TOOL-031)
edit("bom-kept", "alpha\nbeta\n", [("beta", "B")], bom=True)
edit("crlf-first", "a\r\nb\r\nc\r\n", [("b", "B")])
edit("crlf-first-with-lone-cr", "a\r\nb\rc\nd\r\n", [("c", "C")])
edit("lf-first-then-crlf", "a\nb\r\nc\r\n", [("c", "C")])
edit("cr-only", "a\rb\rc", [("b", "B")])
edit("no-final-newline", "alpha\nbeta", [("beta", "BETA")])
edit("add-final-newline", "alpha\nbeta", [("beta", "beta\n")])
edit("bom-and-crlf", "x\r\ny\r\n", [("y", "Y")], bom=True)

# ---- decoding / encoding / UTF-16 semantics
edit("invalid-utf8-decoded", "", [("A", "B")], raw_bytes=b"\xff\xfeA\n")
edit("astral-in-content", "\U0001F600 one \U0001F601\nthe end\n", [("one", "1"), ("end", "END")])
edit("lone-surrogate-new-text", "alpha\n", [("alpha", "a\ud800b")])
write("write-ascii", "hello\n")
write("write-multibyte", "café naïve\n")
write("write-astral", "\U0001F600\U0001F601")
write("write-lone-surrogate", "x\udc00y")
write("write-empty", "")

# ---- diff / patch shapes (details)
base_lines = [f"line {i}" for i in range(1, 41)]
edit("diff-two-hunks", "\n".join(base_lines) + "\n", [("line 5\n", "LINE 5\n"), ("line 30\n", "LINE 30\n")])
edit("diff-joined-context-8", "\n".join(base_lines) + "\n", [("line 10\n", "L10\n"), ("line 19\n", "L19\n")])
edit("diff-split-context-9", "\n".join(base_lines) + "\n", [("line 10\n", "L10\n"), ("line 20\n", "L20\n")])
edit("diff-no-newline-at-eof", "a\nb\nc", [("c", "C")])
edit("diff-insert-lines", "a\nb\n", [("a\n", "a\nx\ny\nz\n")])
edit("diff-delete-lines", "a\nx\ny\nz\nb\n", [("x\ny\nz\n", "")])
edit("diff-width-changes", "\n".join(base_lines[:9]) + "\n", [("line 9", "line 9\nline 10\nline 11")])
edit("diff-repeated-lines-myers", "a\nb\na\nb\na\nb\n", [("b\na\nb\na", "b\nZ\nb\nZ")])

# ---- prepareEditArguments (edit.ts:116-147)
prepare("prepare-json-string-array", {"path": P, "edits": json.dumps([{"oldText": "a", "newText": "b"}])})
prepare("prepare-json-string-single", {"path": P, "edits": json.dumps({"oldText": "a", "newText": "b"})})
prepare("prepare-json-string-invalid", {"path": P, "edits": "[not json"})
prepare("prepare-json-string-other", {"path": P, "edits": json.dumps(42)})
prepare("prepare-single-object", {"path": P, "edits": {"oldText": "a", "newText": "b", "extra": 1}})
prepare("prepare-legacy-top-level", {"path": P, "oldText": "a", "newText": "b"})
prepare("prepare-legacy-appends", {"path": P, "edits": [{"oldText": "x", "newText": "y"}], "oldText": "a", "newText": "b"})
prepare("prepare-legacy-non-string-ignored", {"path": P, "oldText": "a", "newText": 3})
# JSON.parse numbers are IEEE-754 doubles: a 5000-digit integer is Infinity, not a parse failure
# (L13-WP132-I002, implementation review docs #192).
prepare("prepare-json-string-huge-integer-extra",
        {"path": P, "edits": '{"oldText": "a", "newText": "b", "extra": ' + "9" * 5000 + "}"})
prepare("prepare-not-an-object", "just a string")
cases.append({"id": "validate-empty-edits", "kind": "edit", "args": {"path": P, "edits": []}, "file_b64": enc("x\n")})

# ---- fuzzy_normalize directly
for cid, t in [("fz-trim-set", "a \t\u000b\u000c ﻿     　  \n"),
               ("fz-not-trimmed", "a\u0085\u001c\u001d\u001e\u001f᠎​\n"),
               ("fz-nfkc-compose", "é Å ẛ̣ ｶﾞ"),
               ("fz-quotes-dashes-spaces", "‘’‚‛“”„‟‐‑‒–—―−     　"),
               ("fz-unicode16-17", "\U0001CCD6\U0001CCF9꟱")]:
    fuzzy(cid, t)

# ---- seeded random differential cases
ALPHA = ["a", "b", "c", " ", "  ", "\t", "’", "“", "—", " ", "ﬁ", "\U0001F600", "é",
         "é", "　", "x", "y", "\u0085"]
rng = random.Random(0x132)
for i in range(300):
    lines = ["".join(rng.choice(ALPHA) for _ in range(rng.randint(0, 6))) for _ in range(rng.randint(1, 8))]
    sep = rng.choice(["\n", "\n", "\r\n"])
    text = sep.join(lines) + rng.choice(["", sep])
    edits = []
    for _ in range(rng.randint(1, 3)):
        norm = text.replace("\r\n", "\n")
        if norm and rng.random() < 0.85:
            a = rng.randrange(len(norm))
            b = min(len(norm), a + rng.randint(1, 8))
            old = norm[a:b]
            if rng.random() < 0.4:
                old = old.replace("’", "'").replace("—", "-").replace(" ", " ").replace("ﬁ", "fi")
            if rng.random() < 0.2:
                old = old.rstrip(" \t")
        else:
            old = "".join(rng.choice(ALPHA) for _ in range(rng.randint(1, 3)))
        new = "".join(rng.choice(ALPHA + ["\n"]) for _ in range(rng.randint(0, 5)))
        edits.append((old, new))
    edit(f"random-{i:03d}", text, edits, bom=rng.random() < 0.1)

ids = [c["id"] for c in cases]
assert len(ids) == len(set(ids))
with open(sys.argv[1], "w", encoding="utf-8", newline="\n") as f:
    json.dump(cases, f, ensure_ascii=True, indent=1)
print(len(cases), "cases")
