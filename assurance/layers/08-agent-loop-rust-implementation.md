# Layer 08 — Rust implementation, conformance, and certification candidate

**Status:** `CROSS-LANGUAGE CERTIFIED / CLOSED` (independent final closure verification complete,
below). Layer 09 was not started.

## Authority and starting state

- accepted code baseline: `490d0d05c2d229ac003006ba31b2cd43a5e96060`
- accepted docs baseline: `4a3156d1fbcf4488ecc1207f0aa8de1bf72f5f1f`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- final contract approval: `assurance/layers/08-agent-loop-rust-contract-r014-rereview-pass14.md`
- Rust implementation candidate: `1fb88002d1093203787db85bf57b8c7d71dd18ba`

The implementation resumed from the merged PASS-14 contract. It did not derive Rust semantics from
the Python control flow and did not modify Python, normative spec, or canonical scenario semantics.

## Rust architecture

Rust adds a typed `agent_loop` module split by semantic responsibility:

- `context.rs`: shallow run-local context snapshots over typed messages and visible tools;
- `decisions.rs`: typed pre-step, prepare-next-turn, and stop-decision event seams;
- `events.rs`: complete typed Agent lifecycle vocabulary and serial live dispatch;
- `state.rs`: reduce-before-listener Agent-state projection;
- `driver.rs`: guarded prompt/continue admission, one-turn provider/tool execution, continuation,
  failure recovery, and the Minion follow-up pump;
- `error.rs`: typed public boundary and eager-start errors.

The implementation reuses the certified `Message`, `LlmService`/stream, `Session`, `Context`, Inbox,
ToolRegistry, and Layer-06 executor. It introduces no duplicate transcript, registry, queue, message
transform, or tool-execution authority.

## Contract realization

- Run entry takes shallow top-level snapshots of system prompt, effective messages, and visible tools,
  with independent run-local model/thinking configuration.
- `prepareNextTurn` may replace the whole run-local context and model/thinking values without
  mutating persistent Agent state or leaking to later runs.
- Dynamically added tool names extend only the current run context through the certified tool result
  metadata path.
- Prompt and continuation enforce their exact active/no-transcript boundaries, typed Message batches,
  and text-plus-images convenience normalization.
- First-turn prompt lifecycle completes before the initial steering claim; continuation pre-drains do
  not double-claim steering.
- Full certified stream partials drive `streaming_message`; lifecycle order is
  `message_start -> message_update* -> message_end`.
- Agent and tool lifecycle events dispatch live through the real serial listener seam. State/log
  reduction precedes listener observation, listener rejection is fail-fast, and accepted update
  dispatches join before final tool completion.
- Tool continuation, prepare/stop decisions, steering, and follow-up retain Pi ordering. Tool-result
  `terminate` suppresses only tool-driven continuation; represented `error`/`aborted` is immediately
  terminal.
- Unexpected run failures synthesize exactly the Pi recovery trace without an invented turn start.
  The failure identity reads the Agent's live persistent model at settlement: a run-local model B is
  excluded, while a later persistent mutation C is included.
- `AgentEnd.messages` is invocation-local, including the distinct synthesized-failure override.
- `run_until_idle` is the approved Minion follow-up pump with typed causes/origins and wake handling;
  it does not add a step cap, boundary-stop API, or Layer-09 abort propagation.

## Implementation-exposed lower-layer remediation

Canonical RED work exposed two Rust implementation gaps in already-approved lower-layer rules:

1. Inbox envelopes lacked the approved stable ID/origin projection and the real follow-up pump lacked
   complete typed causes/end reasons. Commit `b408d731c3cab6c71df1fc04af3e5cee79199160`
   repaired those seams and passed independent review.
2. A Layer-06 before-hook block could not carry `terminate=true`. Commit
   `855b370b8ddf50de514e68668c3e49f7931d5691` added the typed reason/termination shape and propagated
   it through the immediate end result and non-empty unanimity fold. Focused RED produced four
   `E0559` errors against the old shape; GREEN passed 22 Layer-06 language tests and the canonical
   adapter. Independent review approved the repair.

Neither repair changed the shared contract or reopened a certified lower-layer semantic rule.

## Canonical conformance

The Rust adapter dynamically inspects all Agent YAML documents by semantic shape:

- 79 discovered;
- 35 executable Layer-08 scenarios executed and passed;
- 19 pinned-Pi placeholder documents deferred and never counted as passing;
- 25 primitive-family documents delegated to their existing adapters;
- 0 unclassified.

The adapter constructs scripted typed dependencies, invokes real `AgentLoop`, Agent/Inbox, Session,
LLM, ToolRegistry/executor, hooks, and listeners, then normalizes observations. It does not claim or
clear queues, choose continuation order, derive Session history, reconstruct streaming state,
synthesize lifecycle/failure recovery, fold termination, inject dynamic tools into run context,
sort traces, or calculate expected outcomes.

## Tests and gates

Fresh certification results at `1fb88002d1093203787db85bf57b8c7d71dd18ba`:

- `cargo fmt --all -- --check`: PASS.
- `cargo clippy --workspace --all-targets --all-features -- -D warnings`: PASS.
- `cargo test --workspace --all-features`: PASS, 277 tests.
- `RUSTDOCFLAGS="-D warnings" cargo doc --workspace --no-deps`: PASS.
- `cargo run -p xtask -- conformance verify`: PASS.
- Layer-08 canonical adapter: 2/2 harness tests; 35/35 executable scenarios passed.
- shared schema validation: 185/185 passed (`--no-cov`; the initial targeted invocation's schema
  assertions also passed but the repository-wide coverage wrapper correctly had no production
  coverage to measure).
- manifest validation: 76 rows / 76 unique IDs; all eleven Layer-08 Rust fields are implemented or
  explicitly Layer-09-deferred.
- `git diff --check`: PASS.

Sensitive Layer 01–07 regressions passed within the full workspace gate, including Runtime listener
ordering, typed LLM streams, Session reset/effective derivation, XFORM, ToolRegistry visibility,
Layer-06 parallel execution/update ordering and termination, and Layer-07 Agent/Inbox reset and wake
semantics.

## Independent final Rust review

A separate exact-SHA review approved `1fb88002d1093203787db85bf57b8c7d71dd18ba` as the Rust
certification candidate. It audited the complete baseline diff, every Layer-08 manifest row and
evidence pointer, all high-risk state-machine/event/failure/pump/tool paths, the two L08-R014
witnesses, canonical runner thinness, and the Layer-09 boundary. Its fresh package gate passed
267/267 tests. It made no edits and found no blocker.

## Traceability

AG-001 through AG-006, AG-008 through AG-010, and AG-021 now point to real Rust production,
language-test, and canonical evidence. AG-007 remains explicitly deferred to Layer 09. Only `rust:`
evidence fields changed; Pi pointers, normative rules, tests, phase, and dispositions are unchanged.

## Findings

- `PI_PARITY_DEFECT`: none active.
- `CONTRACT_ASSURANCE_DEFECT`: none active.
- `PI_BEHAVIOR_UNCERTAIN`: none active.
- `PARITY_CONSTRAINED_RISK`: none blocking.
- `PARITY_NEUTRAL_HARDENING`: typed Rust vocabulary, RAII run settlement, narrow lock scopes, and
  deterministic ordered collections.

## Independent final closure verification

Performed directly against the exact merged candidate SHAs -- code `minion-agent@main`
`3ec1a386c86a93a13344ed38d796fbb74e9817bd` (squash-merged from PR #14 @
`1fb88002d1093203787db85bf57b8c7d71dd18ba`), docs `minion-agent-docs@master` (this PR, from
`80ba30b40e90abc41f558ac63a48a96852e76052`) -- via a disposable worktree
(`minion-agent/.worktrees/rust-layer-08-final-closure-code`), never modified:

```text
cargo fmt --all -- --check                                       PASS
cargo clippy --workspace --all-targets --all-features -- -D warnings   PASS
cargo test --workspace --all-features                            PASS, 277/277 (exact match)
RUSTDOCFLAGS="-D warnings" cargo doc --workspace --no-deps        PASS
cargo run -p xtask -- conformance verify                          PASS (exit 0)
cargo test -p minion-agent --features conformance
    --test agent_loop_conformance -- --nocapture                 PASS, 2/2 harness tests
    (all_layer_08_scenarios_drive_the_real_rust_agent_loop iterates every executable
    Layer-08 canonical document and panics with the failing path on any mismatch --
    confirmed non-vacuous by reading the harness source directly, not merely trusting
    the reported 35/35 count)
```

Both `L08-R014` witnesses read directly from source and confirmed non-vacuous
(`crates/minion-agent/tests/agent_loop_failure.rs`):

- `run_local_model_replacement_does_not_change_synthesized_failure_identity` asserts the
  failure identity equals the persistent model A, not the run-local `prepareNextTurn`
  replacement B;
- `persistent_model_mutation_during_run_is_read_live_by_failure_settlement` asserts the
  failure identity equals C, a persistent-model mutation applied while the run was still
  active -- confirming the live-read (not construction-time-snapshot) semantics
  `spec/agent.md`'s own PASS-14 correction specifies, matching Python's own
  `test_settle_run_failure_uses_the_agents_persistent_model_not_the_run_local_override`/
  `test_settle_run_failure_reports_the_live_persistent_model_not_a_run_start_snapshot` exactly.

`git diff` between the accepted shared baseline (`490d0d0`) and the Rust candidate
(`1fb8800`) confirmed the change is scoped correctly: only `pi-parity-manifest.yaml`'s own
`rust:` evidence fields changed outside `minion-agent-rust/**` (10 rows: AG-001 through
AG-006, AG-008 through AG-010, AG-021 -- `id`/`pi`/`rule`/`tests`/`python`/`disposition`
fields on every row unchanged); no Python, spec, or canonical-scenario semantic file was
touched. Manifest re-validated: 76/76 unique rows, zero rows still reading `PENDING`
(`AG-007` remains correctly `NOT_APPLICABLE -- deferred to Layer 09`, its own long-standing,
unaffected disposition). A grep for `abort`/`cancel` in `agent_loop/` found only a pre-existing
test name for the already-in-scope represented-terminal classification -- no Layer-09
cancellation machinery was introduced.

Every reported result was independently reproduced at the exact SHA, not merely re-stated from
the candidate's own report or the separate independent package reviewer's own 267/267 (a
narrower package-scoped subset of this same 277).

## Candidate verdict

```text
Python Layer 08
    CERTIFIED

Rust Layer 08
    CERTIFIED

shared Layer-08 contract
    APPROVED / IMPLEMENTED / CLOSED

Layer 08 cross-language
    CROSS-LANGUAGE CERTIFIED / CLOSED

Rust certified through
    Layer 08

Layer 09
    ELIGIBLE / NOT STARTED
```
