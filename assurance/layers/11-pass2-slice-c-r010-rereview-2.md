# Layer 11 Pass 2 Slice C — L11-SC-R010 second re-review

## Exact target

- Code PR #32: `3aa7cd574d7e22aaa9c5280beec1ad9b72c1633a`
- Docs PR #82: `9b479523de2c4244a428c7ba65f053f696e1f13e`
- Pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- Prior R010 review: docs PR #87 at
  `62847eec65bdf8081808db975c97a58e3a38dac6`

Issue #29 recorded the same remote-reachable heads and `NEXT_OWNER = Codex`. Both candidates were
open, Ready for Review, and unmerged. This was a complete review-only pass; no candidate, Python,
Rust, Slice-D, or Layer-12 work was changed.

## Complete review result

`L11-SC-R001` through `L11-SC-R009` remain closed. R010's exact templates, negative-zero rule,
number-notation boundaries, non-ASCII witness, and integer-index-key ordering correction were
independently rechecked and are sound. The normative authority remains ECMAScript
`JSON.stringify`, which is the correct language-neutral rule.

## L11-SC-R010 — `CONTRACT_ASSURANCE_DEFECT` — STILL OPEN / refined again

The attempted exhaustive string-escaping paraphrase says every non-ASCII character passes through
literally and that generic control escapes use `\u00XX` “zero-padded to 2 digits.” Both statements
are false for reachable, successfully parsed JSON:

```text
Node 22:
JSON.stringify(JSON.parse('"\\ud800"'))  -> "\\ud800"
JSON.stringify(JSON.parse('"\\u0001"'))  -> "\\u0001"
```

Modern ECMAScript's well-formed `JSON.stringify` escapes an unpaired UTF-16 surrogate code unit;
valid JSON can contain one through a `\uD800` escape. A valid astral scalar represented by a paired
surrogate passes through literally, but that does not justify “every non-ASCII character.” Generic
`\u` escapes always contain four hexadecimal digits; `00XX` is four digits, not two.

The section also ends by saying its confirmed examples are not a guarantee against further edge
cases. That is appropriate for an example list, but not for a replacement algorithm. The complete,
stable contract should keep ECMAScript `JSON.stringify` as normative and treat the listed cases as
discriminating witnesses rather than claiming the prose subset exhaustively reimplements the
standard.

Minimal correction:

1. correct generic control escapes to four zero-padded lowercase hex digits;
2. distinguish valid Unicode scalar values from unpaired surrogate code units and require a lone-
   surrogate witness;
3. retain ECMAScript `JSON.stringify` as the complete normative authority; present the detailed
   bullets as required examples/constraints, not a self-declared exhaustive substitute;
4. keep all already-correct R010 templates, numeric rules, ordering rules, and witnesses unchanged.

No lower-layer or implementation change is required.

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

Keep convergence active and remediate only refined R010. Any changed candidate requires another
complete exact-SHA review.
