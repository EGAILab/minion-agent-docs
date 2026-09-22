# CE-L13-WP131-01 Lane C R006 independent re-review 2

**Mode:** convergence sub-checkpoint review only. No Python or Rust implementation was performed
or authorized. No Layer 12 or Layer 14 work was performed.

## Exact target

```text
coordination issue:  EGAILab/minion-agent#48
status:              CONTRACT_CONVERGENCE
next owner:          Codex
docs PR:             EGAILab/minion-agent-docs#132
docs head:           268b0ff2298ea1f2e4f479fe0b1e78afb0fe2ce4
manifest PR:         EGAILab/minion-agent#52
manifest head:       cca8d8b325bb159be549e10c8321b3468f043e7f (frozen)
docs base:           master @ 0bbd737fab8c1360995f4efff2b41c1c5531a9c3
code base:           main @ 92aa4be168dc82111832467922089206e858a9c4
pinned Pi:           b7bb00b936dbe21b8e160b3e89efdec361846699
episode:             CE-L13-WP131-01
artifact:            assurance/layers/13-wp131-ce-l13-wp131-01-r006-ls-collation-v2.md
scope:               R006 only (Lane C revision 2)
prior review:        EGAILab/minion-agent-docs#141 @
                     9012e8aa0f8b53a163048177396ae18e02ef3977
```

The issue-recorded heads matched the open remote PR heads and were remote-reachable. Both PRs were
open, Ready for Review, and mergeable. The handoff carried the existing governance provenance and
was not derived from quarantined work. R003/R004/R008 and resolved R002-A/R005-A were not reopened.

## Result

```text
R006 CHARACTERIZATION:  REJECTED
OWNER DECISION READY:   NO
IMPLEMENTATION:         NOT AUTHORIZED
```

## Independent source recheck

Pinned Pi still sorts `ls` entries with:

```text
entries.sort((a, b) => a.toLowerCase().localeCompare(b.toLowerCase()))
```

with no explicit locale or collator options. A fresh local probe reported Node 22.15.1 using
locale `en-001`, ICU 76.1, CLDR 46.0, and Unicode 16.0. Python 3.13.5 reported Unicode 15.1.0.
Those observations confirm that a host-default Pi profile and runtime-provided Unicode lowercase
tables are not one universally fixed cross-language artifact.

## Prior-finding closure ledger

### L13-WP131-R006-C1

```text
status: RESOLVED
```

Revision 2 correctly removes ICU4X from the host-ICU option and identifies
`rust_icu_ucol`/`rust_icu` as an ICU4C FFI family. It also discloses Python `setlocale` as
process-global state with concurrency and unrelated-process-work consequences. The option remains
low-reproducibility by design, but its proposed mechanism is no longer factually mislabeled.

### L13-WP131-R006-C2

```text
status: RESOLVED
```

Revision 2 withdraws the false `FULL` reproducibility claim. It now calls R006-B `HIGH, not FULL`,
identifies the observed Unicode table skew, and discloses that recently assigned or changed case
mappings can order differently unless a common mapping version is actually pinned. That is an
honest owner-visible residual divergence. The deterministic ordinal tiebreak remains separately
disclosed as a divergence from Pi's stable filesystem-enumeration tie behavior.

### L13-WP131-R006-C3

```text
status: NOT_RESOLVED
classification: CONTRACT_ASSURANCE_DEFECT
```

The prior review required **at least one exact candidate tuple** containing the engine/artifact
version, locale, collation/options, and data/version discipline for both languages. Revision 2
labels its proposal concrete but supplies only a tuple *shape*:

```text
PyICU==2.x / ICU 76.x                 (example; exact pin deferred)
EITHER rust_icu_ucol OR ICU4X         (mechanism not selected)
locale "e.g. en-001"                  (locale not selected)
options "e.g." resolved defaults      (profile not fixed)
differential proof                    (required but not performed)
```

Those placeholders still permit materially different observable implementations. The two Rust
branches are not interchangeable: one can share a pinned ICU4C artifact with Python; the other is
a cross-engine ICU4C/ICU4X mapping whose equivalence is expressly unknown. Similarly, `en-001`
and some other locale are different contracts, and "matching versions as closely as possible" is
not a version discipline.

Deferring the exact tuple and its feasibility evidence until implementation would ask the owner
to select R006-C without knowing which implementation is being selected or whether the selected
pair agrees on the stated witness surface. This is precisely the uncertainty the contract-first
checkpoint is meant to settle before implementation authorization.

### Minimal documentary witness

```text
finding:          L13-WP131-R006-C3
source basis:     Pi uses host-default localeCompare; a deterministic substitute must identify
                  its own exact observable collation profile.
minimal setup:    independently implement the revision-2 R006-C prose.
choice 1:         PyICU/ICU4C plus rust_icu_ucol against one pinned ICU4C artifact.
choice 2:         PyICU/ICU4C plus ICU4X icu_collator with separately supplied data.
candidate result: both choices satisfy the prose even though cross-engine agreement is explicitly
                  unproven and their data/version behavior can differ.
required result:  the option must identify at least one exact, feasible tuple and provide the
                  differential evidence required to establish that tuple's claimed behavior.
discrimination:   two observably distinct implementations cannot both be the same concrete owner
                  option merely because implementation will choose between them later.
```

## Narrow correction required

For R006-C only:

1. Select at least one actual candidate mechanism, not `EITHER` alternatives.
2. Pin exact Python package/wrapper, Rust crate/wrapper, underlying engine/data artifact, locale,
   and collator option values (or explicitly versioned defaults).
3. State how both languages consume the same artifact, or, for a cross-engine tuple, run and record
   the required differential corpus before calling the option feasible.
4. Retain the accurate disclosure that a fixed locale diverges from Pi on hosts whose default
   locale differs.

No correction is requested for R006-A or R006-B.

## Verdict

```text
R006:                      CHARACTERIZATION REJECTED
Lane C:                    CHANGES REQUIRED
Owner decision ready:      NO
Implementation authorized:NO
Python WP-13.1:            NOT_IMPLEMENTED / NOT AUTHORIZED
Rust WP-13.1:              NOT_IMPLEMENTED / BLOCKED
Layer 13 cross-language:   NOT CLOSED
Layer 14:                  NOT STARTED
```

Return only Lane C R006-C to the shared-contract owner. Preserve R006-A/R006-B as corrected,
preserve every other frozen/resolved lane, and do not begin Lane D or Lane E.
