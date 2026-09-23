# Layer 13 WP-13.1 — TOOL-025/TOOL-026 integration re-review 4

**Mode:** independent Rust-side targeted closure review only. No implementation.

**Verdict:** **APPROVED** — TOOL-025/TOOL-026 contract integration is faithful to the approved
R002-A, R005-A, and R010-B decisions. TOOL-028 remains pending R006-C.

## Exact target

```text
docs PR #132 (unchanged)
    d3eb0c05f6d0a4d7665fe825f45ed4d4dba2e945

manifest PR #52
    019f13d69b9e422e5bf47d887d21c387d088d485

prior review evidence
    minion-agent-docs#156
    ee05a462682ddf2aac88b06526ce20193a97a798

pinned Pi
    b7bb00b936dbe21b8e160b3e89efdec361846699
```

The new manifest SHA was fetched and verified remote-reachable. Issue #48 was open and named
`NEXT_OWNER = Codex`. This pass checked only the binding ownership-matrix correction.

## Closure result

### L13-WP131-INT-R003 — machine-readable disposition purity

**RESOLVED.**

TOOL-029 retains `disposition: intentional divergence` and now governs only deterministic
raw/hybrid error-text replacement. It no longer governs or tests stable-template preservation.
The `read_operation_aborted_template_preserved_verbatim` planned witness is correctly owned by
TOOL-025's adopted row.

### L13-WP131-INT-R004 — TOOL-028 isolation

**RESOLVED.**

The manifest now states the owner already settled R010-B for both tools; only TOOL-028's normative
integration is deferred while R006-C remains feasibility-blocked. TOOL-029 does not claim the
three `ls` stable templates, and the existing TOOL-028 row remains mechanically unchanged.

## Ownership matrix confirmed

```text
TOOL-025 / adopted
    core read behavior
    Operation aborted preservation + witness

TOOL-026 / adopted
    preprocessing and strict-rejection classification

TOOL-029 / intentional divergence
    deterministic raw/hybrid error-text replacement only
    currently evidenced for TOOL-025 + TOOL-026

TOOL-028 / pending R006
    three ls stable templates not yet integrated
    R010-B choice settled; normative ls integration deferred
```

## Regression checks

- R005-A's pinned-Photon authority remains intact.
- R002-A remains the direct, unwrapped, pre-`ctx.fs` strict conversion path.
- TOOL-029 retains the exact R010-B governance permalink.
- TOOL-026/TOOL-027/TOOL-028 rows are unchanged by this remediation.
- Manifest validation: `8 passed`.
- No Python, Rust, Layer-12, or WP-12.E1 implementation changes exist in this candidate.

## Verdict

```text
TOOL-025/TOOL-026 INTEGRATION
    APPROVED

INT-R001
    RESOLVED

INT-R002
    RESOLVED

INT-R003
    RESOLVED

INT-R004
    RESOLVED

R006-C / TOOL-028
    FEASIBILITY_BLOCKED / NOT INTEGRATED

Python/Rust WP-13.1 implementation
    NOT AUTHORIZED / NOT STARTED
```

This approval applies only to the exact SHAs above. It does not approve TOOL-028, close WP-13.1,
authorize implementation, change Layer 12/WP-12.E1, or start Layer 14.
