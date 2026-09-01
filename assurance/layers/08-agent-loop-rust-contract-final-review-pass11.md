# Layer 08 final independent Rust contract review — PASS 11

## Exact target

Review mode only. No candidate, Python, Rust, shared-contract, or canonical file was modified.

- code PR #13: `a8744f73aa254f573618b1eb1dfe8f2cdee82ac0`
- docs PR #3: `ddf324a20692919edae6a8e718fd9ed482ecf009`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- preceding PASS-10 review: docs PR #13 at `c4627bdc1a3edc7aced8d1f050922066078e1924`

Both candidate heads were fetched and verified remote-reachable, open, Ready for Review, and equal to coordination issue #12. This verdict applies only to these exact SHAs.

## Pi-first audit

Re-read pinned Pi before the candidate implementation:

- `packages/agent/src/types.ts`: `AgentToolResult<T>`, `AgentToolUpdateCallback<T>`, `AgentEvent`, `AgentState`, `AgentContext`, `AgentLoopTurnUpdate`.
- `packages/agent/src/agent-loop.ts`: `executePreparedToolCall`, stream/run loop, post-turn ordering.
- `packages/agent/src/agent.ts`: lifecycle wrapper, failure recovery, state reducer, serial listeners.

Pi's partial value has required `content` and `details`, optional `usage`, `addedToolNames`, and `terminate`, and no nested call identity or error-status field. The enclosing event carries call identity.

No new witness reopens L08-R002/L08-R004. L08-R012 and L08-R013 remain closed.

## PASS-11 finding ledger

| Finding | Independent result | Verdict |
|---|---|---|
| L08-R011 — nested identity/error fields | New `ToolPartialResult` removes them structurally and update dispatch passes the value unchanged | `RESOLVED` |
| L08-R011 — optional-field presence | Python now uses `None` for optional usage/added names/terminate | `RESOLVED` at production type boundary |
| L08-R011 — required details | Candidate says details is required but the constructor defaults it and canonical permits/produces omission | `PARTIALLY_RESOLVED_BLOCKING` |
| L08-R011 — complete canonical structure | Details/terminate/added names improved; usage remains unrepresentable/unobserved and schema remains an unrestricted object | `PARTIALLY_RESOLVED_BLOCKING` |
| L08-R011 — Rust adapter delta | Accurately disclosed as pending Rust-owned adapter work; production Rust remains correct | Open implementation dependency, not a new production defect |
| L08-R012 | Complete `streaming_message` rule remains coherent | `RESOLVED` |
| L08-R013 | AG-001 evidence pointer remains correct | `RESOLVED` |

## Remaining L08-R011 contract defects

### Required `details` is still optional and collapsible

**Classification:** `PI_PARITY_DEFECT` and `CONTRACT_ASSURANCE_DEFECT`.

The normative spec correctly says `content` and `details` are required. Certified Rust's `AgentToolResult.details: Value` is required. Python's new type instead declares:

```python
details: dict[str, Any] = field(default_factory=dict)
```

so `ToolPartialResult(content=())` is valid without supplying details. A direct witness constructs it successfully and observes `{}`. The canonical decoder likewise uses `spec.get("details", {})`.

The encoder then includes details only when truthy:

```python
if partial.details:
    encoded["details"] = partial.details
```

An explicit required empty object is therefore omitted from observation. This repeats the already-established `{}`-versus-absence hazard from generated Layer-06 results and contradicts the candidate's own “required” rule.

### Canonical schema/evidence remains incomplete

**Classification:** `CONTRACT_ASSURANCE_DEFECT`.

`toolUpdate.partial`, `emits_updates[]`, and `late_update` remain unrestricted `type: object` schemas. Fresh schema witnesses confirm all of these are accepted as partial values:

```json
{}
{"is_error": true}
{"tool_call_id": "nested"}
```

Thus the schema neither represents the approved fields nor excludes the exact Python-only fields PASS 11 says are forbidden.

The fixture/observer now covers text, non-empty details, explicit false terminate, and added-tool names, which is a real improvement. It still does not decode or encode concrete `usage`; a direct witness with non-empty usage serializes without that field. The canonical therefore does not yet prove the full `AgentToolResult` shape claimed by spec/manifest.

### Narrow remediation

1. Make Python `ToolPartialResult.details` a genuinely required constructor field; convenience constructors may explicitly supply `{}`.
2. Serialize `details` unconditionally, including `{}`, because absence is not a legal state.
3. Define a reusable language-neutral partial-result schema with required content/text shorthand and details, optional usage/added-tool names/terminate, `additionalProperties: false`, and no identity/error fields.
4. Decode and encode concrete usage and add discriminating canonical evidence for it.
5. Retain the now-correct production type and optional `None` distinctions.

## Rust adapter dependency

PASS 11 now accurately records that Rust production is already Pi-faithful while its Layer-06 conformance adapter still parses update fixtures as strings. Fresh execution confirms:

```text
cargo test -p minion-agent --test tool_execution_conformance
    all_layer_06_scenarios_drive_the_real_rust_tool_executor

FAIL: Value::as_str().unwrap() on the object-shaped emits_updates fixture
```

This adapter-only change is valid Rust implementation/evidence work once the shared shape is approved; it must not alter production `AgentToolResult`. It is not, by itself, a reason to make the Python/shared owner edit Rust. It does, however, remain a required lower-layer regression gate before Rust Layer-08 certification or cross-language closure.

## Full Layer-08 regression audit

The PASS-11 production diff is confined to the partial-update type. The complete state-machine conclusions from the prior final review remain supported:

- prompt typed/sequence/text/images and continuation branches: PASS;
- exact active/empty/assistant-last errors and initial pre-drain behavior: PASS;
- run-local context/model/thinking snapshots and whole-context replacement: PASS;
- dynamic run-local tool additions without live-registry leakage: PASS;
- prompt lifecycle before steering and one first provider request: PASS;
- tool/steering/follow-up continuation and terminate ordering: PASS;
- represented error/aborted terminal behavior: PASS;
- failure recovery trace/catch boundary and listener ordering: PASS;
- full streamed partial fidelity and runtime-state timing: PASS;
- invocation-local `agent_end.messages`: PASS;
- no max-step/boundary-stop divergence: PASS;
- AG-007 remains deferred exclusively to Layer 09: PASS.

AG-001..AG-010 and AG-021 retain coherent dispositions. TOOL-019 remains blocked only in the incomplete partial-result assurance described above and the declared Rust adapter dependency. No applicable manifest row cites a placeholder as satisfying evidence. Manifest inventory is 76 rows / 76 unique IDs.

## Fresh gates

```text
Python pytest
    1043 passed, 19 xfailed
    configured coverage 100.00%

ruff
    PASS

mypy
    PASS, 57 source files

manifest
    76 rows, 76 unique IDs

targeted Rust Layer-06 canonical regression
    FAIL in the acknowledged object-fixture adapter parse
```

Green Python gates do not override the required-field and canonical-schema defects.

## Findings

```text
PI_PARITY_DEFECT
    L08-R011 remains open: Python permits omission of Pi-required partial details

CONTRACT_ASSURANCE_DEFECT
    L08-R011 remains open: required empty details collapse to absence;
    canonical schema admits forbidden/undefined shapes and does not observe usage

PI_BEHAVIOR_UNCERTAIN
    none

PARITY_CONSTRAINED_RISK
    none

PARITY_NEUTRAL_HARDENING
    none
```

## Verdict

```text
shared Layer-08 contract
    REJECTED

Python Layer 08
    REOPENED

Rust Layer 08
    BLOCKED / NOT_IMPLEMENTED

Layer 08 cross-language
    NOT CLOSED

Layer 09
    NOT STARTED
```

PASS 11 resolves the larger Python type and identity/error-field defects, but L08-R011 is not fully closed. Return only the narrow required-details and complete canonical-shape remediation. Any changed candidate SHA requires exact-SHA review.
