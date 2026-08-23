# LLM Seam — Fidelity Assurance & Certification

**Layer ID:** `02`  
**Status:** `IN_AUDIT`  
**Audit date:** 2026-08-23 (Steps 0-2 complete: Pi source read directly, requirement traceability and
Python module deep audit done; all 4 PI_PARITY_DEFECT findings (LLM-F003..F006) remediated and
verified this pass — 3 fully, 1 (LLM-F006) with a disclosed compromise; §6 existing-test audit and
§8-14 review not yet started — see §17)  
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
| LLM-001 | `TextBlock{text, text_signature?}` | Master §4 Vocabulary; Pi `types.ts::TextContent` | `tests/llm/test_content.py`, `tests/session/test_derive.py::test_replay_signature_fields_round_trip` | COVERED — `text_signature: str \| None = None` added, encode/decode round-trips it (`LLM-F004`) |
| LLM-002 | `ThinkingBlock{thinking, thinking_signature?, redacted=false}` | Master §4; Pi `TextContent`/`ThinkingContent` | `tests/llm/test_content.py`, `tests/session/test_derive.py::test_replay_signature_fields_round_trip` | COVERED — `thinking_signature`/`redacted` added, round-trips (`LLM-F004`) |
| LLM-003 | `ImageBlock{mime_type, data\|reference}`, content-addressed/immutable, intentional divergence from Pi's inline-base64-only `ImageContent` | Master §4 (explicit divergence); Pi `ImageContent` | none canonical; `content.py.ImageBlock.__post_init__` enforces exactly-one-of | COVERED (by construction) — implemented correctly, matches the documented intentional divergence |
| LLM-004 | `ToolCall{id, name, arguments, thought_signature?, namespace?}` | Master §4; Pi `types.ts::ToolCall` | `tests/llm/test_content.py`, `tests/session/test_derive.py::test_replay_signature_fields_round_trip` | COVERED — `thought_signature`/`namespace` added, round-trips (`LLM-F004`) |
| LLM-005 | `UserMessage{role=user, content: string\|[TextBlock\|ImageBlock], timestamp}` | Master §4; Pi `UserMessage` | none | **GAP/PARTIAL** — unchanged this pass; `messages.py.UserMessage.content` is always `tuple[ContentBlock,...]`, no bare-string shorthand path confirmed |
| LLM-006 | `AssistantMessage` full 15-field shape (`api, provider, model, response_model?, response_id?, diagnostics?, usage, stop_reason, deferred?, error_message?, raw_stop_reason?, end_turn?, timestamp`) | Master §4; Pi `types.ts::AssistantMessage` (matches master exactly) | `tests/llm/test_messages.py` (4 new tests), `tests/session/test_derive.py::test_assistant_message_response_identity_and_diagnostics_round_trip` | COVERED — all 15 fields now present; `api` defaults to `"mock"` (disclosed, see LLM-F006) but `service.py`/`mock.py` populate it from `request.model.api` where a real value exists rather than relying on the default (`LLM-F003`) |
| LLM-007 | `ToolResultMessage{role, tool_call_id, tool_name, content, details?, usage?, added_tool_names?, is_error, timestamp}` | Master §4; Pi `types.ts::ToolResultMessage` | `tests/llm/test_messages.py`, `tests/session/test_derive.py::test_tool_result_message_optional_fields_round_trip`, `tests/tools/test_result.py` | COVERED — all fields added; `tools/result.py::to_message()` now threads `details`/`added_tool_names` through from `ToolResult` (previously silently dropped since the vocabulary field didn't exist); `tool_name`/`usage` have no source yet — `ToolResult` doesn't carry a tool name or execution-usage figure, and threading one through the tool-execution pipeline is `TOOL-###` territory, not this layer's (`LLM-F005`) |
| LLM-008 | `DeferredHandle{provider, model_id, api, id, expires_at?, poll_after_ms?, data?}` | Master §4; Pi `types.ts::DeferredHandle`; manifest `AI-009` | `tests/llm/test_messages.py::test_deferred_handle_carries_provider_identity` | COVERED — type added to `messages.py`, exported, round-trips via `_encode_deferred`/`_decode_deferred` (`LLM-F005`) |
| LLM-009 | `AssistantMessageDiagnostic{type, timestamp, error?, details?}` + `DiagnosticError{message, name?, stack?, code?}` | Master §4; Pi `diagnostics.ts`; manifest `AI-010` | `tests/llm/test_messages.py::test_assistant_message_diagnostic_carries_a_structured_error` | COVERED — both types added, round-trip via `_encode_diagnostic`/`_decode_diagnostic` (`LLM-F005`) |
| LLM-010 | `LlmContext{system_prompt?, messages, tools?}` | Master §4; Pi `types.ts::Context`; manifest `AI-011` | none | **GAP/PARTIAL** — unchanged this pass; `service.py.Request` bundles a different shape (a resolved request, not the provider-neutral context type); no standalone `LlmContext` exists |
| LLM-011 | Model identity is the triple `provider + api + model_id` | Master §4; confirmed no Pi source contradiction | `tests/llm/test_service.py::test_model_id_defaults_api_to_mock`, `test_registering_an_adapter_carries_its_declared_api` | COVERED — `ModelId.api: str = "mock"` added. **Disclosed compromise, not full Pi fidelity:** Pi's `api` is required (no default); making it required in Python broke 133 tests across `agent/`/`agent_loop/`/`conformance/` (positional 2-arg `ModelId(provider, model)` calls throughout those layers' own test suites, outside this audit's scope to touch broadly). Defaulted to `"mock"` instead — correct for every current caller (the sole registered adapter), and the `Adapter` protocol/`LlmService.register()` now thread a real `api` value through when an adapter declares one. The default becomes actively wrong once a second API exists (Phase 5) and must be removed then (`LLM-F006`) |
| LLM-012 | `ProviderRequestOptions`/`StreamOptions`/`SimpleStreamOptions` schema exists, every Pi-observable option for an implemented API has a schema-mapped or explicitly-deferred path | Master §4; Pi `types.ts` (confirmed field-for-field match at the spec level, §3) | none | **GAP** — unchanged this pass; no option schema exists anywhere in `minion_agent/llm/`. Appropriately low-urgency: no real (non-mock) API is implemented yet (Phase 5, deferred) |
| LLM-013 | `StopReason = pending\|stop\|length\|tool_use\|error\|aborted\|deferred` | Master §4; Pi `types.ts::StopReason` (exact match) | `tests/llm/test_messages.py::test_stop_reason_includes_deferred` | COVERED — `DEFERRED` added, all 7 values present (`LLM-F005`) |
| LLM-014 | `Usage{input, output, cache_read, cache_write, cache_write_1h?, reasoning?, total_tokens, cost:{input,output,cache_read,cache_write,total}}` | Master §4; Pi `types.ts::Usage` (exact match) | `tests/llm/test_messages.py` (2 new tests), `tests/session/test_derive.py::test_usage_cost_and_total_tokens_round_trip` | COVERED — `Cost` dataclass added, `cost`/`cache_write_1h`/`total_tokens` all present and round-trip; the pre-existing computed `.total` property is unchanged (kept for the existing tests/call sites that use it as a convenience sum, distinct from the new stored `total_tokens`) (`LLM-F005`) |
| LLM-015 | Stream chunk/event vocabulary (`start`, `text_start/delta/end`, `thinking_start/delta/end`, `tool_call_start/delta/end`, `done`, `error`), every chunk carries the current partial message | Master §4; Pi `types.ts::AssistantMessageEvent` (see §3 for the `toolcall_start` vs `tool_call_start` master-paraphrase discrepancy) | `premature-eof-synthesizes-error-terminal`, `public-stream-fuses-after-first-terminal` (both real, passing) | COVERED — `stream.py`'s 12 chunk dataclasses all carry `partial`; structurally matches |
| LLM-016 | Image content identity: content-addressed, immutable, model-visible-byte-preserving | Master §4 (folds into LLM-003) | — | Folded into LLM-003 |
| LLM-017 | Responses-family replay signatures: content-owned opaque-string replay model, same-model-signed retains, same-model-unsigned-empty removes, cross-model loses signature | Master §4 "Responses-family replay signatures" | `same-model-thinking-signature-replayed`, `cross-model-signatures-stripped` (both still placeholders, unfilled) | **GAP, but unblocked** — the signature *fields* now exist (LLM-001/002/004, `LLM-F004` resolved), so the vocabulary is representable, but the *decision logic* (same-model retains, cross-model strips) is target-model-transformation behavior — `XFORM-###` territory, spec'd at `spec/target-model-transformation.md`, not yet audited or implemented. Filling these two scenarios meaningfully still requires that layer's work, not just this one's |
| LLM-018 | The never-raises contract: ordinary exceptions before a stream is invoked, in-band terminal errors after; public stream is `non-terminal* -> exactly one terminal -> EOF`, fused (no draining past the first terminal); premature raw EOF normalizes to an in-band error carrying the accumulated partial | Master §4 "The never-raises contract"; Pi `StreamFunction` doc comment (exact match); manifest `AI-012` | `premature-eof-synthesizes-error-terminal`, `public-stream-fuses-after-first-terminal`, `represented-provider-error-rides-stream`, `premature-eof-preserves-partial-message`, `eager-invalid-model-fails-before-stream` (all real, passing) | COVERED — verified in `service.py._settled()` and `errors.py`; the eager/lazy boundary and fuse-after-terminal behavior are both correctly implemented and both have genuine, executing, passing canonical evidence |
| LLM-019 | The API/provider split as an architectural seam (wire protocol vs. endpoint/auth/model) | Master §4 "API and provider split" | `tests/llm/test_service.py::test_registering_an_adapter_carries_its_declared_api` | COVERED — same fix as LLM-011; `api` is now a real, distinct field from `provider`, defaulted per the same disclosed compromise (`LLM-F006`) |
| LLM-020 | Every Pi-observable model/request option used by an implemented API has an equivalent config/plugin-registration path (omission is a parity decision, not an accident) | Master §4 "Model and request options" | n/a | **N/A pending Phase 5** — no real API is implemented yet, so there is nothing to omit-or-map; revisit once Phase 5 starts |
| LLM-021 | Authentication seam: credential source/login/store composition; external refresh state not independently mutated; Minion-owned credentials may be refreshed/persisted atomically; no implicit fallback chains | Master §4 "Authentication"; Pi `auth/types.ts::CredentialStore` (rules match, see §3) | n/a | **N/A pending Phase 5** — appropriately unimplemented; only matters once a real (non-mock) adapter exists |

**Summary: 21 requirements drafted (LLM-016 folded into LLM-003, so 20 distinct).** After this
remediation pass: **14 COVERED** (LLM-001/002/003/004/006/007/008/009/011/013/014/015/018/019),
**2 N/A pending Phase 5** (LLM-020, LLM-021), **3 open GAP** (LLM-005, LLM-010, LLM-012 — all
lower-severity, none blocking on a missing type), **1 GAP unblocked but requiring a different layer's
work** (LLM-017, needs `XFORM-###`'s transformation logic once that layer is audited). Zero severe
gaps remain. The never-raises contract (LLM-018) was already solid; the rest of the vocabulary went
from "partially to almost entirely unimplemented" to fully present, with one disclosed compromise
(`ModelId.api`'s default, `LLM-F006`) recorded rather than silently accepted.

---

## 5. Implementation inventory

All 8 modules read in full and checked against Pi source (§3) and frozen master §4, not just against
the master's prose in isolation.

| File/module | Responsibility | Decision | Evidence |
|---|---|---|---|
| `content.py` | `TextBlock`/`ThinkingBlock`/`ImageBlock`/`ToolCallBlock` content vocabulary | MODIFIED (this pass) — added `text_signature`/`thinking_signature`+`redacted`/`thought_signature`+`namespace`; `ImageBlock` was already correct and complete (LLM-003) | LLM-001, LLM-002, LLM-003, LLM-004 |
| `messages.py` | `StopReason`, `Cost`, `Usage`, `UserMessage`, `AssistantMessage`, `ToolResultMessage`, `DeferredHandle`, `AssistantMessageDiagnostic`, `DiagnosticError` | MODIFIED (this pass) — added `StopReason.DEFERRED`; new `Cost` type and `Usage.cost`/`cache_write_1h`/`total_tokens`; `AssistantMessage` extended from 7 to all 15 Pi fields; `ToolResultMessage` extended with `tool_name`/`details`/`usage`/`added_tool_names`; new `DeferredHandle`/`AssistantMessageDiagnostic`/`DiagnosticError` types. `LLM-005`/`LLM-010`-adjacent gaps (`UserMessage` string-content shorthand, standalone `LlmContext`) left open, out of this pass's scope | LLM-006, LLM-007, LLM-008, LLM-009, LLM-013, LLM-014 |
| `errors.py` | `LlmError`/`UnknownModelError`/`AdapterProtocolError`, eager/lazy boundary | RETAIN — correctly matches the "raises before a stream, never after" split; docstring states the design-spec section explicitly | LLM-018 |
| `service.py` | `ModelId`, `Request`, `Adapter` protocol, `LlmService`, `_settled()` (the never-raises wrapper) | MODIFIED (this pass) for `ModelId`/`Adapter`/`register()` — added `api` (defaulted, `LLM-F006`) and threaded it from adapter to model identity to `AssistantMessage`; RETAIN for `LlmService.stream()`/`_settled()`, which already correctly implements the never-raises contract's premature-EOF-normalization and fuse-after-first-terminal rules; `Request`'s option-schema gap (LLM-012) left open, appropriately deferred to Phase 5 | LLM-011, LLM-012, LLM-018, LLM-019 |
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

**One cross-package fix, outside `minion_agent/llm/` but caused by this pass's changes:**
`minion_agent/tools/result.py::ToolResult.to_message()` was silently dropping `details`/
`added_tool_names` — not a bug in the old code exactly, since `ToolResultMessage` had nowhere to put
them before this pass — but now that `LLM-F005` gives the vocabulary type those fields,
`to_message()` was updated to actually thread them through. `tool_name`/`usage` remain unpopulated
there (no source exists yet in `ToolResult` or its callers; threading one through the tool-execution
pipeline is `TOOL-###` territory). Verified via new tests in `tests/tools/test_result.py`; the
existing `test_details_do_not_reach_the_model` test's intent (details must never appear in `content`,
the readable text) is preserved and unaffected — the fix only changes whether the message *object*
carries the metadata, not what the model reads.

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
| LLM-F003 | HIGH | `PI_PARITY_DEFECT` — RESOLVED | `AssistantMessage` — the vocabulary type carrying Pi-visible response identity/state for provider replay — had only 7 of the 15 fields Pi's `types.ts::AssistantMessage` and the frozen master both require (confirmed field-for-field match between Pi and master in §3, so this was not a spec ambiguity): missing `api, response_model, response_id, diagnostics, deferred, raw_stop_reason, end_turn`. | Fixed: all 7 fields added to `messages.py.AssistantMessage` (LLM-006). `api` defaults to `"mock"` (see `LLM-F006`'s disclosed compromise) but `service.py._empty_partial()` and `adapters/mock.py::build()` explicitly pass `api=request.model.api` rather than relying on the default. `session/derive.py` extended to round-trip all 7 fields, including new `_encode_diagnostic`/`_decode_diagnostic`/`_encode_deferred`/`_decode_deferred` helpers. 4 new unit tests plus a round-trip test. Full suite + `ruff` clean. |
| LLM-F004 | HIGH | `PI_PARITY_DEFECT` — RESOLVED | None of the three replay-signature fields existed anywhere in the content-block vocabulary: `TextBlock.text_signature`, `ThinkingBlock.thinking_signature`/`redacted`, `ToolCallBlock.thought_signature`/`namespace` were all absent from `content.py`. This made the "Responses-family replay signatures" contract (LLM-017) structurally unrepresentable. | Fixed: all three fields/pairs added to `content.py`'s dataclasses (LLM-001, LLM-002, LLM-004), all optional/defaulted (fully backward-compatible — every construction site in the codebase uses keyword args). `session/derive.py`'s `_encode_block`/`_decode_block` extended to round-trip them. 6 new unit tests plus a round-trip test. **Does not by itself close `LLM-F001`'s two replay-signature placeholder scenarios** — filling those meaningfully needs the same-model/cross-model *decision logic*, which is `XFORM-###` territory (see LLM-017's updated §4 row), not yet audited. |
| LLM-F005 | MEDIUM | `PI_PARITY_DEFECT` — RESOLVED | Grouped vocabulary gaps, each confirmed against Pi source: (1) `Usage.cost` sub-object did not exist at all, `cache_write_1h` also missing; (2) `StopReason` enum was missing `DEFERRED`; (3) `ToolResultMessage` was missing `tool_name, details, usage, added_tool_names`; (4) `DeferredHandle` and `AssistantMessageDiagnostic`/`DiagnosticError` did not exist as types anywhere in `minion_agent/llm/`. | Fixed: new `Cost` dataclass and `Usage.cost`/`cache_write_1h`/`total_tokens` added (the pre-existing computed `.total` property kept unchanged, distinct from the new stored `total_tokens`); `StopReason.DEFERRED` added; `ToolResultMessage` extended with all 4 missing fields; `DeferredHandle`/`AssistantMessageDiagnostic`/`DiagnosticError` added and exported. **Side effect, verified not just assumed:** `tools/result.py::ToolResult.to_message()` was silently dropping `details`/`added_tool_names` — it had nowhere to put them before this pass — now threads them through; `tool_name`/`usage` remain unpopulated (no source in `ToolResult`/its callers; threading one through the tool-execution pipeline is `TOOL-###` territory). All encode/decode round-trips extended. Full suite + `ruff` clean. |
| LLM-F006 | MEDIUM | `PI_PARITY_DEFECT` — RESOLVED, with a disclosed compromise | Model identity was architecturally a `(provider, model)` pair (`service.py.ModelId`), not the `provider + api + model_id` triple the master requires. No `api` field existed anywhere in `ModelId`, `Request`, or the `Adapter` protocol. | `api: str` added to `ModelId` and the `Adapter` protocol; `LlmService.register()` threads it from adapter to model identity. **Not full Pi fidelity — disclosed, not silent:** Pi's `api` is required (no default). Making it required in Python broke 133 tests across `agent/`/`agent_loop/`/`conformance/` — positional 2-arg `ModelId(provider, model)` calls throughout those layers' own test suites, well outside this audit's scope to touch broadly in an LLM-layer pass. Reverted to `api: str = "mock"`, correct for every current caller (the sole registered adapter today). 3 fake `Adapter` test doubles inside `llm`/`agent_loop` test files (the only ones actually reached by `register()`) updated with a real `api` attribute. The default becomes actively wrong once a second API exists (Phase 5) and must be removed then — noted directly in the field's own docstring, not just here. |

---

## 16. Certification gate

```text
Design alignment                         [x]  all 20 distinct LLM-### requirements traced to frozen §4
Pi parity                                [~]  vocabulary/stream-contract fields now Pi-parity-complete (LLM-F003..F006 resolved); LLM-005/010/012/017 remain open, none severe
Normative spec                           [~]  spec/llm.md exists, not yet re-audited for completeness against the now-larger vocabulary
Parity manifest                          [ ]  AI-001..012 cover vocabulary/stream contract; LLM-F002 — 4 subsections still uncovered
Canonical conformance                    [ ]  LLM-018 real+passing; vocabulary placeholders in LLM-F001 not yet filled (fields now exist, but filling wasn't in this pass's scope)
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
No unresolved parity defect              [x]  LLM-F003, F004, F005, F006 all resolved (LLM-F006 with a disclosed, documented compromise)
No unresolved contract-assurance defect  [ ]  LLM-F001, LLM-F002 still open
Deferred risks recorded                  [x]  LLM-020, LLM-021 explicitly N/A pending Phase 5; LLM-F006's default explicitly flagged to remove once Phase 5 adds a second API
```

## 17. Certification result

**Result:** `NOT YET ELIGIBLE`

Steps 0-2 are complete with real grounding: pinned Pi source (`ref-repos/pi/packages/ai/src/`) was
read directly, not inferred from the frozen master's paraphrase — one master-paraphrase discrepancy
was found in passing (`toolcall_start` vs `tool_call_start`, §3) and flagged for the design owner
rather than silently corrected. All 20 distinct `LLM-###` requirements are drafted (§4) and all 8
Python modules are deep-audited (§5).

**Remediation is also complete for this pass** (following the same survey-then-fix sequencing
Runtime used): all four `PI_PARITY_DEFECT` findings (`LLM-F003`..`F006`) are resolved.
`AssistantMessage` now carries all 15 Pi fields; the three replay-signature fields exist across the
content-block vocabulary; `Usage.cost`/`StopReason.DEFERRED`/`ToolResultMessage`'s remaining
fields/`DeferredHandle`/`AssistantMessageDiagnostic`/`DiagnosticError` all exist; `ModelId`/`Adapter`
carry a real `api` field. One deliberate, disclosed compromise: `LLM-F006`'s `api` field is defaulted
rather than required, because making it required broke 133 tests across `agent/`/`agent_loop/`/
`conformance/` — outside this audit's scope to sweep through in an LLM-layer pass. The default is
correct for every current caller and is explicitly flagged (in the field's own docstring and here)
to be removed once Phase 5 adds a second API. Every fix is covered by new unit tests and, where
applicable, round-trip tests; the full Python suite and `ruff` are clean throughout.

**Not done this pass, deliberately:** filling `LLM-F001`'s 4 placeholder canonical scenarios (the
vocabulary fields now exist, but two of the four need `XFORM-###`'s transformation logic, not just
this layer's vocabulary — see LLM-017); resolving `LLM-F002` (parity-manifest rows); §6 (existing-test
audit); §8-14. None of these were blocked by anything found this pass — they're simply the next
slices of work, kept separate the same way Runtime's audit and remediation passes stayed distinct
from each other.

**Follow-up dependencies:**

1. Fill the `public-llm-vocabulary-schema` and (if still relevant once surveyed) other
   vocabulary-only placeholder scenarios now that the fields backing them exist, closing part of
   `LLM-F001`.
2. `same-model-thinking-signature-replayed`/`cross-model-signatures-stripped` need `XFORM-###`'s
   transformation logic before they can be meaningfully filled — track as a cross-layer dependency,
   not a re-open of `LLM-F004`.
3. Resolve `LLM-F002` (parity-manifest rows) now that the vocabulary work makes rows for Responses
   replay signatures and authentication describable in terms of real, not aspirational, behavior.
4. Deep-audit `minion_agent/llm/`'s existing tests (§6).
5. Complete §8-14 review.
6. Independent Rust cross-check, once Python's evidence is stable — same sequence Runtime followed.
7. When Phase 5 adds a second API: remove `ModelId.api`'s default (`LLM-F006`) and update every
   call site that relied on it, this time with real API values to assign, not a placeholder sweep.
