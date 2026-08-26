# Layer 07 — Agent Public State + Inbox/Queues — Shared/Python Certification

**Pass date:** 2026-08-26
**Scope:** shared contract (`spec/agent.md`, `pi-parity-manifest.yaml`, canonical-scope decision)
and Python implementation only. **No Rust file was read for editing purposes and none was
modified.** Layer 08 (run/turn state machine) and Layer 09 (cancellation) were not implemented,
touched, or certified.

## Starting state

```text
minion-agent       2fe813c6c42923e2abdf08b354e0eac8c32a5fcd
minion-agent-docs  9e777797da132170cf314fa66ca67652aea09ab8
pinned Pi          b7bb00b936dbe21b8e160b3e89efdec361846699
Layers 01-06        CROSS-LANGUAGE CERTIFIED / CLOSED
```

The unrelated Phase-5 working-tree change was left untouched, unstaged, and uncommitted throughout.

**Important scope-defining discovery, made before any design decision:** `minion-agent-python/src/
minion_agent/agent/` and `agent_loop/` already exist, are already substantial (identity, inbox,
instance, registry, plugin, decisions, events, projection, and a full turn/step driver), and are
already extensively tested (77 existing tests across `tests/agent/` alone before this pass, plus
property-based tests in `tests/agent/test_properties.py`, plus `tests/agent_loop/`). This code
predates the Layer-07/08 split the same way Layer 06's execution code predated its own split from
Layer 05 -- it is functional and already exercised by Layer 06's own canonical test runner, but had
not yet been through Pi-audit/manifest/spec certification as its own layer. This pass's job was
therefore primarily **audit and formal certification of what already exists**, plus filling the one
concrete gap the audit found, not building a queue/state layer from scratch.

---

## Pinned Pi symbol audit

Read directly at pinned Pi (local `ref-repos/pi` checkout, confirmed at the exact pinned commit):
`packages/agent/src/agent.ts` (full file, 592 lines) and `packages/agent/src/types.ts` (`AgentState`,
`QueueMode`, `AgentContext`, lines 1-420).

```text
Pi symbol                                  Pi file        Layer owner   Minion disposition
Agent (class)                              agent.ts       L07 (state/   Split: state+queues here;
                                                           queues) +     prompt/continue/run
                                                           L08 (run)     orchestration is
                                                                         AgentLoop/driver.py (L08,
                                                                         untouched this pass)
AgentState.isStreaming                     types.ts       L07 vocab,    AgentStatus.IDLE/RUNNING
                                                           L08 timing    (initial value certified;
                                                                         transitions L08-owned)
AgentState.streamingMessage                types.ts       L07 vocab,    NOT YET IMPLEMENTED --
                                                           L08 timing    documented only (spec),
                                                                         no code stub added
AgentState.pendingToolCalls                types.ts       L07 vocab,    NOT YET IMPLEMENTED --
                                                           L08 timing    documented only
AgentState.errorMessage                    types.ts       L07 vocab,    NOT YET IMPLEMENTED --
                                                           L08 timing    documented only
AgentState.messages                        types.ts       L03           Projection only
                                                           (certified)   (`derive_messages`); Agent
                                                                         never stores messages
AgentState.tools                           types.ts       L05           ToolRegistry via scope;
                                                           (certified)   Agent never stores tools
AgentState.systemPrompt / model /          types.ts       L07-adjacent  AgentDefinition (frozen,
  thinkingLevel                                           (mutable in   shared across instances) --
                                                           Pi; static    per-instance mutability
                                                           in Minion)    not implemented; noted as
                                                                         a known, deferred gap
                                                                         below, not fixed this pass
PendingMessageQueue (class)                agent.ts       L07           Inbox (2 targets, 3
                                                                         aliases)
Agent.steer                                agent.ts       L07           Inbox.steer -> NEXT_STEP,
                                                                         wakes
Agent.followUp                             agent.ts       L07           Inbox.followup -> NEXT_TURN,
                                                                         wakes
(no Pi equivalent)                         --             L07           Inbox.inject -> NEXT_STEP,
                                                                         silent (intentional Minion
                                                                         extension)
QueueMode ("all" | "one-at-a-time")        types.ts       L07           ClaimPolicy.ALL /
                                                                         ONE_AT_A_TIME (exact match)
PendingMessageQueue.drain                  agent.ts       L07           Inbox.claim(target, policy)
Agent.clearSteeringQueue                   agent.ts       L07           Inbox.clear(NEXT_STEP) --
                                                                         NEW this pass
Agent.clearFollowUpQueue                   agent.ts       L07           Inbox.clear(NEXT_TURN) --
                                                                         NEW this pass
Agent.clearAllQueues                       agent.ts       L07           Inbox.clear_all() -- NEW
                                                                         this pass
Agent.hasQueuedMessages                    agent.ts       L07           Inbox.has_pending() -- NEW
                                                                         this pass
Agent.reset                                agent.ts       L07 (queue    NOT reproduced in place --
                                                           half) + L03  intentional divergence, see
                                                           (transcript  "Reset" below
                                                           half, frozen)
Agent.prompt / Agent.continue              agent.ts       L08           AgentLoop.run_until_idle
                                                                         (existing, untouched)
Agent.abort / this.signal                  agent.ts       L09           Not implemented
                                                                         (`AgentLoop.cancel()`
                                                                         exists as a structural stub
                                                                         only; untouched this pass)
Agent.subscribe / listeners                agent.ts       L08           EventBus (Runtime, already
                                                                         certified) realizes this
                                                                         architecturally
config.getSteeringMessages                 types.ts       L08 (calls   AgentLoop._claim_step_input
                                                           the L07      (existing, untouched)
                                                           primitive)
config.getFollowUpMessages                 types.ts       L08           AgentLoop._run_turn's
                                                                         NEXT_TURN claim (existing,
                                                                         untouched)
```

---

## Layer boundary

**Layer 07 owns:** the Agent processing-status vocabulary and its initial value; steering/follow-up
queue storage, independence, ordering, provenance; the claim primitive for both policies; queue
clearing and pending-input observation.

**Layer 08 defers:** the run/turn/step state machine; exactly when the claim primitive is invoked
for either queue; `prompt()`/`continue()` caller-rejection rules while active; `shouldStopAfterTurn`/
`prepareNextTurn` orchestration; steering-vs-follow-up priority during a run; the actual wiring of
`streamingMessage`/`pendingToolCalls`/`errorMessage`, since their transitions require step/turn
timing this pass does not implement or certify.

**Layer 09 defers:** abort/cancellation propagation into an active run and its providers/tools/hooks.

**Boundary coherent:** YES. The existing `AgentLoop`/driver.py (already written, already exercised
by Layer 06's own canonical tests, not re-certified or modified by this pass) already consumes
exactly the Layer-07 primitives above (`inbox.pending`, `inbox.claim`) without needing any change
to introduce Layer-07's new operations (`clear`/`clear_all`/`has_pending`) -- proof by construction
that Layer 08 can consume Layer-07's primitives without redesign, since Layer 08's own existing code
already does, unmodified.

---

## Public state contract

**Initial state:** a live `AgentInstance` starts `AgentStatus.IDLE` (`test_an_instance_starts_idle`,
pre-existing). `Inbox` starts with both targets empty and no wake pending
(`test_has_pending_is_false_for_an_empty_inbox`, new this pass).

**Observable fields (Layer-07 scope):** `AgentInstance.status` (`AgentStatus.IDLE | RUNNING`);
`Inbox.pending(target)`, `Inbox.has_pending()`, `Inbox.wake_requested`.

**Mutation rules:** `AgentInstance.set_status()` is a no-op for a same-value assignment (a
transition signal must signal transitions, not assignments -- `test_setting_the_same_status_twice_
reports_once`, pre-existing). `Inbox.send`/`clear`/`clear_all` mutate only their own target(s); a
claim removes exactly what it returns, nothing else.

**Session overlap:** none. `AgentInstance` holds a `SessionLog` reference, not a message list;
`derive_messages(log)` is the only message projection, and it is Layer-03's own certified function,
unchanged and uncalled by anything this pass added.

**Pi parity:** PASS for everything Layer 07 owns. One known, disclosed gap outside this pass's
fix scope: Pi's `AgentState.systemPrompt`/`model`/`thinkingLevel` are mutable per-instance fields
(a caller can reassign them between runs); Minion's `AgentDefinition` is a frozen dataclass shared
across instances with no per-instance override. This is a genuine divergence, not yet reproduced --
recorded here as a known gap rather than silently accepted or hastily redesigned, since fixing it
correctly would mean deciding whether `AgentDefinition` gains a mutable per-instance layer or a
separate override mechanism, a design question this narrow pass should not rush.

---

## Steering contract

**Input type:** `UserMessage` (Minion's own narrowing of Pi's broader `AgentMessage` union --
classified as an intentional, low-risk divergence: steering conceptually represents asynchronous
*user* input arriving mid-run, and nothing in Pi's own agent-loop consumption ever requires a
non-user role to be steerable).
**Enqueue:** `Inbox.steer(message, origin=None)` -> appends to the `NEXT_STEP` target, requests a
wake, returns a unique `InputEnvelope`.
**Ordering:** FIFO, proven both by direct tests and property-based tests across arbitrary
interleavings with follow-up/inject.
**Poll/drain:** `Inbox.claim(NEXT_STEP, policy)` -- policy-exact reproduction of Pi's `QueueMode`
(see Claim contract above).
**Snapshot semantics:** a claim is atomic with respect to the caller: it returns a fixed set of
already-queued envelopes and mutates the queue in the same call; anything enqueued *after* a claim
call returns is not part of that claim's result, matching Pi's own synchronous, single-threaded
`drain()`. Distinguishing this from "one poll always empties everything currently there" would
require an interleaving that adds new input *during* a single claim call, which is not possible in
Minion's synchronous `claim()` any more than in Pi's synchronous `drain()` -- both mutate and return
in one uninterruptible step, so no scenario can observe a difference. This was verified directly
against Pi's source (`drain()`'s body has no `await`/yield point), not assumed from Python's own
concurrency model.
**Idle behavior (Layer-07 scope):** enqueueing while idle is unconditionally accepted; nothing
about `Inbox.steer` depends on `AgentInstance.status`.
**Active behavior (Layer-07 scope):** identical -- `Inbox` has no awareness of run state at all;
whether an active run *sees* newly steered input before its next step boundary is Layer-08 timing,
out of scope here.
**Pi parity:** PASS.

---

## Follow-up contract

**Input type:** `UserMessage` (same narrowing and rationale as steering).
**Enqueue:** `Inbox.followup(message, origin=None)` -> appends to the `NEXT_TURN` target, requests
a wake, returns a unique `InputEnvelope`.
**Ordering:** FIFO, proven the same way as steering.
**Poll/drain:** `Inbox.claim(NEXT_TURN, policy)` -- same policy-exact primitive as steering, applied
to the other target.
**Snapshot semantics:** identical reasoning to steering, above.
**Pi parity:** PASS.

---

## Queue relationship

**Separate storage:** YES -- two independent lists behind one `dict[InboxTarget, list[...]]`,
proven never to leak into each other under arbitrary claim/enqueue interleavings
(`test_the_two_queues_never_leak_into_each_other`, property-based, pre-existing).
**Cross-queue global order:** NOT APPLICABLE -- pinned Pi itself keeps two independent arrays with
no shared ordering; Minion's two targets are equally independent. Provenance is per-envelope, not
a global sequence, precisely because a batch claim can merge several origins into one turn/step
(design spec section 6) -- a single global order would not let that distinction survive a
claim-all.
**Cross-queue priority owned by:** L08 (which target is claimed first, and when, during a run is
entirely `AgentLoop`'s decision, already implemented, not re-certified here).
**Future Layer-08 compatibility:** PASS -- confirmed by construction: `AgentLoop._run_turn`/
`_claim_step_input` already call exactly `inbox.claim(target, policy)` and `inbox.pending(target)`,
the same primitives this pass certifies, unmodified. No duplicated queue authority exists anywhere
in the codebase (`Inbox` is the single owner; nothing else stores queue state).

---

## Manifest

```text
New rows:    AG-011, AG-012, AG-013 (continuing the existing AG- prefix; AG-001..AG-010 already
             reserved this master-phase-3 surface for Layer-08/09 concerns and were NOT touched)
Pi pointers: packages/agent/src/agent.ts::PendingMessageQueue/Agent.steer/Agent.followUp/
             Agent.clearSteeringQueue/clearFollowUpQueue/clearAllQueues/hasQueuedMessages,
             packages/agent/src/types.ts::QueueMode
Canonical evidence: none added this pass (see "Canonical scope decision" below) -- Python
             language tests are the evidence for all three new rows
Python evidence: src/minion_agent/agent/inbox.py, src/minion_agent/agent/envelope.py
Rust status: PENDING -- Layer 07 not yet implemented in Rust (stated plainly on all three rows,
             not left blank and not described as conformant)
unclassified rows: none
```

Total manifest size: 69 rows (was 66), 69 unique IDs, confirmed by direct parse.

---

## Canonical scope decision (why no new `conformance/agent/*.yaml` was added)

The existing canonical family (`conformance/agent/*.yaml`) is built entirely around a full
provider-script/tool-stub/turn-driven scenario (per `test_agent_conformance.py`'s own schema) --
there is no schema primitive for observing `Inbox` state directly, only for observing the
*consequences* of a full run. Writing a new scenario that exercises `steer`/`followup`/`inject`
through that schema and asserts anything about *when* those messages entered the transcript would
inherently also be observing -- and implicitly certifying -- `AgentLoop`'s own polling timing,
which is Layer 08's job and explicitly out of scope for this pass (`IMPORTANT: No Layer-07
canonical scenario should pretend to run that state machine unless the scenario is strictly testing
a queue primitive` -- the governing instruction's own words). No such schema-level primitive exists
yet that isolates the queue behavior from run timing.

The pure queue mechanics Layer 07 actually owns (ordering, independence, claim policy, clearing) do
not need a provider or a run to observe at all -- they are plain, synchronous data-structure
behavior, already thoroughly proven by both direct and property-based Python tests (77 tests across
`tests/agent/`, 21 in `test_inbox.py` alone, including hypothesis-driven arbitrary-interleaving
proofs). Per the governing instruction's own escape valve ("If this is not independently observable
until Layer 08, document the primitive now but defer orchestration coverage" / "Do not force this
scenario if no Layer-07-level observable seam exists"), this pass documents the primitive precisely
(spec + manifest, above) and treats the Python test suite as the authoritative Layer-07 evidence,
rather than inventing new canonical-schema machinery (e.g. an `expect_inbox_pending` observation)
whose only current consumer would be this one layer, with no second (Rust) implementation yet to
benefit from a language-neutral fixture. This is disclosed explicitly, not a silent gap: cross-
language canonical coverage for the queue primitives is a reasonable fast-follow once Rust
implements its own Layer 07, exactly the same reasoning applied to the earlier IR-L06-001 finding's
own deferred canonical scenario before Python's fix existed to prove it meaningful.

---

## Python implementation

**Agent state owner:** `AgentInstance` (`identity.py` + `instance.py`) -- unchanged this pass,
already correct.
**Steering queue:** `Inbox` (`inbox.py`), target `InboxTarget.NEXT_STEP` -- unchanged.
**Follow-up queue:** `Inbox`, target `InboxTarget.NEXT_TURN` -- unchanged.
**Drain/poll primitive:** `Inbox.claim(target, policy)` -- unchanged.
**Reset/clear:** `Inbox.clear(target)`, `Inbox.clear_all()`, `Inbox.has_pending()` -- **new this
pass** (did not exist before; genuine `CONTRACT_ASSURANCE_DEFECT`, resolved).
**Layer-08 logic implemented:** NO -- `AgentLoop`/`driver.py` was read for context and boundary
verification only; zero lines changed.
**Layer-09 logic implemented:** NO -- `AgentLoop.cancel()`'s existing structural stub was read,
not touched.

---

## RED → GREEN evidence

```text
test_has_pending_is_false_for_an_empty_inbox                          RED -> GREEN
test_has_pending_is_true_with_only_a_next_turn_item                    RED -> GREEN
test_has_pending_is_true_with_only_a_next_step_item                    RED -> GREEN
test_clearing_one_target_leaves_the_other_untouched                    RED -> GREEN
test_clearing_an_empty_target_is_a_harmless_no_op                      RED -> GREEN
test_clear_all_empties_both_queues                                     RED -> GREEN
test_clearing_does_not_affect_the_wake_signal                          RED -> GREEN
```

RED confirmed directly: all seven failed with `AttributeError: 'Inbox' object has no attribute
'clear_all'` (or `'clear'`/`'has_pending'`) before `Inbox.clear`/`clear_all`/`has_pending` were
added; all seven pass after.

---

## Contract-quality check

**Can Layer 08 reproduce Pi's steering polling without Layer-07 redesign?** YES -- it already does,
unmodified, via `inbox.claim(NEXT_STEP, policy)`/`inbox.pending(NEXT_STEP)`.
**Can Layer 08 reproduce Pi's follow-up polling without Layer-07 redesign?** YES -- same primitive,
`NEXT_TURN` target, already in use.
**Duplicated queue authority?** NO -- `Inbox` is the sole owner; `AgentLoop` never maintains its own
queue state.
**Runner workaround required?** NO -- not applicable, since no new canonical runner code was
written this pass.
**Contract quality:** PASS.

---

## Runner audit

Not applicable in the canonical-YAML sense (no new scenario was added -- see "Canonical scope
decision"). For the Python test suite itself: no test constructs its own queue, reimplements FIFO,
or simulates `Inbox`/`AgentInstance` state -- every assertion reads the real `Inbox`/`AgentStatus`
objects directly.

```text
owns queue storage        NO
implements FIFO            NO
drains queue itself        NO
simulates state             NO
implements Layer-08 timing  NO
thin                        YES
```

---

## Quality gates

```text
full pytest (coverage enabled):     930 passed, 19 xfailed, 0 failed, 100.00% coverage
                                     (was 923; +7, the new Inbox clear/has_pending tests)
ruff check .:                        All checks passed
mypy (configured scope + typing fixtures): Success, no issues found in 59 source files
schema validation:                   166 passed (unchanged -- no schema file touched)
manifest parse + unique-ID audit:    69 / 69 unique (was 66; +3: AG-011, AG-012, AG-013)
Runtime canonical:                   26 passed (unchanged)
Session canonical:                   20/20 passed (unchanged)
XFORM canonical:                     14/14 passed (unchanged)
Layer-05 canonical + integrity:      9 + 7 = 16 passed (unchanged)
Layer-06 canonical:                   11/11/11/0 (unchanged)
Layer-07 (new):                       no new canonical scenario (see decision above); 21 Inbox
                                      tests (14 pre-existing + 7 new), 77 total tests/agent/
                                      (unchanged except the 7 additions)
```

---

## Regression

```text
Layers 01-06    PASS -- every regression count above is identical to the pre-Layer-07 baseline
new regressions  none
```

---

## Active findings

```text
PI_PARITY_DEFECT              none
CONTRACT_ASSURANCE_DEFECT     none active -- the one found (missing clear/has_pending operations)
                               was resolved this pass
PI_BEHAVIOR_UNCERTAIN         none -- every Pi symbol audited above was read directly from source,
                               not inferred
PARITY_CONSTRAINED_RISK       none blocking; one disclosed, non-blocking known gap: Pi's mutable
                               per-instance systemPrompt/model/thinkingLevel has no Minion
                               equivalent yet (AgentDefinition is frozen and shared) -- recorded,
                               not fixed, since correcting it is a separate design decision this
                               narrow pass should not rush
```

---

## Assurance

**Artifact:** this document.
**Status:** Python Layer 07 `CERTIFIED` for everything within this pass's ownership boundary
(steering/follow-up queue storage, claim policy, clearing, processing-status vocabulary). The
public-state fields requiring run/turn transitions (`streaming_message`/`pending_tool_calls`/
`error_message`) and the mutable-per-instance-config gap remain explicitly open, tracked above, not
silently certified.

---

## Verdict

```text
Shared Layer-07 contract    READY FOR INDEPENDENT RUST REVIEW
Python Layer 07              CERTIFIED
Rust Layer 07                NOT IMPLEMENTED / PENDING REVIEW
Layer 07 cross-language      NOT CLOSED
Layer 08                     NOT STARTED
```

## Next action

Independent Rust review of this Layer-07 shared contract (`spec/agent.md`'s new Layer-07 section,
`pi-parity-manifest.yaml`'s `AG-011`/`AG-012`/`AG-013`) against Rust's own architecture, before any
Rust implementation begins. Do not implement Rust in response to this document.

---

# PASS 2.5 — remediation after independent Rust rejection (2026-08-26)

## Rust review commit

`bb6bd276a2093904d0fbe424bafd45d2b6c08443`
(`assurance/layers/07-agent-state-inboxes-rust-review.md`, merged via fast-forward).

## Rejection summary

```text
L07-R001  PI_PARITY_DEFECT           mutable per-instance systemPrompt/model/thinkingLevel omitted
L07-R002  PI_PARITY_DEFECT           steer/followUp narrowed AgentMessage -> UserMessage
L07-R003  PI_PARITY_DEFECT           fresh-instance replacement is not Pi's in-place reset()
L07-R004  CONTRACT_ASSURANCE_DEFECT  zero language-neutral canonical scenarios
L07-R005  CONTRACT_ASSURANCE_DEFECT  incomplete AgentState field disposition coverage
```

All five were independently re-audited against pinned Pi directly (`agent.ts` re-read in full a
second time), not accepted from the review's own description.

## L07-R001 — mutable per-instance state

Confirmed directly: `createMutableAgentState`'s `systemPrompt`/`model`/`thinkingLevel` are plain,
directly assignable properties (not getter/setter pairs), defaulting from `initialState?.x ?? ...`;
`Agent.state` returns this same live object, so assignment through it is immediately observable and
affects every subsequent run.

**Implementation:** `AgentInstance` gained `system_prompt: str`, `model: ModelId`,
`thinking_level: ThinkingLevel` (new `ThinkingLevel` enum, pinned Pi's seven values verbatim, in
`identity.py`) -- plain mutable instance attributes, initialized from `definition.system`/`.model`/
`ThinkingLevel.OFF`, freely reassignable per instance afterward. `AgentDefinition` remains frozen
and shared, per the review's own preferred architecture; Minion did not make it mutable to imitate
Pi.

**Deliberate scope boundary, disclosed, not hidden:** the existing, uncertified `AgentLoop`/
`driver.py` (`_run_step`) still reads `instance.definition.model`/`.definition.system` directly for
an actual request -- it was **not** rewired to read `instance.model`/`.system_prompt`. Rewiring
those three read sites is Layer-08 run/turn implementation, explicitly out of this narrow pass's
ownership boundary. The review's own words license this: "Layer 07 must define current per-instance
state and its mutation surface; Layer 08 may own when run snapshots are consumed." The state and its
mutation surface now exist, are per-instance-isolated, and are ready for Layer 08 to consume without
any further Layer-07 redesign, once Layer 08 itself is undertaken.

**Status: RESOLVED** (state ownership/mutation surface); consumption wiring correctly and
explicitly deferred to Layer 08, not silently skipped.

## L07-R002 — `AgentMessage` domain

Confirmed directly: `AgentMessage = Message | CustomAgentMessages[keyof CustomAgentMessages]`, and
`CustomAgentMessages` is an empty interface in pinned Pi itself (apps extend it via TypeScript
declaration merging; nothing in pinned Pi populates it). The actual, complete domain is therefore
exactly `Message` -- the already-certified Layer-02 vocabulary.

**Implementation:** `Inbox.send`/`steer`/`followup`/`inject`, `InputEnvelope.message`, and the new
`AgentInstance.steer`/`.follow_up`/`.inject` wrappers are all typed `Message`, not `UserMessage`.
This cascaded into two purely type-level (zero behavior change) fixes to keep `mypy` clean:
`decisions.Enter.messages` and `driver.py::AgentLoop._pre_step`'s parameter both widened from
`tuple[UserMessage, ...]` to `tuple[Message, ...]` -- confirmed zero behavioral change via the full,
unmodified `tests/agent_loop/` suite (62 tests) staying green.

**Tests added** prove a `UserMessage`, an `AssistantMessage`, and a `ToolResultMessage` are each
individually accepted by `steer`/`followup`, and that a claim returns all three, mixed, in FIFO
order (`test_steer_accepts_an_assistant_message`, `test_followup_accepts_an_assistant_message`,
`test_steer_accepts_a_tool_result_message`, `test_claim_returns_mixed_message_variants_in_fifo_
order`) -- not merely re-proven with `UserMessage` alone.

**Status: RESOLVED.**

## L07-R003 — in-place reset

Confirmed directly (full re-read of `Agent.reset()`): in-place, idle-only (`this.activeRun` check),
exact rejection text, clears `messages`/`isStreaming`/`streamingMessage`/`pendingToolCalls`/
`errorMessage`/both queues, retains everything else including object identity.

**Implementation:** `AgentInstance.reset()` (new `AgentActiveError`), genuinely in-place -- the same
`Inbox`/`SessionLog`/scope objects survive (`test_reset_is_in_place_not_a_fresh_instance`); config
(`system_prompt`/`model`/`thinking_level`), `on_status_change`, and `definition` all retained
(`test_reset_retains_identity_configuration_and_tool_relationship`); exact rejection text and
no-partial-mutation-on-rejection both proven
(`test_reset_while_running_is_rejected_atomically`); runtime state and both queues cleared
(`test_reset_clears_runtime_state_and_both_queues`).

**One sub-piece explicitly classified, not silently dropped:** clearing `messages`. Checked
directly: `SessionLog` (`session/log.py`) has exactly four public members --
`__len__`/`events`/`append`/`surface` -- no truncate/clear operation exists, by design (an
already-certified Layer-03 append-only property). Teaching `derive_messages` to respect a "reset
boundary" marker mid-log would itself be a new Layer-03 projection semantic. Per the governing
instruction's own explicit escape valve ("If implementing full mutable message replacement would
require altering certified Layer-03 semantics: STOP, classify the dependency explicitly"), this is
recorded as a classified cross-layer dependency, not implemented unilaterally, and not silently
omitted either -- `reset()` clears every other Pi-cleared field it can safely reach.

**Status: SUBSTANTIALLY RESOLVED** -- every observable difference the review's own rejection turned
on (identity, references, listeners, active-rejection, retained configuration) is closed; the one
remaining sub-piece is a disclosed, classified, cross-layer dependency on a Layer-03 primitive this
pass has no mandate to add.

## L07-R004 — language-neutral canonical evidence

The prior zero-canonical decision is withdrawn. A fourth `conformance/agent/` scenario shape was
added (`agent_inbox`/`expect`, `agent-inbox-scenario.schema.json`), discriminated the same way the
existing `transform`/`tool_registry` shapes already are -- still one canonical family
(`conformance/agent`), not a fourth. `tests/conformance/agent_inbox_runner.py` +
`test_agent_inbox_conformance.py` execute it against the real `Inbox` primitive directly: no
provider, no tool, no run-loop timing.

```text
agent-inbox-queue-mode-fifo.yaml
    steering: enqueue A, B; claim one-at-a-time -> [A]; enqueue C; claim all -> [B, C];
    claim all again on the now-empty queue -> [] (proves both QueueMode values, an empty claim,
    and enqueue-after-claim, in one scenario)

agent-inbox-queue-independence-and-clearing.yaml
    steering: A, C; follow-up: B; hasQueuedMessages before any clear -> true; clear steering;
    hasQueuedMessages after -> true (follow-up survives); claim follow-up -> [B];
    hasQueuedMessages after draining follow-up -> false
```

Both were run against the real production `Inbox`, not a runner-computed expectation; the runner
performs no FIFO logic, no claim-policy branching, and no wake bookkeeping of its own -- confirmed
by direct code reading of `agent_inbox_runner.py` (43 lines, one dispatch per action type, each a
direct method call).

**Status: RESOLVED.**

## L07-R005 — complete public-state disposition

Every pinned Pi `AgentState` field now has an explicit, non-contradictory disposition (manifest
`AG-014`/`AG-015`, plus the corrected `AG-011`/`AG-013`; see the authority-map table this pass added
to `spec/agent.md`). No field is left with "non-blocking gap"/"architectural difference"/"later
maybe" language -- every disposition is exactly `adopted`, `deferred parity`, or `intentional
divergence`, per the governing instruction's own closed list.

`messages`/`tools` public projection semantics, previously "authority identified, semantics
unspecified" per the review, are now specified precisely (see spec's new "Messages and tools"
section): `messages` is a fresh `derive_messages` projection every read (new
`AgentInstance.messages` property, `test_messages_projects_the_session_log`); `tools` is the
existing, certified `ToolRegistry.visible_from(scope)` query, not a new store. `is_streaming`'s
disposition (`AgentStatus`, `adopted`, not "architectural adaptation") and `wake_requested`'s
disposition (intentional Minion extension, kept separate from every adopted rule) are both now
explicit, matching the review's own specific requests.

**Status: RESOLVED.**

## Manifest delta

```text
AG-011  corrected: UserMessage narrowing removed (Message adopted), Agent-level steer/follow_up/
        inject wrappers added, canonical evidence cited
AG-012  corrected: canonical evidence cited (rule text itself was already accurate)
AG-013  corrected: reset conflation removed (moved to its own row, AG-016); Agent-level
        clear/has_queued_messages wrappers added; canonical evidence cited
AG-014  NEW: mutable per-instance current configuration (L07-R001)
AG-015  NEW: complete AgentState field disposition -- messages/tools projections, runtime-field
        vocabulary, status/wake dispositions (L07-R005)
AG-016  NEW: in-place reset (L07-R003)
```

Total: 72 rows (was 69), 72 unique IDs, confirmed by direct parse. `AG-001`..`AG-010` untouched.

## RED → GREEN (this pass)

```text
test_current_config_defaults_from_the_definition                         RED -> GREEN
test_mutating_one_instances_config_does_not_affect_a_sibling_or_the_definition   RED -> GREEN
test_runtime_fields_start_at_pis_own_initial_values                       RED -> GREEN
test_messages_projects_the_session_log                                   RED -> GREEN
test_reset_clears_runtime_state_and_both_queues                          RED -> GREEN
test_reset_retains_identity_configuration_and_tool_relationship          RED -> GREEN
test_reset_is_in_place_not_a_fresh_instance                              RED -> GREEN
test_reset_while_running_is_rejected_atomically                          RED -> GREEN
test_steer_and_follow_up_delegate_to_the_inbox_at_the_agent_surface      RED -> GREEN
test_inject_delegates_to_the_inbox_without_waking                        RED -> GREEN
test_agent_level_queue_clearing_delegates_to_the_inbox                   RED -> GREEN
agent-inbox-queue-mode-fifo (canonical)                                  RED -> GREEN
agent-inbox-queue-independence-and-clearing (canonical)                  RED -> GREEN
```

RED confirmed directly for the `AgentInstance`-level additions: `ImportError: cannot import name
'AgentActiveError'` before it existed; subsequent `AttributeError`s for `system_prompt`/`model`/
`thinking_level`/`streaming_message`/`pending_tool_calls`/`error_message`/`messages`/`reset`/
`steer`/`follow_up`/`inject`/`has_queued_messages`/`clear_*` before each was added. The broadened
`AgentMessage` domain (`L07-R002`) had no *runtime* RED (Python does not enforce type hints), since
nothing ever rejected a non-`UserMessage` value at the object level -- its defect was in the
*declared* type contract and the disposition narrative, both corrected; the new tests prove the
now-official contract, not a runtime behavior change.

## Contract-quality check

```text
Can L08 mutate is_streaming/streaming_message/pending_tool_calls/error_message
  without changing their type or location?                                YES
Can L08 consume current system_prompt/model/thinking_level
  without redesigning AgentInstance?                                       YES (fields already
                                                                             exist; only driver.py's
                                                                             own read sites would
                                                                             need updating, a
                                                                             mechanical change, not
                                                                             a redesign)
Can L08 poll steering/follow-up with exact Pi timing through
  certified primitives?                                                    YES (unchanged --
                                                                             AgentLoop already
                                                                             consumes inbox.claim/
                                                                             pending unmodified)
Can reset remain correct once L08 exists?                                  YES -- reset does not
                                                                             touch anything L08 will
                                                                             own, and L08's own
                                                                             active-run check
                                                                             (status) is the same
                                                                             primitive reset already
                                                                             uses
Duplicate state authority?                                                  NO
Contract quality                                                            PASS
```

## Runner audit (agent_inbox)

```text
owns queue storage        NO
implements FIFO            NO
implements QueueMode        NO
performs clear itself       NO
computes hasQueued itself   NO
resets state itself         NO -- not applicable (agent_inbox scenarios don't touch reset)
stores Agent state itself   NO
simulates L08                NO
thin                          YES
```

## Quality gates (final, this pass)

```text
full pytest (coverage enabled):     950 passed, 19 xfailed, 0 failed, 100.00% coverage
                                     (was 930 at the start of this pass)
ruff check .:                        All checks passed
mypy (configured scope + typing fixtures): Success, no issues found in 59 source files
schema validation:                   169 passed (was 166; +3: new schema file validity + 2 new
                                      scenario validations)
manifest parse + unique-ID audit:    72 / 72 unique (was 69; +3: AG-014/015/016)
Runtime canonical:                   26 passed (unchanged)
Session canonical:                   20/20 passed (unchanged)
XFORM canonical:                     14/14 passed (unchanged)
Layer-05 canonical + integrity:      9 + 7 = 16 passed (unchanged)
Layer-06 canonical:                   11/11/11/0 (unchanged)
Layer-07 canonical (new):             2 discovered / 2 executed / 2 passed / 0 deferred
tests/agent_loop/ (Layer-8-ish,
  unmodified logic, type-only touch): 62 passed (unchanged -- proves the AgentMessage widening
                                      caused zero behavioral change)
```

## Active findings (after this pass)

```text
PI_PARITY_DEFECT              none
CONTRACT_ASSURANCE_DEFECT     none active -- one explicitly classified cross-layer dependency
                               remains open (Layer-03 primitive needed for full reset parity;
                               documented in AG-016 and spec/agent.md's Reset section, not hidden)
PI_BEHAVIOR_UNCERTAIN         none
PARITY_CONSTRAINED_RISK       none blocking
```

## Verdict (supersedes this document's own PASS-1 verdict above)

```text
L07-R001    RESOLVED
L07-R002    RESOLVED
L07-R003    RESOLVED (substantially -- one classified, disclosed cross-layer dependency remains)
L07-R004    RESOLVED
L07-R005    RESOLVED

Shared Layer-07 contract    READY FOR REPEAT INDEPENDENT RUST REVIEW
Python Layer 07              RE-CERTIFIED
Rust Layer 07                 BLOCKED / PENDING REVIEW
Layer 07 cross-language       NOT CLOSED
Layer 08                       NOT STARTED
```

## Next action

Repeat independent Rust Layer-07 contract review of this corrected candidate. Do not implement
Rust until that review explicitly approves the contract for Rust implementation.

# PASS 3 — remediation after second independent Rust rejection (2026-08-27)

Between PASS 2.5 above and this pass, a verification-only increment (`minion-agent-docs@32bf5a9`)
added two small spec clarifications and re-confirmed PASS 2.5's own remediation against pinned Pi
directly; it changed no Python file and is not repeated here. This section addresses the *next*
independent Rust review, which ran against that verified PASS 2.5 candidate and found four new
findings PASS 2.5 had not closed.

## Rust review commit

`e25006668a59109d4dd03829c04e37d52f434107`
(`.worktrees/l07-rereview-docs/assurance/layers/07-agent-state-inboxes-rust-rereview.md`).

## Rejection summary

```text
L07-R003  PI_PARITY_DEFECT           reset leaves messages visible despite an already-certified
                                      Session reset marker PASS 2.5 did not find; tools sub-finding:
                                      no Agent-level tools accessor actually existed
L07-R004  CONTRACT_ASSURANCE_DEFECT  action schema's minProperties:1 permits ambiguous
                                      multi-operation actions; claimed clear-all canonical evidence
                                      was absent
L07-R005  CONTRACT_ASSURANCE_DEFECT  AG-015 bundled four different dispositions under one
                                      `disposition:` value; wake-on-reset left unspecified
L07-R006  CONTRACT_ASSURANCE_DEFECT  spec's isStreaming write-point sentence incorrectly claimed
                                      no other code path ever assigns it (initialization and reset
                                      both do)
```

All four were independently re-verified against pinned Pi source and the actual current repository
state directly, not accepted from the review's own description.

## L07-R003 — reset must clear messages; tools accessor

**Reset/messages, re-audited:** the review's own Layer-03 analysis was checked directly against
`session/operations.py` and `session/derive.py`. It is correct: `session.reset(log)` already exists,
already certified, and already appends a `session/reset` marker event that `derive.py`'s
`_latest_of`/`effective_surface`/`_derive` already treat as an exclusive floor. PASS 2.5's own
conclusion that no such primitive existed was wrong -- it read `SessionLog`'s own four public
members (`__len__`/`events`/`append`/`surface`) and stopped there, without checking
`session/operations.py`, a separate module in the same package that provides operations *as log
events* rather than as `SessionLog` methods (see that module's own docstring: "none of these can be
a method that edits history").

**Implementation:** `AgentInstance.reset()` now calls `reset_session_log(self.log)` (imported as
`from ..session import reset as reset_session_log`) after clearing runtime state and both queues.
`AgentInstance.messages` reads `()` immediately after, while `len(instance.log)` grows (full history
retained underneath, per `session.reset`'s own contract) --
`test_reset_clears_messages_via_the_session_reset_marker`,
`test_reset_preserves_full_history_for_audit_after_clearing_the_projection`. RED proven directly:
reverting the one-line `reset_session_log(self.log)` call reproduced the failure
(`assert instance.messages == ()` failed with the message still present) before restoring it.

**Wake-on-reset, specified normatively (not previously stated at all):** `reset()` does not clear
`Inbox.wake_requested`. This was already true of the code (delegating to `clear_all()`, which never
touches wake), but nothing said so as a deliberate contract; `test_reset_does_not_clear_a_pending_
wake_signal` now pins it, and both `spec/agent.md`'s "Reset" section and manifest `AG-016` state it
explicitly.

**Tools sub-finding:** confirmed directly -- `AgentInstance` had no `tools` attribute or property at
all before this pass; the prior "adopted" disposition rested on `ToolRegistry.visible_from(scope)`
existing *somewhere*, not on any Agent-level accessor actually calling it. `AgentInstance.tools`
(new property) closes this: `self._ctx.tools.visible_from(self.scope.key)`, resolved the same way
`AgentLoopFactory.for_instance` already resolves `ctx.tools` when composing a driver --
`test_tools_projects_the_tool_registry_visible_from_this_instances_scope`,
`test_tools_reflects_registrations_made_after_construction`.

**Status: RESOLVED** (reset/messages fully; tools accessor added).

## L07-R004 — schema ambiguity; missing clear-all evidence

**Schema, re-audited directly:** confirmed the bug by constructing a two-operation action
(`{"steer": {...}, "follow_up": {...}}`) against the unmodified schema and observing zero validation
errors -- the RED state. `$defs.action` had `minProperties: 1` but nothing preventing more than one
of the six operation keys from co-occurring.

**Implementation:** added an `oneOf` over `required: ["steer"]` / `["follow_up"]` / `["inject"]` /
`["claim"]` / `["clear"]` / `["has_queued_messages"]` to `$defs.action`. A document naming two
operation keys now matches more than one branch (rejected by `oneOf`'s exclusivity); a document
naming zero matches none (also rejected). The review's own required action went further than bare
exclusivity: "`observe` constrained to claim/pending operations" -- the four enqueue/clear branches
additionally carry `"not": {"required": ["observe"]}`, so an action combining e.g. `steer` with
`observe` also matches zero branches (an enqueue/clear operation has no pinned-Pi return value to
observe in the first place, per the field's own pre-existing docstring -- that rule is now
schema-enforced, not merely documented). Re-ran the original two-operation probe: now 1 error.
Confirmed both existing canonical scenarios still validate unchanged, and added permanent regression
coverage to `test_schema_validation.py`: `test_agent_inbox_action_rejects_ambiguous_or_empty_
operations` (three parametrized negative fixtures) / `test_agent_inbox_action_accepts_exactly_
one_operation` (positive counterpart) for exclusivity, and `test_agent_inbox_action_rejects_
observe_on_enqueue_or_clear_operations` (four parametrized negative fixtures) / `test_agent_inbox_
action_accepts_observe_on_claim_or_pending_operations` (two positive fixtures) for the `observe`
constraint.

**Clear-all canonical evidence:** confirmed directly that `agent-inbox-queue-independence-and-
clearing.yaml` never actually exercised `clear: {queue: all}` despite `AG-013`'s own citation
claiming it did. Extended the same file (not a new one, since it is already the clearing-focused
scenario) with a second round: repopulate both queues, `clear: {queue: all}`, confirm
`has_queued_messages` is now false. The runner's existing `clear`/`all` branch
(`agent_inbox_runner.py`) required no changes -- it already called `inbox.clear_all()` correctly; only
the fixture had never invoked that branch.

**Status: RESOLVED.**

## L07-R005 — AG-015 disposition split; wake-on-reset

**Re-audited directly:** the review's complaint was structural, not about any individual sub-fact --
AG-015's single `disposition: adopted` value covered `messages` (an intentional divergence:
projection vs. live reference), `tools` (an intentional divergence: no wholesale-replace setter,
plus the missing accessor above), `streamingMessage`/`pendingToolCalls`/`errorMessage` (deferred
parity: initial values only, transitions deferred to Layer 08), and `wake_requested`/`take_wake` (not
Pi parity at all -- a Minion-only extension) -- four genuinely different dispositions bundled under
one field.

**Manifest split:** AG-015 now covers `isStreaming` only (`disposition: adopted`, unchanged
correctness, just narrowed scope). Three new rows: `AG-017` (`messages`/`tools` projections,
`disposition: intentional divergence`), `AG-018` (runtime-field vocabulary/initial values,
`disposition: deferred parity`), `AG-019` (wake signal, `disposition: intentional divergence`, the
closest available taxonomy value for "no Pi rule exists to be parity with"). `AG-016` gained the
wake-on-reset normative statement (see L07-R003 above).

**Status: RESOLVED.**

## L07-R006 — isStreaming write-point sentence

**Re-audited directly against `agent.ts`:** the review is correct. `createMutableAgentState`'s own
initial value for `isStreaming` is `false` (construction), and `Agent.reset()` sets it back to
`false` when idle (already documented at AG-016) -- both are code paths that assign `isStreaming`,
contradicting the prior sentence "No other code path in pinned Pi ever assigns `isStreaming`."

**Fix:** `spec/agent.md`'s "Public processing status" section now scopes that sentence to the
active-run lifecycle specifically ("Pi's own two *active-run-lifecycle* `isStreaming` transition
points..."), followed by a new paragraph naming the two non-run-lifecycle assignment points
(construction, reset) and noting both are already Layer-07-owned, not Layer-08 territory.

**Status: RESOLVED.**

## Manifest delta

```text
AG-015  narrowed: isStreaming only (disposition unchanged: adopted)
AG-017  NEW: messages/tools public projections, split out of the old AG-015 (L07-R005)
AG-018  NEW: runtime-field vocabulary/initial values, split out of the old AG-015 (L07-R005)
AG-019  NEW: wake signal, split out of the old AG-015 (L07-R005)
AG-016  corrected: messages-clearing resolved (was classified as an open dependency), wake-on-reset
        specified normatively, tests/python citations updated
AG-013  unchanged text, now factually true: its clear-all canonical citation is backed by an actual
        clear-all step in agent-inbox-queue-independence-and-clearing.yaml
```

Total: 75 rows (was 72), 75 unique IDs, confirmed by direct parse. `AG-001`..`AG-010` untouched.

## RED → GREEN (this pass)

```text
test_reset_clears_messages_via_the_session_reset_marker                  RED -> GREEN
test_reset_preserves_full_history_for_audit_after_clearing_the_projection  (positive, no prior RED
                                                                             needed -- new behavior)
test_reset_does_not_clear_a_pending_wake_signal                          GREEN already (pins existing
                                                                             behavior normatively)
test_messages_reflects_events_actually_appended_to_the_log               GREEN already (new positive
                                                                             coverage, not a defect)
test_tools_projects_the_tool_registry_visible_from_this_instances_scope   RED -> GREEN
test_tools_reflects_registrations_made_after_construction                RED -> GREEN
test_agent_inbox_action_rejects_ambiguous_or_empty_operations (x3)       RED -> GREEN
test_agent_inbox_action_accepts_exactly_one_operation                     GREEN already (positive
                                                                             counterpart)
test_agent_inbox_action_rejects_observe_on_enqueue_or_clear_operations (x4)  RED -> GREEN
test_agent_inbox_action_accepts_observe_on_claim_or_pending_operations (x2)  GREEN already (positive
                                                                             counterpart)
```

RED confirmed directly for the two genuine defects this pass fixes: (1) the schema ambiguity --
constructing a two-operation action against the unmodified schema and observing zero errors before
the `oneOf` fix; (2) reset/messages -- reverting the one-line `reset_session_log(self.log)` call and
re-running `test_reset_clears_messages_via_the_session_reset_marker` reproduced the exact failure
(`instance.messages` still contained the message) before restoring the fix. The `tools` property and
the manifest/spec corrections are additive surface (nothing previously claimed a runtime contract a
test could regress against), so they have no meaningful prior RED beyond "the accessor did not
exist, so calling it raised `AttributeError`" -- reported as such rather than manufacturing a
different kind of failure.

## Quality gates (final, this pass)

```text
full pytest (coverage enabled):     966 passed, 19 xfailed, 0 failed, 100.00% coverage
                                     (was 950 at the start of this pass)
ruff check .:                        All checks passed
ruff format --check (touched files only): clean (7 pre-existing, unrelated files elsewhere in the
                                     tree would be reformatted; none touched by this pass, left as
                                     found per the surgical-changes discipline)
mypy (configured scope + typing fixtures): Success, no issues found in 59 source files
schema validation:                   179 passed (was 169; +10: 3 negative + 1 positive fixture for
                                      operation exclusivity, 4 negative + 2 positive fixtures for the
                                      `observe` constraint)
manifest parse + unique-ID audit:    75 / 75 unique (was 72; +3: AG-017/018/019)
Layer-07 canonical (unchanged count, extended content): 2 discovered / 2 executed / 2 passed / 0
                                      deferred -- agent-inbox-queue-independence-and-clearing.yaml
                                      now exercises 6 actions more than before (clear-all round)
```

## Active findings (after this pass)

```text
PI_PARITY_DEFECT              none
CONTRACT_ASSURANCE_DEFECT     none
PI_BEHAVIOR_UNCERTAIN         none
PARITY_CONSTRAINED_RISK       none blocking
```

No classified cross-layer dependency remains open: the one PASS 2.5 left open (message-clearing on
reset) is now fully resolved via the already-certified `session.reset()` mechanism, not superseded
by a new one.

## Verdict (supersedes this document's own PASS-2.5 verdict above)

```text
L07-R003    RESOLVED (fully -- messages-clearing closed; tools accessor added; wake-on-reset
             specified normatively)
L07-R004    RESOLVED (schema ambiguity closed; clear-all canonical evidence added)
L07-R005    RESOLVED (AG-015 split into four coherent, non-contradictory dispositions)
L07-R006    RESOLVED (isStreaming write-point sentence corrected)

Shared Layer-07 contract    READY FOR REPEAT INDEPENDENT RUST REVIEW
Python Layer 07              RE-CERTIFIED
Rust Layer 07                 BLOCKED / PENDING REVIEW
Layer 07 cross-language       NOT CLOSED
Layer 08                       NOT STARTED
```

## Next action

Repeat independent Rust Layer-07 contract review of this corrected candidate. Do not implement Rust
Layer 07 and do not start Layer 08 in this same pass.
