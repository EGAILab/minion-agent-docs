# Layer 11 Pass 2, Slice A — L11-SA-R001/R002/R003 remediation

## Candidates

```text
prior rejected candidate (first independent Rust contract review)
    code PR #30 @ f7ba37ee164763dfd083c3df3a0d6d5e55261cf0
    docs PR #75 @ 0715fae04c2d43c6fdbb5441cfa44bca25f1d9c9

first independent Rust contract review (rejecting)
    docs PR #76 @ dc75a40b1dde8fdc588bb44f05f3f3c898bcda37
    assurance/layers/11-pass2-slice-a-rust-contract-review.md
```

## Trigger check

This is the first review of Slice A's own candidate; none of the three findings has itself
survived a prior review, and the layer/slice has not accumulated three rejections. §11.8
convergence is NOT triggered. This is an ordinary remediation pass.

## Independent re-verification (not trusting the review's own table alone)

Re-ran all six of `L11-SA-R001`'s own witnesses directly against a live Node v22 process before
touching any code, confirming each independently:

```text
atob("eyJh IjoxfQ==")               -> "{\"a\":1}" (interior space tolerated)
atob("MTIzNA=")                      -> throws "Invalid character"
atob("TmFO")                         -> "NaN"; JSON.parse("NaN") throws "not valid JSON"
atob("SW5maW5pdHk=")                 -> "Infinity"; JSON.parse(...) throws "not valid JSON"
atob("OTAwNzE5OTI1NDc0MDk5Mw==")     -> "9007199254740993"; JSON.parse(...) === 9007199254740992
atob("LTA=")                          -> "-0"; JSON.parse("-0") is -0 (Object.is confirmed)
```

Additionally reverse-engineered the WHATWG "forgiving-base64 decode" algorithm's exact padding
rule empirically (not from a half-remembered spec summary), probing eleven further cases
(`MTIzNA==`, `MTIzNA=`, `MTIzNA`, `MTIzNA===`, `MTIzN`, `MTIz`, `MTIz=`, whitespace-surrounded,
interior tab, interior `=`, leading `=`) to confirm the exact success/failure boundary before
writing `_forgiving_base64_decode`.

## L11-SA-R001 — implementation

`device_code.py`-style boundary work, but in `openai_codex.py`:

- New `_forgiving_base64_decode(data: str) -> bytes`: strips the five ASCII-whitespace code points
  (tab/LF/FF/CR/space) anywhere in the input; strips trailing `=` ONLY when the whitespace-stripped
  length is a multiple of 4 AND ends in exactly one or two `=`; rejects remainder-1 lengths; rejects
  any character outside `[A-Za-z0-9+/]`; re-pads the validated content before delegating to
  `base64.b64decode(..., validate=True)`. Replaces the prior naive "pad to a multiple of 4, then
  validate" logic, which both rejected whitespace `atob` tolerates and silently repaired malformed
  padding `atob` rejects.
- New `_reject_js_incompatible_constant`, wired as `json.loads`'s own `parse_constant` hook --
  raises for the three tokens (`NaN`, `Infinity`, `-Infinity`) Python's `json` module otherwise
  accepts as a non-standard extension, matching `JSON.parse`'s own rejection of them.
- `json.loads`'s own `parse_int=float` hook -- every integer literal now round-trips through the
  same IEEE-754-double coercion JS's own single number type performs unconditionally, reproducing
  both silent precision loss beyond `2**53` and sign-preserving negative zero with one change.

`tests/auth/test_openai_codex.py`: six new permanent witnesses, one per finding-table row.

**Independently confirmed discriminating by revert-and-confirm (all four mechanisms)**:

1. Reverted `_forgiving_base64_decode` to the prior naive padding logic: the whitespace-tolerance
   witness failed (`None` instead of `{"a": 1}`) and the malformed-padding witness failed
   (`1234.0` instead of `None`) -- both reproducing the exact review-reported symptom. Restored;
   both passed.
2. Reverted `json.loads`'s own `parse_int`/`parse_constant` hooks to Python's defaults: all four
   remaining witnesses failed with the exact wrong values (`nan`/`inf` instead of `None`;
   `9007199254740993` instead of `9007199254740992.0`; positive-signed `0.0` instead of `-0.0`).
   Restored; all four passed.

Full `tests/auth/test_openai_codex.py` suite: 23/23 passed after each restoration, including every
pre-existing witness from the original candidate, confirming no regression.

## L11-SA-R002 — implementation

`spec/auth.md`:

- Removed the premature `PROV-014` reference in the document's own introduction (Slice B has not
  run yet; the interaction vocabulary is still, accurately, attributed to the bundled `PROV-013`
  row pending that separately-reviewed split).
- Corrected the stale "`PROV-011`, deferred" cross-reference near the credential-vocabulary
  section (left over from Pass 1, not updated when `PROV-011` was moved to adopted) to "`PROV-011`,
  adopted -- see ... below".

Independently re-read the full file after editing to confirm no other stale `PROV-011`/`PROV-014`
reference remained (`grep -n "PROV-011\|PROV-014" spec/auth.md`, three matches, all consistent).

## L11-SA-R003 — implementation

The review's own core point: an agent's own restatement of "the owner approved this" is not
independently verifiable, and is exactly the failure mode the immediately-prior unauthorized-agent-
action incident was about. Two corrections, matching the review's own "minimal correction"
suggestion exactly:

1. Posted the owner's own scope-decision message VERBATIM (not paraphrased, not summarized) as a
   durable GitHub issue comment: `minion-agent#29`,
   `https://github.com/EGAILab/minion-agent/issues/29#issuecomment-5659001629`, with an explicit
   attestation that the quoted block is reproduced without alteration from the owner's own message
   in this session's controlling conversation. This is now the citable `GOVERNANCE_SOURCE`
   (`agent-workflow.md` §11.10) -- a reviewer can check it directly, not merely trust a paraphrase.
2. Narrowed `PROV-011`'s own manifest citation: its own disposition change does not depend on the
   broader owner citation at all -- it is a routine execution of the closure criterion Pass 1
   itself already recorded for this exact row. The broader citation is retained only for what
   actually needs it: the Pass-2 restart's own sequencing context, and the (not-yet-implemented)
   `PROV-013`/`PROV-014` split and `httpx` choice future slices will consume.

## Normative deltas

- `spec/auth.md`: `PROV-014` reference removed; stale `PROV-011` deferred-reference corrected.
- `pi-parity-manifest.yaml`: `PROV-011`'s `rule`/`tests` extended with the `L11-SA-R001`/`L11-SA-R003`
  correction paragraphs described above; test count updated to 23.

## Fresh quality gates

- `tests/auth/test_openai_codex.py` (targeted, `--no-cov`): 23 passed, 0 failed.
- `tests/conformance/test_manifest_validation.py`: 8/8.
- `ruff check .` / `ruff format --check .`: clean, same pre-existing 7-file drift baseline.
- `mypy` (default gate, `files = ["src/minion_agent"]`): clean, 67 source files.
- `mypy` including all typing fixtures: clean, 70 source files.
- Full `pytest` suite (fresh, with coverage): to be run and recorded with exact counts immediately
  before push, per this project's "report fresh counts, never reuse old numbers" rule.

## Next action

Push to the same candidate branches, updating PRs #30/#75 in place. `STATUS = RUST_CONTRACT_REVIEW`,
requesting a NEW complete exact-SHA review per §11.8.8 (prior approval is stale). `NEXT_OWNER =
Codex`. Do not start Slice B. Do not start Layer 12.
