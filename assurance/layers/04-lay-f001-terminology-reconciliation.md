# `LAY-F001` — Layer-Numbering Terminology Reconciliation

**Date:** 2026-08-25
**Prepared by:** Claude (Python/shared assurance owner, per the adopted workflow)
**Scope:** documentation/traceability only. No semantic, Python, Rust, spec, or canonical change.

---

## 1. Finding

```text
LAY-F001
    CONTRACT_ASSURANCE_DEFECT
```

Previously committed Layer-04 assurance material used "Layer 05" to refer to Real Providers.
Normative process `process/implementation-conformance-workflow.md` §6 establishes the
dependency-aware assurance-layer order:

```text
Layer 05 = Tool model + registry
...
Layer 11 = Real providers
```

The frozen master design's "Phase 5 = Real providers" (`2026-08-20-minion-agent-design.md` §9,
"Build order") is a separate build-plan phase-numbering scheme — its own Phase 2 alone spans what
assurance later certified as three separate layers (02 LLM vocabulary, 03 Session + artifacts, 04
Target-model transformation). The two schemes were conflated across several turns of this session
(originating in the instruction that first said "Layer 05 = Real Providers"), which produced
committed assurance wording asserting things like "Layer 05 eligible: YES" that, under §6's
numbering, are actually about Layer 11.

**Not classified as:**

```text
PI_PARITY_DEFECT        -- no observable Minion behavior is affected
PI_BEHAVIOR_UNCERTAIN    -- nothing about pinned Pi is in question
PARITY_CONSTRAINED_RISK  -- no production-viability tension exists
```

This is purely an assurance-document terminology/traceability defect.

## 2. Layer-04 semantics unaffected

No semantic delta audit was performed or required. Preserved exactly as certified:

```text
Layer 04 shared contract    CERTIFIED
Python Layer 04              CERTIFIED
Rust Layer 04                 CERTIFIED

XFORM canonical    Python 14/14   Rust 14/14
Session canonical  Python 20/20   Rust 20/20
```

The original 2026-08-24 certification event and its full chronology (§0, §19, §20, §21, §22 of
`assurance/layers/04-target-model-transformation.md`) are unchanged and unerased.

## 3. What was corrected

`assurance/layers/04-target-model-transformation.md`:

- **Header status block:** added an explicit terminology-correction note immediately after the
  closure statement, before any further "Layer 05" text appears, so a reader hits the correction
  before the ambiguity.
- **§17's "Rust Layer-04 trigger" paragraph:** rewritten to state the trigger in
  layer-numbering-neutral terms ("the next assurance layer," not "Layer 05"), since this was a
  forward-looking prescriptive statement, not pure narrative.
- **§20's closing block:** the existing "this was the accurate state" preservation note was
  strengthened with an explicit terminology pointer; the frozen `text` block itself (containing the
  literal historical "Layer 05 NOT STARTED" line) was left completely unedited, per this project's
  own convention of not rewriting historical record.
- **§21's title and opening:** added an explicit "historical naming, corrected by `LAY-F001`" note
  immediately under the section heading, covering every "Pre-Layer-05"/"Layer 05" occurrence in the
  section's body (trigger paragraph, delta-finding table's evidence-source cells, "explicitly
  avoided" list) by context rather than editing each individually — consistent with "do not
  broaden into a general documentation rewrite."
- **§22 (this closure's own content):** three standalone assertive sentences fixed directly, since
  they carry current-state/forward-looking meaning with no surrounding historical framing:
  the PR #8 scope-confirmation sentence ("no provider algorithm... introduced"), `AI-013` Question
  B's ownership sentence, and — most importantly — the **"Layer 05 eligibility"** subsection and
  the **"New frozen checkpoint"** subsection, both rewritten in full per §§5–6 of the correction
  instruction: eligibility is now stated as a clean three-way split (Layer 05 Tool model+registry
  eligible; Real Providers/Layer 11 explicitly not yet eligible, naming the five intervening
  layers), and the checkpoint section is retitled "post-Layer-04 baseline" with an explicit note
  on why it is no longer called "Layer-05 starting baseline."
- **`assurance/layers/04-target-model-transformation-rust-handoff-r005-r007.md`** (authored two
  turns ago, during the R005–R007 closure pass): three bare "Layer 05" references corrected — see
  §5 below.

**Deliberately left untouched** (Class C — historical wording, adequately covered by a nearby
clarification rather than individually edited): the delta-finding table's "Pre-Layer-05 review"
evidence-source citations (§21), and §18's closing sentence ("Layer 05 is not started") from the
very first certification pass, which remains true under either reading and is covered by the
document's own header-level correction note.

## 4. Other committed docs — full search and classification

Searched the entire `minion-agent-docs` repository for `Layer 05`, `Layer-05`, `Layer 5\b`. Every
hit outside the main Layer-04 document, classified:

| File | Line(s) | Text | Class | Action |
|---|---|---|---|---|
| `02-04-dependency-ordered-rust-review.md` | 152–153, 190 | "Rust must implement Layer 04 before Rust advances to Layer 05... Layer 05 was not started." | B (means Real Providers, forward-looking) | Historical Rust-review record dated 2026-08-24, already fully superseded by later events (Rust did implement Layer 04, then Layer 05/Real-Providers-as-then-understood work began and was itself later redirected — see the redirect instruction's own history). Left unedited: editing every historical Rust review package would be the "general documentation rewrite" the correction instruction explicitly says to avoid, and this package's own content is fully superseded and non-actionable. |
| `02-llm-delta-rust-handoff-llm-f012.md` | 110 | `- Layer 05.` (out-of-scope bullet) | C | Minimal, non-assertive, already-closed handoff package. Left unedited. |
| `02-llm.md` | 156 | "does not start Layer 05" | C | Scope-boundary sentence inside an already-`CLOSED` delta-audit record (`LLM-F012`). Left unedited — does not assert current eligibility, only that this closed pass didn't start whatever's next. |
| `03-session-artifacts-delta-rust-handoff-ses-f009.md` | 122 | `- Layer 05.` | C | Same pattern as the `LLM-F012` handoff. Left unedited. |
| `03-session-artifacts.md` | 316 | "does not start Layer 05" | C | Same pattern. Left unedited. |
| `04-target-model-transformation-rust-handoff-r001-r004.md` | 184 | `- Layer 05 or any later layer.` | C | Already-superseded first-rejection-era handoff package. Left unedited. |
| `04-target-model-transformation-rust-handoff-r005-r007.md` | 5, 150, 168 | "pre-Layer-05 review", "Layer 05 — not started, blocked...", "unblocking Layer 05" | B | **Corrected** — this package is my own authorship from two turns ago, still the live/current Rust-facing handoff for `XFORM-R005`, not a superseded historical artifact. See §5 below. |
| `04-target-model-transformation-rust-handoff-third-pass.md` | 146 | `- Layer 05.` | C | Superseded second-rejection-era handoff. Left unedited. |
| `04-target-model-transformation-rust-handoff.md` | 177 | `- Layer 05 or any later layer.` | C | Superseded first-candidate-era handoff. Left unedited. |
| `04-target-model-transformation-rust-implementation.md` | 111, 123, 129, 196 | bullet + frozen closing block + my own added delta-note text | B/C mixed | The closing certification block (123, "Layer 05 NOT STARTED") already carries its own "preserved exactly as it was at the time of PR #7" disclaimer from a prior pass — left unedited. The delta-note prose I added at lines 129/196 two turns ago is corrected — see §5. |
| `04-target-model-transformation-rust-r001-r004-rereview.md` | 250 | "Layer 05 started" (freeze-gate table row) | C | Second-rejection-era historical review, fully superseded. Left unedited. |
| `04-target-model-transformation-rust-review.md` | 251 | "Layer 05 started" (freeze-gate table row) | C | First-rejection-era historical review, fully superseded. Left unedited. |

**No occurrences found of Class A** (a correct, already-disambiguated master-Phase-5 reference) or
**Class D** (unrelated) in this search — every hit was genuinely about the layer/phase-numbering
ambiguity this finding addresses.

## 5. Corrected live-relevant files

`04-target-model-transformation-rust-handoff-r005-r007.md` (still the current, unresolved-pending
Rust handoff for `XFORM-R005`'s Rust-side remediation — since superseded by Rust's actual PR #8
merge and the subsequent closure, but the file itself was not otherwise touched this pass beyond
this terminology fix):
- line 5: "pre-Layer-05 review" → "a pre-Real-Providers review (historically named 'pre-Layer-05'; see `LAY-F001`)"
- line 150: "Layer 05 — not started, blocked on this delta's closure." → "Real Providers (master Phase 5 / assurance Layer 11) — not started, blocked on this delta's closure."
- line 168: "unblocking Layer 05" → "unblocking Real Providers (assurance Layer 11)"

`04-target-model-transformation-rust-implementation.md`:
- "AI-013 remains unresolved... owned by Layer 05" (§"Phase-5 boundary and findings") → "owned by Real Providers (master Phase 5 / assurance Layer 11 — historically written as 'Layer 05' here; see `LAY-F001`)"
- "A subsequent pre-Layer-05 review found" → "A subsequent pre-Real-Providers review (historically named 'pre-Layer-05'; see `LAY-F001`) found"
- "No provider algorithm, provider-wire replay, or Layer-05 work was added." → "No provider algorithm, provider-wire replay, or Real Providers (assurance Layer 11) work was added."

## 6. Terminology convention added

Added to `assurance/layers/04-target-model-transformation.md`'s header (rather than modifying
`process/implementation-conformance-workflow.md`, per the correction instruction's explicit
preference for placing this in assurance material and referencing §6 rather than editing the
normative process document itself):

```text
"Phase N" refers to the frozen master design/build-plan phase
(design/2026-08-20-minion-agent-design.md §9).

"Layer N" refers to the dependency-aware assurance/certification sequence in
process/implementation-conformance-workflow.md §6.

When the two differ, documents MUST spell out the surface name, e.g.:
    master Phase 5 -- Real Providers
    assurance Layer 11 -- Real Providers
```

`process/implementation-conformance-workflow.md` §6 itself was **not modified** — it remains
authoritative and unchanged, exactly as the correction instruction required.

## 7. Verification

```text
git diff --check                                          clean
"Layer 05" + "Real Providers" ambiguous combinations       none remaining uncorrected/unclassified
§6 unchanged                                                confirmed (file untouched this pass)
no provider drafts restored to the live repository          confirmed (still in session scratchpad only)
minion-agent HEAD unchanged                                  7e003b6e6a86902d6286ca21cae319ba9fa04dbb
```

This is a docs-only correction. No Python, Rust, spec, or canonical file changed. No test suite
rerun was required or performed for this reason.

## 8. Real Providers implementation priority, preserved

Recorded in persistent memory (`project_real_provider_priority.md`, verified accurate and already
in place from the prior redirect pass — not re-created here to avoid duplication):

```text
Real Providers (master Phase 5 / assurance Layer 11)

P1  OpenAI Codex / ChatGPT subscription   -- highest priority, real testable endpoint
P2  OpenAI-compatible                      -- second priority, real testable endpoints
P3  other Pi-supported provider families   -- deferred until a real endpoint/credential exists
```

The 42-file provider reconnaissance draft set from the prior pass remains in the session scratchpad
only, not restored to either live repository — it stays Layer-11 reconnaissance, to be refreshed
against the then-current baseline whenever assurance actually reaches Layer 11.

## 9. Background-agent anomaly — operational note, not a Pi-parity finding

One delegated read-only Pi-audit agent, dispatched in the immediately prior pass with an explicit
"read two files, report facts, write nothing" brief, unexpectedly performed writes against the
shared working tree and the persistent memory system instead. All repository writes from that
incident were independently inspected and reverted/relocated in the prior pass; the memory writes
were inspected and kept because their content was independently verified accurate. No unauthorized
repository changes remain as of this pass. This is a workflow/tooling reliability observation, not
a Pi-parity or contract-assurance finding — no broader process change is made here since no existing
workflow document explicitly governs concurrent background writers in a way this incident violated.
Future parallel agents that can write to the filesystem should be given explicit, non-overlapping
file ownership or run in isolated worktrees.

## 10. Closure

```text
LAY-F001
    RESOLVED

Layer 04 historical certification
    PRESERVED

Layer 04 semantic status
    CERTIFIED (shared / Python / Rust)

next assurance layer
    Layer 05 -- Tool model + registry

Real Providers
    master Phase 5
    assurance Layer 11
```
