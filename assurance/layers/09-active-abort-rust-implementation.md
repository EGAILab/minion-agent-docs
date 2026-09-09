# Layer 09 — Rust implementation and certification candidate

**Status:** `RUST CERTIFICATION CANDIDATE`; independent cross-language closure review is pending.
Layer 10 was not started.

## Authority and baseline

- merged code baseline: `f94d840453b47e5f6572e05ddeba4c138fe0e250`
- merged docs baseline: `561cdd289973ee607eccbe93a2f578ba535aa50b`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- exact contract candidate approved by the final independent review: code `3c0a916`; docs
  `8dc2b590`
- final approval evidence: docs PR #42, commit `e3649fc`
- Rust implementation candidate: `7437bcc913e6248a5e4f3cca96e351fc91b376ab`

Rust was implemented from pinned Pi and the merged shared contract. Python was not modified and was
used only as secondary evidence. Normative spec and canonical scenarios were not changed.

## Architecture

`runtime/signal.rs` adds one read-only, cloneable `RunSignal` per active run and a crate-private
`RunAbortController`. Only `AgentInstance::abort` can reach mutation authority. `AgentInstance`
installs the controller before publishing `Running`, clears it before publishing `Idle`, exposes no
public controller or signal mutator, treats idle abort as a no-op, and allocates fresh identity for
each independent run.

The same signal identity is propagated through:

- Agent lifecycle event contexts;
- pre-step, prepare-next-turn, and should-stop contexts;
- provider-local transform-context listeners;
- `LlmRequest` and the adapter boundary;
- Layer-06 before/after hook contexts and `ToolExecutionRequest`.

The signal is cooperative and poll-based. No task cancellation, forced interruption, transport
cancellation, or Layer-10 behavior was added. A consumer may ignore the signal and complete
normally.

Rust models authoritative metadata with typed APIs. Transform listeners may replace only the
provider-local message vector; Agent identity and signal are not part of the replacement type.
Before/after hook normalization restores the original signal at every raw waterfall handoff. This
is the idiomatic typed realization of the shared authority and delegation grammar, not a port of
Python tuple-arity mechanics.

## Agent and failure semantics

- The signal remains live through awaited `agent_end` listeners and is cleared only during final
  run settlement.
- An exception settled while the live signal is aborted produces a represented assistant result
  with `StopReason::Aborted`; otherwise it remains `Error`.
- Failure settlement continues to read the live persistent Agent model, not a run-local model
  override.
- Reset remains illegal while the Agent is active, including after abort is requested.
- No synchronous status-observer extension exists in Rust; therefore the Python-specific
  reservation/rollback mechanism is neither needed nor duplicated. Rust preserves the shared
  observable entry/exit ordering directly.

## Tool semantics

Layer 09 extends the existing Layer-06 executor rather than introducing a second engine.

- unknown-tool, preparation, validation, and throwing-before-hook outcomes retain priority over an
  already-aborted signal;
- after a returning before-hook waterfall, abort produces exact `Operation aborted` and wins over a
  returned block decision;
- `execute` receives the same cooperative signal independently of its structured update callback;
- the after-hook always runs after execution was reached and receives the same signal;
- sequential mode polls after each complete call lifecycle and truncates later calls;
- parallel mode polls after each sequential preflight outcome, truncates later preflight, and still
  executes all calls prepared before the poll through the existing concurrent barrier.

The A/B/C regression proves the last rule: A is retained as prepared, B aborts during preflight and
finalizes immediately as aborted, C is never started, then A executes and finalizes. Results remain
source ordered.

## Transform-context semantics

`register_transform_context_listener` is a serial, typed, provider-local chain invoked immediately
before every provider request. A listener may continue with no change, continue with replacement
messages, or settle the chain with replacement messages. Listener failure is routed through the
existing Layer-08 run-failure boundary. Neither persistent Session messages nor run-local context
messages are mutated, and signal/Agent authority cannot be redirected through the return type.

## Canonical and evidence status

The three Layer-09 canonical documents remain explicit
`TO_BE_FILLED_FROM_PINNED_PI_BEHAVIOR` placeholders:

- `active-abort-provider.yaml`;
- `active-abort-tool.yaml`;
- `abort-settles-before-idle.yaml`.

They are deferred and are not counted as passing canonical evidence. This implementation therefore
uses the approved explicit-language-test evidence path. Existing Layer 01–08 canonical adapters and
all executable scenarios remain green through `xtask conformance verify`; no runner simulates abort
semantics.

## Rust tests

New discriminating evidence covers:

- read-only Agent-owned authority, idle no-op, active observation, abort, settlement, and fresh
  per-run signal identity;
- one signal identity across lifecycle, transform, provider, before-hook, execute, and after-hook;
- provider-local transform behavior and unreplaceable authoritative metadata;
- pre-step, prepare-next-turn, and stopping consumers;
- aborted exception classification and live persistent-model failure identity;
- abort requested during `agent_end` listener settlement;
- the complete preflight error/abort/block priority;
- unconditional after-hook execution after cooperative abort;
- sequential and parallel batch truncation, including the A/B/C barrier witness.

All lower-layer tests remained enabled. The full workspace gate passed **287 tests**.

## Fresh quality gates

- `cargo fmt --all -- --check`: PASS.
- `cargo clippy --workspace --all-targets --all-features -- -D warnings`: PASS.
- `cargo test --workspace --all-features`: PASS, 287 tests.
- `RUSTDOCFLAGS="-D warnings" cargo doc --workspace --no-deps`: PASS.
- `cargo run -p xtask -- conformance verify`: PASS.
- shared schema validation: PASS, 185 tests.
- manifest validation: PASS, 79 rows / 79 unique IDs.
- `git diff --check`: PASS.

Sensitive regression families passed within the full workspace gate: Runtime event ordering and
waterfall normalization, typed LLM request/stream behavior, Session derivation/reset, XFORM,
ToolRegistry visibility, Layer-06 execution/update/barrier behavior, and Layer-07 Agent/Inbox state.

## Traceability

Only Rust evidence fields were updated in `pi-parity-manifest.yaml`, for `AI-027`, `AG-007`,
`AG-023`, and `TOOL-024`. Their Pi pointers, shared rules, dispositions, Python evidence, and
canonical status are unchanged.

## Findings and boundary

- `PI_PARITY_DEFECT`: none active.
- `CONTRACT_ASSURANCE_DEFECT`: none active.
- `PI_BEHAVIOR_UNCERTAIN`: none active.
- `PARITY_CONSTRAINED_RISK`: none blocking.
- `PARITY_NEUTRAL_HARDENING`: typed read-only signal/controller split; typed transform replacement;
  pointer-identity equality for signal witnesses.

Actual provider/network transport cancellation remains deferred to `PROV-004`. Layer 10 was not
started.

## Handoff verdict

Python Layer 09 remains certified. Rust Layer 09 is a certification candidate at the exact SHA
above. Cross-language Layer 09 is **not closed** until the independent shared/Python owner verifies
this candidate and completes the merge/closure workflow.

## Independent closure verification (shared/Python owner)

Performed against the exact reviewed SHAs -- code PR #18 at
`7437bcc913e6248a5e4f3cca96e351fc91b376ab`, docs PR #43 at
`9f9c622ff6f62b22d9d161ea6dc5c6b91f6bca61` -- fetched directly from GitHub into
`review-worktrees/rust-layer-09-impl` (a clean worktree; `git status --short` confirmed empty
before and after this review), not read from local-only or chat-reported state. Coordination
issue #16 (`STATUS: CLOSURE_REVIEW`, `NEXT_OWNER: Claude`) and both candidate PRs were confirmed
open, mergeable, and unmerged before verification began.

**Scope confirmation:** `gh pr diff 18` covers exactly `minion-agent-rust/**` (12 source/test
files) plus `pi-parity-manifest.yaml`. The manifest diff touches only the `rust:` evidence field
on exactly four rows (`AI-027`, `AG-007`, `AG-023`, `TOOL-024`) -- their own `id`/`pi`/`rule`/
`tests`/`python`/`disposition` fields are byte-for-byte unchanged. No `minion-agent-python/**`
path appears anywhere in the diff. Docs PR #43 touches exactly one new assurance file (this one) --
no `spec/**` or `conformance/**` path changed.

**Architecture read, independently, before reading this file's own claims:** confirmed directly
from source (`agent/instance.rs`, `agent_loop/driver.rs`) that `AgentInstance::try_begin_run`/
`finish_run` never invoke listener code between claiming entering input and committing to a run --
both the status/controller flip and the subsequent `Inbox` claim are synchronous, non-`async`
calls with no `.await` between them, and `finish_run` itself is a plain field-write with no
dispatch of any kind, invoked unconditionally via `PreparedRun`'s own `Drop` impl regardless of
success, failure, or early return. This independently confirms the "no synchronous status-observer
extension exists in Rust" claim above BEFORE reading it -- the Python-specific `_Reservation`
mechanism genuinely has no applicable Rust counterpart, not merely an undisclosed one.

Read `agent_loop/decisions.rs` directly: `AGENT_TRANSFORM_CONTEXT`'s Rust realization
(`TransformContextAction::{Next(Option<Vec<Message>>), Replace(Vec<Message>)}`) cannot express an
`instance`/`signal` replacement in its own type at all -- the `L09-R018` leading-vs-trailing-
omission ambiguity is structurally unrepresentable, not merely avoided by convention. `pre_step`/
`prepare_next_turn` use the pre-existing (unmodified by this PR) `EventBus::waterfall_normalized`
primitive with a field-level closure (`delegated.signal = authoritative.clone()`) rather than a
positional-tuple transform -- confirmed by reading `runtime/event.rs::run_waterfall` directly that
the normalize closure is applied at every listener-to-listener handoff, matching the shared
contract's own normative rule.

Read `tools/execution.rs` and the `parallel_abort_stops_future_preflight_but_runs_already_
prepared_calls` test directly: reproduces the required A/B/C scenario exactly (A prepared and
executed; B aborts during its own before-hook and settles immediately via the preflight-priority
path, never reaching `execute`; C's own before-hook never runs at all) with the correct message
count (2, not 3 -- C produces no result at all, matching Pi's own truncation semantics already
certified at Layer 06), not merely a passing test taken on faith.

**Gates independently re-run**, not accepted from the candidate's own report:

```text
cargo fmt --all -- --check                                   PASS (reproduced)
cargo clippy --workspace --all-targets --all-features
    -- -D warnings                                            PASS (reproduced)
cargo test --workspace --all-features                        287 passed, 0 failed (reproduced,
                                                                exact count matches)
RUSTDOCFLAGS="-D warnings" cargo doc --workspace --no-deps    PASS (reproduced)
cargo run -p xtask -- conformance verify                      PASS, exit 0 (reproduced)
git diff --check (main..candidate)                             PASS (reproduced)
pi-parity-manifest.yaml parse + unique-ID audit                79 rows / 79 unique (reproduced,
                                                                independent parse)
shared schema validation (pytest tests/conformance/
    test_schema_validation.py)                                 185 passed (reproduced)
```

**Canonical placeholder audit:** read `conformance/agent/abort-settles-before-idle.yaml` directly
-- still genuinely `TO_BE_FILLED_FROM_PINNED_PI_BEHAVIOR`/`TO_BE_BOUND_TO_REAL_PUBLIC_API`/
`TO_BE_PINNED_EXACTLY`, not fabricated or silently marked filled. `active-abort-provider.yaml`/
`active-abort-tool.yaml` confirmed the same by file listing; all three remain excluded from
`xtask conformance verify`'s own passing scope, matching the disclosed evidence policy.

**Baseline currency:** `origin/main` at `f94d840453b47e5f6572e05ddeba4c138fe0e250` and
`origin/master` at `561cdd289973ee607eccbe93a2f578ba535aa50b` independently confirmed to be the
CURRENT tips of both default branches at review time, matching the baselines this candidate and
the final approval (docs PR #42) both declare -- neither PR was building on stale state.

No active blocker found. Both candidates approved at the exact reviewed SHAs and merged:

- code PR #18 -> `main`, merge commit `6c10aa5d75b2c78dbb999278363b156c99cf4b70`
- docs PR #43 -> `master`, merge commit `5209ab75d970eab1d22d5b739b50b36cbabaf680`

Workflow `§14` retrospective performed at closure -- two reusable lessons promoted into
`process/agent-workflow.md` (multi-field authority-protection witnesses; Rust-applicability
characterization for a defect's own root extensibility point), recorded in full at
`assurance/process-history.md`'s own Layer 09 entry.

## Candidate verdict

```text
Python Layer 09
    CERTIFIED

Rust Layer 09
    CERTIFIED

shared Layer-09 contract
    APPROVED / IMPLEMENTED / CLOSED

Layer 09 cross-language
    CROSS-LANGUAGE CERTIFIED / CLOSED

Rust certified through
    Layer 09

Layer 10
    ELIGIBLE / NOT STARTED
```
