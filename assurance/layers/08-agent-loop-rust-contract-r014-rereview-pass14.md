# Layer 08 — independent Rust approval of PASS-14 L08-R014 remediation

## Exact review target

- code PR `EGAILab/minion-agent#15`: `c92c1230b17f2eeb87af91ab0046d5be813df097`
- docs PR `EGAILab/minion-agent-docs#16`: `a6e482730978c12fad57e97fe446f0ff3c3b89fd`
- accepted code baseline: `f428a7b47bcc720b0126ca799be7c72c5977f8c2`
- accepted docs baseline: `a77a3843279b59f567f171753147a4806e74982e`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- preceding rejected review: docs PR `#17`, commit
  `87d1eba6bf0b702c5ca488b593e666c411d6f0a7`
- Rust WIP PR `EGAILab/minion-agent#14`: `d3006375dc56deda1514ee9793708a14c9dd3dfe`

Both candidate heads were remote-reachable, open, Ready for Review, unmerged, and matched issue
`EGAILab/minion-agent#12`. This approval applies only to the exact candidate SHAs above.

## Independent source result

Pinned Pi uses three distinguishable model values:

1. the initial/current persistent Agent model;
2. a run-local `prepareNextTurn` override, stored only in the loop's local config;
3. a later caller mutation of the live persistent `AgentState.model`.

`agent-loop.ts:230-238` proves source 2 does not mutate persistent Agent state.
`agent.ts:511-524::handleRunFailure` reads current `this._state.model` inline at settlement. The
public `state` getter and the certified Layer-07 contract make source 3 observable. Therefore failure
identity excludes source 2, but includes source 3.

## L08-R014 closure

PASS 14 closes the residual contract contradiction:

- both normative spec passages now require a live read of the current persistent Agent model;
- they explicitly reject both the run-local override and a construction/run-start cache;
- the Python docstring says the same;
- the original A -> run-local B -> failure test remains;
- the new A -> run-local B -> persistent C -> failure test requires C;
- production already reads `self.instance.model` at settlement and required no change.

Independent execution:

```text
test_settle_run_failure_uses_the_agents_persistent_model_not_the_run_local_override
    PASS

test_settle_run_failure_reports_the_live_persistent_model_not_a_run_start_snapshot
    PASS
```

The corrected rule is language-neutral and sufficient for Rust Task 8: query
`AgentInstance::model()` while settling the failure; do not reuse `PreparedRun.config.model` and do
not cache the persistent model at entry.

Finding status: **RESOLVED**.

## Traceability note

AG-009's appended PASS-14 rule and tests are coherent. Its `rust:` status sentence still says the
WIP resumes after PASS 13 rather than PASS 14. This is a non-semantic transitional evidence pointer:
it does not alter the now-unambiguous rule, and the Rust implementation/certification pass already
owns replacing that field with final implementation/test evidence. Classified
`PARITY_NEUTRAL_HARDENING`, non-blocking; it must be corrected before Rust certification.

## Active findings

```text
PI_PARITY_DEFECT
    none

CONTRACT_ASSURANCE_DEFECT
    none

PI_BEHAVIOR_UNCERTAIN
    none

unapproved observable divergence
    none
```

## Verdict

```text
shared Layer-08 contract at the exact PASS-14 SHAs
    APPROVED FOR RESUMED RUST IMPLEMENTATION

Python Layer 08
    CERTIFIED

Rust Layer 08
    PARTIALLY_IMPLEMENTED — Task 8 may resume

Layer 08 cross-language
    NOT CLOSED

Layer 09
    NOT STARTED
```

No Rust implementation or candidate shared/Python file was modified during this review.
