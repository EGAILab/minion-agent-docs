# Layer 11 Pass 2 Slice C — L11-SC-R010 complete re-review

## Exact review target

- Code PR #32: `e082b84a16d06187019b729c9e87a1e9544e209c`
- Docs PR #82: `e05fae4eb9f360802fa66f51c17248de011a0b44`
- Pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- Prior final review: docs PR #86 at
  `87c9acf073677abcd26df649a19e209d521482fa`

Issue #29 recorded the same remote-reachable candidate pair and `NEXT_OWNER = Codex`. Both
candidate PRs were open, Ready for Review, and unmerged. This was a fresh complete review-only
pass. No candidate, Python, Rust, Slice-D, or Layer-12 implementation was changed.

## Complete-review result

Pinned Pi, the full `PROV-012`/`PROV-016` contract, manifest, certified auth seams, and all prior
findings were rechecked. `L11-SC-R001` through `L11-SC-R009` remain closed. The three exact Pi error
templates are now stated correctly. No lower-layer reopen is required.

`L11-SC-R010`, however, remains open because the new explanatory and implementation rule is
factually false and incomplete.

## L11-SC-R010 — `CONTRACT_ASSURANCE_DEFECT` — STILL OPEN / refined witness

The candidate correctly names ECMAScript `JSON.stringify` as the normative renderer, but then says
Python `json.dumps(value, separators=(",", ":"))` reproduces it **exactly for every ordinary
case**, apart from whole-valued floats needing `.0` removal. Direct Node 22 and Python 3.13 probes
disprove that assertion:

| Value | Node `JSON.stringify` | Python compact `json.dumps` |
|---|---|---|
| object whose `s` value contains U+00E9 | literal U+00E9 in the JSON string | `{"s":"\u00e9"}` |
| `{"n":-0.0}` | `{"n":0}` | `{"n":-0.0}` |
| `{"n":1e-7}` | `{"n":1e-7}` | `{"n":1e-07}` |
| `{"n":1e20}` | `{"n":100000000000000000000}` | `{"n":1e+20}` |
| `{"2":"b","1":"a","x":0}` | `{"1":"a","2":"b","x":0}` | `{"2":"b","1":"a","x":0}` |

The last row also disproves the spec's blanket statement that `JSON.parse`/`JSON.stringify` and
Python preserve the same source key order: ECMAScript's own-property enumeration orders
array-index-like keys numerically before other string keys. Removing `.0` alone cannot implement
ECMAScript number serialization; negative zero and exponent/fixed-notation thresholds are separate
rules.

The contract is therefore internally contradictory: its normative headline requires exact
ECMAScript output while its supposedly binding host mapping and required evidence certify an
algorithm that produces different observable error messages.

Minimal correction:

1. retain the exact three templates and the normative `JSON.stringify` rule;
2. remove the false “compact `json.dumps` is exact except `.0`” claim and the ad-hoc whole-float
   prescription;
3. describe or normatively reference ECMAScript `JSON.stringify`/number/property-enumeration
   semantics without pretending separators alone implement them;
4. extend the future discriminating witnesses to cover non-ASCII strings, negative zero, small
   exponent form, the fixed-vs-exponent threshold, and integer-index-like object keys, in addition
   to null/array/ordinary object/template coverage.

This is a contract/evidence correction only. It does not require Python implementation or any
certified lower-layer delta.

## Fresh gates

- `uv run pytest -q`: **1337 passed, 19 xfailed, 0 failed**, **100.00%** coverage.
- `uv run pytest tests/conformance/test_manifest_validation.py --no-cov -q`: **8 passed**.
- `uv run ruff check .`: PASS.
- `uv run mypy src/minion_agent tests/typing`: PASS (72 source files).
- Manifest: 95 rows / 95 unique IDs.

## Verdict

```text
Layer 11 Pass 2 Slice C shared contract
    REJECTED

Python Slice C
    NOT_IMPLEMENTED / BLOCKED

Rust Slice C
    NOT_IMPLEMENTED / BLOCKED

Layer 11 Pass 2
    NOT CLOSED

Layer 12
    NOT STARTED
```

Keep the existing convergence track active and remediate only refined `L11-SC-R010`. Any changed
candidate requires another complete exact-SHA review.
