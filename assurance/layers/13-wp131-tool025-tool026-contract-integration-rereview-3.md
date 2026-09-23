# Layer 13 WP-13.1 — TOOL-025/TOOL-026 integration re-review 3

**Mode:** independent Rust-side targeted review of TOOL-029 scope/purity only. No implementation.

**Verdict:** **REJECTED** — the wording is narrower, but the manifest row still mixes adopted
behavior into an intentional-divergence row and incorrectly reopens an owner-settled decision.

## Exact target

```text
docs PR #132 (unchanged)
    d3eb0c05f6d0a4d7665fe825f45ed4d4dba2e945

manifest PR #52
    661c9fee051e7edb8601d6a83b142ef1a92b4812

prior targeted review
    minion-agent-docs#156
    47b8bc21611e154b6f068921c65a49414acb9556

pinned Pi
    b7bb00b936dbe21b8e160b3e89efdec361846699
```

The manifest candidate was fetched and verified remote-reachable. Issue #48 was open and named
`NEXT_OWNER = Codex`. The prior R005-A/R002-A integration remains untouched.

## Finding result

### L13-WP131-INT-R003 — row purity

**Status: STILL OPEN (`CONTRACT_ASSURANCE_DEFECT`, blocking).**

TOOL-029 now correctly says the three `ls` templates are not currently integrated. However, its
binding rule explicitly says “THIS row's governed semantics cover” both:

1. preservation of `read`'s `"Operation aborted"` template (`DIRECT_PI_PARITY`, adopted); and
2. replacement of raw/hybrid provider text (intentional divergence).

Its `tests` list likewise includes
`read_operation_aborted_template_unaffected_by_r010b`. Therefore the row still contains two kinds
of semantic content under one machine-readable `disposition: intentional divergence`. Moving from
“all four stable templates” to “one stable template” narrows the mixed-disposition defect but does
not remove it.

**Required correction:** TOOL-029's governed rule and evidence must contain only the raw/hybrid
text replacement. Move/retain the abort-template preservation rule and its planned witness solely
under TOOL-025's adopted row. TOOL-029 may mention stable templates only as non-governed source
contrast, explicitly outside this row's semantic/evidence ownership.

### L13-WP131-INT-R004 — TOOL-028 isolation

**Status: STILL OPEN (`CONTRACT_ASSURANCE_DEFECT`, blocking refinement).**

The row now says whether R010-B applies to `ls` raw/hybrid sites “at all” is TOOL-028's future open
question. That contradicts the already-settled owner decision: R010-B applies to Layer 13's
raw/hybrid sites; TOOL-028's normative integration is deferred because R006-C blocks TOOL-028, not
because the R010 governance choice remains open.

**Required correction:** state that the owner-approved R010-B mapping is binding for TOOL-028's
eventual raw/hybrid integration, while all TOOL-028 wording/evidence remains deferred until R006-C
resolves. Do not claim a future governance choice still exists.

## Binding ownership matrix for the correction

```text
TOOL-025 / adopted
    core read behavior
    Operation aborted preservation + its witness

TOOL-026 / adopted
    preprocessing and strict-rejection classification

TOOL-029 / intentional divergence
    deterministic raw/hybrid error-text replacement only
    currently evidenced for TOOL-025 + TOOL-026

TOOL-028 / pending R006
    three ls stable templates not yet integrated
    ls raw/hybrid R010-B integration deferred, but owner choice already settled
```

This matrix is the convergence boundary; another prose reshuffle that leaves adopted evidence in
TOOL-029 will not close INT-R003.

## Gates

```text
manifest validation
    8 passed

candidate scope
    TOOL-029 row only

R005-A / R002-A prior repairs
    unchanged

implementation changes
    none
```

## Verdict

```text
TOOL-025/TOOL-026 INTEGRATION
    REJECTED

INT-R003
    STILL OPEN — BLOCKING

INT-R004
    STILL OPEN — BLOCKING REFINEMENT

R006-C
    FEASIBILITY_BLOCKED / unchanged

Python/Rust WP-13.1 implementation
    NOT AUTHORIZED / NOT STARTED
```

Return only the ownership-matrix correction above. Do not reopen any approved characterization or
begin implementation.
