# Layer 08 final independent Rust contract review — PASS 10

## Review target

Review mode only. No candidate, Python, Rust, shared-semantic, or canonical file was modified.

- code PR #13: `36429068c104f165e04a9aa06fa69f35a5f280ad`
- docs PR #3: `b3f44f3a323ae00831a85ed8e75f9f86df1289fa`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- preceding final review: docs PR #12 at `e747e91536f9a66dce526cf5b91eebfbc6ef0ae7`

The candidate heads were fetched and verified remote-reachable, open, Ready for Review, and equal to coordination issue #12. This verdict applies only to the exact SHAs above.

## Independence and Pi audit

Reviewed in authority order: pinned Pi, normative spec, manifest, canonical schema/scenarios, certified Rust architecture, assurance, then Python as secondary evidence.

Pinned symbols re-read:

- `packages/agent/src/types.ts`: `AgentState`, `AgentToolResult`, `AgentToolUpdateCallback`, `AgentContext`, `AgentEvent`, `AgentLoopTurnUpdate`.
- `packages/agent/src/agent.ts`: prompt/continue entry, context/config snapshot, lifecycle, failure recovery, reducer/listener delivery.
- `packages/agent/src/agent-loop.ts`: run/turn loops, streaming lifecycle, post-turn ordering, tool execution/update/finalization.

The PASS-9 convergence result remains held: no new witness reopens L08-R002 or L08-R004. The per-listener yield rule remains the correct Python analogue of Pi's awaited serial listener loop.

## PASS-10 findings re-review

| Finding | PASS-10 claim | Independent result | Verdict |
|---|---|---|---|
| L08-R011 | Structured tool-update payload adopted end to end | Payload is no longer a string, but Python reuses a larger, observably different `ToolResult`; canonical evidence hides most fields; current certified Rust canonical regression fails | `PARTIALLY_RESOLVED_BLOCKING` |
| L08-R012 | Correct complete `streaming_message` rule | Normative spec now states every message's start/end window and full streamed assistant partials without the provider-request contradiction | `RESOLVED` |
| L08-R013 | Correct AG-001 Python pointer | Pointer now identifies `_execute_run` / `_run_inner` / `_admit_messages` | `RESOLVED` |

## L08-R011 — remaining structured-update defect

**Classification:** `PI_PARITY_DEFECT` and `CONTRACT_ASSURANCE_DEFECT`.

Pinned Pi's callback value is exactly `AgentToolResult<T>`:

```text
content
details
usage?
addedToolNames?
terminate?
```

It has no nested `toolCallId`, `toolName`, or `isError`; call identity is already carried by the enclosing `tool_execution_update` event. Certified Rust represents this faithfully with `AgentToolResult` and `ToolExecutionUpdate { tool_call_id, tool_name, arguments, update }`.

PASS 10 instead changes Python `ToolUpdate` to accept its existing finalized pipeline `ToolResult`. That type adds:

```text
tool_call_id
tool_name
is_error
```

and uses concrete defaults where Pi/Rust preserve optional absence:

```text
terminate = false
added_tool_names = ()
```

`_execute_and_finalize.update()` then normalizes the nested id/name and preserves nested `is_error`. A direct live-event witness supplied spoofed identity, `is_error=true`, details, terminate, and added names. The listener observed:

```text
tool_call_id       t1
tool_name          echo
is_error           true
details            {progress: 1}
terminate          true
added_tool_names   [new]
```

The normalized identity and `is_error` subfield do not exist in Pi's partial-result value or Rust's `AgentToolResult`. The candidate spec nevertheless calls Python `ToolResult` “the SAME shape” as Pi/Rust, then normatively specifies identity normalization. Those statements cannot both be true.

The canonical change is not sufficient to detect this divergence:

- schema merely changes `partial` to unrestricted `type: object`;
- fixture decoding recognizes only `{text: ...}`;
- observation serializes only joined text content;
- details, usage, added-tool names, terminate presence/value, and the Python-only identity/error fields are not observed.

The shared change also breaks an already-certified Rust gate. Fresh `cargo test --workspace --all-features` fails in `all_layer_06_scenarios_drive_the_real_rust_tool_executor`: the Rust adapter still parses `emits_updates[]` with `Value::as_str().unwrap()`, while PASS 10 supplies an object. This is adapter/evidence work, not a Rust production parity defect, but it disproves the manifest/assurance claim that Rust is “unaffected” and leaves Layer-06 cross-language evidence non-green.

### Narrow remediation required

1. Define a language-neutral partial result shape equal to Pi/Rust `AgentToolResult`, distinct from Python's finalized execution `ToolResult` unless that finalized type is first made semantically exact.
2. Do not expose nested call identity or `is_error` in `partial_result`; retain identity only at the enclosing event.
3. Preserve observable absent/concrete distinctions for optional usage, added-tool names, and terminate according to the shared cross-language rules.
4. Expand the canonical schema/fixture/observation to represent and assert the structured fields, not only a text shorthand.
5. Complete the declared post-certification Layer-06 delta: update the Rust canonical adapter through the real existing `AgentToolResult` seam and rerun its full gates. Do not change faithful Rust production semantics.
6. Correct spec/manifest/assurance claims that the Python `ToolResult` shape is identical and that Rust is unaffected.

## Full Layer-08 regression audit

The PASS-10 production diff is confined to the update payload and does not alter the run state machine. The complete source/spec/canonical recheck found no new witness against the prior final review's passing conclusions:

- prompt typed/sequence/text/images, continuation branches, exact guards, and invocation-local `agent_end.messages`: PASS;
- context/model/thinking snapshot and whole-context replacement, run-local dynamic tool extension, and no later-run leakage: PASS;
- first prompt lifecycle before steering, single pre-drain suppression, tool/steering/follow-up continuation, terminate semantics: PASS;
- represented error/aborted immediate termination and failure recovery trace/catch boundary: PASS;
- complete streamed assistant partials and message lifecycle ordering: PASS;
- state reduction before listener dispatch, listener order/failure behavior, and outer status settlement: PASS;
- no max-step or boundary-stop divergence: PASS;
- AG-007 remains correctly deferred to Layer 09: PASS.

AG-001..AG-010 and AG-021 retain coherent adopted/deferred dispositions except that AG-009/TOOL-019 evidence is blocked by L08-R011. No applicable row counts an unfilled placeholder as satisfying evidence. Manifest inventory is 76 rows / 76 unique IDs.

## Runner and contract quality

The Layer-08 runner otherwise remains thin and drives the real AgentLoop, inbox, session, provider adapter, and tool executor. It does not simulate run/turn ordering. For update partials specifically, however, its text-only decoder/observer is too lossy to prove the claimed structured rule and permits Python/Rust observable disagreement.

Two reasonable implementations following the written artifacts can differ on nested identity, error state, and optional-field presence. Rust cannot implement both its already-certified Pi-faithful type and the Python-specific normalized `ToolResult` rule. Contract approval therefore remains blocked.

## Fresh gates

```text
Python pytest
    1042 passed, 19 xfailed
    configured coverage 100.00%

ruff
    PASS

mypy
    PASS, 57 source files

manifest
    76 rows, 76 unique IDs

Rust cargo test --workspace --all-features
    FAIL
    all_layer_06_scenarios_drive_the_real_rust_tool_executor panics while parsing object-shaped emits_updates
```

Green Python gates do not override the Pi/shared/Rust evidence defect.

## Findings

```text
PI_PARITY_DEFECT
    L08-R011 remains open for Python's observable update-partial shape

CONTRACT_ASSURANCE_DEFECT
    L08-R011 remains open for contradictory shape rules, lossy canonical evidence,
    and an incomplete post-certification Layer-06 delta

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

L08-R012 and L08-R013 are closed. L08-R002/L08-R004 remain provisionally closed. Remediate only the remaining L08-R011 structured-shape and cross-language evidence delta, then provide new exact candidate SHAs for review.
