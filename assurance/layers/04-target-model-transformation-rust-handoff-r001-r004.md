# Layer 04 — `XFORM-R001`..`R004` Narrow Re-Review Package

**Prepared:** 2026-08-24
**Prepared by:** Claude (Python/shared-contract owner, per the adopted workflow)
**Why this exists:** the independent Rust implementation-owner review of the first Layer-04
candidate (`minion-agent@84c6ba2` / `minion-agent-docs@a4eef91`) returned:

```text
LAYER 04 XFORM SHARED CONTRACT
    REJECTED — PI_PARITY_DEFECT
```

with four findings (`04-target-model-transformation-rust-review.md`, docs `0f3d419`):
`XFORM-R001` (`PI_PARITY_DEFECT`), `XFORM-R002`/`XFORM-R003`/`XFORM-R004` (`CONTRACT_ASSURANCE_DEFECT`).
All four were independently reproduced against the actual rejected candidate before being accepted
(not taken on the review's word — see `assurance/layers/04-target-model-transformation.md` §0 for
full reproduction detail) and narrowly repaired. **This is not another full Pi audit from zero.** It
asks Rust to verify four specific fixes plus a short regression list against everything the first
review already approved.

**Reviewed commits (corrected candidate):**

```text
minion-agent        42ef135   src/minion_agent/llm/transform_messages.py (R001 fix),
                                      tests/llm/test_transform_messages.py (+9 R001 tests),
                                      conformance/schema/agent-transform-scenario.schema.json
                                      (R002 rewrite), tests/conformance/transform_runner.py
                                      (rich-field threading, R002), tests/conformance/
                                      test_transform_conformance.py (optional-timestamp
                                      comparison), 12 existing conformance/agent/*.yaml scenarios
                                      (rich-field defaults added, evidence-only), new
                                      conformance/agent/string-user-content-survives-
                                      transformation.yaml, pi-parity-manifest.yaml (AI-013, R003)
minion-agent-docs   6f18962   spec/target-model-transformation.md (rule 2 string/array
                                      clarification, invariants wording fix — see §0.1),
                                      assurance/layers/04-target-model-transformation.md
                                      (§0 rejection/remediation record, §15 four-finding history
                                      corrected — R004), this handoff
```

**Pinned Pi revision:** `b7bb00b936dbe21b8e160b3e89efdec361846699` (unchanged).

**Status update (2026-08-24): Rust already performed this review.** Recorded in full in
`04-target-model-transformation-rust-r001-r004-rereview.md`. Result: `LAYER 04 XFORM SHARED
CONTRACT — REJECTED — PI_PARITY_DEFECT`. `XFORM-R003` was confirmed `APPROVED` (unchanged);
`XFORM-R001`/`XFORM-R002`/`XFORM-R004` remained open, with the review tracing `XFORM-R001`'s root
cause further upstream to already-certified Layer 02/03 Python implementations
(`LLM-F012`/`SES-F009`, see `assurance/layers/02-llm.md` §0b and `assurance/layers/
03-session-artifacts.md` §0b). All findings independently reproduced and repaired; the fresh,
dependency-ordered re-review requests are `02-llm-delta-rust-handoff-llm-f012.md` (review first),
`03-session-artifacts-delta-rust-handoff-ses-f009.md` (second), and
`04-target-model-transformation-rust-handoff-third-pass.md` (third, this layer's own remaining
`XFORM-R001`-complete/`XFORM-R002`/`XFORM-R004` fixes plus a regression check). This document
remains the record of the first re-review request and its full scope — not rewritten.

**Do not modify Rust in response to this package without first recording a verdict.** Rust
implementation timing (`REQUIRED NOW` vs. `EXPLICITLY DEFERRED BY PLAN`) is still not adjudicated by
this package — that determination remains for the reviewer to make only after a shared-contract
`APPROVED` verdict, exactly as the first handoff specified.

---

## 1. `XFORM-R001` — verify independently, do not trust this document

**What changed:** `transform_messages.py::_downgrade_unsupported_images` now checks
`isinstance(message.content, str)` for `UserMessage` before attempting placeholder replacement, and
passes a string through completely untouched. Re-read Pi's `downgradeUnsupportedImages` directly
(`transform-messages.ts` lines 35-57) and confirm the `Array.isArray(msg.content)` guard is the
exact behavior being reproduced — a string never reaches `replaceImagesWithPlaceholder` in Pi
either.

**Reproduce the original defect and the fix, independently:**

```python
transform_messages([UserMessage(content="hello", timestamp=1)], target_novision)
# before the fix: content == ("h", "e", "l", "l", "o")
# after the fix:  content == "hello"
```

**Verdict questions:**
1. Does the fix apply only to `UserMessage` (correct — `ToolResultMessage.content` has no string
   variant in the frozen vocabulary; `AssistantMessage.content` likewise never carries a string)?
2. Does `spec/target-model-transformation.md` rule 2's new clarifying text accurately state the
   `string | array` distinction, matching `spec/llm.md`'s own frozen `UserMessage.content` shape?
3. Is the new canonical scenario (`string-user-content-survives-transformation.yaml`) real evidence
   — does it invoke the actual `transform_messages()` seam, or does the runner special-case string
   content itself? (Expected: real seam; `transform_runner.py::_user_content` only decides
   string-vs-array based on the YAML's own JSON type, performing no transformation logic itself.)

## 2. `XFORM-R002` — schema completeness, verify the adversarial matrix independently

**What changed:** full rewrite of `agent-transform-scenario.schema.json` — `$defs/userContent`
(string or block array) used by both message directions; every remaining certified
`AssistantMessage`/`ToolResultMessage` optional field now accepted (inlined per-variant rather than
composed via `allOf`, since `additionalProperties: false` does not see properties declared in a
sibling `allOf` branch — verify this JSON Schema behavior independently if unfamiliar, it is a real
composition pitfall, not an assumption); `target.provider`/`api`/`model_id` now require
`minLength: 1`; `expect` now requires `minProperties: 1`.

**Reproduce this exact matrix directly against the corrected schema, do not reuse this document's
reported results:**

```text
valid user string                 ACCEPT
user block array                  ACCEPT
legacy user null                  ACCEPT
empty target.provider             REJECT
empty target.api                  REJECT
empty target.model_id             REJECT
rich AssistantMessage              ACCEPT
rich ToolResultMessage             ACCEPT
tool_result missing tool_name       REJECT
tool_result tool_name=null          REJECT
empty expect: {}                    REJECT
assistant + image                   REJECT
```

**Verdict questions:**
1. Does the schema still correctly reject every role/content-legality violation the first review
   confirmed (`assistant` + image, etc.) — i.e., did completeness repair avoid becoming permissiveness?
2. Is `tool_result`'s `timestamp` now correctly optional in `expect` (present in the real output
   always, but only compared when the scenario's own expectation includes it)? Confirm
   `transform_runner.py::_normalize_message` always includes real `timestamp` for tool_result, and
   `test_transform_conformance.py::_for_comparison` is the only place that ever drops it, and only
   when absent from that one scenario's expectation.
3. Do idiomatic typed Rust equivalents (a Rust enum for `userContent`, optional fields on rich
   message structs) map cleanly to this corrected shape?

## 3. `XFORM-R003` — verify the manifest correction is honest, not merely tidy

**What changed:** `pi-parity-manifest.yaml`'s `AI-013` row rewritten to state the Question-A/
Question-B split explicitly and name both cited tests as Question-A-only prerequisite evidence.
**No fake Responses encoder or placeholder scenario was added.**

**Verdict questions:**
1. Does `AI-013`'s `rule:` text now correctly distinguish "does a signature survive
   `transform_messages()`" from "does a retained signature get correctly re-encoded into a real
   Responses wire request," without claiming the latter is proven?
2. Does `AI-021`'s own row (unchanged this pass) correctly retain ownership of the Question-A
   evidence, so the split is real ownership separation rather than one row losing evidence?
3. Is it still true, independently confirmed, that no Responses/Codex adapter exists anywhere in
   this repository's history (re-verify Layer 02's own claim rather than trusting it, if you have
   not already independently confirmed it during the original Layer 02 delta review)?

## 4. `XFORM-R004` — verify the history correction is accurate, not self-serving

**What changed:** `assurance/layers/04-target-model-transformation.md` §15 now lists all four
first-pass `CONTRACT_ASSURANCE_DEFECT` findings (previously three), and a new §0 records the full
rejection/remediation lifecycle without erasing or reframing the rejected candidate.

**Verdict questions:**
1. Does §4 (the original shared-contract repair section) still list exactly the same four repairs
   it always did — i.e., is this genuinely a bookkeeping-only fix, not a stealth re-classification?
2. Is the rejected candidate's finding set fully preserved (not deleted, not summarized away) as
   positive assurance evidence?

## 5. Regression check — confirm nothing already-approved moved

Re-verify each of these is unchanged from the first review's own approval, using the corrected
candidate directly rather than assuming continuity:

```text
same-model redacted thinking            unchanged
thinking compatibility matrix           unchanged
placeholder-dedup mechanics             unchanged (only its scope relative to string content
                                         clarified, not its own array-content behavior)
image capability gate                   unchanged
frozen target identity triple           unchanged (now additionally non-empty-enforced)
injected ID-normalization callback      unchanged
cross-model signature stripping         unchanged, including the empty-string-thought_signature
                                         truthy-check quirk
orphan synthesis ordering               unchanged
error/aborted exclusion                 unchanged
Session -> XFORM composition            unchanged
runner thinness                         unchanged (both runners re-verified against the expanded
                                         checklist after their respective edits)
Phase-5 production-wiring boundary      unchanged
```

## 6. Explicitly out of scope for this package

- Any Rust implementation change or timing determination (§39 of the original remediation
  instruction — still deferred to post-approval).
- Layer 05.
- Re-litigating any of the twelve items in §5 above without new evidence.

## 7. Expected outcome

```text
LAYER 04 XFORM SHARED CONTRACT
    APPROVED
```

or a precise rejection naming exactly which of the four fixes remains incomplete, non-language-
neutral, or not idiomatically expressible in typed Rust. If rejected again, the established cycle
applies unchanged: reproduce, narrow repair, new candidate SHA, fresh review.
