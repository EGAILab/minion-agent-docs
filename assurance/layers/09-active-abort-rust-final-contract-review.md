# Layer 09 — final complete independent Rust contract review

**Verdict: REJECTED FOR RUST IMPLEMENTATION.** The convergence findings through `L09-R006`
remain closed at the exact candidate below, but the mandatory complete review found two new
Python parity defects and one current contract/evidence contradiction. Rust Layer 09 must not be
implemented from this candidate.

## Exact reviewed state

- code PR: `EGAILab/minion-agent#17`
- exact code head: `ffecd2f9860dc4edd1d605f22ad571f5b36f66c5`
- docs PR: `EGAILab/minion-agent-docs#26`
- exact docs head: `7dde9ad3e4596e1d1fb64207de62f7bff00eace1`
- accepted code baseline: `3ec1a386c86a93a13344ed38d796fbb74e9817bd`
- accepted docs baseline: `ecb809798b7437045e1325683306c3f15f46571e`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- checkpoint review: docs PR #23 / `3787ceda5ef90fe03a9115649e7b9d92e0101530`
- checkpoint targeted re-review: docs PR #25 /
  `aa9886e1363c75a88324403c00c556801b39b1cc`
- PASS-1 full rejection: docs PR #27 /
  `0a781d3f6710d633f9fcf4c10ef11422dfeef1ee`
- PASS-2 targeted rejection: docs PR #28 /
  `9a8b9632f78a7bf0ba398f9ba4cc314981bdb8d4`
- PASS-3 targeted closure: docs PR #29 /
  `17c6abdc234f0ced60f543421608679d95744304`
- coordination issue: `EGAILab/minion-agent#16`, received as
  `STATUS = RUST_CONTRACT_REVIEW`, `NEXT_OWNER = Codex`

Both candidate heads were fetched and remote-reachable, matched issue #16, were Ready for Review,
open, unmerged, and cleanly mergeable. The candidate branches were not modified. Existing
untracked `.worktrees/` were preserved.

## Authority and source audit

The review used the required order: pinned Pi, normative spec, manifest, canonical conformance,
certified Rust architecture, assurance, and Python implementation last. Pinned Pi was re-read at
the exact revision in:

- `packages/agent/src/agent.ts`: `Agent.signal`, `Agent.abort`, `runWithLifecycle`, `finishRun`,
  `processEvents`, callback wrapping, and failure settlement;
- `packages/agent/src/agent-loop.ts`: request signal propagation, `transformContext`, tool
  preflight, sequential/parallel batch polling, execute/finalize, and after-hook delivery;
- `packages/agent/src/types.ts`: `AgentLoopConfig`, hook, tool, request, and signal-bearing types.

Pi creates and installs the active run/controller before setting `isStreaming = true`. It retains
that controller through failure recovery and awaited `agent_end` listeners. `finishRun` clears
`isStreaming` and then removes `activeRun`; outside Minion's synchronous transition callback there
is no externally interleavable point between those final writes. Every callback receives the same
read-only `AbortSignal`; only `Agent.abort()` owns the controller. Cancellation is cooperative.

## Complete closure ledger

### Checkpoint findings

- **L09-C001 — CLOSED:** sequential polling occurs after each complete call; parallel polling
  occurs after each sequential preflight outcome, before the next source call. Prepared calls
  retained before an abort still execute behind the parallel barrier.
- **L09-C002 — CLOSED:** unknown tool, preparation/validation failure, and a throwing before-hook
  retain priority over abort; after a returning hook, abort beats a block/proceed decision.
- **L09-C003 — CLOSED:** all consumers may ignore cancellation; represented aborted output,
  exception classification while aborted, cooperative tool behavior, and abort during
  `agent_end` settlement remain distinct.

### Prior implementation-review findings

- **L09-R001 — CLOSED for the raw event seams, but see new L09-R008:** raw
  `TOOLS_PRE_EXECUTE`/`TOOLS_POST_EXECUTE` listeners receive the active signal.
- **L09-R002 — CLOSED:** failure settlement reads the live signal and selects aborted/error from
  its state at the classification point.
- **L09-R003 — CLOSED:** `ToolDefinition.wants_signal` plus arity represents neither,
  update-only, signal-only, and signal-plus-update capabilities.
- **L09-R004 — CLOSED:** consumers receive a read-only `RunSignal`; the controller remains private
  to `AgentInstance`, and the signal property has no public setter.
- **L09-R005 — CLOSED:** `AGENT_TRANSFORM_CONTEXT` is present at every request boundary and is
  provider-local, non-persistent, and signal-bearing.
- **L09-R006 — CLOSED:** all three waterfall seams restore the original signal at every listener
  handoff; replacement and omission attacks cannot redirect downstream listeners.

The exact PASS-3 replacement/drop probes and full regression suite remain green. These closures do
not cure the new surfaces below, which the targeted reviews did not exercise.

## L09-R007 — signal lifetime is inverted at public status transitions

**Classification: `PI_PARITY_DEFECT`.**

The shared rule says `AgentInstance.signal` is `None` while idle and the same signal is live for
the run's entire active duration. Minion's `AgentStatus.RUNNING`/`IDLE` is the approved public
projection of Pi's `isStreaming` state. However `AgentLoop._run_wrapped` currently performs:

```text
set_status(RUNNING)       # synchronously emits agent/status and on_status_change
_start_run_signal()
...
set_status(IDLE)          # synchronously emits agent/status and on_status_change
_end_run_signal()
```

An independent real-loop witness registered `on_status_change`, read `instance.signal` at each
transition, and called `instance.abort()` when RUNNING was published:

```text
status_observations = [('running', True, None), ('idle', False, False)]
request_signal_aborted = False
after_run_signal_is_none = True
```

The public RUNNING observer sees no signal and its abort is a no-op; the subsequent provider
request receives an un-aborted signal. The public IDLE observer sees the previous run's live
signal. This contradicts both the signal-lifetime rule and the status projection, even though the
values become correct after each synchronous callback returns.

**Required narrow remediation:** install the per-run controller before publishing RUNNING and
remove it before publishing IDLE, preserving the already-approved fact that the signal remains
live through failure recovery and awaited `agent_end` settlement. Preserve cleanup and established
status-listener failure behavior: a transition callback failure must not leak a controller, strand
status, or bypass the run's required settlement semantics. Add a discriminating real-loop test in
which the RUNNING callback observes and aborts the signal and the IDLE callback observes `None`.

## L09-R008 — the recommended after-hook helper hides the signal

**Classification: `PI_PARITY_DEFECT`.**

Pinned Pi calls `afterToolCall(context, signal)`. The current shared spec and `TOOL-024` adopt the
rule that before/after hooks receive the active signal. Raw `tools/post-execute` listeners now do,
but the public, exported, documented-as-recommended `register_after_tool_call_hook` helper still
defines its hook as `Callable[[ToolResult], ...]` and invokes only `hook(result)`.

An independent witness registered a helper hook accepting `(result, signal)` and executed a real
tool call with an active signal:

```text
seen = []
is_error = True
content = "hook() missing 1 required positional argument: 'signal'"
```

The raw-listener test named `test_after_hook_receives_the_active_signal` therefore proves only the
raw event seam, not the recommended typed hook seam. A caller using the intended constrained API
cannot observe cancellation through its after-hook at all.

**Required narrow remediation:** make helper-registered after-hooks able to receive the exact
authoritative signal while preserving compatibility for existing one-argument helpers (or adopt
another explicit, language-neutral-compatible API shape). Add a discriminating helper-path test;
retain raw-listener authoritative restoration and after-hook failure replacement semantics. Align
the helper documentation and manifest evidence with the resulting public API.

## L09-R009 — current manifest and assurance contradict the repaired tool capability

**Classification: `CONTRACT_ASSURANCE_DEFECT`.**

The current `TOOL-024` row contains mutually exclusive rules. Its early current-description
paragraph says a signal-bearing tool must declare a fourth `(signal, update)` slot and calls the
inability to express signal-only tools a disclosed constraint. Later in the same row, the R003
remediation correctly says `wants_signal=True` makes a three-parameter
`(tool_call_id, arguments, signal)` tool signal-only. The row likewise preserves an obsolete R001
paragraph saying explicit delegation must re-supply signal and omission degrades downstream to no
signal, before the later R006 paragraph says authoritative normalization makes both replacement
and omission impossible.

The current PASS-3 assurance conclusion also still lists this disproven active-state claim:

```text
4-parameter arity dispatch required for a tool wanting signal
(cannot want signal alone without also declaring update)
```

That is not merely historical narrative: it appears in the current active-findings/verdict area.
An independent Rust implementer can reasonably derive conflicting APIs from the manifest and
assurance despite `spec/tools.md` now containing the correct dispatch table.

**Required narrow remediation:** rewrite `TOOL-024` as one unambiguous current rule, moving or
clearly labeling superseded chronology so it cannot be read normatively. Remove the obsolete
must-re-supply/degrade behavior and the obsolete four-parameter limitation from current assurance
conclusions. Keep the correct four-combination table and authoritative signal-restoration rule.
Audit `AG-007`'s opening “DEFERRED” wording similarly so the current `disposition: adopted` and
“now realized” status are unmistakable.

## Consumer and settlement matrix

Source inspection confirms the same active signal is otherwise reachable at the following
production seams:

| Consumer | Candidate behavior | Result |
|---|---|---|
| lifecycle listeners | read-only through `instance.signal` | pass during event dispatch |
| transform-context listeners | explicit, authoritatively restored | pass |
| LLM request | exact active signal on `Request.signal` | pass |
| raw before-hook listeners | explicit, authoritatively restored | pass |
| tool execute | explicit declared capability | pass |
| raw after-hook listeners | explicit, authoritatively restored | pass |
| helper after-hook | signal omitted | **fail (R008)** |
| prepare-next-turn / should-stop listeners | reachable through active `instance.signal` | pass by source |
| `agent_end` listener settlement | signal retained until `_execute_run` returns | pass by source |
| public RUNNING/IDLE transition observers | signal starts too late and ends too late | **fail (R007)** |

The load-bearing ignore rule remains correct: merely having or aborting a signal does not forcibly
cancel Python tasks, provider work, tools, or listeners. The tool batch alone applies the two
specified cooperative polls. Actual provider transport cancellation remains properly deferred to
`PROV-004`.

## Canonical and evidence audit

The three Layer-09 canonical documents remain placeholders:

- `active-abort-tool.yaml`
- `active-abort-provider.yaml`
- `abort-settles-before-idle.yaml`

Each still contains `TO_BE_FILLED_FROM_PINNED_PI_BEHAVIOR` and is not executable evidence. The
manifest discloses this rather than counting them for `AG-007`, `AI-027`, or `TOOL-024` (the
`PROV-004` future-provider row references `active-abort-provider`, but remains a future Phase-5
target rather than current Layer-09 certification evidence). The current Python language suite is
therefore load-bearing. It did not contain the R007 status-boundary or R008 helper-path witnesses.

No runner was found simulating Layer-09 behavior. The absence of current canonical evidence is not
by itself the rejection reason under the project's accepted canonical-or-explicit-language-test
rule; the two uncovered production behaviors and contradictory current evidence are.

## Rust implementability and certified-layer impact

The corrected semantic design remains implementable without redesign:

- certified Rust Layer 06 already has `ToolExecutionSignal` and
  `ToolExecutionRequest.signal` as typed, poll-based seams;
- Rust Layer 08 has typed `AgentInstance`, `AgentLoop`, lifecycle dispatch, `LlmRequest`, and
  post-turn decision seams to extend;
- the agent controller/read-only signal split can use `Arc` and an atomic flag;
- `LlmRequest` can gain an optional typed read-only signal capability;
- listener APIs can carry a cloned `Arc<dyn ToolExecutionSignal>` outside listener-transformable
  payload, including the recommended after-hook registration helper;
- no Runtime default dispatch behavior, Session contract, LLM message vocabulary, XFORM rule,
  ToolRegistry semantics, or non-cancellation Layer-06 execution ordering needs to change.

The defects are therefore not Rust architectural blockers and require no certified lower-layer
reopen. They are candidate Python/shared remediation obligations. Rust could implement a guessed
correct behavior, but doing so now would violate reviewer/author separation and would not implement
the exact approved cross-language contract.

## Fresh evidence

```text
full Python suite
    1089 passed, 19 xfailed, 0 failed

coverage
    100.00% (2791/2791 statements)

ruff
    PASS

mypy src
    PASS (58 source files)

schema tests
    185 passed with --no-cov
    (a focused run without --no-cov also passed all assertions but correctly failed the
     repository-wide 100% coverage gate because it intentionally executed only schema tests)

manifest structural audit
    79 rows, 79 unique IDs

independent semantic probes
    status/signal boundary: FAIL
    helper after-hook signal delivery: FAIL
```

Green aggregate gates do not override the discriminating failures above.

## Contract-quality answers

```text
runner simulates production semantics
    NO

Python workaround caused solely by incomplete shared contract
    NO identified; the failures are direct implementation/evidence mismatches

same signal reaches every advertised consumer
    NO (helper after-hook and public status boundary)

signal authority preserved across raw waterfall handoffs
    YES

could two Rust implementers derive different tool callback APIs from current artifacts
    YES (TOOL-024/assurance contradiction)

could Rust implement the corrected language-neutral behavior idiomatically
    YES

lower-layer contract reopen required
    NO
```

## Final findings and verdict

```text
PI_BEHAVIOR_UNCERTAIN
    none

PI_PARITY_DEFECT
    L09-R007 -- signal lifetime inverted at public RUNNING/IDLE transition callbacks
    L09-R008 -- recommended after-hook helper does not deliver the active signal

CONTRACT_ASSURANCE_DEFECT
    L09-R009 -- TOOL-024 and current assurance retain contradictory superseded rules

PARITY_CONSTRAINED_RISK
    none blocking

PARITY_NEUTRAL_HARDENING
    add explicit prepare-next-turn/should-stop/agent_end signal witnesses while the Python
    language suite remains the sole executable Layer-09 contract evidence

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

## Required next action

Return to the Python/shared owner for the three narrow remediations above. Preserve C001-C003 and
R001-R006 unless a new witness contradicts them. Any new code/docs candidate SHA requires review;
because these are newly discovered surfaces from the mandatory final review, use the workflow's
normal remediation and exact-SHA targeted closure review before another final approval gate. Do
not implement Rust Layer 09 and do not start Layer 10.
