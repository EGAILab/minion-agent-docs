# Layer 09 — Rust targeted re-review of PASS 5 L09-R007 implementation

**Mode:** targeted finding-closure review (`agent-workflow.md` §11.8.7)

**Verdict:** `L09-R007 IMPLEMENTATION BEHAVIOR VERIFIED, BUT NOT PROVISIONALLY CLOSED`

## Exact remote state reviewed

- code PR: `EGAILab/minion-agent#17` at
  `92885995d66dce716b69e92793d61e924cb030fc`
- docs PR: `EGAILab/minion-agent-docs#26` at
  `b390c867247179b506847c653bd6060f60c9f636`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- agreed convergence review: docs PR #32 at
  `b410cb9fa1dbb9468b7555ce3c1aa37c9dbd59db`

Both candidate SHAs were fetched and verified remote-reachable. PRs #17 and #26 were open,
Ready for Review, and matched coordination issue `EGAILab/minion-agent#16`, which assigned this
targeted review to Codex.

## Scope

Reviewed the agreed L09-R007 surface and dependencies changed by PASS 5:

- RUNNING-notification failure rollback;
- IDLE-notification failure post-commit settlement;
- steering/follow-up preclaim restoration;
- `ONE_AT_A_TIME` and `ALL` FIFO behavior;
- retry and pump behavior;
- `Inbox.restore()` and AG-011 queue invariants;
- spec, manifest, tests, and PASS-5 assurance updates.

`L09-C001`–`C003`, `L09-R001`–`R006`, `L09-R008`, and `L09-R009` were not reopened except where
the new Inbox operation directly touched AG-011.

## L09-R007 agreed behavior verification

The implementation correctly realizes the agreed run-entry/run-exit behavior:

- the run signal is installed before RUNNING publication;
- a throwing RUNNING observer discards the signal, silently restores internal status to `IDLE`,
  emits no run lifecycle, restores the exact preclaimed batch, and re-raises the original error;
- steering and follow-up `continue_()` paths capture the exact claimed batch and target;
- `run_until_idle()` does likewise for its follow-up batch;
- restoration prepends the claimed prefix ahead of input enqueued during the failing observer;
- retry consumes the restored batch exactly once through the normal driver path;
- successful run-entry claim membership remains fixed at the original pre-notification claim;
- exit clears signal, streaming message, and pending tool calls before publishing IDLE;
- a throwing IDLE observer sees settled state and does not hide the already-committed run outcome.

The twelve new tests were inspected. A fresh targeted run at the exact code SHA executed all tests
in `tests/agent/test_inbox.py` and `tests/agent_loop/test_active_abort.py`: 48 tests passed. The
first run used the repository's global 100%-coverage gate and therefore exited nonzero only because
a two-file subset naturally covers 69% of the whole package; rerunning the same targeted set with
`--no-cov` passed completely. This is not a candidate test failure.

The two disclosed non-RED IDLE witnesses are honestly characterized: they protect the agreed
settlement contract but do not distinguish the old reachable implementation because the affected
fields were already settled by inner paths. No false RED claim remains.

## L09-R010 — unrestricted public restore authority

### Classification

`CONTRACT_ASSURANCE_DEFECT`

### Basis

The convergence contract approved an observable rollback result and deliberately left its
mechanism implementation-owned. It did not approve a new unrestricted caller operation.

PASS 5 adds `Inbox.restore(target, envelopes)` as an ordinary public method on the exported public
`Inbox` type. The method accepts any envelope tuple, tracks no claim ownership, and has no one-shot
guard. A caller can therefore:

- restore an envelope that is still queued and was never claimed;
- restore the same claimed batch multiple times;
- restore an envelope into a different target;
- manufacture duplicate queue entries with the same envelope ID/message/origin.

This directly contradicts AG-011's current certified statement that every sent message is claimed
exactly once and that queue identity/storage semantics are unchanged. The PASS-5 manifest calls
`restore` merely a reader/preserver of those rules, but the public method enlarges the operation
surface and can violate them.

Pinned Pi's `PendingMessageQueue` is private to `Agent`, exposes no restore operation, and cannot be
used by callers to synthesize duplicate queued identity. Minion's `Inbox` is intentionally public,
so method visibility is observable and cannot be dismissed as a Python-only implementation detail.

### Executed discriminating witness

Against the real PASS-5 candidate:

```python
inbox = Inbox()
envelope = inbox.followup(message_a)
inbox.restore(InboxTarget.NEXT_TURN, (envelope,))
assert [item.id for item in inbox.pending(InboxTarget.NEXT_TURN)] == [
    envelope.id,
    envelope.id,
]

inbox.restore(InboxTarget.NEXT_TURN, (envelope,))
assert [item.id for item in inbox.pending(InboxTarget.NEXT_TURN)] == [
    envelope.id,
    envelope.id,
    envelope.id,
]
```

Observed exactly: the same envelope ID appeared twice after the first call and three times after
the second. No claim or failed run-entry was involved. This distinguishes the intended internal
rollback capability from the candidate's new public mutation authority.

### Narrow remediation

Keep the already-correct L09-R007 driver behavior, but make the rollback capability internal to the
Agent/Inbox implementation boundary or otherwise prove it is a one-shot restoration of a batch
actually claimed from that same target. Language-neutral requirements:

```text
ordinary callers cannot invoke rollback restoration as a public Inbox operation
rollback cannot restore an unclaimed batch
rollback cannot restore the same claim more than once
rollback cannot move a claimed batch across targets
normal L09-R007 failed-entry restoration remains exact and FIFO-preserving
```

An internal/private `_restore_claimed(...)` used only by `AgentLoop`, a linear claim token, or an
equivalent idiomatic design is acceptable. Rust should use private or crate-private authority,
not expose unrestricted `pub fn restore`.

Add the executed duplicate-ID witness as permanent negative API/invariant evidence. Update the
spec/manifest/assurance wording so it describes internal rollback capability rather than a newly
adopted public Inbox operation. No Pi semantic or lower-layer reopen is required.

## Contract quality and lower-layer impact

- The status/signal and preclaimed-input observable contract is coherent.
- No runner simulates the behavior.
- The candidate does not require a Layer-01–08 semantic reopen.
- The defect is the visibility/authority of the new mechanism, not the agreed rollback behavior.
- Remediation is parity-neutral and narrowly local to Layer 09's integration with the certified
  Inbox authority.

## Finding ledger

```text
L09-R007
    agreed observable implementation behavior: PASS
    provisional closure: WITHHELD pending L09-R010

L09-R008
    PROVISIONALLY CLOSED, unaffected

L09-R009
    PROVISIONALLY CLOSED, unaffected

L09-R010
    CONTRACT_ASSURANCE_DEFECT
    OPEN

PI_BEHAVIOR_UNCERTAIN
    none

PI_PARITY_DEFECT
    none newly classified; the blocker is Minion public-contract authority
```

## Verdict and next action

```text
PASS-5 TARGETED REVIEW
    REJECTED

L09-R007
    NOT PROVISIONALLY CLOSED

Layer 09 shared/Python candidate
    REMEDIATION REQUIRED

Rust Layer 09
    NOT IMPLEMENTED

Layer 10
    NOT STARTED
```

Claude should narrow restoration to internal/one-shot claimed-batch authority, add the exact
duplicate-ID negative witness, correct current spec/manifest/assurance wording, rerun the agreed
L09-R007 witnesses, and hand new exact SHAs back for targeted review. The mandatory final complete
review remains pending after all findings are provisionally closed.
