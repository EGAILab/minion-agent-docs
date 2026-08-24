# Target-Model Message Transformation

Mandatory stage order (frozen design's own sequencing):

```text
session projection -> AgentMessage-to-Message projection -> target-model transform -> provider encoder
```

`transform_messages(messages, target, normalize_tool_call_id?)` owns generic compatibility
transformation for one target model's identity (`provider + api + model_id`, the same frozen triple
`ModelId` already uses) and its one relevant capability, image input support. It does not own
provider wire encoding, and it does not own the concrete tool-call-ID normalization algorithm a
specific target API requires -- see rule 13.

**Internal pipeline order is itself normative** (observable, not an implementation detail): legacy
null-content normalization runs first and unconditionally; then unsupported-image downgrade; then a
single forward pass over per-message content transform (thinking/text/tool-call handling, and the
matching tool-result ID rewrite, both in transcript order since a result can only be rewritten once
its call's mapping already exists); then a second forward pass that synthesizes orphaned tool
results and excludes historical `error`/`aborted` assistants. Changing this order changes output for
real inputs -- an implementation MUST NOT reorder these stages.

Rules:

1. **Legacy content normalization.** Any message whose `content` is `null`/`undefined` (an untyped
   caller -- a custom tool, a hand-built history, an old session file) normalizes to an empty
   content list before anything else runs, on every role uniformly.
2. **Unsupported user image.** If, and only if, the target model's capability excludes image input,
   every image block in a `user` message's content becomes the literal text
   `(image omitted: model does not support images)`.
3. **Unsupported tool-result image.** Under the same capability gate, every image block in a
   `tool_result` message's content becomes the distinct literal text
   `(tool image omitted: model does not support images)`. `assistant` content never carries image
   blocks (frozen per-role union, `SES-F005`), so this rule has no assistant-side case.
4. **Placeholder mechanics, precisely.** Within one message's content array, consecutive raw image
   blocks collapse into exactly one placeholder text block -- not "N images become N placeholders,"
   and not deduplication across separate messages. A non-image block breaks the run: the next image
   after it gets its own placeholder. The mechanism additionally treats *any* text block whose text
   already equals the placeholder string as if a placeholder had just been emitted -- a real text
   block that happens to read the placeholder string suppresses the placeholder for an image
   immediately following it, exactly as it would suppress a second consecutive image's placeholder.
5. **Same-model signed thinking retained, even empty.** A non-redacted thinking block with a
   signature, for the same target model, is retained completely unchanged -- including when its
   visible text is empty (a provider's encrypted-reasoning case, where the signature alone carries
   replay value).
6. **Same-model unsigned non-empty thinking retained.** A non-redacted, unsigned thinking block
   with non-empty text, for the same target model, is retained unchanged.
7. **Same-model unsigned empty thinking removed.** A non-redacted, unsigned thinking block whose
   text is empty or all-whitespace, for the same target model, is dropped entirely.
8. **Same-model redacted thinking retained unchanged.** A redacted thinking block, for the same
   target model, is retained completely unchanged regardless of its signature or visible text --
   its opaque encrypted payload is only ever valid for the model that produced it, and same-model is
   exactly the case where it stays valid. (This rule was missing from the frozen spec before Layer
   04's audit; the `redacted` check runs first in the real transform, ahead of every other thinking
   case, same-model or not.)
9. **Cross-model non-redacted non-empty thinking converts to text.** A non-redacted thinking block
   with non-empty text, crossing to a different target model, becomes an ordinary text block
   carrying only its text -- true whether or not it was signed: cross-model, only the same-model
   signed-retention case (rule 5) checks the signature at all, so a cross-model block always falls
   through to this or the next rule. Any signature is discarded, never carried onto the new text
   block.
10. **Cross-model non-redacted empty thinking removed.** A non-redacted thinking block whose text is
    empty or all-whitespace, crossing to a different target model, is dropped entirely -- including
    when it carries a signature: cross-model, signature presence never overrides emptiness.
11. **Cross-model redacted thinking omitted.** A redacted thinking block, crossing to a different
    target model, is dropped entirely, regardless of signature or visible text (the same opaque
    payload that rule 8 keeps for the same model).
12. **Cross-model text loses `text_signature`.** An ordinary (non-thinking) text block crossing to a
    different target model is replaced by a fresh text block carrying only its text; same-model, it
    is retained unchanged, signature included.
13. **Cross-model tool call loses `thought_signature`; `namespace` and everything else survive.**
    Crossing to a different target model, a tool call's `thought_signature` is cleared -- but only
    when it is a genuinely non-empty string (an empty-string signature is left untouched, matching
    the underlying truthy check rather than a presence check). `id`, `name`, `arguments`, and
    `namespace` are never touched by this rule.

    **Tool-call-ID normalization is a separate, distinct mechanism, and this module does not own
    the algorithm.** `transform_messages` accepts an optional target-API-supplied
    `normalize_tool_call_id(id, target, source_assistant) -> id` callback; it has no built-in
    normalization algorithm of its own. When supplied, it is invoked only cross-model (never
    same-model), for every tool call in transcript order; whatever id it returns is recorded in a
    map for that call's lifetime, and the matching later `tool_result.tool_call_id` (looked up by
    the *original* id) is rewritten to the normalized id in the same single forward pass. An id with
    no recorded mapping, or a same-model call, is never rewritten. Owning the *decision of whether
    and how* to normalize a specific target API's ids is Phase-5/provider territory (`AI-023`); this
    module owns only the generic orchestration -- building the map and applying it consistently --
    which is fully testable today with any real, even trivial, supplied callback.
14. **Orphan tool-result synthesis.** A tool call left unresolved when a later `user` or `assistant`
    message interrupts, or when history ends with it still unresolved, gets a synthesized
    `ToolResultMessage`: `content` a single text block reading `No result provided`, `is_error:
    true`, `tool_call_id` and `tool_name` taken from the original `ToolCall` (`tool_name` is
    required, not optional -- `LLM-F011` -- so this rule must never fabricate, omit, or null it),
    and `timestamp` set to real wall-clock time at synthesis (matching Pi's `Date.now()`) -- not a
    contract value canonical evidence asserts. Only calls belonging to an assistant message this
    stage actually keeps are ever tracked as pending; a historical `error`/`aborted` assistant's own
    tool calls (rule 15) are dropped along with the message and never receive a synthetic result.
    Multiple unresolved calls from the same assistant each get their own synthetic result, in
    source order.
15. **Historical `error`/`aborted` assistant exclusion.** A historical assistant message whose
    `stop_reason` is `error` or `aborted` -- and only those two reasons, not `pending`, `length`,
    `tool_use`, or `deferred` -- is excluded entirely from what a later model request replays. Its
    own tool calls are discarded with it, per rule 14's own note.

**Invariants a conforming implementation MUST satisfy**, independent of the rules above: source
messages are never mutated (every transformed message is a new value); output is deterministic for
identical input, apart from a synthesized result's wall-clock timestamp; every output message
satisfies the Layer-02 vocabulary exactly (no null content, no role-invalid content block, no
missing required field); a non-image-capable target's output never contains an image block; a
cross-model target's output never carries a `text_signature` or (non-empty-string-sourced)
`thought_signature`.

Conformance runners MUST invoke the real library path; they may not implement any of these rules
themselves, including the tool-call-ID map orchestration -- a canonical scenario exercising rule 13
supplies a real (if trivial) `normalize_tool_call_id` callback and lets the real function build and
apply the map, rather than a runner pre-computing the rewritten ids.
