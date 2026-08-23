# LLM Seam — Fidelity Assurance & Certification

**Layer ID:** `02`  
**Status:** `IN_AUDIT`  
**Audit date:** 2026-08-23 (§1-6 and §8-14 complete: Pi source read directly, requirement
traceability, module and existing-test audits, and the full §8-14 review all done; 4 PI_PARITY_DEFECT
findings (LLM-F003..F006) resolved in the prior pass; one more hardening fix (LLM-F007, centralizing
the never-raises guarantee against a misbehaving adapter) made and verified during this pass's own
adversarial review — see §8 and §15 for why this is PARITY_NEUTRAL_HARDENING, not a Pi-parity defect:
Pi's own central dispatcher does not defend against this either. `LLM-F002` partially resolved —
`AI-013` added to the parity manifest for Responses-family replay signatures, with a precise Pi
source distinct from `XFORM-###`'s; the other 3 uncovered subsections deliberately left unresolved
pending Phase 5. Rust handoff package prepared (`02-llm-rust-handoff.md`). `LLM-F010` design/
implementation pass since complete: observability matrix, `agent-scenario.schema.json`/
`agent_runner.py`/`adapters/mock.py` extended, `public-llm-vocabulary-schema.yaml` filled and
passing — implemented and verified, not yet marked resolved pending shared-contract review.
Rust's own independent Layer 02 pass has separately landed (§18) — see §17)  
**Auditor:** Claude (Python-driven, per adopted workflow)  
**Python status:** `IMPLEMENTED`  
**Rust status:** `IMPLEMENTED / READY FOR CROSS-LANGUAGE CERTIFICATION` — typed vocabulary,
strict three-part model identity, adapter/service boundary, central settled `AssistantStream`,
scripted real-trait adapter, Rust tests, and a thin partial agent-family conformance adapter are
implemented on `audit/llm-rust-assurance`; see §18. Overall Layer 02 remains `IN_AUDIT` while the
shared `LLM-F001`/`LLM-F010` vocabulary-conformance blocker is open.

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
| LLM-017 | Responses-family replay signatures: content-owned opaque-string replay model, same-model-signed retains, same-model-unsigned-empty removes, cross-model loses signature | Master §4 "Responses-family replay signatures"; Pi `api/openai-responses-shared.ts` (792 lines — the actual wire-format signature encode/decode: `JSON.parse(block.thinkingSignature)` as a `ResponseReasoningItem`, `encodeTextSignatureV1`); manifest `AI-013` (new, this pass) | `same-model-thinking-signature-replayed`, `cross-model-signatures-stripped` (both still placeholders, unfilled) | **GAP, but unblocked and more precisely scoped than previously recorded.** The signature *fields* now exist (LLM-001/002/004, `LLM-F004` resolved). `AI-013` gives this requirement its own precise Pi source, distinct from target-model-transformation's `transform-messages.ts` — `openai-responses-shared.ts` implements the Responses-API-specific *wire-format encode/decode* mechanism (this layer's own concern), separate from `XFORM-###`'s general cross-model *survives-or-not* filtering rules (`spec/target-model-transformation.md` rules 5-12, which independently also govern thinking/text/tool-call signature survival). **Not yet resolved: which of the two existing placeholder scenarios exercises which mechanism.** Both are still empty `TO_BE_FILLED_FROM_PINNED_PI_BEHAVIOR` scaffolding — their eventual assertions, not just their names, will decide whether `same-model-thinking-signature-replayed`/`cross-model-signatures-stripped` are `LLM-###`'s own evidence (wire-format replay), `XFORM-###`'s (survival filtering), or need one scenario per layer. Recorded as a joint decision for whoever fills them, not resolved unilaterally here — see `LLM-F002` |
| LLM-018 | The never-raises contract: ordinary exceptions before a stream is invoked, in-band terminal errors after; public stream is `non-terminal* -> exactly one terminal -> EOF`, fused (no draining past the first terminal); premature raw EOF normalizes to an in-band error carrying the accumulated partial | Master §4 "The never-raises contract"; Pi `StreamFunction` doc comment (exact match); manifest `AI-012` | `premature-eof-synthesizes-error-terminal`, `public-stream-fuses-after-first-terminal`, `represented-provider-error-rides-stream`, `premature-eof-preserves-partial-message`, `eager-invalid-model-fails-before-stream` (all real, passing) | COVERED — verified in `service.py._settled()` and `errors.py`; the eager/lazy boundary and fuse-after-terminal behavior are both correctly implemented and both have genuine, executing, passing canonical evidence |
| LLM-019 | The API/provider split as an architectural seam (wire protocol vs. endpoint/auth/model) | Master §4 "API and provider split" | `tests/llm/test_service.py::test_registering_an_adapter_carries_its_declared_api` | COVERED — same fix as LLM-011; `api` is now a real, distinct field from `provider`, defaulted per the same disclosed compromise (`LLM-F006`) |
| LLM-020 | Every Pi-observable model/request option used by an implemented API has an equivalent config/plugin-registration path (omission is a parity decision, not an accident) | Master §4 "Model and request options" | n/a | **N/A pending Phase 5** — no real API is implemented yet, so there is nothing to omit-or-map; revisit once Phase 5 starts |
| LLM-021 | Authentication seam: credential source/login/store composition; external refresh state not independently mutated; Minion-owned credentials may be refreshed/persisted atomically; no implicit fallback chains | Master §4 "Authentication"; Pi `auth/types.ts::CredentialStore` (rules match, see §3) | n/a | **N/A pending Phase 5** — appropriately unimplemented; only matters once a real (non-mock) adapter exists |

**Summary: 21 requirements drafted (LLM-016 folded into LLM-003, so 20 distinct).** After this
remediation pass: **14 COVERED** (LLM-001/002/003/004/006/007/008/009/011/013/014/015/018/019),
**2 N/A pending Phase 5** (LLM-020, LLM-021), **3 open GAP** (LLM-005, LLM-010, LLM-012 — all
lower-severity, none blocking on a missing type), **1 GAP unblocked and now more precisely scoped**
(LLM-017 — has its own Pi source and manifest row, `AI-013`, as of this pass; which of its two
placeholder scenarios belongs to this layer vs. `XFORM-###` is a joint decision not yet made, not a
block on either layer's own work). Zero severe
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

All 7 files in `tests/llm/` plus `tests/session/test_derive.py` (the vocabulary's own encode/decode
round-trip suite, heavily extended in the prior remediation pass) read in full and run individually
to confirm current pass state before classifying:

```text
KEEP                 solid unit-level test, stays as implementation-detail coverage
STRENGTHEN           real gap or weak assertion worth fixing
MOVE TO CONFORMANCE  tests cross-language-relevant behavior that duplicates/should replace a scenario
REWRITE              tests something real but is structured badly (asserts internals, not behavior)
DELETE               redundant with canonical conformance, adds nothing as a unit test
```

| File | Verdict | LLM-* | Reason |
|---|---|---|---|
| `test_content.py` | KEEP | LLM-001, LLM-002, LLM-003, LLM-004 | Every content-block field, including all 3 replay-signature additions from the prior pass, tested with explicit default-and-settable assertions; frozen-ness verified |
| `test_messages.py` | KEEP | LLM-006, LLM-007, LLM-008, LLM-009, LLM-013, LLM-014 | Comprehensive coverage of the prior pass's additions (`AssistantMessage`'s 7 new fields, `Cost`/`Usage.total_tokens`/`cache_write_1h`, `StopReason.DEFERRED`, `ToolResultMessage`'s 4 new fields, `DeferredHandle`, `AssistantMessageDiagnostic`) — none stale, all current with the now-15-field shape |
| `test_mock_adapter.py` | KEEP | LLM-018 | Script ordering, tool-call responses, in-band error/abort, request recording, usage pass-through — all behavioral, none assert internal shape |
| `test_service.py` | KEEP | LLM-011, LLM-018, LLM-019 | Registration/withdrawal/replacement semantics plus the two `ModelId.api` tests added in the prior pass; `test_a_later_adapter_replaces_an_earlier_one_for_the_same_model` directly answers this pass's §10 question about overlapping registration — confirmed intentional, not incidental dict-overwrite behavior (see §10) |
| `test_stream.py` | KEEP | LLM-015, LLM-018 | `collect()`'s settle/error/protocol-violation paths, partial-message propagation |
| `test_stream_boundary.py` | KEEP | LLM-018 | The layer's most rigorous suite: premature EOF, empty stream, double-terminal fusing, well-formed pass-through, represented error, source-not-drained-past-terminal. **Strengthened this pass**: added `test_an_adapter_that_raises_mid_iteration_still_settles_in_band`, the regression test for `LLM-F007` (found and fixed in this pass, see §8) |
| `test_tool_schema.py` | KEEP | — | `ToolSchema`/`Request.tools` shape and canonical-form (order-independent, JSON-safe) hashing; genuinely `TOOL-###`-adjacent vocabulary, correctly living here per `messages.py`'s own layering note (model-facing, no tool-registry import) |
| `tests/session/test_derive.py` | KEEP | LLM-001, LLM-002, LLM-004, LLM-006, LLM-007, LLM-008, LLM-009, LLM-013, LLM-014 | Round-trips every content-block type and the full `AssistantMessage`/`ToolResultMessage`/`Usage` shape through `encode_message`/`decode_message`; this is the vocabulary's own serialization-fidelity evidence, distinct from unit-level field tests |

No file merits `STRENGTHEN` beyond the one already applied, `REWRITE`, `DELETE`, or `MOVE TO
CONFORMANCE`. No stale tests found: every file already reflects the post-remediation shapes (the
concern going in — that a test might still assert the old 7-field `AssistantMessage` or a
`ModelId` with no `api` — did not materialize; the prior pass's own test updates were thorough).

**Out of scope, excluded with reason:** `tests/agent_loop/*.py` and the rest of `tests/session/*.py`
(`test_compaction.py`, `test_fork.py`, `test_properties.py`, `test_reset.py`) and `tests/agent/*.py`
construct LLM messages only incidentally as fixtures for their own layer's semantics (agent-loop turn
lifecycle, session fork/reset/compaction) — their assertions are about those layers, not this one.
`tests/tools/test_result.py` is `TOOL-###`'s own test suite (`ToolResult`, the tool-execution
pipeline's internal type) even though it's cited in §4 as `LLM-007` evidence for the
`details`/`added_tool_names` threading fix — its own audit belongs to the tools layer, not repeated
here.

---

## 7. Missing test / conformance coverage

### `LLM-F010` observability matrix (complete)

Built before any schema/runner change, per every frozen field in `AssistantMessage`, the
content-block vocabulary, `Usage`/`Cost`, `DeferredHandle`, `AssistantMessageDiagnostic`/
`DiagnosticError`, and `StopReason`. "Current DSL path" is what `agent-scenario.schema.json` could
already express before this pass; "current runner path" is what `agent_runner.py` actually read from
or wrote into the outcome dict.

| Field | Status (before) | Current DSL path (before) | Current runner path (before) | Extension required |
|---|---|---|---|---|
| `AssistantMessage.content` | OBSERVABLE NOW | `scriptedResponse.content[]` (`contentBlock`) | `_block()`/`_ROLE`+`text_of()` (text only) | Content-block signature fields, see below |
| `AssistantMessage.api` | NOT OBSERVABLE | none | derived internally, never projected | New `assistantMessageDetail.api` + runner read |
| `AssistantMessage.provider` | NOT OBSERVABLE | none | derived internally, never projected | New `assistantMessageDetail.provider` + runner read |
| `AssistantMessage.model` | NOT OBSERVABLE | none | derived internally, never projected | New `assistantMessageDetail.model` + runner read |
| `AssistantMessage.response_model` | NOT OBSERVABLE | none | `ScriptedResponse` has no such field at all | New `ScriptedResponse.response_model` (production code) + DSL + runner |
| `AssistantMessage.response_id` | NOT OBSERVABLE | none | same as above | New `ScriptedResponse.response_id` + DSL + runner |
| `AssistantMessage.diagnostics` | NOT OBSERVABLE | none | same as above | New `ScriptedResponse.diagnostics` + DSL + runner |
| `AssistantMessage.usage` (all sub-fields) | NOT OBSERVABLE | `scriptedResponse.usage: {type: object}` (untyped, unvalidated) | **declared but never read** — `_script()` never passed `response.get("usage")` into `ScriptedResponse` | Typed `$defs/usage`/`$defs/cost` + `_script()` fix + runner projection |
| `AssistantMessage.stop_reason` | PARTIALLY OBSERVABLE | `stop_reason` enum missing `deferred` | `assistant_stop_reasons` projects the value | Add `deferred` to both enums |
| `AssistantMessage.deferred` | NOT OBSERVABLE | none | `ScriptedResponse` has no such field | New `ScriptedResponse.deferred` + `$defs/deferredHandle` + runner |
| `AssistantMessage.error_message` | OBSERVABLE NOW | `scriptedResponse.error_message` | round-trips already (existing scenarios rely on it) | none |
| `AssistantMessage.raw_stop_reason` | NOT OBSERVABLE | none | `ScriptedResponse` has no such field | New `ScriptedResponse.raw_stop_reason` + DSL + runner |
| `AssistantMessage.end_turn` | NOT OBSERVABLE | none | `ScriptedResponse` has no such field | New `ScriptedResponse.end_turn` + DSL + runner |
| `AssistantMessage.timestamp` | NOT LAYER-02-OWNED | n/a | derived from call count | Not a Pi-observable field a scenario scripts; internal bookkeeping |
| `TextBlock.text`/`ThinkingBlock.thinking`/`ToolCall.{id,name,arguments}` | OBSERVABLE NOW | `contentBlock` | `_block()` (text/tool_call only — **`thinking` type silently fell through to `TextBlock`**, a real pre-existing bug) | Fix `_block()`'s `thinking` branch |
| `TextBlock.text_signature` | NOT OBSERVABLE | none | `_block()` never read it | Add to `contentBlock` + `_block()`/normalizer |
| `ThinkingBlock.thinking_signature`/`redacted` | NOT OBSERVABLE | none | same | Add to `contentBlock` + `_block()`/normalizer |
| `ToolCall.thought_signature`/`namespace` | NOT OBSERVABLE | none | same | Add to `contentBlock` + `_block()`/normalizer |
| `DeferredHandle` (all fields) | NOT OBSERVABLE | none | type didn't exist in the runner's imports | New `$defs/deferredHandle` + runner construct/normalize |
| `AssistantMessageDiagnostic`/`DiagnosticError` (all fields) | NOT OBSERVABLE | none | same | New `$defs/diagnostic`/`diagnosticError` + runner construct/normalize |
| `StopReason.DEFERRED` | NOT OBSERVABLE | absent from both enums | `StopReason(response["stop_reason"])` would accept it once the schema does | Add `"deferred"` to both enums |

Two things the matrix caught that a narrower "just add the missing fields" pass would have missed:
(1) `scriptedResponse.usage` already existed in the schema but was **silently dead** — `_script()`
never read it, so every prior scenario that might have tried to script usage was quietly ignored;
(2) `_block()`'s `thinking`-type branch never actually existed — any scenario scripting
`type: thinking` would have silently gotten a `TextBlock` instead. Neither was new damage from this
pass, but both are exactly the kind of latent gap an observability matrix is meant to surface before
extending anything.

### `LLM-F001` placeholder reclassification (complete, all 42 pre-pass placeholders)

Every placeholder in `conformance/agent/` re-classified by which layer's contract it actually
exercises, using the same reasoning already established for the three replay-signature scenarios in
§4's `LLM-017` row (same-model wire-format replay is this layer's `AI-013` mechanism; cross-model
survival/stripping is `XFORM-###`'s rules 5-12 in `spec/target-model-transformation.md`) and applying
it consistently to the rest.

**A — Layer-02-owned (3 total, only category filled this pass):**

| Scenario | Reasoning |
|---|---|
| `public-llm-vocabulary-schema` | The layer's own vocabulary-shape evidence. **Filled this pass** — see below. |
| `same-model-thinking-signature-replayed` | Same-model Responses-wire-format replay retaining a signature — `AI-013`'s own mechanism (`openai-responses-shared.ts`), not a cross-model survival decision. **Not filled this pass** — needs the actual replay algorithm (Phase 5/`AI-013` implementation), which is separate work from the DSL/runner extension this pass delivered. |
| `same-model-unsigned-thinking-not-replayed` | Same reasoning — same-model, wire-format concern. **Not filled this pass**, same blocker. |

**B — `XFORM-###`-owned (10):** `cross-model-redacted-thinking-omitted` (rule 10), `cross-model-signatures-stripped` (rules 8/11/12 — this resolves the previously-open joint question: "stripped" is the survival decision, not the replay mechanism), `cross-model-thinking-converts-to-text` (rule 8), `nonvision-tool-image-placeholder` (rule 3, already cited as `AI-020`'s own test evidence in the manifest), `nonvision-user-image-placeholder` (rule 2, same), `null-content-normalizes-empty` (rule 1), `orphan-tool-result-synthesized` (rule 14), `tool-call-id-normalization` (rule 13), `aborted-assistant-excluded-from-replay` (rule 15), `errored-assistant-excluded-from-replay` (rule 15). None touched this pass.

**C — `AGENT-###`-owned (29):** `abort-settles-before-idle`, `active-abort-provider`, `active-abort-tool`, `after-hook-failure-replaces-result-with-tool-error`, `agent-end-messages-prompt-vs-continuation`, `agent-state-streaming-projection`, `before-hook-failure-becomes-tool-error`, `continue-ordering`, `continue-steering-no-double-drain`, `execute-failure-becomes-tool-error`, `followup-only-when-otherwise-idle`, `high-level-callback-failure-settlement`, `idle-after-agent-end-listeners`, `initial-prompt-order-after-turn-start`, `initial-steering-before-first-request`, `late-tool-update-ignored`, `length-stop-executes-no-tools`, `parallel-tool-completion-vs-message-order`, `pending-tool-calls-state`, `prepare-arguments-failure-becomes-tool-error`, `prompt-while-running-rejected`, `schema-validation-failure-becomes-tool-error`, `terminate-allows-follow-up-when-otherwise-idle`, `terminate-does-not-discard-steering`, `terminate-still-runs-prepare-and-stop-policy`, `terminate-suppresses-tool-driven-continuation`, `tool-batch-parallel`, `tool-batch-sequential-contagion`, `turn-lifecycle-order` — all turn/tool/queue lifecycle semantics, agent-loop territory even though several construct `AssistantMessage`s as fixtures. None touched this pass.

**D — other:** none found; every placeholder maps cleanly to A, B, or C.

3 + 10 + 29 = 42, matching the pre-pass placeholder count exactly. Only the one category-A scenario
ready without further Pi-behavior work (`public-llm-vocabulary-schema`) was filled.

---

## 8. Failure model

Every raised exception in `minion_agent/llm/` checked for type, message content, and whether any
path swallows a failure instead of surfacing it: `LlmError` (base), `UnknownModelError` (names the
unresolvable provider/model), `AdapterProtocolError` (raised only for a genuine adapter bug — an
empty stream with no terminal at all, via `stream.py`'s `collect()`). All three are documented in
`errors.py`'s own module docstring as the eager/lazy split's raising side.

**Tested adversarially against a failure shape none of the existing tests constructed, and the
result required correcting an initial mis-classification (`LLM-F007`) — recorded here as a caution
for future review passes, not just a finding.** The never-raises contract (LLM-018) was probed with
an adapter that raises a Python exception mid-iteration instead of encoding its failure in-band (a
`ConnectionError` after a `StreamStart` chunk). `_settled()`'s `async for chunk in source:` had no
`try`/`except`, so the exception propagated straight out of `LlmService.stream()`'s iteration.

The first pass at this finding classified it `PI_PARITY_DEFECT` — wrong. Checked Pi's own central
dispatcher directly (`ref-repos/pi/packages/ai/src/compat.ts::stream()`): it calls
`provider.stream(model, context, options)` with **no `try`/`catch` around it at all**. If a
registered Pi adapter has this exact bug, Pi's own dispatcher does not protect its caller either —
each of Pi's *individual* built-in adapters (`anthropic-messages.ts`, `azure-openai-responses.ts`,
etc.) separately wraps its own request logic, but nothing centralizes the guarantee the way this fix
does. The frozen master's "Programming/invariant failures remain programming failures; this rule
does not require swallowing impossible internal states" carve-out plausibly covers exactly this case
(an adapter failing its own obligation is the adapter's bug, not the sort of expected
provider/network failure the rule is about) — so the *pre-fix* Python behavior was arguably already
consistent with both confirmed Pi behavior and a defensible reading of the master's own prose. There
is no confirmed Pi behavior this fix restores; it goes beyond what Pi itself guarantees.

**Fixed anyway, as a deliberate, disclosed hardening choice, not a parity restoration
(`PARITY_NEUTRAL_HARDENING`, not `PI_PARITY_DEFECT` — see §15).** `_settled()`'s loop is now wrapped
in `try`/`except Exception`, converting any adapter-raised exception into an in-band `StreamError`
terminal that preserves the accumulated partial, via a small `_error_terminal()` helper shared with
the pre-existing premature-EOF path. Verified with a throwaway repro script before and after, plus a
new permanent regression test, `test_an_adapter_that_raises_mid_iteration_still_settles_in_band`.
`asyncio.CancelledError` is a `BaseException`, not `Exception`, so explicit consumer-driven
cancellation is untouched — it still propagates and unwinds normally. The rationale for keeping the
fix despite it not being Pi-required: a plugin architecture where third-party adapter authors
(especially once Phase 5 lands) cannot be assumed to get their own obligation right benefits from the
service enforcing it centrally too — but this is a judgment call about defense-in-depth, not
something this pass had authority to decide is *required*, so it is recorded as hardening open to
reconsideration, not as a settled parity fix.

## 9. Security

Reviewed: whether any caller-supplied or model-supplied value (model/provider names,
`ToolCallBlock.arguments`, the new `details`/`data` blobs on `ToolResultMessage`/`DeferredHandle`/
`AssistantMessageDiagnostic`) could reach somewhere unsafe. Grepped the whole package for
`eval`/`exec`/`__import__`/`pickle`/`subprocess`/`os.system` — none found. `ToolCallBlock.arguments`
and every new `dict[str, Any]`/`Any` field (`details`, `data`) are carried as opaque data; nothing in
this layer interprets or executes them — that's `TOOL-###`'s job for `arguments` specifically, once
that layer exists. `ModelId`/`Request` construction does no string formatting into anything
execution-adjacent (SQL, shell, template). No security finding. This category is solid.

## 10. Reliability and operations

Walked `LlmService.register()`/`withdraw()`/`stream()` for any window where a mid-operation exception
could leave state inconsistent. `register()` is fully synchronous with no `await` points — Python's
own execution model makes it atomic with respect to any concurrent `asyncio` task, and its only loop
(`for model_id in ids: self._adapters[model_id] = adapter`) iterates a `list` built from a
`frozenset[str]` in one prior step, so there's no realistic partial-registration failure mode (a
custom pathological `Adapter.models` implementation that raises mid-iteration is an adapter author's
own bug, not a reachable reliability gap in `LlmService` itself). `withdraw()`'s own guard (`if
self._adapters.get(model_id) is adapter`) already correctly prevents a superseded adapter's
withdrawal from removing its replacement — directly tested
(`test_a_later_adapter_replaces_an_earlier_one_for_the_same_model`).

**"Last adapter wins" for a duplicate model registration — confirmed Pi-parity-correct, not merely
untested dict-overwrite behavior.** Checked Pi source (`ref-repos/pi/packages/ai/src/compat.ts`,
`registerApiProvider`): `apiProviderRegistry.set(provider.api, ...)` — a plain `Map.set()`, the exact
same last-write-wins semantics as Python's `self._adapters[model_id] = adapter`. This is a genuinely
different mechanism from Runtime's `ServiceRegistry` (RT-005: registration is *exclusive*, a second
`provide()` raises) — the two are unrelated seams (`LlmService`'s adapter-to-model map is this
layer's own internal registry, not the Runtime service seam `ctx.llm` itself resolves through), and
this layer's overwrite semantics match Pi's own registry mechanism, not an accidental omission of
Runtime-style exclusivity.

No reliability finding beyond `LLM-F007` (already fixed, §8).

## 11. Observability

`MockAdapter.requests`/`.pulled` let a test inspect exactly what was sent and how much of the stream
was actually consumed — but neither is part of the `Adapter` protocol (which only requires
`provider`/`api`/`models`/`stream()`); they're `MockAdapter`'s own instrumentation for testability.
**Gap noted, not urgent:** once a real (non-mock) adapter exists, there is no standardized
LLM-layer hook for observing the actual request/response an adapter sent to its provider — no
request/response logging or tracing seam at this layer. This is squarely `TEL-###` (telemetry)
territory per the requirement-ID convention, not something to build here, and it doesn't block this
layer's own certification — recorded as `LLM-F009` for whoever picks up the telemetry layer.

Every state transition that matters here — a stream's chunks, in order, ending in exactly one
terminal — is already the full observable surface `AssistantStream` offers; there's no silent
transition the way Runtime's `ctx.plugin()` had one (RT-F013).

## 12. Performance

Reviewed for accidentally-quadratic patterns, not benchmarked (no perf harness exists, consistent
with Runtime's own §12 scope decision). `LlmService._adapters: dict[ModelId, Adapter]` gives O(1)
lookup in `stream()`; `register()` is `O(len(adapter.models))`; `models()` is `O(n)` over the dict.
No caching, no repeated linear scans, nothing that would degrade with realistic adapter/model counts
(single digits to low tens, not thousands). No performance finding. This category is solid.

## 13-14. Public API and documentation

`minion_agent/llm/__init__.py` re-checked: `Cost`, `DeferredHandle`, `AssistantMessageDiagnostic`,
`DiagnosticError` are all present in both the import list and `__all__` (added in the prior pass),
alphabetically ordered consistent with the rest of the list. Every exported class/field carries a
docstring; spot-checked `tools.py::ToolSchema` (fully documented, including the deliberate
plain-`dict`-not-pydantic design rationale) and the newly-added `messages.py` types — all documented
in the prior pass already.

**`spec/llm.md` checked against the now-much-larger real vocabulary for drift — none found, and the
reason is worth recording precisely.** The expectation going into this check was that the spec
predates this pass's fixes and would be missing `Cost`, the 8 new `AssistantMessage`/
`ToolResultMessage` fields, the 3 signature fields, and `api` on model identity. It is not missing
any of them — every field this pass added to the Python implementation was *already* present in
`spec/llm.md`, because the spec was written from the frozen master's vocabulary directly (which
always specified the full 15-field `AssistantMessage`, full replay signatures, etc.), not from
Python's implementation state at the time it was written. It was the implementation that lagged the
spec, not the spec that lagged the implementation — this pass's remediation caught Python up to a
contract that was already correctly and completely documented. Field-by-field cross-check (content
blocks, both messages, `Usage`/`Cost`, `DeferredHandle`, `AssistantMessageDiagnostic`/
`DiagnosticError`, `StopReason`, model identity, the never-raises contract, Responses replay) found
exactly zero discrepancies.

**One real, minor naming drift found: `spec/llm.md` calls the tool-call content block `ToolCall`
(matching the frozen master's own vocabulary sketch), but Python implements it as `ToolCallBlock`**
— inconsistent with `TextBlock`/`ThinkingBlock`/`ImageBlock`, which the spec names with a `Block`
suffix and Python matches exactly. Recorded as `LLM-F008`, LOW severity: not touching `spec/llm.md`
(shared-contract file) or renaming the Python class (touches every construction site across several
packages) — just flagging the inconsistency for whoever next has reason to touch either.

---

## 15. Findings

| ID | Severity | Classification | Description | Disposition / action |
|---|---|---|---|---|
| LLM-F001 | LOW | `CONTRACT_ASSURANCE_DEFECT` — Layer-02-owned portion RESOLVED | Survey complete (63 scenarios in `conformance/agent/`, 21 real/passing, 42 unfilled placeholders pre-pass). The never-raises contract (LLM-018) already had genuine, passing canonical evidence commingled in `conformance/agent/` — no dedicated `conformance/llm/` family needed. All 42 pre-pass placeholders reclassified by ownership (see §7's full A/B/C table): 3 Layer-02-owned, 10 `XFORM-###`-owned, 29 `AGENT-###`-owned, 0 unowned. | **Category A resolved: `public-llm-vocabulary-schema` filled** using the new `expect_assistant_details` DSL (`LLM-F010`), driven through the real agent loop and mock adapter — two turns, one scripting every optional field the reference adapter can carry (proving presence), one scripting none of them (proving the real object reports absence as `null`, not a runner-side fabrication). Passes; schema-validates; full suite/`ruff`/`mypy` clean. **Category A still open: the two same-model replay-signature scenarios** — the DSL can now express them, but filling them needs the actual Responses-family replay algorithm (`AI-013`, unimplemented — Phase 5 work, a different blocker than `LLM-F010`). **Categories B/C explicitly deferred to their owning layers**, not forced into Layer 02 to close this finding numerically. |
| LLM-F002 | LOW | `CONTRACT_ASSURANCE_DEFECT` — PARTIALLY RESOLVED | `/pi-parity-manifest.yaml` had zero `AI-###` rows for four of frozen master §4's LLM-owned subsections: Responses-family replay signatures, the API/provider split, model/request options, and authentication. Only vocabulary and the never-raises contract (`AI-001..012`) had parity-manifest coverage. | **`AI-013` added** for Responses-family replay signatures — real, precise Pi source found (`api/openai-responses-shared.ts`), and the two existing placeholder scenarios (`same-model-thinking-signature-replayed`, `cross-model-signatures-stripped`) already name exactly this requirement (see LLM-017's updated row). **The other three deliberately not added.** Checked whether a real (not aspirational) row could be written for each: API/provider split has a real Pi symbol (`compat.ts::stream`/`registerApiProvider`) but zero existing conformance scenarios to cite as `tests:` (the manifest's own convention names real, even if placeholder, scenario files — inventing new ones now would mean authoring Phase-5-scoped conformance content ahead of any adapter to test it against); model/request options and authentication are in the same position. Adding rows for these three now would violate this finding's own resolution criterion ("describe real, not aspirational, behavior") in the opposite direction it was originally violated (an uncovered requirement vs. a manifest row with nothing real behind it). Revisit once Phase 5 gives each a real adapter/scenario to cite. |
| LLM-F003 | HIGH | `PI_PARITY_DEFECT` — RESOLVED | `AssistantMessage` — the vocabulary type carrying Pi-visible response identity/state for provider replay — had only 7 of the 15 fields Pi's `types.ts::AssistantMessage` and the frozen master both require (confirmed field-for-field match between Pi and master in §3, so this was not a spec ambiguity): missing `api, response_model, response_id, diagnostics, deferred, raw_stop_reason, end_turn`. | Fixed: all 7 fields added to `messages.py.AssistantMessage` (LLM-006). `api` defaults to `"mock"` (see `LLM-F006`'s disclosed compromise) but `service.py._empty_partial()` and `adapters/mock.py::build()` explicitly pass `api=request.model.api` rather than relying on the default. `session/derive.py` extended to round-trip all 7 fields, including new `_encode_diagnostic`/`_decode_diagnostic`/`_encode_deferred`/`_decode_deferred` helpers. 4 new unit tests plus a round-trip test. Full suite + `ruff` clean. |
| LLM-F004 | HIGH | `PI_PARITY_DEFECT` — RESOLVED | None of the three replay-signature fields existed anywhere in the content-block vocabulary: `TextBlock.text_signature`, `ThinkingBlock.thinking_signature`/`redacted`, `ToolCallBlock.thought_signature`/`namespace` were all absent from `content.py`. This made the "Responses-family replay signatures" contract (LLM-017) structurally unrepresentable. | Fixed: all three fields/pairs added to `content.py`'s dataclasses (LLM-001, LLM-002, LLM-004), all optional/defaulted (fully backward-compatible — every construction site in the codebase uses keyword args). `session/derive.py`'s `_encode_block`/`_decode_block` extended to round-trip them. 6 new unit tests plus a round-trip test. **Does not by itself close `LLM-F001`'s two replay-signature placeholder scenarios** — filling those meaningfully needs the actual replay implementation (`AI-013`, added this pass — see `LLM-F002`) and/or `XFORM-###`'s survival-filtering rules; which scenario needs which is not yet resolved (see LLM-017's updated §4 row). |
| LLM-F005 | MEDIUM | `PI_PARITY_DEFECT` — RESOLVED | Grouped vocabulary gaps, each confirmed against Pi source: (1) `Usage.cost` sub-object did not exist at all, `cache_write_1h` also missing; (2) `StopReason` enum was missing `DEFERRED`; (3) `ToolResultMessage` was missing `tool_name, details, usage, added_tool_names`; (4) `DeferredHandle` and `AssistantMessageDiagnostic`/`DiagnosticError` did not exist as types anywhere in `minion_agent/llm/`. | Fixed: new `Cost` dataclass and `Usage.cost`/`cache_write_1h`/`total_tokens` added (the pre-existing computed `.total` property kept unchanged, distinct from the new stored `total_tokens`); `StopReason.DEFERRED` added; `ToolResultMessage` extended with all 4 missing fields; `DeferredHandle`/`AssistantMessageDiagnostic`/`DiagnosticError` added and exported. **Side effect, verified not just assumed:** `tools/result.py::ToolResult.to_message()` was silently dropping `details`/`added_tool_names` — it had nowhere to put them before this pass — now threads them through; `tool_name`/`usage` remain unpopulated (no source in `ToolResult`/its callers; threading one through the tool-execution pipeline is `TOOL-###` territory). All encode/decode round-trips extended. Full suite + `ruff` clean. |
| LLM-F006 | MEDIUM | `PI_PARITY_DEFECT` — RESOLVED, with a disclosed compromise | Model identity was architecturally a `(provider, model)` pair (`service.py.ModelId`), not the `provider + api + model_id` triple the master requires. No `api` field existed anywhere in `ModelId`, `Request`, or the `Adapter` protocol. | `api: str` added to `ModelId` and the `Adapter` protocol; `LlmService.register()` threads it from adapter to model identity. **Not full Pi fidelity — disclosed, not silent:** Pi's `api` is required (no default). Making it required in Python broke 133 tests across `agent/`/`agent_loop/`/`conformance/` — positional 2-arg `ModelId(provider, model)` calls throughout those layers' own test suites, well outside this audit's scope to touch broadly in an LLM-layer pass. Reverted to `api: str = "mock"`, correct for every current caller (the sole registered adapter today). 3 fake `Adapter` test doubles inside `llm`/`agent_loop` test files (the only ones actually reached by `register()`) updated with a real `api` attribute. The default becomes actively wrong once a second API exists (Phase 5) and must be removed then — noted directly in the field's own docstring, not just here. |
| LLM-F007 | MEDIUM | `PARITY_NEUTRAL_HARDENING` — RESOLVED (reclassified from an initial, incorrect `PI_PARITY_DEFECT` — see §8) | `service.py._settled()`'s `async for chunk in source:` loop had no `try`/`except`. An adapter that raises a Python exception mid-iteration instead of encoding its failure in-band (verified adversarially with a throwaway repro: a `ConnectionError` after a `StreamStart` chunk) propagated straight through `LlmService.stream()`'s iteration, uncaught. **Not a Pi-parity gap:** Pi's own central dispatcher (`compat.ts::stream()`) has no `try`/`catch` around `provider.stream(...)` either — confirmed by direct source read — so nothing centralizes this guarantee in Pi; each of Pi's built-in adapters separately implements the discipline itself. The master's "programming/invariant failures remain programming failures" carve-out plausibly already covered the pre-fix behavior. No existing test constructed this shape before this pass. | Fixed as a disclosed hardening choice, not a parity restoration: the loop now wraps in `try`/`except Exception`, converting the exception into an in-band `StreamError` terminal via a small shared `_error_terminal()` helper, preserving the accumulated partial exactly like the pre-existing premature-EOF path. `asyncio.CancelledError` (a `BaseException`, not `Exception`) is untouched — explicit cancellation still propagates and unwinds normally. New permanent regression test `test_an_adapter_that_raises_mid_iteration_still_settles_in_band`. Full suite + `ruff` clean. Worth reconsidering whether a future pass wants this centralized, or prefers matching Pi's per-adapter-only discipline exactly — recorded as an open judgment call, not a closed decision. |
| LLM-F008 | LOW | `CONTRACT_ASSURANCE_DEFECT` | `spec/llm.md` names the tool-call content block `ToolCall` (matching the frozen master's vocabulary sketch), but Python implements it as `ToolCallBlock` — inconsistent with `TextBlock`/`ThinkingBlock`/`ImageBlock`, which both the spec and Python name with a `Block` suffix. A naming-only drift, not a field/behavior gap: checked `spec/llm.md` field-by-field against the full post-remediation vocabulary and found no other discrepancy — the spec was already complete before this pass (it was written from the frozen master directly, not from Python's implementation state, so it never lagged; Python's implementation was what caught up). | Open, not fixed — `spec/llm.md` is a shared-contract file outside this pass's authority to edit, and renaming the Python class touches every construction site across several packages. Flagged for whoever next has reason to touch either side. |
| LLM-F009 | LOW | `PARITY_NEUTRAL_HARDENING` | No LLM-layer hook exists for observing a real adapter's actual request/response traffic. `MockAdapter.requests`/`.pulled` provide this for tests, but neither is part of the `Adapter` protocol — a real (non-mock) adapter has no standardized way to expose what it sent/received for debugging or telemetry. | Open — this is `TEL-###` (telemetry) territory per the requirement-ID convention, not something to build in this layer's own pass. Recorded for whoever picks up the telemetry layer; does not block this layer's certification. |
| LLM-F010 | MEDIUM | `CONTRACT_ASSURANCE_DEFECT` — Python implementation complete and verified; **OPEN pending shared-contract review** | Attempting to fill `public-llm-vocabulary-schema.yaml` (`LLM-F001`) found the `agent`-family conformance DSL/runner could not observe most of this pass's new vocabulary — full root cause in §7's observability matrix (built before any fix, per field). Confirmed two latent pre-existing gaps along the way, neither new damage: `scriptedResponse.usage` was declared in the schema but never read by `_script()`; `_block()`'s `thinking`-type branch never existed, so scripting one silently produced a `TextBlock` instead. | **Implemented and verified, this pass:** (1) production code — `adapters/mock.py::ScriptedResponse` extended with `response_model`/`response_id`/`diagnostics`/`deferred`/`raw_stop_reason`/`end_turn`, threaded into `build()`'s real `AssistantMessage` construction; proven with new `tests/llm/test_mock_adapter.py` cases, including one proving unset fields stay `None`, not synthesized. (2) shared schema — `conformance/schema/agent-scenario.schema.json`: `contentBlock` gained the 3 signature fields (nullable, `additionalProperties: false` now enforced, matching its sibling `$defs`); new `$defs/usage`, `/cost`, `/diagnostic`, `/diagnosticError`, `/deferredHandle`, `/assistantMessageDetail`; new top-level `expect_assistant_details` (exhaustive per-message shape, parallel to `expect_assistant_stop_reasons`); `deferred` added to both `stop_reason` enums. All new/changed properties nullable where the real object can legitimately be absent, `additionalProperties: false` throughout for language-neutral strictness. (3) Python runner — `agent_runner.py`: `_script()`/`_block()` now construct real `Usage`/`Cost`/`AssistantMessageDiagnostic`/`DiagnosticError`/`DeferredHandle`/content-block objects from scenario data (construct-real-inputs, not synthesize); new `_normalize_*` functions read real `AssistantMessage`/content-block objects' actual fields into the schema's dict shape (read-real-object-normalize, not fabricate) — verified thin by the explicit absence-stays-`null` test at both the adapter and (via the filled scenario's second turn) the full-stack level. **Category-A scenario filled:** `public-llm-vocabulary-schema.yaml`, passing, schema-validated. **Not treated as resolved**, per instruction: the shared-contract reviewer rule (`conformance/**`/`schema/**`) requires explicit review before a change is canonical; Rust's independent Layer 02 pass (§18) already confirms it hit the identical blocker and did not invent a private schema — its existing `tests/llm_conformance.rs` is direct evidence the DSL style is Rust-consumable, but that is corroboration, not the review itself. Send this schema/runner diff for that review before marking `LLM-F010` `RESOLVED`. |

---

## 16. Certification gate

```text
Design alignment                         [x]  all 20 distinct LLM-### requirements traced to frozen §4
Pi parity                                [~]  vocabulary/stream-contract fields now Pi-parity-complete (LLM-F003..F006 resolved); LLM-005/010/012/017 remain open, none severe; LLM-F007 is hardening beyond Pi, not a parity fix
Normative spec                           [x]  spec/llm.md re-audited field-by-field against the full vocabulary — no drift found (LLM-F008 is naming-only)
Parity manifest                          [~]  AI-001..012 vocabulary/stream contract, AI-013 Responses replay (new); LLM-F002 partially resolved — 3 subsections still uncovered, deliberately (no real behavior to describe yet)
Canonical conformance                    [~]  LLM-018 real+passing; LLM-F010 implemented+verified (Python), public-llm-vocabulary-schema filled; open pending shared-contract review, not yet RESOLVED
Python tests where implemented           [x]  8 files audited (§6), all KEEP, one STRENGTHEN applied (LLM-F007's regression test)
Rust tests where implemented             [x]  §18 (Rust's own record) — 118 tests incl. 17 LLM, cargo fmt/clippy/doc/xtask all pass
Property/invariant tests                 [ ]  none exist for this layer; not flagged as a gap this pass (no property space obviously needing one was found — the vocabulary is data-shape, not algorithmic)
Concurrency tests where applicable       [~]  not directly applicable — this layer has no shared mutable state accessed concurrently beyond LlmService's dict, addressed under reliability (§10)
Fault-injection tests where applicable   [x]  LLM-F007's adversarial raising-adapter test (a hardening probe, not a parity check) is exactly this; premature-EOF/empty-stream/double-terminal already covered pre-pass
Security review                          [x]  §9 — no unsafe eval/exec/dynamic-import; caller/model-supplied data carried as opaque, not executed; no finding
Reliability review                       [x]  §10 — LLM-F007 fixed; "last adapter wins" confirmed Pi-parity-correct against real Pi source, not just untested
Observability review                     [x]  §11 — LLM-F009 recorded (no adapter request/response hook), non-blocking, TEL-### territory
Performance review                       [x]  §12 — no accidentally-quadratic pattern; no finding
Public API review                        [x]  §13-14 — Cost/DeferredHandle/AssistantMessageDiagnostic/DiagnosticError exports confirmed, all documented
Documentation                            [x]  §13-14 — spec/llm.md re-checked field-by-field, no drift beyond LLM-F008's naming note
All findings classified                  [x]  LLM-F001..F010 classified
No unresolved Pi uncertainty             [x]  none raised this pass — every ambiguity resolved by reading Pi source directly
No unresolved parity defect              [x]  LLM-F003..F006 all resolved (LLM-F006 with a disclosed, documented compromise); LLM-F007 reclassified PARITY_NEUTRAL_HARDENING, not a parity defect
No unresolved contract-assurance defect  [ ]  LLM-F001 Layer-02 portion resolved (2 A-category scenarios remain, blocked on Phase-5 replay logic, not on DSL); LLM-F010 implemented+verified but open pending shared-contract review; LLM-F002 partially resolved; LLM-F008 open (LOW/naming-only)
Deferred risks recorded                  [x]  LLM-020, LLM-021 N/A pending Phase 5; LLM-F006's default flagged for removal then; LLM-F007's design choice (centralize vs. per-adapter) flagged for Rust-cross-check reconsideration; LLM-F009 open for the telemetry layer
```

## 17. Certification result

**Result:** `NOT YET ELIGIBLE`

Steps 0-2 are complete with real grounding: pinned Pi source (`ref-repos/pi/packages/ai/src/`) was
read directly, not inferred from the frozen master's paraphrase — one master-paraphrase discrepancy
was found in passing (`toolcall_start` vs `tool_call_start`, §3) and flagged for the design owner
rather than silently corrected. All 20 distinct `LLM-###` requirements are drafted (§4) and all 8
Python modules are deep-audited (§5).

**Remediation from the prior pass is complete** (following the same survey-then-fix sequencing
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

**§6 and §8-14 are also now complete.** All 8 in-scope test files (`tests/llm/`'s 7 plus
`tests/session/test_derive.py`) were read in full, run, and classified — all `KEEP`, none stale
against the post-remediation shapes. The §8-14 review adversarially tested the never-raises contract
with an adapter that raises instead of encoding its failure in-band (a `ConnectionError` mid-stream)
and found `_settled()` had no guard against it — but the finding this produced (`LLM-F007`) required
a correction during this same pass: it was initially classified `PI_PARITY_DEFECT`, which direct
verification against Pi's own central dispatcher (`compat.ts::stream()` — no `try`/`catch` around
the adapter call) showed was wrong. Pi does not centrally defend against this either; nothing in
confirmed Pi behavior was being violated. The fix (a `try`/`except` in `_settled()` preserving the
accumulated partial, locked in with a permanent regression test) was kept anyway as a deliberate,
disclosed hardening choice appropriate to a plugin architecture — but reclassified
`PARITY_NEUTRAL_HARDENING` and recorded as an open judgment call, not a settled parity fix. This
correction is itself worth noting: verify a fork's findings against primary source before accepting
its classification, the same discipline this session has applied throughout — a finding produced by
adversarial testing is not exempt from that check just because the underlying code behavior was
confirmed by a repro script. Security and performance came back clean with no findings. Two
low-severity, non-blocking findings also recorded: `LLM-F008` (a naming-only spec/implementation
inconsistency — `ToolCall` vs `ToolCallBlock` — found while confirming `spec/llm.md` has no other
drift; the spec itself turned out to have been complete and correct all along, since it was written
from the frozen master rather than from Python's implementation state) and `LLM-F009` (no adapter
request/response observability hook yet, `TEL-###` territory).

**`LLM-F002` partially resolved; `LLM-F001` attempted and found genuinely blocked at the time, not
just unstarted — since resolved for its Layer-02-owned portion (see the pass recorded just below).**
`AI-013` was added to the parity manifest for Responses-family replay signatures, with a
real Pi source distinct from `XFORM-###`'s own (`api/openai-responses-shared.ts` vs.
`transform-messages.ts`); the other three uncovered subsections were deliberately left unresolved —
no existing conformance scenario exists to cite for any of them, so a row now would be aspirational,
which is this finding's own resolution criterion in the direction it forbids. Attempting to fill
`public-llm-vocabulary-schema.yaml` (part of `LLM-F001`) found a real, precise blocker rather than
completing the task: the `agent`-family conformance runner's message projection exposes only
`{role, text}`, with no path for any of this pass's new vocabulary fields, and `StopReason.DEFERRED`
is missing from two schema enums. Recorded as `LLM-F010` rather than filled with a scenario that
would only prove the old 7-field subset while `LLM-013`/`LLM-014` cite it as if it proved the full
shape — the placeholder was left as a placeholder, honestly, not silently converted to weak evidence.

**`LLM-F010` resolution pass (this pass, following the Rust handoff):** built the observability
matrix first (§7, every frozen field, before touching anything), which surfaced two latent
pre-existing gaps beyond the originally-diagnosed ones (`scriptedResponse.usage` declared but never
read; `_block()`'s `thinking` branch never existed). Extended `adapters/mock.py::ScriptedResponse`
(production code) with the six missing `AssistantMessage` fields; extended
`agent-scenario.schema.json` with a new `expect_assistant_details` construct and supporting `$defs`
(`usage`, `cost`, `diagnostic`, `diagnosticError`, `deferredHandle`), all nullable where the real
object can legitimately be absent; extended `agent_runner.py` to construct real typed objects from
scenario data and normalize real objects back to the schema's shape — verified thin with an explicit
absence-stays-`null` test, not just code review. Filled `public-llm-vocabulary-schema.yaml`, the one
category-A placeholder ready without further Pi-behavior work; full A/B/C reclassification of all 42
pre-pass placeholders is in §7. **Not marked `RESOLVED`** — the shared-contract reviewer rule applies
to this `conformance/**`/`schema/**` change, and that review hasn't happened yet. Full Python suite,
`ruff`, and `mypy` (on every touched file) clean throughout.

**Rust's independent Layer 02 pass has since landed (§18, `audit/llm-rust-assurance` branch)** —
typed vocabulary, strict required three-part model identity (confirming `LLM-F006`'s Python default
was a Python-specific compromise, not a necessary one), independently-adopted centralized
never-raises hardening (confirming `LLM-F007`'s reclassification), and a working
`tests/llm_conformance.rs` that already consumes the shared `conformance/agent/*.yaml` scenarios
through the real typed Rust service. Rust explicitly confirmed it hit the identical `LLM-F010`
blocker and did not invent a private scenario schema — direct, independent corroboration that this
is a genuine shared-contract gap, not a Python-only one, and that the DSL shape chosen this pass is
plausible for Rust to consume, though Rust's own review of the actual diff is still the thing that
settles it.

The Rust handoff package — the shared contract, Python status summary, the `LLM-F001`/`LLM-F002`
carry-forward, the `LLM-F006`/`LLM-F007` independent-decision probes, and the from-scratch
implementation scope as it stood before Rust's own pass — is `assurance/layers/02-llm-rust-handoff.md`.
Python continued `LLM-F001`/`LLM-F010` in parallel with Rust's work, not blocked on the handoff
landing first, per instruction.

**Follow-up dependencies:**

1. **`LLM-F010` is implemented and verified (this pass) but not resolved.** Send the schema/runner
   diff (`agent-scenario.schema.json`'s `expect_assistant_details`/`usage`/`diagnostic`/
   `deferredHandle`/`contentBlock` extensions, `agent_runner.py`'s `_script`/`_block`/`_normalize_*`
   changes, `adapters/mock.py`'s `ScriptedResponse` extension) through the shared-contract reviewer
   process before treating it as canonical — Rust's own Layer 02 pass (§18) independently hit the
   same blocker and its existing `tests/llm_conformance.rs` is corroborating evidence the DSL style
   is Rust-consumable, but that isn't the review itself.
2. Once `LLM-F010` is formally approved, fill the two remaining category-A placeholders
   (`same-model-thinking-signature-replayed`, `same-model-unsigned-thinking-not-replayed`) — blocked
   now on the Responses-family replay algorithm itself (`AI-013`, Phase 5), not on the DSL. Decide,
   jointly with whoever owns `XFORM-###`, whether `cross-model-signatures-stripped` (reclassified
   category B this pass, §7) needs its own Layer-02-adjacent scenario or is fully `XFORM-###`'s.
3. `LLM-F002` is partially resolved (`AI-013` added). The remaining three subsections (API/provider
   split, model/request options, authentication) stay unresolved until Phase 5 gives each a real
   adapter/scenario to cite — do not add aspirational rows for them before then.
4. ~~Independent Rust implementation and cross-check~~ — **done, see §18.** Rust independently
   confirmed `LLM-F006` is Python-specific (Rust's own `api` is required, non-defaulted) and
   independently arrived at the same `LLM-F007` `PARITY_NEUTRAL_HARDENING` classification. Rust's
   existing `tests/llm_conformance.rs` consumes 5 shared scenarios; once this pass's schema diff is
   reviewed and adopted, it should grow to include the now-real `public-llm-vocabulary-schema` too —
   Rust's own follow-up, not Python's to make.
5. When Phase 5 adds a second API: remove `ModelId.api`'s default (`LLM-F006`) and update every
   call site that relied on it, this time with real API values to assign, not a placeholder sweep.
6. Optionally resolve `LLM-F008` (rename either side for naming consistency) and `LLM-F009` (an
   adapter observability hook) whenever something else already has reason to touch that code —
   neither is worth a dedicated pass on its own.

---

## 18. Rust implementation and independent assurance result

**Rust pass date:** 2026-08-23

**Branch:** `audit/llm-rust-assurance`

**Result:** `RUST READY`; overall layer remains `IN_AUDIT` because `LLM-F001`/`LLM-F010` is shared
canonical-contract work, not a missing Rust runtime behavior.

### Implementation evidence

- `crates/minion-agent/src/llm/model.rs` — validated value-identity
  `provider + api + model_id`; all components are required for direct construction and serde
  deserialization. Rust independently rejects Python's temporary `api = "mock"` fallback.
- `crates/minion-agent/src/llm/vocabulary.rs` — typed snake_case content/message/usage/diagnostic/
  deferred/context/options/chunk vocabulary. Tool-call arguments are object-typed, user content
  supports Pi's string-or-block shape, and immutable references require `sha256:<64 hex>` identity.
- `crates/minion-agent/src/llm/adapter.rs` — typed provider seam returning
  `Stream<Item = Result<StreamChunk, AdapterStreamError>>`; eager adapter-start and operational
  stream errors are distinct concrete Rust errors.
- `crates/minion-agent/src/llm/assistant_stream.rs` — owns provider-neutral accumulation,
  operational-error settlement, premature-EOF error settlement preserving the accumulated partial,
  terminal normalization, fusion, and no-hidden-drain behavior. It does not catch Rust panics.
- `crates/minion-agent/src/llm/service.rs` — exact model lookup and eager stream-creation boundary;
  the adapter registry lock is released before adapter code runs.
- `crates/minion-agent/src/llm/scripted.rs` — deliberately dumb scripted adapter implementing the
  real trait. It records typed requests and emits raw script items without settlement semantics.

### Executable evidence

- `tests/llm_vocabulary.rs` — strict identity, common validation boundary, value equality,
  snake_case/optional-field forms, stop reasons, usage, thinking default, and content-addressed
  image-reference identity (`LLM-001..LLM-016`, excluding separately deferred behavior).
- `tests/llm_adapter.rs` — unknown-model and adapter-start eager failures, real-trait scripted
  request recording/exhaustion, and adapter boundary (`LLM-011`, `LLM-018`, `LLM-019`).
- `tests/llm_assistant_stream.rs` — represented operational errors, cancellation, premature EOF,
  partial preservation, malformed terminal normalization, exactly-one terminal, fusion, and
  post-terminal suppression (`LLM-015`, `LLM-018`).
- `tests/llm_conformance.rs` — thin partial agent-family adapter consumes the shared
  `premature-eof-synthesizes-error-terminal`, `premature-eof-preserves-partial-message`,
  `public-stream-fuses-after-first-terminal`, `represented-provider-error-rides-stream`, and
  `eager-invalid-model-fails-before-stream` scenarios through the real typed Rust service/stream.
  It translates fixture raw output and projects results only; settlement remains in the library.

### Independent finding decisions

- `LLM-F006`: **not a Rust defect.** Rust requires non-empty `provider`, `api`, and `model_id` and
  applies the same validation during deserialization. The Python compatibility default remains a
  Python-owned disclosed compromise.
- `LLM-F007`: Rust independently adopts central typed operational-error settlement as
  `PARITY_NEUTRAL_HARDENING`. The raw adapter reports expected failures as `AdapterStreamError`;
  `AssistantStream` settles them. Panics are not caught or converted.
- `LLM-F001`: **shared-contract concern, applicable to Rust.** Rust executes the five already-filled
  Layer-02 stream-boundary scenarios. The full vocabulary placeholder remains honestly blocked by
  `LLM-F010`; Rust does not invent a private scenario schema or claim weak evidence as canonical.
- `LLM-F002`: **shared-contract concern, applicable but not Rust-owned.** `AI-013` is consumed. The
  remaining parity rows stay deferred until implemented provider behavior has real evidence.
- `LLM-F008`: Rust uses the normative `ToolCall` name, so no Rust-local naming drift.
- `LLM-F009`: no production-provider traffic hook is introduced; remains deferred to telemetry.
- `LLM-F010`: remains the exact overall certification blocker. Rust's typed serde tests provide
  implementation evidence but do not substitute for the missing shared vocabulary DSL/projection.

### §8-14 Rust review

- Failure model: eager lookup/start errors are typed; expected post-return failures settle in-band;
  malformed raw terminal errors receive a non-empty implementation diagnostic; panics propagate.
- Security: dynamic JSON is limited to specified opaque/object fields; no eval/dynamic loading;
  authentication remains Phase 5 and no implicit credential fallback was introduced.
- Reliability/operations: service locks are narrow and never held through adapter code; dropping or
  fusing releases the raw stream; scripted request retention is explicit test-adapter behavior.
- Observability: typed terminal messages preserve provider error text and partial state; production
  traffic hooks remain `LLM-F009`/telemetry scope.
- Performance: large message/script enum variants are boxed after Clippy review; stream processing
  is single-pass and does not drain after terminal.
- Public API: every current Rust Layer-02 surface is used by direct or canonical tests; no agent,
  target-transformation, real-provider, session, or telemetry API was introduced speculatively.
- Documentation: module, adapter, service, and stream rustdoc state ownership/failure boundaries.

### Shared-contract changes

`NONE`. Rust consumed the committed specification, parity manifest, and canonical scenarios as-is.
The existing `LLM-F010` governance path remains the correct place for the later shared DSL/schema
expansion.

### Rust verification gates

Fresh results from the isolated worktree after the final implementation commit:

```text
cargo fmt --check
    PASS

cargo clippy --workspace --all-targets --all-features -- -D warnings
    PASS

cargo test --workspace --all-features
    PASS — 118 tests, 0 failed (including 17 LLM tests)

cargo test -p minion-agent --test llm_conformance -- --nocapture
    PASS — 2 adapter tests consuming 5 shared Layer-02 scenarios, 0 failed

RUSTDOCFLAGS="-D warnings" cargo doc --workspace --no-deps
    PASS

cargo run -p xtask -- conformance verify
    PASS

cargo run -p xtask -- coverage verify
    PASS (current repository command completed successfully; it emitted no detailed per-file report)
```
