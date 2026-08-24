# Rust Layer 04 — Target-Model Transformation Implementation Assurance

**Date:** 2026-08-24
**Verdict:** `RUST LAYER 04 IMPLEMENTATION — APPROVED`

## Scope and provenance

```text
Certified shared contract
    minion-agent-docs@0b02b9bcdef31ff9b23da7e7eeea48a13a732681

Implementation baseline
    minion-agent@65569ba7079995e6e8dc717652ce17152fe08b78

Pinned Pi
    b7bb00b936dbe21b8e160b3e89efdec361846699

Implementation head
    3514784da40500316c019b5eeab7edb1488c80cf

PR / merge
    EGAILab/minion-agent#7
    439651eb7a5f4ecbee49c573696aa94dee62ed02
```

## Implementation seams

- `minion-agent-rust/crates/minion-agent/src/llm/transform.rs`
  - `TransformTarget`
  - `ToolCallIdNormalizer`
  - `transform_messages`
- `minion-agent-rust/crates/minion-agent/src/llm/transform_compat.rs`
  - library-owned legacy-null normalization, gated by the non-default `conformance` feature
- `minion-agent-rust/crates/minion-agent/tests/xform_conformance.rs`
  - thin adapter over all 13 canonical XFORM scenarios
- `minion-agent-rust/crates/minion-agent/tests/session_conformance.rs`
  - real Session derive followed by real XFORM for the Layer-04 composition scenario

The implementation reuses the certified Layer-02 `Message` vocabulary. No XFORM-specific message
hierarchy exists. `TransformTarget` contains only the full model identity and image capability.
Provider-specific ID normalization remains injected policy; the callback receives the original
source `AssistantMessage`.

## Semantic evidence

Direct Rust tests cover:

- string-valued user content for vision/non-vision, empty, whitespace, literal-placeholder, and
  cross-identity cases;
- user and tool-result image preservation/downgrade and exact placeholder-run behavior;
- the same/cross-model thinking matrix, including same-model redacted and signed-empty cases;
- cross-model text/thought signature stripping and namespace preservation;
- provider + API + model identity;
- transcript-ordered ID normalization, matching result rewrite, unrelated result preservation, and
  original-source callback input;
- error/aborted filtering, orphan placement/order, normalized synthetic IDs, and required real
  `tool_name`;
- rich Assistant and ToolResult field preservation and source-history immutability;
- library-owned legacy-null normalization before the typed core.

```text
XFORM canonical
    discovered    13
    executed      13
    passed        13
    deferred       0

Session canonical
    discovered    20
    executed      20
    passed        20
    deferred       0

request-reconstruction-after-target-transform
    PASS — real Session -> derive -> real XFORM; transformed values are not persisted
```

## Runner and boundary review

The XFORM adapter supplies typed target data and scripted normalization policy, then invokes the
real library seam. It does not downgrade images, transform thinking, strip signatures, track ID
mappings, synthesize orphan results, or filter assistants. The Session adapter performs no XFORM
semantics.

The initial independent review found that the dynamic legacy entry was publicly adjacent to the
normal typed API. Before merge it was narrowed behind a non-default `conformance` feature, and a
second review found no Critical, Important, or Minor issues. Formal verdict:

```text
RUST LAYER 04 IMPLEMENTATION
    APPROVED
```

## Fresh post-merge gates

Executed on `minion-agent@439651eb7a5f4ecbee49c573696aa94dee62ed02`:

```text
cargo fmt --check                                            PASS
cargo clippy --workspace --all-targets --all-features
  -- -D warnings                                             PASS
cargo test --workspace --all-features                        145 passed / 0 failed
RUSTDOCFLAGS="-D warnings" cargo doc --workspace --no-deps   PASS
cargo run -p xtask -- conformance verify                     PASS
```

## Phase-5 boundary and findings

No real provider, Responses wire replay, provider request encoding, or concrete provider-specific
ID normalizer was implemented. `AI-013` remains unresolved at the provider-wire level and owned by
Layer 05.

```text
PI_PARITY_DEFECT             none
PI_BEHAVIOR_UNCERTAIN        none
CONTRACT_ASSURANCE_DEFECT    none
PARITY_NEUTRAL_HARDENING     none
PARITY_CONSTRAINED_RISK      none

Layer 04 shared              CERTIFIED
Layer 04 Python              CERTIFIED
Layer 04 Rust                CERTIFIED
Layer 05                     NOT STARTED
```
