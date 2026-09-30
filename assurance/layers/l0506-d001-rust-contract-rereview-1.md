# L0506-D001 — targeted R001/R002 contract re-review

**Targeted verdict: APPROVED. R001/R002 PROVISIONALLY CLOSED.** Final complete exact-SHA contract review remains pending; this targeted closure is not implementation approval, certification or merge authorization.

## Exact target / eligibility

- Code #89: `23344258c02b8d2868b756ed395b18769b2af092`.
- Docs #195: `ab09009580b57a7695c9a635935452f5ea44bb0c`.
- Pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`.
- Prior rejection: docs #196 / `5af2d1c5b0b2d012ee1ee91436d1888993724e23`, preserved unchanged.
- Accepted bases remain code `97d7c6bd98f2f07027e6ab1d057b3c7e6adab345`, docs `44858bc4abf7ff78786ab4c421db462883f78b1e`.

Fetched/pruned both repositories, verified issue #88 CONTRACT_REVIEW / NEXT_OWNER Codex and the exact OPEN/ready remote PR pair. Used separate detached candidate worktrees and a review-only branch. Local primary HEADs remain code `4301816d6ba66f3be1d5f5b4b48fdeb46f939ac0` and docs `631aaabbf07891af7f7d65c1b303f5c440d925a0`; unrelated local work preserved. Owner Option 1 provenance and accepted NaN reachability remain unchanged. No candidate production files changed.

## R001 — diagnostic serialization

**PROVISIONALLY CLOSED.** Pi validation.ts JSON.stringify projection, agent-loop.ts prepared-call handoff and the prior reviewer witness agree with the remediation. The new `declared-number-diagnostic-projection` authority case uses the actual pinned validator, recording:

```
diagnostic_arguments: {limit: null, extra: null, negativeZero: 0}
runtime_after_failure: {/limit: +Infinity, /extra: NaN, /negativeZero: -0}
```

The new normative serialization section distinguishes the successful in-memory pipeline, Pi's diagnostic-only projection, Minion's already-certified validator-error text mapping and unchanged raw ToolCall serialization. TOOL-041 matches it. Assurance explicitly supersedes the earlier decision-4 blanket claim without rewriting history. Neither the hook nor execute runs on the failure; diagnostic nulls cannot be treated as runtime values. No unrelated error-text parity reopening or new owner decision is introduced.

This corrects a documentary characterization defect; the permanent authority case and unchanged runtime-token observations discriminate diagnostic projection from a destructive runtime round-trip. The diagnostic need not become Minion's validation-error format.

## R002 — canonical forms / tokens / preflight

**PROVISIONALLY CLOSED.** The schema now requires schema/prepare_set for custom cases, forbids those fields for edit cases, requires observed for prepared outcomes (and result_text for edit success), and forbids successful observation fields for failure. Numeric token syntax is explicit. A language-neutral preflight checks exact expected observation-pointer sets and finiteness of finite literals; overflow must use a named Infinity token and cannot silently default to NaN.

Re-ran the original reviewer probe unchanged against the new pair:

| Isolated mutation | Prior reviewed schema | New schema |
|---|---|---|
| custom missing schema | ACCEPTED | REJECTED |
| custom missing prepare_set | ACCEPTED | REJECTED |
| prepared missing expect.observed | ACCEPTED | REJECTED |
| prepare_set extra = 1garbage | ACCEPTED | REJECTED |

The prior acceptance result is reproduced/preserved in #196's executable check.py evidence. Permanent candidate tests cover all four, additionally failure-with-observed, every committed case's preflight and an overflowing finite token (with largest-finite positive control). These are grammar/preflight tests, not a substitute for future production-binding negative controls. Existing canonical positive forms continue to validate.

## Fresh evidence

- Pinned Node 22.15.1-alpine execution: **27 authority cases**; actual Pi validation/edit hashes and typebox 1.3.7 SRI verified.
- Authority SHA-256: `44fc0308006b303ba9fc9a84073a178662f14e9f2690b9815cd8b368b16dc062`, byte-identical to candidate output; regenerated cases hash identical.
- Regenerated **4/4 scenario Git blobs byte-identical**: 8 edit, 7 declared-number, 6 declared-integer, 6 unconstrained cases.
- Candidate schema/manifest gates: **305 passed**, including the new negative probes and preflight tests.
- No production changes; no full-language implementation/certification counts claimed. Python C001 remains a known planned delta fix, Rust runtime representation remains not implemented, and binding-level negative controls remain future review obligations.

## Scope / process / next action

This is targeted closure after ordinary remediation, not a complete re-audit. Neither finding survived this remediation review; no new convergence trigger or lower-layer scope decision is created. The existing narrow owner-authorized delta remains the only affected surface. Historical Layer-05/06 certification elsewhere remains valid; WP-13.2 is still blocked until delta certification.

Advance #88 to **FINAL_CONTRACT_REVIEW / NEXT_OWNER Codex** on this exact unchanged candidate pair for one complete independent contract review. Preserve R001/R002 as provisionally closed and do not silently widen this verdict to later SHAs. Stop here: no merge, Python implementation, Rust implementation or WP-13.2 resumption in this pass.
