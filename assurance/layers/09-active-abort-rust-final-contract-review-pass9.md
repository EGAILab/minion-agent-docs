# Layer 09 active abort — final independent Rust contract review (PASS 9)

## Verdict

**REJECTED FOR RUST IMPLEMENTATION.**

The exact candidate reviewed was:

- code PR `EGAILab/minion-agent#17` at
  `e015c20c25b3506372c1887a6f7b079a7f8d9e7a`;
- docs PR `EGAILab/minion-agent-docs#26` at
  `7012b28ee5b8784a8b72367afd294a1b2b1ad99c`;
- pinned Pi at `b7bb00b936dbe21b8e160b3e89efdec361846699`.

Both candidate commits were fetched from GitHub and matched coordination issue
`EGAILab/minion-agent#16`. At review start both candidate PRs were open, ready for review,
mergeable, and unmerged; the issue recorded `STATUS = RUST_CONTRACT_REVIEW` and
`NEXT_OWNER = Codex`. The PASS-9 targeted closure remains separately preserved in docs PR
#37 at `cf76b4ed821acba8f395f9602863e5b2c15a4ebe`.

This is the mandatory workflow §11.8.8 final complete review. It changes no candidate,
shared semantic, Python, or Rust implementation file.

## Authority and independent source audit

The review used the required order: pinned Pi, normative specification, parity manifest,
canonical evidence, certified Rust architecture, assurance, then Python only as secondary
implementation evidence.

Pinned Pi files and symbols re-read directly:

- `packages/agent/src/agent.ts`: `ActiveRun`, `Agent.signal`, `abort`, `prompt`,
  `continue`, `createLoopConfig`, `runWithLifecycle`, `handleRunFailure`, `finishRun`, and
  `processEvents`;
- `packages/agent/src/agent-loop.ts`: `streamAssistantResponse`, `transformContext`, loop
  continuation callbacks, sequential and parallel tool batches, `prepareToolCall`,
  `executePreparedToolCall`, and finalization;
- `packages/agent/src/types.ts`: Agent callbacks, tool request/update, signal, hook, and
  lifecycle types;
- relevant pinned tests and call sites for abort, signal identity, callback delivery, and
  tool-batch truncation.

The source reconfirms the accepted core contract: one controller/read-only signal per run;
Agent-only abort authority; cooperative rather than forced cancellation; the same signal at
transform/provider/tool/continuation consumers; the agreed preflight priority and distinct
sequential/parallel batch algorithms; represented-aborted versus exception settlement; and
transport cancellation remaining a later provider concern.

## Complete prior-finding ledger

| Finding | Final-review result | Independent result |
|---|---|---|
| L09-C001 | CLOSED | Sequential and parallel tool-batch abort algorithms remain separately and correctly specified. |
| L09-C002 | CLOSED | The six-outcome preflight priority remains aligned with pinned Pi. |
| L09-C003 | CLOSED | The consumer matrix, ignore-signal rule, and four terminal distinctions remain complete. |
| L09-R001 | CLOSED | Raw and helper tool hooks receive the active signal. |
| L09-R002 | CLOSED | Failure classification reads the current active signal at settlement. |
| L09-R003 | CLOSED | Neither/update-only/signal-only/both tool capability combinations remain representable. |
| L09-R004 | CLOSED | Public consumers receive a read-only signal and cannot acquire abort authority. |
| L09-R005 | CLOSED AS TO SEAM EXISTENCE | Per-request provider-local `transformContext` exists; the new L09-R018 concerns its multi-listener authority grammar. |
| L09-R006 | **REOPENED BY L09-R018** | Signal replacement/drop is blocked for the tested trailing-signal form, but true omission of the leading authoritative Agent corrupts messages. |
| L09-R007 | CLOSED | Entry status/signal failure policy and rollback behavior match the agreed convergence contract. |
| L09-R008 | CLOSED | The recommended after-tool helper supplies signal when requested. |
| L09-R009 | CLOSED | Superseded signal-authority prose is unmistakably historical. |
| L09-R010 | CLOSED | No unrestricted public restoration/insertion authority remains. |
| L09-R011 | CLOSED | The former peek/commit identity defect is gone with the reservation design. |
| L09-R012 | CLOSED | AG-011 now describes the current reservation mechanism coherently. |
| L09-R013 | CLOSED | A re-entrant observer cannot claim the already-reserved entering batch. |
| L09-R014 | CLOSED | Partial-prefix duplication is structurally removed by reserve-before-observer. |
| L09-R015 | CLOSED | `AGENT_PRE_STEP` and `AGENT_PREPARE_NEXT_TURN` restore redirected and truly omitted Agent identity without shifting transformable fields. |
| L09-R016 | CLOSED | Tool signal-capability prose and evidence are current. |
| L09-R017 | CLOSED | `_Reservation.envelopes` is getter-only and rollback remains bound to the private original tuple. |

The targeted PASS-9 closure witnesses for L09-R015 and L09-R017 were repeated against the
exact candidate and passed. Their provisional closure is confirmed. The complete audit found
one new blocker on the adjacent transform-context authority boundary.

## Requirement and traceability audit

| Row | Pi/shared rule | Evidence and disposition | Rust feasibility / result |
|---|---|---|---|
| AI-027 | LLM request carries the cooperative run signal | Adopted; Python language evidence; placeholder canonical not counted | Additive typed request field; feasible. |
| AG-007 | One signal per run, Agent abort authority, settlement and complete consumer propagation | Adopted; extensive language evidence | Feasible using typed controller/view; blocked by L09-R018 at one consumer boundary. |
| AG-011 | Two FIFO inboxes and exactly-once identity/order | Adopted; direct canonical plus language evidence | Current reservation integration is coherent and feasible. |
| AG-023 | Per-request, provider-local `transformContext(messages, signal)` | Adopted; Python language evidence | **FAIL:** multi-listener normalization can turn the signal into provider messages. |
| TOOL-009 | Tool signal/update capability vocabulary | Adopted/current | Feasible with explicit typed capabilities. |
| TOOL-018 | Layer-06 structural execution-signal seam activated by Layer 09 | Adopted mapping | Existing Rust seam is suitable; no lower-layer reopen. |
| TOOL-024 | Same authoritative signal through tool pre/execute/post and batch polling | Adopted; Python language evidence | Feasible with the certified Rust execution split. |
| PROV-004 | Real transport cancellation | Explicit later provider defer | Correctly outside Layer 09. |

The manifest parses as 79 rows with 79 unique IDs. No unfilled canonical placeholder is
counted as satisfying evidence.

## Canonical evidence

The three Layer-09 scenario files remain explicit placeholders:

- `active-abort-provider.yaml`;
- `active-abort-tool.yaml`;
- `abort-settles-before-idle.yaml`.

The manifest expressly excludes them from current executable evidence. Python language tests
therefore carry the listener-driven Layer-09 evidence. No canonical runner was found
simulating abort, signal, inbox reservation, or transform-context behavior. This evidence
policy remains acceptable and is not the rejection reason.

## New blocking finding

### L09-R018 — transform-context authoritative-position omission corrupts messages

Classification: **PI_PARITY_DEFECT**.

Pinned Pi calls the application seam as `transformContext(messages, signal)`: messages and
the active signal occupy distinct typed positions, and no Agent argument can be omitted into
that tuple. Minion deliberately adds its Agent instance as authoritative architectural
metadata, producing the waterfall payload `(instance, messages, signal)`. Candidate prose
and `_transform_context`'s own docstring say both `instance` and `signal` are restored and
only `messages` is transformable.

The implementation only supports the interpretation “a two-element replacement omitted the
trailing signal”:

```python
def _restore_signal(current):
    current_messages = current[1]
    return (original_instance, current_messages, original_signal)
```

A listener that truly omits the leading authoritative Agent while retaining the two Pi-level
arguments delegates with `next_(messages, signal)`. The normalizer then treats `signal` as
`messages`. A second listener receives the original Agent and original signal, but receives a
`RunSignal` in its messages position; the real provider request likewise receives that
`RunSignal` instead of the message tuple.

The exact real-loop witness against the reviewed SHA observed:

```text
listener_calls                 1
instance_is_original           true
downstream_messages_type       RunSignal
downstream_signal_is_original  true
request_messages_type          RunSignal
Agent.error_message            none
```

This is externally observable provider-input corruption, not a Rust implementation
preference. Existing tests cover full-length signal replacement, but not true leading-Agent
omission.

There is also a contract-expression problem beneath the implementation defect: with a
positional three-field waterfall, a two-field replacement is ambiguous between
`(instance, messages)` (signal omitted) and `(messages, signal)` (Agent omitted). The current
normative prose requires both authoritative values to survive but does not define a
language-neutral delegation grammar that distinguishes those two cases. Two independent
implementations can therefore satisfy the prose while choosing different two-field
interpretations.

Required remediation is narrow but must be agreed before another implementation patch:

1. characterize all transform-context delegation shapes: full payload, omitted Agent,
   omitted signal, and both authoritative fields omitted;
2. define an unambiguous language-neutral representation/normalization rule in which only
   messages are transformable and neither authoritative field can shift into that slot;
3. implement that rule without type/position guessing that admits two valid interpretations;
4. add at least two chained-listener witnesses for true Agent omission and true signal
   omission, asserting original Agent, original signal, unchanged/replaced messages as
   intended, and the real provider request payload;
5. re-audit the other authoritative-metadata waterfalls for the same multi-authoritative-slot
   ambiguity.

Because this is the same authority-normalization mechanism family as L09-R006 and L09-R015
after repeated review cycles, workflow convergence applies. A checkpoint/challenge should
settle the payload grammar before further code changes; the reviewer must not author that
shared repair.

## Whole-contract and architecture audit

The remainder of the complete Layer-09 state-machine audit passed:

- signal installation precedes RUNNING observation and cleanup precedes IDLE observation;
- failed RUNNING notification retains entering input exactly once through a private linear
  reservation; listener-side unrelated effects are not reversed;
- abort is cooperative and cannot forcibly cancel Python tasks;
- failure settlement selects aborted/error from the signal's current state and uses the live
  persistent Agent model;
- transform output is intended to be provider-local and non-persistent;
- provider, tool hooks, tool execution, prepare-next-turn, and turn-stopping consumers receive
  the same run signal;
- sequential and parallel tool batches preserve their distinct Pi ordering and truncation;
- abort does not itself end the run, suppress ordinary continuation policy, or replace the
  already-certified represented-aborted terminal path;
- transport-level cancellation remains deferred to PROV-004;
- no Layer-10 behavior is claimed.

Certified Rust Layers 01–08 already provide typed Agent/Inbox/LLM request structures,
`ToolExecutionSignal`, `ToolExecutionRequest.signal`, lifecycle events, continuation hooks,
and the Layer-08 driver. The intended Layer-09 design remains implementable without reopening
those layers, but Rust must not guess the ambiguous transform delegation rule or copy the
candidate defect.

## Contract-quality answers

- Does a canonical runner simulate production semantics? **No.**
- Does Python contain a workaround solely because the shared contract is incomplete? **Yes at
  AG-023:** positional normalization assumes which authoritative argument was omitted.
- Can Python and Rust both satisfy the written prose while behaving observably differently?
  **Yes:** the two-field transform delegation has two plausible meanings.
- Does the transform-context contract explain authoritative metadata without positional
  corruption? **No.**
- Does any earlier certified layer prevent repair? **No.** This is an Agent event-payload and
  normalization design issue.
- Can Rust otherwise implement the cooperative Layer-09 contract idiomatically? **Yes.**
- Has provider transport cancellation leaked into Layer 09? **No.**

## Fresh evidence gates

Executed against the exact code candidate:

- full Python suite: PASS, 1125 passed and 19 expected failures;
- statement coverage: PASS, 100% (author/full coverage gate);
- `uv run ruff check .`: PASS;
- `uv run mypy src`: PASS (58 source files);
- schema validation: PASS, 185 tests;
- manifest integrity: PASS structurally, 79 rows / 79 unique IDs;
- targeted Inbox/active-abort tests: PASS, 68 tests;
- exact L09-R015 true-omission witness: PASS;
- exact L09-R017 immutable-binding witness: PASS;
- new L09-R018 real-loop witness: **FAIL**, with `RunSignal` delivered as provider messages.

Green aggregate gates do not cover or cure the new semantic witness.

## Taxonomy and final status

Active findings:

- `PI_PARITY_DEFECT`: L09-R018;
- `CONTRACT_ASSURANCE_DEFECT`: the unambiguous delegation grammar required to close L09-R018
  is absent (recorded as part of that finding rather than a duplicate ID);
- `PI_BEHAVIOR_UNCERTAIN`: none;
- blocking `PARITY_CONSTRAINED_RISK`: none;
- `PARITY_NEUTRAL_HARDENING`: none required for this verdict.

Final status:

```text
shared Layer-09 contract
    REJECTED

Python Layer 09
    REOPENED

Rust Layer 09
    BLOCKED / NOT_IMPLEMENTED

Layer 09 cross-language
    NOT CLOSED

Layer 10
    NOT STARTED
```

## Next action

Return to the shared/Python owner for a narrow convergence checkpoint and remediation of
L09-R018. Any candidate SHA change requires a new exact-SHA independent review. Do not
implement Rust Layer 09 and do not start Layer 10.
