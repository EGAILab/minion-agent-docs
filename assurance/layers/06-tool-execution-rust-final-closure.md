# Layer 06 Rust final closure review

**Review date:** 2026-08-26
**Code candidate:** `minion-agent@4185fa6c8e7baf311f1bc4652c9f90e240bff070`
**Docs candidate:** `minion-agent-docs@5be4e0a2717f07f8e3f7324d1191fc788c40ceee`
**Pinned Pi:** `b7bb00b936dbe21b8e160b3e89efdec361846699`
**Previous Rust re-review:** `09764e6fc86ee8619a6139202a8eee9440d6aabf`
**Rust production modified:** NO

## Verdict

```text
Layer-06 shared contract
    REJECTED

Python Layer 06
    IN_REMEDIATION

Rust Layer 06
    NOT_IMPLEMENTED

Rust current certified position
    Layer 05

Layer 07
    NOT STARTED
```

`L06-R001` is resolved. `L06-R002`, `L06-R004`, and `L06-R005` remain resolved.
`L06-R003` and `L06-R006` remain open because protected after-hook fields are restored only
after the complete waterfall: later listeners can observe and act on forbidden intermediate
replacements.

## Finding closure

| Finding | Verdict | Evidence |
|---|---|---|
| `L06-R001` | RESOLVED | Public module/field documentation now distinguishes Layer-05 storage from Layer-06 execution-time validation through Pydantic or `jsonschema`; raw-schema production tests remain green. |
| `L06-R002` | RESOLVED | Focused error tests still expose `boom`/semantic messages without Python exception-class prefixes. |
| `L06-R003` | OPEN | `_finalize` restores final identity and `added_tool_names`, but only after `EventBus.waterfall`; mandatory two-listener probes show downstream listeners receive forbidden replacements. |
| `L06-R004` | RESOLVED | The ten Layer-06 scenarios remain executable and pass; `pending-tool-calls-state` remains Layer 07+. |
| `L06-R005` | RESOLVED | Rust signal structures remain acknowledged and cancellation behavior remains explicitly deferred to Layer 09. |
| `L06-R006` | OPEN | The dangling `TOOL-022` API citation is removed, but the normative N-listener composition is internally inconsistent until protected authority is enforced at each waterfall step. |

## R001 — public schema documentation

The current `ToolDefinition` module and `parameters` field documentation state:

```text
Layer 05 construction stores the schema.
Layer 06 validates execution arguments.
Pydantic model -> Pydantic validation.
Raw JSON Schema mapping -> jsonschema validation.
```

Searches found the old phrases only in explicitly historical remediation prose. `_validate`
still uses `Draft202012Validator` for raw mappings after `prepare_arguments`. The focused raw
schema and prepare-before-validation tests passed. No R001 blocker remains.

## R003 — authoritative after-hook authority

Pinned Pi's `AfterToolCallResult` permits only:

```text
content
details
isError
usage
terminate
```

It excludes `tool_call_id`, `tool_name`, and `added_tool_names`.

The candidate snapshots those protected fields before `EventBus.waterfall` and restores them
after the entire waterfall. This blocks forbidden changes in the final direct fields, preserves
allowed `content`/`terminate` changes, and preserves execute-produced `added_tool_names`.
`ToolResult` is frozen, so in-place mutation is blocked.

It does not protect the accumulated value between listeners. A production-seam probe registered
a raw listener A that delegated a replacement containing:

```text
tool_call_id     evil-id
tool_name        evil-name
added_tool_names [evil]
```

Listener B observed all three forbidden values. A second mixed raw -> helper -> raw probe showed
both later listeners observing them; the helper copied `evil-name` into its allowed `details`
override, making the forbidden intermediate identity indirectly observable in the final result:

```text
SEEN  helper: evil-id / evil-name / [evil]
      raw:    evil-id / evil-name / [evil]
FINAL t1 / echo / [alpha] / details.helper_seen = evil-name
```

The root cause is exact: `EventBus.waterfall.next_(replacement)` passes the replacement unchanged
to the next listener, while `_finalize` normalizes only the final return value. Final restoration
is therefore not an authoritative per-listener boundary.

Minimal shared repair: normalize the protected fields after every listener application/before
delegation to the next listener (or use an equivalent event-specific dispatcher boundary), and
add a regression test in which listener B must see the original id, name, and added-tool names
after listener A attacks them. No generic EventBus redesign is required.

## R006 — traceability and composition

`register_after_tool_call_hook` no longer cites `TOOL-022`; it cites existing `TOOL-005`.
The manifest contains 65 rows, 65 unique IDs, and no `TOOL-022` row. Current API/normative
surfaces classify Pi's single callback separately from Minion's intentional ordered N-listener
extension.

However, `TOOL-005` and `spec/tools.md` simultaneously say that protected fields cannot be
replaced and that each listener sees the accumulated result produced by the previous listener.
Production currently lets that accumulated result contain forbidden protected replacements.
Thus the N-listener rule is not yet coherent or implemented across raw/helper paths. R006 closes
when R003's authority holds at each step and the mandatory downstream-observer test passes.

## Public-seam probes

| Probe | Result |
|---|---|
| Raw listener final `tool_call_id` rewrite | BLOCKED |
| Raw listener final `tool_name` rewrite | BLOCKED |
| Raw listener final `added_tool_names` rewrite | BLOCKED |
| In-place mutation | BLOCKED (`ToolResult` frozen) |
| Allowed `content` override | PASS |
| Allowed `terminate` override | PASS |
| Execute-produced `added_tool_names` preservation | PASS |
| Mixed raw/helper final restoration | PASS |
| Failure short-circuit | PASS |
| Listener B sees original `tool_call_id` after attack | FAIL (`evil-id`) |
| Listener B sees original `tool_name` after attack | FAIL (`evil-name`) |
| Listener B sees original `added_tool_names` after attack | FAIL (`evil`) |
| Protected authority enforced per waterfall step | FAIL |

## Canonical and focused evidence

The Layer-06 scenarios remain:

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

Fresh focused results:

```text
tools/test_execute.py + tools/test_post_execute.py
    36 passed

Layer-06 canonical scenarios
    discovered/selected 10
    executed            10
    passed              10
    deferred             0

manifest
    rows                 65
    unique IDs           65
```

The canonical runner remains thin and unchanged by this remediation. It uses the production
executor and constrained helper; it does not restore protected fields or implement waterfall
authority. `pending-tool-calls-state` remains assigned to Layer 07+.

## Rust feasibility

The existing Layer-05 `ToolDefinition`, `ToolRegistry`, `ToolExecutionSignal`, Runtime registry,
and context surface remain reusable. No Runtime or Layer-05 redesign is required. Rust can model
the correct rule with a typed `AfterToolCallOverride` or another implementation that normalizes
after each listener; it need not copy Python's snapshot/restore technique. Implementation must
not begin until the shared/Python per-step authority defect is repaired and independently closed.

## Active findings

```text
PI_PARITY_DEFECT
    L06-R003 — downstream listeners observe forbidden protected-field replacements

CONTRACT_ASSURANCE_DEFECT
    L06-R006 — N-listener accumulated-result rule contradicts protected-field authority

PARITY_NEUTRAL_HARDENING
    none

intentional Minion architectural extensions
    ordered N-listener hook composition (accepted in principle; implementation still open)

PARITY_CONSTRAINED_RISK
    none

PI_BEHAVIOR_UNCERTAIN
    none
```

## Required questions

| Q | Answer |
|---:|---|
| 1 | YES. |
| 2 | NO; old wording remains only in explicitly historical remediation prose. |
| 3 | YES. |
| 4 | YES. |
| 5 | `content`, `details`, `isError`, `usage`, and `terminate`. |
| 6 | NO. |
| 7 | NO in final direct output. |
| 8 | NO in final direct output. |
| 9 | NO in final direct output. |
| 10 | NO; `ToolResult` is frozen. |
| 11 | YES. |
| 12 | YES. |
| 13 | YES. |
| 14 | YES for final restoration; NO for per-listener accumulated authority. |
| 15 | YES, but with the per-step authority defect. |
| 16 | NO; listener B sees `evil-id`. |
| 17 | NO; listener B sees `evil-name`. |
| 18 | NO; listener B sees `evil`. |
| 19 | NO. |
| 20 | YES. |
| 21 | NO. |
| 22 | NO in current API/normative surfaces; historical review/remediation text truthfully mentions it. |
| 23 | YES. |
| 24 | YES as citations, but `TOOL-005`'s promised authority is not implemented per step. |
| 25 | YES. |
| 26 | YES. |
| 27 | YES, registration order. |
| 28 | YES. |
| 29 | YES in prose, but production contradicts protected authority between listeners. |
| 30 | NO at each listener boundary; YES only for final restoration. |
| 31 | YES. |
| 32 | YES: 10/10/10/0. |
| 33 | YES. |
| 34 | YES, ACCEPTED. |
| 35 | NO. |
| 36 | NO. |
| 37 | YES. |
| 38 | YES. |
| 39 | NO until the shared per-listener authority rule is repaired; the intended rule itself is understandable. |
| 40 | YES. |
| 41 | YES: `L06-R003`. |
| 42 | YES: `L06-R006`. |
| 43 | NO. |
| 44 | NO. |
| 45 | NO. |

## Next action

Return only the remaining R003/R006 per-waterfall-step authority blocker to the shared/Python
owner. Do not implement Rust Layer 06 and do not start Layer 07.
