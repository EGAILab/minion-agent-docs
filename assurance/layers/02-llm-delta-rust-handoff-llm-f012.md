# Layer 02 — `LLM-F012` Delta Rust Implementation-Owner Review Package

**Prepared:** 2026-08-24
**Prepared by:** Claude (Python/shared-contract owner, per the adopted workflow)
**Why this exists:** Layer 02 was `CERTIFIED` on 2026-08-23, and its first post-certification delta
(`LLM-F011`) `CLOSED` on 2026-08-24. A Layer-04 Rust review then found that `messages.py`'s public
vocabulary types excluded values the certified contract (`spec/llm.md`) and pinned Pi already
require to be valid — most visibly, `UserMessage.content` excluded its own `string` alternative.
Full finding detail: `assurance/layers/02-llm.md` §0b (`LLM-F012`).

**Dependency-ordering note:** review this package **first**, before the `SES-F009` and Layer-04
`R001`/`R002` re-review packages — Session persists this vocabulary (`SES-F009` depends on this
landing correctly) and Layer 04's `transform_messages()` operates on it directly (`XFORM-R001`'s
complete fix depended on this too).

**Reviewed commits (delta candidate):** see the consolidated candidate SHAs recorded in the final
report accompanying this handoff round (this pass bundles `LLM-F012`, `SES-F009`, and Layer 04's
`XFORM-R001`/`XFORM-R002` fixes in one Python/shared push, since they were discovered and fixed
together — but each retains its own finding ID and independent verdict requirement below).

**Pinned Pi revision:** `b7bb00b936dbe21b8e160b3e89efdec361846699` (unchanged).

**Do not modify Rust in response to this package without first recording a verdict.**

---

## 1. What changed

`src/minion_agent/llm/content.py`: new role-specific aliases —
`UserContentBlock = TextBlock | ImageBlock`, `AssistantContentBlock = TextBlock | ThinkingBlock |
ToolCallBlock`, `ToolResultContentBlock = TextBlock | ImageBlock`. The generic `ContentBlock` alias
is retained only for internal generic helpers (encode/decode, normalization) — never for a message
type's own field.

`src/minion_agent/llm/messages.py`:
- `UserMessage.content: str | tuple[UserContentBlock, ...]` (was `tuple[ContentBlock, ...]`)
- `AssistantMessage.content: tuple[AssistantContentBlock, ...]` (was `tuple[ContentBlock, ...]`)
- `ToolResultMessage.content: tuple[ToolResultContentBlock, ...]` (was `tuple[ContentBlock, ...]`)
- `text_of()` returns a string-valued `content` directly, rather than attempting to iterate it as
  blocks (which would split it character-by-character).

Nine consumer call sites retyped to their real role-specific shape, no new runtime validation added
anywhere: `session/derive.py` (`encode_message`/`decode_message`, two `typing.cast` uses narrowing
`_decode_block`'s generic return to the role already known from `raw["role"]` at that call site —
role/content legality remains a schema-level concern, `SES-F005`, not re-validated here),
`llm/transform_messages.py` (five sites), `llm/adapters/mock.py::ScriptedResponse.content` (scripted
responses are always assistant content), `tools/result.py::ToolResult.content` (always tool-result
content).

New permanent static-type evidence: `tests/typing/valid_message_construction.py` — never imported
or executed by pytest; `mypy` checking it *is* the test. Proves seven positive constructions,
including the three the Layer-04 review named directly: `UserMessage(content="hello", ...)`,
`UserMessage(content=(TextBlock(...),), ...)`, `UserMessage(content=(ImageBlock(...),), ...)`, plus
the analogous `AssistantMessage`/`ToolResultMessage` shapes. Run via:

```text
mypy src/minion_agent tests/typing/valid_message_construction.py
```

(a single-file invocation fails with spurious `import-untyped` errors, since mypy then treats the
installed `minion_agent` package as third-party rather than first-party; including `src/minion_agent`
in the same invocation resolves this).

Five negative probes (role-invalid combinations: user+`ThinkingBlock`, user+`ToolCall`,
assistant+`ImageBlock`, tool_result+`ThinkingBlock`, tool_result+`ToolCall`) were run directly and
all five correctly rejected with the exact incompatible-type error naming the frozen union —
confirmed, not committed as a permanent fixture (a file that must fail to type-check cannot itself
be part of a passing gate).

**No `spec/llm.md` change was required** — the contract already correctly specified
`UserMessage.content: string | [TextBlock|ImageBlock]`; only the Python implementation had diverged.

---

## 2. Rust's required independent verdict, per question — do not trust Python's classification

1. **Language-neutral?** Does the role-specific typing rule (`UserMessage` string-or-array,
   `AssistantMessage`/`ToolResultMessage` array-only with their own closed variant sets) hold
   independent of Python's specific implementation?
2. **Pi-compatible?** Re-read `packages/ai/src/types.ts::UserMessage`/`AssistantMessage`/
   `ToolResultMessage` directly at the pinned commit. Confirm the exact per-role content unions.
3. **Does Rust's own typed vocabulary already avoid this class of error?** This is the most
   important question for this package: did Rust's Layer-02 implementation (merged PR #3) ever
   type `UserMessage.content` (or the Rust equivalent) in a way that excluded a valid string, or
   collapse the three message types' content into one generic union? If Rust's own typed enums
   already correctly express the frozen per-role shape (a reasonable expectation for an
   idiomatically-typed language), this finding requires no Rust code change — confirm this
   directly rather than assuming it.
4. **Thin/no special-casing?** Does consuming this corrected vocabulary require any Rust runner or
   consumer to special-case string-vs-array content beyond ordinary pattern matching?

## 3. Explicitly out of scope for this package

- `SES-F009` (Layer 03) and Layer 04's `XFORM-R001`/`XFORM-R002` — handed off separately, gated
  behind this package landing first.
- Any change to `LLM-F011`'s already-closed finding or its own history.
- Layer 05.

## 4. Expected outcome

```text
LAYER 02 DELTA CONTRACT (LLM-F012)
    APPROVED
```

or a precise rejection naming exactly which typing rule is not language-neutral or not
Pi-compatible. If approved, review proceeds to `SES-F009` next (dependency order),
then Layer 04's `R001`/`R002` re-review.
