# CE-L13-WP131-01 — Lane C revision 3: `R006-C` correction only

Mode: §11.8 sub-checkpoint characterization, Lane C, `R006-C` revision only. **No Python or Rust
implementation performed or authorized. No Layer 12 production change. Review this revision only
-- `R003`/`R004`/`R008` remain frozen `CHECKPOINT-READY`, `R002`/`R005` remain
`OWNER_DECISION_RESOLVED`, and `R006-A`/`R006-B` remain `RESOLVED` per `minion-agent-docs#142` @
`104ff6b8b41c6d64695f0c4d7d4cc36724ee9982`; do not reopen any of them unless this revision
presents concrete contradictory evidence.**

Targeted remediation of the independent Lane C revision-2 review (`minion-agent-docs#142` @
`104ff6b8b41c6d64695f0c4d7d4cc36724ee9982`, verdict `R006 CHARACTERIZATION REJECTED` on `R006-C`
alone -- `R006-A` and `R006-B` were both found `RESOLVED`) against Lane C revision 2
(`minion-agent-docs#132` @ `268b0ff2298ea1f2e4f479fe0b1e78afb0fe2ce4`). `R006-C` still supplied
only a placeholder tuple shape: unspecified exact versions, two mutually exclusive Rust mechanism
branches presented as an unresolved "EITHER/OR," example (not selected) locale/options, and a
differential-proof requirement that was flagged but not given a concrete corpus/methodology/pass
criterion. Corrections 1 and 2 below (from revision 2, covering `R006-A`/`R006-B`) are unchanged
and preserved as the historical, now-resolved record. Only Correction 3 (`R006-C`) is revised.

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

## Correction 3 (revision 3) -- `R006-C` given one selected, concrete tuple, not a placeholder shape

`minion-agent-docs#142`'s rejection: the revision-2 tuple was still a *shape* (a template with
blanks), not a *selection* -- unspecified exact versions, an unresolved Rust "EITHER/OR" branch,
an "e.g." locale, and a differential-proof requirement with no stated corpus/methodology/pass
criterion. This revision commits to one candidate profile end-to-end, with every version verified
directly this revision (via `WebSearch`, current as of this revision's writing date, 2026-09-22 --
not carried over from any earlier, possibly stale, source):

```text
Engine (Python):    PyICU 2.16.2 (verified current PyPI release this
                     revision; released 2026-03-20). PyICU is an FFI
                     wrapper: it does not bundle its own ICU4C copy, it
                     links against whatever ICU4C the build environment
                     provides.
Engine (Rust):       rust_icu_ucol 5.1.0 (verified current crates.io
                     release this revision). SELECTED over icu_collator/
                     ICU4X -- dropping revision 2's unresolved "EITHER/OR"
                     -- because rust_icu_ucol is, like PyICU, a genuine
                     FFI binding to the SAME underlying ICU4C library
                     family, not an independent reimplementation; this
                     maximizes cross-language agreement without requiring
                     the differential corpus to bridge two unrelated
                     codebases. icu_collator/ICU4X is not selected for
                     this candidate (noted below as a rejected
                     alternative, not left open).
ICU4C target:        78.3 (verified current stable ICU4C release this
                     revision; released 2026-03-17). This is a target for
                     the BUILD ENVIRONMENT, not a value either wrapper
                     package pins by itself -- see the caveat below.
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

**Build-environment caveat (a real gap this selection does not close by itself)**: neither PyICU
nor `rust_icu_ucol` bundles or vendors its own copy of ICU4C -- both are FFI bindings resolved
against whichever ICU4C shared library is installed/linked at build time on the machine that
compiles them. Pinning `PyICU==2.16.2` and `rust_icu_ucol==5.1.0` therefore pins the *binding*
layer, not the *data* layer: two build machines with different system ICU4C installs (e.g. one
with ICU4C 76.x, one with 78.3) would link the same wrapper-package versions against genuinely
different Unicode data, producing the SAME class of version-skew risk `R006-B` already disclosed
for `toLowerCase()`. Reaching the "78.3 target" declared above requires ALSO controlling the build
environment itself (e.g. a container image pinned to a specific ICU4C package build, or a
vendored/statically-linked ICU4C 78.3), which is an implementation/build-infrastructure decision,
not a characterization-layer one -- flagged here as a concrete, disclosed prerequisite rather than
left implicit.

**Differential proof requirement -- given a concrete corpus, methodology, and pass criterion (the
review's core ask; the proof itself remains unperformed, out of this characterization pass's
scope, required BEFORE implementation, not before owner decision)**:

```text
Corpus:      the same witness set this lane and the original combined
             checkpoint already assembled -- ASCII case pairs, accented
             Latin, the straße/strasse case-folding-adjacent pair, CJK
             samples, and punctuation-leading filenames.
Method:      for each corpus filename pair, compare the sort order
             produced by (a) PyICU 2.16.2 icu.Collator, locale "en-001",
             the pinned options above, against (b) rust_icu_ucol 5.1.0
             UCollator, same locale and equivalent option mapping, on a
             build where both link against the SAME installed ICU4C
             version (78.3 target, per the caveat above).
Pass:        every corpus pair orders identically under (a) and (b). Any
             disagreement is a CONTRACT_ASSURANCE_DEFECT against this
             candidate, blocking its selection, not a finding to silently
             work around.
```

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
  Now (revision 3): ONE selected, concrete candidate -- PyICU 2.16.2 +
  rust_icu_ucol 5.1.0, both targeting ICU4C 78.3, locale "en-001", the
  Intl.Collator-matched options above -- with the build-environment
  caveat (wrapper-version pins alone do not pin the linked ICU4C data
  version) disclosed, a concrete differential-proof corpus/method/pass
  criterion specified (not yet run), and icu_collator/ICU4X explicitly
  named as a rejected alternative rather than left open.
```

No option is selected among `R006-A`/`R006-B`/`R006-C` -- this revision only makes the `R006-C`
candidate itself concrete and singular, per the review's request; the owner still chooses among the
three. `TOOL-028`'s collation scope cannot proceed to contract-review-ready status until the owner
picks one.

## Lane-C status (this revision)

```text
R006-A: RESOLVED (unchanged from revision 2, confirmed by minion-agent-docs#142)
R006-B: RESOLVED (unchanged from revision 2, confirmed by minion-agent-docs#142)
R006-C: revised -- now a single concrete candidate, not a placeholder shape
R006:   OWNER_DECISION_REQUIRED
```
