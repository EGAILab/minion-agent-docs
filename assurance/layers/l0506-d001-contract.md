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
