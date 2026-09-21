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

Never modifies any file; reads only `idna.uts46data` (an installed third-party package) and
`importlib.metadata` (stdlib). Refuses to run against an `idna` version other than the one this
corpus was originally generated and reviewed against (`EXPECTED_IDNA_VERSION` below) -- an
upgraded `idna` may renumber its own interval table, silently changing which codepoints this
generator samples and invalidating the reviewed provenance of the committed corpus. Regenerating
against a newer `idna` is a deliberate act: bump `EXPECTED_IDNA_VERSION` explicitly and note the
regeneration in the characterization artifact's own history, rather than letting a routine
dependency upgrade silently redefine what this corpus tests.
"""

from __future__ import annotations

import importlib.metadata
import sys

from idna.uts46data import uts46_starts

EXPECTED_IDNA_VERSION = "3.19"

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

# Expected total case count for EXPECTED_IDNA_VERSION -- a corpus-shape assertion, checked by
# both this generator and compare_oracles.py, so a silent idna-table change (even one that
# somehow bypassed the version guard above, e.g. a patch release that edits the table without a
# version bump) is still caught by a mismatched count rather than passing through unnoticed.
EXPECTED_CASE_COUNT = 8246


def _check_idna_version() -> None:
    installed = importlib.metadata.version("idna")
    if installed != EXPECTED_IDNA_VERSION:
        print(
            f"generate_corpus.py: installed idna=={installed} does not match "
            f"EXPECTED_IDNA_VERSION=={EXPECTED_IDNA_VERSION} this corpus was generated and "
            f"reviewed against. idna.uts46data's own interval table may have changed, which "
            f"would silently change which codepoints this generator samples. Regenerating "
            f"against a different idna version is a deliberate act -- bump "
            f"EXPECTED_IDNA_VERSION explicitly (after confirming the resulting corpus shape)"
            f" rather than suppressing this check.",
            file=sys.stderr,
        )
        raise SystemExit(1)


def generate_urls() -> list[str]:
    _check_idna_version()
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
    if len(urls) != len(set(urls)):
        raise AssertionError("generate_corpus.py produced duplicate URLs -- generator bug")
    if len(urls) != EXPECTED_CASE_COUNT:
        raise AssertionError(
            f"generate_corpus.py produced {len(urls)} cases, expected {EXPECTED_CASE_COUNT} "
            f"for idna=={EXPECTED_IDNA_VERSION} -- the interval table's own shape may have "
            f"changed without a package-version bump; investigate before trusting this corpus"
        )
    return urls


if __name__ == "__main__":
    # Force UTF-8 stdout regardless of the host console's own active codepage (Windows
    # consoles commonly default to a legacy codepage like cp1252, which cannot represent most
    # of this corpus's own swept codepoints and would otherwise raise UnicodeEncodeError before
    # a single line is written) -- these URLs are pure ASCII (Punycode-encoded), so this only
    # matters for robustness against a misconfigured environment, not for THIS script's own
    # output content.
    sys.stdout.reconfigure(encoding="utf-8", errors="strict", newline="\n")
    for url in generate_urls():
        print(url)
