# Layer 13 WP-13.1 — TOOL-025/TOOL-026 integration re-review 2

**Mode:** independent Rust-side targeted review of `INT-R003` only. No implementation.

**Verdict:** **REJECTED** — the machine-readable row split is present, but TOOL-029 mixes in and
misattributes frozen TOOL-028 behavior. One narrow manifest correction remains.

## Exact target

```text
docs PR #132
    d3eb0c05f6d0a4d7665fe825f45ed4d4dba2e945

manifest PR #52
    40706f3f656deaa52ea92d7941de4b1e5edbd195

prior targeted review
    minion-agent-docs#156
    87e7c3814241a8c894c1eef21b49f998688089ac

pinned Pi
    b7bb00b936dbe21b8e160b3e89efdec361846699
```

Both candidates were fetched and verified remote-reachable. Issue #48 was open and named
`NEXT_OWNER = Codex`. This pass did not reopen R002-A, R005-A, R010-B, or the already-resolved
INT-R001/INT-R002 mechanics.

## INT-R003 result

**Status: `PARTIALLY_RESOLVED_BLOCKING`.**

The requested machine-readable split now exists: TOOL-029 has `disposition: intentional
divergence`, while TOOL-025 and TOOL-026 retain `adopted`. That is the correct structural direction.

However, TOOL-029's binding rule also states that all four stable Pi templates are preserved
verbatim and “covered by TOOL-025/TOOL-026's own `adopted` disposition.” Only one of those four
templates (`"Operation aborted"`) belongs to the currently-integrated `read` surface. The other
three are `ls`/TOOL-028 templates:

```text
Path not found: <path>
Not a directory: <path>
Cannot read directory: <underlying message>
```

TOOL-028 remains frozen and `PENDING_R006`; TOOL-025/TOOL-026's adopted rows cannot cover those
three behaviors. The new planned test name
`read_stable_hand_authored_templates_unaffected_by_r010b` likewise uses plural “templates” for a
`read` surface with only the one abort template.

This is both:

- a residual `INT-R003` purity problem — an `intentional divergence` row still normatively claims
  adopted stable-template behavior; and
- a regression of `INT-R004`'s partial-integration boundary — three TOOL-028 semantics are again
  asserted through a new cross-row statement even though TOOL-028 itself remains frozen.

## Minimal correction

Keep TOOL-029 and its `intentional divergence` disposition, but make its binding rule govern only
the raw/hybrid text replacement currently scoped to TOOL-025 plus TOOL-026's strict-conversion
rejection. Pi's four stable templates may be mentioned solely as source/background contrast if the
row explicitly says they are outside TOOL-029's governed semantics. State that only `read`'s
`"Operation aborted"` template is currently integrated; defer the three `ls` templates to
TOOL-028's own post-R006 integration. Rename/narrow the planned test accordingly.

No spec change is required by this finding; `spec/tools.md` already points to the separate row and
does not make the incorrect TOOL-025/TOOL-026-owns-all-four claim.

## Checks

```text
manifest validation
    8 passed

TOOL-029 machine-readable disposition
    intentional divergence — present

INT-R001 / INT-R002 prior fixes
    unchanged

TOOL-028 existing row/section
    mechanically unchanged, but semantically referenced by TOOL-029 as described above

implementation changes
    none
```

## Verdict

```text
TOOL-025/TOOL-026 INTEGRATION
    REJECTED

INT-R003
    PARTIALLY_RESOLVED_BLOCKING

INT-R004
    REGRESSED NARROWLY / BLOCKING

R006-C
    FEASIBILITY_BLOCKED / unchanged

Python/Rust WP-13.1 implementation
    NOT AUTHORIZED / NOT STARTED
```

Return only this narrow TOOL-029 scope/purity correction. Do not modify the resolved R005-A or
R002-A integration and do not begin implementation.
