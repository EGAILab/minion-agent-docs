# L0506-D001 contract draft: prepared runtime numeric domain (`TOOL-041`)

- **Coordination:** `minion-agent#88`.
- **Governance:** Owner decision `L13-WP132-I004`, Option 1 (`minion-agent#49` comment `5912178299`), which authorizes this scoped post-certification delta; `standing_delegation: minion-agent#75`.
- **State:** CONTRACT_DRAFT → CONTRACT_REVIEW.

## What this delivers

| Deliverable | Where |
|---|---|
| contract text | `spec/tools.md`, Layer 06, "Prepared runtime numeric domain (`TOOL-041`, post-certification delta `L0506-D001`)" |
| manifest row | `minion-agent` `pi-parity-manifest.yaml` `TOOL-041` (CONTRACT_DRAFT; Python and Rust not implemented) |
| canonical witnesses | `minion-agent` `conformance/agent/prepared-runtime/`: 4 documents, 26 cases, shape `prepared-runtime-scenario.schema.json` (own directory, so existing runners are unaffected), plus Python schema validation of it |
| authority and characterization | `data/l0506-d001/` (see its `README.md`) |

## Decisions made in the draft (for the independent review)

1. **NaN is in the prepared runtime domain.** Core preparation cannot produce it, but a tool's own `prepare_arguments` can, and pinned Pi's validator keeps NaN in an undeclared key and the hook observes it. This follows the Owner rule (§4): include only values authoritative Pi behavior can produce at this boundary.

   If the review judges that the custom-shim path should not count as "authoritative Pi behavior", this is the point to challenge. It would then become a genuine semantic choice for the Owner.
2. **Declared `number`/`integer` are finite-only.** This is pinned Pi's validator behavior, and JSON Schema's own data model agrees. Certified Python currently diverges, as finding `L0506-D001-C001` (the `jsonschema` library's `number` admits non-finite floats). Its fix belongs to this delta's Python implementation, not to this contract pass.
3. **Scope limits.**
   - Non-numeric runtime values a shim could return stay out of scope.
   - Pydantic-model parameters get the finite-only rule. Pydantic's own int coercion of `-0.0` to `0` is pre-existing and disclosed under the certified pydantic divergence, and is not changed here.
4. **Serialization.** No projection is defined. Layer 06 serializes no prepared value, and raw `ToolCall` serialization is unchanged.

## Reviewer checklist

1. Reproduce `out/authority.json` and the scenario directory byte for byte (README).
2. Check the characterization, especially Pi's validator on declared versus undeclared positions, and that `JSON.parse` cannot produce NaN.
3. Check the scope boundary: raw arguments, `tool_execution_*` original arguments and serialization are unchanged, and no whole-layer reopening.
4. Check the NaN reachability classification, decision 1 above.
5. Check the negative-control list against the Owner decision §8.

## Status

- `L0506-D001` contract: READY FOR INDEPENDENT CONTRACT REVIEW.
- Python: NOT_IMPLEMENTED, with known defect C001.
- Rust: NOT_IMPLEMENTED.
- `WP-13.2` (#49) stays blocked on this delta for Python approval, Rust implementation and closure.

## Remediation 1: `L0506-D001-R001`, `L0506-D001-R002`

**Trigger.** Codex's independent contract review (`minion-agent-docs#196`) requested changes. It accepted decision 1 (NaN reachability) and reproduced the authority and scenario blobs byte for byte. Both findings are accepted.

### `L0506-D001-R001`: Pi's diagnostic serialization

**The defect.** The draft's blanket statement "Layer 06 serializes no prepared value" missed a serialization: Pi's validation-failure text uses `JSON.stringify(preparedToolCall.arguments, null, 2)`.

**The fix.**
- The spec's serialization boundary now distinguishes:
  - the in-memory successful path, where nothing is serialized;
  - Pi's failure diagnostic, a projection of ±Infinity and NaN to `null` and `-0` to `0`, with the runtime values unchanged;
  - Minion's `TOOL-003` validator text, which is its own. Text parity is not reopened.
- The manifest `TOOL-041` rule is corrected to match. Decision 4 above is superseded by this.

**Witness.** The authority now records, for every failure, `diagnostic_arguments` (Pi's serialization) and `runtime_after_failure` (the untouched runtime values). A new case, `declared-number-diagnostic-projection`, prepares `{limit: +Infinity, extra: NaN, negativeZero: -0}`:
- diagnostic: `{"limit": null, "extra": null, "negativeZero": 0}`;
- runtime: `+Infinity`, `NaN`, `-0`.

The authority now has 27 cases, and the declared-number document 7.

### `L0506-D001-R002`: the canonical grammar

**The fix.** `prepared-runtime-scenario.schema.json` now has:
- explicit `editCase` and `customCase` forms, with `schema` and `prepare_set` required on custom and forbidden on edit;
- prepared and failure expectation forms, with `observed` required on prepared (and `result_text` on edit), and `observed` forbidden on failure;
- a strict token grammar: the four named tokens, or a finite JSON number literal;
- a stated language-neutral PREFLIGHT: observed pointers exactly equal `observe`, and a finite literal must be finite. A violation fails the document and is never defaulted.

**Tests** (Python schema validation):
- each of the review's four mutations (missing `schema`, missing `prepare_set`, prepared without `observed`, `1garbage`), plus failure-with-`observed`, is **rejected**;
- the preflight holds for every committed case;
- an overflowing "finite" literal fails the preflight.

**Scope.** No production code changes.

## Remediation 2: `L0506-D001-R003`, acyclic evidence staging

**Trigger.** Codex's final complete review (`minion-agent-docs#198`) kept R001 and R002 closed, and found that the eight real-`edit` cases made delta certification depend on WP-13.2. WP-13.2 itself waits for this delta. Accepted.

**The fix.**
- **Schema.** Every document now requires a `gate`, either `L0506-D001` or `WP-13.2`. A delta-gated document may hold only `custom` cases, which the schema enforces. The top-level comment states the filter policy: explicit selection by `gate`, and never a skip, alias or simulation.
- **Documents.** The three custom documents (19 cases) are gate `L0506-D001`. The real-`edit` document (8 cases) is gate `WP-13.2`, with a note on its trigger. The generator writes the gate.
- **Spec.** A new "Evidence staging" paragraph gives the two gates, the trigger for the `WP-13.2` gate, and the acyclic order.
- **Manifest.**
  - `TOOL-041`'s tests name only the three delta-gated documents as its certification witness, and list the `edit` document as a WP-13.2-gated integration witness that is not part of this row's certification.
  - `TOOL-030` gains `edit_prepared_runtime_numbers`, the gate-`WP-13.2` document.
- **Tests.** Python schema tests: every document is gated; delta-gated documents are custom-only; an `edit` case moved into the delta gate is rejected; a missing gate is rejected.
- **Unchanged.** The authority results (27 cases), the numeric semantics and R001/R002.
- **Coordination.** `#49` (WP-13.2) records the added gate: after `#88` certifies, its Python approval and Rust implementation reviews run the gate-`WP-13.2` document.

**Scope.** No production code changes, and no change to the Owner's condition: Rust WP-13.2 still follows delta certification.
