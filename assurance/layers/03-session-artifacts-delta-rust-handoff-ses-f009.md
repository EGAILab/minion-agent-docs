# Layer 03 — `SES-F009` Delta Rust Implementation-Owner Review Package

**Prepared:** 2026-08-24
**Prepared by:** Claude (Python/shared-contract owner, per the adopted workflow)
**Why this exists:** Layer 03 was `CERTIFIED` on 2026-08-24, and its first post-certification delta
(`SES-F004`..`SES-F008`) `CLOSED` the same day. The same Layer-04 Rust review that surfaced
`LLM-F012` also found that Session persistence (`session/derive.py::encode_message`/
`decode_message`) could not safely round-trip a valid string-valued `UserMessage.content`, since it
computed `content` uniformly (as a block array) before dispatching on role. Full finding detail:
`assurance/layers/03-session-artifacts.md` §0b (`SES-F009`).

**Dependency-ordering note:** review this package **after** `02-llm-delta-rust-handoff-llm-f012.md`
(`LLM-F012` must be `APPROVED` first — Session persists Layer-02 vocabulary, it does not own its
typing) and **before** Layer 04's `R001`/`R002` re-review.

**Reviewed commits (delta candidate):**

```text
minion-agent        4ed360d   src/minion_agent/session/derive.py, conformance/schema/
                               session-scenario.schema.json, tests/conformance/session_runner.py,
                               conformance/session/string-user-message-round-trip.yaml (new),
                               tests/session/test_derive.py -- same push as LLM-F012 (§1 of the
                               02-llm-delta-rust-handoff-llm-f012.md package)
minion-agent-docs   f610e8b   assurance/layers/03-session-artifacts.md (§0b, this finding), this
                               handoff
```

**Pinned Pi revision:** `b7bb00b936dbe21b8e160b3e89efdec361846699` (unchanged — `MINION-002`
already marks Session persistence as Minion-owned architecture, not Pi-derived).

**Do not modify Rust in response to this package without first recording a verdict.**

---

## 1. What changed

`src/minion_agent/session/derive.py`:
- `encode_message()`'s `user` branch: a `str`-valued `content` encodes as itself (already
  JSON-safe); a block-array `content` encodes through the existing, unchanged path.
- `decode_message()`'s `user` branch: a JSON string decodes to a Python string directly; a JSON
  array decodes through the existing `_decode_block` path, unchanged.
- Assistant and tool-result branches are entirely unchanged — their vocabulary has no string
  content variant (`LLM-F012` confirmed this).

`conformance/schema/session-scenario.schema.json`:
- `step.append.content` gained a `user`-only (and plugin-role, which builds as a user message per
  `session_runner.py`'s own established rule) string alternative, via the same role-conditional
  `allOf`/`if`/`then` pattern already governing the existing content-type-enum restriction.
  `assistant`/`tool_result` remain array-only.
- New `expect_user_details` observation (mirroring the existing `expect_assistant_details`/
  `expect_tool_result_details` pattern), since `expect_messages`' role/text projection cannot
  distinguish a string-valued `content` from a single-`TextBlock` array — both produce identical
  visible text. This is the language-neutral observation that actually proves which representation
  Session persisted.

`tests/conformance/session_runner.py`: new `_user_content()` (decode: a scripted string stays a
string; the pre-existing `text` shorthand still means "one `TextBlock`," deliberately unchanged, to
avoid conflating the two) and `_user_detail()` (the matching real-value normalizer for comparison).

New canonical scenario `conformance/session/string-user-message-round-trip.yaml`: scripts a string
message, a single-`TextBlock`-array message, and — after a real `fork` — another string message.
`expect_user_details` proves all three retain their real scripted representation through actual
Session persistence and derivation, **including across a fork boundary** (fork references, does
not copy — `SES-006` — so this also incidentally re-confirms that unmodified representation
carries across the reference correctly).

Two new focused unit tests in `tests/session/test_derive.py` pin the encode/decode behavior
directly: `test_string_valued_user_message_round_trips_as_a_string`,
`test_string_and_single_text_block_user_messages_remain_distinct_after_round_trip`.

---

## 2. Rust's required independent verdict, per question — do not trust Python's classification

1. **Language-neutral?** Does "a string-valued `UserMessage.content` persists and derives as a
   string, exactly, never normalized into a block array" hold as a rule independent of either
   implementation's internal storage representation?
2. **Does Rust's own certified Session implementation already handle this correctly?** This is the
   central question. Rust's `session::Session` was certified in the original `SES-004`..`008` cycle
   before this string-content question was ever raised. Determine directly: does Rust's own
   message-persistence path (`session/mod.rs` and whatever typed representation it uses for a
   persisted `UserMessage`) already distinguish string from block-array content, or did it — like
   Python — implicitly assume block-array content uniformly? If Rust's typed persistence layer
   already used an enum distinguishing the two (a natural idiomatic-Rust choice), this finding may
   require zero Rust code change; if not, this is a genuine Rust implementation gap parallel to the
   Python one just fixed, and should be recorded as such rather than assumed away.
3. **Thin runner possible?** Confirm the Rust canonical Session runner (if one exists for this
   scenario family) can construct a real string-valued `UserMessage`, call the real persistence
   API, and observe the real derived representation, without simulating anything itself.
4. **Fork boundary interaction correct?** Confirm the new canonical scenario's fork-boundary case
   (a string-content message inherited across a fork) exercises Rust's real `fork()`/derivation
   path with no special-casing.

## 3. Explicitly out of scope for this package

- `LLM-F012` (Layer 02) — reviewed separately, gates this package.
- Layer 04's `XFORM-R001`/`XFORM-R002` — reviewed separately, depends on this package.
- `SES-F004`..`SES-F008`'s own already-closed history — not reopened.
- Layer 05.

## 4. Expected outcome

```text
LAYER 03 DELTA CONTRACT (SES-F009)
    APPROVED
```

or a precise rejection. If approved, review proceeds to Layer 04's `R001`/`R002` re-review
(dependency order: this package must land before that one is meaningful, since Layer 04 consumes
Session-derived output).
