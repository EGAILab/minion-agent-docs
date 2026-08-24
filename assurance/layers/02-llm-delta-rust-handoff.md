# Layer 02 (LLM) — Post-Certification Delta Rust Implementation-Owner Review Package

**Prepared:** 2026-08-24
**Prepared by:** Claude (Python/shared-contract owner, per the adopted workflow)
**Why this exists:** Layer 02 was `CERTIFIED` on 2026-08-23. Rust's own independent Layer-03
implementation (PR #4) then surfaced a real cross-language defect against this already-certified
layer: Rust's previously-correct `ToolResultMessage.tool_name: String` had to be weakened to
`Option<String>` to consume a Python-authored canonical scenario that scripted `tool_name: null`.
Per the new governance guardrail this pass adds
(`process/implementation-conformance-workflow.md` §4.6), this triggers a post-certification delta
audit of Layer 02 — not a Layer-03-only fix — because `tool_name` requiredness is vocabulary, not
Session-owned. Full finding detail: `assurance/layers/02-llm.md` §0 (`LLM-F011`).

**This is not a reopening of Layer 02's full certification.** Only `LLM-F011`'s exact semantics are
in scope. Layer 02's status is `historically CERTIFIED (2026-08-23), POST-CERTIFICATION DELTA AUDIT
OPEN (IN_DELTA_AUDIT)` — not "never certified."

**Reviewed commits (delta candidate):**

```text
minion-agent        f88c79d   LLM-F011 remediation (bundled with SES-F004..F008): messages.py,
                               tools/result.py, tools/execute.py, session/derive.py,
                               tests/conformance/session_runner.py,
                               conformance/schema/session-scenario.schema.json,
                               conformance/session/rich-assistant-message-round-trip.yaml,
                               pi-parity-manifest.yaml (AI-006), ~21 test call sites across
                               8 test files
minion-agent-docs   27bde67   assurance/layers/02-llm.md (§0), spec/llm.md (content-union
                               annotations, no requiredness change), this handoff
```

**Pinned Pi revision:** `b7bb00b936dbe21b8e160b3e89efdec361846699` (unchanged).

**Do not modify Rust in response to this package without first recording a verdict.** Rust's own
review-before-remediation workflow applies: `APPROVED` / `REJECTED — CONTRACT_ASSURANCE_DEFECT` /
`REJECTED — PI_PARITY_DEFECT` / `PI_BEHAVIOR_UNCERTAIN`. Only after a recorded `APPROVED` verdict
should Rust's own implementation fix land, as a new remediation PR (do not rewrite PR #4 history).

---

## 1. What changed, classified by ownership

**SHARED CONTRACT:**

- `conformance/schema/session-scenario.schema.json` — `toolResultDetail.tool_name` type narrowed
  from `["string","null"]` to `"string"`; `step.append`'s existing `allOf` conditional gained a
  clause requiring `tool_name` in `required` whenever `role: tool_result`.
- `conformance/session/rich-assistant-message-round-trip.yaml` — both tool_result appends now
  script a real `tool_name` (the second previously left it unscripted, defaulting to `null`, which
  is exactly the shape that forced Rust's regression).
- `pi-parity-manifest.yaml` — `AI-006` row's `rule:` text expanded to state `tool_name` is required,
  citing Pi's `toolName: string` (no `?`) and noting `spec/llm.md` already had it required before
  Python's implementation was corrected to match; `tests:` gained
  `rich-assistant-message-round-trip`.
- `spec/llm.md` — **no requiredness change** (it already lacked `?` on `tool_name`, confirmed
  correct before this pass). `AssistantMessage`/`ToolResultMessage` content unions made explicit
  inline, matching `UserMessage`'s existing style — cosmetic, not semantic.

**PYTHON IMPLEMENTATION:**

- `minion_agent/llm/messages.py::ToolResultMessage.tool_name` — now a required `str` field (was
  `str | None = None`).
- `minion_agent/tools/result.py::ToolResult.tool_name` — new required field; `to_message()` now
  passes it through; `text_result()` gained a required `tool_name` parameter.
- `minion_agent/tools/execute.py::execute_call` — all 5 `ToolResult`/`text_result` construction
  sites now pass the real `call.name` (the model's own requested tool name), not a synthesized or
  empty value.
- `minion_agent/session/derive.py` — `encode_message`/`decode_message` no longer treat
  `ToolResultMessage.tool_name` as optional.

**TEST-ONLY (supporting evidence, not itself under cross-language review):**

- `tests/conformance/session_runner.py::_message()` reads `spec["tool_name"]` directly (schema now
  guarantees its presence for `role: tool_result`), no `.get()` fallback.
- ~21 call sites across `tests/agent_loop/test_terminate.py`, `tests/conformance/agent_runner.py`,
  `tests/tools/test_added_tools.py`, `tests/tools/test_batch.py`, `tests/tools/test_execute.py`,
  `tests/tools/test_post_execute.py`, `tests/tools/test_properties.py`, `tests/tools/test_result.py`
  updated to supply a real `tool_name`.

---

## 2. Explicitly rejected fixes (per the original review's own constraint)

Do not accept a Rust-side fix that:

- Makes `tool_name` optional (`Option<String>`) — this is the exact regression under review.
- Substitutes an empty string as a semantic placeholder for "no tool name."
- Invents a fake tool name inside a runner/adapter rather than threading the real one from the
  executed call.

---

## 3. Rust's required independent verdict, per question — do not trust Python's classification

For `LLM-F011`:

1. **Language-neutral?** Does `ToolResultMessage.tool_name: String` (required, non-optional) hold
   as a rule independent of Python's specific implementation choice? Verify against the corrected
   schema and `spec/llm.md` directly, not against this document's framing.
2. **Pi-compatible?** Re-read `packages/ai/src/types.ts::ToolResultMessage` at the pinned commit
   directly. Confirm `toolName: string` has no `?`. Do not take Python's citation on faith.
3. **Idiomatic typed Rust representation possible?** Is `pub tool_name: String` (required, no
   `Option`) achievable at every real construction site in Rust's own tool-execution pipeline
   without an artificial default? If Rust's pipeline currently lacks a real source for `tool_name`
   at some call site, that is a defect in that call site (tool-layer territory), not a reason to
   weaken the vocabulary type.
4. **Thin runner possible?** Does satisfying this requirement in Rust's canonical Session runner
   require the runner to fabricate or simulate a tool name, or can it always read one from a real
   `ToolCallBlock`/dispatched call?
5. **Future-layer simulation required?** Does anything about this fix require Rust's Session/LLM
   layers to simulate tool-execution semantics that belong to a later layer (`TOOL-###`)? Expected
   answer: no — `call.name` is already available at the point `ToolResultMessage` is constructed in
   both languages' real pipelines.

---

## 4. Expected Rust remediation (only after a recorded `APPROVED` verdict)

- `llm/vocabulary.rs::ToolResultMessage.tool_name` — revert from `Option<String>` back to `String`
  (undoing PR #4's forced regression), removing the `#[serde(skip_serializing_if = "Option::is_none")]`
  attribute and the `Some(...)` wrapping at the constructor.
- Consume the corrected schema (`tool_name` required whenever `role: tool_result`) without adding
  any Rust-side special case.
- Re-run Rust's own full gate suite (`cargo fmt --check`, strict Clippy, rustdoc, `xtask conformance
  verify`, the full workspace test suite) fresh — do not reuse the PR #4 counts.
- Open a new remediation PR; do not rewrite PR #4's history.

---

## 5. What Rust does NOT need to do in this pass

- Does not need to address `SES-F004`..`SES-F008` in this package — those are Layer 03's own delta
  findings, handed off separately in `03-session-artifacts-delta-rust-handoff.md`. Layer 03's delta
  certification is gated behind this one landing first (persistence depends on the vocabulary being
  settled).
- Does not need to start Layer 04 (XFORM).
- Does not need to touch anything outside the four production files and the shared-contract files
  listed in §1.
