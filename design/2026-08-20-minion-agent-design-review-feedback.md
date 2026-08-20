# Review — `2026-08-20-minion-agent-design.md` (Pi-fidelity audit revision)

**Reviewer note on method:** this document's own governing rule is "when behavior is uncertain,
inspect the relevant adopted Pi source before designing from first principles" and "silence is not
a valid disposition for a discovered Pi semantic change." I applied that same standard to the review
itself: every specific factual claim below was checked against the actual Pi source at the commit
this document names as its baseline (`b7bb00b936dbe21b8e160b3e89efdec361846699`), not accepted on
the document's word. Where I did not have budget to independently verify a claim, that is stated
explicitly rather than left silent — per this document's own rule, an unverified claim is not the
same as a verified one.

**Overall verdict:** the technical content is unusually well-grounded. Every specific, checkable
claim I verified — vocabulary field names/shapes, the full target-model transformation algorithm,
the active-cancellation signal-propagation mechanism, the text-signature V1/legacy wire format —
matched the actual Pi source at the named commit exactly, often field-for-field and string-for-string.
This reads like a genuine source audit, not an approximation. The problems below are not "this
document is wrong about Pi" — they are two serious cross-document consequences this revision creates
that the document itself doesn't address, plus a handful of smaller items.

---

## BLOCKING — this revision invalidates the just-finalized Phase 5 amendment's cancellation deferral

`2026-08-20-phase-5-real-providers-amendment-proposal.md` (finalized this session, five review
rounds) defers live mid-stream provider cancellation, justified by this sentence:

> "agent cancellation currently prevents subsequent work at cooperative loop boundaries; V1 does not
> require asynchronous interruption of an already-running provider stream"

backed by a direct citation to `agent_loop/driver.py` — the actual, currently-merged Python
implementation, which genuinely is cooperative/boundary-only (`self._cancelled` checked between turn
steps; no code path closes a live stream). That citation was correct when made.

This new design's §6 "Active abort/cancellation" section states the opposite as a **MANDATORY**
requirement:

> "Minion MUST expose equivalent behavior... Abort does not mean 'wait until the next
> provider-request boundary.' It is an active cancellation request... signal propagates to: provider
> stream / pending provider attempt..."

**I checked whether this claim about Pi is actually true, rather than assuming either document is
right.** It is. At the audited commit:

- `packages/agent/src/agent.ts:319` — `abort(): void { this.activeRun?.abortController.abort(); }`,
  a real, immediate `AbortController.abort()` call, not a flag checked later.
- `packages/agent/src/agent-loop.ts` — that same `signal` is threaded through `runLoop` →
  `streamAssistantResponse` → directly into the provider call: `streamFunction(config.model,
  llmContext, { ...config, apiKey: resolvedApiKey, signal })`.
- `packages/ai/src/api/openai-codex-responses.ts` (checked earlier this session) — that `signal` is
  wired into the actual `fetch()` call's `AbortSignal`, so aborting genuinely tears down an in-flight
  HTTP request.

So: Pi really does support active mid-stream cancellation reaching the transport layer, this
revision correctly identifies that as a Pi-fidelity gap, and correctly marks it MUST. None of that is
wrong. But the Phase 5 amendment's cancellation section was built entirely on the premise that
cooperative-only cancellation *is* the frozen design's position — a premise this revision now
explicitly overturns. As it stands, the Phase 5 amendment defers something the design that supersedes
its own stated target (`2026-08-18-minion-agent-design.md` → this document) now says is mandatory.

**This needs an explicit disposition, not a silent gap between two documents both dated 2026-08-20.**
Options, not a recommendation of one over the other since this is a real design tradeoff:

1. Amend the Phase 5 amendment's cancellation section to align with this document — commit to active
   cancellation reaching the provider transport as in-scope work (a materially larger scope increase
   for Phase 5's transport layer than what five rounds of review just settled).
2. Record active cancellation as a formally deferred Pi-parity item (per this document's own
   three-way disposition rule — Adopted / Deferred Pi parity / Intentional divergence) rather than
   letting the Phase 5 amendment's deferral stand as an unlabeled, undiscovered contradiction.
3. Sequence it: this document's §9 build order doesn't currently name active cancellation as its own
   phase gate; if it's meant to land with Phase 5 (real providers, since that's where a stream first
   exists to cancel), the amendment and this document need to agree on that before either freezes.

Whichever is chosen, "silence is not a valid disposition" (this document's own words) applies exactly
here.

---

## HIGH — the Phase 5 amendment's `ThinkingBlock.signature` proposal is now superseded, and should be reconciled rather than left standing as written

Independently of the point above: this session's Phase 5 amendment work (five review rounds,
finalized just before this document was presented) proposed adding **one field**, `signature`, to
`ThinkingBlock`, to carry Codex's `encrypted_content` continuation — verified at the time against
Pi's actual `openai-codex-responses.ts`/`openai-responses-shared.ts`.

This document's §4 vocabulary goes further and uses different, more precise naming, which I verified
against `packages/ai/src/types.ts` at the audited commit line-by-line:

| This document | Pi source (`types.ts`) | Verified |
|---|---|---|
| `ThinkingBlock.thinking_signature` | `thinkingSignature?: string` (line 359) | exact match |
| `ThinkingBlock.redacted` | `redacted?: boolean` (line 363) | exact match |
| `TextBlock.text_signature` | `textSignature?: string` (line 353) | exact match |
| `ToolCall.thought_signature` | `thoughtSignature?: string` (line 377) | exact match |
| `ToolCall.namespace` | `namespace?: string` (line 379) | exact match |

Two consequences:

1. **Naming inconsistency if both land as written**: the amendment's `ThinkingBlock.signature` and
   this document's `ThinkingBlock.thinking_signature` are the same concept with different names. If
   this document freezes first, the amendment's decision-log item 18 needs its field name corrected
   (`signature` → `thinking_signature`) and its `redacted` handling added — it currently has neither.
2. **The amendment's own "related, not fixed here" flag is resolved by this document.** The amendment
   explicitly noted "pi uses the identical opaque-signature pattern on `TextBlock` too... a related
   gap in the same already-frozen vocabulary, out of scope here." This document closes that gap
   directly (`text_signature`, plus `thought_signature`/`namespace` on `ToolCall` — a third case the
   amendment never flagged at all). That's a genuine improvement, not a conflict, but it means the
   amendment's scope note is now stale and should say so rather than continuing to describe a gap
   this document has already closed.

Recommend: revise the Phase 5 amendment's decision-log items 13/18 to point at this document's
vocabulary as the actual resolution once (if) this document freezes, rather than maintaining a
parallel, slightly-divergent vocabulary proposal.

---

## HIGH — this is a migration of already-shipped, tested, merged code, not new-behavior documentation

Worth stating plainly because the document doesn't: unlike the Phase 5 amendment (net-new behavior,
nothing implemented yet), §4's vocabulary changes hit code from Plan 2, already executed and merged.
Checked directly against the current implementation:

```
src/minion_agent/llm/messages.py — AssistantMessage currently has 7 fields:
    content, stop_reason, usage, model, provider, timestamp, error_message

This document's AssistantMessage has 14:
    (adds) api, response_model, response_id, diagnostics, usage-shape changes,
    deferred, error_message, raw_stop_reason, end_turn
```

```
src/minion_agent/llm/content.py — ThinkingBlock currently: { thinking: str } only.
This document's ThinkingBlock: { thinking, thinking_signature, redacted }.
```

`StopReason` gains a seventh value (`deferred`) — verified real in Pi (`types.ts:405`,
`"pending" | "stop" | "length" | "toolUse" | "error" | "aborted" | "deferred"`), but adding an enum
member to an already-frozen, already-conformance-tested type is a breaking change to existing
conformance scenarios and any exhaustive `match`/`if`-chain over `StopReason` in the current codebase
— worth an explicit sweep, not just a vocabulary table update.

This isn't a defect in the design — the changes are, as verified above, accurate Pi-parity
corrections. It's a scope/sequencing observation the document should state explicitly: freezing this
revision commits to a **migration** for already-merged Phase 2 code, and §9's build order doesn't
currently name that as its own line item (it reads as if Phase 2's original vocabulary still stands,
with these differences folded in retroactively). Recommend adding an explicit "Phase 2 vocabulary
realignment" note to §9, scoped like the other build-order phases, so this doesn't become invisible
rework discovered mid-Phase-5. The project owner has confirmed a fresh reimplementation of the
affected Phase 2 code is an acceptable alternative to incremental migration where it's cleaner — this
finding is about naming the scope explicitly in §9, not about which of the two approaches to take.

---

## On resolving the BLOCKING and first HIGH finding: the project owner has set the deciding rule

Not a finding, a note for whoever is reconciling the two items above. The project owner has confirmed
that Pi observable-behavior fidelity is a non-negotiable, top-priority constraint, and that once this
document is signed off it becomes retroactively authoritative over prior design work, including the
Phase 5 amendment. Concretely, that means the expected resolution direction for both items above is
already decided, not a three-way tradeoff to negotiate further:

- **Cancellation**: this document's mandatory active-cancellation requirement stands as written; the
  Phase 5 amendment's deferral is what needs to change (option 1 in the BLOCKING finding above), not
  this document's MUST language.
- **Signature vocabulary**: this document's naming (`thinking_signature`, `redacted`,
  `text_signature`, `thought_signature`) is what the Phase 5 amendment should be updated to match.

Both are still genuinely open until this document is signed off — it remains in draft — but the
reconciliation direction, once that happens, is not expected to be in question.

---

## Verified accurate (spot-checked against Pi source at the named commit)

Listed so the confidence behind the "unusually well-grounded" verdict above is checkable, not
asserted. All checked against `git show b7bb00b936dbe21b8e160b3e89efdec361846699:<path>` in
`ref-repos/pi`.

- **Full vocabulary field audit** (table above) — `text_signature`, `thinking_signature`, `redacted`,
  `thought_signature`, `namespace`, `response_model`, `response_id`, `diagnostics`, `deferred`
  (both as a `StopReason` value and an `AssistantMessage` field), `cache_write_1h`, `total_tokens` —
  every one present in `types.ts` under the expected (camelCase-equivalent) name.
- **Target-model transformation algorithm** (`packages/ai/src/api/transform-messages.ts`, 223 lines,
  read in full) — every specific rule in this document's transformation section matches the actual
  code exactly: the two image-placeholder strings verbatim; the thinking-compatibility branching
  (redacted+same-model retained, redacted+different-model dropped, signed+same-model retained
  including empty text, unsigned+same-model+empty removed, different-model+non-redacted converted to
  plain text with signature dropped); text/tool-call signature stripping on cross-model replay;
  tool-call-id remapping via a consistent map applied to matching `ToolResultMessage`s; orphaned
  tool-call synthesis with the exact `"No result provided"` / `is_error: true` shape, firing before a
  later assistant *and* user message and at end-of-history; and errored/aborted assistant messages
  skipped from replay entirely (`continue` before tool-call tracking, so their orphaned calls are
  dropped too, not synthesized — a detail this document's prose correctly implies without needing to
  spell out).
- **Active-cancellation signal propagation** (`agent.ts`, `agent-loop.ts`) — confirmed real, not
  overclaimed; see the blocking finding above for detail.
- **`textSignature` V1/legacy wire format** (`openai-responses-shared.ts`) —
  `encodeTextSignatureV1`/`parseTextSignature` confirmed: JSON `{v:1, id, phase?}` with phase
  constrained to `"commentary" | "final_answer"`, falling back to treating any non-JSON or
  malformed-JSON string as a bare legacy id (`{id: signature}`). Matches this document's description
  exactly, including the phase enum values.
- **Reasoning replay omission for unsigned same-model thinking** — confirmed in
  `openai-responses-shared.ts`'s encode path: a `thinking` block with no `thinkingSignature` pushes
  nothing to the request `output`/`input` array (no `else` branch) — matches "contributes no replay
  item."

## Minor — process

- **RESOLVED during this review.** Local `ref-repos/pi` was initially stale relative to the claimed
  audit baseline — checked out at `209bc7b9` (2026-08-17) while the claimed baseline `b7bb00b9`
  (2026-08-19, not 2026-08-20 as this document's reference table states — a one-day date discrepancy,
  still minor) required a `git fetch` to even become reachable locally. The commit was real and the
  content genuinely matched (that's how the verification above was performed), so this was never a
  fabrication concern — only a drift-governance gap. `ref-repos/pi` has since been pulled to
  `b7bb00b9` and now matches the audited baseline exactly. Recommend keeping it pinned there (or
  recording the commit somewhere machine-checkable) so future "verify against Pi" passes don't need
  their own fetch-and-guess step, consistent with this document's own drift-governance emphasis.
- **Thinking-compatibility table has one uncovered cell.** The table in §4 doesn't state the
  different-model + empty + non-redacted case. The code removes it (the empty-check runs before the
  same/different-model branch), and this document's rules are consistent with that outcome by
  implication, but the table itself doesn't say so — a reader relying on the table alone rather than
  the code could reasonably guess "convert to text" (matching the non-empty different-model row)
  instead of "remove." Worth an explicit fifth row.

## Not independently verified — flagged per this document's own "silence is not a disposition" rule

Given review scope, the following were read for internal consistency but not independently checked
against Pi source line-by-line, and should not be treated as verified by this review:

- The compaction estimator's exact algorithm (last-valid-usage search, error/aborted exclusion,
  `total_tokens`-vs-component-sum preference, trailing-message heuristic).
- The full skill-discovery rule list (`.gitignore`/`.ignore`/`.fdignore` handling, traversal order,
  frontmatter validation specifics).
- The exact harness message projection wrapper strings for bash execution and custom messages (the
  branch-summary and compaction-summary wrappers were read and are plausible but not diffed against
  Pi's actual string constants).
- Steering/follow-up queue mode semantics beyond what was already established in the prior design.

None of these read as suspicious — they're consistent with everything that *was* verified — but per
this document's own governance section, an unverified claim should be named as such rather than
folded silently into a clean bill of health.

## Governance note

This document's Status line calls itself a "Revised frozen design candidate" but doesn't carry the
explicit "PROPOSED / pending Rust-side + design-reviewer sign-off" framing this project has used
consistently elsewhere (the `840d414` precedent, and this session's Phase 5 amendment's own Status
line). Given its scope — superseding the entire master design, not just amending one section — it
should probably carry at least as much explicit pending-review framing as the smaller Phase 5
amendment did, not less.
