# Layer 06 Rust contract approval

**Review date:** 2026-08-26
**Code candidate:** `minion-agent@b6edc5ca0571244f098db8db0544f08f0be332eb`
**Docs candidate:** `minion-agent-docs@cf942f71a5c363d2ad68ca2f671c6e5d2e760488`
**Pinned Pi:** `b7bb00b936dbe21b8e160b3e89efdec361846699`
**Previous closure review:** `573c11521c22b89aef53f83f70b48dfcf19dfbc8`
**Rust production modified:** NO

## Verdict

```text
L06-R001 ... L06-R006
    ALL RESOLVED

Layer-06 shared contract
    APPROVED FOR RUST IMPLEMENTATION

Python Layer 06
    CERTIFIED

Rust Layer 06
    NOT_IMPLEMENTED

Rust current certified position
    Layer 05

Layer 07
    NOT STARTED
```

This approval closes the Layer-06 shared-contract review loop. A separate pass may now implement
Rust Layer 06. This artifact does not certify a Rust Layer-06 implementation.

## Per-listener normalization

`EventBus.waterfall` has an optional `normalize_step` callback. Inside each listener's `next_`,
the implementation selects the replacement/current tuple, applies `normalize_step`, and only then
calls `step(index + 1, forwarded)`. Thus the next listener cannot receive an unnormalized
replacement.

When `normalize_step` is absent, `forwarded` passes through unchanged. Existing generic waterfall
tests remain green, and an independent default-path probe confirmed that a generic replacement is
still observed unchanged by the next listener.

For `TOOLS_POST_EXECUTE`, `_finalize` captures the authoritative baseline:

```text
tool_call_id
tool_name
execute-produced added_tool_names
```

Its event-specific normalizer restores only those fields at every listener handoff while retaining
`content`, `details`, `is_error`, `usage`, and `terminate`. The retained final reconstruction in
`_finalize` separately protects a last/short-circuiting listener result that never passes through
another `next_` boundary.

## Independent attack matrix

Initial production result:

```text
tool_call_id     t1
tool_name        echo
added_tool_names [alpha]
```

Raw listener A attempted:

```text
tool_call_id     evil-id
tool_name        evil-name
added_tool_names [evil]
```

Independent probes produced:

| Path | Downstream observation | Verdict |
|---|---|---|
| raw -> raw | `t1`, `echo`, `alpha` | PASS |
| raw -> helper | `t1`, `echo`, `alpha` | PASS |
| helper -> raw | `t1`, `echo`, `alpha`; helper content retained | PASS |
| helper -> raw attacker -> helper | protected originals observed | PASS |

Listener B can no longer copy a forged protected value into `details`; it copies the authoritative
original. In-place mutation remains blocked because `ToolResult` is frozen.

The same raw replacement changed all Pi-authorized fields in one probe. Listener B observed and the
final result retained:

```text
content     changed
details     {a: 1}
is_error    true
usage.input 2
terminate   true
```

`added_tool_names` remained `alpha`. A terminal raw listener that short-circuited with forged
protected fields was corrected by final restoration while its allowed content/terminate changes
survived.

## Failure semantics

A raw predecessor attempted protected replacements, a middle listener raised
`RuntimeError("boom")`, and a later listener was registered. Fresh observation:

```text
later listener called    NO
semantic error text      boom
tool_call_id             t1
tool_name                echo
```

Failure short-circuit and source identity therefore remain intact.

## Finding closure

| Finding | Verdict | Evidence |
|---|---|---|
| `L06-R001` | RESOLVED | Raw object-valued schemas remain execution-validated; public docs distinguish Layer-05 storage from Layer-06 validation. |
| `L06-R002` | RESOLVED | Focused error path still normalizes `RuntimeError("boom")` to `boom`. |
| `L06-R003` | RESOLVED | Protected fields are restored before every downstream listener and again on the final result across raw/helper paths. |
| `L06-R004` | RESOLVED | The ten Layer-06 scenarios execute and pass with zero defers; pending-tool state remains Layer 07+. |
| `L06-R005` | RESOLVED | Rust signal structures remain documented and behavioral cancellation remains validly deferred to Layer 09. |
| `L06-R006` | RESOLVED | `TOOL-005` explicitly specifies merged-and-normalized per-listener authority; no current API/normative `TOOL-022` citation remains. |

## Traceability

`TOOL-005` now states that every listener sees the result merged and normalized by prior
listeners, identifies the three protected fields, preserves the five Pi-authorized override
fields, covers raw/helper mixtures in either order, and classifies ordered N-listener composition
as an intentional Minion architectural extension over Pi's single-callback baseline.

The manifest has 65 rows and 65 unique IDs. `TOOL-022` is absent. Historical assurance prose may
truthfully mention the former dangling citation; current public API and normative surfaces do not
cite it as an active requirement.

## Canonical and verification evidence

Fresh commands and results:

```text
focused tools + EventBus waterfall tests
    64 passed

Layer-06 canonical scenarios
    discovered 10
    executed   10
    passed     10
    deferred    0

schema validation
    165 passed

ruff (modified production/tests)
    PASS

mypy src/minion_agent
    57 files PASS

manifest
    65 / 65 unique
```

The ten Layer-06 scenarios remain:

1. `after-hook-failure-replaces-result-with-tool-error`
2. `before-hook-failure-becomes-tool-error`
3. `execute-failure-becomes-tool-error`
4. `late-tool-update-ignored`
5. `length-stop-executes-no-tools`
6. `parallel-tool-completion-vs-message-order`
7. `prepare-arguments-failure-becomes-tool-error`
8. `schema-validation-failure-becomes-tool-error`
9. `tool-batch-parallel`
10. `tool-batch-sequential-contagion`

The canonical runner remains unchanged by this remediation and delegates execution, hook
authority, normalization, ordering, and failure behavior to production code.

## Rust feasibility

The certified Layer-05 `ToolDefinition`, `ToolRegistry`, `ToolExecutionSignal`, Runtime registry,
and context surface remain reusable. Rust can enforce the same observable rule more strongly with
a typed `AfterToolCallOverride` that cannot contain protected fields; it need not reproduce
Python's `normalize_step` or snapshot mechanics. No Runtime semantic redesign, second registry,
or Layer-05 semantic change is required. Future AgentLoop can consume the executor seam without
redesign.

## Active findings

```text
PI_PARITY_DEFECT
    none

CONTRACT_ASSURANCE_DEFECT
    none

PARITY_NEUTRAL_HARDENING
    optional generic EventBus normalize_step mechanism (default behavior unchanged)

intentional Minion architectural extensions
    ordered N-listener hook composition

PARITY_CONSTRAINED_RISK
    none

PI_BEHAVIOR_UNCERTAIN
    none
```

## Required questions

| Q | Answer |
|---:|---|
| 1 | YES. |
| 2 | YES. |
| 3 | YES. |
| 4 | YES. |
| 5 | YES. |
| 6 | NO. |
| 7 | YES. |
| 8 | YES. |
| 9 | YES. |
| 10 | YES. |
| 11 | YES. |
| 12 | YES. |
| 13 | YES. |
| 14 | YES. |
| 15 | YES. |
| 16 | YES. |
| 17 | YES. |
| 18 | YES. |
| 19 | YES. |
| 20 | YES. |
| 21 | YES. |
| 22 | NO; only truthful historical remediation descriptions remain. |
| 23 | YES, `TOOL-005`. |
| 24 | YES. |
| 25 | YES. |
| 26 | YES. |
| 27 | YES. |
| 28 | YES. |
| 29 | YES. |
| 30 | YES: 10/10/10/0. |
| 31 | YES. |
| 32 | NO. |
| 33 | NO. |
| 34 | NO. |
| 35 | NO. |
| 36 | NO. |
| 37 | NO. |
| 38 | NO. |
| 39 | YES. |
| 40 | YES. |

## Next action

Stop this review. The next pass is Rust Layer-06 implementation, conformance, and assurance. No
further Layer-06 contract review is required unless implementation exposes genuinely new contract
evidence.
