# R002 direct Ada 2.9.2 reference oracle -- reproduction

Committed per the independent checkpoint rejection at `minion-agent-docs#120` @
`2a99d49371b740f0a4a01862383143478672b660`, which required characterizing the concrete version
relationship among Node's URL/ICU behavior and the Unicode/UTS46 data a Python reimplementation
would use, rather than trusting the WHATWG prose alone. This directory holds a DIRECT executable
oracle built from the exact Ada C++ library Node v22.19.0 vendors, so Python/Rust candidates can
be differentially tested against the real reference implementation, not a standards description
of it.

**Revision 3** (this version): corrects two further assurance defects an independent checkpoint
re-review found in revision 2 (`minion-agent-docs#120` @
`93a44820695d4ec6ce413230cfa0dac1b31d2663`) -- see "What changed in revision 3" below. That
review independently confirmed the exact witnesses, all 8,246 key sets, a fresh
`ada-url==1.15.3` exact match, the Ada LTR-bidi source bug, and the 55/61 taxonomy -- none of
that is revisited here; only the two defects it found are fixed.

**Revision 2**: corrected three assurance defects an earlier independent checkpoint re-review
found in the first committed version (`minion-agent-docs#120` @
`8c1469c1de13cf0a70dab9f6d4bcfd8abcd8e32e`) -- see "What changed in revision 2" below. The
central Strategy A result (`ada-url==1.15.3` matches the direct Ada 2.9.2 oracle exactly) was
independently reproduced by that review and remains unchanged.

## Provenance

- `ada-2.9.2.h` / `ada-2.9.2.cpp`: the official single-header amalgamation of the Ada URL C++
  library, tag `v2.9.2`, downloaded from
  `https://github.com/ada-url/ada/releases/download/v2.9.2/ada.h` and
  `https://github.com/ada-url/ada/releases/download/v2.9.2/ada.cpp`.
  SHA-256: `ada-2.9.2.h` = `46ecdbdd0e460ed81f5eec0120f7bc144f56a92edf243be43f7f4b9cf0f79eb5`;
  `ada-2.9.2.cpp` = `30f1265b340b928e5e105787bc7af207396903c6c234cc1dca9279a90cec327b`. Confirmed
  `#define ADA_VERSION "2.9.2"` present in the header (`ada-2.9.2.h`, grep `ADA_VERSION`).
- Confirmed this is the EXACT version Node v22.19.0 vendors by reading
  `https://raw.githubusercontent.com/nodejs/node/v22.19.0/src/node_url.cc` directly: line 228
  (`BindingData::DomainToUnicode`) and line 624 (the Windows `file://`-to-path UNC branch) both
  call `ada::idna::to_unicode(hostname)` on a hostname obtained from `ada::parse<ada::url>(...)`'s
  own `get_hostname()` -- the exact call sequence `oracle.cpp` below reproduces.

## `oracle.cpp`

A minimal C++ harness (assurance/research tooling only -- never linked into or shipped with
Minion production code) that mirrors Node's own call sequence exactly:

```text
ada::parse<ada::url>(url) -> get_hostname() -> ada::idna::to_unicode(hostname)
```

Reads one full `file://...` URL per line on stdin, writes `<url>\t<decoded-host>` or
`<url>\tPARSE_ERROR` per line on stdout.

Build (Windows, MSVC -- this is how it was built for this artifact):

```sh
"<VS install>/VC/Auxiliary/Build/vcvars64.bat"
cl.exe /std:c++20 /EHsc /O2 /utf-8 /Fe:oracle.exe oracle.cpp ada-2.9.2.cpp
```

(rename `ada-2.9.2.cpp`/`.h` to `ada.cpp`/`ada.h` alongside `oracle.cpp`, or adjust the
`#include "ada.h"` path -- the header is included in the source tree here under the versioned
name to make the exact pinned source unambiguous). Any C++20 compiler on any platform (g++,
clang++) builds this identically -- there is nothing MSVC-specific in `oracle.cpp` itself.

## `systematic_node_probe.mjs`

Reads a newline-delimited file of `file://...` URLs (a path given as `process.argv[2]`) and
runs each through `node:url`'s own `fileURLToPath(url, {windows: true})`, writing the same
`<url>\t<result-or-PARSE_ERROR>` shape (JSON-quoted Windows path on success) so its output is
directly comparable to `oracle.cpp`'s own output via `compare_oracles.py`.

## `generate_corpus.py` -- the actual, committed, deterministic corpus generator

Requires `idna` installed (a `minion-agent-python` project dependency) -- run it with THAT
project's own interpreter, e.g. from a `minion-agent-python` checkout:
`uv run python <path-to-this-file>/generate_corpus.py > systematic_corpus.txt`. A bare system
Python without `idna` installed fails with `ModuleNotFoundError`, not a script defect -- this is
a missing prerequisite, not a harness bug. Read-only
over the installed `idna` package's own `idna.uts46data` interval table; writes nothing except
the corpus file itself when run this way. Re-verified byte-for-byte identical to the committed
`systematic_corpus.txt` before this revision was written.

Produces **8,246 cases**:

- **4 permanent named regression witnesses**, always present verbatim regardless of how the
  interval-sweep portion changes as `idna`'s own data is upgraded:
  - `file://xn--3pc/share` -- the exact bare A-label from independent review evidence
    (`minion-agent-docs#120` @ `2a99d49371b740f0a4a01862383143478672b660`) that Node/Ada 2.9.2
    ACCEPTS (decodes to U+0C3C TELUGU SIGN NUKTA).
  - `file://xn--8g0n/share` -- the same evidence's REJECTED witness (U+2EBF0 CJK UNIFIED
    IDEOGRAPH-2EBF0, unassigned in Ada 2.9.2's own ~2024 Unicode snapshot).
  - `file://xn--a-y5e/share` / `file://xn--a-8n62a/share` -- the SAME two codepoints in the
    leading-`"a"`-prefixed shape the interval sweep below uses, so the permanent-witness set and
    the sweep-derived set overlap in a checkable way rather than silently testing disjoint
    things.
- **8,242 interval-sweep cases**: one representative codepoint per non-ASCII, non-surrogate
  interval in `idna.uts46data`'s own interval table (`idna==3.19`, 8,372 total intervals), each
  placed in a Punycode-encoded single-label host as `a<codepoint>` (a leading `a` avoids
  conflating the "leading combining mark" structural rule with the specific codepoint being
  swept), formatted as `file://xn--.../share`. This mirrors the independent review's own stated
  methodology ("one or more representative codepoints from every interval in `idna.uts46data`")
  so results are comparable.

## Raw oracle outputs (committed for reproducibility, not just summarized)

- `systematic_node_22190.txt` / `systematic_node_22232.txt`: `systematic_node_probe.mjs` run
  against checksum-verified Node v22.19.0 (Pi's declared floor) and v22.23.2 (drift check).
  **Zero differences between the two** (every one of the 8,246 rows identical).
- `systematic_ada292.txt`: `oracle.cpp` (this directory's own compiled binary) run against the
  same corpus.
- `systematic_pyada_1153.txt`: Python `ada-url==1.15.3` (installed in an isolated scratch venv),
  driven through the two-step pipeline `ada_url.URL(u).host` then `ada_url.idna_to_unicode(host)`
  (treating an unchanged `"xn--..."` result as rejected, matching `oracle.cpp`'s own convention).
- `systematic_pyada_400.txt`: the SAME two-step pipeline against the project's then-current
  pinned `ada-url==4.0.0`.
- `systematic_prototype_rejected.txt`: the checkpoint-rejected `idna.uts46data`-driven decode
  prototype (`minion-agent-docs#121` @ `854f5c1097b9aa2aee2494bd378753961d478314`) run against
  the same corpus, for direct root-cause reclassification.
- `prototype_mismatches_all.txt`: every one of that rejected prototype's mismatches against the
  direct Ada 2.9.2 oracle, uncapped (61 rows over this corpus).

## `compare_oracles.py`

Loads all of the above BY THEIR ACTUAL COMMITTED FILENAMES (this revision's own fix -- the prior
version referenced filenames that did not match what was actually committed), reports
`accept_mismatch`/`output_mismatch` counts for each pairing including the DECISIVE Ada-2.9.2-vs-
`ada-url==1.15.3` comparison (the prior version omitted this from the script itself, computing it
only in an uncommitted one-off check), and additionally splits the Ada-2.9.2-vs-`ada-url==4.0.0`
mismatches into two evidence-supported root-cause groups (see below) rather than a single
generic count. Reproduce with:

```sh
python compare_oracles.py
```

(run from this directory; expects every `systematic_*.txt` file alongside it, all committed).

## What changed in revision 3

The independent checkpoint re-review of revision 2 (`minion-agent-docs#120` @
`93a44820695d4ec6ce413230cfa0dac1b31d2663`) independently confirmed the exact witnesses, all
8,246 keys across every dataset, a fresh isolated `ada-url==1.15.3` run, the Ada LTR-bidi source
bug and its Node controls, and the 55/61 taxonomy against official Unicode assignment data.
Agreement was withheld on two further, narrower defects, both fixed here:

1. **`compare_oracles.py` crashed on a default Windows console** and did not enforce corpus
   counts, key-set uniqueness, or key-set equality across the five loaded datasets. Fixed: the
   script now calls `sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")` before
   printing anything (verified under a forced cp1252 console codepage -- completes with exit
   code 0, where it previously raised `UnicodeEncodeError` partway through); `load_node`/
   `load_bare` now reject a duplicate key within a single file; a new `check_corpus_integrity`
   function verifies all five datasets share an IDENTICAL key set, of the exact size
   `generate_corpus.py`'s own `EXPECTED_CASE_COUNT` produces, before any comparison count is
   trusted or printed -- a dataset silently missing or gaining rows (e.g. a stale/truncated
   regeneration) now fails loudly instead of silently under-reporting mismatches. `generate_corpus.py`
   itself now refuses to run against a different `idna` package version than the one this corpus
   was reviewed against (`EXPECTED_IDNA_VERSION`), so an `idna` upgrade cannot silently redefine
   what the corpus samples.

2. **The claim that `ada-url==1.15.3` "has neither defect" -- including the Group A bidi bug --
   was backwards.** Exact parity with the pinned Ada 2.9.2 oracle REQUIRES reproducing Group A's
   bug, not avoiding it; the prior wording ("it postdates the fix") was the opposite of what the
   evidence shows. Fixed: `compare_oracles.py` now includes
   `check_ada_url_1153_reproduces_group_a_bug`, which explicitly confirms, as POSITIVE evidence
   (not merely an absence of mismatches), that `ada-url==1.15.3` gives the exact same (buggy)
   output Ada 2.9.2 does for every one of the 55 Group-A witnesses -- e.g. it silently accepts
   `xn--ab-wld` exactly as Ada 2.9.2 does, not the `ada-url==4.0.0` fixed behavior. `ada-url`'s
   own fix was made LATER, between `1.15.3`'s release and `4.0.0`'s -- `1.15.3` PREDATES the fix,
   not postdates it.

## What changed in revision 2

The independent checkpoint re-review (`minion-agent-docs#120` @
`8c1469c1de13cf0a70dab9f6d4bcfd8abcd8e32e`) reproduced the central Strategy A result but withheld
agreement on three narrow assurance defects, all corrected here:

1. **Exact witnesses now literally present.** `xn--3pc`/`xn--8g0n` are now committed verbatim in
   `systematic_corpus.txt` (via `generate_corpus.py`'s own `PERMANENT_WITNESSES` list), not
   merely represented by a differently-shaped (`"a"`-prefixed) proxy case.
2. **Reproduction tooling now actually works as committed.** `compare_oracles.py` was previously
   an ad-hoc scratch script whose filenames didn't match what got committed, and never included
   the decisive `ada-url==1.15.3` comparison at all (that number came from an UNCOMMITTED
   one-off check). `generate_corpus.py` -- the actual corpus generator -- did not exist as a
   committed file; the corpus's own provenance was described only in prose. Both are now real,
   committed, runnable, and were re-verified end to end from a clean directory before this
   revision was written.
3. **The `ada-url==4.0.0` mismatch taxonomy is now evidence-supported, not asserted.** The prior
   revision claimed "all [mismatches] are ... assignment-boundary differences" and then cited
   `U+05D0 HEBREW LETTER ALEF` -- a codepoint assigned since Unicode 1.0 -- as an example,
   directly contradicting its own claim. Investigating that specific contradiction found a
   REAL, verified-in-source bug: `ada-2.9.2.cpp`'s own `is_label_valid` function validates an
   LTR-classified label's bidi properties with the loop `for (i = 0; i < last_non_nsm_char; i++)`
   -- strictly less than, so the label's own LAST non-NSM character is NEVER evaluated against
   the LTR-allowed bidi-property set. A 2-character label like `"a" + <RTL codepoint>` has that
   RTL codepoint AS its last (and only non-initial) character, so it is silently never checked;
   Ada 2.9.2 wrongly ACCEPTS it. Reproduced independently with constructed witnesses
   `xn--ab-wld` (decodes to `"ab" + HEBREW ALEF`, accepted -- same bug, confirmed against both
   the direct oracle and live Node v22.19.0) versus `xn--ab-uld` (`HEBREW ALEF + "ab"`, an
   RTL-INITIAL label taking the OTHER code branch, correctly rejected by both). `ada-url==4.0.0`
   does not reproduce this bug (it correctly rejects these cases) -- a genuine ALGORITHM/bugfix
   difference between Ada versions, not a Unicode-data-table version difference.

   The corrected classification, computed mechanically by `compare_oracles.py` itself (see
   `classify_ada292_vs_ada400_mismatches`), splits all 116 mismatches (was reported as 115 before
   the two bare-form permanent witnesses were added to the corpus) into:

   - **Group A -- Ada 2.9.2's own LTR-bidi off-by-one bug, fixed in `ada-url==4.0.0`: 55/116.**
     Every member's swept codepoint has a Unicode bidirectional category outside
     `{L,EN,ES,CS,ET,ON,BN,NSM}` (i.e. is itself R/AL/AN or similarly RTL-restricted), Ada 2.9.2
     accepted it, and `ada-url==4.0.0` correctly rejected it -- matching the bug's own exact
     verified shape. `U+05D0` (the contradicting example from the prior revision) is in this
     group, not the assignment-boundary group.
   - **Group B -- genuine Unicode-codepoint-assignment-boundary difference: 61/116.** The swept
     codepoint was unassigned in Ada 2.9.2's own (~Unicode-16-era) data but has since been
     assigned -- matches the `xn--8g0n`/U+2EBF0 witness's own shape exactly (including
     `xn--8g0n` itself and its `"a"`-prefixed sibling `xn--a-8n62a`, both now in this group since
     they are permanent witnesses added to the corpus).

   Neither group affects the Strategy A recommendation, but NOT because `ada-url==1.15.3` avoids
   either defect -- the opposite: exact parity with the pinned oracle REQUIRES reproducing Group
   A's bug too, not avoiding it. `compare_oracles.py`'s own
   `check_ada_url_1153_reproduces_group_a_bug` confirms this directly, not merely by the absence
   of a mismatch count: for every one of the 55 Group-A witnesses, `ada-url==1.15.3` gives the
   EXACT SAME (buggy) output Ada 2.9.2 does -- it silently accepts `xn--ab-wld` (`"ab" + HEBREW
   LETTER ALEF`) exactly as Ada 2.9.2 does, not the `ada-url==4.0.0` fixed behavior. `ada-url`'s
   own fix for this bug was made LATER, sometime between `1.15.3`'s release and `4.0.0`'s --
   `1.15.3` PREDATES it, not postdates it. Group B (assignment-boundary) is a genuinely
   version-boundary-sensitive gap `ada-url==1.15.3` also avoids, but for the ordinary reason
   that it shares Ada 2.9.2's own Unicode-data snapshot almost exactly (confirmed by the
   0/8246 result below), not because of anything specific to Group A's own bug.

## Headline results (this corpus, 8,246 cases)

```text
Node v22.19.0  vs  Node v22.23.2        : 0 mismatches (drift check)
Node v22.19.0  vs  direct Ada 2.9.2     : 0 mismatches  <- Strategy A's premise, PROVEN
direct Ada 2.9.2  vs  ada-url==1.15.3   : 0 mismatches  <- exact-parity PyPI release,
    INDEPENDENTLY REPRODUCED TWICE by checkpoint re-reviews (docs PR #120 @ 8c1469c1, @ 93a4482)
ada-url==1.15.3 reproduces all 55 Group-A (Ada 2.9.2 bidi-bug) witnesses IDENTICALLY -- positive
    evidence the exact match includes the bug, not evidence the bug was avoided
direct Ada 2.9.2  vs  ada-url==4.0.0    : 116 accept mismatches, 0 output mismatches
    Group A (Ada 2.9.2's own LTR-bidi off-by-one bug, verified in source, fixed in 4.0.0): 55
    Group B (genuine Unicode-codepoint-assignment-boundary difference): 61
direct Ada 2.9.2  vs  rejected prototype (idna.uts46data-driven): 61 mismatches
    (historical evidence from the prior characterization round; not re-litigated here)

corpus integrity: all 5 oracle-output datasets share an identical 8,246-key set, matching
    generate_corpus.py's own generate_urls() exactly (compare_oracles.py's own
    check_corpus_integrity, verified to run and exit 0 under a forced cp1252 console codepage)
```
