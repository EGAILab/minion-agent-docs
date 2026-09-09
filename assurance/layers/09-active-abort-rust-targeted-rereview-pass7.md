# Layer 09 — Rust targeted re-review of PASS 7 L09-R011/L09-R012 remediation

**Mode:** targeted finding-closure review (`agent-workflow.md` §11.8.7)

**Verdict:** `L09-R011/L09-R012 PROVISIONALLY CLOSED; FINAL COMPLETE REVIEW REQUIRED`

## Exact remote state reviewed

- code PR: `EGAILab/minion-agent#17` at
  `ef23829a9a7acf4033df7a9186a810c41433ad64`
- docs PR: `EGAILab/minion-agent-docs#26` at
  `633f6a82822e82705a5fe956dad28bd4c0ce4acb`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- preceding targeted review: docs PR #32 at
  `248dd3c62f96b66d7dfed50519b468c78f80c9a3`

Both candidate SHAs were fetched and verified remote-reachable. PRs #17 and #26 were open,
non-draft, and matched coordination issue `EGAILab/minion-agent#16`.

## Scope and fresh evidence

This review examined only the two open PASS-6 findings and the semantic dependencies changed by
their repair: Inbox run-entry selection/commit, synchronous RUNNING-observer reentrancy, the
existing L09-R007 failed-entry behavior, AG-011 traceability, and the current normative wording.
It did not repeat the release-level Layer-09 audit.

A fresh targeted run at the exact code SHA executed every test in
`tests/agent/test_inbox.py` and `tests/agent_loop/test_active_abort.py`: **57 passed** with
`--no-cov`.

## L09-R011 — exact-prefix commit under reentrancy

### Result

`PROVISIONALLY CLOSED`

The PASS-7 implementation no longer removes by count. `_commit_claim(target, envelopes)` now:

1. treats an empty batch as a no-op;
2. checks that the queue contains at least the selected batch;
3. checks each queue-prefix element is the exact selected envelope in the same position; and
4. removes that prefix only when every check succeeds; otherwise it removes nothing.

The implementation uses Python object identity internally. That is not made normative. The shared
observable rule is stable envelope identity plus exact ordered-prefix matching, which Rust can
implement idiomatically with private owned claim state, stable IDs, or an equivalent linear token.

The two required discriminating witnesses now pass through the real driver:

- `ONE_AT_A_TIME`, queue `A,B`: the synchronous RUNNING observer claims `A`; the subsequent stale
  commit is a no-op and leaves `B` queued.
- `ALL`, queue `A,B`: the observer clears the target and enqueues `C`; the stale commit is a no-op
  and leaves `C` queued.

Both driver witnesses use a represented-aborted terminal response so the observation happens
before Layer 08's independent post-turn steering poll. They therefore isolate run-entry commit
authority instead of confusing it with legitimate later queue consumption.

The corrected unit tests also prove that a repeated stale commit cannot delete the later `B`, and
that a front mismatch is a no-op. Ordinary unchanged prefixes still commit exactly once. The
public duplicate-insertion surface rejected under L09-R010 remains absent.

This closes the precise PASS-6 witness without weakening L09-R007's failure-atomicity rule or
silently undoing observer-owned queue mutations.

```text
L09-R011
    PROVISIONALLY CLOSED
    @ code ef23829a9a7acf4033df7a9186a810c41433ad64
    @ docs 633f6a82822e82705a5fe956dad28bd4c0ce4acb
```

## L09-R012 — AG-011 evidence pointer

### Result

`PROVISIONALLY CLOSED`

AG-011's current `python:` evidence now identifies `Inbox.peek` and
`Inbox._commit_claim (L09-R010/L09-R011, identity-checked)` and explicitly records that the earlier
public `Inbox.restore` mechanism was removed. The row no longer points at a nonexistent current
implementation seam. Historical assurance references to the superseded mechanism remain clearly
scoped as history and do not contradict the current rule.

```text
L09-R012
    PROVISIONALLY CLOSED
    @ code ef23829a9a7acf4033df7a9186a810c41433ad64
    @ docs 633f6a82822e82705a5fe956dad28bd4c0ce4acb
```

## Contract quality and Rust implementability

- No canonical runner simulates the run-entry commit behavior.
- The repair changes no pinned-Pi interpretation and introduces no Pi uncertainty.
- No certified lower-layer contract needs reopening.
- The private commit remains removal-only and introduces no new public mutation authority.
- Rust need not reproduce Python coroutine or object-identity mechanics; the exact-prefix/no-op
  rule is language-neutral and admits an idiomatic private linear implementation.
- No Layer-10 behavior was introduced or reviewed.

## Finding ledger and next gate

```text
L09-C001..C003
    PROVISIONALLY CLOSED, unaffected

L09-R001..R006
    PROVISIONALLY CLOSED, unaffected

L09-R007
    PROVISIONALLY CLOSED, regression surface remains green

L09-R008..R010
    PROVISIONALLY CLOSED, unaffected

L09-R011
    PROVISIONALLY CLOSED @ exact PASS-7 SHAs

L09-R012
    PROVISIONALLY CLOSED @ exact PASS-7 SHAs

PI_BEHAVIOR_UNCERTAIN
    none in targeted scope

PI_PARITY_DEFECT
    none in targeted scope

CONTRACT_ASSURANCE_DEFECT
    none open in targeted scope

Rust Layer 09
    NOT IMPLEMENTED

Layer 10
    NOT STARTED
```

Every known blocking finding is now provisionally closed. This is not shared-contract approval or
certification. Workflow §11.8.8 now requires **one final complete independent contract review of
these exact remote candidate SHAs** before approval, merge, or Rust implementation.
