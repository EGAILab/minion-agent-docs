# CE-L13-WP131-01 — Lane C revision 4: `R006-C` correction (version + artifact only)

Mode: §11.8 sub-checkpoint characterization, Lane C, `R006-C` revision only. **No Python or Rust
implementation performed or authorized. No Layer 12 production change. Review this revision only
-- `R003`/`R004`/`R008` remain frozen `CHECKPOINT-READY`, `R002`/`R005` remain
`OWNER_DECISION_RESOLVED`, and `R006-A`/`R006-B` remain `RESOLVED` per `minion-agent-docs#142` @
`104ff6b8b41c6d64695f0c4d7d4cc36724ee9982`; do not reopen any of them unless this revision
presents concrete contradictory evidence.**

Targeted remediation of the independent Lane C revision-3 review (`minion-agent-docs#143` @
`e506a277bb65409d174ce492e78453b4cadc087f`, verdict `R006 CHARACTERIZATION REJECTED`,
`R006-C NOT_RESOLVED`) against Lane C revision 3 (`minion-agent-docs#132` @
`6355431610a6443785dcfcc25fa2deb877c033f0`). That review raised three blocking points against
`R006-C`:

1. `rust_icu_ucol 5.1.0` was claimed current; crates.io reports `5.8.0` as current -- fixed below
   (Correction 3a), verified directly this revision via the crates.io API, not search snippets
   (the earlier `5.1.0` figure came from a stale/cached `WebSearch` result -- see the note at the
   end of Correction 3a).
2. ICU4C 78.3 remained only a named target, not one shared, identifiable build artifact with
   integrity/build discipline -- fixed below (Correction 3b), with a concrete official source
   artifact identified.
3. The candidate's own stated criterion ("any disagreement blocks selection") was not yet
   satisfied because the differential run has not been executed -- **NOT fixed in this revision**;
   this is flagged separately below as an open scope question requiring an owner decision, not a
   documentation-level correction, since satisfying it means compiling and running two new
   ICU-linked native packages (PyICU, `rust_icu_ucol`) outside any certified Python/Rust tree,
   which is a materially different kind of action from this lane's prior direct-verification
   probes (which only queried already-installed runtimes/libraries, installed nothing, and
   compiled nothing).

Corrections 1 and 2 (from revision 2, covering `R006-A`/`R006-B`) remain unchanged and preserved
as the historical, now-resolved record. Only Correction 3 (`R006-C`) is revised, and only its
sub-parts 3a/3b; the differential-execution point (3c) is explicitly left open below.

## Correction 1 -- `R006-A`'s Rust mechanism was wrong; ICU4X is not a host-ICU binding

Revision 1 described the Rust `icu` crate family (ICU4X) as "a system-ICU binding... bound to the
host's installed ICU." **This is incorrect.** ICU4X is an independent, self-contained
reimplementation of ICU algorithms in Rust, explicitly designed to embed its OWN compiled-in
Unicode data (a "baked" or otherwise supplied data provider) rather than link against, or read,
whatever ICU library happens to be installed on the host operating system -- this is one of
ICU4X's own stated core design goals (portability/no host dependency), not an incidental
implementation detail. It therefore does **not** belong in `R006-A` (environment-sensitive, "use
whatever the host provides") at all -- it belongs conceptually with `R006-C` (deterministic,
pinned), since its behavior is fixed by whichever crate version is compiled in, identical on every
machine, regardless of host locale/ICU state.

**Corrected `R006-A` Rust mechanism**: a genuine host-ICU binding requires an actual FFI wrapper
around the system's installed ICU4C library -- the `rust_icu` crate family (e.g. `rust_icu_ucol`
for collation) is such a binding, analogous in spirit to Python's `PyICU`. This is the corrected
`R006-A` Rust candidate, replacing the ICU4X reference.

**Also added (the review's second `R006-A` point)**: Python's `locale.setlocale()` mutates
**process-global** state, not thread-local state -- calling it concurrently from multiple threads,
or from within a long-running process that also performs unrelated work, has effects beyond the
single `ls` call that invoked it (a real operational caveat for any implementation choosing
`R006-A`'s `locale.strxfrm`-based mechanism, not previously disclosed).

## Correction 2 -- `R006-B`'s "FULL reproducibility" claim did not account for real Unicode-version
skew

Revision 1 claimed `toLowerCase()`'s full-mapping table is "a standard Unicode data table any
conformant implementation reproduces identically" and rated `R006-B` "Cross-language
reproducibility: FULL." **Verified this revision, directly, that this is not exactly true**: Node,
Python, and Rust's ICU4X currently ship **different** Unicode data versions.

```text
Node 22.15.1:        unicode 16.0  (process.versions.unicode, verified directly this
                                    revision)
Python 3.13.5:        Unicode 15.1.0  (unicodedata.unidata_version, verified directly
                                       this revision)
Rust icu4x (2.3.x):    Unicode ~17.0 (per the independent reviewer's own verification;
                                      not independently re-derived a third time in this
                                      revision, cited with that provenance)
```

For the vast majority of already-long-assigned characters (including every character in this
lane's own probe corpus -- ASCII, common accented Latin, CJK), case-mapping tables are stable
across these Unicode versions and produce identical `toLowerCase()` output regardless of which
table version is used. But **"FULL" reproducibility is not a correct unqualified claim** -- a
filename containing a character whose case mapping was newly assigned or changed between Unicode
15.1 and 17.0 could observably lowercase differently across these three runtimes.

**Corrected disclosure**: `R006-B`'s reproducibility is `HIGH, not FULL, and contingent on
Unicode-version alignment` -- for the option to be a coherent, fully-specified contract, it must
additionally either (a) explicitly pin a target Unicode version for the case-mapping step (e.g.
requiring each language's case-mapping data to be no older than a stated minimum version, or
exactly a stated version), or (b) explicitly accept and disclose that names containing very
recently (re)assigned characters may lowercase differently across implementations, as a narrow,
bounded residual divergence.

## Correction 3a -- `rust_icu_ucol`'s version was stale; corrected via primary-source lookup

`minion-agent-docs#143` found revision 3's `rust_icu_ucol 5.1.0` claim false: crates.io reports
`5.8.0` as current. **Confirmed independently this revision**, via the crates.io registry API
itself (`https://crates.io/api/v1/crates/rust_icu_ucol`, both `max_stable_version` and
`newest_version` fields), not a search-engine snippet: **`rust_icu_ucol` current is `5.8.0`**. The
earlier `5.1.0` figure came from a `WebSearch` result that was evidently serving a stale/cached
index entry -- re-confirmed by re-running the same query this revision, which still returned
`5.1.0` from search snippets even after the crate had moved to `5.8.0`. **Lesson applied**: for a
fact that will be written into a contract as a pinned version, a registry's own API/JSON endpoint
is verified this revision to be more reliable than search-engine result snippets, which can lag
the registry itself; the corrected candidate below and the `PyICU`/`ICU4C` figures (unaffected by
this specific defect) were re-checked the same way. `rust_icu_ucol` does not itself declare a
minimum/maximum ICU4C version in its published docs (checked this revision via `docs.rs`) -- like
PyICU, it is a build-time FFI binding to whatever ICU4C the build links against, not a version-
pinned wrapper; this is consistent with, and does not change, the build-environment caveat below.

```text
Engine (Python):    PyICU 2.16.2 (current PyPI release, verified this
                     revision via the PyPI JSON API, pypi.org/pypi/pyicu
                     /json; unaffected by the rust_icu_ucol defect).
                     PyICU is an FFI wrapper: it does not bundle its own
                     ICU4C copy, it links against whatever ICU4C the
                     build environment provides.
Engine (Rust):       rust_icu_ucol 5.8.0 (CORRECTED this revision from
                     the false "5.1.0" claim; current crates.io release,
                     verified via the crates.io registry API directly).
                     SELECTED over icu_collator/ICU4X -- because
                     rust_icu_ucol is, like PyICU, a genuine FFI binding
                     to the SAME underlying ICU4C library family, not an
                     independent reimplementation; this maximizes
                     cross-language agreement without requiring the
                     differential corpus to bridge two unrelated
                     codebases. icu_collator/ICU4X is not selected for
                     this candidate (noted below as a rejected
                     alternative, not left open).
ICU4C target:        78.3 (current stable ICU4C release, verified this
                     revision via the unicode-org/icu GitHub releases API;
                     unaffected by the rust_icu_ucol defect). This is a
                     target for the BUILD ENVIRONMENT, not a value either
                     wrapper package pins by itself -- see the caveat
                     below, now made concrete in Correction 3b.
Locale:              "en-001" (SELECTED, not an example -- matching this
                     session's own observed Node default; not "whatever
                     the host's default is," which would collapse this
                     option back into R006-A's own non-determinism)
Collator options:    {usage: "sort", sensitivity: "variant", collation:
                     "default", numeric: false, caseFirst: "false"}
                     (SELECTED -- matching Intl.Collator's own defaults,
                     verified this lane via new Intl.Collator()
                     .resolvedOptions())
```

## Correction 3b -- ICU4C 78.3 given one concrete, checksummed source artifact, not just a version number

`minion-agent-docs#143`'s second blocking point: "78.3" alone names a version, not a build
artifact -- two builds could both claim "ICU4C 78.3" while linking against different bytes (a
source rebuild vs. a distro package vs. a differently-configured build). **Corrected, concrete
artifact identity, verified this revision directly against the official release** (GitHub API,
`unicode-org/icu`, tag `release-78.3`):

```text
Artifact:    icu4c-78.3-sources.tgz, published under the unicode-org/icu
             GitHub release tagged "release-78.3"
             (https://github.com/unicode-org/icu/releases/tag/release-78.3).
             This is the single, official upstream source distribution --
             not a Linux-distro repackaging, not "whatever ICU4C apt/brew
             happens to have," which would silently reintroduce the same
             version-skew class of risk R006-B already disclosed.
Integrity:   the release publishes per-file checksums (a SHASUM512.txt
             covering all release assets, plus detached PGP .asc
             signatures). This characterization pass does NOT transcribe
             the exact checksum value into this document -- doing so
             through a summarizing fetch tool risks a silent
             transcription error in a value whose entire purpose is
             byte-exact verification, which would be worse than omitting
             it. Implementation MUST pin the exact digest recorded in
             that release's own published checksum file at the time of
             vendoring, not a value copied through an intermediary.
Build
discipline:  both languages link against ONE build of this SAME source
             artifact -- built once, reused by both the Python (PyICU)
             and Rust (rust_icu_ucol) toolchains via an explicit ICU4C
             install prefix (e.g. ICU_ROOT / PKG_CONFIG_PATH pointed at
             the shared build), never each language independently
             discovering "whatever the OS provides." This is what
             actually closes the build-environment gap Correction 3
             (revision 3) flagged but left open -- a shared, named,
             checksum-verifiable artifact, not merely a shared version
             number.
```

**Differential proof requirement -- corpus, methodology, and pass criterion (unchanged in content
from revision 3; version references below updated to match Correction 3a)**:

```text
Corpus:      the same witness set this lane and the original combined
             checkpoint already assembled -- ASCII case pairs, accented
             Latin, the straße/strasse case-folding-adjacent pair, CJK
             samples, and punctuation-leading filenames.
Method:      for each corpus filename pair, compare the sort order
             produced by (a) PyICU 2.16.2 icu.Collator, locale "en-001",
             the pinned options above, against (b) rust_icu_ucol 5.8.0
             UCollator, same locale and equivalent option mapping, on a
             build where both link against the SAME vendored ICU4C 78.3
             artifact (Correction 3b).
Pass:        every corpus pair orders identically under (a) and (b). Any
             disagreement is a CONTRACT_ASSURANCE_DEFECT against this
             candidate, blocking its selection, not a finding to silently
             work around.
```

**Correction 3c -- NOT fixed in this revision, flagged as an open scope question**:
`minion-agent-docs#143`'s third blocking point holds this candidate to its own stated pass
criterion -- it cannot be `RESOLVED` while the differential run above remains unexecuted. That is
correct as far as it goes. But actually executing it means installing/compiling two new
ICU-linked native packages (PyICU's C extension against a vendored ICU4C build; `rust_icu_ucol`
linked the same way) in a throwaway environment outside any certified Python/Rust tree -- a
materially larger and more failure-prone action than this lane's prior direct-verification probes
(querying `process.versions.unicode`, `unicodedata.unidata_version`, `errno` behavior, or grepping
`Cargo.lock` -- all of which used only already-installed, already-trusted toolchains and installed
or compiled nothing new). Whether running that probe now is within this characterization pass's
authority, or requires the owner's explicit go-ahead (given the Layer 13 authorization's own
"SCOPING/read-only-audit/work-package-definition ONLY... IMPLEMENTATION: NOT YET AUTHORIZED"
boundary), is an open question this revision surfaces rather than resolves unilaterally.

**Rejected alternative, disclosed rather than left open**: `icu_collator`/ICU4X remains a
technically viable Rust engine (its foundational crates are already transitively present in
`minion-agent-rust`'s `Cargo.lock`, per this lane's own earlier finding) but is not part of this
candidate, because it is an independent reimplementation of ICU algorithms rather than an ICU4C
binding -- pairing it with PyICU would require the differential corpus to bridge two unrelated
codebases with no a priori reason to expect agreement, which is a strictly harder proof burden than
this candidate's same-library pairing.

**Fixed-locale disclosure (unchanged from revision 2, still accurate)**: pinning `"en-001"` makes
this option's OWN behavior fully deterministic and portable, but it diverges from Pi's own actual
behavior on any host machine whose Node/ICU default locale resolves to something other than
`en-001` -- Pi itself has no single locale to match on every host, so this pinned choice is, by
construction, an exact match to Pi only on hosts sharing that specific default, and a disclosed,
accepted divergence everywhere else.

## Corrected option summary

```text
R006-A: environment-sensitive host collation
  Python: locale.strxfrm (process-global state, not thread-safe -- new
          caveat)
  Rust:   rust_icu_ucol (a genuine host-ICU4C binding -- CORRECTED from
          the wrong ICU4X reference)
  Still: no cross-language reproducibility guarantee; approximate,
  unverifiable Pi-fidelity at best.

R006-B: deterministic Minion ordering (toLowerCase + ordinal + ordinal
  original-string tiebreak)
  Reproducibility: HIGH, not FULL -- contingent on Unicode-version
  alignment across Node 16.0 / Python 15.1 / Rust ICU4X ~17.0 (verified
  this revision for the first two; cited from the reviewer for the
  third). A residual, bounded divergence exists for characters whose
  case mapping changed across those versions.
  Tie-break: still a disclosed, genuine divergence from Pi's own
  (filesystem-enumeration-order-dependent) tie behavior, unchanged from
  revision 1.

R006-C: pinned collation implementation
  Now (revision 4): ONE selected, concrete candidate -- PyICU 2.16.2 +
  rust_icu_ucol 5.8.0 (version CORRECTED this revision), both targeting
  ICU4C 78.3 via the exact official icu4c-78.3-sources.tgz artifact
  (NEW this revision, replacing the bare version number), locale
  "en-001", the Intl.Collator-matched options above -- with the build-
  environment gap now closed by a named, checksum-verifiable shared
  artifact (Correction 3b), a concrete differential-proof corpus/method/
  pass criterion specified (still not yet run -- Correction 3c, flagged
  as an open scope question below, not resolved unilaterally), and
  icu_collator/ICU4X explicitly named as a rejected alternative rather
  than left open.
```

No option is selected among `R006-A`/`R006-B`/`R006-C` -- this revision makes the `R006-C`
candidate's version and build-artifact claims concrete and correct, per two of the review's three
blocking points; the owner still chooses among the three, and the differential-execution question
(Correction 3c) remains open. `TOOL-028`'s collation scope cannot proceed to contract-review-ready
status until both are settled.

## Lane-C status (this revision)

```text
R006-A: RESOLVED (unchanged from revision 2, confirmed by minion-agent-docs#142)
R006-B: RESOLVED (unchanged from revision 2, confirmed by minion-agent-docs#142)
R006-C: partially revised -- version (3a) and build artifact (3b) fixed
        and verified via primary sources; differential-execution
        requirement (3c) explicitly NOT fixed, flagged as an open scope
        question for the owner
R006:   OWNER_DECISION_REQUIRED (R006-C's 3c question specifically)
```
