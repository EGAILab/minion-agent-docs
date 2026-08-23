# LLM Seam — Fidelity Assurance & Certification

**Layer ID:** `02`  
**Status:** `IN_AUDIT`  
**Audit date:** 2026-08-23 (Steps 0-2 complete: Pi source read directly, requirement traceability and
Python module deep audit done; §6 existing-test audit and §8-14 review not yet started; 4 new
PI_PARITY_DEFECT findings raised, none remediated yet — see §17)  
**Auditor:** Claude (Python-driven, per adopted workflow)  
**Python status:** `IMPLEMENTED`  
**Rust status:** unassessed this pass — Python drives audit/remediation first, per the adopted
workflow; Rust cross-check follows once Python's evidence is stable, the same sequence Runtime
followed.

---

## 1. Scope

### Owns

The provider-neutral LLM vocabulary and stream contract (`process/requirement-id-convention.md`
prefix `LLM-###`), per frozen master §4 "The LLM seam (`ctx.llm`)":

- Core content vocabulary: `TextBlock`, `ThinkingBlock`, `ImageBlock`, `ToolCall`, and the three
  opaque replay-signature fields (`text_signature`, `thinking_signature`, `thought_signature`).
- Message vocabulary: `UserMessage`, `AssistantMessage`, `ToolResultMessage`, `DeferredHandle`,
  `DiagnosticError`, `AssistantMessageDiagnostic`, `LlmContext`.
- Model identity: the `provider + api + model_id` triple as the canonical compatibility key.
- Request/stream option schema: `ProviderRequestOptions`, `StreamOptions`, `SimpleStreamOptions`,
  and the obligation that every Pi-observable option for an implemented API has a schema-mapped or
  explicitly-deferred path.
- `StopReason` and `Usage` vocabulary, including cost accounting fields.
- Stream chunk/event vocabulary (`start`, `text_start/delta/end`, `thinking_start/delta/end`,
  `tool_call_start/delta/end`, `done`, `error`) and partial-update semantics.
- Image content identity: content-addressed, immutable, model-visible-byte-preserving.
- Responses-family replay signatures: content-owned opaque-string replay model for
  `thinking_signature`/`text_signature`, including what does and does not survive same-model
  replay.
- The never-raises contract: the exact boundary between ordinary-exception failures (before a
  provider stream is invoked) and in-band terminal-error failures (after), and the
  terminal/fused public stream shape (`non-terminal* -> exactly one terminal -> EOF`).
- The API/provider split as an architectural seam (wire protocol vs. endpoint/auth/model), and the
  general obligation that every Pi-observable model/request option used by an implemented API has
  an equivalent configuration/plugin-registration path.
- Authentication as a seam: credential source/login/store composition, ownership boundaries around
  externally- vs. Minion-owned refresh state.

### Does not own

- **Target-model message transformation** (`XFORM-###`) — frozen master §4's own distinct
  subsection ("Pi-compatible target-model message transformation," including the
  null-content/image/thinking-compatibility/tool-call-ID/orphan-tool-call/errored-assistant rules),
  already spec'd separately at `spec/target-model-transformation.md`. This is intentionally excised
  from `LLM-###`'s scope, matching the requirement-ID convention's own prefix split
  (`LLM-### = "LLM vocabulary / stream contract"`, `XFORM-### = "target-model transformation"`).
  Certified as its own later layer, not folded into this one.
- **Provider-specific adapter behavior** (`PROV-###`) — the actual `openai-completions`/
  `codex-responses` real-provider adapters (OpenRouter, Ollama, LM Studio, generic
  OpenAI-compatible, OpenAI Codex). Per the frozen master §9 build order this is Phase 5, and per
  the user's explicit 2026-08-23 ruling (see memory `project_assurance_layer_sequencing`), Phase 5
  work does not start until assurance reaches that layer. The `mock` adapter
  (`minion_agent/llm/adapters/mock.py`) is in scope here as the conformance-facing reference
  implementation of the `Adapter` protocol, since it's what canonical scenarios actually exercise.
- Session log serialization of these message types (`SES-###`) — how `AssistantMessage` etc. get
  persisted/reconstructed is session-layer territory even though the vocabulary itself is LLM-owned.
- Tool execution semantics beyond the `ToolCall`/`ToolResultMessage` vocabulary shape (`TOOL-###`)
  — the tool pipeline (prepare_arguments → schema validation → hooks → execute → finalize) is its
  own later layer.
- Agent-loop orchestration of LLM calls (`AGENT-###`) — turn/run lifecycle, decision algebra, and
  queue policies are agent-layer territory even where they consume `ctx.llm`.

### Depends on

Runtime (`01`, `CERTIFIED`) — `ctx.llm` is a service resolved through the plugin runtime's service
seam (RT-004..RT-008), and the mock/real adapters are ordinary plugins.

### Depended on by

Every layer above it: target-model-transformation, session, tools, agent, providers all consume the
LLM vocabulary and stream contract.

### LLM-specific certification note

Unlike Runtime (`MINION-001`, intentional divergence), the LLM seam is **Pi-derived**: frozen master
§4 states the vocabulary "mirrors current Pi semantics first" and the never-raises contract is
explicitly "Pi's stream contract." This layer's normative authority is therefore the frozen design
*plus* the adopted Pi baseline/pinned source, not a Minion-only architecture the way Runtime was.
`PI_PARITY_DEFECT` and `PI_BEHAVIOR_UNCERTAIN` findings are live possibilities here in a way they
structurally were not for Runtime (per Runtime's own §3, "Pi has no equivalent plugin/fiber/service
runtime kernel" — that exemption does not apply to this layer).

---

## 2. Normative sources

- Frozen design: `design/2026-08-20-minion-agent-design.md` §4, "The LLM seam (`ctx.llm`)" —
  specifically the "Vocabulary," "Responses-family replay signatures," "The never-raises contract,"
  "API and provider split," "Model and request options," and "Authentication" subsections. Excludes
  the "Pi-compatible target-model message transformation" subsection (XFORM's territory).
- Spec: `spec/llm.md` — exists, 41 lines, condensed normative prose already covering most of the
  above. Not yet audited for completeness/accuracy against the master or the real implementation
  this pass.
- `/pi-parity-manifest.yaml`: all 19 `AI-###` rows are `phase: 2`, disposition `adopted`. `AI-001`
  through `AI-012` map to this layer's vocabulary/never-raises-contract scope (pinned Pi source
  `packages/ai/src/types.ts` and `packages/ai/src/utils/diagnostics.ts`): `AI-001` TextContent,
  `AI-002` ThinkingContent, `AI-003` ToolCall, `AI-004` UserMessage, `AI-005` AssistantMessage,
  `AI-006` ToolResultMessage, `AI-007` Usage, `AI-008` StopReason, `AI-009` DeferredHandle, `AI-010`
  AssistantMessageDiagnostic, `AI-011` Context, `AI-012` StreamFunction (never-raises contract).
  `AI-020` through `AI-026` are target-model transform (`transform-messages.ts`) — correctly out of
  this layer's scope. **Gap noted:** no manifest row yet exists for Responses-family replay
  signatures, the API/provider split, model/request options, or authentication — those four master
  §4 subsections have no `AI-###` parity-manifest coverage at all, not even a deferred/divergent
  disposition. Each `AI-001..012` row also names expected test IDs (e.g.
  `public-llm-vocabulary-schema`, `content-signatures-round-trip`, `null-content-normalizes-empty`,
  `represented-provider-error-rides-stream`, `premature-eof-synthesizes-error-terminal`,
  `public-stream-fuses-after-first-terminal`) — concrete search terms for the conformance survey in
  §4, not yet cross-checked against actual scenario/test names.
- Canonical conformance: **no dedicated `conformance/llm/` directory exists.** LLM-relevant
  scenarios appear to live inside `conformance/agent/` (e.g. `cross-model-signatures-stripped.yaml`,
  `aborted-assistant-excluded-from-replay.yaml`, `errored-assistant-excluded-from-replay.yaml` by
  name), likely because the agent-level conformance runner is what exercises the LLM seam
  end-to-end via the mock adapter. Whether these scenarios' names indicate XFORM content (excluded
  from this layer) versus genuine LLM-### content (never-raises contract, replay signatures) needs a
  full survey before the requirement traceability table can be trusted — not yet done. No
  `conformance/schema/llm-scenario.schema.json` exists either; scenarios in this space likely use
  `agent-scenario.schema.json` or the generic `scenario.schema.json`.
- Pinned Pi source: not yet identified/confirmed this pass — needed before any `PI_PARITY_DEFECT`
  or `PI_BEHAVIOR_UNCERTAIN` finding can be responsibly raised (per the Runtime-layer precedent of
  never asserting Pi behavior from memory or generic best practice).
- Requirement-ID convention: `process/requirement-id-convention.md`, prefix `LLM-###` (`ADOPTED`).

---

## 3. Pi behavior summary

Read in full: `ref-repos/pi/packages/ai/src/types.ts` (857 lines, pinned commit `b7bb00b9`,
2026-08-19) and `.../utils/diagnostics.ts`. Findings against the frozen master's own paraphrase:

- **`Api`/`ProviderId` are open string unions** (`KnownApi | (string & {})`), not closed enums — Pi
  already ships 10 known APIs (`openai-completions`, `mistral-conversations`, `openai-responses`,
  `azure-openai-responses`, `openai-codex-responses`, `anthropic-messages`, `bedrock-converse-stream`,
  `google-generative-ai`, `google-vertex`, `pi-messages`) and dozens of known providers. The master's
  build-order table (`openai-completions`/`codex-responses`/`mock`) is explicitly "build order, not
  the limit of the vocabulary" — matches; the vocabulary's `api`/`provider` fields must stay open
  strings, never a closed enum, in any implementation.
- **`ProviderRequestOptions`/`StreamOptions`/`SimpleStreamOptions` match the master's schema field-
  for-field** (modulo camelCase-vs-snake_case): `timeoutMs`, `maxRetries`, `maxRetryDelayMs`,
  `headers`, `env` on the base type (Pi's `signal`/`fetch`/`onPayload`/`onResponse`/
  `telemetryContext`/`apiKey` are correctly excluded from the master's JSON-safe schema as "runtime
  handles, not JSON values" — matches the master's own comment exactly); `temperature`,
  `samplingParams`, `maxTokens`, `transport`, `cacheRetention`, `sessionId`,
  `websocketConnectTimeoutMs`, `metadata` on `StreamOptions`; `toolChoice`, `reasoning`, `deferred`,
  `thinkingBudgets` on `SimpleStreamOptions`. No discrepancy found. `ThinkingLevel` is
  `"minimal"|"low"|"medium"|"high"|"xhigh"|"max"` (`ModelThinkingLevel` adds `"off"`) — the master's
  vocabulary section never pins these exact enum values; worth noting as underspecified but not a
  parity defect (Pi's own enum is authoritative once someone builds against it).
- **`StopReason`**: Pi = `pending|stop|length|toolUse|error|aborted|deferred` (7 values, camelCase
  `toolUse`) — matches the master's `pending|stop|length|tool_use|error|aborted|deferred` exactly
  once translated to snake_case. No discrepancy.
- **`Usage`**: Pi = `input, output, cacheRead, cacheWrite, cacheWrite1h?, reasoning?, totalTokens,
  cost:{input,output,cacheRead,cacheWrite,total}` — matches the master's schema field-for-field. No
  discrepancy in the *specification*; see §5 for a severe *implementation* gap (Python has no `cost`
  field at all).
- **`AssistantMessage`**: Pi's 15 fields (`role, content, api, provider, model, responseModel?,
  responseId?, diagnostics?, usage, stopReason, deferred?, errorMessage?, rawStopReason?, endTurn?,
  timestamp`) match the master's vocabulary list **exactly**, field-for-field. No discrepancy in the
  spec; see §5 for a severe implementation gap (Python has 7 of 15).
- **`ToolResultMessage`**: Pi's role literal is `"toolResult"` (no snake_case in Pi source itself —
  Minion's own stated policy is that canonical serialization is snake_case regardless of Pi's
  internal casing, so `role = tool_result` in the master is correct translation, not a discrepancy).
  Fields (`toolCallId, toolName, content, details?, usage?, addedToolNames?, isError, timestamp`)
  match the master's list exactly.
- **`TextContent`/`ThinkingContent`/`ToolCall` all carry an explicit `type` discriminant** (`"text"`,
  `"thinking"`, `"toolCall"`) that Pi's own discriminated union relies on to deserialize a mixed
  content array. The master's terse vocabulary sketch (`TextBlock{text,text_signature?}` etc.) does
  not show this tag explicitly, but a discriminant of some form is structurally required for any
  serialized mixed-content array — **not yet confirmed whether Python's implementation carries an
  equivalent tag anywhere** (its `ContentBlock` union relies on Python's own `isinstance`, which has
  no JSON analogue); flagged for the eventual session/conformance-serialization audit, not resolved
  this pass.
- **Discrepancy found in the master's own paraphrase, not a Python implementation issue**: Pi's
  actual stream-event type literals are `toolcall_start`/`toolcall_delta`/`toolcall_end` (no
  underscore between "tool" and "call"), but the frozen master's vocabulary section lists
  `tool_call_start / tool_call_delta / tool_call_end` (with the underscore). This is the master's own
  paraphrase diverging from real Pi source — worth flagging to the design owner as a documentation
  correction opportunity (not something this pass can fix, since the frozen master is user-owned),
  but not itself blocking: Python's stream-chunk dataclasses (`ToolCallStart`/`ToolCallDelta`/
  `ToolCallEnd` in `stream.py`) are Python class names, not wire-serialized type tags, so which
  spelling the eventual wire format uses is still open — noted, not yet resolved.
- **The never-raises contract** (`StreamFunction`'s doc comment): "Once invoked, request/model/
  runtime failures should be encoded in the returned stream, not thrown... Error termination must
  produce an AssistantMessage with stopReason `error`/`aborted` and errorMessage" — matches the
  master's never-raises contract exactly. Confirmed against Python's real implementation in §5: the
  boundary sits correctly at `LlmService.stream()`/`_settled()`, not scattered elsewhere.
- **No pinned Pi source was found this pass for Responses-family replay signatures as a *dedicated*
  module** (no `responses-shared.ts`-style file was read in depth this pass, and none of Python's
  implementation implements signatures at all — see §5 — so tracing the exact Pi replay algorithm
  was deprioritized in favor of confirming the vocabulary gap is real first). **Authentication** does
  have real, extensive pinned Pi source (`ref-repos/pi/packages/ai/src/auth/types.ts`, 240 lines):
  `CredentialStore` with a single serialized `modify()` write path (locked read-modify-write,
  cross-process where the backing store supports it — directly matches the master's "externally
  owned refresh state is not independently mutated... Minion-owned interactive/device login
  credentials may be refreshed and atomically persisted" framing), `ApiKeyAuth`/`OAuthAuth` per-
  provider composition, `AuthPrompt`/`AuthEvent`/`AuthInteraction` for login UX. The master's terse
  "Authentication" prose accurately summarizes the *behavioral rules* (no discrepancy found), just
  not the full type shape — expected, since master documents are intentionally terse. This remains
  entirely unimplemented in Python (no `auth` module exists in `minion_agent/llm/`), which is
  appropriate: authentication only matters once a real (non-mock) provider adapter exists, and that
  is Phase-5, explicitly deferred work per this layer's own scope (§1).

---

## 4. Requirement traceability

| ID | Requirement | Source | Canonical scenario / test | Status |
|---|---|---|---|---|
| LLM-001 | `TextBlock{text, text_signature?}` | Master §4 Vocabulary; Pi `types.ts::TextContent` | none | **GAP** — `content.py.TextBlock` has no `text_signature` field at all (`LLM-F004`) |
| LLM-002 | `ThinkingBlock{thinking, thinking_signature?, redacted=false}` | Master §4; Pi `TextContent`/`ThinkingContent` | none | **GAP** — `content.py.ThinkingBlock` has neither `thinking_signature` nor `redacted` (`LLM-F004`) |
| LLM-003 | `ImageBlock{mime_type, data\|reference}`, content-addressed/immutable, intentional divergence from Pi's inline-base64-only `ImageContent` | Master §4 (explicit divergence); Pi `ImageContent` | none canonical; `content.py.ImageBlock.__post_init__` enforces exactly-one-of | COVERED (by construction) — implemented correctly, matches the documented intentional divergence |
| LLM-004 | `ToolCall{id, name, arguments, thought_signature?, namespace?}` | Master §4; Pi `types.ts::ToolCall` | none | **GAP** — `content.py.ToolCallBlock` has neither `thought_signature` nor `namespace` (`LLM-F004`) |
| LLM-005 | `UserMessage{role=user, content: string\|[TextBlock\|ImageBlock], timestamp}` | Master §4; Pi `UserMessage` | none | **GAP/PARTIAL** — `messages.py.UserMessage.content` is always `tuple[ContentBlock,...]`, no bare-string shorthand path confirmed; not fully verified whether a higher layer normalizes a string into content before construction |
| LLM-006 | `AssistantMessage` full 15-field shape (`api, provider, model, response_model?, response_id?, diagnostics?, usage, stop_reason, deferred?, error_message?, raw_stop_reason?, end_turn?, timestamp`) | Master §4; Pi `types.ts::AssistantMessage` (matches master exactly) | none | **GAP — SEVERE** — `messages.py.AssistantMessage` has only 7 of 15 fields (`content, stop_reason, usage, model, provider, timestamp, error_message`); missing `api, response_model, response_id, diagnostics, deferred, raw_stop_reason, end_turn` (`LLM-F003`) |
| LLM-007 | `ToolResultMessage{role, tool_call_id, tool_name, content, details?, usage?, added_tool_names?, is_error, timestamp}` | Master §4; Pi `types.ts::ToolResultMessage` | none | **GAP** — `messages.py.ToolResultMessage` has only `tool_call_id, content, timestamp, is_error`; missing `tool_name, details, usage, added_tool_names` (`LLM-F005`) |
| LLM-008 | `DeferredHandle{provider, model_id, api, id, expires_at?, poll_after_ms?, data?}` | Master §4; Pi `types.ts::DeferredHandle`; manifest `AI-009` | none | **GAP** — no such type exists anywhere in `minion_agent/llm/` (`LLM-F005`) |
| LLM-009 | `AssistantMessageDiagnostic{type, timestamp, error?, details?}` + `DiagnosticError{message, name?, stack?, code?}` | Master §4; Pi `diagnostics.ts`; manifest `AI-010` | none | **GAP** — neither type exists anywhere in `minion_agent/llm/` (`LLM-F005`) |
| LLM-010 | `LlmContext{system_prompt?, messages, tools?}` | Master §4; Pi `types.ts::Context`; manifest `AI-011` | none | **GAP/PARTIAL** — `service.py.Request` bundles `model, system (required, not optional), messages, max_output_tokens, tools` — a different shape serving a different purpose (a resolved request, not the provider-neutral context type); no standalone `LlmContext` exists |
| LLM-011 | Model identity is the triple `provider + api + model_id` | Master §4; confirmed no Pi source contradiction | none | **GAP** — `service.py.ModelId` is only `(provider, model)`, no `api` field; the identity triple is architecturally unrepresentable in current core types (`LLM-F006`) |
| LLM-012 | `ProviderRequestOptions`/`StreamOptions`/`SimpleStreamOptions` schema exists, every Pi-observable option for an implemented API has a schema-mapped or explicitly-deferred path | Master §4; Pi `types.ts` (confirmed field-for-field match at the spec level, §3) | none | **GAP** — no option schema exists anywhere in `minion_agent/llm/`; `service.py.Request` has only `max_output_tokens`. Appropriately low-urgency: no real (non-mock) API is implemented yet (Phase 5, deferred) |
| LLM-013 | `StopReason = pending\|stop\|length\|tool_use\|error\|aborted\|deferred` | Master §4; Pi `types.ts::StopReason` (exact match) | `public-llm-vocabulary-schema` (placeholder, unfilled) | **GAP** — `messages.py.StopReason` enum is missing `DEFERRED`; only 6 of 7 values (`LLM-F005`) |
| LLM-014 | `Usage{input, output, cache_read, cache_write, cache_write_1h?, reasoning?, total_tokens, cost:{input,output,cache_read,cache_write,total}}` | Master §4; Pi `types.ts::Usage` (exact match) | `public-llm-vocabulary-schema` (placeholder, unfilled) | **GAP — SEVERE** — `messages.py.Usage` has no `cost` sub-object at all, no `cache_write_1h`, and computes `.total` as a property rather than storing `total_tokens` (`LLM-F005`) |
| LLM-015 | Stream chunk/event vocabulary (`start`, `text_start/delta/end`, `thinking_start/delta/end`, `tool_call_start/delta/end`, `done`, `error`), every chunk carries the current partial message | Master §4; Pi `types.ts::AssistantMessageEvent` (see §3 for the `toolcall_start` vs `tool_call_start` master-paraphrase discrepancy) | `premature-eof-synthesizes-error-terminal`, `public-stream-fuses-after-first-terminal` (both real, passing) | COVERED — `stream.py`'s 12 chunk dataclasses all carry `partial`; structurally matches |
| LLM-016 | Image content identity: content-addressed, immutable, model-visible-byte-preserving | Master §4 (folds into LLM-003) | — | Folded into LLM-003 |
| LLM-017 | Responses-family replay signatures: content-owned opaque-string replay model, same-model-signed retains, same-model-unsigned-empty removes, cross-model loses signature | Master §4 "Responses-family replay signatures" | `same-model-thinking-signature-replayed`, `cross-model-signatures-stripped` (both placeholders, unfilled) | **GAP** — unimplementable until LLM-001/002/004's signature fields exist (`LLM-F004`); zero real canonical evidence |
| LLM-018 | The never-raises contract: ordinary exceptions before a stream is invoked, in-band terminal errors after; public stream is `non-terminal* -> exactly one terminal -> EOF`, fused (no draining past the first terminal); premature raw EOF normalizes to an in-band error carrying the accumulated partial | Master §4 "The never-raises contract"; Pi `StreamFunction` doc comment (exact match); manifest `AI-012` | `premature-eof-synthesizes-error-terminal`, `public-stream-fuses-after-first-terminal`, `represented-provider-error-rides-stream`, `premature-eof-preserves-partial-message`, `eager-invalid-model-fails-before-stream` (all real, passing) | COVERED — verified in `service.py._settled()` and `errors.py`; the eager/lazy boundary and fuse-after-terminal behavior are both correctly implemented and both have genuine, executing, passing canonical evidence |
| LLM-019 | The API/provider split as an architectural seam (wire protocol vs. endpoint/auth/model) | Master §4 "API and provider split" | none | **GAP** — same root cause as LLM-011: no `api` field exists on `ModelId`/`Request`, so the split isn't representable yet (`LLM-F006`) |
| LLM-020 | Every Pi-observable model/request option used by an implemented API has an equivalent config/plugin-registration path (omission is a parity decision, not an accident) | Master §4 "Model and request options" | n/a | **N/A pending Phase 5** — no real API is implemented yet, so there is nothing to omit-or-map; revisit once Phase 5 starts |
| LLM-021 | Authentication seam: credential source/login/store composition; external refresh state not independently mutated; Minion-owned credentials may be refreshed/persisted atomically; no implicit fallback chains | Master §4 "Authentication"; Pi `auth/types.ts::CredentialStore` (rules match, see §3) | n/a | **N/A pending Phase 5** — appropriately unimplemented; only matters once a real (non-mock) adapter exists |

**Summary: 21 requirements drafted (LLM-016 folded into LLM-003, so 20 distinct).** 3 COVERED
(LLM-003, LLM-015, LLM-018), 2 appropriately N/A-pending-Phase-5 (LLM-020, LLM-021), 15 GAP — of
which 4 (LLM-006, LLM-008, LLM-009, LLM-014) are severe (entire vocabulary types or most of a type's
fields simply do not exist in the implementation). The never-raises contract (LLM-018, `AI-012`) —
arguably this layer's single highest-stakes behavioral guarantee — is solidly implemented and has
real passing canonical evidence. The rest of the vocabulary (LLM-001/002/004/006/007/008/009/011/
012/013/014/017/019) ranges from partially to almost entirely unimplemented, confirmed by direct
reads of `content.py`/`messages.py`/`service.py`, not inferred from the parity manifest's `(rewrite)`/
`'target: ...'` markers alone (those markers turned out to still be literally true — the rewrite
target was recorded but not yet done).

---

## 5. Implementation inventory

All 8 modules read in full and checked against Pi source (§3) and frozen master §4, not just against
the master's prose in isolation.

| File/module | Responsibility | Decision | Evidence |
|---|---|---|---|
| `content.py` | `TextBlock`/`ThinkingBlock`/`ImageBlock`/`ToolCallBlock` content vocabulary | MODIFY — `ImageBlock` is correct and complete (LLM-003); the other three are missing every replay-signature field the spec/Pi both require | LLM-001, LLM-002, LLM-003, LLM-004 |
| `messages.py` | `StopReason`, `Usage`, `UserMessage`, `AssistantMessage`, `ToolResultMessage` | MODIFY — `StopReason` missing one value; `Usage` missing `cost` entirely; `AssistantMessage`/`ToolResultMessage` missing most of their Pi-required fields | LLM-005, LLM-006, LLM-007, LLM-013, LLM-014 |
| `errors.py` | `LlmError`/`UnknownModelError`/`AdapterProtocolError`, eager/lazy boundary | RETAIN — correctly matches the "raises before a stream, never after" split; docstring states the design-spec section explicitly | LLM-018 |
| `service.py` | `ModelId`, `Request`, `Adapter` protocol, `LlmService`, `_settled()` (the never-raises wrapper) | MODIFY for `ModelId`/`Request` (LLM-011/012/019 gaps); RETAIN for `LlmService.stream()`/`_settled()`, which correctly implements the never-raises contract's premature-EOF-normalization and fuse-after-first-terminal rules — verified against real Pi `StreamFunction` semantics, not just the master's prose | LLM-011, LLM-012, LLM-018, LLM-019 |
| `stream.py` | 12 stream-chunk dataclasses, `collect()` helper | RETAIN — every chunk carries `partial`; `collect()`'s own raise is a defensive-only path for a genuinely broken adapter (the real premature-EOF normalization happens one layer up in `service.py._settled()`, confirmed by reading both together, not assumed) | LLM-015, LLM-018 |
| `tools.py` | `ToolSchema` (model-facing tool definition) | RETAIN, minor note — no `constrained_sampling` field (Pi's `Tool.constrainedSampling`); likely appropriately deferred ("where implemented" per `spec/tools.md`) and arguably `TOOL-###` territory more than `LLM-###` despite living in this package for the stated layering reason (model-facing, no tool-registry import) | out of this layer's primary scope, noted only |
| `plugin.py` | `llm_plugin`/`mock_adapter_plugin` runtime-plugin wiring | RETAIN — correctly mounts through the runtime service seam (RT-004..008); no discrepancy found | — |
| `adapters/mock.py` | `MockAdapter`/`ScriptedResponse`/`_Replay` — the reference `Adapter` implementation conformance scenarios drive | RETAIN — deliberately exercises the contract's edge cases (`truncated`, `chunks_after_terminal`) rather than only the happy path; own docstring states it is "a real adapter, not a test double" and the evidence in LLM-018 confirms that claim | LLM-018 |

**Pattern, not scattered bugs.** Every gap found in §4 traces to the same root: the vocabulary types
were scaffolded with the fields needed for the mock-adapter-driven agent-loop/tool-execution
conformance work already built (Phases 2-4), and never extended to the full Pi-parity shape the
manifest's own `AI-001..012` rows already commit to. The never-raises contract — the part of this
layer that *was* fully built out — is correspondingly solid. This is a coherent, explainable state
(a real implementation gap, confirmed empirically), not a sign of scattered carelessness.

---

## 6. Existing-test audit

Not started.

---

## 7. Missing test / conformance coverage

Derivable from §4 now that it exists, but not separately itemized this pass — the gaps are the same
ones §4/§15 already enumerate per-requirement (`LLM-001..002/004/006..014/017/019`, findings
`LLM-F003..F006`). Revisit as its own checklist once remediation starts, mirroring how Runtime's §7
tracked closure progress across several remediation passes.

---

## 8-14. Failure model / security / reliability / observability / performance / API / documentation

Not started.

---

## 15. Findings

| ID | Severity | Classification | Description | Disposition / action |
|---|---|---|---|---|
| LLM-F001 | MEDIUM | `CONTRACT_ASSURANCE_DEFECT` | Survey complete (63 scenarios in `conformance/agent/`, 21 real/passing, 42 unfilled `TO_BE_...` placeholders). The never-raises contract (LLM-018) has genuine, real, passing canonical evidence commingled in `conformance/agent/` — acceptable, no dedicated family needed for that requirement, mirroring Runtime's non-1:1 precedent. But vocabulary/replay-signature evidence is essentially placeholder-only: `public-llm-vocabulary-schema`, `null-content-normalizes-empty`, `same-model-thinking-signature-replayed`, `cross-model-signatures-stripped` all exist as files but are unfilled `TO_BE_FILLED_FROM_PINNED_PI_BEHAVIOR` scaffolding, not executing evidence. | No dedicated `conformance/llm/` family is needed — `conformance/agent/` is the right home, matching how the seam is actually exercised (end-to-end via the agent loop and mock adapter, no standalone LLM-only runner exists or is needed). Remaining work is filling the 4 named placeholder scenarios once the vocabulary gaps (`LLM-F003`..`F006`) are closed enough to make them meaningful — filling them before the fields exist would just re-encode the same gap as an expected-failure scenario. |
| LLM-F002 | MEDIUM | `CONTRACT_ASSURANCE_DEFECT` | `/pi-parity-manifest.yaml` has zero `AI-###` rows for four of frozen master §4's LLM-owned subsections: Responses-family replay signatures, the API/provider split, model/request options, and authentication. Only vocabulary and the never-raises contract (`AI-001..012`) have parity-manifest coverage. | Pi source exists for Responses-family replay signatures (implied by the vocabulary fields, not independently traced this pass) and authentication (`auth/types.ts`, confirmed §3); model/request options and API/provider split are architectural framing rather than a single Pi symbol. Add manifest rows once the vocabulary gaps below are closed enough that a row would describe real, not aspirational, behavior. |
| LLM-F003 | HIGH | `PI_PARITY_DEFECT` | `AssistantMessage` — the vocabulary type carrying Pi-visible response identity/state for provider replay — has only 7 of the 15 fields Pi's `types.ts::AssistantMessage` and the frozen master both require (confirmed field-for-field match between Pi and master in §3, so this is not a spec ambiguity): missing `api, response_model, response_id, diagnostics, deferred, raw_stop_reason, end_turn`. A message currently cannot record which API served it, carry diagnostics, represent a deferred/async response, or preserve the model's raw stop reason. | Extend `messages.py.AssistantMessage` with the 7 missing fields (LLM-006). Blocks: deferred-execution support, diagnostic reporting, and any provider that needs `api`/`response_model`/`response_id` for replay (i.e., most of Phase 5). Not urgent for the mock-only present, but real work, not deferred risk debt per this project's taxonomy rule (`CONTRACT_ASSURANCE_DEFECT`/`PI_PARITY_DEFECT` must be repaired before certification, not risk-registered). |
| LLM-F004 | HIGH | `PI_PARITY_DEFECT` | None of the three replay-signature fields exist anywhere in the content-block vocabulary: `TextBlock.text_signature`, `ThinkingBlock.thinking_signature`/`redacted`, `ToolCallBlock.thought_signature`/`namespace` are all absent from `content.py`. This makes the entire "Responses-family replay signatures" contract (LLM-017) structurally unrepresentable — there is nowhere to put the data even if the logic existed. Confirmed the two related canonical scenarios (`same-model-thinking-signature-replayed`, `cross-model-signatures-stripped`) are both unfilled placeholders, consistent with there being nothing yet to test. | Add the three signature fields to `content.py`'s dataclasses (LLM-001, LLM-002, LLM-004) before any Responses-family replay logic or its conformance evidence can be built. This is upstream of `LLM-F001`'s remaining placeholder-filling work for those two scenarios. |
| LLM-F005 | MEDIUM | `PI_PARITY_DEFECT` | Grouped vocabulary gaps, each confirmed against Pi source: (1) `Usage.cost` sub-object (`input/output/cache_read/cache_write/total`) does not exist at all in `messages.py.Usage`, and `cache_write_1h` is also missing; (2) `StopReason` enum is missing `DEFERRED` (6 of 7 Pi-required values); (3) `ToolResultMessage` is missing `tool_name, details, usage, added_tool_names` (4 of 8 Pi-required fields); (4) `DeferredHandle` and `AssistantMessageDiagnostic`/`DiagnosticError` do not exist as types anywhere in `minion_agent/llm/`. | Extend `messages.py` with the missing `Usage` fields and `StopReason.DEFERRED`; extend `ToolResultMessage`; add `DeferredHandle`/`AssistantMessageDiagnostic`/`DiagnosticError` dataclasses (LLM-007, LLM-008, LLM-009, LLM-013, LLM-014). Cost accounting in particular blocks any real usage/billing telemetry. |
| LLM-F006 | MEDIUM | `PI_PARITY_DEFECT` | Model identity is architecturally a `(provider, model)` pair (`service.py.ModelId`), not the `provider + api + model_id` triple the master states is "the identity used by target-model compatibility checks." There is no `api` field anywhere in `ModelId` or `Request` — the gap isn't that the field is unpopulated, it's that the type has no place to put it. This also means the API/provider architectural split (LLM-019) isn't representable: nothing distinguishes "which wire protocol" from "which model," since only one of the two axes (`model`) exists in the core type. | Add an `api` field to `ModelId` (and thread it through `Request`, `AssistantMessage` once `LLM-F003` is fixed, and adapter registration in `service.py.LlmService.register()`). This is foundational — every real (non-mock) provider adapter in Phase 5 needs it, so it should land before or alongside the first real adapter, not after. |

---

## 16. Certification gate

```text
Design alignment                         [ ]  not yet traced
Pi parity                                [ ]  not yet audited — Pi-derived layer, unlike Runtime
Normative spec                           [~]  spec/llm.md exists, not yet audited for completeness
Parity manifest                          [ ]  AI-001..012 cover vocabulary/stream contract; LLM-F002 — 4 subsections uncovered
Canonical conformance                    [ ]  LLM-018 real+passing; rest of vocabulary is placeholder-only (LLM-F001)
Python tests where implemented           [ ]  not audited (§6 not started)
Rust tests where implemented             [ ]  not audited
Property/invariant tests                 [ ]  not audited
Concurrency tests where applicable       [ ]  not audited
Fault-injection tests where applicable   [ ]  not audited
Security review                          [ ]  not started
Reliability review                       [ ]  not started
Observability review                     [ ]  not started
Performance review                       [ ]  not started
Public API review                        [ ]  not started
Documentation                            [ ]  not started
All findings classified                  [x]  LLM-F001..F006 classified
No unresolved Pi uncertainty             [x]  none raised this pass — every ambiguity resolved by reading Pi source directly
No unresolved parity defect              [ ]  LLM-F003, F004, F005, F006 open (HIGH x2, MEDIUM x2)
No unresolved contract-assurance defect  [ ]  LLM-F001, LLM-F002 open
Deferred risks recorded                  [x]  LLM-020, LLM-021 explicitly N/A pending Phase 5
```

## 17. Certification result

**Result:** `NOT YET ELIGIBLE`

Steps 0-2 are complete with real grounding: pinned Pi source (`ref-repos/pi/packages/ai/src/`) was
read directly, not inferred from the frozen master's paraphrase — one master-paraphrase discrepancy
was found in passing (`toolcall_start` vs `tool_call_start`, §3) and flagged for the design owner
rather than silently corrected. All 20 distinct `LLM-###` requirements are drafted (§4) and all 8
Python modules are deep-audited (§5). The result: this layer's single highest-stakes guarantee, the
never-raises contract (LLM-018), is solidly implemented with genuine passing canonical evidence. The
rest of the vocabulary is substantially incomplete — `AssistantMessage` has 7 of 15 required fields,
`Usage` has no cost accounting at all, `DeferredHandle`/`AssistantMessageDiagnostic` don't exist,
model identity can't represent the required `provider+api+model_id` triple, and every replay-
signature field is absent. Four new `PI_PARITY_DEFECT` findings record this (`LLM-F003`..`F006`,
2 HIGH + 2 MEDIUM) — confirmed against real Pi source and the master's own vocabulary section, which
agree with each other exactly, so this is a genuine implementation gap, not a spec ambiguity.

This is not remediation work done yet — per the same sequencing Runtime followed (survey and
traceability first, fix second, as its own deliberate pass), none of `LLM-F003`..`F006` were fixed
this pass. §6 (existing-test audit) and §8-14 remain entirely unstarted.

**Follow-up dependencies:**

1. Remediate `LLM-F004` first (replay-signature fields) — it's the smallest, most isolated fix and
   unblocks `LLM-F001`'s remaining placeholder scenarios.
2. Remediate `LLM-F003` (`AssistantMessage`), `LLM-F005` (`Usage.cost`/`StopReason`/
   `ToolResultMessage`/`DeferredHandle`/`Diagnostics`), and `LLM-F006` (model identity triple) —
   likely one pass each, mirroring how Runtime's RT-F0xx fixes were sized.
3. Fill the 4 placeholder canonical scenarios once their underlying vocabulary exists, closing
   `LLM-F001`.
4. Resolve `LLM-F002` (parity-manifest rows) once the vocabulary work above makes the rows describe
   real behavior rather than aspiration.
5. Deep-audit `minion_agent/llm/`'s existing tests (§6).
6. Complete §8-14 review.
7. Independent Rust cross-check, once Python's evidence is stable — same sequence Runtime followed.
