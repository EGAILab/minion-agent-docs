# Layer 09 — Rust agreement on the L09-R007 convergence contract

**Mode:** targeted convergence checkpoint review (`agent-workflow.md` §11.8.5)

**Verdict:** `CONVERGENCE CONTRACT — AGREED FOR IMPLEMENTATION`

## Exact remote state reviewed

- code PR: `EGAILab/minion-agent#17` at
  `f13ee17404aa0c1a65b3a8c1c1d622340713f929`
- docs PR: `EGAILab/minion-agent-docs#26` at
  `93b21fd9bc6f1c471c040bdd5128650b0f75c65f`
- checkpoint revision 2:
  `assurance/layers/09-active-abort-contract-checkpoint-r007-convergence.md`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- revision-1 Rust challenge: docs PR #32 at
  `17cdfb61b4996206a75baececb3c50d0dcf5130b`

Both candidate SHAs were fetched and verified remote-reachable. PRs #17 and #26 were open,
Ready for Review, and matched coordination issue `EGAILab/minion-agent#16`, which named Codex as
the next owner for this checkpoint review.

## Independent source verification

Pinned Pi `packages/agent/src/agent.ts` was re-read at `PendingMessageQueue`, `Agent.continue()`,
`runPromptMessages()`, `runContinuation()`, `runWithLifecycle()`, and `finishRun()`.

The revision-2 source account is correct:

- assistant-last `continue()` destructively drains steering or follow-up before entering
  `runWithLifecycle()`;
- `PendingMessageQueue.drain()` removes either the first item or the complete current queue;
- Pi has no fallible synchronous status-notification extension between that drain and executor
  entry;
- Minion's added synchronous `AGENT_STATUS` / `on_status_change` surface creates the failure case,
  so its rollback behavior is a Minion architectural contract rather than a directly copied Pi
  branch.

## Revision-2 challenge closure

The previously missing preclaim dimension is now fully stated as observable behavior:

- no claimed envelope is lost or duplicated when RUNNING publication fails;
- envelope ID, message, origin, and target are retained;
- the restored claimed prefix precedes later same-target input enqueued by the failing observer;
- queue pending/wake state remains coherent;
- retry observes the original envelopes exactly once;
- steering and follow-up `continue_()` branches and the Minion `run_until_idle()` pump are covered;
- `ONE_AT_A_TIME` and `ALL` are covered;
- direct `prompt()` is correctly excluded because it does not claim from Inbox.

The four new witnesses are discriminating and, together with revision 1's four status/signal
witnesses, cover the remaining L09-R007 surface sufficiently for one coherent implementation pass.

## Agreed implementation constraints

The mechanism remains implementation-owned, with these constraints:

1. If destructive removal is delayed until after RUNNING notification, the membership of the
   entering batch must nevertheless be fixed at the original Pi-equivalent pre-drain boundary.
   A naïve post-notification `ALL` claim must not absorb a new message enqueued by a successful
   status observer. Retaining/restoring the exact claimed batch is the simpler valid option, but
   is not mandated.
2. “Same identity, not a copy” means the same semantic envelope identity—especially the exact
   envelope ID/message/origin—not language-specific object-address identity.
3. Retry witnesses must disable/remove the deliberately failing observer before retrying; the
   retry assertion tests restored input, not repeated observer failure.
4. Rollback must remain local to the failed run-entry attempt. It must not undo unrelated
   side effects performed by the observer or impose cross-target ordering where the Inbox contract
   deliberately defines none.

These constraints refine implementation/evidence interpretation without changing revision 2's
observable rule.

## Lower-layer and Rust feasibility

No lower-layer semantic reopen is required. Layer 07's Inbox remains the sole queue authority;
Layer 09 needs only a rollback-capable operation or a run-entry ownership pattern that preserves
the certified envelope/FIFO semantics.

Rust can implement the agreed behavior idiomatically with an owned claimed batch and explicit
commit/rollback guard. The status/signal state can be settled without holding internal locks across
listener dispatch. No Python scheduler or object-identity mechanic is part of the contract.

## Finding status

```text
L09-R007
    CONTRACT SURFACE AGREED FOR IMPLEMENTATION
    not yet provisionally closed; implementation and all eight witnesses still required

L09-R008
    PROVISIONALLY CLOSED, unaffected

L09-R009
    PROVISIONALLY CLOSED, unaffected

PI_BEHAVIOR_UNCERTAIN
    none

PI_PARITY_DEFECT
    none in the agreed contract

CONTRACT_ASSURANCE_DEFECT
    none in the agreed L09-R007 checkpoint
```

## Convergence checkpoint

```text
CONVERGENCE CONTRACT
    AGREED FOR IMPLEMENTATION

OPEN FINDING
    L09-R007

ACCEPTANCE WITNESSES
    tests/agent_loop/test_active_abort.py
        four status/signal failure witnesses from revision 1
        four preclaimed-input restoration witnesses from revision 2

NORMATIVE DELTAS
    minion-agent-docs/spec/agent.md
    minion-agent/pi-parity-manifest.yaml, AG-007
    minion-agent/pi-parity-manifest.yaml, AG-011 cross-reference only

NEXT OWNER
    Claude
```

Claude may now implement the agreed L09-R007 surface in one coherent pass, RED-prove and retain all
eight witnesses, synchronize the specified normative/evidence artifacts, and hand the exact remote
candidate back for targeted finding-closure review. This agreement is not final Layer-09 approval,
does not authorize Rust Layer-09 implementation, and does not start Layer 10.
