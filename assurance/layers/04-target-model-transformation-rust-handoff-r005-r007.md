# Layer 04 — Post-Certification Delta Rust Review Package (`XFORM-R005`/`R006`/`R007`)

**Prepared:** 2026-08-24
**Prepared by:** Claude (Python/shared-contract owner, per the adopted workflow)
**Why this exists:** a pre-Layer-05 review found three findings after Rust's own Layer-04
implementation (`EGAILab/minion-agent#7`, `439651e`) had already been certified
(`04-target-model-transformation-rust-implementation.md`). Full delta record:
`assurance/layers/04-target-model-transformation.md` §21.

**Rust's primary semantic responsibility in this package is `XFORM-R005`.** `XFORM-R006`/`R007` are
shared-assurance/traceability corrections only — no Rust code changed for either, and no Rust code
change is being requested for either; they are included here only so Rust's review confirms the
corrected documents are self-consistent from its own side too.

**Reviewed commits (delta candidate):**

```text
minion-agent        8a398235187850f88f3942617d9e62a845cd7290   spec/target-model-transformation.md
                     lives in minion-agent-docs (see below); this SHA covers
                     src/minion_agent/llm/transform_messages.py (matching-result rewrite condition),
                     tests/llm/test_transform_messages.py (+4 tests),
                     conformance/agent/tool-call-id-normalization-empty-string.yaml (new),
                     pi-parity-manifest.yaml (AI-020..AI-026 rust: pointers, AI-023 rule text,
                     AI-026 rule text)
minion-agent-docs   871f2d05f32213ccb7e38cbd580c906c2b7ca76e   spec/target-model-transformation.md
                     (rule 13 rewrite), assurance/layers/04-target-model-transformation.md (header
                     rewrite + §21), assurance/layers/
                     04-target-model-transformation-rust-implementation.md (delta note appended,
                     original evidence unchanged), this handoff
```

**Do not modify Rust in response to this package without first recording a verdict.** Rust
implementation timing for the fix itself is adjudicated by Rust, only after this package's
shared-contract question is answered.

**Pinned Pi revision:** `b7bb00b936dbe21b8e160b3e89efdec361846699` (unchanged).

---

## 1. `XFORM-R005` — independently reproduce, do not just verify the Python patch

Rust must reproduce the pinned-Pi case directly, not merely confirm Python's fix matches Python's
own description of it.

**Pi source** (`packages/ai/src/api/transform-messages.ts`, read directly at the pinned commit):

```text
ToolCall rewrite (lines ~136-142):
    if (!isSameModel && normalizeToolCallId) {
        const normalizedId = normalizeToolCallId(toolCall.id, model, assistantMsg);
        if (normalizedId !== toolCall.id) {
            toolCallIdMap.set(toolCall.id, normalizedId);
            normalizedToolCall = { ...normalizedToolCall, id: normalizedId };
        }
    }

Matching ToolResult rewrite (lines ~84-90):
    if (msg.role === "toolResult") {
        const normalizedId = toolCallIdMap.get(msg.toolCallId);
        if (normalizedId && normalizedId !== msg.toolCallId) {
            return { ...msg, toolCallId: normalizedId };
        }
        return msg;
    }
```

The ToolCall side rewrites unconditionally on `!==`. The ToolResult side additionally requires
`normalizedId` to be truthy — a mapped `""` is falsy in JavaScript, so the real result is **not**
rewritten and keeps its original id. The transformed call (now `""`) and the real result (still the
original id) no longer match, so the second-pass orphan synthesis fires for the empty id.

**Required Rust verdict, per question — do not trust Python's classification:**

1. **Reproduce independently:** construct the identical case directly against `ref-repos/pi`'s
   pinned source (a cross-model assistant with one `ToolCall`, a real matching `ToolResult`, and a
   normalizer returning `""`). Confirm: `ToolCall.id` becomes `""`? real `ToolResult` keeps its
   original id? a synthetic `""` orphan (`tool_name` from the real call, `is_error: true`,
   `"No result provided"`) is synthesized? Record `YES`/`NO` for each, independently — not copied
   from this document.
2. **Does Rust's own certified Layer-04 implementation already avoid this class of error?**
   `transform.rs::transform_content`'s `Message::ToolResult` arm currently reads:
   ```rust
   if let Some(normalized) = id_map.get(&result.tool_call_id) {
       result.tool_call_id.clone_from(normalized);
   }
   ```
   This is unconditional on any recorded mapping, not gated on the mapped value's truthiness.
   Confirm directly against the real merged source (unchanged since PR #7) whether this already
   reproduces Pi's asymmetry or requires a fix. Do not assume the answer from this document's own
   analysis — verify against the actual file.
3. **Does the rewritten shared-contract rule (`spec/target-model-transformation.md` rule 13) now
   state the asymmetry precisely enough that an implementation could be written correctly from the
   spec alone**, without needing to re-read Pi source? Confirm the rule states: (a) the ToolCall
   rewrite is unconditional on `returned != original`, including empty string; (b) the ToolResult
   rewrite requires the mapped value be truthy AND different from the current id; (c) the observable
   consequence (unmatched call → orphan synthesis) is stated causally, not left implicit.
4. **Does the new canonical scenario capture it exactly?**
   `conformance/agent/tool-call-id-normalization-empty-string.yaml` — confirm it exercises a real
   `normalize_tool_call_ids` map with an empty-string value through the real transform seam (not
   runner-simulated), and that `expect.messages` asserts exactly: the transformed `ToolCall.id ==
   ""`, the real `ToolResult` preserved at `tool_call_id == "old-id"`, and a synthetic
   `ToolResult` with `tool_call_id == ""`, `tool_name == "lookup"`, `is_error == true`, and the
   `"No result provided"` text.
5. **Does the corrected Python implementation conform?** Re-run the empty-string case directly
   against the real `transform_messages()` and confirm 3 output messages with the shapes described
   above.

**Formal shared verdict required:**

```text
XFORM-R005 SHARED CONTRACT
    APPROVED
```

or a precise rejection naming exactly which sub-question above failed.

---

## 2. `XFORM-R006` — assurance-document self-consistency, confirm only

No Rust code involved. Confirm `assurance/layers/04-target-model-transformation.md`'s header no
longer simultaneously claims `Rust Layer 04: CERTIFIED` and "Rust has not yet implemented Layer 04"
as both current; confirm the one-layer-behind period is now explicitly framed as historical
chronology predating PR #7, and that §20's own historical certification block is unchanged with a
forward-pointing note to §21 rather than being rewritten.

No verdict beyond confirmation is required for this item; it does not gate `XFORM-R005`'s verdict.

---

## 3. `XFORM-R007` — manifest traceability, confirm only

No Rust code involved. Confirm `pi-parity-manifest.yaml`'s `AI-020`..`AI-026` rows now cite real
Rust implementation/test paths (`minion-agent-rust/crates/minion-agent/src/llm/transform.rs`,
`transform_compat.rs`, `tests/llm_transform.rs`, `tests/xform_conformance.rs`) instead of the
pre-implementation `Phase 2 target-model transform` placeholder — and independently spot-check at
least `AI-023` and `AI-026` against the real source to confirm the cited symbols/tests actually
exist and actually cover what the row claims. Confirm `AI-026`'s rewritten `rule:` text no longer
implies Rust's typed `Message` accepts null (it does not — `transform_compat.rs` decodes untyped
JSON into the typed vocabulary before construction).

No verdict beyond confirmation is required for this item; it does not gate `XFORM-R005`'s verdict.

---

## 4. Explicitly out of scope for this package

- `XFORM-R001`..`R004`'s own already-closed history — not reopened.
- `LLM-F012`/`SES-F009` — closed, not reopened.
- Layer 05 — not started, blocked on this delta's closure.
- Rust semantic remediation itself — this package requests only the shared-contract verdict on
  `XFORM-R005`. Remediation begins only after `APPROVED` is recorded, per the adopted
  review-before-remediation workflow (§25/§26 of the originating instruction).

## 5. Expected outcome

```text
XFORM-R005 SHARED CONTRACT
    APPROVED
```

or a precise rejection. If approved, Rust may proceed with its own narrow semantic remediation
(the matching-`ToolResult` rewrite condition in `transform.rs::transform_content`, gated on
truthiness, mirroring the Python fix — exact Rust syntax/structure is implementation-owned), direct
Rust test evidence for the empty-string case, fresh full Rust gates against merged `main`, and its
own independent implementation review before merge — all Rust-owned steps outside this package's
scope. Only after Rust's delta is merged and green does Layer 04's post-certification delta audit
close and Layer 04 return to a three-part `CERTIFIED` (shared/Python/Rust), unblocking Layer 05.
