# WP-13.2 R004/R005 targeted independent Rust re-review

## Exact target and result

**CHANGES REQUIRED — R005 CLOSED; R004 PARTIALLY RESOLVED / STILL OPEN.** No new finding ID, semantic repair, or implementation was introduced.

- Code PR #81: `0770ec7038e9ac1182175b24896f60fb734835d4`.
- Docs PR #178: `a53ae1c54051dfd0cfa029d7a6defd2c5a41659c`.
- Pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`.
- Previous reviewed pair: code `29d5b772a7df165e528bf97cbe380b23d32ec6ab`, docs `ea8ddb24a654ff68182474481adc65187c497c16`; rejection docs #187 at `02f8a7a1b20014e51860e22efe53fcf74d68af13`.
- Issue #49 independently verified `CONTRACT_REVIEW / NEXT_OWNER Codex`; both candidate PRs open, Ready for Review, unmerged, exact heads unchanged on publication.

Fetched/pruned both repositories and fetched both PR refs. Used detached candidate worktrees, preserving unrelated local work. Fetched defaults were code/main `d3c591a83759caf3cff26c62f1690781d2b08439`, docs/master `148e71938ce3f1558eaf3155049a710a2b393c7a`; the review-only branch starts at the latter. Issue #79 is closed with EXEC-009 `CERTIFIED_CLOSED`; code #83 and docs #184 are merged at `8a2a39481f3613d3caea7d23048b518e05931bc0` and `6bbfccf63f5a55a3bbefc186d72314f2cfe35806`. That dependency is no longer blocking WP-13.2, and was not reopened/re-reviewed here.

## Scope and independent checks

Read the Remediation 1 record, every code/docs delta from the previously reviewed pair, schema comments, and revised scenarios. Rechecked pinned `agent-loop.ts::prepareToolCall` against tool-local `write.ts`/`edit.ts` and `file-mutation-queue.ts`, plus certified Minion Layer-06 preflight and Rust `ToolCall.arguments`.

Exact change inventory:

- Code: four scenario documents and `builtin-mutation-scenario.schema.json` only. No production files or manifest changed.
- Docs: spec boundary/evidence prose, README counts, append-only Remediation 1 record, and `make_scenarios.py` only. Cases, source pins, authority/mutant/queue output files unchanged.
- Regenerated all 26 documents with the new generator against the previously independently replayed, unchanged authority outputs. All **26 Git blobs** match byte for byte. Canonical case counts now 373 generated + 43 hand-authored, plus 11 queue scenarios. The non-object helper authority result remains preserved.
- Fresh `pytest tests/conformance/test_schema_validation.py tests/conformance/test_manifest_validation.py -q -o addopts=` with candidate src on PYTHONPATH: **292 passed**.
- Schema negative controls: the prior schema accepts a raw-string case and a queue call with `signal: pre_aborted`; the new schema rejects both. This is direct RED/GREEN structural evidence against the exact previously rejected schema, not claimed production execution of unimplemented tools.

Prior R001/R002/R003 results remain intact: in-lock absolute path, factored preprocessing, global registration until earlier success/failure settlement. No new complete audit was substituted for the requested targeted review.

## R005 — CLOSED at this exact pair

The integration domain is now object-valued. `prepare-not-an-object` is removed only from generated integration scenarios and remains in the pinned helper authority corpus. Spec states that a direct prepare callback still reproduces the defensive non-object branch. Rust can implement this through its real prepare callback without widening `ToolCall.arguments`, wrapping malformed inputs, or synthesizing a Layer-06 schema result in the runner. The generator, schema, canonical expectations and disclosure agree.

## R004 — entry mismatch resolved; answer-timing proof still missing

The pre-aborted write/edit cases now expect zero fs calls through certified Layer-06 preflight. Registration-abort cases start live and abort after `canonical_path` hands back, including fallback-key completion; these conform to the real entry and preserve the tool-local checkpoints. The queue call B likewise starts live and is aborted by a step after quiescence while A's write gate remains held. No concealed signal retiming or lower-layer change is required.

The remaining defect is in `builtin-mutation-queue-released-after-error-and-after-abort.yaml`: its prose claims B **answers only after acquiring the lock**, but its order assertions do not constrain `result B` relative to A's held write. They only require:

```text
canonical_path B ok < result A
write A permission_denied < absolute_path C start
absolute_path B NEVER
final results: A error, B Operation aborted, C success
final file: C
```

Those assertions allow B to answer before A releases. A realistic queue-wait abort listener can reject B's caller immediately, release B's slot, and still leave C's tail chained behind A. It violates the required B answer timing without changing C's ordering or final data.

**Classification:** `CONTRACT_ASSURANCE_DEFECT`, blocking, refined R004 (not a new finding).

### Fresh discriminating reproduction

Permanent review probe: `data/13-wp132-r004-review/r45_queue_probe.mjs`. Run:

```text
docker run --rm -v <pinned Pi>:/pi:ro -v <review data/13-wp132-r004-review>:/probe:ro node:22.15.1-alpine node --disable-warning=ExperimentalWarning --experimental-strip-types /probe/r45_queue_probe.mjs
```

It executes the pinned queue source with scripted realpath answers and critical-section gates (the same seam as the candidate authority). The known-bad control replaces only waiting for `currentQueue` with an abort race that releases that waiting entry on rejection. A is held, B registers behind A, C registers behind B; abort B, then release/fail A. Scripted critical-section results and final file projection are identical. The probe is a **negative-control characterization**, not a replacement production runner and not evidence that nonexistent write/edit tools have passed.

Fresh observed result:

| Queue | Current scenario assertions | Required `write A settled < result B` |
|---|---|---|
| pinned original | PASS | PASS |
| abort-race mutant | PASS | **FAIL** |

Original suffix: `write A permission_denied, result A, result B, absolute_path C start, result C`.

Mutant suffix: `result B, write A permission_denied, result A, absolute_path C start, result C`.

The probe asserts both rows so replay fails if it no longer discriminates. No nondeterministic sleep is used: the held A gate and event-loop draining force the phase separation.

### Minimal correction

Add the exact required event-order assertion:

```yaml
order:
  # preserve the existing pairs
  - ["p write_file f.txt #1 permission_denied", "result B"]
```

The existing expected B result already requires B to settle. Do **not** require `result A < result B`: the contract is lock-release/operation settlement order, not caller-result scheduling order. Regenerate the scenario, retain all existing assertions, and show this realistic early-answer control fails while the pinned behavior passes. No production implementation or semantic redesign is needed.

## Trigger check and handoff

R004 has now survived two independent reviews, so workflow §11.8 trigger A **has fired**. The work package has three rejected reviews counting this targeted rejection, so trigger C has also fired. This review invokes the workflow's explicit narrow-point-fix exception rather than another convergence episode: the remaining semantic rule is agreed and fully characterized; one missing order pair closes the evidence hole, with a concrete known-bad mutant above. There is no unresolved semantic breadth or new architectural mechanism to design. State that exception explicitly before remediation; do not silently ignore the thresholds.

Return #49 to `CONTRACT_DRAFT / NEXT_OWNER Claude` for that single R004 assertion and RED/GREEN evidence, then targeted closure at refreshed exact heads. R005 is closed at the reviewed pair; preserve R001-R003. No merge or WP-13.2 production implementation is authorized by this review. Rust WP-13.2 remains NOT_IMPLEMENTED/BLOCKED, Python WP-13.2 NOT_IMPLEMENTED, cross-language NOT CLOSED; no Layer 14 work.
