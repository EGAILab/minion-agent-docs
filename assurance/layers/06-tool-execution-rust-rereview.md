# Layer 06 Rust closure re-review — Tool execution pipeline

**Review date:** 2026-08-26
**Code candidate:** `minion-agent@573774575777e0945a8d8838a38ebec90df48c57`
**Docs candidate:** `minion-agent-docs@d3dc48bae7de99d708961631c9b3f570c1105180`
**Pinned Pi:** `b7bb00b936dbe21b8e160b3e89efdec361846699`
**Previous Rust review:** `d090b3ca79a66ca74117646210ce643c7264130b`
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

R002, R004, and R005 are resolved. R001's runtime behavior is repaired but its current public
ToolDefinition documentation says the opposite. R003 remains observably bypassable through a
public exported event seam. R006 cites a nonexistent requirement and therefore remains
incompletely traced.

## Finding closure

| Finding | Verdict | Reason |
|---|---|---|
| L06-R001 | OPEN | Production and canonical behavior validate raw JSON Schema, but `ToolDefinition.parameters` still says a raw dict is “not Python-validated.” |
| L06-R002 | RESOLVED | All four callback failure paths now expose the message only; canonical expectations use exact language-neutral text. |
| L06-R003 | OPEN | The helper is constrained, but public `ctx.events.on(TOOLS_POST_EXECUTE, ...)` still accepts a whole-result replacement and can rewrite identity/added names. |
| L06-R004 | RESOLVED | The actual ten scenarios are consistently reported as 10/10; pendingToolCalls remains Layer 07+. |
| L06-R005 | RESOLVED | Rust's existing signal types are acknowledged and the behavioral Layer-09 defer remains future-compatible. |
| L06-R006 | OPEN | Disposition prose is repaired, but production docs cite nonexistent `TOOL-022`; the raw-event bypass also leaves the documented constrained N-listener contract unenforced. |

## R001 — raw schema validation

Pinned Pi validates prepared arguments against every `Tool.parameters: TSchema`. The repaired
Python `_validate` now does the same at the shared level: Pydantic-backed definitions use
Pydantic, and raw object-valued schemas use `Draft202012Validator`. The canonical fixture carries
the actual Layer-05 JSON Schema mapping; the runner passes it through and does not validate.

Focused tests prove valid input executes, invalid input skips execute/after, preparation can repair
invalid input, and preparation can invalidate previously valid input. The Layer-05 schema domain
remains object-valued rather than restricted to a top-level `type: object`.

One current public implementation statement remains false:

```text
minion-agent-python/src/minion_agent/tools/definition.py::ToolDefinition.parameters
    “a raw, object-valued JSON Schema dict (not Python-validated -- TOOL-F010)”
```

That statement directly contradicts `_validate`, the repaired spec, TOOL-003, canonical evidence,
and the remediation assurance. Minimal closure is a documentation-only correction to describe the
real production validator. The semantic R001 implementation does not need another rewrite.

## R002 — error normalization

Pinned Pi uses `error.message`, not the runtime exception class. Python now uses `str(error)` at
prepare/before, execute, and after failure boundaries. Direct tests use exact equality; canonical
fixtures expect `cannot repair these arguments`, `policy engine unavailable`, `disk on fire`, and
`annotation service unavailable` without `RuntimeError:` prefixes. Validation diagnostics retain a
Minion-authored `invalid arguments:` prefix while host-library detail is asserted only through a
language-neutral substring.

```text
L06-R002
    RESOLVED
```

## R003 — after-hook authority

Pinned Pi permits partial overrides of exactly:

```text
content
details
isError
usage
terminate
```

The new `AfterToolCallOverride`, `_merge_override`, and
`register_after_tool_call_hook` correctly implement that surface and preserve `tool_call_id`,
`tool_name`, and `added_tool_names`. The migrated tests and canonical runner use the helper.

However, the old public escape path remains exported:

```text
TOOLS_POST_EXECUTE is exported from minion_agent.tools
Context.events.on is public
TOOLS_POST_EXECUTE remains a public WATERFALL event over ToolResult
```

A direct production-seam probe registered a raw listener and observed:

```text
tool_call_id       rewritten
tool_name          rewritten-name
added_tool_names   (injected,)
content            changed
```

The helper being the “only sanctioned” path is convention, not structural enforcement. It is
therefore still false that Python exposes only the constrained override surface or that identity
replacement is impossible through public API.

Minimal repair: make the production post-execute event itself carry/fold the constrained override
type, or stop exporting/publicly admitting raw whole-result listeners and enforce the adapter at
the dispatch boundary. Add a negative public-seam regression test. Python certification remains
open until this is real rather than conventional.

## R004 — canonical inventory

Repository discovery from the pre-Layer-06 baseline yields exactly ten changed Layer-06 fixtures:

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

Current spec/assurance/handoff use 10/10. `pending-tool-calls-state` remains a Layer-07+ placeholder,
not a Layer-06 defer.

```text
L06-R004
    RESOLVED
```

## R005 — signal defer

The current contract accurately records the asymmetry:

- pinned Pi accepts a signal in hooks and execute;
- Rust Layer 05 already has `ToolExecutionSignal` and `ToolExecutionRequest.signal`;
- Python has no certified corresponding cancellation architecture;
- Layer 06 certifies non-cancelled semantics;
- Layer 09 owns cancellation propagation/timing/results.

```text
SIGNAL DEFER
    ACCEPTED

future non-cancelled Layer-06 semantic redesign required
    NO

L06-R005
    RESOLVED
```

## R006 — hook composition

The normative prose now consistently distinguishes Pi's zero/one optional callback from Minion's
observable N-listener extension. Registration order, accumulated before/after replacements,
short-circuit behavior, and failure behavior are specified and are implementable with Rust's
ordered Runtime event machinery.

Traceability is not complete:

```text
register_after_tool_call_hook docstring
    cites TOOL-022

pi-parity-manifest.yaml
    contains no TOOL-022 row

manifest inventory
    65 / 65 unique IDs
```

TOOL-004/005 discuss the extension, but the implementation explicitly claims a separate missing
requirement. That dangling requirement reference must either be removed in favor of TOOL-004/005
or backed by a real requirement row with complete Pi/Minion/spec/evidence/Rust-planned fields.
R003's raw event bypass must also be closed so the implemented N-listener surface actually has the
authority described by the requirement.

## Regression and runner review

```text
focused tools/conformance tests
    PASS

manifest
    65 / 65 unique

stage ordering
    PASS

mode/default/contagion/failure isolation
    PASS

parallel source/completion/result ordering
    PASS

late update cutoff
    PASS, production-owned

length stop
    PASS

Layer-05 source/semantics changed
    NO
```

The canonical runner passes a plain JSON Schema into the real ToolDefinition, invokes the real
ToolRegistry/executor, and uses the constrained helper for its scripted after hooks. It does not
validate, normalize exceptions, choose scheduling, reorder results, or suppress late updates.

## Rust feasibility

The repaired semantics remain implementable with existing Layer-05 types and Runtime. Rust can add
a JSON Schema validator later, normalize typed errors to semantic messages, model
`AfterToolCallOverride`, compose ordered hook listeners, retain the existing structural signal
field, and expose batch results to a future AgentLoop without redesign.

```text
Layer-05 ToolDefinition reusable       YES
ToolRegistry reusable                  YES
Runtime redesign required              NO
JSON Schema validation implementable   YES
error normalization implementable      YES
constrained override implementable     YES
N-listener ordering implementable      YES
signal seam reusable                    YES
future AgentLoop compatible             YES
```

## Required questions

| Q | Answer |
|---:|---|
| 1 | YES. |
| 2 | YES. |
| 3 | YES. |
| 4 | YES. |
| 5 | YES. |
| 6 | YES. |
| 7 | YES. |
| 8 | YES. |
| 9 | YES. |
| 10 | YES, exactly `boom`. |
| 11 | YES. |
| 12 | YES. |
| 13 | content, details, isError, usage, terminate. |
| 14 | NO: the helper does, but the exported raw event does not (R003). |
| 15 | YES through the raw public event; NO through the helper (R003 OPEN). |
| 16 | YES through the raw public event; NO through the helper (R003 OPEN). |
| 17 | YES through the raw public event; NO through the helper (R003 OPEN). |
| 18 | YES through the helper. |
| 19 | YES. |
| 20 | YES through the helper. |
| 21 | 10. |
| 22 | YES. |
| 23 | YES, 10/10 with zero Layer-06 defers. |
| 24 | YES for current candidate surfaces; historical rejection remains truthful. |
| 25 | YES. |
| 26 | YES. |
| 27 | YES. |
| 28 | YES. |
| 29 | YES — ACCEPTED. |
| 30 | YES. |
| 31 | YES in normative prose. |
| 32 | YES. |
| 33 | YES through the helper. |
| 34 | YES. |
| 35 | YES. |
| 36 | YES when the listener delegates with replacement. |
| 37 | YES. |
| 38 | YES through the helper. |
| 39 | YES through the helper. |
| 40 | NO across the full public surface (R003). |
| 41 | YES through the helper. |
| 42 | NO: `TOOL-022` is dangling and R003 remains (R006 OPEN). |
| 43 | YES. |
| 44 | YES. |
| 45 | YES. |
| 46 | YES. |
| 47 | YES. |
| 48 | YES. |
| 49 | YES. |
| 50 | YES. |
| 51 | YES. |
| 52 | YES. |
| 53 | NO. |
| 54 | YES. |
| 55 | YES. |
| 56 | YES. |
| 57 | YES. |
| 58 | YES. |
| 59 | YES. |
| 60 | NO active semantic parity defect; R001 has a current contradictory public doc statement. |
| 61 | YES: R001 documentation, R003 public authority, R006 traceability. |
| 62 | NO. |
| 63 | NO. |
| 64 | NO, not unambiguously while the public hook surface and traceability contradict the contract. |
| 65 | NO. |

## Next action

Return only the remaining closures to the shared/Python owner:

1. correct `ToolDefinition.parameters`' stale “not Python-validated” documentation;
2. make the constrained after-hook override authoritative at the public production event seam;
3. remove or define the dangling `TOOL-022` traceability reference.

Do not implement Rust Layer 06 and do not start Layer 07.
