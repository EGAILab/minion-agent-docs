# R002 direct Ada 2.9.2 reference oracle -- reproduction

Committed per the independent checkpoint rejection at `minion-agent-docs#120` @
`2a99d49371b740f0a4a01862383143478672b660`, which required characterizing the concrete version
relationship among Node's URL/ICU behavior and the Unicode/UTS46 data a Python reimplementation
would use, rather than trusting the WHATWG prose alone. This directory holds a DIRECT executable
oracle built from the exact Ada C++ library Node v22.19.0 vendors, so Python/Rust candidates can
be differentially tested against the real reference implementation, not a standards description
of it.

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

## `systematic_corpus.txt`

8,244 cases: one representative codepoint per non-ASCII interval in `idna.uts46data`'s own
interval table (`idna==3.19`, 8,372 total intervals; ASCII and surrogate-range intervals
excluded), each placed in a Punycode-encoded single-label host as `a<codepoint>` (a leading `a`
avoids conflating the "leading combining mark" structural rule with the specific codepoint being
swept), formatted as `file://xn--.../share`. This mirrors the independent review's own stated
methodology ("one or more representative codepoints from every interval in `idna.uts46data`")
so results are comparable. Generation is mechanical and reproducible from `idna`'s own installed
data; regenerate with the snippet in `compare_oracles.py`'s own header comment if `idna` is
upgraded.

## Raw oracle outputs (committed for reproducibility, not just summarized)

- `systematic_node_22190.txt` / `systematic_node_22232.txt`: `systematic_node_probe.mjs` run
  against checksum-verified Node v22.19.0 (Pi's declared floor) and v22.23.2 (drift check).
  **Zero differences between the two** (every one of the 8,244 rows identical).
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
- `prototype_mismatches_all.txt`: every one of the rejected prototype's mismatches against the
  direct Ada 2.9.2 oracle, uncapped (59 rows over this corpus).

## `compare_oracles.py`

Loads all of the above, reports `accept_mismatch`/`output_mismatch` counts for each pairing, and
prints example rows. Reproduce with:

```sh
python compare_oracles.py
```

(run from this directory; expects the `systematic_*.txt` files alongside it).

## Headline results (this corpus, 8,244 cases)

```text
Node v22.19.0  vs  Node v22.23.2        : 0 mismatches (drift check, as established elsewhere)
Node v22.19.0  vs  direct Ada 2.9.2     : 0 mismatches  <- Strategy A's premise, PROVEN
direct Ada 2.9.2  vs  ada-url==1.15.3   : 0 mismatches  <- exact-parity PyPI release identified
direct Ada 2.9.2  vs  ada-url==4.0.0    : 115 accept mismatches, 0 output mismatches
    (Unicode-codepoint-assignment-boundary differences -- codepoints newly assigned between
    Ada 2.9.2's and Ada 4.0.0's respective data-generation snapshots; NOT an algorithm difference)
direct Ada 2.9.2  vs  rejected prototype: 59 mismatches, 58/59 in ONE direction (Ada accepts,
    prototype rejects) -- NOT explained by Unicode-version alignment alone; idna.uts46data's own
    VALID/DEVIATION table is not a faithful proxy for Ada's actual (differently-structured)
    validity gate, independent of which Unicode version that table targets
```
