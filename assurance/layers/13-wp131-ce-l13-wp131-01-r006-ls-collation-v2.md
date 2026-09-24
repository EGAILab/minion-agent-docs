# CE-L13-WP131-01 — Lane C revision 2: `R006` corrections

Mode: §11.8 sub-checkpoint characterization, Lane C, `R006` revision only. **No Python or Rust
implementation performed or authorized. No Layer 12 production change. Review this revision only
-- `R003`/`R004`/`R008` remain frozen `CHECKPOINT-READY` and `R002`/`R005` remain
`OWNER_DECISION_RESOLVED`; do not reopen any of them unless this revision presents concrete
contradictory evidence.**

Targeted remediation of the independent Lane C review (`minion-agent-docs#141` @
`9012e8aa0f8b53a163048177396ae18e02ef3977`, verdict `R006 CHARACTERIZATION REJECTED`) against
Lane C revision 1 (`minion-agent-docs#132` @ `54eaadbf29bc7bd85d3bc7f341a9285b78f59525`).
Revision 1's Pi-source characterization and the `toLowerCase()`-versus-case-folding correction
were confirmed accurate; the three items below are corrected.

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

## Correction 3 -- `R006-C` needs a concrete version/locale/options tuple or differential proof, not
named libraries alone

Revision 1 named PyICU and `icu_collator`/ICU4X as candidates but did not specify concrete
versions, a target locale, or collation options, and did not establish -- by proof, not
assumption -- that the two engines would actually agree given the same nominal inputs (they are
different codebases: PyICU wraps genuine ICU4C; ICU4X is an independent reimplementation of ICU
algorithms, not a fork or port sharing source with ICU4C).

**Corrected, concrete proposal (still not selected as this lane's final answer -- presented as the
concrete SHAPE `R006-C` would need, per the review's own request)**:

```text
Engine (Python):    PyICU, pinned to a specific PyICU release wrapping a
                     specific ICU4C version (e.g. "PyICU==2.x bundling
                     ICU 76.x" -- exact pin deferred to implementation,
                     not decided in this characterization pass)
Engine (Rust):       EITHER (a) rust_icu_ucol pinned to a specific
                     ICU4C version matching Python's PyICU pin as closely
                     as possible (maximizes cross-language AND Pi
                     fidelity, since both would then wrap genuine,
                     version-aligned ICU4C), OR (b) icu_collator/ICU4X
                     pinned to a specific crate version (maximizes
                     build-time simplicity/no system-ICU dependency, at
                     the cost of being a DIFFERENT codebase from Python's
                     ICU4C-backed PyICU -- requiring differential proof,
                     below, rather than assumed agreement)
Locale:              a single, explicitly pinned locale string (e.g.
                     "en-001", matching this session's own observed Node
                     default) -- NOT "whatever the host's default is";
                     that would collapse this option back into R006-A's
                     own non-determinism
Collator options:    explicitly pinned (e.g. default strength/case-level
                     settings matching Intl.Collator's own defaults,
                     verified this lane: {usage: "sort", sensitivity:
                     "variant", collation: "default", numeric: false,
                     caseFirst: "false"} -- from this session's own
                     earlier new Intl.Collator().resolvedOptions() probe)
```

**Differential proof requirement (the review's core ask, not yet performed -- explicitly out of
this characterization pass's scope, flagged as required BEFORE implementation, not before
owner decision)**: before this option could be implemented, a differential corpus (the same
witness corpus this lane and the original checkpoint already assembled -- ASCII case pairs,
accented Latin, the `straße`/`strasse` case-folding-adjacent pair, CJK, punctuation) must be run
through the actually-chosen concrete engine pairing to CONFIRM they agree, rather than assuming
agreement because both nominally implement "ICU semantics." If `rust_icu_ucol` (genuine ICU4C
binding) is chosen for Rust, agreement with PyICU is highly likely (same underlying C library,
given matching versions) but not automatically guaranteed without the differential run. If
`icu_collator`/ICU4X is chosen instead, agreement with PyICU is a genuinely open, unproven
question requiring the differential corpus to settle.

**Corrected fixed-locale disclosure (the review's other explicit ask)**: pinning `"en-001"` (or
any other single locale) makes this option's OWN behavior fully deterministic and portable, but
it diverges from Pi's own actual behavior on any host machine whose Node/ICU default locale
resolves to something other than `en-001` -- Pi itself has no single locale to match on every
host, so any single pinned locale choice here is, by construction, an exact match to Pi only on
hosts sharing that specific default, and a disclosed, accepted divergence everywhere else.

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
  Now: an explicit, concrete engine/version/locale/options tuple shape
  (above), with an explicit differential-proof requirement before
  implementation, and an explicit disclosure that any single pinned
  locale diverges from Pi on hosts whose own default differs.
```

No option is selected. `TOOL-028`'s collation scope cannot proceed to contract-review-ready status
until the owner picks one.

## Lane-C status (this revision)

```text
R006:  OWNER_DECISION_REQUIRED
```
