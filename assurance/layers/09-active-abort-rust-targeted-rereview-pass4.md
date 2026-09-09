# Layer 09 PASS 4 — targeted independent Rust finding-closure review

**Verdict:** `L09-R008` and `L09-R009` are provisionally closed. `L09-R007` is
`PARTIALLY_RESOLVED_BLOCKING`: the normal transition path is correct, but a synchronous RUNNING
observer failure leaves an orphaned live signal and permanently stranded RUNNING agent. Because
the same material finding has now survived two independent reviews, workflow section 11.8's
mandatory convergence trigger is met.

## Exact reviewed state

- code PR: `EGAILab/minion-agent#17`
- exact code head: `f13ee17404aa0c1a65b3a8c1c1d622340713f929`
- docs PR: `EGAILab/minion-agent-docs#26`
- exact docs head: `8c5610623520cafeb6b55ecba91ff2115b73f978`
- rejected PASS-3 code head: `ffecd2f9860dc4edd1d605f22ad571f5b36f66c5`
- rejected PASS-3 docs head: `7dde9ad3e4596e1d1fb64207de62f7bff00eace1`
- mandatory final-review rejection: docs PR #30 /
  `364504a1e1823ff40277da5a4fe08c0dc3e407cb`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- coordination issue: `EGAILab/minion-agent#16`, received as
  `STATUS = RUST_CONTRACT_REVIEW`, `NEXT_OWNER = Codex`

The exact candidate heads were fetched, remote-reachable, matched issue #16, Ready for Review,
open/unmerged, and cleanly mergeable. Candidate branches were not modified. The review used Pi,
spec, manifest, prior review acceptance criteria, touched dependencies, and Python last.

## Finding ledger

### L09-R007 — signal lifetime at public status transitions

**Result: `PARTIALLY_RESOLVED_BLOCKING`.**

The requested normal-path ordering is implemented:

```text
_start_run_signal()
set_status(RUNNING)
...
_end_run_signal()
set_status(IDLE)
```

The new permanent witness is discriminating and passes. During a returning RUNNING callback the
observer sees the active signal, its `abort()` lands on the provider request, and a returning IDLE
callback sees `None`. This closes the original happy-path witness.

However, the prior review explicitly required safe cleanup when the synchronous transition
observer fails. Both `AGENT_STATUS` emit listeners and `on_status_change` run synchronously inside
`set_status`. `_start_run_signal()` and `set_status(RUNNING)` are still before `_run_wrapped`'s
`try/finally`. A refined real-loop witness makes `on_status_change` raise on RUNNING:

```text
raised = RuntimeError status-boom
status = running
signal_is_none = False
provider requests = 0
second prompt = AgentActiveError
```

No run executor or `agent_start` lifecycle began, yet the agent is permanently RUNNING and owns a
live signal no code will clear. The same failure can originate from a synchronous `agent/status`
EventBus listener before `on_status_change` is reached. PASS 4 therefore moved the leaked resource
into existence without putting the entry transition under a rollback/settlement boundary.

Pinned Pi has no Minion `agent/status`/`on_status_change` extension, so the precise observer-failure
policy cannot be inferred from Pi. What Pi does establish is that its active-run resource is owned
by `runWithLifecycle` and always reaches `finishRun` once installed. The shared Minion contract
currently specifies successful transition visibility but not failure atomicity for this
extension. This residual is a `CONTRACT_ASSURANCE_DEFECT` within `L09-R007`, not a reason to copy a
Python mechanism into Rust.

### L09-R008 — recommended after-hook helper signal

**Result: `PROVISIONALLY CLOSED` at the exact PASS-4 SHAs.**

`register_after_tool_call_hook` now distinguishes the existing one-argument helper form from a
two-argument `(result, signal)` form. Independent execution of the new tests proves:

- a two-argument helper sees the exact active signal;
- it sees `None` when execution has no active signal;
- every existing one-argument helper remains unchanged;
- the helper delegates without re-supplying signal, and raw downstream normalization still
  restores authoritative metadata.

This matches Pi's `afterToolCall(context, signal)` observable capability while preserving Minion's
constrained N-listener helper API. No ambiguity relevant to Rust remains: Rust can express the two
typed forms explicitly rather than copy Python arity inspection.

### L09-R009 — contradictory current manifest/assurance rules

**Result: `PROVISIONALLY CLOSED` at the exact PASS-4 SHAs.**

`TOOL-024` now opens with one explicit current dispatch table and authoritative-signal rule. The
old four-argument-only and must-re-supply/degrade statements are marked superseded in place.
`AG-007` similarly labels its Layer-08-era deferral as historical and its Layer-09 realization as
current. The latest PASS-4 assurance conclusion says no signal-only arity constraint remains.
Historical PASS sections still reproduce their then-current conclusions, but are now clearly
superseded rather than competing current guidance. Manifest structure remains 79 rows / 79 unique
IDs.

## Convergence trigger and characterization for residual L09-R007

Trigger check:

```text
same material finding survives two independent reviews
    YES — R007 was found in the mandatory final review and remains partially open here

layer has accumulated three rejected contract reviews
    YES — independently true, though the same-finding trigger alone is sufficient

required workflow state
    CONTRACT_CONVERGENCE
```

### Open surface

Atomic ownership and cleanup of the per-run controller across Minion's synchronous public status
notification extension.

### Observable behavior matrix

| Transition observer behavior | Required observable constraint | PASS-4 result |
|---|---|---|
| no observer | one fresh signal for whole run; `None` afterward | pass |
| RUNNING observer returns | sees live signal | pass |
| RUNNING observer calls `abort()` and returns | same provider/request signal is aborted | pass |
| IDLE observer returns | sees `None` | pass |
| RUNNING `on_status_change` throws | must not leave an ownerless active signal or permanently strand the agent | **fail** |
| RUNNING `AGENT_STATUS` emit listener throws | same atomicity requirement; later callback behavior must be defined | **uncovered/fail by control flow** |
| IDLE observer throws | signal must already be `None`; run-state/error propagation policy must be explicit | signal passes; policy unspecified |

### Minimal executable witnesses

1. Existing PASS-4 happy-path witness: RUNNING callback sees signal, aborts it, request sees
   aborted, IDLE callback sees `None`.
2. New failure witness: RUNNING `on_status_change` raises; afterward assert the chosen contract's
   terminal status/signal state, error propagation/settlement outcome, and whether a second prompt
   is legal.
3. Same witness through an `AGENT_STATUS` EventBus listener, including whether
   `on_status_change` is skipped after the first listener failure.
4. IDLE observer failure witness, defining whether successful run output remains committed and
   whether the caller sees an error, without reintroducing a live signal.

### Contract decisions required before implementation

Because the transition callback is Minion-only, the shared owner must explicitly choose and record
one coherent policy rather than infer it from Python accident:

- whether a RUNNING notification failure rolls entry back and propagates, or is converted into the
  normal run-failure lifecycle;
- the exact final `status` and `signal` after that failure;
- whether an IDLE notification failure propagates after the run has otherwise settled;
- ordering/failure short-circuit across `AGENT_STATUS` listeners and `on_status_change`;
- how rollback itself avoids recursively failing transition notification.

Whichever policy is chosen must preserve: no orphaned controller, no permanently false-active
agent, no provider request after failed entry unless explicitly settled as a run, and the signal
remaining live through genuine `agent_end` settlement. This is a contract/evidence checkpoint;
this review does not prescribe Python mechanics.

### Required deltas

- normative `spec/agent.md`: status-observer failure atomicity and controller ownership;
- `AG-007` and, if ownership warrants it, the status row: one coherent rule/evidence pointer;
- Python language tests for both public synchronous observer seams and entry/exit failures;
- Python implementation only after the shared owner challenges/agrees the policy;
- no canonical scenario is required if the existing canonical schema cannot express synchronous
  listener failures and explicit language tests are recorded as the load-bearing evidence.

### Out of scope

- forced task cancellation;
- provider transport abort (`PROV-004`);
- tool batch/preflight changes;
- Layer 10;
- Rust implementation.

## Touched dependency regression

- C001-C003 and R001-R006 remain provisionally closed; PASS 4 did not alter their algorithms.
- Raw pre/post waterfall signal restoration remains authoritative.
- One- and two-argument helper tests pass through the real executor.
- The successful status-order witness passes through the real loop.
- No canonical runner simulates these semantics; the three Layer-09 canonical files remain
  disclosed placeholders and are not counted as evidence.
- Rust remains able to implement the eventual rule idiomatically with a scoped run guard/RAII and
  typed signal handles; no certified lower-layer semantic reopen is indicated.

## Fresh gates

```text
focused PASS-4 witnesses
    4 passed

full Python suite
    1093 passed, 19 xfailed, 0 failed

coverage
    100.00% (2794/2794 statements)

ruff
    PASS

mypy src
    PASS (58 files)

manifest
    79 rows / 79 unique IDs

independent throwing-RUNNING-observer probe
    FAILS contract atomicity; status=running, signal live, zero requests, second prompt rejected
```

## Verdict

```text
L09-R007
    PARTIALLY_RESOLVED_BLOCKING

L09-R008
    PROVISIONALLY CLOSED @
      code f13ee17404aa0c1a65b3a8c1c1d622340713f929
      docs 8c5610623520cafeb6b55ecba91ff2115b73f978

L09-R009
    PROVISIONALLY CLOSED @
      code f13ee17404aa0c1a65b3a8c1c1d622340713f929
      docs 8c5610623520cafeb6b55ecba91ff2115b73f978

PI_PARITY_DEFECT
    none new beyond the resolved happy-path portion of R007

CONTRACT_ASSURANCE_DEFECT
    L09-R007 residual status-observer failure/cleanup semantics

PI_BEHAVIOR_UNCERTAIN
    none — Pi has no status observer; this is an explicitly Minion-owned mapping decision

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

## Next action

Enter `CONTRACT_CONVERGENCE` for the residual R007 status/signal failure-atomicity surface. The
shared/Python owner should challenge this characterization and record an agreed policy/witness
matrix before another implementation pass. Preserve R008/R009 and every earlier closure unless a
new witness contradicts them. Any new candidate SHA requires targeted exact-SHA closure review;
once all findings are provisionally closed, workflow section 11.8.8 still requires another final
complete review before approval.
