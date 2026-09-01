# Layer 08 final independent Rust contract review — PASS 12

## Exact target and mode

Review mode only. No candidate, shared-contract, canonical, Python, or Rust file was modified.

- code PR #13: `4decd72e6b153867c72a6e80967a92eeb72217c0`
- docs PR #3: `5da18e55801aa006d1a6cdd9a77ecdb91f0a7124`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- preceding PASS-11 review: docs PR #14 at `61805fe5c225a5debe6fb9da80a196f929da5bdd`

Both candidate heads were fetched and verified remote-reachable, open, Ready for Review, and equal
to coordination issue #12. This approval applies only to those exact candidate SHAs.

## Authority-first audit

The review used pinned Pi first, then the normative spec, manifest, canonical schema/scenario,
certified Rust architecture, assurance, and Python only as secondary implementation evidence.
Re-read:

- Pi `packages/agent/src/types.ts::AgentToolResult`, `AgentToolUpdateCallback`, and the
  `tool_execution_update` event;
- Pi `packages/agent/src/agent-loop.ts::executePreparedToolCall`;
- current `spec/tools.md` and the relevant `spec/agent.md` rule;
- `pi-parity-manifest.yaml::TOOL-019` and AG-001..AG-010/AG-021;
- `conformance/schema/agent-scenario.schema.json` and
  `conformance/agent/late-tool-update-ignored.yaml`;
- certified Rust `AgentToolResult`, update execution, and Layer-06 conformance adapter;
- PASS-12 assurance and Python type/runner only after the shared audit.

Pi's partial result has required `content` and `details`; optional `usage`, `addedToolNames`, and
`terminate`; and no nested call identity or error-status field. The enclosing update event carries
call identity and original arguments. The PASS-12 contract now expresses that distinction without
the omissions accepted by PASS 11.

## PASS-12 closure ledger

| Finding | Independent evidence | Result |
|---|---|---|
| L08-R011 — required details | `ToolPartialResult.details` has no default; direct construction without it raises `TypeError` | `RESOLVED` |
| L08-R011 — empty details observation | `_encode_partial` emits `details` unconditionally; canonical first update asserts `{}` | `RESOLVED` |
| L08-R011 — schema closure | reusable `toolPartialResult` requires `text` and `details`, forbids extras, and is referenced by all three fixture/expectation sites | `RESOLVED` |
| L08-R011 — usage evidence | runner decodes/encodes `Usage`; canonical second update asserts concrete normalized usage | `RESOLVED` |
| L08-R011 — optional presence | omitted optional fields remain absent; explicit `false`, non-empty names, and usage remain observable | `RESOLVED` |
| L08-R011 — Rust adapter | production Rust remains correct; adapter still expects strings and must be updated during Rust implementation | Open Rust implementation dependency, not a contract blocker |
| L08-R002 / L08-R004 | PASS-12 diff does not overlap the converged lifecycle surface; no new witness | remain provisionally closed |
| L08-R012 / L08-R013 | unchanged and coherent | remain resolved |

## Adversarial schema reproduction

Fresh validation against `$defs.toolPartialResult` produced:

```text
{}
    INVALID — text/details required

{"is_error": true}
    INVALID — required fields missing and additional property forbidden

{"tool_call_id": "nested"}
    INVALID — required fields missing and additional property forbidden

{"text": "x"}
    INVALID — details required

{"text": "x", "details": {}}
    VALID

{"text": "x", "details": {}, "usage": {"input": 5, "output": 3, "total_tokens": 8}}
    VALID

{"text": "x", "details": {}, "usage": null}
    INVALID — optional means absent, not explicit null

{"text": "x", "details": []}
    INVALID — Minion's already-approved structured-details domain is an object
```

The canonical scenario sends two real updates: one proves required-but-empty details survive, and
one proves non-empty details, usage, explicit `terminate: false`, and added tool names survive. Its
late update uses the same closed shape. The runner dispatches typed `ToolPartialResult` values
through production and only decodes/normalizes observations; it does not synthesize update
semantics.

## Complete Layer-08 regression review

The delta from the PASS-11 exact candidate is confined to the partial-result type, its canonical
decoder/encoder/schema/scenario, TOOL-019 evidence, and assurance/spec clarification. The full
PASS-11 state-machine audit was rechecked against that narrow delta. No new witness reopens the
held findings:

- prompt typed/sequence/text/images and all continuation branches: PASS;
- active/empty/assistant-last guards and initial pre-drain behavior: PASS;
- run-local messages/tools/config snapshot and whole-context replacement: PASS;
- dynamic run-local tool additions without uncontrolled registry reads: PASS;
- prompt lifecycle before steering and a single first provider request: PASS;
- tool-, steering-, and follow-up-driven continuation plus terminate ordering: PASS;
- represented error/aborted immediate termination: PASS;
- ordinary/failure lifecycle delivery, recovery catch boundary, and listener ordering: PASS;
- full streamed assistant partial fidelity and runtime-state timing: PASS;
- invocation-local `agent_end.messages`: PASS;
- no max-step or boundary-stop divergence: PASS;
- AG-007 remains deferred exclusively to Layer 09: PASS.

AG-001..AG-010 and AG-021 remain internally coherent (`adopted`, except AG-007's explicit
Layer-09 `deferred parity`). TOOL-019 now matches Pi and the executable shared evidence. No row
uses an unfilled placeholder as satisfying evidence. Manifest inventory is 76 rows / 76 unique
IDs.

## Rust independent implementability

The approved shape maps directly to certified Rust `AgentToolResult`: required `details: Value`,
optional usage/added names/terminate, and no nested identity/error fields. Rust need not copy
Python's dataclass or scheduler mechanics.

The current Rust Layer-06 conformance adapter still calls `as_str().unwrap()` for
`emits_updates[]`; fresh execution against the PASS-12 fixture fails there. This is an accurately
disclosed adapter-only evidence delta. The adapter must parse the shared object into the existing
typed `AgentToolResult` and serialize the full observation during the Rust implementation pass.
It must not change production update semantics or reconstruct fields absent from production.

That pending work means current Rust gates are not green against the new fixture and Rust Layer 08
is not implemented or certified. It does not make the now-complete language-neutral contract
ambiguous or require Python/shared remediation.

## Fresh evidence

```text
Python full pytest
    1043 passed, 19 expected failures (1062 collected)
    configured coverage 100.00% (2720/2720 statements)

ruff check
    PASS

ruff format — PASS-12-owned Python files
    PASS (2 files already formatted)

mypy
    PASS, 57 source files

schema validation suite
    PASS, 185 tests

manifest
    76 rows, 76 unique IDs

targeted Rust Layer-06 canonical regression
    expected FAIL at tool_execution_conformance.rs:102
    object fixture reaches the disclosed legacy as_str().unwrap() adapter path
```

A full-tree `ruff format --check` also reports seven older formatting differences outside the
PASS-12 delta (including a PASS-10-era update test); this is non-semantic repository hygiene and
does not contradict the PASS-12-owned-file formatting claim or contract approval.

## Contract-quality answers

```text
runner simulates production tool-update semantics
    NO

Python workaround required by an incomplete shared contract
    NO

shared shape forces Python mechanics on Rust
    NO

two conforming implementations can disagree about required/optional fields
    NO

earlier certified production semantics must change
    NO

Layer 09 leaked into Layer 08
    NO
```

## Findings

```text
PI_PARITY_DEFECT
    none — L08-R011 closed

CONTRACT_ASSURANCE_DEFECT
    none — L08-R011 closed

PI_BEHAVIOR_UNCERTAIN
    none

PARITY_CONSTRAINED_RISK
    none

PARITY_NEUTRAL_HARDENING
    full-tree Python formatting cleanup remains optional and outside PASS-12 semantics
```

## Verdict

```text
shared Layer-08 contract
    APPROVED FOR RUST IMPLEMENTATION

Python Layer 08
    CERTIFIED

Rust Layer 08
    NOT_IMPLEMENTED

Layer 08 cross-language
    NOT CLOSED

Layer 09
    NOT STARTED
```

This approval is exact-SHA-bound to code `4decd72e6b153867c72a6e80967a92eeb72217c0`
and docs `5da18e55801aa006d1a6cdd9a77ecdb91f0a7124`. Merge the approved shared/Python candidate, then
begin a separate Rust Layer-08 implementation pass. That pass must first update the Rust canonical
adapter through the existing `AgentToolResult` seam and restore the lower-layer canonical gate.
Do not implement Rust Layer 08 or start Layer 09 in this review pass.
