# Layer 11 Pass 2 Slice C — Rust implementation candidate

**Status:** `RUST CERTIFICATION CANDIDATE`; independent shared/Python-owner closure review is
pending. Layer 12 was not started.

## Authority and exact baseline

- merged code baseline: `8134c43168240e1a6fbe30fdbf40e1c5a7c41114`
- merged docs baseline: `e43b0c4c7bab81d78e0168370cdc85dc7f9b69cf`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- approved shared/Python candidate: code
  `a51bfcd8e34be0c9d0b72f935321ffb50804a5f0`; docs
  `c04f00a6309336fc697c41a2aa4d622599792370`
- final approval artifact: `assurance/layers/11-pass2-slice-c-final-complete-approval.md`
- Rust implementation candidate: `cd02f92e18da69f8758c44aa8aa9a4464805ab59`
- Rust PR: `EGAILab/minion-agent#34`

Rust was implemented from pinned Pi and the merged normative contract. Python was consulted only
after the independent semantic mapping, as secondary evidence for edge-case diagnosis. The pass
changed no normative spec, canonical scenario/schema, expected observation, or disposition. The
only shared-file edits are Rust evidence pointers for `PROV-011`, `PROV-012`, `PROV-014`,
`PROV-015`, and `PROV-016`.

The merged Rust baseline contained Pass 1 only: the non-deferred Pass-2 dependencies (`PROV-011`
and `PROV-014`/`PROV-015`) were not implemented. Because Slice C consumes those surfaces, this
candidate implements the complete non-deferred Pass-2 chain rather than creating private Slice-C
duplicates. `PROV-013` remains deferred.

## Rust architecture

### Interaction and auth-method vocabulary

`auth/interaction.rs` adds typed prompt and notification enums, the optional-signal
`AuthInteraction` trait, its required-signal `ProviderAuthInteraction` specialization, and typed
API-key/OAuth method callbacks. Notification remains synchronous. Prompt results remain async.
`is_subscription` is genuinely three-valued. `ProviderAuth::new` enforces the required initial
presence of at least one method while public fields retain the contract's ordinary post-construction
assignability. The read-only trait signal view is Rust's sound realization of the owner-approved
`PROV-015` trade-off; one optional signal authority backs the guaranteed-present provider
projection, preventing two signal identities from drifting.

### Codex projection

`auth/openai_codex.rs` implements the exact three-segment JWT boundary, WHATWG forgiving Base64
(including ASCII-whitespace tolerance, missing padding, malformed-padding rejection, and discarded
trailing-bit behavior), Latin-1 binary-string interpretation, JavaScript-number decoding, account
claim extraction, credential projection, and bearer `ModelAuth` projection. No signature
verification is invented.

### JavaScript JSON boundary

`auth/js_json.rs` is a narrow provider-response boundary rather than a general replacement for
Serde. It retains JavaScript's IEEE-754 number domain and UTF-16 string domain, including lone
surrogates that a Rust `String`/`serde_json::Value` cannot represent. Its renderer follows the
binding `JSON.stringify` observations: numeric-property ordering, ECMAScript number notation,
negative zero, non-finite-to-null, literal valid Unicode, and escaped unpaired surrogates. This
avoids rejecting a Pi-valid response merely because Rust's normal string type excludes lone UTF-16
code units.

### Injectable HTTP transport

`auth/http_transport.rs` defines project-owned request/response/body traits. The response exposes
status and reason phrase before body consumption; body text is lazy, cached, strips exactly one
leading BOM, and can be explicitly discarded without exposing cleanup failures. No internal lock
is held while an injected body reader runs. A Tokio task owns an in-progress body read so cancelling
one waiter cannot strand shared state. `ReqwestTransport` uses rustls, follows redirects, adds no
request timeout, and cancels an in-flight request by dropping its future when the existing
poll-based `Abortable` fires.

### Codex OAuth flow

`auth/openai_codex_oauth.rs` implements:

- exact provider identity, endpoints, request headers/bodies, login options, and messages;
- browser PKCE/state generation, the fixed authorization URL, silent callback-bind failure,
  callback/manual race, truthiness-based state/code handling, and notification-before-cleanup
  ordering;
- a local callback server with the required route/status/header rules and contained `500` path;
- device authorization start/poll/exchange using the certified `PROV-010` poller;
- exact JavaScript interval coercion, including ECMAScript whitespace and unsigned radix prefixes;
- lazy status/body branching, status-only body disposal, body-read failure asymmetry, cancellation
  translation, and refresh-specific request-error wrapping;
- the owner-approved six-field strict-string ingress rule (`PROV-016`);
- the already-certified account-id credential and bearer-auth projections.

No real provider secrets or network calls occur in tests. Outbound behavior is exercised through a
scripted typed transport; callback tests bind only ephemeral loopback ports. The production callback
continues to use the normative fixed port.

## Evidence

Focused Rust evidence covers:

- all prompt/event variants, three-valued subscription state, assignability, provider subtyping,
  and the initial `ProviderAuth` invariant;
- all pinned JWT decoding discriminators and account/auth projection;
- ECMAScript trimming, number coercion/rendering, numeric key order, valid surrogate pairs, lone
  surrogates, non-finite numbers, invalid constants, and IEEE-754 precision;
- lazy/cached/discarded response bodies, BOM handling, and prompt cancellation of in-flight work;
- browser manual-win, callback-win, bind-failure fallback, empty-manual cancellation, and the
  deliberately uncleaned notification-failure boundary;
- callback wrong-route, state mismatch, absent code, empty code, contained internal failure, and
  success cases;
- device pending/completion behavior through the real certified poller and exact request payloads;
- all six `PROV-016` strict-string fields;
- success-body raw failures versus non-success fallback and status-only no-read behavior.

All certified lower-layer suites remained enabled. The full workspace passed **328 tests**.

## Fresh gates

- `cargo fmt --all -- --check`: PASS.
- `cargo clippy --workspace --all-targets --all-features -- -D warnings`: PASS.
- `cargo test --workspace --all-features`: PASS, 328 tests.
- `RUSTDOCFLAGS="-D warnings" cargo doc --workspace --no-deps`: PASS.
- `cargo run -p xtask -- conformance verify`: PASS.
- shared schema/manifest/layering validation subset with coverage disabled: PASS, 218 tests.
- `git diff --check`: PASS.

## Scope and findings

Implemented rows: `PROV-011`, `PROV-012`, `PROV-014`, `PROV-015`, and `PROV-016`.

Still deferred: `PROV-013` generic provider-auth orchestration. Browser launching, Codex Responses
wire encoding, real-provider LLM adapters, and Layer 12 remain out of scope and were not started.

- `PI_PARITY_DEFECT`: none active.
- `CONTRACT_ASSURANCE_DEFECT`: none active.
- `PI_BEHAVIOR_UNCERTAIN`: none active.
- `PARITY_CONSTRAINED_RISK`: none blocking.
- `PARITY_NEUTRAL_HARDENING`: typed errors/enums, invariant-preserving construction, task-owned
  lazy reads with narrow lock scope, and a typed UTF-16 JSON boundary.

## Handoff verdict

Python Layer 11 Pass 2 remains certified. Rust Layer 11 Pass 2 is a certification candidate at the
exact code SHA above. Layer 11 Pass 2 is **not cross-language closed** until the independent
shared/Python owner verifies the candidate and completes the merge/closure workflow. Layer 12
remains not started.
