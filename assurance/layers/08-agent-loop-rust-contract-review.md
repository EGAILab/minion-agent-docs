# Layer 08 — Independent Rust Contract Review

**Verdict:** `REJECTED`  
**Review mode:** contract review only; no Rust implementation  
**Reviewed code candidate:** `45a7e039233e262eabb7821c1aeb713024ac3bda` (PR `EGAILab/minion-agent#13`)  
**Reviewed docs candidate:** `fe854a6f583359512cfb538a628ba5e3a6811a47` (PR `EGAILab/minion-agent-docs#3`)  
**Pinned Pi:** `b7bb00b936dbe21b8e160b3e89efdec361846699`

This approval decision applies only to the two exact candidate SHAs above. Both PRs were open,
Ready for Review, unmerged, and their remote heads matched coordination issue `#12` when the review
started. The issue recorded `STATUS = RUST_CONTRACT_REVIEW` and `NEXT_OWNER = Codex`.

## Authority and source audit

The review used the required order: pinned Pi, frozen/normative design and spec, parity manifest,
canonical conformance, certified Rust architecture, assurance, then Python only as secondary
evidence.

Pinned Pi files and symbols inspected:

- `packages/agent/src/types.ts`: `AgentContext`, `AgentLoopTurnUpdate`, `AgentLoopConfig`,
  `AgentState`, `AgentEvent`;
- `packages/agent/src/agent-loop.ts`: `runAgentLoop`, `runAgentLoopContinue`, `runLoop`,
  `streamAssistantResponse`, tool continuation and terminate handling;
- `packages/agent/src/agent.ts`: `prompt`, `continue`, `createContextSnapshot`, `createLoopConfig`,
  `runWithLifecycle`, `handleRunFailure`, `finishRun`, `processEvents`;
- pinned Pi tests for thrown provider-start failure and `prepareNextTurn` context replacement.

The source behavior is determinate. There is no active `PI_BEHAVIOR_UNCERTAIN`.

## AG-001..AG-010 review ledger

| Row | Pi behavior and shared rule | Evidence / implementation result | Verdict |
|---|---|---|---|
| AG-001 | `agent_start -> turn_start -> initial prompt message lifecycle` | The cited legacy scenarios exercise the real driver and no placeholder is counted. The narrow initial-prompt rule is correct. | PASS |
| AG-002 | Pi polls steering after the already-emitted first `turn_start` | Python claims the queue before `_run_step` appends `TURN_START`. The public projected trace hides the claim event, so the cited tests do not prove the required ordering. | FAIL (`L08-R006`) |
| AG-003 | Plain continuation seeds invocation-local output empty; assistant-last pre-drains use the prompt-style seeded path | Source mapping is correct. The plain continuation case is explicitly Python-only and the canonical scenario accurately limits its claim to the follow-up pre-drain case. | PASS |
| AG-004 | One turn per provider response; after `turn_end`: `prepareNextTurn`, stop policy, steering | The row still says `prepareNextTurn` is not implemented, contradicting the candidate spec, implementation, assurance, and its own `adopted` disposition. It also omits Pi's full context replacement semantics. | FAIL (`L08-R001`, `L08-R004`) |
| AG-005 | Follow-up is polled only when the inner loop would otherwise stop and continues the same run | Rule and finite evidence are consistent with Pi. `run_until_idle` remains a disclosed Minion pump. | PASS |
| AG-006 | Public `prompt`/`continue` caller rules and exact errors | Active/continue branching is mostly correct, but the public Pi `prompt(text, images?)` convenience overload is absent from contract and implementation while the row claims exact reproduction. | FAIL (`L08-R007`) |
| AG-007 | Active abort-signal propagation and listener settlement | Correctly named as Layer 09 deferred parity; placeholders are not counted as Layer-08 evidence. | PASS |
| AG-008 | Runtime-field transition timing and full partial `streamingMessage` | Candidate deliberately exposes text-only partial state although both certified Python and Rust stream chunks already carry full `partial` messages. | FAIL (`L08-R003`) |
| AG-009 | High-level `handleRunFailure` | Candidate changes event order, narrows the catch boundary, and changes failure `agent_end.messages`. | FAIL (`L08-R002`) |
| AG-010 | Invocation-local `agent_end.messages` | Normal-run accumulation is correct, but Pi's failure fallback emits `[failureMessage]`; candidate projection includes all earlier messages in the run. | FAIL (`L08-R002`) |

`adopted` is therefore not accurate for AG-004, AG-006, AG-008, or AG-009 at these SHAs. AG-007's
Layer-09 deferral is valid. The nineteen `TO_BE_FILLED_FROM_PINNED_PI_BEHAVIOR` agent fixtures are
xfail placeholders and were not treated as evidence.

## Blocking findings

### L08-R001 — incomplete run context snapshot and `prepareNextTurn` update

**Classification:** `PI_PARITY_DEFECT`

Pinned Pi's `createContextSnapshot()` copies:

```text
systemPrompt
messages (top-level array copy)
tools (top-level array copy)
```

`createLoopConfig()` separately snapshots `model` and `thinkingLevel`. During the run, the low-level
loop uses its local `currentContext` and config; it does not re-read Agent state each request.
`AgentLoopTurnUpdate` can replace the entire `context`, plus `model` and `thinkingLevel`.

The candidate instead defines `_RunSnapshot` as only `system_prompt`, `model`, and
`thinking_level`; derives messages live from Session and visible tools live from ToolRegistry on
each request; and exposes `RunConfigUpdate` with only those same three configuration fields.
Consequences include caller/session/tool-registry mutations leaking into an active run and no way
for `prepareNextTurn` to replace run-local messages or tools. The candidate also passes neither
Pi's complete current context nor invocation-local `newMessages` through its prepare/stop hook
surface.

This contradicts both pinned Pi and the frozen design, which explicitly says `prepareNextTurn` may
replace model, **context**, and thinking level. No lower-layer reopen is required: Rust can own a
run-local `AgentContext` snapshot over cloned messages and tool handles, and Python can do the same.

**Required remediation:** specify and implement the complete shallow run snapshot; define a
language-neutral update containing optional whole `context`, `model`, and `thinking_level`; pass
the required turn context to prepare/stop listeners; add discriminating evidence for mid-run
message/tool/config mutation and whole-context replacement.

### L08-R002 — `handleRunFailure` trace, catch boundary, and failure output differ from Pi

**Classification:** `PI_PARITY_DEFECT`

Pinned Pi's `runWithLifecycle` catches any exception from the run executor. Its own test proves a
synchronous `streamFn` throw (`"provider exploded"`) is converted into the failure lifecycle. The
fallback emits:

```text
message_start(failure)
message_end(failure)
turn_end(failure, [])
agent_end(messages=[failure])
```

It does **not** emit a new `turn_start`. If a recovery event listener itself rejects, recovery can
stop and the error propagates; `finishRun` still executes.

The candidate catches only three Minion event-dispatch sites, deliberately lets provider/model and
other executor failures escape, inserts a synthetic `TURN_START`, and derives `agent_end.messages`
from every message accumulated since `AGENT_START` rather than Pi's `[failureMessage]`. Calling the
extra bracket a disclosed simplification is not an approved parity disposition.

**Required remediation:** adopt the actual high-level catch boundary, remove the synthetic
`turn_start`, preserve Pi's failure-only `agent_end.messages`, and add direct canonical or explicit
language evidence for provider-start failure, post-turn callback failure, and recovery-listener
failure.

### L08-R003 — streaming state and assistant message lifecycle are observably truncated

**Classification:** `PI_PARITY_DEFECT`

Pi assigns every stream event's complete `event.partial` to the active context and emits
`message_start` on `start`, then zero or more `message_update` events carrying complete partial
messages for text, thinking, and tool-call start/delta/end, then `message_end`.

The candidate reconstructs only text deltas and ignores the already-available `chunk.partial`.
This is not blocked by Layer 02/04: current certified Python `StreamChunk` explicitly documents and
stores `partial` on every variant, `collect(on_chunk=...)` passes the complete chunk to the caller,
and the certified Rust `StreamChunk::partial()` exposes the same shape. The candidate's assertion
that `collect()` exposes only raw deltas is factually false.

The projected canonical trace compounds the mismatch: `tool-round-trip.yaml` and
`projected-execution-ends-follow-completion-order.yaml` expect `message_update` before
`message_start` for streamed text, while pinned Pi emits start first. This wrong order is now
encoded in shared canonical data.

**Required remediation:** set `streaming_message` from each real `chunk.partial`, represent the
stream-start lifecycle, make `message_start -> message_update* -> message_end` normative and
canonical, and cover thinking/tool-call partials as well as text.

### L08-R004 — AG-004 and the shared contract are internally contradictory

**Classification:** `CONTRACT_ASSURANCE_DEFECT`

AG-004 still states that `prepareNextTurn` is not implemented and that its semantics remain a
tracked gap. The candidate spec, AG-008/AG-009 prose, assurance report, and Python code say it is
implemented. The row's claimed four-stage ordering is therefore neither a coherent current rule
nor complete traceability. The spec additionally truncates the frozen design's whole-context
replacement to three configuration fields.

**Required remediation:** rewrite AG-004 as one current semantic rule, align it with the corrected
whole-context contract, and cite real discriminating evidence rather than historical PASS-1 state.

### L08-R005 — `max_steps` is an undispositioned observable stop rule

**Classification:** `CONTRACT_ASSURANCE_DEFECT`

Pinned Pi has no Layer-08 `max_steps` stop in the audited source. Minion's canonical runner and
driver expose one, but no Layer-08 manifest row or normative spec disposition defines it as a
Minion extension or its interaction with adopted Pi ordering. The implementation checks the limit
immediately after `turn_end`, before `prepareNextTurn`, `shouldStopAfterTurn`, steering, and
follow-up, so it creates an exception to the candidate's otherwise-unconditional post-turn rule.

**Required remediation:** give `max_steps` an explicit governed Minion disposition and normative
ordering, reconcile it with the adopted Pi callback/queue sequence, and add evidence. If the chosen
behavior intentionally diverges observably from Pi, obtain the required governance approval.

### L08-R006 — initial steering is claimed before the first turn starts

**Classification:** `PI_PARITY_DEFECT`

Pi emits `agent_start`, then `turn_start`, emits initial prompt lifecycle events, and only then
calls `getSteeringMessages()` inside `runLoop`. The candidate calls `_claim_step_input()` and
dispatches `_pre_step()` before `_run_step()` appends `TURN_START`. Offline projection hides this
by not projecting inbox-claim events, but queue mutation and Minion listeners make the timing
observable.

**Required remediation:** open the first turn and admit prompt messages before the initial steering
poll, while retaining the no-double-drain continuation rule; add a listener-driven ordering test.

### L08-R007 — `prompt(text, images?)` is missing while AG-006 claims exact public parity

**Classification:** `PI_PARITY_DEFECT`

Pinned Pi exposes both the typed `AgentMessage | AgentMessage[]` overload and the convenience
`prompt(text: string, images?: ImageContent[])` overload, which creates one timestamped user
message with text followed by supplied images. Candidate `AgentLoop.prompt` accepts only `Message`
or a tuple and the spec describes only that shape.

**Required remediation:** specify and implement the convenience overload or obtain an explicit
intentional-divergence approval; add exact input-normalization evidence without narrowing the typed
Message boundary.

### L08-R008 — represented assistant `error`/`aborted` does not use Pi's terminal branch

**Classification:** `PI_PARITY_DEFECT`

In Pi, after the assistant message is appended, `stopReason === "error" || "aborted"` emits
`turn_end`, emits `agent_end`, and returns immediately. It does not call `prepareNextTurn`,
`shouldStopAfterTurn`, steering, or follow-up for that turn.

The candidate reduces a no-tool error/aborted message to the same `None` outcome as an ordinary
stop, then runs prepare/stop/steering/follow-up. Its current canonical error scenario passes only
because no listener or queued continuation distinguishes the branches.

**Required remediation:** represent terminal assistant error/aborted explicitly in the loop result,
exit before post-turn callbacks/queues as Pi does, and add discriminating evidence with listeners
and queued steering/follow-up.

## High-risk semantic reconstruction

- **First turn:** Pi emits run/turn start and prompt lifecycle before the initial steering poll.
- **Tool continuation:** a tool batch closes its turn; post-turn prepare/stop/steering runs; a
  non-terminated tool result can cause the next turn.
- **Steering:** checked after prepare and stop; if present it continues the same inner loop.
- **Follow-up:** checked only when the inner loop would otherwise end; continues the same run.
- **Terminate:** suppresses only tool-call-driven continuation. It does not skip prepare, stop,
  steering, or otherwise-eligible follow-up.
- **Represented error/aborted:** terminal immediately after its `turn_end`; no post-turn callbacks
  or queue polling.
- **Unexpected executor failure:** high-level recovery trace above; no added `turn_start`.
- **`agent_end.messages`:** prompt runs are seeded by prompt messages, plain continuation is empty
  seeded, pre-drained steering/follow-up uses the prompt-style seed, and failure recovery supplies
  only the synthesized failure message.

## Canonical and runner review

The two new scenarios are language-neutral and their runner operations are thin:

- `two-runs-have-independently-scoped-agent-end-messages.yaml` correctly proves independent normal
  run scoping;
- `continuation-excludes-the-prior-runs-messages.yaml` correctly proves only the assistant-last
  follow-up pre-drain branch it claims.

The runner dispatches to real Inbox/AgentLoop APIs and does not implement queue semantics. However,
canonical coverage is not sufficient for AG-001..AG-010, and two modified scenarios encode the
wrong assistant lifecycle order described in `L08-R003`. Placeholder scenarios are correctly xfail
and are not counted as evidence.

## Rust feasibility and lower-layer impact

The corrected contract is implementable in Rust without redesigning certified Layers 01, 03, 05,
06, or 07. Existing Rust Layer-07 `AgentInstance` already projects Session and ToolRegistry state;
Layer 08 can take a shallow run-local snapshot without duplicating either authority.

No Layer-02/04 reopen is required for full streaming fidelity: Rust already exposes complete
partial messages on every `StreamChunk`, and Python does too. The candidate's limitation is local
Layer-08 code, not a certified lower-layer contract barrier.

Layer 09 remains the owner of active cancellation propagation and cancellation settlement. None of
the findings above requires starting Layer 09.

## Fresh evidence

Against the exact code candidate:

```text
uv run pytest -q
    PASS; configured coverage 100.00%; placeholder cases xfailed

schema validation suite
    PASS (candidate reports 185 cases; focused suite passed)

manifest structural audit
    75 rows / 75 unique IDs

agent canonical inventory
    79 YAML files total
    19 placeholder/TO_BE cases
    60 executable files across all reached agent layers
```

Green tests do not override the source/contract contradictions above.

## Finding summary

```text
PI_PARITY_DEFECT
    L08-R001  incomplete context snapshot / prepareNextTurn
    L08-R002  failure catch boundary, trace, and output
    L08-R003  partial streaming state and message lifecycle
    L08-R006  initial steering poll timing
    L08-R007  missing prompt(text, images?) overload
    L08-R008  represented error/aborted continuation

CONTRACT_ASSURANCE_DEFECT
    L08-R004  contradictory AG-004 / truncated shared rule
    L08-R005  undispositioned max_steps ordering

PI_BEHAVIOR_UNCERTAIN
    none

PARITY_CONSTRAINED_RISK
    none

PARITY_NEUTRAL_HARDENING
    none material to this review
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

The next owner must perform narrow shared/Python remediation for L08-R001 through L08-R008 and
publish new candidate SHAs. Any candidate-head change requires a full independent Rust contract
re-review. Rust Layer 08 must not be implemented from the rejected candidates.
