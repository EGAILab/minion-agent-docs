# Layer 08 — independent Rust contract re-review of L08-R014

## Exact review target

- code PR `EGAILab/minion-agent#15`: `84137cbd1a1d648225959185b848e483a6bea4f8`
- docs PR `EGAILab/minion-agent-docs#16`: `cb88b55b15a5f8cd0fed8183c3235671d73d2909`
- accepted code baseline: `f428a7b47bcc720b0126ca799be7c72c5977f8c2`
- accepted docs baseline: `a77a3843279b59f567f171753147a4806e74982e`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- Rust WIP PR `EGAILab/minion-agent#14`: `d3006375dc56deda1514ee9793708a14c9dd3dfe`

Both candidate PR heads were remote-reachable, open, Ready for Review, unmerged, and matched issue
`EGAILab/minion-agent#12`. This review applies only to the exact candidate SHAs above. Candidate
branches were not modified.

## Authority and source audit

Reviewed in authority order: pinned Pi, normative spec, AG-009, evidence, then Python.

Pinned Pi establishes two distinct model authorities:

1. `agent-loop.ts:230-238` applies `prepareNextTurn.model` only to the invocation-local loop config.
2. `agent.ts:511-524::handleRunFailure` constructs the synthesized failure identity by reading
   `this._state.model` at failure settlement.

The public `Agent.state` getter (`agent.ts`, the live `AgentState` return) exposes that state object,
and the already-certified Layer-07 contract explicitly adopts direct caller mutation of
`AgentState.model` / `AgentInstance.model`. Therefore `this._state.model` is the Agent's **current
persistent state value at settlement**, not necessarily the construction-time value.

## L08-R014 re-review

### Reported witness: persistent A -> run-local B -> failure

PASS 13 correctly repairs the original implementation mismatch:

- Python `_settle_run_failure` no longer accepts `RunConfig`.
- It reads `self.instance.model`, not the run-local replacement.
- The new language test is discriminating for A -> run-local B -> failure and passes independently
  with `pytest --no-cov`.
- The spec and AG-009 now explicitly exclude the run-local `prepareNextTurn` replacement as the
  failure identity source.

This part is **RESOLVED**.

### Residual contradiction: current persistent value vs construction-time value

The repaired normative text also repeatedly says the persistent model is “set once when the Agent
is constructed,” “fixed at construction,” or equivalent. That contradicts the certified Layer-07
rule in the same `spec/agent.md`: `AgentState.model` is a freely reassignable live per-instance
current value. Pinned Pi's `state` getter returns the live state object, so a caller may mutate the
persistent model while a run is active; `handleRunFailure` subsequently reads that current value.

Discriminating witness:

1. Agent starts a run with persistent model A.
2. `prepareNextTurn` replaces run-local model with B.
3. While the run remains active, caller/listener sets the Agent's persistent model to C through the
   adopted Layer-07 mutation surface.
4. A later run-executor/listener failure reaches `handleRunFailure`.

Pinned Pi reports C because it reads current `this._state.model`. The new source-based rule and
Python implementation also imply C. But the new “fixed/set once at construction” prose implies A.
Two independent Rust implementations can therefore satisfy different sentences and produce
different observable failure identities.

Classification: `CONTRACT_ASSURANCE_DEFECT`.

Status: **PARTIALLY_RESOLVED_BLOCKING**.

## Evidence observations

- Targeted PASS-13 regression: PASS with `uv run pytest --no-cov ...`.
- Running the isolated test under the repository's default 100% aggregate coverage gate executes
  the test successfully but fails the aggregate threshold as expected for a single-test invocation;
  this is not a semantic failure.
- Candidate diff is narrow: Python failure identity/call signature, one discriminating test,
  AG-009, spec text, and PASS-13 assurance.
- No canonical scenario was added. An explicit language test is sufficient for the original A/B
  witness, but the contradictory C witness remains uncovered.
- Rust Tasks 1-7 are unaffected; Rust Task 8 remains correctly paused.

## Required narrow remediation

1. Replace every PASS-13 “set once/fixed at construction” assertion in normative spec, AG-009, and
   current assurance conclusions with: **the current persistent Agent model value read at failure
   settlement**.
2. State explicitly that a run-local `prepareNextTurn` override is excluded, while an independent
   caller mutation of the Agent's adopted Layer-07 current model is visible to later failure
   settlement, matching pinned Pi.
3. Add a discriminating Python language test for A -> run-local B -> persistent C -> failure,
   expecting C. The current implementation should already satisfy it; the test closes the ambiguous
   contract branch.
4. Re-run shared/Python certification and submit the resulting exact SHAs for targeted Rust
   re-review. Do not change unrelated Layer-08 semantics.

## Verdict

```text
shared Layer-08 L08-R014 contract remediation
    REJECTED — PARTIALLY_RESOLVED_BLOCKING

Python Layer 08
    REOPENED for narrow contract/evidence correction

Rust Layer 08
    PARTIALLY_IMPLEMENTED / TASK 8 BLOCKED

Layer 08 cross-language
    NOT CLOSED

Layer 09
    NOT STARTED
```

No Rust implementation, shared candidate, or Python candidate file was modified during this review.
