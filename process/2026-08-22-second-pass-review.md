# Review — second pass: repo README, plans README, requirement-ID convention, reviewer policy

**Date:** 2026-08-22

**Scope:** four new files (`README.md`, `plans/README.md`,
`process/requirement-id-convention.md`, `process/shared-contract-reviewer-policy-proposal.md`) and
four modified files (`assurance/archive/...-audit-v2.md`,
`design/2026-08-21-frozen-master-process-reference-patch.md`,
`reference/2026-08-21-pi-parity-manifest.md`, and the Phase 5 amendment review-feedback file, left
untouched per standing instruction).

## New files — reviewed, sound, cross-reference gaps fixed

- **`README.md`** — a real front-door orientation doc that didn't exist before. Verified its file
  listings (`spec/`, `assurance/`, `plans/`) against actual `ls` output; every claim matches. The
  active-vs-historical split is accurate and consistent with everything established this session.
- **`plans/README.md`** — accurately summarizes the per-plan status notes already applied to the
  Python/Rust plan files earlier this session; no discrepancy found.
- **`process/requirement-id-convention.md`** — fills a real gap: `fidelity-assurance-method.md` §3
  referenced stable requirement IDs but never defined the convention. Sound: correctly distinguishes
  requirement IDs (which normative rule is certified) from parity-manifest IDs (which Pi source
  surface produced the obligation), explicitly allows non-1:1 mapping, gives a sane layer-by-layer
  rollout order. Minor observation, not a defect: several requirement-ID prefixes (`TOOL-`, `PROV-`,
  `HAR-`) share a prefix with existing parity-manifest IDs of the same name — the doc explicitly
  flags these as separate ID spaces, but a reader skimming both files could still misread `TOOL-001`
  in one context as the other. Worth a distinguishing convention (e.g. requirement IDs always
  written with a `REQ:` prefix in prose) if this causes real confusion in practice; not blocking.
  **Cross-reference gap fixed:** added a pointer from `fidelity-assurance-method.md` §3 to this
  document — it existed unlinked from anywhere in the active documentation chain.
- **`process/shared-contract-reviewer-policy-proposal.md`** — resolves the required-reviewer open
  item I flagged in the 2026-08-21 and 2026-08-22 workflow-doc reviews, without inventing an
  unstaffed two-approver requirement: mandatory semantic-owner approval now, implementation-owner
  review added once those roles exist. Sound and directly actionable. **Applied**: replaced the
  open-item paragraph in `process/implementation-conformance-workflow.md` with the adopted rule, and
  marked this proposal `ADOPTED`.

## Modified files — reviewed, sound

- **`assurance/archive/...-audit-v2.md`** — added an explicit supersession banner pointing at the
  active charter/method/template/register/gate split. A real improvement over relying on directory
  location alone to signal "historical."
- **`design/2026-08-21-frozen-master-process-reference-patch.md`** — updated to fix the stale
  `docs/process/...` path (now correctly `process/implementation-conformance-workflow.md` in the
  companion repo) and to add assurance-governance language. Still correctly framed as a
  pending-review patch against the frozen master, not applied to that file.
- **`reference/2026-08-21-pi-parity-manifest.md`** — two fixes: corrected the manifest's canonical
  location to the actual root-level path (not nested in `conformance/`), and escaped a raw `|` in
  the `AI-004` table row that was breaking Markdown table rendering. Both verified correct.
- **`design/2026-08-20-phase-5-real-providers-amendment-proposal-review-feedback.md`** — same
  uncommitted ninth-review-round content flagged in every prior pass. Left untouched, still set
  aside per standing instruction; unrelated to this review.

## Disposition

Committed everything reviewed above except the Phase 5 amendment file. Two direct edits applied
beyond simple review: the reviewer-policy adoption (workflow doc + proposal status), and the
requirement-ID-convention cross-reference from the assurance method doc.
