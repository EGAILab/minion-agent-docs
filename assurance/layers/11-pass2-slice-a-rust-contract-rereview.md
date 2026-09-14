# Layer 11 Pass 2 Slice A — independent Rust contract re-review

## Exact candidate

- code PR `EGAILab/minion-agent#30` @
  `a252602226eddc3660a7513266fe7085b2d7f5df`
- docs PR `EGAILab/minion-agent-docs#75` @
  `5318049581985be2af8046e6520582203ef99931`
- pinned Pi `b7bb00b936dbe21b8e160b3e89efdec361846699`
- prior rejection: docs PR #76 @
  `dc75a40b1dde8fdc588bb44f05f3f3c898bcda37`

Both candidate heads were fetched and remote-reachable. They remain based on the accepted Slice A
baselines and are not descendants of either quarantined artifact.

## Pi-first re-audit

Re-read pinned Pi `packages/ai/src/auth/oauth/openai-codex.ts` (`decodeJwt`, `getAccountId`,
`credentialsFromToken`, `toAuth`) and `packages/ai/src/auth/types.ts` before inspecting the
remediation. Direct Node v22 comparisons were rerun for all six prior witnesses.

## Finding ledger

### L11-SA-R001 — STILL OPEN (`CONTRACT_ASSURANCE_DEFECT`)

The Python implementation is now Pi-faithful for every prior discriminating witness:

| boundary | result |
|---|---|
| ASCII whitespace accepted by `atob` | PASS |
| malformed partial padding rejected | PASS |
| bare `NaN` rejected by `JSON.parse` | PASS |
| bare `Infinity`/`-Infinity` rejected | PASS |
| large integer coerced through IEEE-754 | PASS |
| negative zero sign preserved | PASS |

`_forgiving_base64_decode` correctly implements the relevant WHATWG algorithm: strip exactly the
five ASCII-whitespace characters, remove one/two trailing padding characters only under the
length-divisible-by-four condition, reject remainder one, reject every non-standard-alphabet
character, then decode. `parse_constant` and `parse_int=float` correctly close the observed
JavaScript/Python JSON differences without a hand-written parser. The 23 tests exercise the real
production seam and all pass.

The normative contract was not remediated, however. `spec/auth.md` still says `decode_jwt` returns
“whatever `json.loads` produces” and says it reproduces “two” quirks exactly. It specifies neither
the WHATWG whitespace/partial-padding rule nor the JavaScript rejection/coercion rules. Both claims
are now false relative to production and `PROV-011`'s expanded manifest text. An independent Rust
implementation following the normative spec would remain free to reproduce the rejected PASS-1
behavior and would need to read Python or remediation prose to discover the actual rule.

Minimal correction: update the normative `PROV-011` section to define the full adopted boundary
already implemented and evidenced—WHATWG forgiving-base64 behavior, Latin-1 byte interpretation,
JavaScript rejection of non-JSON constants, and IEEE-754 parsing of all number literals. Replace
“whatever `json.loads` produces” with a language-neutral JavaScript-`JSON.parse`-equivalent result.
No Python production change is requested.

### L11-SA-R002 — CLOSED

The stale `PROV-011, deferred` reference is now adopted/current. The premature `PROV-014`
reference is removed; the current spec accurately leaves the vocabulary under existing
`PROV-013` until Slice B formally performs the split. No contradictory current requirement state
remains on this surface.

### L11-SA-R003 — CLOSED

The exact owner message and scope are durably recorded verbatim at
`https://github.com/EGAILab/minion-agent/issues/29#issuecomment-5659001629`. It expressly covers
PROV-011, the later PROV-013/014 split, Slice ordering, and the later HTTP transport choice.
`PROV-011` also correctly identifies its own adoption as execution of its already-recorded closure
criterion rather than depending on new governance.

## Gates

Fresh against the exact code SHA:

- Slice A tests: 23 passed
- manifest validation: 8 passed
- full Python tests without coverage: pass (1,321 passed / 19 expected failures by current
  inventory)
- Ruff: pass
- mypy: pass (67 source files)
- direct Node/Python six-witness comparison: pass

Green implementation gates do not resolve the remaining normative-spec defect.

## Verdict

```text
Layer 11 Pass 2 Slice A shared contract
    REJECTED @ code a252602226eddc3660a7513266fe7085b2d7f5df
               docs 5318049581985be2af8046e6520582203ef99931

Python Slice A implementation
    PI witnesses conforming; contract certification remains open

Rust Slice A
    NOT_IMPLEMENTED / BLOCKED

Slice B
    NOT STARTED
```

Only the normative `spec/auth.md` correction under L11-SA-R001 remains. No Rust code was changed,
no candidate was merged, and no quarantined artifact was used as evidence.
