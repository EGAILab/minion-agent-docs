<!--
TRACKING NOTE — 2026-08-20 — FINAL
Rust sign-off disposition for `2026-08-20-minion-agent-design.md`:
- The focused Rust re-review approved all substantive Pi semantics and the Rust implementation direction.
- Its only remaining blocker was one stale historical bullet claiming tool-batch `terminate` was a hard stop before `agent/turn-stopping`.
- That bullet has now been replaced by an explicit supersession note stating the corrected Pi semantics: `terminate` only suppresses tool-driven automatic continuation; normal prepare/stop/steering/follow-up processing remains eligible.
- The master design status is now FROZEN.
- Rust sign-off is COMPLETE; no further Rust design review is required for this master revision.
- Next work is systematic parity-manifest-driven realignment of canonical spec/conformance, the Phase 5 amendment, Python agent-facing implementation, and Rust Phase 2+ plans/implementation.
-->

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
---

# Resolution pass — review applied to the revised master design — 2026-08-20

## Disposition

The substantive review findings have now been incorporated into
`2026-08-20-minion-agent-design.md`.

### Resolved in the master design

1. **Cancellation conflict**
   - Active run cancellation remains the mandatory Pi-fidelity behavior.
   - The master design now explicitly states that the earlier Phase 5 cooperative-only cancellation
     deferral is superseded.
   - Phase 5 build-order text now requires propagation through pending attempts, retry/backoff,
     provider streaming, and transport cancellation.

2. **Signature-vocabulary conflict**
   - The authoritative shared fields are now explicitly the Pi-shaped:
     `thinking_signature`, `redacted`, `text_signature`, `thought_signature`, and `namespace`.
   - Earlier Phase 5 wording using generic `ThinkingBlock.signature` is explicitly superseded.

3. **Already-merged implementation migration**
   - §9 now contains an explicit **Existing implementation realignment** section.
   - Existing Phase 2/3 code may be migrated incrementally or replaced where cleaner, but must pass
     the revised conformance contract before Phase 5 is considered complete.

4. **Pi baseline date**
   - The baseline commit remains
     `b7bb00b936dbe21b8e160b3e89efdec361846699`.
   - Its recorded date is corrected to **2026-08-19**.

5. **Thinking transformation matrix**
   - The previously implicit cell is now explicit:
     different target model + non-redacted empty thinking -> remove.

6. **Governance/status**
   - Status is now explicitly **PROPOSED revised master design** pending Rust-side sign-off.
   - A normative supersession/precedence rule now defines how master design, conformance, amendments,
     plans, and existing implementation resolve conflicts.

## Remaining work — not a new master-design blocker

No further architecture-design feedback is required before Rust-side sign-off.

The remaining tasks are reconciliation tasks produced by the new authoritative master contract:

```text
Phase 5 amendment
    -> remove/replace cooperative-only cancellation deferral
    -> use master signature vocabulary and target-model transformation semantics

Rust Phase 0-2 design + implementation design
    -> realign public vocabulary and stream/cancellation seams

Python implementation
    -> perform the one-time Phase 2/3 parity realignment

canonical conformance/spec
    -> add/update cases for revised vocabulary, transformMessages parity,
       active abort, Pi run/turn semantics, and other master-design corrections
```

These are implementation/document synchronization tasks, not reasons to reopen the master
architecture.

After Rust-side sign-off, the master design status should change from `PROPOSED` to `FROZEN`, and
the reconciliation work above should proceed against that frozen contract.

---

# Rust sign-off review — fresh Pi-fidelity audit of the revised master design

## Review method and authority

This is not a review of whether the design is elegant in isolation. The governing constraint is:

> Reproduce Pi's observable behavior and semantics as closely as practical.

I therefore treated the vendored Pi checkout at
`b7bb00b936dbe21b8e160b3e89efdec361846699` as the default behavioral oracle and
checked claims against the actual source, not against earlier Minion plans or shipped behavior.
The local checkout resolves exactly to that commit; its commit timestamp is
`2026-08-19T23:35:43+02:00`.

The following Pi files were read directly for this pass:

```text
packages/ai/src/types.ts
packages/ai/src/api/transform-messages.ts
packages/ai/src/api/openai-responses-shared.ts
packages/agent/src/types.ts
packages/agent/src/agent.ts
packages/agent/src/agent-loop.ts
packages/agent/src/harness/types.ts
packages/agent/src/harness/skills.ts
packages/agent/src/harness/compaction/compaction.ts
packages/coding-agent/src/core/messages.ts
```

The Pi-first constraint supersedes earlier review preferences where they conflict. In particular,
Pi's opaque string signature fields are now the correct default vocabulary. The earlier suggestion
to replace them with a generalized provider-metadata envelope should not be carried forward merely
because it is more type-explicit.

## Overall verdict

The direction change is correct and necessary. The revised design is substantially closer to Pi
than the 2026-08-18 design and should become the new ground truth after correction.

**Rust-side sign-off is withheld in the current revision.** Three observable agent/tool behaviors
contradict the pinned Pi source, one governance rule is internally contradictory, and several
public observable shapes remain too implicit to serve as a cross-language ground truth. These are
fixable without redesigning the plugin runtime.

## BLOCKING 1 — `terminate` is not an absolute run stop in Pi

The design currently says:

```text
Hard termination from the finalized tool batch takes precedence before optional continuation policy.

and

agent/turn-stopping does not run when hard tool-batch termination already ended the run.
```

The validation list reinforces that rule with:

```text
terminate-precedes-turn-stopping
terminate-not-overridable
```

This does not match Pi.

In `packages/agent/src/agent-loop.ts`, Pi folds the batch flag as:

```ts
hasMoreToolCalls = !executedToolBatch.terminate;
```

but then, unconditionally for that completed turn, executes:

```text
turn_end
prepareNextTurn
shouldStopAfterTurn
steering poll
```

If no automatic continuation or steering remains, it then polls follow-up. A terminated tool batch
therefore means only:

> The tool calls from this assistant response do not themselves require another automatic provider
> turn.

It does **not** mean:

- skip `prepareNextTurn`;
- skip `shouldStopAfterTurn`;
- reject queued steering;
- reject follow-up;
- terminate the run before normal continuation policy.

This is independently visible in the event trace and in whether queued input is processed.

Required corrections:

1. Rename the design concept away from “hard termination” or define it narrowly as suppression of
   tool-call-driven automatic continuation.
2. Remove the exception around `agent/turn-stopping`; Pi still invokes `shouldStopAfterTurn`.
3. Replace the two incorrect conformance cases with Pi-shaped cases, for example:

```text
terminate-suppresses-tool-driven-continuation
terminate-still-runs-prepare-and-stop-policy
terminate-does-not-discard-steering
terminate-allows-follow-up-when-otherwise-idle
```

4. Rework the current Python loop, which explicitly breaks before its stopping hook when
   `BatchOutcome.terminate` is true.

This is a sign-off blocker because the existing design and shipped Python code agree with each
other but disagree with Pi.

## BLOCKING 2 — initial event order and initial steering are wrong/incomplete

The design's run diagram currently places the initial input lifecycle before `turn_start`:

```text
agent_start
    [initial input message lifecycle]
    turn_start
```

Pi's `runAgentLoop()` emits, in this exact order:

```text
agent_start
turn_start
message_start(initial prompt 1)
message_end(initial prompt 1)
...
```

Only then does the first turn reach the provider request.

Pi also polls steering once at the start of `runLoop`. Messages queued while the prompt was being
started are injected into the already-open first turn before the first provider request:

```text
agent_start
turn_start
initial prompt message lifecycle
initially queued steering message lifecycle
first provider request
```

The current design describes steering only as an after-turn queue and does not pin this initial
poll. `Agent.continue()` from an assistant message separately drains steering and starts a prompt
run with the initial poll suppressed, preventing double-drain.

Required corrections:

1. Fix the normative run diagram.
2. Pin initial steering polling and the `continue()` no-double-drain behavior.
3. Add canonical trace cases for initial prompt ordering and steering queued before the first
   provider request.

Event order is public Pi behavior, so a diagram that places the events differently cannot be left
as approximate prose.

## BLOCKING 3 — tool and hook exception conversion must match Pi

The design states:

> Expected tool execution failure becomes an error tool result visible to the model. Programming/
> invariant failure remains a programming failure.

That distinction is attractive, but it is not Pi's observable tool boundary. Pi catches thrown
values across all of these stages:

```text
prepareArguments
schema validation
beforeToolCall
tool.execute
afterToolCall
```

and converts them into error tool results. The relevant catches are in `prepareToolCall`,
`executePreparedToolCall`, and `finalizeExecutedToolCall` in
`packages/agent/src/agent-loop.ts`. `afterToolCall` failure replaces the result with an error result;
it is not allowed to escape as a framework failure.

The design may still reserve panics/exceptions for Minion runtime invariants outside the Pi tool
extension boundary. It may not classify an arbitrary exception thrown by a tool or Pi-equivalent
tool hook as such an invariant, because Pi normalizes that exact observable event.

Required corrections:

- State that every thrown/rejected value crossing the Pi-compatible tool and tool-hook boundary is
  converted to an error tool result.
- Keep framework invariant failures distinct only where the failure is produced by Minion-owned
  runtime machinery outside that extension boundary.
- Add cases for `prepare_arguments`, before-hook, execute, and after-hook failure conversion.
- Specify that an after-hook failure replaces the prior result with the generated error result,
  matching Pi.

The current Python tool execution catches tool exceptions, but its event-waterfall hooks and
post-processing need to be audited against the full Pi catch boundary rather than assumed aligned.

## HIGH 1 — normative precedence contradicts the validation section

The new precedence list says:

```text
1. current frozen master design and language-neutral spec
2. canonical conformance
```

The validation section later says:

> For behavior a conformance scenario covers, the executable result is the compatibility oracle and
> wins over prose.

Both cannot govern the same conflict.

Recommended resolution:

```text
For covered examples:
    canonical conformance is the executable oracle.

For the general rule and behavior outside finite examples:
    normative spec governs.

The master design explains architecture and intent, but a conflict among these artifacts is a
release-blocking defect to repair, not an invitation to silently choose one by a global list.
```

If a strict list is retained, it should put the normative spec and covered conformance at the same
semantic authority with disjoint scopes, then place design rationale, amendments, plans, and code
below them. “Master design and spec” should not be one undifferentiated precedence entry.

## HIGH 2 — `agent_end.messages` needs its Pi meaning

The design lists `agent_end(messages)` but does not say which messages the array contains.

Pi's meaning is not “the complete transcript”:

- a prompt run returns/emits the initial prompt messages plus all messages produced during that run;
- a continuation run returns/emits only messages newly produced by that invocation, excluding the
  pre-existing context;
- queued steering/follow-up messages processed during the run join that run-produced list.

This affects callers, persistence projections, and conformance. Pin it explicitly and add a case
that distinguishes prompt-run output from continuation-run output.

## HIGH 3 — the public LLM vocabulary is not yet complete enough to freeze

The refreshed fields that are listed match Pi, including opaque string signatures. However, several
observable Pi shapes are only named or omitted:

- `UserMessage.content` is `string | [TextBlock | ImageBlock, ...]`, not only a block tuple;
- `DeferredHandle` has provider, model id, API, id, optional expiry/poll delay, and JSON-safe data;
- `AssistantMessageDiagnostic` has type, timestamp, optional structured error, and details;
- diagnostic error carries optional name, stack, and string-or-number code plus required message;
- `Context`, model identity, request/stream options, and the exact serialized spelling of the richer
  vocabulary still need a language-neutral schema;
- `transformMessages` normalizes null/undefined content from untyped/legacy callers to an empty
  content list before applying the rest of the transformation.

The design can remain implementation-neutral, but the normative spec/schema must pin these shapes
before Python and Rust publish incompatible interpretations. Add null-content normalization to the
target-model transformation rules and add schema-backed coverage for the structures above.

## HIGH 4 — callback contract violations need Pi-shaped settlement rules

Pi documents `transformContext`, steering retrieval, and follow-up retrieval as callbacks that must
not throw/reject. At the high-level `Agent` boundary, an unexpected loop failure is caught and
projected as a terminal assistant failure trace (`message_start`, `message_end`, `turn_end`,
`agent_end`) before the run becomes idle, unless a failing event listener itself prevents that
recovery path.

The design currently says an application hook should return fallback data while “a plugin bug
remains a programming failure,” without specifying the public trace. That leaves Python and Rust
free to diverge between raising, panicking, and producing Pi's failure message.

Pin the high-level Agent behavior for failures from context conversion/transformation and queue
callbacks. Keep low-level direct-loop APIs and event-listener failure behavior separate where Pi
itself differs. This should be source-audited and scenario-tested rather than generalized from the
never-raises provider rule.

## Confirmed Pi-aligned areas

The following important areas were verified directly and support the revised direction:

- the pinned Pi commit and date;
- opaque `text_signature`, `thinking_signature`, `thought_signature`, plus `redacted` and
  `namespace`;
- richer assistant identity/state, `deferred`, and usage fields;
- exact target-model transformations for unsupported images, thinking compatibility, cross-model
  metadata stripping, tool-call-id rewriting, orphan result synthesis, and exclusion of historical
  error/aborted assistants;
- content-owned Responses reasoning replay and V1/legacy text signatures;
- active run abort propagation via one `AbortController` signal;
- `is_streaming`, partial message, pending tool calls, and idle-after-final-listener state;
- prompt/continue caller errors and queue modes;
- parallel tool preflight/execution/result ordering, batch contagion, late-update suppression,
  length-stop safety, and the all-results `terminate` fold itself;
- execution-seam `Result` contracts;
- compaction defaults and last-valid-usage estimator;
- skill discovery fundamentals and the available-skills XML/escaping;
- branch/compaction summary wrapper strings.

The incorrect finding is not the `terminate` fold calculation; it is the stronger control-flow
meaning Minion assigned to the resulting boolean.

## Complete realignment requirement

Once corrected and signed off, this document should become the sole design ground truth. Realignment
must be systematic rather than a collection of opportunistic patches.

Create a checked-in parity manifest with one row per adopted Pi semantic surface:

```text
Pi source path + symbol
    -> master-design/spec rule
    -> canonical scenario(s) or explicit language-specific test
    -> Python implementation location
    -> Rust implementation location or planned phase
    -> disposition: adopted | deferred parity | intentional divergence
```

Every row must have a disposition. This is the practical enforcement mechanism for the design's
“silence is not valid” rule and should be the Phase 0 exit artifact.

Audit the exact pinned revision first. A later Pi update is a separate source-diff exercise; do not
mix moving-target parity with the one-time realignment.

## Rebuild versus migrate recommendation

### Python

Do not restart the entire repository. The plugin runtime, append-only session primitives, artifact
store, and deterministic test infrastructure embody intentional Minion architecture and can be
retained where their externally visible behavior passes the revised suite.

Reimplement the agent-facing vertical slice fresh rather than incrementally preserving its current
control model:

```text
LLM vocabulary + target-model transformation
    -> Pi-shaped Agent state and queue APIs
    -> Pi-shaped run/turn driver and event trace
    -> Pi-shaped tool preparation/execution/finalization
    -> active abort propagation
```

The existing Python loop defines “turn” as multiple model steps, checks `terminate` before the stop
hook, uses cooperative boundary-only cancellation, and lacks the revised vocabulary/state surface.
Those are foundational assumptions, so patching them one at a time risks retaining hidden obsolete
semantics. A fresh internal driver behind retained plugin/session interfaces is cleaner.

### Rust

Keep the completed Phase 1 runtime unless revised runtime conformance finds an actual conflict; Pi
fidelity does not require replacing Minion's intentional plugin-kernel architecture.

Rust Phase 2 and later semantic services are not substantially implemented. Discard and rewrite the
superseded Phase 2+ executable plans before writing those modules. Starting those layers fresh from
the corrected Pi parity manifest is lower risk than translating the old provider-neutral API and
then migrating it immediately.

Do not carry forward the earlier generic signature envelope or separate `ProviderContinuation`
architecture. Do retain restartable provider-attempt control, active cancellation, exact public
stream settlement, and Rust-appropriate typed representations of the Pi-visible fields.

### Canonical conformance

Treat the existing suite as evidence about the superseded design, not as authority over the new
ground truth. Preserve runtime cases that remain valid. Replace or revise agent/session cases that
encode old turn, terminate, cancellation, vocabulary, or projection semantics.

Run new alignment cases against Python first to prove they detect the shipped divergences, then
implement the same cases through the real Rust APIs. Thin runners may translate values but must not
implement Pi transformation or loop semantics themselves.

## Required actions before Rust sign-off

1. Correct `terminate` control flow and replace the contradictory conformance cases.
2. Correct initial event order and pin initial steering/no-double-drain behavior.
3. Align tool and hook exception conversion with Pi.
4. Resolve normative precedence without contradicting the conformance-oracle rule.
5. Pin `agent_end.messages` semantics.
6. Complete the public vocabulary/spec shapes and add null-content normalization.
7. Pin high-level callback-failure settlement.
8. Add the parity-manifest requirement to Phase 0 and use it to audit all prior artifacts.

After those changes, perform one focused Rust review of the corrected sections. Do not rerun the old
Phase 5 continuation debate; the new master vocabulary supersedes it.

## Final disposition

```text
PI-FIDELITY DIRECTION
    APPROVED AND NON-NEGOTIABLE

CURRENT MASTER DESIGN
    NOT YET SIGNED OFF

REASON
    three verified Pi behavior mismatches
    one normative-authority contradiction
    several underspecified observable contracts

IMPLEMENTATION STRATEGY AFTER SIGN-OFF
    preserve Minion runtime/session infrastructure where revised tests prove compatibility
    rewrite Python agent-facing vertical slice where old control assumptions dominate
    keep Rust Phase 1 runtime
    rewrite Rust Phase 2+ plans and implement those layers fresh
```

The design is close in architecture but cannot be frozen while its conformance list and shipped
Python loop encode behavior that the pinned Pi source demonstrably does not have.
---

# Resolution of first Rust sign-off review — corrected master submitted for focused re-review

## Summary

All eight actions requested by the Rust sign-off review have been applied to the attached
`2026-08-20-minion-agent-design.md`.

## Blockers

### BLOCKING 1 — terminate control flow — RESOLVED IN DESIGN

The design no longer treats batch `terminate` as an absolute run stop.

It now pins:

```text
all finalized tool results terminate
    -> suppress tool-call-driven automatic continuation only

then still:
    turn_end
    prepareNextTurn
    shouldStopAfterTurn
    steering poll
    follow-up when otherwise idle
```

The old conformance cases:

```text
terminate-precedes-turn-stopping
terminate-not-overridable
```

have been removed from the proposed canonical list and replaced by:

```text
terminate-suppresses-tool-driven-continuation
terminate-still-runs-prepare-and-stop-policy
terminate-does-not-discard-steering
terminate-allows-follow-up-when-otherwise-idle
```

### BLOCKING 2 — initial event order / initial steering — RESOLVED IN DESIGN

The normative prompt-run trace is now:

```text
agent_start
turn_start
initial prompt message lifecycle
initial steering poll + claimed-message lifecycle
first provider request
...
```

`continue()` now explicitly suppresses the initial steering poll when it already pre-drained
steering to seed the continuation invocation, preventing double claim.

Added proposed canonical cases:

```text
initial-prompt-order-after-turn-start
initial-steering-before-first-request
continue-steering-no-double-drain
```

### BLOCKING 3 — tool/hook exception conversion — RESOLVED IN DESIGN

The Pi-compatible tool extension boundary now converts thrown/rejected values into error tool
results for:

```text
prepare_arguments
schema validation
beforeToolCall / tools-pre-execute
tool.execute
afterToolCall / tools-post-execute
```

An after-hook failure explicitly replaces the previously produced result with the generated error
result.

Framework invariant failures may still escape only when produced by Minion-owned runtime machinery
outside this Pi-compatible extension boundary.

Added proposed canonical cases for every stage.

## High findings

### HIGH 1 — normative authority — RESOLVED IN DESIGN

The contradictory global precedence list is removed.

The design now states:

```text
covered finite example
    -> canonical conformance is executable oracle

general rule / behavior outside finite examples
    -> normative spec governs

master design
    -> architecture, scope, adopted decisions, mapping obligations

contradiction among frozen master/spec/conformance
    -> release-blocking specification defect to repair
```

No frozen artifact silently wins a contradiction by list position.

### HIGH 2 — `agent_end.messages` — RESOLVED IN DESIGN

The value is now explicitly invocation-local:

```text
prompt run
    -> initial prompt + all messages produced/queue-consumed in that run

continuation run
    -> only messages newly produced/queue-consumed by that invocation
       (pre-existing transcript excluded)
```

Agent return value and `agent_end.messages` use the same message set.

### HIGH 3 — public LLM vocabulary — RESOLVED IN DESIGN

The master now explicitly pins:

```text
UserMessage.content = string | [TextBlock | ImageBlock, ...]

DeferredHandle
DiagnosticError
AssistantMessageDiagnostic
LlmContext
canonical model identity = provider + api + model_id
canonical snake_case serialization
shared ProviderRequestOptions / StreamOptions / SimpleStreamOptions semantic fields
```

It also pins legacy/null content normalization to an empty content list before target-model
transformation and adds schema-backed conformance coverage.

### HIGH 4 — high-level callback failures — RESOLVED IN DESIGN

Unexpected high-level Agent failures from context conversion/transformation or steering/follow-up
retrieval now have a Pi-shaped settlement rule:

```text
terminal assistant failure
message_start
message_end
turn_end
agent_end
idle
```

subject to Pi's separate event-listener failure behavior. Low-level loop/runtime invariant behavior
remains separate.

## Complete realignment / parity manifest — ACCEPTED

Phase 0 now requires the checked-in parity manifest requested by Rust review:

```text
Pi source path + symbol
    -> master/spec rule
    -> canonical scenario(s) or explicit language-specific test
    -> Python implementation location
    -> Rust implementation location or planned phase
    -> adopted | deferred parity | intentional divergence
```

The design also adopts the review's implementation strategy:

```text
Python
    retain compatible runtime/session/artifact/test infrastructure
    reimplement agent-facing vertical slice fresh

Rust
    retain Phase 1 runtime if revised runtime conformance remains green
    rewrite Phase 2+ executable plans before implementing semantic layers
```

## Requested focused Rust re-review

The master remains:

```text
PROPOSED
```

No additional broad design review is requested.

Please re-review only the corrected surfaces corresponding to the eight prior required actions:

1. terminate control flow;
2. initial event order and initial steering/no-double-drain;
3. tool/hook exception conversion;
4. normative authority;
5. `agent_end.messages`;
6. public LLM vocabulary/schema and null-content normalization;
7. high-level callback failure settlement;
8. Phase 0 parity manifest / realignment requirement.

If those corrections match pinned Pi behavior and are internally coherent, the requested disposition
is:

```text
RUST SIDE
    SIGN OFF

MASTER DESIGN
    FROZEN

NEXT
    systematic parity-manifest-driven realignment of:
        canonical spec/conformance
        Phase 5 amendment
        Python agent-facing implementation
        Rust Phase 2+ plans and implementation
```

The retired ProviderContinuation and generalized signature-envelope proposals are outside the scope
of this focused re-review unless the corrected master reintroduces them; it does not.

### Final vocabulary tightening before focused Rust re-review

The generated master design additionally pins the previously shorthand message fields:

- `AssistantMessage.role = assistant`;
- `diagnostics` is explicitly a list of `AssistantMessageDiagnostic`;
- `deferred` is explicitly a `DeferredHandle`, not a boolean;
- `ToolResultMessage` now has an explicit language-neutral shape and role;
- diagnostic details remain JSON-safe.

This is a clarification of HIGH 3, not an additional design direction.

---

# Focused Rust re-review after incorporation

**Date:** 2026-08-20
**Pi baseline rechecked:** `b7bb00b936dbe21b8e160b3e89efdec361846699`

## Result

The revised normative sections now resolve every substantive finding from the first Rust sign-off
review and agree with the pinned Pi implementation:

- a finalized tool-batch `terminate` fold suppresses only tool-driven automatic continuation;
  normal prepare/stop/steering/follow-up processing still occurs;
- prompt lifecycle starts `agent_start -> turn_start -> initial message events`, and the first
  steering poll occurs before the first provider request;
- `continue()` prevents double-claiming steering that it already drained;
- failures crossing Pi's argument-preparation, validation, before-hook, execution, and after-hook
  boundary become error tool results, with after-hook failure replacing the earlier result;
- normative spec and covered conformance have disjoint authority, and disagreement is now treated
  as a release-blocking specification defect;
- `agent_end.messages` is invocation-local and has the same message set as the returned run result;
- the shared LLM vocabulary, target-model identity, option spellings, and null-content normalization
  are sufficiently explicit to produce matching Python/Rust schemas;
- high-level callback failure settlement now matches `Agent.handleRunFailure` while keeping
  low-level loop and Minion runtime-invariant failures distinct;
- Phase 0 now requires the source-to-rule-to-test-to-implementation parity manifest needed for the
  complete realignment.

These conclusions were checked directly against Pi's `packages/agent/src/agent-loop.ts`,
`packages/agent/src/agent.ts`, `packages/agent/src/types.ts`, `packages/ai/src/types.ts`, and
`packages/ai/src/api/transform-messages.ts` at the adopted commit.

## FINAL BLOCKER — stale termination claim remains in the current master

The historical resolution list near the end of the current master still says:

> **Hard termination precedes `agent/turn-stopping`.** The `terminate` batch rule is a loop
> invariant inherited from pi, where no hook could force continuation.

That statement is false for the adopted Pi baseline and directly contradicts the corrected
normative §§6/8 and the new canonical scenario names. Although the supersession section says older
rationale is not competing normative authority, this sentence is embedded in the current master,
references the current §6, and incorrectly attributes the behavior to Pi. It must not remain as an
unqualified “resolved” decision in the frozen document.

Required edit: either delete that historical bullet or replace it with an explicit supersession
note, for example:

> **Superseded termination interpretation.** The 2026-08-18 design incorrectly treated the
> all-results `terminate` fold as a hard stop preceding `agent/turn-stopping`. The 2026-08-20 Pi
> audit corrected it: the fold only suppresses tool-driven automatic continuation, while normal
> prepare/stop/steering/follow-up processing remains eligible.

No code, plan, schema, or architectural change is required beyond removing this internal
contradiction.

## Sign-off disposition

```text
SUBSTANTIVE PI SEMANTICS
    APPROVED

RUST IMPLEMENTATION DIRECTION
    APPROVED

MASTER DESIGN FREEZE
    WITHHELD ONLY FOR THE STALE HISTORICAL TERMINATION BULLET

AFTER THAT EDIT
    Rust sign-off is complete; no further Rust design round is required
```

Once that single cleanup is made, change the master status to frozen and proceed with the
parity-manifest-driven review of all prior conformance, plans, Python code, and Rust Phase 2+ work.
---

# Final Rust sign-off resolution — editorial blocker removed

**Date:** 2026-08-20
**Pi baseline:** `b7bb00b936dbe21b8e160b3e89efdec361846699`

## Final blocker resolution

The focused Rust re-review withheld freeze only because one historical bullet in the current master
still incorrectly said:

```text
Hard termination precedes agent/turn-stopping.
```

That stale statement has now been replaced with:

```markdown
- **Superseded termination interpretation.** The 2026-08-18 design incorrectly treated the
  all-results `terminate` fold as a hard stop preceding `agent/turn-stopping`. The 2026-08-20 Pi
  audit corrected it: the fold only suppresses tool-driven automatic continuation, while normal
  prepare/stop/steering/follow-up processing remains eligible.
```

This removes the final internal contradiction without changing any already-approved normative
semantics.

## Final disposition

```text
SUBSTANTIVE PI SEMANTICS
    APPROVED

RUST IMPLEMENTATION DIRECTION
    APPROVED

FINAL EDITORIAL BLOCKER
    RESOLVED

RUST SIGN-OFF
    COMPLETE

MASTER DESIGN
    FROZEN

FURTHER RUST DESIGN ROUND
    NOT REQUIRED
```

## Next work

Proceed against the frozen master through the Phase 0 parity manifest:

```text
Pi source path + symbol
    -> frozen master/spec rule
    -> canonical scenario(s) / language-specific tests
    -> Python implementation
    -> Rust implementation / planned phase
    -> adopted | deferred parity | intentional divergence
```

Realign, in order:

```text
1. canonical spec/conformance
2. Phase 5 real-provider amendment
3. Python agent-facing vertical slice
4. Rust Phase 2+ plans
5. Rust Phase 2+ implementation
```

The plugin runtime and compatible session/artifact substrate remain retained where the revised
parity suite proves behavior compatible. The retired `ProviderContinuation` and generalized
signature-envelope directions remain superseded and must not be reintroduced through implementation
plans.

## Independent verification (this reviewer, not the Rust review thread above)

Before accepting FROZEN status, I independently re-checked the three highest-risk new claims from
this thread's resolution round against Pi source myself, rather than trusting the thread's own
"checked directly against..." citations at face value:

- **Terminate does not precede `agent/turn-stopping`** (the final blocker) — confirmed. In
  `agent-loop.ts`'s `runLoop`, setting `hasMoreToolCalls = false` (the terminate fold) only affects
  whether the *inner* `while` loop runs another iteration; `turn_end`, `prepareNextTurn`,
  `shouldStopAfterTurn`, and the steering-queue poll all execute unconditionally in the same iteration
  regardless of `hasMoreToolCalls`'s value. The 2026-08-18 design's "hard termination precedes
  turn-stopping" claim was genuinely wrong; this revision's correction is genuinely right.
- **Initial steering poll precedes the first provider request** — confirmed. `pendingMessages` is
  populated via `getSteeringMessages()` *before* `runLoop`'s outer loop even starts (comment:
  "Check for steering messages at start (user may have typed while waiting)"), and the same
  drain-and-inject logic that runs for every later turn applies uniformly to the first iteration.
- **After-hook (`afterToolCall`) failure replaces the result rather than exposing it** — confirmed.
  In `finalizeExecutedToolCall`, a thrown/rejected `afterToolCall` is caught and `result` is
  reassigned to `createErrorToolResult(...)` with `isError = true` — the prior successful result is
  discarded, not merely supplemented.

All three check out exactly as claimed. Combined with the field-for-field vocabulary and
transformation-algorithm verification from my original review (still valid — this revision doesn't
touch that material), I have no remaining reservation about the *technical* content. Sign-off on the
substance is reasonable.

One thing worth the design author's attention, not a blocker: the two items from my original
review that this revision explicitly resolved (mandatory active cancellation; `thinking_signature`
vocabulary superseding `ThinkingBlock.signature`) are stated as decided in this document, but the
Phase 5 amendment itself has not yet been edited to match — it still reads as written under the
2026-08-18 assumptions. Per the project owner's stated priority (this document is ground truth once
signed off, retroactively), that reconciliation is real follow-up work, not merely documented intent.
It's listed in "Next work" above as item 2, so it isn't lost — flagging only so it doesn't quietly
slip if this file is read as the closing artifact of the review rather than a pointer to remaining
work.

## Reviewer verification

Rechecked against the pinned Pi baseline and the complete latest master diff. The supersession edit
removes the sole remaining contradiction, no obsolete hard-termination scenario or normative claim
remains, and the final disposition above is confirmed without qualification.
