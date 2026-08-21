# Review — `implementation-conformance-workflow.md`

**Reviewer note on method:** checked against actual repo state (the monorepo I built and committed this
session: `minion-agent/conformance/`, `minion-agent/pi-parity-manifest.yaml`,
`minion-agent/minion-agent-python/`, the separate `minion-agent-docs/` repo) and against the sibling
`2026-08-21-phase-0-spec-conformance-realignment.md`, not accepted on the document's own word.

**Overall verdict:** the semantic-authority model is sound and matches established project practice —
"neither implementation is a behavioral oracle for the other," the Pi → manifest → spec → conformance →
implementations hierarchy, and the per-phase audit-first workflow are all good, specific, and consistent
with the frozen master design's own philosophy. §7's conformance-runner rule in particular is an
excellent, concrete anti-pattern callout that most process docs of this kind never bother to write down.
The problems below are mostly not "this is bad practice" — they're "this doesn't describe the repo that
actually exists," which is a real defect in a document whose whole job is to be the thing two independent
teams follow literally.

---

## CRITICAL — §2's repo structure contradicts what's already built and already documented elsewhere

Three concrete mismatches, each checked directly against reality rather than assumed:

1. **`docs/` nested inside `minion-agent/` vs. `minion-agent-docs/` as its own established repo.**
   `minion-agent-docs/` has its own `.git`, has held every design/spec/plan artifact this whole project's
   history, and nothing in this session's restructuring work touched that. §2's diagram shows
   `minion-agent/docs/design/`, `minion-agent/docs/spec/`, `minion-agent/docs/process/` as if they were
   subdirectories of the code monorepo. They aren't. The sibling `2026-08-21-phase-0-spec-conformance-
   realignment.md` — a more concretely executable document than this one — itself writes
   `minion-agent-docs/spec/` as a separate path, confirming this workflow document's diagram is the odd
   one out, not reality.
2. **`conformance/pi-parity-manifest.yaml` vs. the actual `minion-agent/pi-parity-manifest.yaml`.** The
   real file sits at the monorepo root, a *sibling* of `conformance/`, not nested inside it. Again, the
   Phase 0 realignment doc's own "Phase 0 outputs" listing shows `pi-parity-manifest.yaml` and
   `conformance/` as siblings — matching reality, not this document's §2 diagram or its §8 repetition of
   the same nested claim.
3. **`python/`, `rust/` vs. the real `minion-agent-python/` (and presumably `minion-agent-rust/`).** This
   session moved `minion-agent-python/` into the monorepo with its full 74-commit git history preserved
   via `git-filter-repo`, specifically under that name. Renaming it to `python/` now would mean either
   another history-preserving path rewrite or losing the traceability just built.

None of these are matters of taste — they're the document disagreeing with itself (via its own sibling
doc) and with what's on disk. **I'm treating this as a documentation defect and fixing §2 to match
reality**, not executing a repo consolidation — folding `minion-agent-docs/` into the code monorepo would
be a real, disruptive, not-yet-discussed decision (atomic cross-cutting commits vs. a lighter docs-only
repo non-engineers might want without the full codebase) and isn't mine to make silently. Flagging it
here as an open question for later, not deciding it now.

---

## GAP — no acknowledgment that two incompatible conformance schema shapes currently coexist

This is not hypothetical — it's the exact state of the repo right now, discovered and preserved earlier
this session. Two schema families:

- **Legacy per-family schemas** (`agent-scenario.schema.json`, `runtime-scenario.schema.json`,
  `session-scenario.schema.json`; `additionalProperties: false`; `provider_script`/`steps`/
  `expect_messages` shape) — backing 41 real, executable, currently-passing scenarios carried over from
  Phases 1-4.
- **One new unified schema** (`family`/`status`/`authority`/`pi_revision`/`given`/`when`/`expect`) —
  backing 48 scenarios that are currently unfilled placeholders (`TO_BE_FILLED_FROM_PINNED_PI_BEHAVIOR`
  etc.), scaffolded with the frozen master's §8 scenario names but no content yet.

§4.4 and §8 describe "canonical conformance" as if it were one homogeneous, single-schema artifact. It
isn't, right now, and this document gives no guidance for the person who next fills in a placeholder
scenario (which schema governs it — the new unified one, presumably, but that's not stated) or the person
who next touches an old scenario (does it need migrating to the new shape, and if so, when — as part of
whatever phase reaches it, or as a dedicated migration pass?). This should be an explicit policy, not
left implicit.

---

## GAP — no reviewer/ownership rule for shared-contract changes

§10-11 describe PR *shapes* and a classification checklist, but never say **who must approve** a change
to `conformance/`, `spec/`, or `pi-parity-manifest.yaml`. For two independently-progressing
implementation teams, an unreviewed reinterpretation of the shared contract by one side is the single
most common real-world failure mode this whole document exists to prevent. Standard practice for a
polyglot monorepo with a shared contract is a CODEOWNERS-style rule: changes under `conformance/**`,
`spec/**`, or the parity manifest require sign-off from an owner on *both* the Python and Rust side before
merge, mirroring §13's own logic ("changes under `conformance/**` ... require both Python and Rust
semantic gates") but for review, not just CI.

---

## GAP — §5's phase-gap invariant has no backstop

"Python phase = N, Rust phase = N or N-1" is stated as a "recommended project invariant" with no
enforcement mechanism and no stated response to it already being violated — which, per the frozen
master's own "Existing implementation realignment" section, it currently is (Rust retains only completed
Phase 1 runtime; Python's existing code reaches Phase 4-5 territory, all now pending realignment). A
document meant to actually govern two teams' cooperation should say what happens once the gap exceeds
target: pause new Python semantic PRs, escalate to a named owner, something — not just name the target
and leave the overrun unaddressed.

---

## AMBIGUITY — §7's runner rule doesn't draw the mock-adapter boundary

The rule itself ("a runner MUST NOT implement semantic behavior that belongs in the library," with
concrete forbidden examples) is the strongest section of the document. But the conformance format's own
scenario shape (`provider_script:`, `tools:` — visible in every scenario file on disk) depends on a
**mock LLM adapter and mocked tool implementations** to drive the real library code through its real
plugin/service seams. The document doesn't say that a mock *adapter*, swapped in through the real seam,
is expected and required — only that a runner *bypassing* the seam to hand-simulate behavior is
forbidden. One clarifying sentence would close a boundary two independent teams will otherwise interpret
differently without ever noticing they disagree.

---

## CROSS-REFERENCE GAP — §13 CI gates don't mention the wire-fixture policy already established elsewhere

The Phase 5 real-providers amendment (`2026-08-20-phase-5-real-providers-amendment-proposal.md`) already
has a full "provider wire-fixture testing philosophy" section: three verification tiers, sanitized
fixtures, and live/credentialed checks explicitly scoped as "manual ... non-gating" — i.e., must never
run automatically in CI. §13's CI decomposition doesn't reference this at all and re-derives CI structure
from scratch, risking the two documents drifting on what CI is and isn't allowed to do with provider
credentials. Should cross-reference rather than silently duplicate.

---

## MINOR — per-scenario `pi_revision` vs. whole-baseline drift model

The already-committed placeholder scenarios each carry their own `pi_revision:` field, but §15's drift
workflow describes drift audits at the whole-baseline level (one adopted revision, one realignment pass,
one freeze). Worth an explicit call on whether per-scenario revision pinning is intentional (it would
allow partial/incremental drift audits, scenario by scenario) or just came along from a template and
should be dropped in favor of the single manifest-level revision field this document's model implies.

---

## Disposition

Applying the CRITICAL fix now (§2 restructured to match actual repo layout, `minion-agent-docs/` named
explicitly as a separate repo, `pi-parity-manifest.yaml` shown as root-level, `minion-agent-python`/
`minion-agent-rust` naming corrected) since it's a documentation-accuracy correction, not a design
decision. Not touching the docs-repo-consolidation question — flagged above, left open. The five
gaps/ambiguities (schema coexistence policy, reviewer ownership, phase-gap backstop, mock-adapter
boundary, wire-fixture CI cross-reference) are proposed as additions below; applying the schema-policy
and mock-adapter clarifications now since they're low-risk, high-value, and directly resolve real
ambiguity already causing confusion in this session's own work. The reviewer-ownership and phase-gap-
backstop items need an actual named owner/policy decision from the project owner, not something to
invent unilaterally — recorded as open items for that decision.
