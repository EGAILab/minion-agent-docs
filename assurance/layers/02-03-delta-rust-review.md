# Rust post-certification delta review — Layers 02 and 03

Date: 2026-08-24

## Reviewed state

- `minion-agent`: `f88c79df837685f85d0dad153d94c96912f99eb1`
- `minion-agent-docs`: `6f23c964150f468852b1d3544eba50dc93164b02`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- historical Rust Layer-03 implementation head: `31ed6698a1e4a9f5d3134d2c2b1788f920ceb330`
- historical PR #4 merge: `2519fc1565ff40ffeb8aa047bc2d3f0aa8bef512`

This is an independent Rust implementation-owner review. Python and the existing Rust
implementation were treated as evidence, not semantic authority. No Rust implementation was
changed because the Layer-03 delta contract is rejected below.

## Layer 02

### A — LLM-F011: required `tool_name`

**Verdict: APPROVED.**

Pinned Pi declares `ToolResultMessage.toolName: string` (not optional) in
`packages/ai/src/types.ts::ToolResultMessage`. The candidate contract consistently requires
`tool_name`: `spec/llm.md` has no optional marker, the Session scenario schema requires it for a
`tool_result`, and `rich-assistant-message-round-trip.yaml` exercises the non-default names
`lookup` and `generic_tool` through Session encode/decode.

The Python production path is genuine rather than fixture-only:

```text
ToolCall.name
    -> tools.execute.execute_call
    -> ToolResult.tool_name
    -> ToolResult.to_message
    -> ToolResultMessage.tool_name
```

All normal and error branches source the value from the actual call name. The conformance runner
reads `spec["tool_name"]` directly and supplies no fallback or fabricated constant.

Idiomatic Rust maps this rule directly as `pub tool_name: String`. The current
`Option<String>` is a Rust implementation defect to correct after the shared contract is approved
as a whole; it does not weaken this verdict.

## LAYER 02 DELTA CONTRACT

**APPROVED**

## Layer 03

### B — SES-F004: compaction event identity

**Verdict: APPROVED, with an assurance-history correction required.**

The reviewed candidate deliberately standardizes `session/compaction`. It is coherent with the
namespaced Session-owned operation identities `session/forked` and `session/reset`, avoids the
collision-prone bare operation name, and is now directly pinned by `spec/session.md` and
`session-owned-event-identity.yaml`. The scenario observes the real committed event sequence; the
Python runner reads `event.kind` from the actual log and does not infer the value from the compact
step. Rust already using this spelling is not the semantic basis for approval.

The history must, however, be described accurately. The previous `spec/session.md` explicitly
pinned bare `compaction`, and both earlier implementation plans repeated it. Therefore the old
spelling was a **superseded prior contract choice**, not merely implementation drift and not a
value that “no normative source pinned.” The handoff/code commentary claiming otherwise should be
corrected when shared assurance is revised.

`expect_event_kinds` is language-neutral and thin: it is a generic ordered array of normative
strings read from real stored events. It introduces no Agent lifecycle ownership.

### C — SES-F005: role-specific content validity

**Verdict: APPROVED.**

The corrected unions match pinned Pi and the frozen Layer-02 vocabulary:

- user: text, image;
- assistant: text, thinking, tool call;
- tool result: text, image.

Independent schema probes accepted every listed valid role/block combination and rejected:
user+thinking, user+tool-call, assistant+image, tool-result+thinking, and
tool-result+tool-call. A tool result without `tool_name` was also rejected. The Rust typed enums
naturally express the same unions without runner-side dropping or reinterpretation.

### D — SES-F006: future fork boundary

**Verdict: APPROVED.**

The language-neutral rule `0 <= boundary <= committed source tip` is necessary to preserve a
fixed ancestry boundary. Permitting an empty parent to fork at future sequence 1 allows a later
parent event at sequence 1 to leak into the already-created child. The schema excludes negative
values, and the real Session API rejects values above the committed tip.

`expect_error` is thin: the runner calls `fork`, observes the real implementation failure, and
normalizes it to the project’s established language-neutral error category. It does not pre-check
the boundary. Rust can map its typed `InvalidForkBoundary` variant to that category.

### E — SES-F007: atomic append and compaction linearization

**Verdict: REJECTED — CONTRACT_ASSURANCE_DEFECT.**

The candidate now defines append atomicity sufficiently for supported execution models:
validation, sequence allocation, append, and committed publication are one logical operation;
committed sequence numbers are unique, gapless, and ordered by commit; rejected validation leaves
no trace. This does not require every implementation to support arbitrary simultaneous callers.
If an implementation admits OS-thread or task concurrency, however, it must preserve those
observables.

The specification does **not** pin the corresponding compaction requirement. It never states that
the effective-surface/provenance snapshot and the compaction event commit are one logical operation
relative to concurrent append/reset/compact operations. That omission admits two conforming-looking
implementations with different observable histories:

```text
compact reads effective surface
    -> another append commits
    -> compact commits a marker derived from the stale snapshot
```

The interleaved event has a sequence before the compaction marker but is absent from the snapshot
that produced `superseded_through` and retained provenance. This is the exact failure class exposed
and hardened in the first Rust Layer-03 implementation. Append itself can remain perfectly atomic,
so the new append paragraph does not rule it out.

The required language-neutral clarification is approximately:

> In an execution model that admits concurrent Session mutation, a compaction's effective-surface
> and retained-provenance snapshot plus its compaction-event commit form one linearizable operation
> relative to append, reset, and other compaction operations. Events committed before that
> operation's linearization point participate according to the derivation rules; events committed
> after it do not alter the recorded compaction provenance.

This is not a universal thread-safety mandate. A single-threaded/cooperative implementation whose
synchronous Session operation cannot interleave may satisfy the rule without a lock. Python's
current synchronous path appears compatible on that basis, and Rust's single mutex spanning
snapshot and marker commit is compatible. The contract must nevertheless state the observable rule
so another implementation cannot legally repeat the split-lock race.

The new Python concurrency tests prove gapless append sequencing and absence of a torn Python call,
but do not independently pin the compaction snapshot/provenance invariant under a forced
interleaving. Add focused language evidence where the execution model permits such interleaving.

### F — SES-F008: event-name validation

**Verdict: APPROVED (Rust implementation defect).**

The canonical expression is:

```regex
^[a-z][a-z0-9_]*(?:/[a-z][a-z0-9_-]*)*$
```

It yields:

| Value | Result |
|---|---|
| `plugin/foo` | accept |
| `plugin/foo-bar` | accept |
| `plugin/foo_bar` | accept |
| `plugin2/foo` | accept |
| `Plugin/foo` | reject |
| `plugin-name/foo` | reject |
| `plugin//foo` | reject |
| `/foo` | reject |
| `plugin/` | reject |

The spec, schema, and Python validator agree. Current Rust applies the same segment rule to the
namespace and later path segments, so it incorrectly accepts `plugin-name/foo`. That is a local
Rust implementation defect, not a contract defect.

## Scenario and runner review

- Session scenarios discovered: 19.
- Current Layer-03 executable: 18.
- Layer-04 deferred: 1 (`request-reconstruction-after-target-transform.yaml`).
- New delta scenarios: `session-owned-event-identity.yaml` and
  `fork-future-boundary-rejected.yaml`.
- Agent-deferred or invalid/misclassified Session scenarios: none.

The Session runner remains thin. It invokes real Session operations, reads real stored events,
normalizes typed values/errors, and compares observations. It does not simulate derivation, Agent
lifecycle, target-model transformation, or expected operation identity.

## Parity manifest and governance

The semantic ownership/dispositions in the parity manifest are sound: `AI-006` cites pinned Pi for
required `tool_name`, while Minion-owned Session behavior does not fabricate Pi evidence. The Rust
evidence fields are stale now that a real Layer-03 implementation exists; they should be updated to
concrete paths such as `llm/vocabulary.rs` and `session/mod.rs`, with the delta remediation state.
This is an evidence-maintenance issue, not the semantic rejection above.

Workflow section 4.6 is approved. It preserves prior certification history and permits a targeted
reopen only for evidence of ambiguity, observable cross-language mismatch, certified
implementation violation, or runner workaround. A merely cleaner implementation does not reopen a
contract.

## LAYER 03 DELTA CONTRACT

**REJECTED — CONTRACT_ASSURANCE_DEFECT**

Blocking defect: `spec/session.md` does not define compaction snapshot/provenance and marker commit
as one logical/linearizable operation in execution models that admit concurrent Session mutation.

## Rust implementation disposition

- Shared contracts both approved: **NO**.
- Rust implementation modified: **NO**.
- Rust remediation status: **BLOCKED**.
- Next owner: **Python/shared assurance**.
- Required next step: narrowly repair the language-neutral compaction atomicity rule, add suitable
  evidence, publish a new candidate SHA, and request a fresh Rust delta review.
- Layer 02 final delta certification readiness: **NO** — contract approved, but the required Rust
  `tool_name: String` remediation has not begun because this pass forbids Rust changes when either
  shared delta contract is rejected.
- Layer 03 final delta certification readiness: **NO**.
- Layer 04 started: **NO**.

## Independent probes run

- adversarial JSON Schema role/content and required-`tool_name` matrix: passed;
- focused Python Session concurrency, schema-validation, tool-execution, and derivation tests with
  coverage disabled for the focused run: passed;
- canonical Session runner inspection: event kinds and errors are observed from real APIs;
- pinned Pi declaration inspection: `ToolResultMessage.toolName` is required and role-specific
  content unions match the candidate.

No new `PI_PARITY_DEFECT` or `PI_BEHAVIOR_UNCERTAIN` was found. The only new blocking result is the
Layer-03 `CONTRACT_ASSURANCE_DEFECT` above.
