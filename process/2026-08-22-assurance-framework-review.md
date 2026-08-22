# Review — new assurance framework and workflow-doc rewrite

**Date:** 2026-08-22
**Scope:** everything that appeared under `minion-agent-docs/` since my last full-folder pass
(`2026-08-21-full-docs-review.md`): the new `assurance/` directory (7 files), a substantial rewrite
of `process/implementation-conformance-workflow.md`, and the two Rust-monorepo-history-import
documents (`design/`... — actually `plans/rust/2026-08-21-rust-monorepo-history-import.md` and
`process/2026-08-21-rust-monorepo-history-import.md`).

**Method note:** consistent with every other review this session, checked against actual repo state
(the real `minion-agent` monorepo, git history, and shipped test code) rather than accepted on the
documents' own word.

---

## `assurance/` — new framework, reviewed, sound

Read in full: `README.md`, `2026-08-22-foundation-fidelity-assurance-charter.md`,
`fidelity-assurance-method.md`, `foundation-release-gate.md`, `layer-certification-template.md`,
`risk-register.md`. Skimmed the header/framing of `archive/2026-08-22-...-audit-v2.md`.

This is a coherent, well-designed assurance program: a consistent four-way finding classification
(`PI_PARITY_DEFECT` / `PARITY_NEUTRAL_HARDENING` / `PARITY_CONSTRAINED_RISK` / `PI_BEHAVIOR_UNCERTAIN`)
stated identically across the charter, the method, and the workflow doc; a genuinely useful decision
rule ("does fixing this change Pi-visible behavior?") that keeps production-quality concerns from
silently overriding Pi fidelity during this phase; a real requirement-traceability discipline
(stable IDs, requirement → source → implementation → evidence, no unmapped scenario, no undispositioned
manifest row); and a reusable layer-certification template with an honest, complete audit checklist
(security, reliability, observability, performance, public API, documentation — not just "does it
pass tests").

The archived v2 audit document is correctly placed in `archive/` — it's the pre-split draft that got
restructured into the current charter/method/template/register/gate split, and reads that way (it's
self-consistent, just superseded by the split, which is itself a sign of good process). No action
needed there.

No defects found in the assurance framework itself. It's new content I didn't author — reviewed and
verified, not modified.

---

## `process/implementation-conformance-workflow.md` — substantial, mostly-good rewrite; four prior fixes silently dropped, three re-applied

The document grew from ~510 to ~1050 lines, integrating the new assurance program throughout (a new
§4 "Fidelity versus hardening," assurance steps woven into the per-phase workflow, a new §12
"Assurance ownership," assurance references throughout PR/CI sections). The integration is
consistent and doesn't contradict the assurance files themselves — cross-checked the finding
classifications, the layer list, and the `/pi-parity-manifest.yaml` root-level path against both the
assurance docs and actual repo state; all agree.

**However**, diffing against the version I reviewed and corrected on 2026-08-21
(`68966bb`/`f45599c`), four of my prior fixes were silently removed with no replacement and no
stated rationale — the same failure pattern already caught once this session in a different file
(the master-design review-feedback's "Independent verification" section). Checked each individually
rather than assuming they should simply come back verbatim:

1. **Mock-adapter boundary clarification** (§9, "Conformance runner rule") — still true, still
   valuable, no replacement content covers it. **Re-applied.**
2. **Schema-coexistence policy** (was §8.1) — this one is more than "still true": the actual shipped
   Python test code (`tests/conformance/placeholder.py`, `test_agent_conformance.py`,
   `test_session_conformance.py`, `test_schema_validation.py`, committed `abc6cd0` and pushed) now
   *implements* exactly this policy — `TO_BE_*` sentinel detection, `pytest.xfail` marking, and
   schema selection keyed by the scenario's own `family` field. Leaving this undocumented meant the
   process doc had actually fallen *behind* what the codebase already does, not just lost a nice-to-have
   explanation. **Re-applied, and updated** to describe the real, shipped mechanism (content-based
   `TO_BE_*` detection, `xfail` with a reason, `XPASS` as the "this is now real, remove it from the
   list" signal) rather than the more speculative version I wrote before that work existed.
3. **Wire-fixture-never-a-CI-gate cross-reference** (§17, CI gates) — still valid, no replacement.
   **Re-applied.**
4. **Required-reviewer-rule open item** (near PR classification) — checked whether the rewrite
   addressed this a different way before re-adding it; it doesn't (grepped for
   `reviewer|approv|codeowner|sign.off` — nothing establishes who must approve a change touching
   `conformance/`, `spec/`, or the parity manifest). Still a real, unaddressed gap. **Re-applied.**

**One prior open item deliberately NOT re-added**, because it's actually been superseded by a better
mechanism, not silently dropped: the "no backstop for when the Python-ahead-of-Rust phase-gap
invariant is exceeded" finding. The new §7.3 ("Certification while Rust is behind") replaces
phase-number tracking with explicit per-layer status (`shared contract: CERTIFIED` / `Python:
CERTIFIED` / `Rust: NOT_IMPLEMENTED — planned Phase N`, named as "a valid state"). That's a more
precise answer to the underlying concern than the CODEOWNERS-style hard block I'd suggested — the
concern was "how do we know if the gap is actually a problem," and per-layer certification status
answers that more directly than a phase-count threshold would. Not re-adding this one.

---

## Rust-monorepo-history-import docs — verified complete, status corrected on the one I own

Two documents describe the same migration: `plans/rust/2026-08-21-rust-monorepo-history-import.md`
(Rust-owned, not touched) and `process/2026-08-21-rust-monorepo-history-import.md` (mine). Both
described the migration as design-approved/pending as of 2026-08-21.

Checked the actual `minion-agent` monorepo directly against the process doc's own stated completion
criteria rather than assuming the PR merge (`d0448b0`, observed in this session) satisfied them:

- `git merge-base --is-ancestor 041b9975b87a5a9e79180c4229cabee8a10d4bc5 HEAD` — succeeds.
- No `minion-agent-rust/conformance/` directory in the checked-out tree.
- Exactly one root `conformance/` and one root `pi-parity-manifest.yaml`.

All three hold. The migration is genuinely complete, not just merged-and-hoped. Updated the status
line on `process/2026-08-21-rust-monorepo-history-import.md` to say so, with the verification
evidence inline, so it reads as historical record of a completed migration rather than a still-open
plan. Left the `plans/rust/` counterpart untouched — Rust's to update if they want to.

---

## Untouched, intentionally

- `design/2026-08-20-phase-5-real-providers-amendment-proposal-review-feedback.md` — a ninth review
  round appeared (arguing against the generic `signature`-field design), uncommitted, in the working
  tree. Per explicit instruction earlier this session ("set aside"), left as-is — the master design
  has since settled the vocabulary question this round was contesting anyway, so the content is
  largely moot.
- `assurance/archive/` — correctly already archived, no action needed.

## Disposition

Applied: three re-added workflow-doc sections (mock-adapter clarification, updated schema/placeholder
policy, wire-fixture CI note), one re-added open item (required reviewer rule), one status correction
(`process/2026-08-21-rust-monorepo-history-import.md`). Deliberately not re-added: the phase-gap
backstop open item, superseded by §7.3's per-layer certification tracking. Not modified: the new
`assurance/` framework (reviewed, sound, not mine to originate further right now), `plans/rust/*`
(Rust-owned), the Phase 5 amendment review-feedback file (set aside per instruction).
