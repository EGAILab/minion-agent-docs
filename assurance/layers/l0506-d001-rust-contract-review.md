# L0506-D001 — independent exact-SHA contract review

**Verdict: CHANGES REQUIRED.** Two CONTRACT_ASSURANCE_DEFECT findings below. NaN reachability (draft decision 1) is supported; no new owner decision or semantic divergence is requested. Review only: no production repairs, implementation, certification or merge.

## Target / starting state / provenance

- Code #89: `1ba82addf2b9e086018b1f50c07aff1c83870316`, OPEN / ready, base main.
- Docs #195: `640d74c640d7ad4b9144149f4e8ad959578cdbbb`, OPEN / ready, base master.
- Accepted bases: code `97d7c6bd98f2f07027e6ab1d057b3c7e6adab345`, docs `44858bc4abf7ff78786ab4c421db462883f78b1e`.
- Local primary HEADs: code `4301816d6ba66f3be1d5f5b4b48fdeb46f939ac0`, docs `631aaabbf07891af7f7d65c1b303f5c440d925a0`. Preserved existing untracked work; used clean detached candidate worktrees and separate review branch.
- Pinned Pi `b7bb00b936dbe21b8e160b3e89efdec361846699` verified.
- Issue #88 CONTRACT_REVIEW / NEXT_OWNER Codex and exact paired heads verified after fetch/prune.
- Owner Option 1 verified from [durable verbatim provenance](https://github.com/EGAILab/minion-agent/issues/49#issuecomment-5912178299): scoped preparation/validation/argument-observation/execute domain delta; raw wire unchanged; no Infinity-null runtime projection or Rust-only divergence.

Read role/workflow/coordination and post-certification-delta rules. Audited Pi before the candidate normative spec, TOOL-041 manifest, canonical schema/evidence, certified Rust architecture and assurance. Python inspected last as secondary evidence.

## Pi mapping and draft decisions

| Boundary | Independent source result / review |
|---|---|
| AgentTool.prepareArguments | Public callback in `packages/agent/src/types.ts:393`; `agent-loop.ts:586–597` invokes it without a finite-only restriction. A custom callback can return NaN; this is a real public Pi seam, not an invented engine state. **Decision 1 accepted.** |
| Core edit preparation | `edit.ts` JSON.parse produces rounded binary64, signed zero and overflow infinities, not NaN. Copied helper checked against actual pinned body. |
| Validation | Actual `packages/ai/src/utils/validation.ts::validateToolArguments` clones the prepared input and uses pinned typebox 1.3.7. Declared number/integer reject non-finites; unconstrained extra positions retain them. |
| Before hook / execute | `agent-loop.ts:617–655,679` passes validated runtime args to beforeToolCall and execute, without a JSON round-trip. Dedicated Rust runtime values can implement this idiomatically. |
| After hook | Pi finalizeExecutedToolCall also passes prepared.args. Existing certified Minion after-hook API projects result/signal, not arguments (Rust AfterToolCallContext and current normative spec). This review does **not** silently enlarge that separately certified API. |
| Events / raw domain | Existing original-argument ownership and serialization contracts are preserved, not widened to non-finite wire JSON. In-place Pi preparation versus Minion original-input preservation remains the existing architectural mapping. |
| Diagnostic serialization | Pi validation failure explicitly JSON.stringify's **prepared** toolCall.arguments. This is missing from the draft's characterization; R001 below. |
| Python C001 | Independently reproduced real execute_call: declared number accepts inf/-inf/nan and hook/execute run; declared integer rejects them; -0 and 1e308 survive. This is a disclosed planned implementation fix within the authorized delta, **not an undisclosed implementation claim**. |
| Pydantic | Existing coercion divergence remains separate; new finite-only validation rule must not accidentally normalize unconstrained non-finites or signed zero. No unrelated model-coercion redesign requested. |

TOOL-041 is a coherent adopted parity correction, with both implementations explicitly planned/not implemented. Rust PrepareArguments, PreparedToolCall, BeforeToolCallContext/Proceed and ToolExecutionRequest currently use serde_json::Value; these are the narrow seams needing the future dedicated runtime domain, not a reason to change raw Layer-02 ToolCall. Historical Layer-05/06 certification outside this surface stands.

## Fresh replay / gates

- Pinned `node:22.15.1-alpine` authority: **26/26 cases**, actual Pi file hashes and typebox 1.3.7 lockfile/tarball SRI verified.
- `authority.json` SHA-256 `53ea011765753a0d9a3f679885dbb0f00e96aeb65fe99a0a84805ed17ba2474b`: byte-identical to candidate; regenerated cases hash matches.
- Generated **4/4 scenario Git blobs byte-identical**, 8 edit + 6 declared number + 6 declared integer + 6 unconstrained cases. Compared repository blobs to avoid checkout newline conversion masquerading as a semantic difference.
- Candidate schema/manifest test files: **298 passed**. These validate positive fixtures but do not catch the malformed shapes below.
- Production source is unchanged by both PRs. No full-language certification gate is claimed from this contract-only review. The secondary Python characterization uses the unchanged certified execution source; current observed C001 agrees with draft disclosure.
- Owner's seven required negative-control categories are listed as **future implementation-review obligations**, not falsely counted as executed/mutant-killed evidence at this contract stage.

Durable reviewer probes: [data/l0506-d001-review](data/l0506-d001-review/README.md).

## L0506-D001-R001 — missing existing prepared-value diagnostic serialization

**Taxonomy:** CONTRACT_ASSURANCE_DEFECT. **Severity:** blocking contract coherence. **Affected text:** spec/tools.md TOOL-041 "Serialization boundary"; TOOL-041 manifest "No serialization projection is defined by Layer 06" where supported by the blanket no-serialization assertion; contract assurance decision 4.

Pi's validation.ts constructs its failure message with `JSON.stringify(toolCall.arguments, null, 2)`. agent-loop.ts passes the **preparedToolCall**, not the original raw call, to that function. The draft says "Layer 06 serializes no prepared value" and omits this already-present serialization from its boundary characterization.

Minimal setup: prepared `{limit: Infinity, extra: NaN, negativeZero: -0}` with declared number limit. Actual pinned validator rejects and its Received arguments diagnostic is:

```json
{
  "limit": null,
  "extra": null,
  "negativeZero": 0
}
```

The original runtime values remain Infinity/NaN/-0, proven by the same executable probe. This distinguishes **diagnostic** projection from runtime corruption; it does not authorize null-mapping hook/execute values. No hooks or execute run on validation failure.

**Minimal correction:** characterize this actual Pi diagnostic boundary and distinguish it from the unchanged successful in-memory path. State how the existing certified Minion validation-error mapping applies; the draft already says error text is Layer 06's own, so do not opportunistically reopen all validation-message parity. Correct the blanket claim consistently in spec/manifest/assurance. Preserve raw serialization and runtime-value rules. Add a permanent diagnostic-versus-runtime characterization witness. No new owner decision needed.

## L0506-D001-R002 — canonical grammar accepts undispatchable / unasserted cases

**Taxonomy:** CONTRACT_ASSURANCE_DEFECT. **Severity:** blocking canonical contract completeness. **Affected surface:** prepared-runtime-scenario.schema.json and its scenario protocol.

Starting from the valid undeclared custom case, each isolated mutation below is **accepted by the candidate schema**:

1. Delete `schema`: no number/integer/open fixture is selected.
2. Delete `prepare_set`: no prescribed runtime preparation is supplied.
3. Delete `expect.observed` for outcome prepared: the numeric observation oracle disappears.
4. Replace the extra value token with `1garbage`: regex accepts it although it denotes no valid finite numeric token; JS Number would produce NaN, while a strict Rust parser may reject it.

The actual schema comment defines schema and prepare_set as the custom-tool fixture and observed as the successful hook/execute oracle, but does not require them or define omissions/defaults. A Rust runner must guess a default, reject independently, or simulate missing semantics. These are different observations allowed by the current schema/protocol. Existing four well-formed documents remain valid; this finding does not allege their positive expectations are wrong.

**Minimal correction:** make custom/edit and prepared/failure forms explicit and enforce required/forbidden dependent fields. Define a strict shared numeric token grammar; do not silently treat malformed finite tokens as NaN. Require the expected pointer observations needed to assert each successful case (a shared preflight can enforce pointer-set consistency). Add automated negative probes for the exact four mutations and positive tests for existing forms. Runner preflight, if used for cross-field checks, must be specified language-neutrally. No new runtime behavior or production implementation in this remediation.

## Outcome / next action

First independent contract review for this work package: neither finding has survived a remediation review, and the delta does not inherit a fictitious rejection count from WP-13.2. Finite documentary/protocol corrections, no disputed numeric semantics; normal targeted remediation is appropriate. Do not start a broad implementation or whole-layer reopening.

Return #88 to **CONTRACT_DRAFT / NEXT_OWNER Claude** for R001/R002 corrections; re-review the exact resulting remote pair. C001 remains the known planned Python fix. WP-13.2 remains blocked. L0506-D001 shared contract **not approved yet**; Python/Rust delta **NOT_IMPLEMENTED**; delta cross-language **NOT CLOSED**. No production edits or merges performed.
