# L05-D001 contract draft: runtime-validation schema string domain (`TOOL-016` / `TOOL-003`)

- **Coordination:** `minion-agent#104`.
- **Governance:** Owner decision `L0506-D002-R001`, Option 1 (`minion-agent#99` comment `5926416181`); `standing_delegation: minion-agent#75`.
- **State:** SCOPING → CONTRACT_DRAFT → CONTRACT_REVIEW.
- **Characterization:** `l05-d001-characterization.md` (pass 1, 729 cells, Pi and Python).

## What this delivers

| Deliverable | Where |
|---|---|
| contract text | `spec/tools.md` Layer 05, "Runtime-validation schema string domain (`TOOL-016` / `TOOL-003`, post-certification delta `L05-D001`)" |
| manifest | `minion-agent` `pi-parity-manifest.yaml` `TOOL-016` (rule and tests). `TOOL-003` is unchanged: its validation rule already covers the schema it validates against |
| canonical witnesses | `minion-agent` `conformance/agent/schema-domain/`: 9 documents, 729 cases, shape `schema-domain-scenario.schema.json` |
| Python evidence | `tests/conformance/schema_domain_runner.py`, `test_schema_domain_conformance.py` (729), `tests/tools/test_schema_domain_negative_controls.py`, schema tests. No production change |
| authority | `data/l05-d001-schema-domain/` (`harness/make_scenarios.py` generates the scenarios) |

## Cross-Language Feasibility Matrix

**Pinned Pi:** `b7bb00b936dbe21b8e160b3e89efdec361846699`. **Author:** Claude. **Independent checkpoint reviewer:** Codex.

### 1. Value-domain matrix (four domains, template §1.1)

| Domain / value | Pi | Python | Rust (certified) | Lossless across all? | Witness |
|---|---|---|---|---|---|
| SCHEMA: property names, `required`, `const`/`enum`, `propertyNames`, `dependentRequired` with an unpaired surrogate or mixed member | JS strings; exact code-unit identity | `dict`/`str`; identical verdicts (729/729) | `Map<String, serde_json::Value>`: **cannot hold** | **NO (Rust)**: this delta | the corresponding role documents |
| SCHEMA: `pattern`, `patternProperties` | Unicode-mode RegExp over code points | Python `re` over `str` code points; identical verdicts | `serde_json` string cannot hold the lone members; a code-unit regex would be wrong | **NO (Rust)** | `pattern`, `pattern-unanchored` (pair-half cells), `pattern-properties` |
| SCHEMA: scalar members (ASCII, BMP, pair, U+FFFD) | as above | identical | representable | YES | the scalar rows of every role |
| INSTANCE | prepared: `L0506-D002`; raw: `L0206-D002` | — | — | outside | — |
| RAW/WIRE | `L0206-D002` | — | — | outside | — |
| SERIALIZED/PROJECTED: provider schema transport | `JSON.stringify` (lone escaped), no `sanitizeSurrogates` | — | — | outside (Layer 11; decision §10) | characterization note |

### 2. Lower-layer capability matrix

| Operation | Layer | Certified seam | Python | Rust | Additive extension? | Non-additive reopen? |
|---|---|---|---|---|---|---|
| hold a JS-string-capable schema in `ToolDefinition.parameters` | 05 | `TOOL-016` | YES | **NO** | **YES:** a runtime-validation schema representation (decision §8) | NO |
| register the tool with such a schema | 05 | registry | YES | NO until the above lands | rides on the above | NO |
| validate names/equality by UTF-16 identity | 06 | `TOOL-003` validator | YES | NO until the above lands | the validator over the new representation | NO |
| validate `pattern` in Unicode mode | 06 | `TOOL-003` validator | YES (`re` over code points) | must be Unicode-mode over code units | as above | NO |

### 3. Hazard checklist (F2/F7)

| Hazard | State | Evidence |
|---|---|---|
| `String.length` / UTF-16 | AUDITED | identity over code units in every role |
| `RegExp` `u` mode | AUDITED | the `pattern-unanchored` pair-half cells (Unicode mode); lone-surrogate patterns compile |
| `JSON.stringify` of schemas | NOT_APPLICABLE here | provider transport, Layer 11 (decision §10) |
| Unicode / ICU | NOT_APPLICABLE | no normalization in validation |
| object key order | NOT_APPLICABLE | each case has one schema key per role; K1 is `L0206-D001` |
| documentary fields | NOT_APPLICABLE | not consumed by validation |
| package versions | AUDITED | typebox 1.3.7 (SRI), `validation.ts` hash |

### 4. Concurrency

`NOT_APPLICABLE`.

### 5. Verdict

```text
FEASIBILITY
    READY for the L05-D001 scope. The Rust "NO" rows are R001's schema half itself, resolved by the authorized
    runtime-validation schema representation (decision s.8). Outside the scope, with owners: L0506-D002, L0206-D002,
    L0206-D001, Layer 11 provider schema transport.
```

## Decisions made in the draft (for the independent review)

1. **The roles are those the validator consumes.** Codex's §2 list plus `additionalProperties` (declared names), `patternProperties`, `propertyNames` and `dependentRequired`, all characterized. Documentary fields are excluded.
2. **`pattern` is stated as a Unicode-mode RegExp, not equality.** The discriminating cells are the pair halves under an unanchored search.
3. **`TOOL-003` text is unchanged.** Its rule already validates against "the exact Layer-05-approved schema". This delta widens what that schema may hold (`TOOL-016`), not how validation is invoked.
4. **The canonical cases carry literal schemas**, in the value grammar. A runner needs no role knowledge, and the role descriptions are documentation.

## Reviewer checklist

1. Reproduce `data/l05-d001-schema-domain/out/schema.json` (`harness/run.sh`) and the 9 scenario documents (`harness/make_scenarios.py`).
2. Check the per-role operations, especially the `pattern-unanchored` pair-half cells.
3. Check the scope against the decision (§§2, 10, 11), including the exclusion of documentary fields.
4. Check that the negative controls kill their mutants.
5. Check Rust feasibility: a JS-string-capable schema representation and a Unicode-mode `pattern` over code units.

## Status

- `L05-D001` contract: READY FOR INDEPENDENT CONTRACT REVIEW.
- Python: conforms with no production change (729 cases; negative controls), PENDING contract review.
- Rust: NOT_IMPLEMENTED.
- WP-13.2: independent (decision §7; confirmed in Codex CONTRACT2 on `L0506-D002`).

## Remediation 1: `L05-D001-R001`, `patternProperties` Unicode-mode evidence

**Trigger check (§11.8).**
- Trigger A has not fired: R001 has survived one independent review (CONTRACT1, docs #211 comment `5930478907`).
- Trigger B has not fired: no successor finding on this surface.
- Trigger C has not fired: the work package has one rejected complete review.
- Ordinary remediation.

**The defect (accepted).** All 81 `pattern-properties` cells anchored their key regex, so a code-unit `patternProperties` matcher passed all 729 cases and every control. Codex demonstrated this with a real-seam mutant.

**The fix.**
- **Authority.**
  - A new role, `pattern-properties-unanchored` (81 cells, 810 in all). It covers both pair halves (accepted: no Unicode-mode match) and the genuine-unpaired guard (`lone-high` in `pair-then-lone-high`, rejected).
  - The key-capture field is corrected to code units (non-blocking observation).
  - Python matches all 810 cells.
- **Canonical:** 10 documents and 810 cases.
- **Negative control.** `test_a_code_unit_pattern_properties_matcher_is_killed` replaces only the `patternProperties` keyword with a code-unit matcher. It is killed by the two pair-half cells, while the guard and the `pattern` keyword's own cells stay correct.
- **Spec and manifest counts:** 810, 10 roles.

**Status:** R001 is REMEDIATED, pending targeted re-review.
