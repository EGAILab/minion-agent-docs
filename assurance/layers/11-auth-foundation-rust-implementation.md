# Layer 11 Pass 1 — Rust auth-foundation implementation candidate

**Status:** `RUST CERTIFICATION CANDIDATE`; independent shared/Python-owner closure review is
pending. Layer 12 was not started.

## Authority and baseline

- merged code baseline: `79eb321b25ad77a7598d69edc4a37c3f9c0ba717`
- merged docs baseline: `2fccfa01948ba8f87586a84c9da89c4072d5e862`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- exact approved shared/Python candidate: code
  `78e6fbf0b04fea377b0ee9a71ad917b98fe06f04`; docs
  `5f7e1a17a9f8f033e5a1f9f32801f2bc266bb48c`
- approval evidence:
  `assurance/layers/11-auth-foundation-final-complete-rust-contract-review-10.md`
- Rust implementation candidate: `47003df7aea11d5334ef76b3b4238fe8bd49fa5e`

Rust was implemented from pinned Pi and the merged shared contract. Python was consulted only as
secondary evidence after the language-neutral mapping was established. No normative spec,
canonical scenario, schema, expected observation, or disposition changed. The only shared change
is the Rust evidence pointer for `PROV-006` through `PROV-010`.

## Rust architecture

The new `minion_agent::auth` module owns the provider-neutral Layer-11 foundation:

- typed auth vocabulary and an injectable `AuthContext`;
- shared-mutable credential handles whose clones and nested `env`/`extra` handles retain Pi's live
  reference identity;
- a generic `CredentialStore` contract and insertion-ordered in-memory reference implementation;
- an auth-local read-only `Abortable` capability, explicit abort controller for standalone auth
  work, and caller/deadline `CombinedSignal`;
- double-checked OAuth refresh authority;
- RFC-7636 PKCE generation and deterministic challenge derivation;
- the RFC-8628 device-code poll state machine and injectable clock.

The store uses one asynchronous gate per provider and never holds its credential-map lock across
an injected modifier. Same-provider mutations serialize; distinct providers do not share a gate;
reads/listing are unsynchronized observations of the current committed map. A cancelled caller's
wait stops promptly while the spawned operation remains live, and the operation's post-callback
checkpoint discards a late result.

Credential scalar state and the two mapping surfaces are synchronized but deliberately mutable.
Cloning a credential or reading it from the store returns another handle to the same state rather
than a defensive snapshot. `env` remains flat string-to-string, while `extra` remains recursive
JSON.

Refresh reuses one effective validity threshold for the optimistic check, locked recheck, and
optional post-check. The JavaScript `Math.max` NaN rule is explicit. Refresh runs inside store
`modify`, receives the caller-or-15-second combined signal, and reports provider refresh failures
separately from store failures.

Device polling owns retry, slow-down, deadline, and cooperative cancellation decisions. Its clock
is injectable for deterministic evidence; the production clock uses Tokio. Poll outcomes are a
typed enum. Interval arithmetic floors exact whole milliseconds with no tolerance. The poll-loop
and exported sleep boundaries retain their distinct negative-infinity and Node `setTimeout`
normalization rules.

## Canonical evidence

`auth_device_code_conformance.rs` dynamically discovers and executes all six current
`auth-device-code-*.yaml` scenarios through the real `poll_device_code_flow` implementation:

- immediate completion;
- pending then slow-down then completion;
- server-provided slow-down interval;
- immediate terminal failure;
- expiry without slow-down;
- expiry after slow-down with the clock-drift-specific error.

The adapter only parses scripted poll outcomes, supplies a deterministic clock, invokes the real
typed state machine, and normalizes its result. It does not implement retry, interval selection,
deadline, outcome, or error semantics. The existing Agent-document inventory was extended only to
classify this independently-run primitive family so the Layer-08 runner continues rejecting truly
unclassified documents.

## Rust language evidence

Focused tests prove:

- live scalar, top-level mapping, and recursive-JSON credential mutation;
- store-read identity, absent reads, `None`-means-unchanged, insertion order, delete/re-add order,
  same-provider serialization, callback-failure isolation, queued cancellation, prompt caller
  cancellation, and late-result discard;
- double-checked refresh exactly once, effective default post-validation, NaN suppression, and
  combined-signal deadline observation;
- the RFC-7636 Appendix-B vector and generated 43-character verifier/challenge consistency;
- finite server interval flooring, direct `setTimeout` boundary normalization, and the distinct
  poll-loop negative-infinity floor.

All lower-layer tests remained enabled. The full workspace gate passed **306 tests**.

## Fresh quality gates

- `cargo fmt --all -- --check`: PASS.
- `cargo clippy --workspace --all-targets --all-features -- -D warnings`: PASS.
- `cargo test --workspace --all-features`: PASS, 306 tests.
- `RUSTDOCFLAGS="-D warnings" cargo doc --workspace --no-deps`: PASS.
- `cargo run -p xtask -- conformance verify`: PASS.
- shared schema/manifest validation subset with coverage disabled: PASS, 213 tests.
- manifest parse/unique-ID audit: PASS, 92 rows / 92 unique IDs.
- `git diff --check`: PASS.

The full Rust workspace gate includes all certified Runtime, LLM, Session, XFORM, Tool, Agent,
Agent-loop, active-abort, and provider-abstraction regressions.

## Scope and findings

Implemented rows: `PROV-006`, `PROV-007`, `PROV-008`, `PROV-009`, and `PROV-010`.

`PROV-011`, `PROV-012`, and `PROV-013` remain explicitly deferred. No provider-specific OAuth,
browser callback, network request, token exchange, concrete provider adapter, generic interactive
auth orchestration, or Layer-12 behavior was added.

- `PI_PARITY_DEFECT`: none active.
- `CONTRACT_ASSURANCE_DEFECT`: none active.
- `PI_BEHAVIOR_UNCERTAIN`: none active.
- `PARITY_CONSTRAINED_RISK`: none blocking.
- `PARITY_NEUTRAL_HARDENING`: typed shared handles, private synchronized state, per-provider gates,
  typed outcomes/errors, and lock-free callback boundaries.

## Handoff verdict

Python Layer 11 Pass 1 remains certified. Rust Layer 11 Pass 1 is a certification candidate at the
exact code SHA above. Layer 11 is **not cross-language closed** until the independent shared/Python
owner verifies this candidate and completes the merge/closure workflow. Layer 12 remains not
started.
