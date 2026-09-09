# Layer 09 — independent Rust contract review of the Python/shared implementation candidate

**Verdict:** REJECTED. The agreed active-abort checkpoint remains Pi-faithful, but the exact
Python/shared candidate below does not implement its complete propagation, authority, and
settlement contract. Rust Layer 09 is blocked; this review does not authorize implementation.

## Exact reviewed state

- code PR: `EGAILab/minion-agent#17`
- exact code head: `b5e44bb780e67dc8fccd27f630ce8d783b11303c`
- docs PR: `EGAILab/minion-agent-docs#26`
- exact docs head: `fdf4d3860d875cb4e800bba01784e22f7ba79ee4`
- accepted code baseline: `3ec1a386c86a93a13344ed38d796fbb74e9817bd`
- accepted docs baseline: `ecb809798b7437045e1325683306c3f15f46571e`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- coordination: `EGAILab/minion-agent#16`, received as `RUST_CONTRACT_REVIEW`,
  `NEXT_OWNER = Codex`
- checkpoint revision-1 review: docs PR #23 at
  `3787ceda5ef90fe03a9115649e7b9d92e0101530`
- checkpoint revision-2 targeted re-review: docs PR #25 at
  `aa9886e1363c75a88324403c00c556801b39b1cc`

Both candidate heads were fetched, were remote-reachable, matched issue #16, were Ready for
Review, and were unmerged when review began. The existing untracked `.worktrees/` entries were
left untouched.

## Authority and Pi audit

The review used pinned Pi first, then the checkpoint/normative spec, manifest, canonical files,
certified Rust architecture, assurance, and finally Python as secondary implementation evidence.
The following pinned symbols were re-read:

- `packages/agent/src/agent.ts`: `Agent.signal`, `Agent.abort`, `runWithLifecycle`,
  `handleRunFailure`, `finishRun`, `processEvents`, and loop-config callback wrappers;
- `packages/agent/src/agent-loop.ts`: `streamAssistantResponse`, sequential and parallel tool
  batches, `prepareToolCall`, `executePreparedToolCall`, and `finalizeExecutedToolCall`;
- `packages/agent/src/types.ts`: `AgentTool.execute`, before/after hook signatures, lifecycle
  listener/config callback signatures, and `AgentState`;
- relevant `packages/agent/test/agent.test.ts` and `e2e.test.ts` abort witnesses.

Independently confirmed:

- abort is cooperative and poll-based, never forced task interruption;
- one signal identity exists per run and is absent while idle;
- consumers receive a read-only `AbortSignal`; only the Agent's controller owns mutation;
- provider, lifecycle listener, transform-context, before hook, execute, after hook,
  prepare-next-turn, and should-stop surfaces receive that same signal;
- unknown/validation/hook-throw outcomes beat abort, while abort after a returning hook beats its
  block decision;
- sequential and parallel batches use the distinct algorithms recorded by checkpoint revision 2;
- an exception escaping after the signal is aborted produces a synthesized failure whose stop
  reason is `aborted`, regardless of causal relationship;
- all consumers may ignore abort and permit normal completion.

No Pi behavior uncertainty remains.

## Checkpoint finding regression

### L09-C001 — batch algorithms

The candidate correctly preserves the split algorithms. Sequential execution polls only after a
call's complete lifecycle. Parallel execution performs sequential preflight, polls after each
retained/immediate outcome, and then executes retained prepared calls concurrently. The exact
A/B/C regression is present and discriminating.

**Result:** remains provisionally closed at the contract level and passes in this candidate.

### L09-C002 — preflight priority

The candidate's single post-waterfall poll is observably equivalent to Pi's hook-present and
hook-absent checks because Minion's zero-listener waterfall follows the same path. Unknown tool,
validation/prepare failure, and a throwing before listener retain priority; abort beats a returned
block; valid non-aborted calls proceed. The focused tests are discriminating.

**Result:** remains provisionally closed at the contract level and passes in this candidate.

### L09-C003 — propagation and settlement matrix

The revision-2 contract itself remains correct, but the implementation does not satisfy it. Tool
hooks cannot observe the signal, exception recovery ignores aborted state, transform-context is
absent from the current contract mapping, and the public signal object/slot permits authority Pi
does not expose. The assurance nevertheless reports no active defect.

**Result:** checkpoint wording remains provisionally closed; implementation readiness is rejected
by `L09-R001`, `L09-R002`, `L09-R004`, and `L09-R005` below.

## Blocking findings

### L09-R001 — before/after tool hooks do not receive the run signal

**Classification:** `PI_PARITY_DEFECT`.

**Pi/source basis:** `prepareToolCall` invokes `beforeToolCall(context, signal)` and
`finalizeExecutedToolCall` invokes `afterToolCall(context, signal)`. The agreed checkpoint and
current `spec/agent.md`/`TOOL-024` say the signal reaches both seams explicitly.

**Candidate:** `_preflight` calls the `TOOLS_PRE_EXECUTE` waterfall with only call, definition,
validated arguments, and waterfall continuation. `_finalize` calls `TOOLS_POST_EXECUTE` with only
the result and continuation. `signal` is never among either listener's arguments. The only hook
test after abort proves that the after hook runs; it does not prove the hook receives the signal.

**Executable witness:** with a real non-null `RunSignal`, a variadic before listener observed:

```text
4 arguments: ToolCallBlock, ToolDefinition, dict, next
contains RunSignal: false
```

A raw after listener observed:

```text
2 arguments: ToolResult, next
contains RunSignal: false
```

**Why discriminating:** a hook that cooperatively stops or changes behavior only when its supplied
signal is aborted can do so in Pi, but cannot do so through Minion's declared hook seam without an
out-of-band capture.

**Required remediation:** add the same read-only run signal to the real before and after hook
interfaces and dispatches, preserving waterfall ordering and the existing preflight priority.
Add tests in which each hook observes the exact active-run signal identity; retain the existing
after-hook-unconditional rule.

### L09-R002 — exception-after-abort is synthesized as `error`, not `aborted`

**Classification:** `PI_PARITY_DEFECT`.

**Pi/source basis:** `runWithLifecycle` calls
`handleRunFailure(error, abortController.signal.aborted)`, and `handleRunFailure` sets the failure
message stop reason from that current boolean. Causation is deliberately irrelevant.

**Candidate:** `AgentLoop._settle_run_failure` hard-codes
`stop_reason=StopReason.ERROR` and never reads `instance.signal.aborted`, contradicting the current
normative paragraph and `AG-007`.

**Executable witness:** one lifecycle listener calls `instance.abort()` and then raises exactly
once. The candidate settles and reports:

```text
stop_reason: error
error_message: boom-after-abort
signal_after: None
```

Pinned Pi requires `stop_reason: aborted` for the synthesized failure.

**Required remediation:** snapshot/read the current active signal at the Pi-equivalent recovery
classification point and select `ABORTED` when it is set. Add the exact unrelated-exception-after-
abort witness, plus a non-aborted exception regression.

### L09-R003 — Python cannot express Pi's signal-only tool capability

**Classification:** `PI_PARITY_DEFECT`.

**Pi/source basis:** `AgentTool.execute(toolCallId, params, signal?, onUpdate?)` makes signal and
update independent optional capabilities. A three-argument implementation receives signal.

**Candidate:** legacy arity dispatch defines three parameters as `(id, args, update)` and supplies
signal only to four-parameter functions as `(id, args, signal, update)`. The candidate's own test
explicitly asserts that a three-parameter tool receives a callable update rather than `RunSignal`.
The assurance calls this a “disclosed Minion-specific constraint,” but `TOOL-024` has disposition
`adopted`; no intentional observable divergence was approved.

**Executable witness:** for `lambda id, args, third: ...`, candidate introspection reports:

```text
wants_update: true
wants_signal: false
```

**Why discriminating:** a tool that wants cancellation but no live-update callback is a valid Pi
tool and receives the signal directly. The candidate requires an unused fourth parameter and
therefore does not implement the adopted capability domain.

**Required remediation:** expose independently selectable signal and update capabilities while
preserving already-certified update-only tools. The mechanism may be Python-idiomatic, but the
public typed/capability surface must represent none, signal-only, update-only, and both. Add all
four witnesses. Do not record the current limitation as adoption.

### L09-R004 — consumers receive cancellation authority and can replace the run signal

**Classification:** `PI_PARITY_DEFECT`.

**Pi/source basis:** consumers receive an `AbortSignal`, which is observational/read-only;
`AbortController` remains private to `Agent.runWithLifecycle`, and public cancellation is owned by
`Agent.abort()`. `Agent.signal` is a getter, not an assignable run-state slot.

**Candidate:** `RunSignal` exposes public `abort()`, and the same object is handed to adapters and
tools. Any consumer can therefore initiate cancellation through the observation handle itself.
`AgentInstance.signal` is also a publicly assignable plain attribute. A listener can replace it
mid-run, violating the “one unchanged signal identity per run” contract and redirecting later
provider/tool requests to the replacement.

**Executable witness:** an `AgentStart` listener stores the original signal, assigns a new
`RunSignal` to `instance.signal`, and allows the run to continue. The candidate reports:

```text
request_is_original: false
request_is_replacement: true
```

An adapter can likewise call `request.signal.abort()` directly, authority Pi's adapter-side
`AbortSignal` does not possess.

**Required remediation:** separate cancellation ownership from the read-only signal view. Only
`AgentInstance.abort()`/the private per-run controller may set the flag; consumers may only poll.
Make the Agent's public signal projection non-replaceable during a run. Add negative authority and
same-identity tests.

### L09-R005 — `transformContext` disappeared from the complete consumer contract

**Classification:** `CONTRACT_ASSURANCE_DEFECT`.

**Pi/source basis:** immediately before every provider request,
`streamAssistantResponse` invokes `config.transformContext(messages, signal)` when configured.
Checkpoint revision 2 explicitly included `transformContext` in its complete consumer matrix.

**Candidate contract:** the current `spec/agent.md` consumer table and `AG-007` claim to cover
every Pi consumer but omit transform-context entirely. Python has no equivalent per-request
transform callback carrying the signal. `AGENT_PRE_STEP` is not equivalent: it runs at input
admission boundaries and changes admitted run context, whereas Pi's transform runs before every
request and returns a provider-local message projection.

**Why discriminating:** a transform may observe abort before a later provider request and either
react or ignore it without mutating the persistent/run-local transcript. Two Rust implementers
cannot infer from the current candidate whether to add this surface, treat pre-step as equivalent,
or omit it.

**Required remediation:** restore this row to the normative consumer matrix and make an explicit
ownership decision. Either add a language-neutral Pi-equivalent per-request transform seam carrying
the same read-only signal, or establish a formally approved disposition with evidence. If the seam
is added as a post-certification delta, audit the affected Layer-04/08 boundaries; do not silently
substitute pre-step. Add a discriminating provider-local/nonpersistent transform witness.

## Manifest/spec/evidence audit

### AG-007

The public idle no-op, per-run lifecycle, provider propagation, batch algorithms, and preflight
priority are correctly described. The row is not currently certifiable as `adopted`: its “same
signal reaches every consumer” claim is false for tool hooks and incomplete for transform-context;
exception-after-abort is not implemented; and public signal authority exceeds Pi.

### AI-027

The optional `Request.signal` field reaches the adapter unchanged and does not alter non-cancelled
Layer-02 behavior. Actual transport cancellation remains correctly deferred to `PROV-004`.
Subject to using the read-only signal view required by `L09-R004`, the additive lower-layer
decision is coherent and Rust-implementable.

### TOOL-024

Preflight priority and batch polling are correct. The row is not currently certifiable as
`adopted` because before/after hooks do not receive signal and the signal-only tool capability is
not representable. Its evidence list tests neighboring behavior but not complete propagation.

### Canonical evidence

The three files `active-abort-tool`, `active-abort-provider`, and `abort-settles-before-idle` remain
unfilled placeholders and are correctly not counted as passing evidence. Explicit language tests
are permissible, but the checkpoint required every load-bearing witness to become permanent
evidence. The candidate lacks discriminating tests for hook signal delivery, transform-context,
exception-after-abort, read-only authority/same identity, prepare-next-turn/should-stop observation,
and abort during `agent_end` settlement. The green suite therefore does not close the complete
matrix.

The code manifest references
`assurance/layers/09-active-abort-rust-checkpoint-rereview.md`, while that path is not present in the
exact docs candidate; it remains remote-reachable only through open review-evidence PR #25. Preserve
and integrate the historical review artifact before eventual final approval.

## Rust feasibility and lower-layer impact

Rust can implement the corrected contract without copying Python mechanics:

- certified Rust Layer 06 already has a read-only `ToolExecutionSignal` trait and a
  `ToolExecutionRequest` carrying signal and update independently;
- the Layer-09 run owner can own a private controller and expose cloned read-only signal handles;
- `LlmRequest` can gain an optional read-only signal handle as the approved additive Layer-02
  delta;
- before/after hook contexts can carry the same handle while retaining typed waterfall behavior;
- Agent-loop listener/prepare/stop contexts can carry or reach the same handle without forced task
  cancellation.

No certified lower-layer semantic contract needs reopening for those changes. They are additive
Layer-09 realizations with mandatory Layer-02/06/08 regressions. The only unresolved ownership
question is the transform-context surface in `L09-R005`; it requires a shared decision before Rust
implementation, not a Rust-only workaround.

## Fresh gate observations

```text
full Python pytest
    1071 passed, 19 xfailed, 0 failed

coverage
    100.00% (2757/2757 statements)

ruff
    PASS

mypy src
    PASS (58 files)

manifest
    78 rows, 78 unique IDs

canonical Layer-09 scenarios
    3 placeholders, 0 executable, 0 counted as evidence
```

The green gates confirm implementation quality for what is tested; they do not override the
source/contract mismatches above.

## Findings and verdict

```text
PI_BEHAVIOR_UNCERTAIN
    none

PI_PARITY_DEFECT
    L09-R001 before/after tool hooks do not receive the signal
    L09-R002 exception-after-abort is synthesized as error
    L09-R003 signal-only tool capability is not representable
    L09-R004 signal observation exposes mutation/replacement authority

CONTRACT_ASSURANCE_DEFECT
    L09-R005 transformContext omitted from the implementation consumer matrix

PARITY_NEUTRAL_HARDENING
    integrate remote checkpoint review evidence and clean stale implementation docstrings

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

Next owner: Claude. Remediate `L09-R001` through `L09-R005` against the exact witnesses above,
synchronize spec/manifest/evidence, and return new exact remote code/docs heads for independent
Rust review. Do not implement Rust Layer 09 or start Layer 10.
