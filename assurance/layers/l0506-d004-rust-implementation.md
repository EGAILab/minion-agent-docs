# L0506-D004 — Rust per-call ToolExecutionContext candidate

## Authority and scope

Coordination: `minion-agent#131`, Rust handoff comment `5970155587`; delegated routine lifecycle under `#75`. Shared/Python approval is docs #233 comment `5970150389`. Accepted baselines:

- code/main `0e2a04ca16a4e7086d98c7b9002ab3de0a0a8a5c`;
- docs/master `20776f0f5df78d73c556be8aef4fda83c6a449fb`.

Semantic sources: Owner WP133-F3 Option A (`#50` comment `5951046523`), `spec/tools.md` “Per-call tool execution context”, and pinned Pi `b7bb00b936dbe21b8e160b3e89efdec361846699`. Pi's `packages/coding-agent/src/core/tools/tool-definition-wrapper.ts:17-18` calls `ctxFactory` inside the wrapped execute invocation. Its session/extension wrapper supplies the executing runner's context; the standalone core loop supplies none. Rust maps that delivery into an owned typed request field rather than copying Python's keyword/arity machinery.

Exact code candidate: `bd9358cc2877868cce238355a870f5a43e0b724d`, branch `layer/l0506-d004-rust`, pushed and checked using `git ls-remote`. The paired docs head is recorded in the PR/handoff (a commit cannot embed its own SHA).

This candidate neither changes the shared semantic contract nor implements bash consumption, persisted session files, or context delivery to hooks. Python source is untouched. TOOL-042's Rust field is evidence-only; its existing rule/disposition and all Python pointers are unchanged.

## Mechanism

`tools/definition.rs` defines `ToolExecutionContext` with private owned fields and read-only getters. It has no agent reference, interior mutability, or setters. `session_file` is `None`; `off` is a present reasoning-level string. The caller can construct a separate snapshot but cannot modify a snapshot's fields.

`ToolExecutionRequest.context` is `Option<ToolExecutionContext>`. Existing tools ignoring it keep their results; three binding-level direct request literals add explicit `None`. No hook payload changes.

`ToolExecutionOptions::with_context_provider` explicitly carries a typed per-call provider. Both sequential and parallel paths pass it to the existing execute/finalize seam. It is evaluated only for a successfully prepared, validated and unblocked call, immediately before invoking the tool. The provider's `ToolCapabilityError` remains inside the ordinary execution-result boundary: error conversion, after-hooks and end delivery run, and a sequential sibling still executes. This preserves the existing Rust typed-error convention; it does not introduce panic recovery absent from the existing tool boundary.

`AgentInstance::tool_execution_context` reads the model and thinking level under one short state lock and copies the immutable session id. No lock crosses a lower-layer call or tool invocation. The driver supplies a closure bound to that executing instance. Per-step provider configuration and process environment are not consulted.

## Acceptance witnesses

Eight new Rust tests exercise the real certified seams:

| Witness | Boundary proved |
|---|---|
| driver `per_call_context_is_fresh_in_one_batch_and_prior_snapshot_is_immutable` | One sequential batch, two calls; first changes the authoritative model/level. Second sees new values, first remains unchanged. `off` and absent session file are explicit. Conflicting prepared provider overrides do not leak. |
| driver `concurrent_agents_share_a_registration_without_sharing_context` | Two real agent pipelines share one registered tool, overlap at a barrier, and observe their own session/model/level. Parallel execution path is exercised. |
| `context_absent_without_provider_and_ignoring_context_is_valid` | Generic batch without a provider delivers `None` and succeeds. |
| `provider_failure_is_a_tool_error_with_end_and_healthy_sibling` | First factory fails, tool body is skipped; after-hooks see error then success, two end deliveries occur, sibling succeeds. No batch-level escape. |
| `provider_not_sampled_for_missing_or_preaborted_calls` | Missing tool and pre-aborted call do not evaluate the factory. |
| `provider_runs_after_before_hooks_and_never_for_a_blocked_call` | Blocked call never samples; surviving call samples after its before-hook. Existing after-hook payload receives no new context. |
| `snapshot_is_owned_and_preserves_absent_and_off` | Independent owned data, absent file, present `off`. |
| `a_tool_ignoring_the_new_field_has_identical_results` | Actual pipeline messages/termination identical with and without explicit context. |

Agent witnesses run the real driver tool-call admission/execution/session path using `prepare_prompt_run` and `run_tool_calls`, not a fabricated context adapter. There is no new shared canonical scenario family: the accepted contract characterizes these as binding-level witnesses and the typed seam is tested directly.

## Discriminating controls and restoration

Each control was applied individually to production source, executed against the named permanent witness, then restored. All produced a genuine test assertion failure (cargo exit 101), not a compilation failure. Local logs are `.tmp/d4-rust/mutant-{batch,boundary,sentinel,off,capture}.log`.

1. **Once-per-batch capture:** replace `with_context_provider`'s stored callable with `let captured = provider();` and a closure cloning that result. The same-batch agent witness observes old `provider` instead of `next-provider` and fails.
2. **Outside ordinary execution boundary:** evaluate the provider before `let executed`, map its error to `ToolLifecycleError`, and remove sampling inside the execute future. The failure/finalization/sibling witness receives an escaping batch `Err(Lifecycle(...))` and fails.
3. **Absent sentinel:** change the agent snapshot's file `None` to `Some("none")`. The same-batch witness fails the absent-file assertion.
4. **Off omitted:** change `Some(level.to_owned())` to `None` when level is `off`. The same-batch witness fails the present-off assertion.
5. **Shared first-context capture:** cache the first projected context in a static `OnceLock` and clone it for later calls. This deliberately models a registration/ambient shared capture's incorrect observable consequence, not a claim that Rust registrations need a global. The concurrent shared-registration witness sees the first agent's context twice and fails.

The latter control rejects the shared-capture consequence; the per-batch control separately rejects eager capture with independent batch providers. Every control was removed. The restored pipeline witnesses and both restored agent witnesses pass; `git diff` contains only intended changes, with no static cache, sentinel, off omission, or escaped provider evaluation.

## Fresh gates and reproducibility

Rust toolchain: `1.97.1`; Windows x86_64. Both language bindings use the verified pinned ICU4C 78.3 build, with `RUST_ICU_MAJOR_VERSION_NUMBER=78`, its native library directory in `RUSTFLAGS`, its bin directory in `PATH`, and `MINION_AGENT_ICU_IDENTITY` pointing to `pinned-icu-identity.txt`.

The new worktree's first debug build exhausted drive E. Only this task's generated Cargo target was removed with `cargo clean` (5.1 GiB); no source, user artifacts or earlier task targets were deleted. Subsequent builds use a task-private target on drive C, `CARGO_INCREMENTAL=0`, and `CARGO_PROFILE_DEV_DEBUG=0` / `CARGO_PROFILE_TEST_DEBUG=0`. These affect build artifacts, not tool behavior. No dependency or lockfile change is needed; the existing cached dependencies permit offline Cargo execution.

Fresh gates:

- `cargo fmt --all -- --check`: PASS.
- `cargo clippy --workspace --all-targets --all-features -- -D warnings`: PASS.
- `cargo test --workspace --all-features`: **527 passed / 0 failed / 0 ignored**, 80 result sections including empty doctest targets. Both agent tests and the final six pipeline tests are included. The existing mutation corpus is slow on this Windows host (one target took 289 seconds), but completed successfully.
- `RUSTDOCFLAGS=-D warnings cargo doc --workspace --no-deps`: PASS.
- `cargo run -p xtask -- conformance verify`: PASS.
- Shared manifest/schema validation: **404 passed** (focused Python validation suite, `--no-cov`; a partial-suite coverage run is not a whole-Python coverage claim).
- Five controls: five genuine RED results; restored context witnesses: **8/8 GREEN**.

Pinned-ICU environment was also used for the focused restored witnesses. MSVC emits its existing non-failing LNK4098 default-library warning when linking test binaries; clippy's strict gate and rustdoc's warning-denial gate pass without a Rust diagnostic. Local gate transcripts live in `.tmp/d4-rust/{cargo-test,clippy,rustdoc,conformance,d004-pipeline}.log`. No full Python suite was rerun for this Rust-only delta; its shared validation subset was run freshly.

## Status and stop

Shared/Python L0506-D004: already approved/merged and Python certified at the accepted baselines. Rust: **implementation candidate, independent CLOSURE_REVIEW pending**. Cross-language: **NOT CLOSED**. The implementation does not certify itself. No Rust bash consumer or next layer is authorized by this record.
