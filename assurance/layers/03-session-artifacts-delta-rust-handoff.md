# Layer 03 (Session + Artifacts) — Post-Certification Delta Rust Implementation-Owner Review Package

**Prepared:** 2026-08-24
**Prepared by:** Claude (Python/shared-contract owner, per the adopted workflow)
**Why this exists:** Layer 03 was `CERTIFIED` on 2026-08-24. Rust's own merged Layer-03
implementation (PR #4, `2519fc1565ff40ffeb8aa047bc2d3f0aa8bef512`) then became the evidence source
for five further Session-owned findings, each independently reproduced against Rust's real merged
`session/mod.rs`, pinned Pi, and Python's current implementation — not mechanically accepted from
Rust's own framing. Full finding detail: `assurance/layers/03-session-artifacts.md` §0
(`SES-F004`..`SES-F008`).

**This is not a reopening of Layer 03's full certification.** Only these five findings' exact
semantics are in scope. Layer 03's status is `historically CERTIFIED (2026-08-24),
POST-CERTIFICATION DELTA AUDIT OPEN (IN_DELTA_AUDIT)` — not "never certified."

**Dependency:** this package's certification is gated behind `LLM-F011`'s own delta certification
(`02-llm-delta-rust-handoff.md`) landing first — `SES-F004` and `SES-F006` both touch
`expect_event_kinds`/`expect_error` schema mechanisms that sit alongside the `tool_name`
requiredness fix in the same schema file, and `ToolResultMessage` is vocabulary Session persists
but does not own.

**Reviewed commits (delta candidate):**

```text
minion-agent        f88c79d   SES-F004..F008 remediation (bundled with LLM-F011): events.py,
                               operations.py, session/__init__.py,
                               tests/session/test_concurrency.py (new),
                               tests/conformance/session_runner.py,
                               tests/conformance/test_schema_validation.py,
                               conformance/schema/session-scenario.schema.json,
                               conformance/session/session-owned-event-identity.yaml (new),
                               conformance/session/fork-future-boundary-rejected.yaml (new)
minion-agent-docs   27bde67   assurance/layers/03-session-artifacts.md (§0), spec/session.md
                               (compaction spelling, fork boundary rule, atomicity
                               clarification), process/implementation-conformance-workflow.md
                               (§4.6 delta-audit guardrail), this handoff
```

**Pinned Pi revision:** `b7bb00b936dbe21b8e160b3e89efdec361846699` (unchanged).

**Do not modify Rust in response to this package without first recording a verdict per finding.**
Rust's own review-before-remediation workflow applies per finding: `APPROVED` /
`REJECTED — CONTRACT_ASSURANCE_DEFECT` / `REJECTED — PI_PARITY_DEFECT` / `PI_BEHAVIOR_UNCERTAIN`.
Only after a recorded `APPROVED` verdict for a given finding should any corresponding Rust fix land,
as a new remediation PR (do not rewrite PR #4 history). Note that three of the five findings
(`SES-F004`, `SES-F006`, `SES-F008`) require **no Rust code change at all** — Rust was already
correct or is expected to already be correct; those still need Rust's own confirmation, not a fix.

---

## 1. Per-finding detail and required independent verdict

### `SES-F004` — compaction event identity (`"compaction"` → `"session/compaction"`)

**What changed:** `events.py::EventKind.COMPACTION` value corrected from the bare `"compaction"` to
the namespaced `"session/compaction"`, matching Rust's own constant and the sibling
`session/forked`/`session/reset` kinds. `spec/session.md`'s owned-kinds list corrected to match. New
`expect_event_kinds` canonical mechanism (schema + runner + `session-owned-event-identity.yaml`)
added so this class of defect (compact()-writes and derive()-reads sharing the same wrong internal
spelling, cancelling out undetected) cannot recur silently.

**Rust's required verdict:**
1. Language-neutral? Is `"session/compaction"` the correct canonical value independent of which
   implementation happened to pick it first?
2. Pi-compatible? N/A — `MINION-002`/`MINION-003` mark this as Minion-owned, not Pi-derived; confirm
   this framing is still correct.
3. Idiomatic typed Rust representation possible? Does Rust's existing `const COMPACTION: &str =
   "session/compaction"` need any change? (Expected: no — Rust was already correct.)
4. Thin runner possible? Does the Rust canonical Session runner read `event_kinds` directly from
   committed events, or does it need new wiring to expose them for `expect_event_kinds`?
5. Future-layer simulation required? No — this is a same-layer constant-identity check.

**Expected Rust action:** confirm-only; no Rust code change expected. If Rust's canonical runner
does not yet expose committed event kinds for the `expect_event_kinds` assertion, add that
projection (test-only, not `session/mod.rs` itself).

---

### `SES-F005` — role-specific content-block validity

**What changed:** `session-scenario.schema.json`'s `step.append` gained a role-discriminated
`allOf`/`if`/`then` restriction so a `user` append cannot carry a `ThinkingBlock`/`ToolCall`, an
`assistant` append cannot carry an `ImageBlock`, and a `tool_result` append cannot carry a
`ThinkingBlock`/`ToolCall` — matching Pi's frozen per-role unions
(`packages/ai/src/types.ts:421-467`). No Python production code changed; Python's real message
objects already only construct valid combinations.

**Rust's required verdict:**
1. Language-neutral? Does the per-role restriction match Pi's frozen unions exactly, independent of
   either implementation's internal representation?
2. Pi-compatible? Re-read `packages/ai/src/types.ts:421-467` directly at the pinned commit; confirm
   `UserMessage: TextContent|ImageContent`, `AssistantMessage: TextContent|ThinkingContent|ToolCall`,
   `ToolResultMessage: TextContent|ImageContent`.
3. Idiomatic typed Rust representation possible? Does Rust's own typed message enum already make
   role-invalid content combinations unrepresentable by construction (the Rust-idiomatic equivalent
   of this JSON Schema restriction)? If so, no Rust change is needed — the schema fix only closes a
   DSL/scenario-authoring gap Rust's own type system never had.
4. Thin runner possible? Does the Rust canonical Session runner reject a role-invalid scenario
   input the same way, or does it need to newly validate this (rather than relying on the type
   system alone, if scenario construction happens through an untyped intermediate)?
5. Future-layer simulation required? No.

**Expected Rust action:** likely confirm-only, since a sum-typed Rust representation should already
make invalid combinations unrepresentable. Verify this claim rather than assume it.

---

### `SES-F006` — fork boundary beyond committed tip

**What changed:** `operations.py::fork()` now rejects `boundary > tip`, raising a new
`InvalidForkBoundaryError` (previously silently accepted, leaking later ancestor writes into an
already-created child — reproduced empirically before the fix). `spec/session.md`'s fork paragraph
now states the rule explicitly: `0 <= boundary <= source's committed tip` at fork time. New
`expect_error` canonical mechanism (the schema declared this key since `SES-F001` but the runner
never implemented it — now fixed) plus `fork-future-boundary-rejected.yaml`.

**Rust's required verdict:**
1. Language-neutral? Is `0 <= boundary <= tip` the correct rule independent of which language
   enforces it, given the contract's own "later writes to either side stay private to that side"
   requirement?
2. Pi-compatible? N/A — fork is Minion-owned (`MINION-002`); confirm this framing.
3. Idiomatic typed Rust representation possible? Rust's own `fork()` already returns
   `Result<Self, SessionError>` with an explicit `InvalidForkBoundary { boundary, tip }` variant —
   confirm this maps to the now-documented rule with no further change needed.
4. Thin runner possible? Confirm Rust's canonical runner calls the real `fork()` API and surfaces
   the real structured error, without pre-checking the boundary itself before calling.
5. Future-layer simulation required? No.

**Expected Rust action:** confirm-only; Rust was already correct and is the reason this defect was
caught in the first place.

---

### `SES-F007` — atomic append/compaction linearization

**What changed:** `spec/session.md`'s atomicity paragraph extended to clarify that "atomic" means
logically indivisible and does not by itself mandate a specific thread-safety mechanism — an
execution model with no concurrent-caller hazard (Python's single-threaded cooperative asyncio,
no `await` mid-append/mid-compact) satisfies the rule without extra synchronization; an execution
model that does admit concurrent callers (Rust's OS threads) must still produce the same observable
result by whatever mechanism its language provides. No Python code changed — 3 new adversarial
`asyncio.gather` interleaving tests added confirming Python's existing lock-free design is already
correct under its own supported execution model.

**Rust's required verdict:**
1. Language-neutral? Does the clarified wording correctly describe both implementations' existing,
   already-correct designs, or does it inadvertently permit an observable difference between them
   that shouldn't be allowed?
2. Pi-compatible? N/A — concurrency behavior is not Pi-derived; Pi's own `Session` has a different
   architecture entirely (`MINION-002`).
3. Idiomatic typed Rust representation possible? Confirm Rust's existing single-mutex-scope
   `compact()`/`append()` design remains the correct, idiomatic way to satisfy the clarified rule
   under Rust's real OS-thread concurrency model — no change expected.
4. Thin runner possible? N/A — this finding's evidence is language-level concurrency tests, not
   canonical YAML, per the explicit instruction that canonical scenarios should not become a thread
   scheduler.
5. Future-layer simulation required? No.

**Expected Rust action:** confirm-only; no Rust code change expected. Rust should independently
verify its own mutex-based design still satisfies the clarified rule and add its own
language-level concurrency regression tests if it does not already have equivalent coverage.

---

### `SES-F008` — event-name validator parity (`plugin-name/foo`)

**What changed:** No schema, spec, or Python code change — the canonical/Python rule (first
`/`-segment excludes `-`, later segments permit it) was already unambiguous, confirmed by testing
`plugin-name/foo` directly against the schema pattern (rejected, as expected). A new pinned
regression test (`test_session_event_name_pattern_matches_the_canonical_rule`, 9 parametrized cases)
was added so a future implementation can be checked against the exact rule, not against prose. Rust
was found to be more permissive (`EventKind::new()` validates every segment identically, allowing
`-` in the first segment too) — classified as a Rust implementation defect, not a new contract
defect.

**Rust's required verdict:**
1. Language-neutral? Confirm the canonical rule (first segment: no `-`; later segments: `-`
   permitted) independent of Rust's current, more permissive behavior.
2. Pi-compatible? N/A — event-name validation is Minion-owned architecture, not Pi-derived.
3. Idiomatic typed Rust representation possible? Can `EventKind::new()`'s validation be split
   per-segment-position (first segment vs. later segments) cleanly in Rust, matching the canonical
   regex exactly?
4. Thin runner possible? N/A — this is a validator-internals fix, not a runner concern.
5. Future-layer simulation required? No.

**Expected Rust action (only after `APPROVED`):** align `EventKind::new()`'s first-segment
validation with the canonical rule (exclude `-` from the first segment only, continue permitting it
in later segments). This is the one finding in this package that does require an eventual Rust code
change — but not in this pass, and not without Rust's own recorded `APPROVED` verdict first.

---

## 2. Explicitly rejected fixes

- Do not fold any of these five findings into a single combined finding — each retains its own ID
  and independent disposition.
- Do not treat `SES-F007`'s clarified wording as license to add unnecessary locking to a design
  that is already correct under its supported execution model, in either language.
- Do not broaden or narrow the `SES-F008` event-name regex in Python/schema — it was confirmed
  already correct; only Rust's validator needs to change, and only after Rust's own review.

---

## 3. What Rust does NOT need to do in this pass

- Does not need to address `LLM-F011` in this package — handed off separately in
  `02-llm-delta-rust-handoff.md`, and gates this package's own certification.
- Does not need to start Layer 04 (XFORM).
- Does not need to touch anything outside the files listed in §1's per-finding sections plus the
  shared-contract files listed in the header.
