"""Deterministic, read-only generator for the R002 systematic differential corpus.

Produces one representative codepoint per non-ASCII, non-surrogate interval in the
currently-installed `idna` package's own `idna.uts46data` interval table (one Punycode-encoded
single-label `file://xn--.../share` URL per codepoint, prefixed with a leading "a" so the swept
codepoint is never the label's own first character -- isolating it from the separate
leading-combining-mark structural rule), PLUS a fixed set of permanent named regression
witnesses that must always be present verbatim regardless of how the interval-sweep portion
changes as `idna`'s own data is upgraded.

Run from this directory: `python generate_corpus.py > systematic_corpus.txt`
(or import `generate_urls()` directly, as `compare_oracles.py` does).

Never modifies any file; reads only `idna.uts46data` (an installed third-party package).
"""

from __future__ import annotations

from idna.uts46data import uts46_starts

# Permanent named regression witnesses (Layer 12 CE-L12-PY-01-01, L12-PY-R002). These are the
# EXACT strings independent review evidence supplied and MUST always be present in the
# generated corpus verbatim -- not merely "a case exercising the same codepoint" via the
# interval sweep below, which uses a DIFFERENT (leading-"a"-prefixed) label shape.
PERMANENT_WITNESSES = [
    # minion-agent-docs#120 @ 2a99d49371b740f0a4a01862383143478672b660 (checkpoint rejection,
    # revision 1 of this characterization): Node/Ada 2.9.2 ACCEPTS this bare A-label
    # (decodes to U+0C3C TELUGU SIGN NUKTA, a leading combining mark on its own -- accepted
    # here specifically because it is presented as an ALREADY-formed Punycode label with
    # nothing before it to make it "leading" in the structural sense the leading-combining-mark
    # rule actually tests; see the root-characterization artifact's own section on this).
    "file://xn--3pc/share",
    # Same evidence source: Node/Ada 2.9.2 REJECTS this bare A-label (decodes to U+2EBF0 CJK
    # UNIFIED IDEOGRAPH-2EBF0 -- unassigned in Ada 2.9.2's own ~2024 Unicode data snapshot).
    "file://xn--8g0n/share",
    # Controls: the same two codepoints in the leading-"a"-prefixed shape the interval sweep
    # uses, so the permanent-witness set and the sweep-derived set overlap in a checkable way
    # rather than silently testing disjoint things.
    "file://xn--a-y5e/share",  # "a" + U+0C3C (a + TELUGU SIGN NUKTA)
    "file://xn--a-8n62a/share",  # "a" + U+2EBF0
]


def generate_urls() -> list[str]:
    urls: list[str] = list(PERMANENT_WITNESSES)
    seen_alabels = {u[len("file://") : -len("/share")] for u in PERMANENT_WITNESSES}
    for cp in uts46_starts:
        if cp < 0x80:
            continue  # ASCII already covered by ordinary letters/digits
        if 0xD800 <= cp <= 0xDFFF:
            continue  # surrogate range -- not a valid scalar value
        if cp > 0x10FFFF:
            continue
        try:
            ch = chr(cp)
        except ValueError:
            continue
        decoded = "a" + ch
        try:
            alabel = "xn--" + decoded.encode("punycode").decode("ascii")
        except UnicodeError:
            continue
        if alabel in seen_alabels:
            continue
        seen_alabels.add(alabel)
        urls.append(f"file://{alabel}/share")
    return urls


if __name__ == "__main__":
    for url in generate_urls():
        print(url)
