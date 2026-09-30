# WP-13.2 R004 targeted exact-SHA closure review

## Verdict

**APPROVED — TARGETED FINDING CLOSURE ONLY.** `L13-WP132-R004` is CLOSED at code PR #81 `61b18f377c926bb09df97994ce91901cad37ed68` and docs PR #178 `2e520b19b2b33885def09246861178f89946fadc`. R005 and R001-R003 closures are preserved. No active finding remains from these reviews; this targeted result is not final complete contract approval, merge authorization, or implementation certification.

Pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`. Prior targeted rejection: docs #188, `f2031748a832bb1ef658441be4af065d941b429e`; reviewed prior code `0770ec7038e9ac1182175b24896f60fb734835d4`, docs `a53ae1c54051dfd0cfa029d7a6defd2c5a41659c`.

## Remote and scope verification

Fetched/pruned both repositories, independently verified #49 `CONTRACT_REVIEW / NEXT_OWNER Codex`, both PRs open, Ready for Review and unmerged at the requested heads. Detached candidate worktrees preserved unrelated local work. Fetched defaults remain code/main `d3c591a83759caf3cff26c62f1690781d2b08439`, docs/master `148e71938ce3f1558eaf3155049a710a2b393c7a`; the evidence branch starts from the latter. Rechecked candidate heads unchanged before publishing.

The complete diff from the preceding reviewed pair is:

- code: exactly one order pair, three YAML lines, in `builtin-mutation-queue-released-after-error-and-after-abort.yaml`;
- docs: matching generator pair/comment and append-only Remediation 2 assurance section;
- no production code, manifest, schema, normative rule, authority output or other scenario changed.

## R004 refined witness

The added pair is exactly:

```yaml
- ["p write_file f.txt #1 permission_denied", "result B"]
```

It requires A's held write to settle before the waiting aborted B answers. It does not impose a language-scheduler-dependent ordering between `result A` and `result B`. All prior assertions remain.

Independently replayed the durable #188 probe `data/13-wp132-r004-review/r45_queue_probe.mjs` under `node:22.15.1-alpine` against the pinned source, then loaded the **actual** old and new scenario YAML and evaluated each scenario's own `expect.order` pairs over both traces. This does not rely on Claude's reported result or merely on the probe's separate `requiredLockTiming` flag.

| Source/control | Prior candidate order assertions | Current candidate order assertions |
|---|---|---|
| pinned queue | PASS | PASS |
| early-answer abort-race mutant | PASS | **FAIL**, added A-settlement-before-B-result pair |

Original trace suffix: `write A permission_denied, result A, result B, absolute_path C start, result C`.

Mutant trace suffix: `result B, write A permission_denied, result A, absolute_path C start, result C`.

The negative control is the previously recorded realistic mutation of the real pinned queue wait: race its predecessor wait with B abort and release B's entry on rejection. It preserves the scripted result text and final-file outcome while violating B's answer timing. A's gate plus quiescence forces the distinction. The current assertion kills it, closing the missing-evidence dimension without changing tool/queue semantics or Layer-06 preflight.

## Fresh gates

- Regenerated all 26 scenario documents using the current exact generator and unchanged pinned authority outputs; **26/26 committed Git blobs byte-identical**. Counts remain 373 generated cases, 43 hand-authored cases, 11 queue scenarios, five fuzzy-normalization fixture cases.
- Candidate source explicitly selected on PYTHONPATH; `pytest tests/conformance/test_schema_validation.py tests/conformance/test_manifest_validation.py -q -o addopts=`: **292 passed**.
- No Rust implementation/certification or full Python certification gates claimed: this is a contract-evidence closure review.

The preflight/direct-execute distinction and object-valued integration boundary established in Remediation 1 remain untouched. EXEC-009/#79 remains independently verified CERTIFIED_CLOSED. R001-R003 and R005 remain closed; no new `PI_PARITY_DEFECT`, `CONTRACT_ASSURANCE_DEFECT`, or `PI_BEHAVIOR_UNCERTAIN` was found in the targeted scope.

## Next gate

Record R004 targeted closure at this exact pair, clear its active blocker, and retain #49 for **one final complete independent exact-SHA contract review**, with `NEXT_OWNER Codex`. Do not infer final work-package approval from this narrow review. The explicit narrow-point-fix exception documented in #188 is now satisfied; do not reopen a characterization mechanism or expand this closure pass into implementation.

Python WP-13.2: NOT_IMPLEMENTED; Rust WP-13.2: NOT_IMPLEMENTED; cross-language NOT CLOSED. No candidate merge, production implementation or Layer 14 work performed or authorized.
