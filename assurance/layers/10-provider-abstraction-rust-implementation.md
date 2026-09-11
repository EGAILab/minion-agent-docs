# Layer 10 — Rust implementation and certification candidate

**Status:** `RUST CERTIFICATION CANDIDATE`; independent cross-language closure review is pending.
Layer 11 was not started.

## Authority and baseline

- merged code baseline: `95266a1af7bfe9856140c77e6fc1f99c6294f5b9`
- merged docs baseline: `87914bd2ae3d6dbae60b87c30a0ac9ff1ebd4d2e`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- exact shared/Python candidate approved by the final independent review: code
  `ea4f250fe0c6d640036960459dd74711795a51d7`; docs
  `a99f348f947431ecfa1b09cdc00f137f3fd0cd80`
- final approval evidence:
  `assurance/layers/10-provider-abstraction-final-contract-rereview-3.md`, including its appended
  `L10-I001` exact-SHA erratum
- implementation preflight evidence:
  `assurance/layers/10-provider-abstraction-rust-implementation-preflight.md`
- Rust implementation candidate: `feda44dcecc24eb03c8e531a9aa60f2c23d71f58`

The implementation began only after code PR #21 and docs PR #49 repaired and merged the two
preflight evidence defects. Rust was implemented from pinned Pi and the merged shared contract.
Python was not modified and was used only as secondary evidence. Normative spec, schemas,
canonical operations, and canonical expected observations were not changed.

## Preflight closure

- `L10-I001`: **CLOSED**. The immutable approval artifact now has an appended erratum identifying
  the exact PASS-7 candidate it audited.
- `L10-I002`: **CLOSED**. The three stale scenario notes now describe the real Pi comparison
  surfaces and the owner-approved Minion registry-granularity divergence. Their executable content
  is unchanged.

## Rust architecture

`LlmAdapter::start` now returns `RawAssistantStream` directly. Once a model identity resolves and
the adapter is invoked, expected request/provider/runtime failures have no eager typed channel;
they settle through the returned stream. `LlmStartError::UnknownModel` remains the deliberately
eager unresolvable-identity boundary. `ScriptedAdapter` represents script exhaustion as an in-band
runtime stream error, matching the same settlement rule.

`LlmService` owns one synchronized full-identity registry. Each `register` or `register_models`
call allocates opaque per-call ownership and returns `LlmRegistration`. Its `withdraw` method is
repeatable and idempotent, removes only identities still owned by that registration call, and
cannot remove later replacements—even when the exact same adapter object is registered again.
One multi-model handle owns all identities from its call, while partial replacement leaves its
unreplaced identities withdrawable. `models()` reports the current registry surface in deterministic
full-identity order.

The service clones the selected adapter out of the registry before invoking it. No registry lock is
held across adapter/provider code, and no Python-shaped dynamic state or second model authority was
introduced.

## Canonical evidence

The new `llm_service_conformance.rs` adapter discovers and executes all seven current
`llm-service-*.yaml` scenarios:

- adapter-detected failure settles in-band;
- registration and replacement;
- withdrawal without replacement;
- stale withdrawal after replacement;
- introspection of current registrations;
- same adapter fixture registered through two distinct handles;
- more than eight stream observations.

The runner parses, validates references, dispatches to the real typed `LlmService`, and normalizes
observations. It does not implement registration ownership, replacement, withdrawal, introspection,
or stream settlement. Ownership observations use the real adapters' request-count deltas and fail
unless exactly one adapter handled the request.

## Rust language tests

Focused tests prove:

- resolved adapter detection failure and exhausted scripted responses settle in-band;
- unknown model identity remains the only eager service-start error;
- withdrawal handles are repeatable, idempotent, stale-safe, and scoped to registration-call
  identity rather than adapter object identity;
- one registration can own multiple identities;
- partial replacement does not make a handle remove entries it no longer owns;
- current model introspection reflects replacement and withdrawal;
- existing Agent-loop recovery distinguishes eager resolution failure from represented stream
  failure.

All lower-layer tests remained enabled. The full workspace gate passed **292 tests**.

## Fresh quality gates

- `cargo fmt --all -- --check`: PASS.
- `cargo clippy --workspace --all-targets --all-features -- -D warnings`: PASS.
- `cargo test --workspace --all-features`: PASS, 292 tests.
- `RUSTDOCFLAGS="-D warnings" cargo doc --workspace --no-deps`: PASS.
- `cargo run -p xtask -- conformance verify`: PASS.
- shared schema and manifest validation: PASS, 205 tests.
- manifest parse/unique-ID audit: PASS, 84 rows / 84 unique IDs.
- `git diff --check`: PASS.

The full workspace gate includes the certified Runtime, LLM message/stream, Session, XFORM, Tool,
Agent state/inbox, Agent-loop, and active-abort regression suites.

## Traceability

Only Rust evidence fields were updated in `pi-parity-manifest.yaml`, for `AI-028` and `AI-030`.
Their Pi pointers, shared rules, tests, Python evidence, and dispositions are unchanged.

`AI-031` (`streamSimple`) and `AI-032` (`fetchDeferred` / `cancelDeferred`) remain explicit
Layer-11 deferred-parity obligations. This pass did not implement or claim them.

## Findings and boundary

- `L10-R003`: **RESOLVED** by removing the resolved-adapter eager expected-error channel.
- `PI_PARITY_DEFECT`: none active.
- `CONTRACT_ASSURANCE_DEFECT`: none active.
- `PI_BEHAVIOR_UNCERTAIN`: none active.
- `PARITY_CONSTRAINED_RISK`: none blocking.
- `PARITY_NEUTRAL_HARDENING`: opaque per-registration ownership, stale-safe idempotent handles,
  deterministic introspection, and lock-free adapter invocation.

No real-provider wire encoding, `streamSimple`, deferred provider operation, or other Layer-11
behavior was added.

## Handoff verdict

Python Layer 10 remains certified. Rust Layer 10 is a certification candidate at the exact SHA
above. Cross-language Layer 10 is **not closed** until the independent shared/Python owner verifies
the candidate and completes the merge/closure workflow.

