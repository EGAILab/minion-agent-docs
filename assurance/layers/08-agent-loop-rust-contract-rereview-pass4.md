# Layer 08 — Independent Rust Contract Re-review (PASS 4)

**Verdict:** `REJECTED`  
**Review mode:** contract review only; no Rust implementation  
**Reviewed code candidate:** `0161b0424e1b95fe2cea9590be8d6de8260ae69c` (PR `EGAILab/minion-agent#13`)  
**Reviewed docs candidate:** `b27d3cef56938b97f59f6066b24671f75b97963d` (PR `EGAILab/minion-agent-docs#3`)  
**Pinned Pi:** `b7bb00b936dbe21b8e160b3e89efdec361846699`

Historical evidence preserved unchanged:

- PASS-2 rejection: docs PR `#4`, commit `88a6aa6c1c1994026001c60045d4c55c00331a52`;
- PASS-3 rejection: docs PR `#5`, commit `a64b78ad2507b142ca7cda911b8968aa61af6a20`.

At review start issue `EGAILab/minion-agent#12` recorded the exact PASS-4 pair above,
`STATUS = RUST_CONTRACT_REVIEW`, and `NEXT_OWNER = Codex`. Both candidate PRs were open, Ready for
Review, clean, and unmerged. This verdict applies only to those exact SHAs.

## Independent Pi audit

The review used the required authority order: pinned Pi, normative spec, manifest, canonical
conformance, certified Rust architecture, assurance, then Python as secondary evidence.

Pinned Pi source re-read:

- `packages/agent/src/agent.ts`: `prompt`, `continue`, `createContextSnapshot`,
  `createLoopConfig`, `runWithLifecycle`, `handleRunFailure`, `finishRun`, `processEvents`, and
  listener subscription;
- `packages/agent/src/agent-loop.ts`: `runAgentLoop`, `runAgentLoopContinue`, `runLoop`,
  `streamAssistantResponse`, tool execution, queue polling, terminal assistants, and turn update;
- `packages/agent/src/types.ts`: `AgentContext`, `AgentLoopTurnUpdate`, callback contexts,
  `AgentState`, and the complete `AgentEvent` union;
- pinned tests for provider-start failure and whole-context `prepareNextTurn` replacement.

Pi behavior is determinate. There is no active `PI_BEHAVIOR_UNCERTAIN`.

## Prior blocker ledger

| Finding | Independent PASS-4 result | Verdict |
|---|---|---|
| L08-R002 — listener-bearing lifecycle/failure recovery | Recovery events now use a live serial seam, but ordinary streamed assistant start/update/end and tool execution events do not. The seam also does not reproduce Pi's per-event state reduction timing. | **STILL OPEN** |
| L08-R004 — normative spec coherence | The Layer-08 body was rewritten, but it is internally contradictory about “every lifecycle event,” and surviving Layer-07 present-tense prose still says Layer 08 is unimplemented/not wired. | **STILL OPEN** |
| L08-R005 — `max_steps` | Production cap and schema field are removed; a 21-turn language test discriminates the old default. The replacement canonical has only three tool turns and would pass the old default-16 implementation, so its stated canonical proof is not discriminating. | **PARTIALLY RESOLVED — BLOCKING EVIDENCE GAP** |
| L08-R006 — initial prompt before steering | Production now admits and live-dispatches prompt lifecycle before claiming steering; both batches reach the same first request and continuation pre-drain still suppresses one poll. | **CLOSED** |
| L08-R009 — local cancel/boundary-stop disposition | Rename and row clarify mechanics, but the public method still terminates a normal Pi-equivalent run where Pi continues. No owner governance approval exists. Its own follow-up behavior also contradicts the row. | **STILL OPEN** |

## L08-R002 — lifecycle authority remains incomplete

Pinned Pi has one public listener seam. Every `AgentEvent` emitted by the low-level loop reaches
`Agent.processEvents`, including:

```text
agent_start
turn_start
message_start
message_update
message_end
tool_execution_start
tool_execution_update where applicable
tool_execution_end
turn_end
agent_end
```

For each event Pi first reduces `AgentState`, then awaits listeners serially in registration order.
A listener failure stops later listeners and propagates. `handleRunFailure` emits its recovery
events through that same method; a recovery-listener failure interrupts the remaining recovery
sequence, while `finally` still runs `finishRun`.

PASS 4 adds `AGENT_LIFECYCLE_EVENT` and correctly routes run/turn boundaries, admitted-message
events, and the four recovery events through it. The recovery interruption tests are useful and
the durable log is appended before dispatch.

The seam is nevertheless not Pi-complete:

1. The assistant reply's live `message_start`, every `message_update`, and `message_end` are
   explicitly excluded. They remain log-plus-offline-projection only. Pi listeners observe and may
   interrupt all three.
2. Layer-06 tool execution events update pending state through separate tool EventBus listeners but
   are never delivered to the unified Agent lifecycle subscriber. Pi's same Agent listener sees
   those events in the same event union.
3. “Log append equals Pi's state reduction” is false for message events. `_admit_messages` appends
   one finalized Session message before dispatching both `MessageStart` and `MessageEnd`; therefore
   a start listener already sees the message in `AgentInstance.messages`, while Pi adds it only at
   `message_end`. Minion also does not set `streaming_message` for that `MessageStart` before the
   listener, while Pi does.
4. Recovery has the same timing mismatch. `_settle_run_failure` appends the finalized assistant
   before failure `MessageStart`, does not set `streaming_message` for that start, and sets
   `error_message` only after the failure `TurnEnd` listener returns. Pi performs each corresponding
   state mutation before that event's listeners.

The synchronous Python `collect(on_chunk=...)` callback is an implementation constraint, not a
Pi-visible contract limitation. It does not justify excluding observable async listener behavior.
Rust's certified LLM seam is an async `Stream` and can implement the Pi rule without lower-layer
redesign; Python can restructure its Layer-08 consumption without changing Layer 02/04 semantics.

**Classification:** `PI_PARITY_DEFECT`.

## L08-R004 — the normative spec is still contradictory

The new Layer-08 body correctly states full run context, full partial fidelity, turn ordering,
terminal assistants, and no turn cap. It then says the live seam delivers the complete Pi event
union through one path, but immediately carves streamed assistant lifecycle out of that path. The
manifest AG-009 repeats the same adopted-but-incomplete rule.

The document's opening and Layer-07 authority map also retain present-tense claims that Layer 08 is
“not yet certified,” AG-001..010 are “unimplemented,” and `streaming_message`,
`pending_tool_calls`, and `error_message` are “not yet wired.” Those statements are not clearly
limited to a historical Layer-07 candidate; they conflict with the current Layer-08 contract later
in the same normative document.

**Classification:** `CONTRACT_ASSURANCE_DEFECT`.

## L08-R005 — cap removed, canonical proof incomplete

Source and structural search confirm:

- `AgentDefinition.max_steps` is removed;
- `_run_inner` has no hidden turn counter/cap;
- the canonical schema and runner no longer accept/inject `max_steps`;
- AG-020 is removed;
- the language test executes 20 tool turns plus a final stopping turn, exceeding the old default
  of 16.

The new `no-turn-count-cap-on-pi-equivalent-run` canonical contains only three tool turns. Against
the PASS-3 implementation with its default cap of 16 and with no scenario-supplied cap, it would
pass unchanged. Its description claims it exceeds an “old default-2” fixture, but 2 was an explicit
scenario override, not the old implementation default. The canonical therefore does not prove
what it claims. The production repair is real; the requested language-neutral evidence is not
discriminating.

**Classification:** `CONTRACT_ASSURANCE_DEFECT` (evidence gap; no remaining production cap found).

## L08-R006 — closed

The first turn now performs:

```text
agent_start
turn_start
initial pre-step decision
prompt message_start/message_end admission
initial steering claim
steering pre-step decision
steering message_start/message_end admission
one provider request containing both batches
```

The queue claim occurs after prompt dispatch completes. Prompt and steering are admitted once,
share one turn/request, and `skip_initial_steering_poll` still prevents duplicate continuation
drain. The listener-driven test observes the actual claim boundary rather than only offline
projection.

**Classification:** closed; no active finding.

## L08-R009 / AG-022 — rename is not governance approval

`request_boundary_stop()` is public on `AgentLoop`. A tool or external host can call it during an
ordinary `prompt()`/`continue()` run, after which Minion may return
`agent_end(reason="boundary_stop")` instead of making the next provider request pinned Pi would
make. This is an observable extension on the same execution seam, not merely private pump
bookkeeping. Renaming the old `cancel()` method accurately separates it from active Layer-09 abort
propagation, but does not make its behavior parity-neutral.

AG-022 declares `intentional divergence`; no owner/governance approval for this new observable
divergence is recorded. The workflow requires owner escalation rather than reviewer approval.

The implementation also fails AG-022's own stated boundary-stop rule for follow-up continuation.
The latch is checked only while the inner loop has tool- or steering-driven work. If the current
turn would otherwise stop, `_run_inner` breaks before checking the latch, claims follow-up, and
starts another turn in the same run despite the pending boundary-stop request. Existing tests cover
only a tool-driven next request, so the cited evidence does not expose this branch.

No provider, stream, tool, hook, or transport signal propagation was introduced; AG-007 remains
correctly deferred to Layer 09.

**Classifications:** `PI_PARITY_DEFECT` for the unapproved public divergence; new `L08-R010`
`CONTRACT_ASSURANCE_DEFECT` for AG-022's rule/evidence/implementation contradiction.

## Closed-finding regression audit

### L08-R001 — PASS

Run start shallow-snapshots system prompt/messages/tools and model/thinking. Requests use run-local
state. `prepareNextTurn` replaces whole context and independent model/thinking fields without
persistent leakage. Only names reported by the current run's tool results extend run-local tools;
unrelated registry mutations do not leak in.

### L08-R003 — PASS for state fidelity and projected order

Every represented stream chunk's complete `partial` drives `streaming_message`, including text,
thinking, and tool-call construction. Projected lifecycle remains
`message_start -> message_update* -> message_end`. Live listener fidelity remains part of active
L08-R002, not a regression in partial content.

### L08-R007 — PASS

Typed single/sequence `Message` input remains intact. Text plus optional images normalizes to one
timestamped user message with text first and images in source order.

### L08-R008 — PASS

Represented `error` and `aborted` append/dispatch their turn end and return before
prepare/stop/steering/follow-up. Tests queue steering at the live turn-end boundary, so the branch
is discriminating.

## Whole-state-machine audit

| Path | Result |
|---|---|
| Fresh typed prompt / sequence | Control flow and invocation-local accumulation match Pi; live assistant lifecycle remains incomplete under R002. |
| Text / text+images prompt | PASS. |
| Plain continuation | PASS; full context, empty invocation seed. |
| Assistant-last continuation | PASS for steering pre-drain, follow-up pre-drain, rejection, and no-double-drain. |
| First-turn steering | PASS after R006 repair. |
| Tool continuation | PASS except unified Agent listener does not receive tool events. |
| Steering/follow-up continuation | Ordering PASS; boundary-stop follow-up interaction FAILS AG-022. |
| prepareNextTurn | Whole context/model/thinking replacement PASS. |
| Dynamic tools | Targeted run-local extension PASS. |
| terminate | Narrow continuation suppression PASS. |
| Represented error/aborted | Immediate terminal branch PASS. |
| Unexpected run failure | Visible recovery trace and failure-only end payload PASS; listener state timing remains wrong. |
| Recovery listener failure | Sequence interruption and final idle settlement PASS for covered events; reduction timing remains wrong. |
| Multiple independent runs | Run-local messages/config PASS. |
| request_boundary_stop | No Layer-09 signal leak; unapproved divergence and follow-up branch defect remain. |
| Runtime fields | Final values/timing broadly PASS; live per-event reduction visibility fails R002. |
| agent_end.messages | Normal and failure-specific sets PASS. |

## Manifest ledger

| Row | Verdict |
|---|---|
| AG-001 | PASS for event order; stale Python pointer `_run_once` remains non-normative evidence hygiene. |
| AG-002 | PASS. |
| AG-003 | PASS. |
| AG-004 | PASS as a turn rule; normative-document contradictions remain R004. |
| AG-005 | PASS. |
| AG-006 | PASS. |
| AG-007 | PASS — active abort propagation is genuinely Layer-09-owned. |
| AG-008 | PASS for field transitions/partial content; live listener timing remains R002. |
| AG-009 | **FAIL** — disposition `adopted` despite explicitly excluding Pi lifecycle events and state timing. |
| AG-010 | PASS. |
| AG-020 | Removed; no live manifest references found. |
| AG-021 | PASS. |
| AG-022 | **FAIL** — unapproved observable divergence and follow-up behavior contradicts the row. |

The manifest contains 77 rows and 77 unique IDs. No placeholder is counted as satisfying
Layer-08 evidence.

## Canonical / runner audit

There are 79 agent scenario files: 60 executable and 19 explicit
`TO_BE_FILLED_FROM_PINNED_PI_BEHAVIOR` placeholders. The runner invokes the real AgentLoop, Inbox,
Session, LLM, and tool seams; it does not simulate lifecycle, queue behavior, context replacement,
or tool visibility. The no-cap replacement scenario is language-neutral but non-discriminating as
described above. Listener-driven rules appropriately require language tests, but current lifecycle
tests omit Pi's full ordinary event and state-reduction surface.

## Rust implementability and lower-layer impact

Rust can implement complete Pi listener semantics idiomatically without copying Python mechanics:
its certified LLM surface exposes an async `Stream<Item = StreamChunk>`, complete partials, typed
Agent state, EventBus serial dispatch, Session, and ToolRegistry. Layer 08 can iterate the stream,
reduce state, durably log, and await the one Agent listener seam per event. No certified lower-layer
semantic reopen is required.

The current written contract is not independently implementable without choosing between the
spec's universal-seam claim and its assistant-event exclusion, or guessing AG-022 behavior and
governance.

## Contract-quality answers

```text
AGENT_LIFECYCLE_EVENT duplicates/bypasses lifecycle authority?       YES — split live/offline and separate tool seams
durable event recorded before a listener failure?                     YES, but message-state reduction is not Pi-equivalent
failure and ordinary progress use exactly the same seam?              NO
first-turn admission uses Pi order without duplication?               YES
request_boundary_stop outside Pi parity?                              NO — it changes the same public run path
Rust implementable without Python control-flow guesses?               NO
Python/Rust could satisfy prose yet differ observably?                 YES
canonical runner simulates production semantics?                      NO
```

## Fresh gates

Against code candidate `0161b0424e1b95fe2cea9590be8d6de8260ae69c`:

```text
uv run pytest -q
    PASS: 1027 passed, 19 xfailed (1046 collected), 100.00% coverage

uv run ruff check .
    PASS

uv run mypy src
    PASS: 57 source files

schema validation
    PASS: 185

agent canonical
    PASS: 35 passed, 19 xfailed placeholders

manifest structural audit
    PASS: 77 rows / 77 unique IDs
```

An intentionally broader `mypy src tests` command is not the repository gate and reports existing
test-annotation issues; the established `mypy src` gate is clean. Green gates do not override the
semantic blockers.

## Findings

```text
PI_PARITY_DEFECT
    L08-R002  unified live lifecycle and per-event state reduction remain incomplete
    L08-R009  public boundary stop is an unapproved observable divergence

CONTRACT_ASSURANCE_DEFECT
    L08-R004  normative spec remains internally/current-state contradictory
    L08-R005  replacement no-cap canonical is not discriminating against the removed default cap
    L08-R010  AG-022 rule/evidence contradict follow-up-driven production behavior

PI_BEHAVIOR_UNCERTAIN
    none

PARITY_CONSTRAINED_RISK
    none beyond the blocking divergence above

PARITY_NEUTRAL_HARDENING
    stale comments/pointers mentioning removed `max_steps` and `_run_once`
```

## Verdict

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

1. make every Pi Agent event, including streamed assistant and tool execution events, use one live
   listener seam with Pi-equivalent reduce-before-listener state visibility;
2. remove the contradictory assistant-event carve-out and stale present-tense Layer-07 statements
   from the normative spec/manifest;
3. make the no-cap canonical exceed the former default cap so it discriminates the removed
   implementation;
4. remove `request_boundary_stop()` from the Pi-equivalent public run seam or obtain explicit owner
   approval for the intentional observable divergence;
5. if retained by governance, define and test boundary stop across tool-, steering-, and
   follow-up-driven continuation consistently.

Any updated candidate SHA requires another complete independent re-review. Rust Layer 08 must not
be implemented from this rejected pair.
