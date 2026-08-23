# Layer 03 (Session + Artifacts) — Rust Implementation-Owner Review Package

**Prepared:** 2026-08-23  
**Prepared by:** Claude (Python/shared-contract owner, per the adopted workflow)  
**Why this exists:** Layer 03's assurance record reached a provisional `CERTIFIED` conclusion without
the required affected-implementation-owner review of the shared contract it had changed. This package
requests that review, following exactly the governance discipline the `LLM-F010` cycle in Layer 02
established: Python does not get to unilaterally certify a shared cross-language layer.

**Reviewed commits (original candidate):**

```text
minion-agent        3d6ffa4   SES-F001: session-scenario.schema.json / conformance/session/*.yaml /
                               pi-parity-manifest.yaml / session_runner.py
minion-agent-docs   92579ee   spec/session.md (SES-F002/F003 boundary clarification) +
                               assurance/layers/03-session-artifacts.md
```

**Status update (2026-08-24): Rust already performed this review and rejected the original
candidate.** `REJECTED — CONTRACT_ASSURANCE_DEFECT`, recorded in full in
`03-session-artifacts-rust-review.md`. Four defects: `assistantDetail`/`toolResultDetail` omitted
`provider`/`model`/`timestamp`/`error_message`/`tool_call_id` under `additionalProperties: false`;
`step.append` admitted role-incompatible field combinations the runner silently ignored;
`contentBlock` was not type-discriminated, admitting structurally impossible variants. `SES-F002`/
`SES-F003`/`MINION-003` were all independently approved by that same review. All four defects were
independently reproduced against the schema before being accepted, then fixed narrowly in:

```text
minion-agent        cda6b50   SES-F001 remediation: the same 4 files, corrected
```

**This corrected candidate is what needs the fresh review** — every question in §9 below still
applies to it, especially B.6/B.8 (do the fixed `assistantDetail`/`toolResultDetail` shapes now
represent the frozen fields correctly?) and B.4/C (does the type-discriminated `contentBlock` and the
role-conditional `step.append` map cleanly to idiomatic Rust?). The prior rejection is not superseded
by this package restating the original questions — it is superseded only by a fresh review verdict on
`cda6b50`.

**Pinned Pi revision:** `b7bb00b936dbe21b8e160b3e89efdec361846699` (unchanged since Layer 02).

---

## 1. What changed, classified by ownership

**SHARED CONTRACT** (this review's primary subject):

- `conformance/schema/session-scenario.schema.json` — extended from a `{role, text}`-only shape to add
  `contentBlock`/`usage`/`cost`/`diagnostic`/`diagnosticError`/`deferredHandle`/`toolStub`/
  `assistantDetail`/`toolResultDetail` `$defs`, a richer `step.append`, a new `record_header` step, and
  `expect_assistant_details`/`expect_tool_result_details`/`expect_reconstructed_header`/
  `expect_artifact_count` top-level assertions. Additive only — the original `{role, text}` shape and
  all 10 pre-existing real scenarios still validate and pass unchanged.
- `conformance/session/*.yaml` — 6 previously-`TO_BE_FILLED` placeholders filled
  (`content-signatures-round-trip`, `deferred-handle-round-trip`, `diagnostic-round-trip`,
  `rich-assistant-message-round-trip`, `request-reconstruction-with-artifacts`, and one the first pass's
  own count had missed) and 2 scenarios the frozen design named but that had never been authored under
  any name (`retained-tail-no-duplicate`, `request-header-component-reuse`) — 17 files total now, 16
  real.
- `pi-parity-manifest.yaml` — `MINION-003`'s `tests:` list gained `request-header-component-reuse`.
- `spec/session.md` — gained the by-value event-identity rule (previously implicit) and an explicit
  Session/Agent/XFORM boundary paragraph. No run/turn/step vocabulary was added — see §4 below for why.

**PYTHON IMPLEMENTATION / RUNNER** (supporting evidence, not itself under cross-language review):

- `minion-agent-python/tests/conformance/session_runner.py` — extended to construct/normalize the
  richer shapes above through real `SessionLog`/`ArtifactStore`/message objects. No `minion_agent/
  session/*.py` production file changed.
- `minion-agent-python/tests/conformance/test_session_conformance.py` — extended to check whichever
  `expect_*` keys a document declares.

**ASSURANCE EVIDENCE** (not shared contract, not requiring Rust review, included for context only):

- `assurance/layers/03-session-artifacts.md`, `assurance/risk-register.md`.

---

## 2. Python semantic-owner review (performed before this handoff, not skipped)

Re-read the finalized diff as semantic owner, not implementation author, against these questions:

- **Does every shared change derive from pinned Pi behavior?** The vocabulary fields
  (`text_signature`/`thinking_signature`/`redacted`/`thought_signature`/`namespace`/`usage`/`cost`/
  `diagnostics`/`deferred`/`api`/`response_model`/`response_id`/`raw_stop_reason`/`end_turn`/
  `tool_name`/`details`/`added_tool_names`) are all already-frozen Layer-02 vocabulary (certified);
  this pass only extends the SESSION-family DSL's ability to *observe* them through the log, exactly
  the same "observability-only" shape `LLM-F010` was. `record_header`/artifact-count assertions derive
  from design §5's own content-addressing rule, not invented.
- **Does the schema express language-neutral semantics?** Yes — snake_case field names matching the
  canonical vocabulary spelling, no Python class/dataclass names, `oneOf`-with-null used consistently
  for every field a real object can legitimately omit.
- **Does the DSL expose real Session behavior rather than Python object structure?** Checked against
  `session_runner.py` directly: every `expect_*` construct normalizes real attributes off real
  `AssistantMessage`/`ToolResultMessage`/reconstructed-header objects; nothing is computed/derived.
- **Does `session_runner.py` remain translation/observation only?** Re-read in full this pass — yes.
  See §6.
- **Does `spec/session.md` describe the actual frozen boundary rather than Python architecture?**
  Deliberately, yes — see §4; it states what Session owns and explicitly declines to specify Agent's
  vocabulary, rather than describing Python's `EventKind` enum.
- **Are all future-layer deferrals explicit?** Yes — `request-reconstruction-after-target-transform`
  carries an explicit `DEFERRED TO LAYER 04` disposition in the assurance record; nothing was filled by
  simulation.
- **Does `pi-parity-manifest.yaml` cite real Pi evidence?** `MINION-002`/`MINION-003` cite
  `N/A — Minion persistence/artifact architecture` (an honest "no direct Pi source" disposition,
  matching their `intentional divergence` classification) plus real test names. `AG-001`/`AG-004`
  (pre-existing, unmodified this pass) cite `packages/agent/src/agent-loop.ts` with real rule text.
- **Does any shared rule accidentally require Python-specific reconstruction?** Two items flagged
  below, not self-cleared — sent to Rust for independent judgment rather than resolved unilaterally.

### Two items flagged for Rust's independent check, not self-approved

1. **`assistantDetail` excludes `provider`, `model`, `timestamp`, `error_message`.** These are fixed
   by the runner (`model="mock-1"`, `provider="mock"`, `timestamp=1` for every message regardless of
   role or position) rather than scripted, and the schema's own description says so. This is
   *structurally* the same shape as `LLM-F010`'s rejected `timestamp` omission — the distinguishing
   claim is that here the runner *cannot* produce a differing real value (unlike Layer 02's real mock
   adapter, which does vary `timestamp` via a request counter), so nothing is being suppressed that a
   real object could legitimately carry differently. This reasoning has the same shape as the reasoning
   that turned out to be incomplete in Python's own first `LLM-F010` self-review. **Rust should verify
   this independently against its own planned Session construction, not accept the claim as given.**
2. **`step.append`'s schema does not conditionally restrict fields by `role`.** `stop_reason`/
   `diagnostics`/`deferred`/`response_model`/etc. are schema-legal on a `user` or `tool_result` append
   even though `session_runner.py`'s `_message()` only reads them for `role: assistant` (and
   `tool_name`/`details`/`usage`/`added_tool_names` only for `role: tool_result`) — a scenario author
   could set an assistant-only field on a user message and the schema would not catch it; the runner
   would silently ignore it. Not a null/absence defect and not currently observed to cause any wrong
   result, but a completeness gap worth an independent opinion: should the schema use `if/then` to
   enforce role-conditional field applicability?

---

## 3. Pi evidence for the Session/Agent/XFORM boundary (`SES-F002`/`SES-F003`)

Read directly this pass, at the pinned revision, not re-trusted from any prior wording:

- **`packages/agent/src/types.ts:428-443`** — `AgentEvent`, Pi's complete lifecycle-notification union:
  `agent_start` / `agent_end {messages}` / `turn_start` / `turn_end {message, toolResults}` (Pi's own
  comment: "a turn is one assistant response + any tool calls/results") / `message_start` /
  `message_update` (streaming only) / `message_end` / `tool_execution_start` / `tool_execution_update`
  / `tool_execution_end`. No third tier between "turn" and "message"/"tool_execution" exists in Pi.
- **`packages/agent/src/harness/session/types.ts`** and **`session.ts`** (Pi's persisted session
  storage — `Entry`/`LaneRecord` types) — searched directly for all nine `AgentEvent` type strings:
  **zero occurrences.** Pi's `AgentEvent` is an ephemeral `Agent.subscribe()` notification stream,
  structurally separate from what Pi's `SessionStorage` actually persists (message/model_change/
  thinking_level_change/active_tools_change/compaction/branch_summary/custom entries, plus
  operation/step/tool/queue/usage records for crash recovery — none of which are `AgentEvent` shapes).
- **`spec/agent.md`** (already-frozen Minion spec, independent of this pass): "A run is one high-level
  prompt/continue invocation. A turn is one assistant response plus tool calls/results caused by it,"
  with the order `agent_start, turn_start, ..., turn_end` — matches Pi source exactly.
- **`minion-agent-python/src/minion_agent/agent_loop/driver.py:1-9`** (module docstring): "A step is
  one model request plus the tools it calls. A turn is zero or more steps." — Minion's own, deliberate,
  internal terminology, defining "turn" as a whole multi-request run. This is where design §6's
  explicit prohibition ("MUST NOT redefine observable turn to mean a whole multi-request run") is
  actually violated — entirely inside a Layer-08 file, not in `session/*.py`.
- **`pi-parity-manifest.yaml`** already carries `AG-001` (phase 3, `pi:
  packages/agent/src/agent-loop.ts::runAgentLoop`, `rule: agent_start -> turn_start -> initial prompt
  message lifecycle`, `python: .../driver.py (rewrite)`, `disposition: adopted`) and `AG-004` (phase 3,
  `surface: turn definition/order`, `rule: one assistant response + resulting tool results; ...`,
  `disposition: adopted`) — found by direct manifest search, not newly added. Their conformance
  evidence (`conformance/agent/initial-prompt-order-after-turn-start.yaml`) is a real (non-fabricated)
  scenario name that is itself still `TO_BE_FILLED` and confirmed `xfailed` by running it.

**Candidate boundary, for Rust to verify independently against Pi, not to take on Python's word:**

```text
Agent:
    owns ephemeral lifecycle notification vocabulary (agent_start/turn_start/message_*/
    tool_execution_*)
    owns event naming/emission timing
    owns run/turn lifecycle definition
    owns causes/origin semantics

Session:
    owns persisted settled messages/tool results
    owns Session operations/records/artifacts (fork/reset/compaction/request-header)
    owns reconstruction/projection of stored Session state
    does not reconstruct Agent's ephemeral lifecycle notification stream

XFORM:
    starts after Session projection (design SS5 "Relationship to Pi's message projection")
    owns target-model compatibility/transformation
    request-reconstruction-after-target-transform.yaml's semantic dependency
```

---

## 4. Full ownership matrix

| Vocabulary item | Pi source | Persisted in Pi session? | Persisted in Minion session? | Reconstructed by Session? | Needed for Session projection? | Layer owner |
|---|---|---|---|---|---|---|
| `agent_start`/`agent_end` | `types.ts:430-431` | NO | Emitted as `TURN_START`/`TURN_END` (misnamed; scoped to the whole multi-step run) | NO | NO | `AGENT` |
| `turn_start`/`turn_end` | `types.ts:433-434` | NO | Emitted as `STEP_START`/`STEP_END` (misnamed; behaviorally correct granularity) | NO | NO | `AGENT` |
| `message_start`/`update`/`end` | `types.ts:436-439` | NO (settled message becomes an Entry separately) | No direct equivalent; `ASSISTANT_CHUNK` is the closest (streaming fidelity, log-only) | Settled surface messages: YES | Settled messages: YES, already correct | `SHARED BOUNDARY` — settled persistence is `SESSION`, live notification is `AGENT` |
| `tool_execution_start`/`update`/`end` | `types.ts:441-443` | NO (`ToolStartedRecord` is a separate crash-recovery mechanism) | `TOOL_CALL` (log-only) + `TOOL_RESULT` (surface) | Settled `TOOL_RESULT`: YES | Settled results: YES, already correct | `SHARED BOUNDARY` — settled persistence is `SESSION`, execution progress is `TOOL`/`AGENT` |
| `session/forked`, `session/reset`, `compaction`, `request/header` | N/A — Minion-owned | N/A | YES, with real interpreted `data` | YES — the only log-only kinds `derive_messages` reads | YES | `SESSION` |
| `causes`/origin metadata | Agent-loop-internal | NO | Opaque JSON-safe `data` on a log-only event | NO | NO | `AGENT` |

**Session-owned, independently re-confirmed correct:** `CORE_SURFACE_KINDS` is exactly `{user/message,
assistant/message, tool/result}`; by-value event-identity is enforced by `is_surface()`'s membership
check and conformance-pinned (`event-name-identity-is-by-value.yaml`); JSON-safety, sequencing, and the
four real Session-owned log-only kinds are all correct.

---

## 5. `SES-F001`/`SES-F002`/`SES-F003` summary

- **`SES-F001`** — 6 of 17 canonical session scenarios were unfilled placeholders and 2 design-named
  scenarios had never been authored (8 total gap items). Filled/authored 7; the 8th
  (`request-reconstruction-after-target-transform`) verified genuinely `DEFERRED TO LAYER 04` — no
  target-model-transformation module exists anywhere in the repository.
- **`SES-F002`** — originally framed as a Session-owned defect (design's log-only event vocabulary
  `run/*`/`turn/*` not matching `session/events.py`'s `turn/*`/`step/*`). Re-scoped this pass: the
  underlying mismatch is real but is entirely `agent_loop/driver.py`'s (Layer 08's) concern, already
  tracked under `AG-001`/`AG-004`. Session's own semantics required no change.
- **`SES-F003`** — `spec/session.md` was incomplete relative to the frozen design. Fixed only after
  `SES-F002`'s boundary was settled, to avoid baking wrong ownership into the spec.

---

## 6. Session runner thinness, re-audited this pass

`tests/conformance/session_runner.py` was read in full. Confirmed:

**Valid, present:** constructs real `SessionLog`/`ArtifactStore`/message-dataclass inputs; calls real
`operations.fork`/`reset`/`compact`, real `derive.encode_message`/`decode_message`/`derive_messages`,
real `request_header.record_header`/`reconstruct_header`/`reconstruct_tools`; normalizes only real
returned attributes.

**Invalid, absent (checked explicitly):** no `agent_start`/`turn_start`-style event emission anywhere
in the runner; no turn/run state machine; no XFORM/target-model-transformation logic; no fabricated
artifact/session metadata; no reconstruction logic that duplicates what `session/*.py` itself should
own.

**Session runner thinness: confirmed. Agent simulation introduced: NO.**

---

## 7. 17-scenario inventory

```text
16  current-layer (Session) scenarios, filled and passing
 1  Layer-04-deferred (request-reconstruction-after-target-transform.yaml)
 0  remaining true Layer-03 placeholders
```

The only Agent-owned (Layer 08) scenario this investigation touched
(`initial-prompt-order-after-turn-start.yaml`) lives in `conformance/agent/`, a different canonical
family, and was not filled, moved, or otherwise touched.

---

## 8. Python gate results (fresh, this pass)

```text
pytest                                    724 passed, 42 xfailed, 0 failed
tests/conformance/test_session_conformance.py   16 passed, 1 xfailed
tests/conformance/test_schema_validation.py     all passed
ruff check .                              all checks passed
mypy (session_runner.py + a src/ file)    no issues found
```

No `minion_agent/session/*.py` or `agent_loop/*.py` file changed this pass — `SES-F002`'s resolution
was a scope/ownership correction recorded in assurance and spec text, not a code change.

---

## 9. Questions Rust's implementation-owner review must answer

### A. Pi compatibility

1. Does the finalized Session contract (schema + `spec/session.md`) match pinned Pi?
2. Does Rust independently confirm the Session/Agent lifecycle boundary in §3/§4 against Pi source,
   rather than accepting Python's citation?
3. Does Rust independently confirm the Session/XFORM boundary?

### B. Language neutrality

4. Can Rust naturally deserialize/represent `session-scenario.schema.json`'s `$defs`?
5. Does any shared field assume Python-specific types?
6. Are null/absence semantics coherent throughout (see the two flagged items in §2)?
7. Are numeric types appropriately language-neutral (`usage`/`cost` fields as `integer`/`number`
   respectively; `diagnostic.timestamp`/`deferredHandle.expires_at`/`poll_after_ms` as `number`)?
8. Does `additionalProperties: false` anywhere omit a frozen, legitimately-representable field? In
   particular, is `assistantDetail`'s exclusion of `provider`/`model`/`timestamp`/`error_message`
   (§2, item 1) actually safe, or does it repeat `LLM-F010`'s defect shape?
9. Does the by-value event-identity rule (`spec/session.md`, `SES-F003`) translate cleanly to Rust
   without encoding Python object identity, dataclass equality, or reference aliasing? What identity is
   preserved, what gets serialized, what gets reconstructed?

### C. Thin-runner feasibility

10. Can Rust consume the 16 current-layer canonical scenarios through a thin runner analogous to
    Python's?
11. Would a Rust runner have to simulate Agent behavior to satisfy anything in the schema?
12. Would it have to simulate XFORM?
13. Would it have to reconstruct values Rust's real Session API doesn't actually expose?

### D. Scenario ownership

14. Are the 16 current-layer scenarios genuinely Session-owned, not Agent-owned scenarios miscounted
    as Session evidence?
15. Is `request-reconstruction-after-target-transform`'s `DEFERRED TO LAYER 04` disposition correct?
16. Does the ownership matrix (§4) hold up, or does Rust's own Session design suggest a different
    split?

### E. Contract completeness

17. Does `spec/session.md` contain enough information for two independent implementations to make the
    same observable choices?
18. Is any Session behavior currently underspecified?

**The question is not "does Python look correct?"** It is: *can an idiomatic Rust Session
implementation consume this exact language-neutral shared contract and reproduce the same observable
Pi-compatible Session semantics, without Python-specific reconstruction or future-layer simulation?*

Return exactly one formal verdict: `APPROVED`, `REJECTED — CONTRACT_ASSURANCE_DEFECT`,
`REJECTED — RUST IMPLEMENTATION DEFECT`, or `PI_BEHAVIOR_UNCERTAIN`. If `REJECTED —
CONTRACT_ASSURANCE_DEFECT`, cite the exact defect the way the `LLM-F010` review did (reproduced edge
cases, not general concerns) so it can be independently verified and narrowly repaired before a fresh
re-review — not treated as approved after a fix without that fresh review.
