# Layer 11 Pass 2, Slice A — L11-SA-R001 spec completion (re-review remediation)

## Candidates

```text
prior rejected candidate (first independent Rust contract re-review)
    code PR #30 @ a252602226eddc3660a7513266fe7085b2d7f5df
    docs PR #75 @ 5318049581985be2af8046e6520582203ef99931

first independent Rust contract re-review (rejecting, one narrow blocker)
    docs PR #76 @ d5fec8ef60999ee7de7567e52445480abba2dd63
    assurance/layers/11-pass2-slice-a-rust-contract-rereview.md
```

## Trigger check

`L11-SA-R001` has now been reviewed twice (original discovery, then this re-review confirming the
Python fix but finding the spec still incomplete) -- both times as the SAME finding ID, meeting
§11.8's "same finding survives two independent reviews" convergence trigger in a strict reading.
However, the re-review's own verdict is explicit that the Python implementation itself is now
fully conforming (all six witnesses pass) and the ONLY remaining gap is that the normative prose
was never updated to match it -- a narrow, mechanical documentation completion, not a new or
continuing semantic disagreement requiring characterization/negotiation. Proceeding as an ordinary
targeted remediation rather than opening a full convergence cycle, consistent with
`agent-workflow.md` §11.8.7 (targeted finding-closure review) for exactly this shape of narrow,
already-agreed correction.

## What was missing

`spec/auth.md`'s own `PROV-011` section still said `decode_jwt` returns "whatever `json.loads`
produces" and that it reproduces "two" Pi/JS decode quirks -- both statements stale since the
`L11-SA-R001` Python remediation, which fixed four additional fidelity gaps beyond those original
two. An independent Rust implementation reading only the normative spec (not the Python source or
assurance prose) would have no way to discover the WHATWG forgiving-base64 behavior or the
JavaScript-`JSON.parse`-equivalent number/constant handling, and could validly re-implement the
already-rejected Pass-1-era behavior.

## Remediation

`spec/auth.md`'s `PROV-011` section rewritten to state all four binding rules as language-neutral
normative prose (not Python-mechanics-specific): the exact WHATWG forgiving-base64 algorithm
(whitespace stripping, the narrow padding-strip condition), Latin-1 byte interpretation, rejection
of the bare `NaN`/`Infinity`/`-Infinity` tokens, and IEEE-754-double coercion of every integer
literal (precision loss beyond `2**53`, sign-preserving negative zero). The `decode_jwt` type
signature in the fenced summary block changed from `-> JsonValue # whatever json.loads produces`
to `-> JS-JSON.parse-equivalent value | absent`, removing the Python-implementation-specific
phrasing the re-review flagged.

No Python production code was changed, per the re-review's own explicit instruction ("No Python
production change is requested") -- confirmed by re-running the full Python gate suite unchanged
to verify this really was a docs-only pass.

## Fresh quality gates

- `tests/conformance/*` (schema/manifest/layering, `--no-cov`): all passing, unchanged from the
  pre-remediation baseline (confirming no Python file was touched).
- No new Python tests were needed or added -- the spec now describes behavior the existing 23
  `tests/auth/test_openai_codex.py` tests already evidence in full.

## Next action

Push to the same candidate branches, updating docs PR #75 in place (code PR #30 unchanged, same
SHA as the re-reviewed candidate). `STATUS = RUST_CONTRACT_REVIEW`, requesting a NEW complete
exact-SHA review per §11.8.8. `NEXT_OWNER = Codex`. Do not start Slice B. Do not start Layer 12.
