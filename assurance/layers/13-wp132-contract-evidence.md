# WP-13.2 contract evidence candidate

- **Coordination:** `minion-agent#49`.
- **Governance:** `standing_delegation: minion-agent#75`; `scope_extension:` the Owner decision "Finish Layer 13 Under Delegation" (`#75`), and owner decisions `L13-WP132-O1`/`O2` (`#49` comment `5881558193`).
- **State:** CONTRACT_DRAFT → CONTRACT_REVIEW. This record requests the independent contract-plus-evidence review. It is not an implementation authorization.

## What this adds

The contract text (`spec/tools.md` WP-13.2) was checkpoint-approved after remediation `R001`–`R003` (Codex's re-review, `minion-agent-docs#183`). That approval deferred the differential corpus, queue interleavings, canonical scenarios and negative controls to this pass. This pass delivers them:

| Spec witness item | Evidence |
|---|---|
| 1. `edit` authority corpus | `data/13-wp132-evidence/`. Pinned-Pi authority over 379 deterministic cases, in the pinned runtime, with the SRI-checked `diff` 8.0.4. |
| 2. canonical `write`/`edit` scenarios | `minion-agent` `conformance/agent/builtin-mutation/`: 8 corpus documents (374 cases, generated) and 7 hand-authored case documents (42 cases); 373 and 43 after remediation 1 (below). The shape is `builtin-mutation-scenario.schema.json`. |
| 3. queue witnesses | 11 queue scenarios, each citing the pinned `file-mutation-queue.ts` trace (9 traced scenarios) whose ordering it asserts. |
| 4. negative controls | Corpus half: 13/13 single-point Pi-source mutants killed. Binding half: listed in the spec's evidence inventory; runs at each implementation review. |

Contract text changes are limited to the witness section:
- the evidence inventory;
- the INTERNAL finding below.

No rule changed.

## Finding: `L13-WP132-E001`, INTERNAL line-count guard reachable

- **Classification:** `PI_BEHAVIOR_UNCERTAIN`, resolved by characterization. There is no contract defect.
- **What was open.** The contract said the two INTERNAL guards are "reproduced if reached", and that the corpus looks for inputs reaching them.
- **What the corpus found.** It reaches both guards:
  - `range`: an empty file whose `oldText` is only whitespace;
  - `line count`: under fuzzy mode, a file ending in a whitespace-only line without `"\n"`. That line trims to nothing and `lines()` drops it, so the base has one line fewer.
- **Consequence.** A benign edit therefore fails with Pi's internal text: `"a’\n   "` with `oldText` `"a'"`, and a CRLF variant.
- **Checked and excluded.** Separately, NFKC under the pinned runtime never changes the `"\n"` count at any of the 1,112,064 scalar values. That source of mismatch is ruled out.
- **Disposition.** `DIRECT_PI_PARITY`, reproduced as is. The spec now states it. No Owner item: this is the contract's existing rule, now witnessed.

## Additive changes outside the spec

- **New canonical shape.** `builtin-mutation-scenario.schema.json` lives in its own directory, `conformance/agent/builtin-mutation/`. The WP-13.1 `builtin_tool` runners in both languages glob only `conformance/agent/*.yaml`, so they are unaffected.
- **Python schema validation.** `test_schema_validation.py` validates the new directory against the new shape.
- **Manifest.** `TOOL-029`..`TOOL-033` name their concrete witnesses in place of the placeholder. Their status is unchanged: CONTRACT_DRAFT, python and rust `not implemented`.
- **Rust.** Rust schema validation and runner support for the new directory belong to the Rust implementation, and are not part of this pass.

## Reviewer checklist

1. Reproduce `out/authority.json`, `out/mutants.json` and `out/queue_authority.json` byte for byte with the README's commands. Then regenerate the scenario directory and compare it byte for byte.
2. Check that every hand-authored expectation (error sites, FALLBACK, cancellation, queue) follows pinned `write.ts:201-233`, `edit.ts:332-386`, `file-mutation-queue.ts` and the contract's templates:
   - the recorded `fs_calls` sequences;
   - the abort-versus-own-error precedence;
   - the in-lock `absolute_path` (R001);
   - the fallback keys, including `not_directory`, which is not `resolve()`.
3. Check that the queue shape's runner protocol is implementable deterministically in both bindings:
   - gates;
   - quiescence;
   - ordering constraints;
   - the pending-call failure.

   Each asserted order must be forced by gates, not by scheduler luck.
4. Check the `unpaired_surrogate_arguments` rule against String semantics (Layer 02/05 hazard recorded, not resolved).
5. Check that the listed binding-level negative controls are killable by the corpus and queue scenarios as written.

## Status

- `WP-13.2 contract + evidence`: READY FOR INDEPENDENT CONTRACT REVIEW (candidate SHAs in `minion-agent#49`).
- `Python WP-13.2`: NOT_IMPLEMENTED. It starts only after the contract review approves.
- `Rust WP-13.2`: NOT_IMPLEMENTED.
- Final `edit` certification also waits on `EXEC-009` (`minion-agent#79`).

## Remediation 1: `L13-WP132-R004`, `L13-WP132-R005`

**Trigger.** Codex's independent contract+evidence review rejected the candidate (code #81 @ `29d5b772`, docs #178 @ `ea8ddb24`), recorded in `minion-agent-docs#187` @ `02f8a7a1`.

- Its byte-exact replay of every evidence output and all 26 scenario blobs matched.
- The 13/13 mutants and the queue determinism audit were confirmed.
- Two blocking `CONTRACT_ASSURANCE_DEFECT`s were found at the canonical entry boundary.

Both are accepted.

### `L13-WP132-R004`: ACCEPTED

**Defect.** Tool-local pre-abort evidence contradicted the required Layer-06 entry.

**Cause.** Pi's `agent-loop.ts` `prepareToolCall`, like certified Layer 06 in both bindings, answers an already-aborted signal before invoking `execute`. The candidate's `pre_aborted` cases expected the tool's own register-before-check trace through that pipeline. That trace is unreachable there.

**Correction.**
- **Preflight witness.** Each tool keeps one `pre_aborted` case, now expecting Layer 06's answer: `"Operation aborted"`, `fs_calls: []`, file untouched. The schema's `signal` comment states this.
- **Tool-level rule, rewitnessed after preflight.** The rule is: no check before the lock; registration, including fallback-key derivation, completes; the answer comes after the lock is acquired. It is now witnessed with an abort that arrives after preflight:
  - `write`/`edit` `abort-during-registration` (`abort_after: canonical_path`);
  - `write` `abort-during-registration-still-derives-fallback-key`;
  - the queue scenario `released-after-error-and-after-abort`. There, B is aborted by a step while it waits in the queue, instead of being pre-aborted. B keeps its place, answers only after the lock, and never reaches its in-lock steps.
- **Schema.** Queue calls no longer accept `signal`. Every call starts live and passes preflight.
- **Spec.** The TOOL-033 "Cancellation" rule now distinguishes the tool's direct `execute` semantics from the Layer 06 boundary. Witness item 2 is updated to match.
- **No change** to Layer 06, to the tools' semantics, or to how the runner handles the signal.

### `L13-WP132-R005`: ACCEPTED

**Defect.** A non-object raw argument cannot enter the object-valued `ToolCall` pipeline.

**Correction.**
- `prepare-not-an-object` is no longer generated as a canonical integration case. It stays in the authority corpus as `prepareEditArguments` helper evidence.
- The schema's case `arguments` is now `type: object`, with the reason stated.
- The spec's `prepareEditArguments` subsection states the entry-domain constraint. It does not widen any lower-layer vocabulary.

### Result

- The corpus scenarios now carry 373 cases; the hand-authored documents carry 43 (the edit cancellation document gained `abort-during-registration`). There are still 26 documents.
- All 26 validate against the schema.
- The authority, mutant and queue outputs are unchanged (byte-identical; `cases.sha256` unchanged). Only `make_scenarios.py` and its outputs changed.

### Dependency update

`EXEC-009` is now CERTIFIED_CLOSED (`minion-agent#79`; closure record `12-wp12e3-closure.md`). The final-`edit`-certification dependency above is satisfied.

## Remediation 2: `L13-WP132-R004` refinement

**Trigger.** Codex's targeted re-review (`minion-agent-docs#188`) closed `R005`, accepted the `R004` entry correction, and kept `R004` open on one missing assertion.

**The gap.** `builtin-mutation-queue-released-after-error-and-after-abort` said that B answers only after acquiring the lock, but no assertion ordered `result B` against A's held write. A queue-wait abort listener that rejects B early passed every existing assertion. Codex's probe (`data/13-wp132-r004-review/r45_queue_probe.mjs`) shows this against the pinned queue source.

**Accepted and corrected.** Added the gate-forced order pair `["p write_file f.txt #1 permission_denied", "result B"]`. A's write is held until the release step, so the pair is forced in a correct implementation.

**Independent replay by Claude.** The probe in `node:22.15.1-alpine` against pinned Pi `b7bb00b9` gives:
- pinned queue: A's write settles, then `result A`, then `result B`;
- abort-race mutant: `result B` comes before A's write settles.

The new assertion therefore passes on the pinned queue and fails on the mutant.

**Scope.** This is the only change: one scenario document (via `make_scenarios.py`). All 26 documents validate. The authority outputs are unchanged.
