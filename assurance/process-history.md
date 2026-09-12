# Process history

A running log of workflow/process improvements distilled from layer retrospectives, per
`process/agent-workflow.md` section 14. This file records the improvement and why it was made;
the semantic/certification detail for the layer itself stays in that layer's own assurance files.

## Layer 10 (Provider abstraction + mock adapter) — closed 2026-09-12

Layer 10 mostly formalized provider infrastructure that already existed from Layer 02, but its
contract and evidence still required several review/convergence cycles before Rust implementation.
Two reusable assurance lessons were promoted into `process/agent-workflow.md` at closure.

### 1. Canonical list ordering needs both a named key and a crossing-key witness

Python and Rust both exposed the same current set of registered models, yet their canonical
runners used different ordering keys: `(provider, model, api)` versus `(provider, api, model)`.
Seven scenarios remained green because every relevant observation contained at most one identity.
The difference surfaced only during Rust closure review, after implementation, when the reviewer
constructed two identities whose `model` and `api` values deliberately cross under those keys.

**Fix:** section 9 now requires the shared contract to state the exact canonicalization key and
field precedence whenever an implementation-defined collection becomes an ordered canonical list,
to separate that tooling rule from production return-order semantics, and to retain a multi-entry
witness that distinguishes plausible competing keys.

### 2. Artifact validators must reject the wrong container before iterating it

Four manifest `tests:` values had silently parsed as YAML mappings rather than lists. The first
permanent validation gate then checked only the values produced by iteration, allowing a scalar
string to masquerade as a one-entry iterable. A later review added the missing container-type
assertion and malformed scalar/mapping witnesses.

**Fix:** section 8 now requires validators to check container shape before content iteration and
to retain negative probes for plausible malformed shapes. The Layer-10 manifest validator already
implements this rule, so the workflow change records and generalizes proven automation rather than
adding a new ceremonial check.

### Not promoted to persistent guidance

The stale exact-SHA header and three stale scenario notes were repaired through the existing
historical-artifact and exact-remote-state rules. Those rules worked once the inconsistencies were
found, so no additional workflow mechanism was needed.

## Layer 09 (Active Abort/Cancellation) — closed 2026-09-09

Layer 09 took ten shared/Python passes, three contract-convergence cycles (`L09-R007`; the
combined `L09-R012`/`R013`/`R014`; `L09-R018`), and one Rust implementation/closure pass. Two
reusable lessons were promoted into `process/agent-workflow.md` itself (see the diff for this
entry's own commit); this section records the fuller context.

### 1. An authority-protection fix needs a separate witness for EACH protected field's own omission, not one shared witness assumed to cover all of them

The same underlying failure mode recurred three times on the same event family:

- `L09-R006` (PASS 3) closed `AGENT_TRANSFORM_CONTEXT`'s signal-REDIRECT case (a listener
  delegating with a fabricated replacement signal). It did not test signal-OMISSION or
  instance-omission at all -- not yet part of that finding's own scope.
- `L09-R015` (found at the PASS-9 mandatory final review, closed in PASS 9 itself after one
  targeted re-review round) found `AGENT_PRE_STEP`/`AGENT_PREPARE_NEXT_TURN`'s own instance-
  redirect case was fixed but instance-OMISSION was not: PASS 8's own two "drop" witnesses both
  called the dispatch primitive's argument-less continuation form (`next_()`), which the
  primitive's own forwarding rule (`replacement or current`) treats as an unchanged forward -- a
  fundamentally different code path from a genuine, shorter replacement missing the protected
  field. Both tests passed against a candidate that could not actually handle true omission,
  because they never reached the omission-handling branch at all.
- `L09-R018` (found at the mandatory final review of the PASS-9 candidate) found that
  `AGENT_TRANSFORM_CONTEXT` -- the ONE event with two protected fields (`instance` leading,
  `signal` trailing) on opposite sides of its one transformable field -- could not safely resolve
  a delegation one field shorter than full at all: the SAME shortened length is produced by
  omitting EITHER protected field, so a fix correct for one single-field omission was silently
  wrong for the other. This required its own convergence cycle to resolve (legal delegation
  lengths restricted to exactly the transformable-field count or full, with any other length
  rejected explicitly rather than guessed).

Three passes, three independent reviews, one recurring meta-lesson: closing the redirect case
does not imply the omission case is closed, closing one field's own omission does not imply
another field's omission is closed, and a witness using a bare no-argument continuation call does
not exercise omission handling at all, regardless of its own name or docstring.

**Fix:** `process/agent-workflow.md` section 9.1 now states this directly -- enumerate each
protected field's own redirect and omission separately for a multi-field authority-protection fix,
and construct a genuinely shorter delegation for an omission witness rather than an argument-less
continuation call.

### 2. A convergence checkpoint's "can Rust implement this" question is not the same question as "does Rust need this at all"

`L09-R007`'s own convergence cycle (PASS 4/5) designed a claim-then-rollback mechanism
(`_Reservation`) specifically to defend `Inbox` claims against a synchronous, reentrant
`on_status_change` observer running between a run-entry attempt and its own commit. Every
convergence checkpoint through this layer asked, and answered, "can Rust implement this
idiomatically" -- always yes, via a typed equivalent. None asked whether Rust's own already-
certified Layer-08 architecture exposed the synchronous, listener-observable status-transition
hook that created the vulnerability in Python in the first place. It does not: Rust's own
`AgentInstance::try_begin_run`/`finish_run` never invoke arbitrary listener code between claiming
entering input and committing to a run, so no reentrancy window exists there at all, and the whole
`_Reservation` mechanism -- five Python implementation passes plus one convergence cycle -- turned
out to have no Rust counterpart whatsoever. This was disclosed correctly and honestly at Rust-
implementation time, but discovering it that late meant the cross-language cost of the underlying
Python architectural choice (a synchronous, fallible `on_status_change` extension point) was never
weighed against its own downstream assurance burden until the very end of the layer.

**Fix:** `process/agent-workflow.md` section 11.8.4's own challenge questions now ask directly
whether a defect's root cause depends on an extensibility point one language's own certified lower
layers expose and the other does not -- surfacing a one-language-only mechanism during
characterization, not only at Rust-closure time.

### Not promoted to persistent guidance

The independent Rust closure review for this layer read the full implementation, independently
re-ran every claimed gate (fmt, clippy, `cargo test` workspace at 287/287, rustdoc, `xtask
conformance verify`, schema validation at 185/185, manifest at 79/79 unique rows) rather than
trusting the candidate's own summary, and found the architecture, gate results, and Rust-side
canonical-placeholder disclosure all matched the claims exactly. This is a clean confirmation that
the existing exact-SHA review invariant (§11.3) and reviewer witness rule (§9.2) work as intended
under a large, multi-pass layer with three separate convergence cycles -- no new rule is needed
here, only the observation that the discipline held.

## Layer 08 (Agent Loop) — closed 2026-09-07

Layer 08 took fourteen shared/Python remediation passes, one contract-convergence cycle
(`L08-R002`/`L08-R004`), a three-round structured-shape correction (`L08-R011`, PASS 10-12), and a
two-round failure-identity correction (`L08-R014`, PASS 13-14) before Rust implementation and
closure. Three reusable lessons were promoted into `process/agent-workflow.md` itself (see the
diff for this entry's own commit); this section records the fuller context.

### 1. The §11.8 convergence trigger was adopted but not reliably checked

Section 11.8 (contract convergence) was itself adopted mid-layer, directly motivated by
`L08-R002`/`L08-R004` surviving five consecutive independent reviews. Once adopted, its own two
trigger conditions (same finding survives two reviews; layer accumulates three rejected reviews)
were not mechanically re-checked at the start of each new pass:

- `L08-R011` was rejected on PASS-9-final (new finding), PASS-10-final (`PARTIALLY_RESOLVED_
  BLOCKING`), and PASS-11-final (`PARTIALLY_RESOLVED_BLOCKING` again) -- three consecutive
  rejections on the exact same finding ID, meeting BOTH trigger conditions independently, but each
  pass proceeded as an ordinary point-fix rather than entering convergence. It happened to close
  cleanly on the third attempt (PASS 12), but the process got there by luck of the specific defect
  shape, not by the safeguard the project had just built for exactly this pattern.
- `L08-R014` was rejected once (PASS-13-final, `PARTIALLY_RESOLVED_BLOCKING`) -- meeting the
  "survives two independent reviews" condition on its second review (the original discovery review
  plus this one). The second remediation (PASS 14) turned out to be a narrow, no-code-change prose
  fix, so convergence would have been unnecessary overhead in hindsight, but that was not known
  in advance; the trigger was simply never checked.

**Fix:** `process/agent-workflow.md` section 11.8 now states plainly that the trigger check is
mandatory before starting a new pass on a named finding ID, not a judgment call exercised only in
retrospect, and that proceeding with an ordinary point-fix despite a met trigger requires stating
why.

### 2. A narrow fix's own prose can be locally true and globally wrong

PASS 13's `L08-R014` remediation correctly fixed the A -> run-local-B -> failure defect and wrote
prose stating the persistent model is "never reassigned in `agent.ts`" -- true, verified directly
against the file. It generalized that to "fixed/set once at construction," which is false once
the ALREADY-CERTIFIED Layer-07 section of the SAME `spec/agent.md` (adopting live, externally
mutable `AgentState.model`) is accounted for. The narrow fix never touched Layer 07, so nothing
prompted a cross-check against it.

**Fix:** `process/agent-workflow.md` section 7's warning-signs list now names this pattern
explicitly: new prose that is true in isolation but contradicts an already-certified section
elsewhere in the same document.

### 3. "The current implementation should already satisfy it" is a claim, not evidence

The PASS-13 rejection review stated the code was already correct and only the prose needed
correction. PASS 14 could have simply rewritten the prose and moved on. Instead it wrote the new
C-witness test and ran it against the UNCHANGED production code FIRST, specifically to confirm the
reviewer's own claim before reporting it as fact -- it passed immediately, which is meaningfully
different evidence than "the reviewer said so."

**Fix:** `process/agent-workflow.md` section 9.2 (reviewer witness rule) now requires the
remediation owner to run a review's own "already satisfies it" claim against the unchanged
candidate and report the confirmation directly, rather than relying on the review's own assertion.

### Not promoted to persistent guidance

Several other pass-level lessons (encoder required-vs-optional fields must be checked per-field,
not by neighboring pattern; a canonical schema widening needs matching decoder/observer widening
to be real evidence; a `rust:` manifest field can go stale silently across several passes) are
already implicitly covered by existing rules (`process/agent-workflow.md` section 8's traceability
chain, section 9's discriminating-evidence rule) and were judged too mechanically specific to
promote into new standalone rules without adding ceremony disproportionate to their recurrence so
far. They remain recorded in `assurance/layers/08-agent-loop-python.md`'s own PASS 11/12/13
retrospective sections if a future layer reopens the same category of question.
