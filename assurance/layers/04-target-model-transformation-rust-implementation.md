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
Real Providers (master Phase 5 / assurance Layer 11 — historically written as "Layer 05" here; see
`LAY-F001`).

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

## Post-certification delta note (2026-08-24, added after this document's original certification)

**This document's certification evidence above is preserved exactly as it was at the time of PR
#7 — it was accurate then and is not rewritten.** A subsequent pre-Real-Providers review
(historically named "pre-Layer-05"; see `LAY-F001` — Real Providers is master Phase 5 / assurance
Layer 11, not Layer 05) found
`XFORM-R005` (`PI_PARITY_DEFECT` + `CONTRACT_ASSURANCE_DEFECT`): pinned Pi's tool-call-ID
normalization has two different, asymmetric rewrite conditions for the `ToolCall` versus the
matching `ToolResultMessage` (spec/target-model-transformation.md rule 13, corrected). Direct
inspection of this implementation's own `transform.rs::transform_content` (the exact source this
document certified, unchanged since) confirms the same defect class Python had: the matching
`ToolResultMessage` rewrite is unconditional on any recorded mapping
(`if let Some(normalized) = id_map.get(&result.tool_call_id) { ... }`), not gated on the mapped
value's truthiness — a callback returning `""` will incorrectly rewrite the real result to `""`
instead of leaving it at its original id.

```text
XFORM-R005 (this implementation)   CONFIRMED PRESENT, NOT YET FIXED
Rust semantic remediation           PENDING -- not performed in the Python/shared delta pass
                                     that discovered this (per the adopted review-before-
                                     remediation workflow: Rust code is not modified until the
                                     shared contract is re-approved)
Full delta record                   assurance/layers/04-target-model-transformation.md SS21
Narrow Rust review package          04-target-model-transformation-rust-handoff-r005-r007.md
```

This document's own `13/13`/`145 passed` counts above describe this implementation's state at PR
#7 and remain historically accurate; they are not the current post-delta count for either language
(Python/shared is now at 14 canonical XFORM scenarios after its own `XFORM-R005` fix, §21 of the
layer document; Rust remains at its original 13 until its own delta remediation lands).

## XFORM-R005 Rust remediation (2026-08-24)

The pending state immediately above is preserved as the pre-remediation snapshot. Rust independently
reviewed the shared package at `minion-agent@8a398235187850f88f3942617d9e62a845cd7290` /
`minion-agent-docs@f2fb2d544cf2e847d197f294a2394eb937714705` against pinned Pi
`b7bb00b936dbe21b8e160b3e89efdec361846699` and recorded:

```text
XFORM-R005 SHARED CONTRACT    APPROVED
XFORM-R006                    CONFIRMED
XFORM-R007                    CONFIRMED
```

The pinned Pi function was executed directly with a normalizer returning `""`. It rewrote the
`ToolCall.id` to `""`, retained the real result at its original ID, and synthesized an empty-ID
orphan. A direct Rust test first failed with two messages instead of three, proving the existing
unconditional real-result rewrite reproduced the defect. The narrow fix retains the empty mapping
and ToolCall rewrite while requiring a non-empty, changed mapped value before rewriting a real
ToolResult.

```text
Rust delta PR                 EGAILab/minion-agent#8
Implementation head          b9b5b4cb4a6c9fba3965439c2cf26152e6a9c334
Merge / post-merge main      feed2fba2f5a02013f1ededcfa432db1c0e1d997
Independent review           RUST LAYER 04 DELTA — XFORM-R005 APPROVED

XFORM canonical              14 discovered / 14 executed / 14 passed / 0 deferred
Session canonical            20 discovered / 20 executed / 20 passed / 0 deferred

cargo fmt --check                                            PASS
cargo clippy --workspace --all-targets --all-features
  -- -D warnings                                             PASS
cargo test --workspace --all-features                        146 passed / 0 failed
RUSTDOCFLAGS="-D warnings" cargo doc --workspace --no-deps   PASS
cargo run -p xtask -- conformance verify                     PASS
```

The canonical adapter changed only its inventory assertion from 13 to 14. Callback invocation,
mapping retention, ToolCall and ToolResult rewrite decisions, and orphan synthesis remain in the
real typed transformer. Session semantics were unchanged.

No provider algorithm, provider-wire replay, or Real Providers (assurance Layer 11) work was added.
Rust reports
`XFORM-R005` remediated and post-merge green; **shared closure completed** —
`assurance/layers/04-target-model-transformation.md` §22 records the manifest pending-marker
cleanup (`AI-023`), the formal closure of `XFORM-R005`/`R006`/`R007`, and the restored three-part
`CERTIFIED` status (shared/Python/Rust), preserving the original certification date.
