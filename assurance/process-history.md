# Process history

A running log of workflow/process improvements distilled from layer retrospectives, per
`process/agent-workflow.md` section 14. This file records the improvement and why it was made;
the semantic/certification detail for the layer itself stays in that layer's own assurance files.

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
