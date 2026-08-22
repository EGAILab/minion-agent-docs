# Review — assurance taxonomy-gap fix bundle

**Date:** 2026-08-22

**Scope:** the seven-file bundle adding `CONTRACT_ASSURANCE_DEFECT` as a fifth finding
classification (`assurance/2026-08-22-foundation-fidelity-assurance-charter.md`,
`assurance/fidelity-assurance-method.md`, `assurance/layer-certification-template.md`,
`assurance/risk-register.md`, `assurance/layers/01-runtime.md`,
`process/implementation-conformance-workflow.md`; `process/requirement-id-convention.md` needed no
change since it was already `ADOPTED`).

## Verdict: the taxonomy addition itself is sound, and directly responsive to real audit output

`CONTRACT_ASSURANCE_DEFECT` genuinely fills the gap I hit writing `01-runtime.md`: I had to invent
an ad-hoc "design/conformance completeness defect" label because runtime's findings don't fit the
original four Pi-specific classes (no Pi runtime exists to diverge from, so `PI_PARITY_DEFECT` never
applies here, but "a stated rule has zero executable evidence" isn't ordinary
`PARITY_NEUTRAL_HARDENING` either — it's a distinct kind of defect, in the contract/evidence itself).
The new class's definition and examples list matches what I was actually writing almost verbatim
(one of the charter's own examples, "a missing normative spec for a frozen Minion-owned
architectural layer," is RT-F005 near word-for-word). Verified the decision-tree ordering across all
three restated versions (charter, `fidelity-assurance-method.md` implicitly via cross-reference,
workflow doc) is logically consistent and non-overlapping. Checked `01-runtime.md`'s classification
normalization against the actual bundle diff: all 5 findings correctly relabeled
`CONTRACT_ASSURANCE_DEFECT`, and — critically — no requirement ID, scenario mapping, or gap
conclusion changed underneath the relabeling. This is genuine taxonomy work, not a rewrite that
happens to also touch findings.

## One real bug found and fixed: broken section numbering

`assurance/fidelity-assurance-method.md`'s new §4 ("Finding classification") insertion left the next
heading, "Implementation disposition," mislabeled `## 14.` instead of `## 5.` — creating a duplicate
`## 14.` (colliding with the document's actual final section, "Language status") and an out-of-order
sequence (4 → 14 → 6 → 7 → ... → 13 → 14) for everything in between. Confirmed by grepping every `##`
header in the file before touching anything. Isolated, mechanical error — every section after it was
already correctly renumbered by +1, only this one line pointed at the wrong number. Fixed directly.

## Two real content losses found and restored

1. **The mock-adapter-vs-runner boundary clarification (§9, "Conformance runner rule") was deleted
   entirely**, not compressed — the paragraph distinguishing a mock swapped in through the library's
   real plugin seam (expected, exactly what `provider_script:`/`tools:` scenario scripts rely on)
   from a runner that hand-simulates behavior around that seam (forbidden). This is the third time
   this specific content has been dropped from this document across the session without explanation.
   Restored, tightened to match the surrounding editorial tone rather than the original's full
   verbosity, since this bundle otherwise reads as a deliberate general tightening pass and a verbose
   restoration would fight that intent.
2. **The `process/shared-contract-reviewer-policy-proposal.md` cross-reference** was dropped from the
   "Shared-contract reviewer rule (adopted)" paragraph — a small, cheap traceability loss (a reader
   no longer knows there's a fuller proposal document explaining the reasoning). Restored the pointer.

## Compressions judged acceptable, not restored

The schema-coexistence/placeholder-scenario policy (§10.1) and the wire-fixture-never-a-CI-gate note
(§17) were both shortened, losing some illustrative detail (exact field-shape examples, the concrete
`TO_BE_FILLED_FROM_PINNED_PI_BEHAVIOR` placeholder string, the `XPASS`-as-signal explanation, the
specific cross-reference to the real-providers amendment's testing philosophy). Judged as acceptable
editorial tightening rather than genuine loss — the actionable rules themselves (family-key
discriminator, `TO_BE_` prefix detection MUST-requirement, xfail-not-skip, no-hardcoded-name-list,
migrate-with-owning-phase, live-provider-never-in-CI) all survive intact. Not fighting to restore
verbatim prose a third time when the substance is unchanged.

## Disposition

Fixed the numbering bug and restored the two genuine content losses directly (low-risk, mechanical,
or previously-established-as-worth-keeping). Committed the bundle with those three corrections
layered on top. The Phase 5 amendment review-feedback file's ninth round remains untouched, still set
aside per standing instruction.
