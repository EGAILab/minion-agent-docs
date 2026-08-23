# LLM Seam — Fidelity Assurance & Certification

**Layer ID:** `02`  
**Status:** `IN_AUDIT`  
**Audit date:** 2026-08-23 (Step 0-2 in progress: scope and normative sources recorded with pinned
Pi source/parity-manifest grounding, two structural findings raised; Pi behavior summary,
requirement traceability, and deep audit not yet started)  
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

**Not yet audited in depth.** Unlike Runtime (where this section was structurally "not applicable,"
since Pi has no equivalent runtime kernel), this layer is Pi-derived and this section has real work
to do. The parity manifest (§2) names the pinned Pi source locations for the vocabulary and
never-raises contract: `packages/ai/src/types.ts` (`TextContent`, `ThinkingContent`, `ToolCall`,
`UserMessage`, `AssistantMessage`, `ToolResultMessage`, `Usage`, `StopReason`, `DeferredHandle`,
`Context`, `StreamFunction`) and `packages/ai/src/utils/diagnostics.ts`
(`AssistantMessageDiagnostic`). No pinned Pi source is yet identified for Responses-family replay
signatures, the API/provider split, model/request options, or authentication — consistent with
those four subsections having no `AI-###` manifest coverage either (§2). Actually reading the pinned
Pi source at those paths, and documenting the audited Pi-visible behavior here (not just citing the
frozen master's own paraphrase of it), is still outstanding — do not infer Pi behavior from this
document's own prose alone without checking against pinned Pi source, per the project's standing
verification discipline.

---

## 4. Requirement traceability

Not yet started. Requires: (1) a full survey of `conformance/agent/` (and any other family) for
scenarios whose actual content exercises `LLM-###` concerns specifically, separated from `XFORM-###`
content that happens to live in the same directory; (2) drafting `LLM-001..LLM-NNN` requirement IDs
from frozen master §4's LLM-owned subsections (see §1 Owns above); (3) mapping each to its Pi
source, its canonical scenario (if any exists) or an explicit `GAP`, and its current status.

---

## 5. Implementation inventory

Not yet started. `minion_agent/llm/` contains: `content.py`, `errors.py`, `messages.py`, `plugin.py`,
`service.py`, `stream.py`, `tools.py`, `adapters/mock.py` — none read in full yet this pass beyond a
brief confirmatory look at `service.py` (which already names the never-raises boundary explicitly in
its own module docstring, a good sign of intentional design-spec alignment, not yet verified against
actual behavior).

---

## 6. Existing-test audit

Not started.

---

## 7. Missing test / conformance coverage

Not assessable until §4 exists.

---

## 8-14. Failure model / security / reliability / observability / performance / API / documentation

Not started.

---

## 15. Findings

| ID | Severity | Classification | Description | Disposition / action |
|---|---|---|---|---|
| LLM-F001 | MEDIUM | `CONTRACT_ASSURANCE_DEFECT` | No dedicated `conformance/llm/` scenario family or schema exists; LLM-relevant canonical evidence, if it exists at all, is currently commingled with `conformance/agent/` (and possibly XFORM-relevant scenarios in the same directory), making it impossible to cite clean per-requirement evidence without a full survey first. | Survey `conformance/agent/` (and other families) to classify existing scenarios by which layer's contract they actually exercise; decide whether LLM-### evidence should get its own `conformance/llm/` family or formally cite specific `conformance/agent/` scenarios as its canonical evidence (mirroring how Runtime's own §4 "Coverage notes" accepted non-1:1 scenario naming) — a decision, not a default. |
| LLM-F002 | MEDIUM | `CONTRACT_ASSURANCE_DEFECT` | `/pi-parity-manifest.yaml` has zero `AI-###` rows for four of frozen master §4's LLM-owned subsections: Responses-family replay signatures, the API/provider split, model/request options, and authentication. Only vocabulary and the never-raises contract (`AI-001..012`) have parity-manifest coverage. | Add manifest rows (or an explicit deferred/divergence disposition) for the four uncovered subsections before this layer can claim complete parity-manifest coverage; this is a manifest-authoring gap, not evidence that those subsections lack a Pi source — needs Pi-source lookup first (§3). |

---

## 16. Certification gate

```text
Design alignment                         [ ]  not yet traced
Pi parity                                [ ]  not yet audited — Pi-derived layer, unlike Runtime
Normative spec                           [~]  spec/llm.md exists, not yet audited for completeness
Parity manifest                          [ ]  AI-001..012 cover vocabulary/stream contract; LLM-F002 — 4 subsections uncovered
Canonical conformance                    [ ]  LLM-F001 — evidence location/ownership unresolved
Python tests where implemented           [ ]  not audited
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
All findings classified                  [x]  LLM-F001, LLM-F002 classified
No unresolved Pi uncertainty             [ ]  not yet assessed
No unresolved parity defect              [ ]  not yet assessed
No unresolved contract-assurance defect  [ ]  LLM-F001, LLM-F002 open
Deferred risks recorded                  [x]  none yet identified
```

## 17. Certification result

**Result:** `NOT YET ELIGIBLE`

This layer's audit has just started. Scope (§1) and normative sources (§2) are recorded with real
grounding: the pinned Pi source locations and parity-manifest rows for vocabulary/never-raises
contract are identified (`AI-001..012`), and two structural findings are recorded — `LLM-F001` (no
dedicated canonical-conformance location) and `LLM-F002` (four master §4 subsections have zero
parity-manifest coverage). §3 onward is unstarted.

**Follow-up dependencies:**

1. Read the pinned Pi source (`packages/ai/src/types.ts`, `packages/ai/src/utils/diagnostics.ts`)
   directly and document audited Pi-visible behavior in §3, rather than citing the frozen master's
   paraphrase of it.
2. Survey `conformance/agent/` (and any other family) to determine which existing scenarios actually
   exercise `LLM-###` content vs. `XFORM-###` content living in the same directory, using the
   parity-manifest's named test IDs (`public-llm-vocabulary-schema`,
   `represented-provider-error-rides-stream`, etc.) as search anchors; resolve `LLM-F001`.
3. Resolve `LLM-F002`: add or explicitly disposition manifest rows for Responses-family replay
   signatures, the API/provider split, model/request options, and authentication.
4. Draft `LLM-001..LLM-NNN` requirement IDs from frozen master §4's LLM-owned subsections and build
   the full §4 traceability table.
5. Deep-audit `minion_agent/llm/`'s modules (§5) and existing tests (§6).
6. Complete §8-14 review.
7. Independent Rust cross-check, once Python's evidence is stable — same sequence Runtime followed.
