# Layer 09 — Rust challenge of the L09-R007 convergence checkpoint

**Mode:** contract-convergence challenge review only (`agent-workflow.md` §11.8.4–§11.8.5)

**Verdict:** `CONVERGENCE CONTRACT — REVISION REQUIRED`

**Open finding:** `L09-R007`

## Exact remote state reviewed

- code PR: `EGAILab/minion-agent#17` at
  `f13ee17404aa0c1a65b3a8c1c1d622340713f929`
- docs PR: `EGAILab/minion-agent-docs#26` at
  `eb844759470e98a8781c5a55d85734187e5957d5`
- proposed checkpoint:
  `assurance/layers/09-active-abort-contract-checkpoint-r007-convergence.md`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- preceding targeted Rust review: docs PR #31 at
  `054de61af0632c1ca9ddc84b4dcdfb2ddf0fe063`

Both candidate PR heads were fetched, were remote-reachable, open, Ready for Review, and
matched coordination issue `EGAILab/minion-agent#16`. The issue named `Codex` as `NEXT_OWNER`
and `CONTRACT_CONVERGENCE` as the status.

## Pi/source audit

Pinned Pi `packages/agent/src/agent.ts` was re-read at `Agent.continue()`,
`runPromptMessages()`, `runContinuation()`, and `runWithLifecycle()`.

The checkpoint's central source conclusion is correct: Pi installs `activeRun` and writes
`isStreaming` with ordinary non-listener-bearing assignments outside the executor `try`.
`finishRun()` likewise performs ordinary settlement writes. Pi has no Minion-equivalent
synchronous status-observer failure surface, so the policy is necessarily a Minion architectural
mapping rather than a rule directly derivable from Pi.

Pi also establishes a dependency the proposed checkpoint omits: when the transcript ends in an
assistant message, `Agent.continue()` drains steering or follow-up **before** calling
`runWithLifecycle()`. In Pi this does not create the reviewed failure case because run entry has no
throwing observer. Minion follows the same pre-drain shape, but its added synchronous RUNNING
notification can throw after the drain and before `_execute_run()` begins.

## Agreed portions of the proposed policy

The proposed asymmetry is coherent for state that `_run_wrapped` itself owns:

- a RUNNING-notification failure occurs before a Pi-equivalent run lifecycle begins;
- the new controller/signal is discarded;
- status is restored to `IDLE` without recursively publishing the same failing notification;
- no fabricated `agent_start` or synthesized failure lifecycle is emitted;
- the original observer exception propagates;
- an IDLE-notification failure occurs after the run outcome is committed;
- signal, streaming message, pending tool calls, and status are settled before the final,
  possibly-throwing IDLE notification;
- the committed outcome is retained and the notification exception propagates separately.

The fail-fast ordering among `AGENT_STATUS` listeners and `on_status_change` is also sufficiently
specified.

These portions are accepted as the basis for a revised checkpoint. They are not yet an agreed
checkpoint because the entry rollback matrix is incomplete.

## Blocking challenge: preclaimed inbox input is outside the rollback matrix

### Classification

`CONTRACT_ASSURANCE_DEFECT` within open finding `L09-R007`.

### Current candidate path

At the exact code SHA:

```text
continue_(), assistant-last transcript
    claim NEXT_STEP, else claim NEXT_TURN
    -> _run_wrapped(...)
        _start_run_signal()
        set_status(RUNNING)  # synchronous observer may throw
        _execute_run(...)    # never reached

run_until_idle()
    claim NEXT_TURN
    -> _run_wrapped(...)
        same failure point
```

`Inbox.claim()` destructively removes the selected prefix. `_run_wrapped` receives only projected
messages and provenance values, not the claimed envelopes or their queue target. The proposed
rollback restores status/signal only. It neither defines nor provides an acceptance witness for
the already-claimed input.

This matters because the checkpoint explicitly defines the failed RUNNING transition as a run
that "never validly started" and requires no run lifecycle or provider request. Silently consuming
the run's entering inbox messages is an additional externally observable effect that contradicts
that failure-atomicity description unless it is explicitly chosen and governed.

### Executed discriminating witness

Setup against the real PASS-4 candidate seam:

1. complete one prompt so the transcript ends in an assistant message;
2. enqueue one steering envelope and retain its ID;
3. install `on_status_change` that raises on `RUNNING`;
4. call `continue_()`;
5. observe the inbox and provider request count.

Observed at `f13ee17404aa0c1a65b3a8c1c1d622340713f929`:

```text
raised                 RuntimeError("status-boom")
NEXT_STEP pending      0
claimed ID present     false
provider request count unchanged
```

The current candidate also retains the already-known pre-convergence defect (`status=RUNNING`,
live signal); the checkpoint proposes to repair those two values. That proposed repair would not
restore the envelope, so this witness discriminates the incomplete checkpoint rather than merely
restating the current implementation defect.

### Required semantic decision

Revise the RUNNING-failure matrix to cover resources acquired before `_run_wrapped`, at minimum:

- assistant-last `continue_()` with pre-drained steering;
- assistant-last `continue_()` with pre-drained follow-up;
- Minion-only `run_until_idle()` with a preclaimed follow-up;
- both `ONE_AT_A_TIME` and `ALL` claims where ordering differs;
- an observer that enqueues another message at the same target before throwing.

The recommended rule, consistent with "the run never validly started," is:

```text
RUNNING notification fails
    -> no claimed entering envelope is lost or duplicated
    -> original envelope identity/message/origin are retained
    -> restored input precedes input enqueued later by the failing observer
    -> wake remains consistent with pending input
    -> retry observes the same FIFO claim behavior
```

The implementation may satisfy this by delaying destructive claim until entry publication succeeds
or by rolling back the exact claimed envelopes. The shared contract should specify the observable
result, not mandate either mechanism. If the project instead deliberately chooses consumption on
failed entry, that is a separate observable Minion policy and must be stated explicitly rather than
implied by silence; it would not be failure-atomic in the ordinary meaning used by this checkpoint.

## Required acceptance witnesses

Add discriminating witnesses alongside the checkpoint's four status/signal witnesses:

1. `continue_()` preclaims steering `A`; RUNNING observer throws; afterward `A` remains pending
   with the same envelope ID/origin, no lifecycle/provider work occurred, and a retry can consume
   `A` exactly once.
2. Same for preclaimed follow-up.
3. With claim policy `ALL`, queue `A,B`; the RUNNING observer enqueues `C` then throws; afterward
   the queue is `A,B,C`, proving restoration does not append the older claimed prefix behind new
   input.
4. `run_until_idle()` preclaims a follow-up and entry publication fails; content remains pending
   and wake/content state is coherent for a later pump.

Each must be RED-proven against the unchanged candidate or a partial status/signal-only
implementation, then retained as permanent regression evidence.

## Rust implementability

Both the accepted state policy and the required input-atomicity rule are implementable
idiomatically in Rust. Neither requires a lower-layer semantic reopen. Rust can delay ownership
transfer until run entry commits or retain an owned claimed batch and restore it on entry failure.
The inbox remains the sole queue authority either way.

The checkpoint's RAII discussion should not say the signal was never published to the rest of the
type system: the failing RUNNING observer is explicitly allowed to observe and abort that live
signal. The relevant guarantee is that the signal is discarded before control returns to the
caller. This is documentary precision, not a separate blocker.

## Finding status and verdict

```text
L09-R007
    STILL OPEN — CONVERGENCE CHECKPOINT INCOMPLETE

PI_BEHAVIOR_UNCERTAIN
    none

PI_PARITY_DEFECT
    none on the newly identified Minion-only observer policy surface

CONTRACT_ASSURANCE_DEFECT
    RUNNING-entry rollback omits already-claimed inbox inputs

CONVERGENCE CONTRACT
    REVISION REQUIRED
```

`L09-R008` and `L09-R009` remain provisionally closed and are not reopened by this challenge.

## Next action

Claude should revise the L09-R007 convergence checkpoint with the preclaim/input behavior matrix
and acceptance witnesses above. No implementation should begin until the revised checkpoint is
independently agreed under §11.8.5. Rust Layer 09 remains unimplemented; Layer 10 is not started.
