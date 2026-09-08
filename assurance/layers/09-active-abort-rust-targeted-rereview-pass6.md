# Layer 09 — Rust targeted re-review of PASS 6 L09-R010 remediation

**Mode:** targeted finding-closure review (`agent-workflow.md` §11.8.7)

**Verdict:** `L09-R007/L09-R010 PROVISIONALLY CLOSED; NEW BLOCKERS L09-R011/L09-R012`

## Exact remote state reviewed

- code PR: `EGAILab/minion-agent#17` at
  `f3dddebd935c1bc5b18e01ca62d1f9f03a5a4eee`
- docs PR: `EGAILab/minion-agent-docs#26` at
  `7f5d3328a2a04eadf739a8d5c59ae5453a98f0fd`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- preceding targeted review: docs PR #32 at
  `03db3aaa1cee5e09d91be2ba7a1a77b91744ab4c`

Both candidate SHAs were fetched and verified remote-reachable. PRs #17 and #26 were open,
Ready for Review, and matched coordination issue `EGAILab/minion-agent#16`.

## Scope and fresh evidence

Reviewed PASS 6's replacement of public `Inbox.restore()` with public read-only `peek()` plus
private `_commit_claim()`, the unchanged eight L09-R007 black-box witnesses, the nine changed Inbox
tests, and current spec/manifest/assurance wording.

A fresh targeted run at the exact code SHA executed every test in `tests/agent/test_inbox.py` and
`tests/agent_loop/test_active_abort.py`: **53 passed** with `--no-cov`.

## L09-R010 closure

The exact public-authority defect is resolved:

- public `Inbox.restore()` no longer exists;
- the reviewer's duplicate-ID insertion witness now raises `AttributeError`;
- public `peek()` is read-only;
- private `_commit_claim()` is removal-only and cannot insert duplicate IDs;
- all eight agreed L09-R007 failed-entry/status-settlement witnesses remain unchanged and pass.

```text
L09-R010
    PROVISIONALLY CLOSED
    @ code f3dddebd935c1bc5b18e01ca62d1f9f03a5a4eee
    @ docs 7f5d3328a2a04eadf739a8d5c59ae5453a98f0fd

L09-R007
    PROVISIONALLY CLOSED for its agreed failure-atomicity matrix at the same SHAs
```

The mandatory final complete review is not yet eligible because the replacement mechanism exposes
a new adjacent reentrancy defect.

## L09-R011 — commit-by-count removes non-peeked input after observer reentrancy

### Classification

`CONTRACT_ASSURANCE_DEFECT`

### Basis

`continue_()` / `run_until_idle()` now perform:

```text
peek exact entering batch
    -> set_status(RUNNING)
        -> synchronous AGENT_STATUS/on_status_change observer may mutate Inbox
    -> _commit_claim(target, peeked_batch)
```

The implementation and its docstring say `_commit_claim()` removes **exactly** the envelopes
returned by the prior peek. It actually ignores their identity and executes:

```python
queue[: len(envelopes)] = []
```

The synchronous status observer is an external/re-entrant seam explicitly central to L09-R007. It
may call any public Inbox operation before returning. If it claims or clears the peeked prefix,
`_commit_claim()` removes unrelated envelopes that moved to the front in the meantime.

This is not hypothetical thread scheduling and involves no `await`: the mutation occurs inside the
exact synchronous notification deliberately placed between peek and commit.

### Executed discriminating witness

Against the exact PASS-6 candidate:

```python
inbox = Inbox()
a = inbox.steer(message_a)
b = inbox.steer(message_b)

peeked = inbox.peek(InboxTarget.NEXT_STEP, ClaimPolicy.ONE_AT_A_TIME)  # A
observer_claim = inbox.claim(InboxTarget.NEXT_STEP, ClaimPolicy.ONE_AT_A_TIME)  # A removed
inbox._commit_claim(InboxTarget.NEXT_STEP, peeked)
```

Observed:

```text
peeked             [A]
observer claimed   [A]
before commit      [B]
after commit       []
B preserved        false
```

The same sequence occurs through the real driver when a successful RUNNING observer claims from
the same target. The run's entering batch remains `A`, but commit silently deletes `B`, which was
never peeked or selected for this run.

The new test `test_calling_commit_claim_repeatedly_only_removes_never_duplicates` currently
codifies this wrong authority: after peeking `A`, it calls `_commit_claim` twice and asserts both
`A` and unrelated `B` are absent. Proving that a private operation cannot insert duplicates is
insufficient if it can delete arbitrary non-selected input.

### Narrow remediation

Preserve the already-correct black-box failed-entry behavior and ensure:

```text
commit removes only the exact batch selected at the pre-drain boundary
a synchronous RUNNING observer cannot cause commit to delete later/unselected input
observer queue mutations are not silently undone or broadened
failed RUNNING notification still removes nothing
successful ordinary entry still consumes the selected batch exactly once
```

An internal claim-plus-private-rollback design, an identity-checked/linear reservation token, or an
equivalent mechanism is acceptable. A count-only commit after a re-entrant observer is not.

Required permanent witnesses:

1. `ONE_AT_A_TIME`, queue `A,B`; RUNNING observer claims `A` and returns; the driver's commit must
   not remove `B`.
2. `ALL`, queue `A,B`; RUNNING observer clears that target, enqueues `C`, and returns; commit must
   not remove `C` as if it were part of the earlier peek.
3. Existing eight L09-R007 witnesses and the L09-R010 no-public-restore witness remain green.

## L09-R012 — stale AG-011 implementation pointer

### Classification

`CONTRACT_ASSURANCE_DEFECT` (documentary/traceability only)

PASS 6 updates AG-011's rule text to `Inbox.peek` / `Inbox._commit_claim`, but its `python:` evidence
pointer still names the removed `Inbox.restore`. This contradicts the same row's current prose and
the exact implementation.

Required remediation: replace the stale pointer with the actual current seam. No executable
witness or semantic change is needed.

## Contract quality and lower-layer impact

- No canonical runner simulates the behavior.
- No Pi uncertainty exists; status observers are Minion-owned architecture.
- No certified lower-layer semantic reopen is required.
- The defect is localized to the Layer-09 entry-commit mechanism and its traceability.
- Rust can implement the requirement idiomatically with private linear/owned claim state and no
  lock held across observer dispatch.

## Finding ledger and verdict

```text
L09-R007
    PROVISIONALLY CLOSED @ exact PASS-6 SHAs

L09-R008
    PROVISIONALLY CLOSED, unaffected

L09-R009
    PROVISIONALLY CLOSED, unaffected

L09-R010
    PROVISIONALLY CLOSED @ exact PASS-6 SHAs

L09-R011
    CONTRACT_ASSURANCE_DEFECT — OPEN

L09-R012
    CONTRACT_ASSURANCE_DEFECT — OPEN

PI_BEHAVIOR_UNCERTAIN
    none

PI_PARITY_DEFECT
    none newly classified

PASS-6 TARGETED REVIEW
    REJECTED due new adjacent blockers

Rust Layer 09
    NOT IMPLEMENTED

Layer 10
    NOT STARTED
```

Claude should remediate R011/R012 narrowly, convert both reentrancy examples into regression
evidence, rerun the existing convergence witnesses, and return exact remote SHAs for targeted
closure. After every blocker is provisionally closed, workflow §11.8.8 still requires one final
complete review before shared-contract approval or merge.
