# Review — full `minion-agent-docs/` folder

**Date:** 2026-08-21
**Scope:** all 27 tracked/untracked files under `minion-agent-docs/` at time of review: `design/` (11),
`plans/python/` (4), `plans/rust/` (3), `process/` (3, including this file's predecessor), `spec/` (7),
`reference/` (1).

**Method note:** as with every review this session, claims were checked against actual repo state
(`minion-agent/` code, `ref-repos/pi/` source at the pinned commit) rather than accepted on the
documents' own word. Where a claim was structural/self-consistency-only, it's noted as such rather than
implied to have been source-verified.

---

## Already reviewed in depth this session (not re-covered here)

- `design/2026-08-18-minion-agent-design.md` — original master, superseded.
- `design/2026-08-20-minion-agent-design.md` + its review-feedback — frozen master, independently
  verified against Pi source; see that file for the full record.
- `design/2026-08-20-phase-5-real-providers-amendment-proposal.md` + its review-feedback — reconciled
  against the frozen master; see that file.
- `process/implementation-conformance-workflow.md` + its review-feedback — reviewed and corrected
  earlier today; see that file.

---

## New material reviewed in this pass

### `spec/*.md` (7 files, ~180 lines total) — accurate, not stubs

Read in full. These are dense, terse condensations of the frozen master's rules, not placeholder
scaffolding (unlike the 48 conformance scenario stubs found and preserved earlier this session).
Spot-checked several specific claims against what I'd already independently verified against Pi source:

- `spec/llm.md`'s `provider + api + model_id` compatibility-identity claim and the seven-value
  `StopReason` — exact match to the master and to Pi's `types.ts`.
- `spec/target-model-transformation.md`'s rule 9 ("different model + non-redacted empty thinking ->
  remove") — this is the exact thinking-compatibility-table gap my own earlier review of the master
  design flagged as missing; it's present and correct here.
- `spec/tools.md`'s terminate-fold wording ("suppresses only tool-driven automatic continuation;
  normal prepare/stop/steering/follow-up remains eligible") — matches the corrected semantics I
  independently verified against Pi's `agent-loop.ts` myself.
- `spec/agent.md`'s prompt-run event order (`turn_start` before initial-prompt lifecycle, steering
  poll before first request) — matches the corrected ordering, also independently verified against Pi
  source earlier.

No defects found on this pass. Note for completeness: `spec/` as scoped (Phases 0-4, matching the
Phase 0 realignment plan's own stated output list) doesn't yet cover Phase 5 provider-specific rules
(retry composition, the `openai-completions`/`codex-responses` API split) — consistent with those
still living only in the Phase 5 amendment, not a gap in what's here.

### `reference/2026-08-21-pi-parity-manifest.md` — accurate, but caught a live divergence during review

The human-readable table (51 rows: 47 adopted, 3 intentional divergence, 1 deferred) matches the real
`pi-parity-manifest.yaml`'s row count and disposition counts. Its own disclaimer ("if this document and
the canonical YAML differ, update this reference from the YAML") is the right framing and wasn't needed
here — the two agree.

**However, while cross-checking this against the actual repo, found `pi-parity-manifest.yaml` sitting
moved — uncommitted — from the monorepo root into `conformance/`, contradicting both this reference
document's own implied root-level location and the workflow document I'd fixed yesterday.** Confirmed
with the project owner rather than guessing: root-level was correct, the move wasn't intentional.
Reverted (moved back, working tree now clean, matches what's already committed). Flagging this
explicitly because it's exactly the kind of live-ground-shifting-mid-review this project's own
governance principle (spec/authority.md: "silence is not a valid disposition") warns about — worth a
habit of re-checking file locations before trusting a document's implied layout, not just its content.

### `design/2026-08-21-frozen-master-process-reference-patch.md` — sound, correctly held as pending

A short, well-scoped proposal to add a "follow the process document" pointer into the frozen master
design. Correctly recognizes the master is already FROZEN and frames itself as "apply as an explicitly
reviewed governance-only edit... rather than silently changing frozen semantic content" — exactly the
right instinct. Not yet applied (by design, pending that explicit review). No issue found; flagging only
that it's still an open action item, not forgotten.

### `process/2026-08-21-phase-0-spec-conformance-realignment.md` (358 lines) — thorough; two concrete gaps found by checking its own completion checklist against real code

Read in full (only skimmed ~80 lines previously). This is a well-structured, specific execution plan —
its own outline matches what the `spec/` files actually contain field-for-field, and its "Required
`agent/`/`session/` cases" lists match the actual scaffolded scenario names exactly. Checked several
items on its own §7 completion checklist directly rather than assuming they were done because the
surrounding files exist:

1. **"scenario schemas encode the frozen vocabulary" — not yet true.** `conformance/schema/
   scenario.schema.json` (the new unified schema) requires only `name`/`family`/`status`/`authority`/
   `pi_revision`, with `given`, `when`, and `expect` all typed as `{}` — completely unconstrained. None
   of the vocabulary fields this same document's own §3 lists (`text_signature`, `thinking_signature`,
   `redacted`, `stop_reason`, `deferred`, etc.) are actually validated by the schema yet. The schema
   file existing is not the same as the schema doing its job — worth not letting that checklist item
   read as done just because the file is present.
2. **Runner-purity spot-check passed.** Read `minion-agent-python/tests/conformance/agent_runner.py`
   directly against §4's runner rule: `terminate` is read from scripted scenario data and threaded into
   a typed `ToolResult` construction (constructing typed input — allowed), and `derive_messages` is
   called on the real library's session log (invoking the real API — allowed). No semantic-logic
   leakage found on this check.

### `plans/python/*.md` (4 files) and `plans/rust/*.md` (3 files) — real, concrete staleness-signaling gap, now fixed

Not read line-by-line (19,430 lines total; the master design's own realignment section already
establishes their vocabulary/semantics content needs reimplementing, so a full correctness audit of
already-known-superseded content wasn't the valuable check here). What I did check: **every one of the
7 files presented itself with no status marker at all** — dated 2026-08-18/19, phrased in the present
tense as currently-actionable ("Goal: Build the provider-neutral LLM vocabulary..."), with nothing in
the document itself signaling that its content was written against the now-superseded 2026-08-18
design. A reader opening `plans/python/2026-08-18-plan-2-llm-session-telemetry.md` cold would have no
way to know its vocabulary content is stale without independently knowing this session's history or
cross-referencing the parity manifest separately. This is exactly the silent-staleness failure mode the
project's own "silence is not a valid disposition" principle exists to prevent — just never applied to
plan documents.

**Fixed directly** (mechanical, low-risk — adding accurate status disclosure, not a design decision):
added a status note to the top of all 7 files, each naming what's specifically superseded and pointing
at the current authority (the frozen master, the relevant `spec/*.md` file, and the relevant
`pi-parity-manifest.yaml` row prefix). Calibrated per plan rather than one generic banner — Plan 1
(runtime/conformance-format) is largely retained per the master's own guidance, so its note says that
rather than overstating the staleness; Plans 2-4 and both Rust plans are more substantially superseded
and say so.

### `design/2026-08-18-foundation-validation.md` + review-feedback, `design/2026-08-18-minion-agent-updated-design-review-feedback.md` — fine as historical record, no changes needed

Headers checked, not read in full (906 + 736 + 541 lines). Unlike the plans, these don't need a status
marker: they're accurately self-dated review/validation artifacts from the 2026-08-18 design-freeze
process ("Date: 2026-08-18", "blocks freezing the `minion-agent` design"), read naturally as historical
record of a process that already completed, not as currently-actionable specification. The distinguishing
factor from the plans: these are written in past/completed framing about a freeze decision that happened;
the plans are written in present-tense imperative framing ("Build X") that reads as live work.

---

## Disposition

Applied: 7 plan-file status notes (mechanical, low-risk). Reverted: the uncommitted
`pi-parity-manifest.yaml` move (confirmed with the project owner, root-level is correct). Flagged, not
applied: the empty-schema gap (§3 vocabulary fields not yet encoded in `scenario.schema.json`) is real
implementation work for whoever next touches the schema, not something to invent unilaterally here.
Everything else reviewed checked out — the `spec/` files, the parity-manifest reference doc's content,
and the frozen-master patch proposal are all sound.
