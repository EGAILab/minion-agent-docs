# CE-L13-WP131-01 Lane C R006-C independent re-review 3

**Mode:** convergence sub-checkpoint review only. No Python or Rust implementation was performed
or authorized. No Layer 12 or Layer 14 work was performed.

## Exact target

```text
coordination issue:  EGAILab/minion-agent#48
status:              CONTRACT_CONVERGENCE
next owner:          Codex
docs PR:             EGAILab/minion-agent-docs#132
docs head:           6355431610a6443785dcfcc25fa2deb877c033f0
manifest PR:         EGAILab/minion-agent#52
manifest head:       cca8d8b325bb159be549e10c8321b3468f043e7f (frozen)
docs base:           master @ 0bbd737fab8c1360995f4efff2b41c1c5531a9c3
code base:           main @ 92aa4be168dc82111832467922089206e858a9c4
pinned Pi:           b7bb00b936dbe21b8e160b3e89efdec361846699
episode:             CE-L13-WP131-01
artifact:            assurance/layers/13-wp131-ce-l13-wp131-01-r006-ls-collation-v3.md
scope:               R006-C only (Lane C revision 3)
prior review:        EGAILab/minion-agent-docs#142 @
                     104ff6b8b41c6d64695f0c4d7d4cc36724ee9982
```

The issue-recorded heads matched the open remote PR heads and were remote-reachable. Both PRs were
open and Ready for Review. The handoff carried existing governance provenance and was not derived
from quarantined work. R003/R004/R008, R002/R005, and resolved R006-A/R006-B were not reopened.

## Result

```text
R006-C:                 NOT_RESOLVED
R006 CHARACTERIZATION:  REJECTED
OWNER DECISION READY:   NO
IMPLEMENTATION:         NOT AUTHORIZED
```

## Independent checks

Pinned Pi still uses `a.toLowerCase().localeCompare(b.toLowerCase())` without an explicit locale.
Revision 3 now selects the correct *kind* of pairing: PyICU and `rust_icu_ucol` are both ICU4C
bindings, `icu_collator`/ICU4X is explicitly rejected, locale `en-001` and the intended collator
profile are selected, and fixed-locale divergence from Pi's host default remains disclosed.

The package/version assertions were checked against their registries and upstream projects:

- PyPI confirms PyICU 2.16.2, published 2026-03-20;
- Unicode's release record confirms ICU 78.3, released 2026-03-17;
- crates.io/Cargo reports `rust_icu_ucol 5.8.0` as current, not 5.1.0;
- `cargo info rust_icu_ucol@5.1.0` confirms 5.1.0 exists but reports latest 5.8.0;
- upstream `google/rust_icu` published 5.8.0 on 2026-08-20.

## Blocking findings

### L13-WP131-R006-C4 — `CONTRACT_ASSURANCE_DEFECT`

Revision 3 says `rust_icu_ucol 5.1.0` was verified as the current crates.io release on
2026-09-22. That statement is false: crates.io reports 5.8.0 as current, and upstream published
5.8.0 on 2026-08-20.

This is not merely a preference for a newer package. The candidate's stated rationale is that the
selected wrapper version is current and suitable for the ICU4C 78.3 target. If an older 5.1.0 is
deliberately required, the option must say so and establish its compatibility with ICU4C 78.3.
Otherwise it must use and assess the actual selected/current release.

Required correction: select the actual wrapper version intentionally, cite its authoritative
registry/upstream record, and establish compatibility with the selected ICU4C artifact.

### L13-WP131-R006-C5 — `CONTRACT_ASSURANCE_DEFECT`

The prior review required an exact underlying engine/data artifact and the differential evidence
needed to establish the tuple. Revision 3 still expressly leaves both unresolved:

```text
ICU4C 78.3 is only a build-environment target;
the candidate does not select a container/package/static artifact or integrity hash;
the differential corpus is specified but unperformed;
any disagreement would block selection;
the artifact says both are deferred until implementation.
```

Consequently this remains a conditional design, not a demonstrated feasible tuple. Wrapper pins
alone do not make both languages consume the same ICU data, which the candidate itself correctly
acknowledges. And because the stated pass criterion says any differential disagreement blocks the
selection, the option cannot be owner-decision-ready before that criterion has actually passed.

### Minimal witness

```text
source basis:       Pi delegates collation to one concrete host Node/ICU environment.
candidate setup 1: build PyICU and rust_icu against ICU4C 78.3 from one controlled artifact.
candidate setup 2: build the same wrapper pins against different host ICU installations.
candidate rule:    both satisfy the wrapper-version prose, while revision 3 admits they can use
                   different Unicode data and produce different ordering.
required result:   one exact engine/data artifact and a recorded passing differential run define
                   the feasible owner option.
discrimination:    the current prose still allows the very data-version skew R006-C is intended
                   to eliminate, and its own pass/fail gate has not been evaluated.
```

## Narrow correction required

For R006-C only:

1. Correct the false `rust_icu_ucol` current-version claim and intentionally select a wrapper
   version shown compatible with the chosen ICU4C release.
2. Select one exact ICU4C 78.3 build/data artifact for both languages, including platform/build
   mechanism and integrity/version discipline; do not leave it as an implementation choice.
3. Execute and record the stated Python/Rust differential corpus against that exact tuple. A
   passing result is required because the candidate's own criterion makes disagreement blocking.
4. Preserve the selected locale/options and fixed-locale Pi-divergence disclosure.

## Verdict

```text
R006-C:                    NOT_RESOLVED
R006:                      CHARACTERIZATION REJECTED
Lane C:                    CHANGES REQUIRED
Owner decision ready:      NO
Implementation authorized:NO
Python WP-13.1:            NOT_IMPLEMENTED / NOT AUTHORIZED
Rust WP-13.1:              NOT_IMPLEMENTED / BLOCKED
Layer 13 cross-language:   NOT CLOSED
Layer 14:                  NOT STARTED
```

Return only Lane C R006-C to the shared-contract owner. Preserve every other frozen/resolved
finding and do not begin Lane D or Lane E.
