# Layers 02–04 — Dependency-Ordered Rust Implementation-Owner Review

**Review date:** 2026-08-24  
**Implementation candidate:** `minion-agent@4ed360dd35550af9bd898d33e7ae3957bce0d2d8`  
**Final handoff package:** `minion-agent-docs@39f1f1336888221e524d44e5bb349878f81c81dd`  
**Pinned Pi:** `b7bb00b936dbe21b8e160b3e89efdec361846699`  
**Reviewer role:** Rust implementation owner; Python is evidence, not semantic authority.

## Dependency gate result

```text
LLM-F012
    APPROVED

LAYER 02 DELTA CONTRACT
    APPROVED

SES-F009
    APPROVED

LAYER 03 DELTA CONTRACT
    APPROVED

XFORM-R001
    APPROVED

XFORM-R002
    APPROVED

XFORM-R003
    APPROVED — unchanged

XFORM-R004
    APPROVED

LAYER 04 XFORM SHARED CONTRACT
    APPROVED
```

No new `PI_PARITY_DEFECT`, `PI_BEHAVIOR_UNCERTAIN`, or
`CONTRACT_ASSURANCE_DEFECT` was found.

## Gate 1 — LLM-F012

Pinned Pi's `packages/ai/src/types.ts` declares the role-specific content vocabulary as:

- `UserMessage.content`: string or text/image blocks;
- `AssistantMessage.content`: text/thinking/tool-call blocks;
- `ToolResultMessage.content`: text/image blocks.

The corrected Python public types match those unions. A fresh mypy run over the production package
and `tests/typing/valid_message_construction.py` passed for all positive constructions. Five direct
negative probes rejected user+thinking, user+tool-call, assistant+image, tool-result+thinking, and
tool-result+tool-call. `text_of(UserMessage(content="hello"))` returned `"hello"` through the real
library path.

Rust already conformed before this review. Its certified vocabulary uses `UserContent::Text(String)`
or `UserContent::Blocks(Vec<UserContentBlock>)`, with role-specific block enums for User, Assistant,
and ToolResult. No Rust semantic change is required for LLM-F012.

## Gate 2 — SES-F009

Python's real Session encode/decode path now preserves string-valued user content as a JSON string
and block-valued content as an array. The canonical scenario uses real append, derive, and fork
paths and observes the derived representation rather than comparing visible text alone. Focused
Python derive tests passed.

Rust's real Session already serializes and deserializes the typed `Message` value, so
`UserContent::Text("hello")` and a one-`TextBlock` array remain distinct through append, derive, and
fork ancestry. No Rust Session semantic change is required. Rust's conformance adapter was stale:
it expected 19 files, could not construct a string from `append.content`, and did not consume
`expect_user_details`. The evidence-only remediation is recorded separately in the Rust PR.

Fresh Session inventory:

```text
20 Session-family YAML files
19 Layer-03-owned
1 Layer-04 Session→XFORM integration
20 executable through the reached Python Layer-04 stack
```

For Rust at reached Layer 03, the adapter discovers all 20, executes the 19 Layer-03 scenarios, and
explicitly defers only `request-reconstruction-after-target-transform.yaml` because Rust XFORM is
not implemented. It does not simulate XFORM.

## Gate 3 — Layer 04 third pass

### XFORM-R001

Python's corrected public `UserMessage` type accepts strings and the real transformer preserves
`"hello"`, empty, whitespace-only, and placeholder-literal strings under vision, non-vision, and
cross-target identities. The canonical string scenario invokes the real transformer; the runner has
no string-preservation branch.

### XFORM-R002

Fresh adversarial JSON-Schema probes produced:

```text
Assistant missing usage                 REJECT
Assistant usage={}                      REJECT
Usage missing each required member      REJECT
Cost missing each required member       REJECT
Assistant complete usage                ACCEPT
ToolResult absent usage                 ACCEPT
ToolResult complete usage               ACCEPT
ToolResult incomplete present usage     REJECT
```

The transform runner reads every required Usage/Cost member directly and does not fabricate zero
defaults. Rust's `Usage`/`Cost` vocabulary is compatible: required members are non-`Option`, while
only `cache_write_1h` and `reasoning` are optional.

### XFORM-R003 and R004

`AI-013` continues to own Phase-5 Responses provider-wire replay. `AI-021` owns current generic
XFORM thinking compatibility evidence. “Zero Layer-04-owned scenarios deferred to Phase 5” is
explicitly an inventory statement and does not erase the Phase-5 wire obligation.

Current assurance arithmetic is consistent: 13 XFORM scenarios (12 original plus one R001
regression) and 20 Session-family scenarios (19 Layer-03-owned plus one Layer-04 integration).
Historical counts remain identified as historical.

Previously approved XFORM behavior was regression-checked without reopening it: same-model
redacted thinking, the thinking matrix, image capability gating, placeholder deduplication, the
provider+api+model identity triple, injected ID-normalization policy, signature stripping, orphan
synthesis with required `tool_name`, error/aborted exclusion, source immutability, rich-field
preservation, runner thinness, Session→XFORM composition, and the Phase-5 production boundary.

Fresh Python evidence:

```text
XFORM library + canonical:               59 passed
Session canonical + schema validation:   157 passed
XFORM canonical inventory:               13 / 13
Session canonical inventory:             20 / 20
```

## Rust implementation disposition

`process/implementation-conformance-workflow.md` §§5.9, 7, 7.3, 8, and 9 permit Python to lead
Rust by approximately one layer and explicitly allow a later, not-yet-implemented language layer
to remain `NOT_IMPLEMENTED`. Current state is Python Layer 04 and Rust Layer 03; no stronger
Layer-04-specific Rust requirement was found.

```text
RUST LAYER-04 IMPLEMENTATION TIMING
    NOT_IMPLEMENTED — VALIDLY ONE LAYER BEHIND
```

Rust must implement Layer 04 before Rust advances to Layer 05 and must not fall beyond the
process-approved lag. Layer 05 was not started.

## Rust evidence and gates

Rust evidence-only changes:

- canonical Session adapter accepts string-valued `append.content` through the real typed API;
- `expect_user_details` observes the real derived `UserContent` representation;
- inventory updated to 20 discovered / 19 executed / 1 Layer-04 deferred;
- focused Rust test proves string and one-TextBlock values remain distinct through append, derive,
  and fork.

Rust evidence PR: `EGAILab/minion-agent#6`  
Rust evidence head: `7888c1b9c14736cbe4a6f34a30066ea6ed848252`

Fresh gates on the review branch:

```text
cargo fmt --check                                      PASS
cargo clippy --workspace --all-targets --all-features
  -- -D warnings                                       PASS
cargo test --workspace --all-features                  129 passed, 0 failed
RUSTDOCFLAGS="-D warnings" cargo doc --workspace
  --no-deps                                             PASS
cargo run -p xtask -- conformance verify               PASS
```

## Readiness handoff

```text
ready for Layer-02 final delta closure?   YES
ready for Layer-03 final delta closure?   YES, after Layer 02
ready for shared Layer-04 certification?  YES, subject to shared assurance

Layer 02 status                           IN_DELTA_AUDIT
Layer 03 status                           IN_DELTA_AUDIT
Layer 04 status                           IN_AUDIT
Layer 05 started?                         NO
```

The Rust side records readiness only. Shared assurance owns the final dependency-ordered closure
and certification decisions.
