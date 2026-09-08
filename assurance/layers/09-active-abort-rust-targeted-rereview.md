# Layer 09 PASS 2 — targeted independent Rust finding-closure review

**Verdict:** REJECTED. PASS 2 closes three findings and implements the missing surfaces for two
others, but it does not preserve the authoritative per-run signal across raw waterfall listener
boundaries. The same defect is stated as permitted behavior in the normative spec and manifest.
Rust Layer 09 remains blocked; this review does not implement Rust or start Layer 10.

## Exact reviewed state

- code PR: `EGAILab/minion-agent#17`
- exact code head: `ee24b8d03bdd4ed26e22356165fe4809be07ec05`
- docs PR: `EGAILab/minion-agent-docs#26`
- exact docs head: `5474cf1fdea345438920500a55f9f7032ff16cdc`
- rejected PASS-1 code head: `b5e44bb780e67dc8fccd27f630ce8d783b11303c`
- rejected PASS-1 docs head: `fdf4d3860d875cb4e800bba01784e22f7ba79ee4`
- PASS-1 Rust review: docs PR #27 / commit
  `0a781d3f6710d633f9fcf4c10ef11422dfeef1ee`
- accepted shared baseline: code `3ec1a386c86a93a13344ed38d796fbb74e9817bd`, docs
  `ecb809798b7437045e1325683306c3f15f46571e`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- coordination issue: `EGAILab/minion-agent#16`, received as `RUST_CONTRACT_REVIEW`,
  `NEXT_OWNER = Codex`

Both candidate heads were fetched, were remote-reachable, matched issue #16, were Ready for
Review, and were open/unmerged. Untracked `.worktrees/` entries were preserved.

This is the workflow section 11.8.7 targeted finding-closure review. It rechecked L09-R001 through
L09-R005, the directly touched event-waterfall boundaries, and the already-closed C001/C002 batch
and priority rules. It is not the final complete section 11.8.8 review.

## Authority and targeted Pi re-audit

Pinned Pi was read first:

- `packages/agent/src/agent.ts`: `Agent.signal`, `Agent.abort`, `runWithLifecycle`,
  `handleRunFailure`, `processEvents`;
- `packages/agent/src/agent-loop.ts`: `streamAssistantResponse`, `prepareToolCall`,
  `executePreparedToolCall`, `finalizeExecutedToolCall`, and batch abort checks;
- `packages/agent/src/types.ts`: `transformContext`, before/after hooks, and
  `AgentTool.execute`.

Pi supplies one stable, read-only `AbortSignal` from its private run controller to each consumer.
The hook and transform callbacks may transform their documented semantic value, but they have no
authority to replace the run's signal for a later consumer. `handleRunFailure` classifies using
the signal's live `aborted` state. Signal and update are independent optional tool capabilities.

## Finding closure ledger

### L09-R001 — signal delivery to tool hooks

PASS 2 adds `signal` to the real `TOOLS_PRE_EXECUTE` and `TOOLS_POST_EXECUTE` dispatch payloads.
The first raw listener at each seam observes the supplied signal and the ordinary single-listener
tests pass.

The repair is incomplete for Minion's public N-listener waterfall extension. A raw listener can
delegate with an explicit replacement payload containing another `RunSignal`, and the next
listener observes that replacement. It can also omit the trailing signal, causing the next
listener to receive no signal or fail by arity. The production `_finalize.normalize_step` preserves
whatever trailing payload the prior listener supplied instead of restoring the authoritative
signal; pre-execute has no normalization boundary at all.

**Status:** `PARTIALLY_RESOLVED_BLOCKING`.

### L09-R002 — failure classification after abort

`_settle_run_failure` now reads `instance.signal.aborted` at the recovery classification point.
The exact unrelated-exception-after-abort witness produces `StopReason.ABORTED`, while the paired
non-aborted exception remains `StopReason.ERROR`. This matches
`runWithLifecycle -> handleRunFailure(error, abortController.signal.aborted)`.

**Status:** `PROVISIONALLY CLOSED @ ee24b8d03bdd4ed26e22356165fe4809be07ec05`.

### L09-R003 — signal-only tools

`ToolDefinition.wants_signal` makes signal selection independent from the pre-existing update-only
arity convention. The four combinations are representable: neither, update-only, signal-only,
and signal-plus-update. The signal-only and update-only regressions pass, and the typed Rust Layer
06 request already represents signal and update independently.

**Status:** `PROVISIONALLY CLOSED @ ee24b8d03bdd4ed26e22356165fe4809be07ec05`.

### L09-R004 — signal authority and stable identity

The public surface is materially repaired: `AgentInstance.signal` is a read-only property,
consumers receive `RunSignal` without a public `abort()`, and only the instance-held controller is
used by `AgentInstance.abort()`. Idle and per-run lifecycle behavior remains correct.

Authority is nevertheless still replaceable inside the public raw waterfall seams. The exact
executable witness below redirected both a later before-hook and a later after-hook from the
original active signal to a caller-created replacement while execution still succeeded. The same
mechanism applies to `AGENT_TRANSFORM_CONTEXT`. Stable Agent-property identity therefore does not
establish stable consumer identity.

**Status:** `PARTIALLY_RESOLVED_BLOCKING`.

### L09-R005 — transformContext

The candidate now has a real per-request `AGENT_TRANSFORM_CONTEXT` seam immediately before request
construction. Its message output is provider-local, is invoked again from untransformed run
history on the next request, and never enters the persistent transcript. The first listener
receives the active signal. This closes the original omission and is independently implementable
in Rust.

Its multi-listener signal metadata is affected by L09-R006 below, but the transform-context
semantic surface itself is present and correct.

**Status:** `PROVISIONALLY CLOSED @ ee24b8d03bdd4ed26e22356165fe4809be07ec05`,
subject to the shared signal-authority blocker.

## New blocking finding

### L09-R006 — waterfall listeners can replace or drop authoritative signal metadata

**Classification:** `PI_PARITY_DEFECT` in production and `CONTRACT_ASSURANCE_DEFECT` in the
written shared contract.

The current normative consumer matrix says the **same** per-run signal reaches every consumer.
But `spec/tools.md` lines 304-314 and `TOOL-024` explicitly say a transforming listener must
re-supply the signal and that forgetting it degrades to “no signal for later listeners.”
`AgentLoop._transform_context` documents the same convention. Thus the candidate both requires
stable signal identity and authorizes listeners to remove or redirect it.

Executable witness against the exact code SHA:

```text
tools/pre-execute
    listener A delegates (call, definition, arguments, replacement_signal)
    listener B observes replacement_signal
    result_error = false

tools/post-execute
    listener A delegates (result, replacement_signal)
    listener B observes replacement_signal
    result_error = false
```

Observed output:

```text
tools/pre-execute is_original=False is_replacement=True result_error=False
tools/post-execute is_original=False is_replacement=True result_error=False
```

This is discriminating. A listener holding only a read-only signal can still redirect all later
listeners to a different signal, including one with a different aborted state. Pi's single hook
cannot replace the run signal, and Minion's N-listener extension cannot call every listener a
consumer of the same signal while allowing an earlier listener to rewrite that metadata.

**Required narrow remediation:** make the run signal authoritative event metadata at every
listener-to-listener boundary for `TOOLS_PRE_EXECUTE`, `TOOLS_POST_EXECUTE`, and
`AGENT_TRANSFORM_CONTEXT`. A listener may transform only the semantic value owned by that
waterfall (arguments/decision, result override, or messages); the dispatcher must restore the
original signal if a raw listener omits or replaces it. Keep generic `EventBus.waterfall` defaults
unchanged and use event-specific normalization/wrappers. Add raw-to-raw and raw-to-helper tests
where listener A drops and replaces signal and listener B must observe the original exact object.
Synchronize spec and manifest so they no longer instruct callers to re-supply authoritative
signal metadata.

## C001/C002 and touched-boundary regressions

- C001 batch split: remains correct. Sequential and parallel algorithms retain their different
  poll points; the A/B/C regressions pass.
- C002 priority: remains correct. Unknown/validation/hook-throw outcomes beat abort; abort after a
  successfully returning hook beats its returned block/proceed result.
- generated error/after-hook reachability and Layer-06 ordering tests pass.
- transform-context remains provider-local and per-request.
- no forced task cancellation or Layer-10 work was introduced.

## Evidence and gates

```text
focused runtime/agent/tools/agent-loop tests
    102 tests passed; pytest process failed only because a deliberately partial run cannot meet
    the repository-wide 100% coverage threshold

full Python suite
    1083 passed, 19 xfailed, 0 failed

coverage
    100.00% (2785/2785 statements)

ruff
    PASS

mypy src
    PASS (58 source files)

manifest parse/uniqueness
    79 rows / 79 unique IDs

Layer-09 canonical
    three placeholders; 0 executable and none counted as passing evidence
```

Green gates confirm the tested implementation but do not cover the two-listener replacement
witness above.

## Rust feasibility

The narrow repair does not require a certified-layer redesign. Rust can keep its read-only signal
handle outside transformable waterfall values and pass the authoritative handle independently to
each listener. Python can use the existing opt-in `normalize_step` mechanism or an event-specific
wrapper. Runtime's default EventBus semantics need not change. Layer-02 request and Layer-06 tool
request changes remain additive Layer-09 deltas.

## Verdict and next action

```text
PI_BEHAVIOR_UNCERTAIN
    none

PI_PARITY_DEFECT
    L09-R001 / L09-R004 remain partially resolved because later raw listeners can receive a
    replaced or missing signal
    L09-R006 authoritative signal metadata is replaceable across waterfall boundaries

CONTRACT_ASSURANCE_DEFECT
    L09-R006 normative spec/manifest contradict stable same-signal delivery

PARITY_CONSTRAINED_RISK
    none

shared Layer-09 contract
    REJECTED FOR RUST IMPLEMENTATION

Python Layer 09
    REOPENED

Rust Layer 09
    BLOCKED / NOT_IMPLEMENTED

Layer 09 cross-language
    NOT CLOSED

Layer 10
    NOT STARTED
```

Return to the Python/shared owner for the narrow authoritative-signal normalization above. Any
new candidate SHA requires another targeted section 11.8.7 review. After every finding is
provisionally closed, perform exactly one final complete exact-SHA review under section 11.8.8.
