# L0506-D001 — final complete independent contract review

**Verdict: CHANGES REQUIRED.** Numeric semantics and R001/R002 corrections remain accepted. One new contract/evidence dependency finding, R003, prevents an implementation-ready checkpoint. No production implementation or merge performed.

## Exact candidate / eligibility

- Code #89: `23344258c02b8d2868b756ed395b18769b2af092`.
- Docs #195: `ab09009580b57a7695c9a635935452f5ea44bb0c`.
- Pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`.
- Accepted/default branches freshly fetched: code `97d7c6bd98f2f07027e6ab1d057b3c7e6adab345`, docs `44858bc4abf7ff78786ab4c421db462883f78b1e`.
- Local primary HEADs remain code `4301816d6ba66f3be1d5f5b4b48fdeb46f939ac0`, docs `631aaabbf07891af7f7d65c1b303f5c440d925a0`; unrelated local work preserved. Used detached candidate worktrees and a new review-only branch.
- Issue #88 FINAL_CONTRACT_REVIEW / NEXT_OWNER Codex and exact OPEN/ready PR pair verified. Owner Option 1 provenance unchanged: #49 comment `5912178299`.
- Historical rejection #196 `5af2d1c5b0b2d012ee1ee91436d1888993724e23` and targeted closure #197 `733a39a2bcc16918ef37ed1497b6226962463f20` preserved.

## Complete semantic / ownership ledger

| Surface | Result |
|---|---|
| Public preparation callback | Pi types.ts AgentTool.prepareArguments and agent-loop.ts prepareToolCallArguments support custom numeric runtime results. NaN reachability accepted under the owner's characterization rule. |
| Core edit preparation | Actual pinned edit.ts helper checked: JSON.parse rounds finite binary64, preserves -0, creates overflow infinities, rejects NaN token. |
| Prepared runtime domain | Finite binary64, signed zero, infinities and characterized custom-callback NaN coherent. Non-numeric runtime extensions remain excluded. |
| Validation | Actual pinned validateToolArguments/typebox finite-only number/integer behavior reproduced; unconstrained positions retain non-finites. The future implementation must preserve general schema constraints, not globally reject all non-finites or substitute null to fit a validator API. |
| Hook / execute handoff | Pi passes validated args in memory. Rust dedicated runtime representation can preserve these values through existing preparation/before-hook/Proceed/execute ownership without widening raw ToolCall. |
| Existing after-hook mapping | Minion's certified result/signal-only after-hook API remains unchanged; no unapproved new after-hook argument surface inferred from Pi. |
| Raw/events/session boundaries | Unchanged original arguments and serialization remain the previously certified Minion ownership mapping. No prepared-value wire widening authorized. |
| Diagnostics (R001) | Pi failure diagnostic null/null/0 projection is distinguished from untouched runtime Infinity/NaN/-0 and Minion's existing error-text mapping. R001 remains provisionally closed. |
| Canonical grammar (R002) | Explicit case/outcome forms, strict numeric-token syntax, finite-literal/pointer-set preflight and permanent malformed-case probes remain valid. R002 remains provisionally closed. |
| TOOL-041 ledger | Adopted, traceable to actual Pi sources; Python/Rust explicitly not implemented. No hidden Rust-only divergence or completed implementation claim. |
| Python C001 | Disclosed finite-number validation defect remains a planned implementation obligation, not a reason to reject the target numeric rule. Pydantic's separately certified coercion divergence stays outside redesign. |
| Binding negative controls | Seven scoped controls are future implementation-review obligations, not counted as already executed production evidence. |
| Certification dependency | Eight real-edit scenarios require a higher-layer tool absent from accepted baselines and blocked behind delta certification: R003 below. |

Re-read actual Pi preparation/validation/hook/execute paths before normative spec, manifest, schema/cases/harness, certified Rust APIs and assurance. Independent Rust can implement the numeric rule idiomatically; the new blocker is evidence staging, not an inability to design the representation.

## Fresh full-contract evidence

Replayed the actual candidate harness in pinned Node 22.15.1-alpine, checking Pi validation/edit hashes and typebox 1.3.7 lockfile/tarball SRI:

- **27/27 authority results**, byte-identical: SHA-256 `44fc0308006b303ba9fc9a84073a178662f14e9f2690b9815cd8b368b16dc062`.
- Regenerated cases hash matches; **4/4 scenario Git blobs byte-identical** (8 edit, 7 declared-number, 6 declared-integer, 6 unconstrained).
- **305 schema/manifest tests passed** freshly.
- Original four malformed schema probes still REJECTED, prior schema ACCEPTED; R002 closure not regressed.
- R001 diagnostic case still records null/null/0 and unchanged runtime values.

These are contract gates, not binding implementation certification. No full Rust/Python implementation suite claimed from a production-unchanged contract candidate.

## L0506-D001-R003 — circular production-evidence prerequisite

**Taxonomy:** CONTRACT_ASSURANCE_DEFECT. **Severity:** blocking implementation/certification plan. **Affected surface:** canonical editCase fixture rule, TOOL-041 evidence/gate staging and #88/#49 dependency coordination.

### Minimal discriminating witness

At the exact candidate code tree and accepted code/main:

```
Python tools/builtin/edit.py: ABSENT
Rust tools/builtin/edit.rs: ABSENT
prepared-runtime canonical cases: 8 real edit, 19 custom lower-layer
```

Inspection of both builtin module exports confirms the real edit tool is absent, not merely housed under another filename. Code #89 adds only contract/evidence support, not production edit implementation. The eight edit cases explicitly require:

```
the REAL built-in edit tool over a fresh root holding f.txt = "a\n"
(its own prepare_arguments, prepareEditArguments)
```

Current #49 next_action requires driving #88 to certification while preserving Python #87 **open/unmerged**, followed only then by final Python approval/merges and Rust WP-13.2 implementation. Its delta dependency explicitly says Python approval also awaits certification. The owner decision itself defers Rust WP-13.2 until delta certification.

Therefore the advertised real-tool canonical gate cannot be completed in either binding from the authorized accepted lower-layer implementation baseline:

```
delta certification needs real edit tool
real edit tool lands through WP-13.2
WP-13.2 progression waits for delta certification
```

The Pi authority's real edit preparation is valid **characterization evidence**, but it is not proof that a Minion real edit tool exists or ran. A runner that silently aliases those cases to a custom imitation, skips them as passing, or copies unmerged WP-13.2 production into the delta would break the stated real-seam/scope/baseline rules.

Read-only reproducer: [dependency_probe.py](data/l0506-d001-final-review/dependency_probe.py). It inventories exact Git trees, counts the canonical fixture forms, prints the schema rule and fetches #49's current dependency/action. Full tree/export inspection, not absence of a filename alone, establishes the missing implementation.

### Minimal correction

Make evidence ownership and certification sequencing explicit and acyclic **without weakening numeric semantics or pretending a simulated edit is production**. A narrow solution is:

- make lower-layer certification depend on real generic preparation/validation/hook/execute witnesses available independently of built-in edit (including string-to-runtime overflow/rounding/-0 where required);
- preserve the eight real-edit authority/scenario witnesses, but explicitly assign their Minion integration gate to WP-13.2 after the delta has certified, with a precise trigger and no false executed/deferred-as-passed count;
- update spec/manifest/assurance/protocol and current coordination consistently so the delta runner has an unambiguous discovery/filter policy.

Equivalent acyclic staging is acceptable. If instead the proposal changes the owner's condition to implement Rust WP-13.2 before delta certification, obtain separate owner governance; do not infer that permission from this review. No runtime redesign or new production work is requested in this contract remediation.

## Outcome / process

R001/R002 closures preserved; one new contract-readiness blocker R003. No new PI_PARITY_DEFECT or PI_BEHAVIOR_UNCERTAIN. Known C001 remains the forthcoming Python obligation. Historical Layer-05/06 certification outside this numeric delta remains valid.

This is the second rejected complete review for this work package, with a new finding rather than failed numeric remediation. No automatic repeated-finding/three-rejection convergence trigger has fired. Require focused evidence-staging characterization and targeted remediation, not another broad implementation pass.

Return #88 to **CONTRACT_DRAFT / NEXT_OWNER Claude** for the narrow R003 staging correction. **AGREED FOR IMPLEMENTATION is not recorded yet.** No contract merge, Python/Rust delta implementation, WP-13.2 resumption or later work performed by this review.
