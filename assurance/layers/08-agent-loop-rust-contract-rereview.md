# Layer 08 — Independent Rust Contract Re-review (PASS 3)

**Verdict:** `REJECTED`  
**Mode:** independent Rust contract review only; no Rust implementation  
**Reviewed code candidate:** `d8caf5c1f299063111a5b47fec3df45f9f9d50fc` (PR `EGAILab/minion-agent#13`)  
**Reviewed docs candidate:** `580fb279ec8703528632b9861bbc80b13d0f5171` (PR `EGAILab/minion-agent-docs#3`)  
**Prior rejected review:** `88a6aa6c1c1994026001c60045d4c55c00331a52` (docs PR `#4`)  
**Pinned Pi:** `b7bb00b936dbe21b8e160b3e89efdec361846699`

The verdict applies only to the exact two PASS-3 candidate SHAs above. At review start issue
`EGAILab/minion-agent#12` recorded those SHAs, `STATUS = RUST_CONTRACT_REVIEW`, and
`NEXT_OWNER = Codex`. Both candidate PRs were open, Ready for Review, clean, and unmerged. The
historical PASS-2 review PR remained open and unchanged.

## Independent authority audit

The review used the required order: pinned Pi, manifest, normative spec, canonical conformance,
certified Rust architecture, assurance, then Python as secondary evidence.

Pinned Pi source re-read:

- `packages/agent/src/agent.ts`: `prompt`, `continue`, `createContextSnapshot`,
  `createLoopConfig`, `runWithLifecycle`, `handleRunFailure`, `finishRun`, `processEvents`;
- `packages/agent/src/agent-loop.ts`: `runAgentLoop`, `runAgentLoopContinue`, `runLoop`,
  `streamAssistantResponse`, represented failure, tool continuation, queue polling, and
  `prepareNextTurn`;
- `packages/agent/src/types.ts`: `AgentContext`, `AgentLoopTurnUpdate`, callback context and event
  types;
- pinned tests for thrown provider-start failure and whole-context `prepareNextTurn` replacement.

The Pi behavior relevant to the active findings is determinate. There is no active
`PI_BEHAVIOR_UNCERTAIN`.

## L08-R001..L08-R008 closure ledger

| Finding | Pi reproduction | PASS-3 change and evidence | Current result |
|---|---|---|---|
| L08-R001 | Run start shallow-copies `systemPrompt`, `messages`, and `tools`; model/thinking are run-local config. `prepareNextTurn` may replace whole context/model/thinking. | `RunContext` now owns the three context components, `RunConfigUpdate.context` is whole replacement, requests use run-local state, and tests distinguish external mutation and later-run leakage. Named `added_tool_names` extend only the current run snapshot through targeted registry resolution. | **CLOSED** |
| L08-R002 | `runWithLifecycle` catches executor failures; recovery calls `processEvents` for start/end/turn/end, so recovery listeners are awaited and may themselves fail; `finishRun` still runs. No synthetic `turn_start`; failure `agent_end.messages` is `[failure]`. | Broad `_run_inner` catch and failure payload/order were corrected, but recovery is raw `SessionLog.append`, not the production listener-bearing event seam, and no recovery-listener-failure evidence exists. The normative spec still describes the rejected narrow boundary and synthetic turn. | **STILL OPEN** |
| L08-R003 | Every assistant event carries the complete partial; lifecycle is `message_start -> message_update* -> message_end`. | Production now consumes `chunk.partial`; text/thinking/tool-call language tests exist; six canonical traces were corrected. | **CLOSED in implementation/evidence**, but the normative spec remains contradictory under L08-R004. |
| L08-R004 | Current normative contract must state one coherent Pi rule. | Manifest AG-004 was rewritten, but docs PR #3 changed only the assurance artifact. `spec/agent.md` still says text-only streaming, a synthetic matched failure turn, and a narrow failure boundary. | **STILL OPEN** |
| L08-R005 | Pinned Pi has no `max_steps` stop. | Check moved after prepare/stop/steering and AG-020 labels it an intentional divergence. It still prevents a next request on the ordinary `prompt`/`continue` semantic path where Pi would continue. No governance approval authorizes that observable divergence. | **STILL OPEN** |
| L08-R006 | Fresh prompt order is `agent_start`, `turn_start`, prompt message lifecycle, then initial steering poll. | PASS 3 moved the claim after `turn_start` only. `_run_inner` still claims steering and dispatches `_pre_step` before `_run_step` logs the prompt messages. Its test observes only `TURN_START`, not prompt lifecycle. | **STILL OPEN** |
| L08-R007 | Pi supports typed messages and `prompt(text, images?)`, normalizing text first and images in order. | Both forms now exist with typed-path preservation and focused tests. | **CLOSED** |
| L08-R008 | Represented assistant `error`/`aborted` emits its `turn_end`, then terminates without prepare/stop/queue polling. | Explicit terminal step outcome and discriminating queued/listener tests cover both reasons. | **CLOSED** |

## Run context and dynamically added tools

The corrected run snapshot is language-neutral and implementable in Rust: it is a shallow
run-local copy, not a live Session or ToolRegistry read. `prepareNextTurn` can replace the complete
context and replacements do not mutate Agent state or leak into later runs.

The `added_tool_names` interaction is also coherent with the already-certified Minion tool
contract. A result may name a tool registered by that execution; Layer 08 resolves only those
specific names and appends the resolved definitions to the run-local context. Unrelated external
registrations remain excluded. The canonical `a-tool-introduced-by-a-tool-is-offered-next`
scenario observes `[load]` followed by `[load, deploy]`. This is an allowed run-owned context
extension, not an uncontrolled live-registry reread.

## Failure boundary and recovery trace

PASS 3 correctly removed its synthetic failure `turn_start`, carries the failure message directly
on `turn_end`, and overrides `agent_end.messages` with the failure-only list. It also catches
ordinary failures across `_run_inner`, while preserving the certified eager `UnknownModelError`
boundary.

It does not, however, reproduce Pi's recovery-listener behavior. Pi's `handleRunFailure` invokes
`processEvents` four times; each call reduces state and awaits every Agent event listener. A
listener failure can interrupt the remaining recovery events, while `finally` still calls
`finishRun`. Minion's `_settle_run_failure` appends raw Session events directly. `project()` later
reconstructs event values but cannot dispatch or fail a live recovery listener. The manifest cites
pre-step/prepare/stop failures only and leaves `high-level-callback-failure-settlement` as a
placeholder. Two independent Rust implementations could therefore choose different recovery
listener semantics from the written contract.

## Streaming lifecycle

The Python implementation now assigns every real chunk's complete `partial` to
`streaming_message`, including thinking and tool-call construction, and clears it on finalization.
The six changed canonical scenarios now order start before update. The runner observes production
projection and does not reorder these traces.

The normative spec is nevertheless still the PASS-2 text. It explicitly calls
`streaming_message` text-only and falsely says the certified stream exposes only raw deltas. That
is a current normative contradiction, not harmless historical prose.

## Initial steering order

Pinned Pi emits prompt message start/end before entering `runLoop`; `runLoop` then performs the
initial steering poll. PASS 3 appends `TURN_START`, immediately calls `_claim_step_input`, and only
later `_run_step` appends every message in `entering + claimed steering`. Thus a pre-step listener
at claim time sees a turn start but not the initial prompt lifecycle, and prompt plus steering are
coalesced into one pre-step decision. The new test proves only the weaker `turn_start` condition.

## `max_steps`

AG-020's claim of parity neutrality is internally false. With a tool result requiring another
turn, `steps >= max_steps` returns `agent_end(reason=max_steps)` after the current turn's hooks and
steering poll. Pinned Pi starts the next provider request. The existing tests intentionally prove
that the cap wins even when a continuation listener says continue. Moving the check later fixed
the old intra-turn ordering defect but did not remove the cross-run observable difference.

The manifest itself uses `disposition: intentional divergence`; the prose simultaneously says no
observable divergence exists. Merely adding that row is not governance approval for changing the
Pi-equivalent `prompt`/`continue` path. This remains a blocking `PI_PARITY_DEFECT` unless the cap is
removed from that seam or the owner explicitly approves and records the observable divergence.

## Prompt, continuation, terminate, and terminal assistants

- Typed prompt and text/image convenience normalization now match Pi.
- Plain continuation and assistant-last steering/follow-up pre-drain retain invocation-local
  `agent_end.messages` semantics and the one-shot steering skip.
- `terminate` remains narrow: it suppresses tool-driven automatic continuation, not
  prepare/stop/steering/follow-up.
- Represented `error` and `aborted` now terminate immediately and preserve the normal invocation
  accumulator, distinct from synthesized failure recovery.
- `error_message` persists after a failed run and clears at the next run start/reset; status and
  streaming/pending fields settle at the documented boundaries.

## Extra regression surfaces

### `AgentLoop.cancel()`

PASS 3 restored the pre-existing local boundary-stop latch and did not add provider/tool/hook
signal propagation; active cancellation remains Layer 09. However, the current Layer-08 manifest
has no row for this public, observable Minion-only boundary stop, and the normative spec does not
define its relationship to AG-007. The implementation comment incorrectly points to AG-019, which
is Layer-07 wake, not cancel. This is a new contract-assurance finding (`L08-R009`): Rust cannot
know from the approved contract whether Layer 08 must implement this latch or leave all public
cancellation to Layer 09.

### Dynamically added tools

The regression is repaired coherently. The current run snapshot is extended only for names
reported by that run's own tool results, using the real registry to resolve those names. The
canonical observes the provider-visible schemas. No general live ToolRegistry reread defeats the
snapshot.

## Manifest ledger

| Row | Result |
|---|---|
| AG-001 | PASS — initial run/turn/prompt event vocabulary is correct. |
| AG-002 | **FAIL** — claims prompt lifecycle precedes initial steering, but production and its test prove only `turn_start` precedes it. |
| AG-003 | PASS — continuation accumulator and pre-drain branches are coherent. |
| AG-004 | PASS as manifest text, but contradicted by normative `spec/agent.md` (`L08-R004`). |
| AG-005 | PASS — follow-up is polled only when otherwise stopping and remains in the same run. |
| AG-006 | PASS — exact public errors and both prompt forms are represented. |
| AG-007 | PASS — active signal propagation remains genuine Layer-09 deferred parity. |
| AG-008 | PASS as manifest/implementation; contradicted by normative spec's text-only rule. |
| AG-009 | **FAIL** — recovery listener interruption is absent/unspecified and the normative spec remains stale. |
| AG-010 | PASS — normal invocation-local and failure-only override cases are distinguished. |
| AG-020 | **FAIL** — observable Pi-path divergence is mislabeled as parity-neutral and lacks owner approval. |
| AG-021 | PASS — represented error/aborted terminal handling is discriminating. |

The manifest contains 77 rows and 77 unique IDs. Nineteen agent scenarios remain explicit
`TO_BE_FILLED_FROM_PINNED_PI_BEHAVIOR` placeholders and were not counted as semantic evidence.

## Canonical and runner quality

There are 79 agent YAML files: 60 executable and 19 placeholders. The six modified streaming
traces now use the correct message lifecycle. The runner invokes the real AgentLoop/Inbox/tool
seams and does not implement FIFO, scheduling, run snapshots, dynamic-tool visibility, or event
sorting itself. Canonical evidence remains incomplete for listener-driven initial ordering and
recovery-listener failure; Python-only evidence is appropriate in principle, but the existing
tests do not prove those exact rules.

## Contract-quality answers

```text
runner simulates production semantics                         NO
projection forces a non-Pi failure event order                NO after PASS 3
Python workaround caused by incomplete contract               YES -- recovery is projected, not listener-dispatched
run-local snapshot/mutation rule clean                         YES
max_steps alters Pi-equivalent behavior                        YES
Layer-09 active propagation leaked into Layer 08               NO
Rust can implement without consulting Python mechanics         NO, because cancel/recovery/spec disagree
two implementations can conform yet differ observably          YES
```

## Fresh evidence

Against the exact code candidate:

```text
uv run pytest -q
    PASS: 1021 passed, 19 xfailed (1040 collected), 100.00% coverage

uv run pytest -q -o addopts='' tests/conformance/test_schema_validation.py
    PASS: 185

uv run pytest -q -o addopts='' tests/conformance/test_agent_conformance.py
    PASS: 35 passed, 19 xfailed

manifest structural audit
    77 rows / 77 unique IDs
```

Green implementation tests do not cure the normative contradictions or observable Pi mismatch.

## Findings

```text
PI_PARITY_DEFECT
    L08-R005  max_steps still truncates the Pi-equivalent run path without approved divergence
    L08-R006  initial steering is still claimed before initial prompt lifecycle

CONTRACT_ASSURANCE_DEFECT
    L08-R002  recovery-listener failure/interruption remains absent and unspecified
    L08-R004  normative spec was not remediated and contradicts manifest/implementation
    L08-R009  public local cancel latch has no coherent Layer-08/Layer-09 manifest disposition

PI_BEHAVIOR_UNCERTAIN
    none

PARITY_CONSTRAINED_RISK
    none beyond the blocking findings above

PARITY_NEUTRAL_HARDENING
    none material
```

## Verdict and required remediation

```text
shared Layer-08 contract
    REJECTED for the exact reviewed candidates

Python Layer 08
    REOPENED / IN REMEDIATION

Rust Layer 08
    BLOCKED / NOT_IMPLEMENTED

Layer 08 cross-language
    NOT CLOSED

Layer 09
    NOT STARTED
```

Narrow remediation required:

1. update the normative spec to the actual full-context/full-partial/failure contract;
2. make initial prompt lifecycle complete before the initial steering claim and prove it at the
   listener/state boundary;
3. remove `max_steps` from the Pi-equivalent run seam, constrain it to a genuinely host-only seam,
   or obtain explicit governance approval for the observable divergence;
4. specify and implement Pi's recovery-listener interruption/settlement behavior, with
   discriminating evidence;
5. formally disposition the pre-existing local `cancel()` boundary stop separately from Layer-09
   active signal propagation.

Any candidate SHA change requires a complete independent re-review. Rust Layer 08 must not be
implemented from these rejected candidates.
