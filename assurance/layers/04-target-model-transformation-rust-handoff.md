# Layer 04 (Target-Model Message Transformation) — Rust Implementation-Owner Review Package

**Prepared:** 2026-08-24
**Prepared by:** Claude (Python/shared-contract owner, per the adopted workflow)
**Why this exists:** Layer 04 is a new layer, Pi-derived (`packages/ai/src/api/transform-messages.ts`,
pinned `b7bb00b936dbe21b8e160b3e89efdec361846699`). Python/shared work is complete and gates are
green; this package requests the first formal Rust implementation-owner review of the shared
contract, following the same discipline `LLM-F010`/`SES-F001` established: Python does not
self-certify a shared cross-language layer.

**Reviewed commits (candidate):**

```text
minion-agent        84c6ba2   src/minion_agent/llm/transform_messages.py (new),
                                      tests/llm/test_transform_messages.py (new),
                                      tests/conformance/transform_runner.py (new),
                                      tests/conformance/test_transform_conformance.py (new),
                                      tests/conformance/test_agent_conformance.py (scenario glob
                                      excludes transform-shaped files),
                                      tests/conformance/session_runner.py (transform_target step),
                                      tests/conformance/test_session_conformance.py
                                      (expect_transformed_messages assertion),
                                      conformance/schema/agent-transform-scenario.schema.json (new),
                                      conformance/schema/session-scenario.schema.json
                                      (transform_target/expect_transformed_messages, additive),
                                      12 conformance/agent/*.yaml scenarios filled (previously
                                      TO_BE_FILLED placeholders),
                                      conformance/session/request-reconstruction-after-target-transform.yaml
                                      filled (previously the sole SES-013 deferred placeholder),
                                      pi-parity-manifest.yaml (AI-020..026 rule text + python:
                                      pointers corrected)
minion-agent-docs   7416645   spec/target-model-transformation.md (rewritten -- see §2),
                                      assurance/layers/04-target-model-transformation.md (new,
                                      IN_AUDIT), this handoff
```

**Pinned Pi revision:** `b7bb00b936dbe21b8e160b3e89efdec361846699` (unchanged since Layers 01-03).

**Status update (2026-08-24): Rust already performed this review.** Recorded in full in
`04-target-model-transformation-rust-review.md`. Result:
`LAYER 04 XFORM SHARED CONTRACT — REJECTED — PI_PARITY_DEFECT`, with four findings
(`XFORM-R001`..`R004`). All four were independently reproduced and narrowly repaired; the fresh,
narrower re-review request is in `04-target-model-transformation-rust-handoff-r001-r004.md`. This
document remains the record of the original review request and its full scope — not rewritten.

**Do not modify Rust in response to this package without first recording a verdict.** Formal
verdict required: `APPROVED` / `REJECTED — CONTRACT_ASSURANCE_DEFECT` / `REJECTED —
PI_PARITY_DEFECT` / `PI_BEHAVIOR_UNCERTAIN`. Only after `APPROVED` should Rust implementation begin
(and only if this review also determines it is `REQUIRED NOW` rather than `EXPLICITLY DEFERRED BY
PLAN` — see §6).

---

## 1. What Layer 04 owns, precisely

`transform_messages(messages, target, normalize_tool_call_id?) -> Message[]` — generic target-model
compatibility transformation, run after Session projection and before a provider encoder. Full scope
boundary in `assurance/layers/04-target-model-transformation.md` §1; the one boundary most likely to
surprise a fresh reviewer: **this module has no built-in tool-call-ID normalization algorithm.** Pi
itself injects one per target API as a caller-supplied callback (verified: all six real Pi call
sites each supply their own); Layer 04 owns only the generic map-building/consistent-rewrite
orchestration. Do not expect or require a concrete per-API algorithm here — that is Phase-5/`PROV-###`
territory.

## 2. Shared-contract repair, independently reproduce before accepting

`spec/target-model-transformation.md` was rewritten this pass. Four real gaps against the pinned Pi
source were found and repaired (full detail: assurance doc §4). Reproduce each independently against
`transform-messages.ts` directly, not against this document's framing:

1. **Same-model redacted thinking retention** — was entirely absent from the prior 15-rule spec.
   Confirm: `transform-messages.ts` lines ~101-106, the `redacted` check runs first, before every
   other thinking case, and for `isSameModel` returns the block completely unchanged.
2. **Placeholder-dedup mechanics** — confirm the exact algorithm in
   `replaceImagesWithPlaceholder` (lines 15-33): consecutive images collapse per message; a
   non-image block breaks the run; a *pre-existing* text block whose text equals the placeholder
   string suppresses the *next* image's own placeholder too (`previousWasPlaceholder` is set from
   either source).
3. **Image-downgrade capability gate** — confirm it is a single boolean on the target
   (`model.input.includes("image")`), not a per-message decision, and that `assistant` content
   structurally never carries images (already established by Layer 03's `SES-F005`).
4. **Tool-call-ID normalization ownership** — confirm via `grep -rn "transformMessages(" packages/`
   in the pinned Pi checkout that all six call sites supply their own `normalizeToolCallId`, and
   that `transform-messages.ts` itself contains no per-API algorithm.

## 3. Cross-language contract hazards, adversarially probed already — verify independently

- **Empty-string `thought_signature`**: Pi's check is `if (!isSameModel &&
  toolCall.thoughtSignature)` — a JS truthy check. An empty string is falsy, so it is *not*
  stripped. Python matches this exactly (`if not same_model and call.thought_signature:`), pinned by
  `test_cross_model_empty_string_thought_signature_is_not_stripped`. Confirm idiomatic Rust can
  express the same truthy-not-presence semantics (e.g. `!signature.is_empty()`, not
  `signature.is_some()`).
- **Legacy null content**: Minion's typed Python dataclasses cannot themselves hold `content: None`
  under static typing, but Python does not enforce field types at runtime, so the check lives inside
  `transform_messages()` itself (matching Pi's own placement) via a runtime `is None` check on an
  otherwise non-optional field. Rust's type system enforces this far more strictly than Python's —
  determine whether Rust's equivalent entry point needs a distinct compatibility representation for
  this one legacy case (design allows this: "two languages need a slightly different internal
  compatibility representation... acceptable as long as the language-neutral observable result is
  identical").
- **Required synthetic `tool_name`**: a synthesized `ToolResultMessage` must carry `tool_name` from
  the real originating `ToolCall` — never fabricated, empty, or optional (`LLM-F011`). Confirm
  Rust's `ToolResultMessage.tool_name: String` (already required per the `LLM-F011` delta
  remediation, PR #5) is satisfied without any workaround.
- **Determinism**: a synthesized result's `timestamp` is real wall-clock time (matching Pi's
  `Date.now()`), deliberately excluded from every determinism assertion and from canonical
  `expect_transformed_messages`/`expect.messages` comparisons. Confirm Rust's equivalent uses the
  same wall-clock source and the same non-assertion convention.
- **Ordering**: the pipeline order (legacy-null → image-downgrade → content-transform →
  orphan-synthesis) is normative, not incidental — confirm Rust's implementation (if built) computes
  passes in the same order, since reordering changes output for real inputs.

## 4. Canonical/schema review

- `conformance/schema/agent-transform-scenario.schema.json` — new, self-contained (duplicates the
  same closed `contentBlock` shape `session-scenario.schema.json` already established, rather than
  cross-file `$ref`, matching this project's existing per-schema self-containment convention).
  Confirm it does not leak Agent-loop or Session concepts into a pure-transformer scenario shape.
- 12 `conformance/agent/*.yaml` scenarios, discriminated by a `transform` top-level key (not a
  fourth canonical family — still `conformance/agent/`, still `family: agent` conceptually).
  Confirm `test_agent_conformance.py`'s scenario glob correctly excludes these
  (`_is_full_loop_scenario`) so no full-loop runner ever tries to execute one.
- `conformance/session/request-reconstruction-after-target-transform.yaml` — Layer 03's own
  previously-deferred `SES-013` scenario, now activated via an additive `transform_target`/
  `expect_transformed_messages` extension to the existing session schema/runner. Confirm this
  composes the real Session and XFORM seams without either absorbing the other's responsibility
  (Session does not gain transform logic; XFORM does not gain Session-reconstruction logic).
- `tests/conformance/transform_runner.py` — confirm thin: no image replacement, placeholder dedupe,
  thinking filtering, signature stripping, ID normalization, orphan detection, synthetic-result
  creation, or errored/aborted filtering anywhere in it (assurance doc §11 has the full checklist).

## 5. Rust's required independent verdict, per question — do not trust Python's classification

1. **Language-neutral?** Does every rule in the rewritten spec hold independent of either
   implementation's internal representation?
2. **Pi-compatible?** Re-read `transform-messages.ts` directly at the pinned commit for every rule;
   do not take this package's line-number citations on faith.
3. **Idiomatic typed Rust representation possible?** Can `TargetModel`, `NormalizeToolCallId` (a
   `Fn(&str, &TargetModel, &AssistantMessage) -> String` or equivalent), and `transform_messages`
   itself be expressed with real typed `Message`/`ContentBlock` values throughout, with no
   `serde_json::Value`-typed shortcut anywhere in the transform path itself (parsing/serialization
   boundaries excepted)?
4. **Thin runner possible?** Can a Rust canonical adapter for these 12 scenarios call the real
   function, without simulating any rule itself?
5. **Layer-02/03 boundary integrity?** Does anything in this candidate touch Layer 02 or Layer 03
   production code, or does it consume their frozen contracts unmodified? (Expected: unmodified —
   verify directly.)
6. **Phase-5 replay deferrals still correctly scoped?** Confirm `same-model-thinking-signature-
   replayed`/`same-model-unsigned-thinking-not-replayed` test only transform-output survival
   (Question A), not provider-wire replay (Question B, still Phase-5-deferred) — assurance doc §6
   has the full reasoning; verify no provider wire encoding is simulated anywhere in either
   scenario's evidence.

## 6. Rust implementation applicability — state explicitly, do not infer from precedent

Layers 01-03 all have first-class Rust implementations, but that precedent alone does not settle
whether Layer 04 requires one now. State explicitly, with normative process/design evidence:

```text
Rust Layer-04 implementation:
    REQUIRED NOW
    or
    EXPLICITLY DEFERRED BY PLAN
```

If required, the expected shape (not prescribed, only illustrative — do not build this without your
own independent design pass): `Vec<Message> -> (typed target identity + capability) -> transform ->
Vec<Message>`, reusing the certified Layer-02 typed `Message`/`ContentBlock` enums and Layer-01's
service-seam conventions; the concrete tool-call-ID algorithm remains explicitly out of scope
(Phase-5), matching this document's own §1 boundary.

## 7. Explicitly out of scope for this review

- Phase-5 provider adapters, real HTTP/API wire encoding, Responses-family replay encoding.
- Any change to Layer 01/02/03 Rust or Python production code.
- Layer 05 or any later layer.

## 8. Expected outcome

```text
LAYER 04 SHARED CONTRACT
    APPROVED
```

or a precise rejection naming exactly which rule, boundary, or type shape is not language-neutral,
not Pi-compatible, or not idiomatically expressible in typed Rust. If rejected, the established
cycle applies: reproduce, narrow repair, new candidate SHA, fresh review — not defended, not
modified in Rust, and not treated as approved by the act of revision alone.
