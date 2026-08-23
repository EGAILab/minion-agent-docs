# LLM Seam — Rust Handoff Package

**Layer:** `02` (LLM Seam)
**Purpose:** Freeze the current Python-side LLM-layer evidence, package the shared contract, and
hand it to Rust for independent implementation and validation, without moving the contract while
Rust works.
**Prepared:** 2026-08-23, from the committed state of `assurance/layers/02-llm.md` as of commit
`752f70b` (docs) / `6b707d7` (code). This handoff package does not itself change the contract, the
taxonomy, or any already-resolved Python finding.
**Status this pass sets:** No change to `02-llm.md`'s `Rust status` field. Rust sets that field
itself once its own work produces a result (see §9 below).

**This handoff differs from Runtime's in one important way: there is no existing Rust code to
audit.** `minion-agent-rust/crates/minion-agent/src/` has only a `runtime` module —
`lib.rs` declares `pub mod runtime;` and nothing else. No `llm` module, stub, or placeholder exists.
Runtime's handoff asked Rust to audit and harden real primitives; this one asks Rust to build the
LLM vocabulary and never-raises contract from scratch, against a contract Python has now verified
and mostly implemented — not to port Python's types, but to implement the same *observable* contract
idiomatically in Rust.

---

## 1. The shared contract Rust must independently implement and validate

- **`LLM-001` through `LLM-021`** (20 distinct — `LLM-016` is folded into `LLM-003`) — the full
  requirement set in `assurance/layers/02-llm.md` §4. Every requirement is Pi-derived, unlike
  Runtime's Minion-owned architecture — Rust's implementation is checked against pinned Pi source
  and `spec/llm.md`, not against Python's source.
- **`spec/llm.md`** — the normative prose, confirmed this pass to have zero drift against the full
  post-remediation vocabulary (checked field-by-field). This is the binding authority for shape and
  behavior.
- **`/pi-parity-manifest.yaml`, rows `AI-001` through `AI-012`** — vocabulary and the never-raises
  contract, all `phase: 2`, disposition `adopted`. Each row already names an explicit Rust target
  (e.g. `AI-001`: `rust: Phase 2 llm vocabulary (new)`) — these were written in advance of any Rust
  LLM work existing, so "new" is accurate: there is nothing to retrofit, only to build correctly the
  first time. `AI-020` through `AI-026` (target-model transform) are **not** this layer's — that's
  `XFORM-###`, a separate future layer.
- **Pinned Pi source** (`ref-repos/pi/`, commit `b7bb00b936dbe21b8e160b3e89efdec361846699`):
  `packages/ai/src/types.ts` (857 lines — `TextContent`, `ThinkingContent`, `ToolCall`,
  `UserMessage`, `AssistantMessage`, `ToolResultMessage`, `Usage`, `StopReason`, `DeferredHandle`,
  `Context`, `StreamFunction`), `packages/ai/src/utils/diagnostics.ts`
  (`AssistantMessageDiagnostic`), `packages/ai/src/auth/types.ts` (`CredentialStore` and related —
  240 lines, relevant once Phase 5 needs it), and `packages/ai/src/compat.ts` (the central
  `stream()`/`registerApiProvider` dispatch — directly relevant to `LLM-F007`, see §5).
- **Canonical conformance**: still unresolved on the Python side too (`LLM-F001`, open) — no
  dedicated `conformance/llm/` family exists; LLM-relevant evidence lives commingled inside
  `conformance/agent/`, mostly as unfilled `TO_BE_FILLED_FROM_PINNED_PI_BEHAVIOR` placeholders (21 of
  63 scenarios in that directory are real/passing, the rest are placeholders — not all are
  LLM-relevant). This is genuinely unsettled for both languages right now, not just for Rust to
  catch up on — see §6.

## 2. Python is not the behavioral oracle

Same hard rule as Runtime's handoff, with one addition specific to this layer:

- Python's findings and fixes (§4 below) are **risk hints and a worked example of applying the
  contract**, not a template to port. Rust validates its own implementation against `LLM-001..021`
  and `spec/llm.md` directly.
- **Do not port Python's dataclass shapes field-for-field as a translation exercise.** Build Rust
  types that are idiomatic Rust (enums for `StopReason`/content-block variants, `Option<T>` for
  optional fields, whatever Rust's own serialization story requires) and satisfy the same observable
  contract — the same relationship Runtime's `ScopeTree`/`Fiber` have to Python's, structurally
  different, behaviorally equivalent.
- **Two specific design choices Python made under real constraints — make your own, don't inherit
  Python's:**
  - `LLM-F006`: Python's `ModelId.api` field defaults to `"mock"` because making it required broke
    133 tests across other Python layers' own test suites — a Python-specific blast-radius problem
    that does not exist in a from-scratch Rust implementation. Rust has no reason to default this
    field at all; making it required from the start is very likely the right call in Rust, since
    there's no legacy call-site debt to work around. Decide this independently.
  - `LLM-F007`: Python added a service-level `try`/`catch` around adapter iteration, converting any
    exception an adapter raises into an in-band error — **confirmed this is not required by Pi**
    (Pi's own `compat.ts::stream()` has no such guard; each Pi adapter individually implements the
    discipline). This is recorded in Python's own assurance file as an open design judgment call, not
    a settled requirement. Decide independently for Rust: match Pi's per-adapter-only discipline, or
    add the same centralized defense Python did, or something else Rust-idiomatic (a wrapper type, a
    trait default method, etc.). Whatever you choose, record the reasoning — don't silently adopt
    Python's choice as if it were mandatory.

## 3. Python-side assurance status (verbatim from `02-llm.md`)

**Requirement traceability (§4):** 14 of 20 distinct requirements COVERED, 2 appropriately N/A
pending Phase 5 (`LLM-020` model/request options, `LLM-021` authentication — neither matters until a
real, non-mock adapter exists), 3 open GAP at lower severity (`LLM-005` `UserMessage` string-content
shorthand, `LLM-010` standalone `LlmContext` type, `LLM-012` request-option schema), 1 GAP that's
unblocked on the vocabulary side but needs a different layer's work (`LLM-017` Responses-family
replay signatures — the fields exist, the same-model/cross-model decision logic is `XFORM-###`
territory).

**Resolved findings, verbatim:**

| ID | Severity | Classification | Disposition (verbatim) |
|---|---|---|---|
| `LLM-F003` | HIGH | `PI_PARITY_DEFECT` — RESOLVED | `AssistantMessage` extended from 7 to all 15 Pi fields (`api, response_model, response_id, diagnostics, deferred, raw_stop_reason, end_turn` added). `api` defaults to `"mock"` (see `LLM-F006`) but production call sites pass a real value where known. |
| `LLM-F004` | HIGH | `PI_PARITY_DEFECT` — RESOLVED | The three replay-signature fields (`text_signature`, `thinking_signature`/`redacted`, `thought_signature`/`namespace`) added across the content-block vocabulary, all optional/defaulted. |
| `LLM-F005` | MEDIUM | `PI_PARITY_DEFECT` — RESOLVED | `Cost`, `Usage.cost`/`cache_write_1h`/`total_tokens`, `StopReason.DEFERRED`, `ToolResultMessage`'s 4 missing fields, `DeferredHandle`, `AssistantMessageDiagnostic`, `DiagnosticError` all added. |
| `LLM-F006` | MEDIUM | `PI_PARITY_DEFECT` — RESOLVED, with a disclosed compromise | `api` added to `ModelId`/`Adapter`, **defaulted rather than required** — Pi's `api` is required with no default; making it required in Python broke 133 tests in unrelated layers' test suites, outside this layer's audit scope to sweep through. Flagged for removal once Phase 5 adds a second API. **Rust should not inherit this compromise — see §2.** |
| `LLM-F007` | MEDIUM | `PARITY_NEUTRAL_HARDENING` — RESOLVED (reclassified from an initial, incorrect `PI_PARITY_DEFECT`) | Service-level guard added against an adapter that raises instead of encoding its failure in-band. **Not Pi-required** — confirmed against Pi's own dispatcher, which has no equivalent guard. Recorded as an open design judgment call. **Rust should decide independently — see §2.** |

**Open, non-blocking findings, verbatim:**

| ID | Severity | Classification | Description |
|---|---|---|---|
| `LLM-F008` | LOW | `CONTRACT_ASSURANCE_DEFECT` | `spec/llm.md` names the content block `ToolCall`; Python implements `ToolCallBlock` (inconsistent with `TextBlock`/`ThinkingBlock`/`ImageBlock`, which match the spec's `Block` suffix exactly). Naming-only, not a field/behavior gap. **Not a constraint on Rust's naming** — Rust should use its own idiomatic type names; this finding is about a Python-specific inconsistency, not a cross-language naming requirement. |
| `LLM-F009` | LOW | `PARITY_NEUTRAL_HARDENING` | No LLM-layer hook exists for observing a real adapter's actual request/response traffic. `TEL-###` (telemetry) territory, not this layer's to build. Applies equally to Rust once a real adapter exists — not blocking now. |

**Security, performance: clean, no findings** (§9, §12 of `02-llm.md`) — both explicitly reviewed,
neither flagged anything. Worth Rust independently confirming the same for its own implementation,
not assuming it transfers.

**Existing-test audit (§6):** 8 Python test files, all `KEEP`, none stale against the
post-remediation vocabulary shapes.

## 4. Two findings carried forward, unresolved by either language yet

Unlike Runtime's handoff (where Python-side findings were resolved before handoff), these two are
**open on the Python side too** — this is a genuinely shared, unresolved question, not a "Rust catch
up" item:

**`LLM-F001`** (MEDIUM, `CONTRACT_ASSURANCE_DEFECT`, open): No dedicated `conformance/llm/` scenario
family exists. 63 scenarios live in `conformance/agent/`; 21 are real and passing (mostly exercising
the never-raises contract, `LLM-018`), 42 are unfilled `TO_BE_FILLED_FROM_PINNED_PI_BEHAVIOR`
placeholders. The never-raises contract's evidence is accepted as sufficient where it lives
(`conformance/agent/`, matching how the seam is actually exercised end-to-end) — the open work is
filling the vocabulary/replay-signature placeholders now that the fields exist. Two of the four named
placeholders (`same-model-thinking-signature-replayed`, `cross-model-signatures-stripped`) need
`XFORM-###`'s transformation logic first, not just this layer's vocabulary.

**`LLM-F002`** (MEDIUM, `CONTRACT_ASSURANCE_DEFECT`, open): `/pi-parity-manifest.yaml` has zero
`AI-###` rows for four of the six LLM-owned master §4 subsections: Responses-family replay
signatures, the API/provider split, model/request options, and authentication. Only vocabulary and
the never-raises contract (`AI-001..012`) have manifest coverage.

**What Rust should do with each:** the same three-way assessment Runtime's handoff asked for —
determine whether each is a Rust-local issue, a shared-contract concern, or not applicable to Rust's
situation, and say which explicitly. In particular, if Rust's own conformance evidence ends up living
somewhere different than `conformance/agent/` for structural reasons, that's worth surfacing as a
shared-contract question (does the language-neutral scenario family choice need to be language-neutral
too, or can each language cite different evidence locations for the same requirement the way Runtime's
RT-010 did with a unit test?), not decided unilaterally by either side.

## 5. Remaining Rust-owned work (this layer, from scratch)

Since nothing exists yet, this is implementation work, not an audit-and-harden pass:

1. **Implement the LLM vocabulary** — content blocks (text/thinking/image/tool-call, with the three
   replay-signature fields), message types (`UserMessage`/`AssistantMessage`/`ToolResultMessage`, the
   full Pi-required field set — see `LLM-006`'s now-complete Python shape as a reference for *what*
   fields are needed, not *how* to type them), `Usage`/`Cost`, `StopReason` (7 variants, including
   `deferred`), `DeferredHandle`, `AssistantMessageDiagnostic`/`DiagnosticError`. Read the pinned Pi
   source directly (§1) rather than working from Python's dataclasses or this document's prose alone.
2. **Model identity** — the `provider + api + model` triple (`LLM-011`/`LLM-019`). Decide the `api`
   field's optionality independently (§2) — very likely required, unlike Python's compromise.
3. **The `Adapter` trait/equivalent and a mock adapter** — the reference implementation conformance
   scenarios will eventually drive, matching what `adapters/mock.py` does for Python: deterministic,
   scriptable, and deliberately exercises edge cases (truncated streams, chunks after a terminal), not
   just the happy path.
4. **A coordinating service (`LlmService` equivalent)** — resolves a request's model to an adapter,
   implements the never-raises contract's eager/lazy boundary (`LLM-018`): ordinary errors for
   unresolved model/caller misuse *before* invoking the adapter, in-band terminal errors for
   everything *after*, plus the terminal/fused public stream shape
   (`non-terminal* -> exactly one terminal -> EOF`). This is this layer's single highest-stakes
   guarantee — verify it adversarially the way Python's §8 did (construct a misbehaving adapter and
   confirm the guarantee actually holds), not just by reading the implementation.
5. **Rust unit tests** for all of the above, mirroring the rigor of Python's 8 `KEEP`-classified test
   files (§6) — field defaults, round-trip-relevant shape (if Rust has its own serialization story),
   the never-raises contract's failure shapes.
6. **Rust's own §8-14 review** once the implementation exists: failure model, security, reliability,
   observability, performance, public API, documentation — same seven categories Python covered.
7. **Once `LLM-F001` is resolved (§4) and canonical scenarios exist for this layer**, a Rust
   conformance adapter that executes them against the real typed library, matching Runtime's own
   `tests/runtime_conformance.rs` precedent: deserialize scenario data, construct typed Rust inputs,
   invoke real public APIs, normalize output — never implement missing semantics itself. This may
   need to wait on `LLM-F001`'s resolution rather than being buildable in isolation right now, since
   there's currently very little real (non-placeholder) canonical LLM vocabulary evidence to run
   against.

## 6. No shared-contract DSL/schema changes this pass

**Superseded — see §9.** This was true when this handoff was first written; it no longer is. `LLM-F001`
was attempted afterward, found genuinely blocked (`LLM-F010`), and the resulting DSL/schema/runner
extension has since landed on `main` (commit `5d65a39`). §9 is the review package for that specific
diff — read it before doing anything with `conformance/schema/agent-scenario.schema.json` or
`tests/conformance/agent_runner.py`, since Rust's own `tests/llm_conformance.rs` will eventually need
to consume the same shape.

## 9. `LLM-F010` shared-contract review package

Prepared 2026-08-23, after the Python/shared-contract-owner's own formal review of the diff (recorded
in full in `02-llm.md` §7's "dedicated verification" and the `LLM-F010` finding row). That review
covers what Rust's implementation-owner review must independently confirm — this package summarizes
it; `02-llm.md` has the complete field-by-field evidence.

**Status update (2026-08-23, later the same pass): Rust already performed this review and rejected
commit `5d65a39`.** `REJECTED — CONTRACT_ASSURANCE_DEFECT`, PR #3 held, recorded in full in `02-llm.md`
§18's "Formal Rust implementation-owner review of finalized LLM-F010 contract". Four concrete schema
defects were found and independently re-verified against the schema text before being accepted:
`assistantMessageDetail` forbade the frozen `timestamp` field via `additionalProperties: false`;
`diagnostic.error`/`.details` and `deferredHandle.expires_at`/`.poll_after_ms` were non-nullable even
though the runner legitimately emits `null` for each when absent; two timestamp-shaped fields were
narrowed to `integer` where the frozen vocabulary specifies `number`. **All four are now fixed** in
`agent-scenario.schema.json` and `agent_runner.py::_assistant_detail`, re-verified by independently
constructing the exact edge-case documents Rust used to reproduce them (all now validate cleanly), and
the full Python gate suite re-run clean. Question 6 below is answered by this: Rust's own review is the
"reason to want it exposed" the question anticipated — `timestamp` is now a required, non-nullable
`number` field on `assistantMessageDetail`. **This is a corrected diff, not the original one under
review — it needs a fresh Rust implementation-owner pass, not silent acceptance on the strength of
Rust's earlier rejection having named the fix.** The rest of this package (files, semantic-surface
framing, thin-runner proof, scenario intent, deferred-scenario list) still describes the diff's
content accurately; only the review outcome and question 6 are superseded.

**Files changed** (originally on `main` at commit `5d65a39804add4b3f5913fdd67a9e484c3dd6039` --
the commit Rust reviewed and rejected; the fix for all 4 defects is now on `main` at commit
`37ce4bbc051fa35885873c04dbe3b51e3c99cb2b`, pending Rust's fresh re-review):
- `conformance/schema/agent-scenario.schema.json`
- `conformance/agent/public-llm-vocabulary-schema.yaml`
- `minion-agent-python/tests/conformance/agent_runner.py`
- `minion-agent-python/src/minion_agent/llm/adapters/mock.py` (production code, not test-only —
  `ScriptedResponse` gained the same 6 fields `AssistantMessage` gained in the earlier `LLM-F003` pass,
  so the reference adapter can carry them)

**What semantic surface each change exposes, and why this is observability-only, not new/redefined
behavior:**

Before this diff, the `agent`-family conformance runner's message projection was `{role, text}` only
— none of `AssistantMessage`'s extended fields (`api`, `response_model`, `response_id`, `diagnostics`,
`deferred`, `raw_stop_reason`, `end_turn`), any `Usage`/`Cost` field, the three content-block signature
fields, or `StopReason.DEFERRED` were observable through a canonical scenario at all, even though every
one of them was already a frozen field on the Python vocabulary type (`LLM-F003`/`LLM-F004`/`LLM-F005`,
resolved in an earlier pass). The diff adds a schema/runner path to observe them; it does not add or
change what those fields *mean* — every field traces to `spec/llm.md`/frozen master §4/pinned Pi
`types.ts` exactly as already documented, verified field-by-field this pass (`02-llm.md` §7). Two
latent pre-existing bugs were also fixed in the same diff, not introduced by it:
`scriptedResponse.usage` was declared in the schema but never read by the runner; `_block()` had no
`"thinking"` branch at all (silently produced a `TextBlock` instead).

**Thin-runner invariants, verified adversarially, not just asserted:** input-side functions
(`_script`/`_block`/`_usage`/`_diagnostic`/`_deferred`) only deserialize scenario YAML into real typed
constructor calls — no derived/computed values (e.g. `total_tokens` is read directly from the
scenario, never summed from the other `Usage` fields, matching Pi's own semantics that a provider's
reported total need not equal the sum of parts). Output-side functions (`_normalize_*`,
`_assistant_detail`) only read real object attributes — verified by an explicit regression test
(`test_unset_response_identity_fields_stay_absent_not_synthesized`) and independently re-confirmed
this pass with a throwaway adversarial script constructing a real `AssistantMessage` with every new
field at its unset default and asserting the normalized projection reflects that absence exactly
(`None`/zero-valued `Usage`), never a fabricated value.

**`public-llm-vocabulary-schema.yaml`'s intent:** two turns through the real agent loop and mock
adapter — one scripts every optional field the reference adapter can carry (proving presence survives
real construction/derivation), one scripts none of them (proving the real implementation reports
absence as `null`, not the runner or adapter inventing a value). This is deliberately the *only*
placeholder filled this pass.

**Known deferred Phase-5 replay scenarios, so Rust doesn't have to re-derive this:**
`same-model-thinking-signature-replayed` and `same-model-unsigned-thinking-not-replayed` remain
unfilled placeholders even after this DSL extension. Verified this pass (`02-llm.md` §7, exhaustive
git-history audit across both repos, all branches — not assumption): their semantic contract
(`LLM-017`/`AI-013`) is Layer-02-owned and complete, but "replay" specifically means parsing a stored
signature back into an outbound Responses-API request, which requires a real Responses/Codex provider
adapter that has never existed in this repository's history under any name or signature model. Filling
either scenario today would require the runner/mock to simulate Responses-provider wire encoding — the
exact thin-runner violation this rule exists to prevent. They stay deferred to Phase 5, non-blocking
for Layer 02, regardless of how Rust's own review of this diff concludes.

**Specific questions Rust must answer** (do not treat Rust's earlier, pre-diff encounter with
`LLM-F010` — landing at the identical blocker independently, §18 in `02-llm.md` — as answering these;
that was corroboration that a gap existed, not a review of this specific resolution):

1. Can `agent-scenario.schema.json`'s new `$defs` (`usage`, `cost`, `diagnostic`, `diagnosticError`,
   `deferredHandle`, `assistantMessageDetail`) and the new `expect_assistant_details` construct be
   consumed naturally from typed Rust — i.e., does a straightforward `serde` deserialization plus a
   normalization function analogous to Python's `_assistant_detail` cover it, or does something about
   the shape (nullable-vs-absent handling, `additionalProperties: false`, the `oneOf`-with-null
   pattern used for `diagnostics`/`deferred`) require awkward Rust-side reconstruction?
2. Can Rust's own real public `AssistantMessage`/`Usage`/`Cost`/content-block-equivalent objects be
   normalized *directly* into this shape, the way Python's `_normalize_*` functions do — reading real
   struct fields, no synthesis — or does Rust's own type shape (if it differs from Python's field-for-
   field mirror) force an awkward translation layer?
3. Would a Rust conformance adapter need to simulate any Agent/XFORM/provider behavior to satisfy this
   schema, or does it stay strictly within "deserialize, construct real inputs, invoke real APIs,
   normalize real outputs, compare"?
4. Are the null/absence semantics (every optional field required-but-nullable, never
   required-and-omittable) sufficiently defined for Rust's own `Option<T>` conventions, or is there an
   ambiguity that would let Python and Rust legitimately disagree about what "absent" means for some
   field?
5. Does any field name, shape, or convention in the diff imply Python-only behavior (a Python class
   name, a dataclass-specific pattern, anything that wouldn't translate to a language-neutral
   description of the vocabulary)?
6. `assistantMessageDetail`'s `required`/`properties` list deliberately omits `AssistantMessage.timestamp`
   (real vocabulary, but a Unix-millisecond value with no meaningful content to pin in a canonical
   scenario — noted in the Python-side review, not silently dropped). Does Rust's own conformance
   design agree this is fine to leave unobservable through this specific construct, or does Rust have
   a reason to want it exposed?

Rust's answers, plus a plain APPROVED/REJECTED (or "approved with the following change needed") on the
diff itself, is what closes `LLM-F010`'s implementation-owner review. This package does not substitute
for Rust actually reading the diff.

## 7. Reviewer-rule requirement (unchanged, for when it becomes relevant)

Per the adopted shared-contract reviewer rule: changes under `conformance/**`, `spec/**`, or
`/pi-parity-manifest.yaml` require explicit semantic-owner approval before merge, and — where
independent Python and Rust maintainers exist, which they now do — review from the affected
implementation owner too. This applies the moment either side starts filling `LLM-F001`'s
placeholders or adding `LLM-F002`'s manifest rows; it doesn't apply to this handoff itself (no such
files are touched here).

## 8. Expected result of this handoff

Rust's work on this layer is complete, for this pass, when it produces:

1. **A working LLM vocabulary and never-raises implementation** — not partial, not a subset; every
   `LLM-001..021` requirement traced to real Rust code or an explicit disposition (`N/A`,
   `deferred`, etc.), the same way Python's §4 table works.
2. **Rust findings, if any** — new finding IDs, classified per the adopted taxonomy, with the same
   evidence-grounded rigor (concrete file/line references, adversarial verification for the
   never-raises contract specifically).
3. **Explicit, independent decisions on `LLM-F006` and `LLM-F007`** — not "matched Python," a reasoned
   Rust-specific call, recorded with why.
4. **A three-way assessment of `LLM-F001` and `LLM-F002`** (§4) — Rust-local, shared-contract, or N/A,
   not silently inherited or silently ignored.
5. **An updated `Rust status` field** in `assurance/layers/02-llm.md`'s header (currently
   unassessed/`NOT_IMPLEMENTED`), reflecting the real outcome.
6. **An explicit statement of what still blocks LLM Layer certification**, enumerated the way
   `02-llm.md` §17 already enumerates Python's own remaining work — not a general "more work needed."

This handoff package itself does not move `02-llm.md`'s status, gate, or `Rust status` field — those
change only once Rust's own work produces the result described above. Python continues its own
remaining work (`LLM-F001`, `LLM-F002`) in parallel with Rust, not blocked on this handoff landing
first.
