# Layer 11 Pass 2 Slice A — independent Rust contract review

## Exact review target

- code PR: `EGAILab/minion-agent#30`
- code head: `f7ba37ee164763dfd083c3df3a0d6d5e55261cf0`
- code base: `main@08433b0e8aa1f4502a2ebd3b6a8c553f29f6f99a`
- docs PR: `EGAILab/minion-agent-docs#75`
- docs head: `0715fae04c2d43c6fdbb5441cfa44bca25f1d9c9`
- docs base: `master@e7f31a33f6fd10ae58bd87d12dd7a9c8de2524fe`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- coordination: `EGAILab/minion-agent#29`

Both candidates were fetched from GitHub, were open, ready for review, and mergeable at the
recorded heads. Both start at the recorded accepted default-branch bases. Neither quarantined
commit (`ed58b714613000bdee6eedfb41a38b2ceb9b5a56` or
`cbc3ba5f373b0a63d5e611fe7e40f6dcca79ff08`) is an ancestor of its corresponding candidate.

## Independent Pi audit

Read before the candidate implementation:

- `packages/ai/src/auth/oauth/openai-codex.ts:41` (`OAuthToken`)
- `packages/ai/src/auth/oauth/openai-codex.ts:103-113` (`decodeJwt`)
- `packages/ai/src/auth/oauth/openai-codex.ts:396-416` (`getAccountId`,
  `credentialsFromToken`)
- `packages/ai/src/auth/oauth/openai-codex.ts:541-543` (`toAuth`)
- `packages/ai/src/auth/types.ts:7-35` (`ModelAuth`, `OAuthCredentials`,
  `OAuthCredential`)
- `packages/ai/test/openai-codex-oauth.test.ts`

The main adopted behavior is correctly identified: `decodeJwt` splits into exactly three
segments, applies `atob` to the payload, applies JavaScript `JSON.parse`, and catches failure;
`getAccountId` admits only a non-empty string at the namespaced claim; credential construction
throws the exact failure message when that claim is unavailable; and `toAuth` projects the access
token as `apiKey`. The existing Minion credential's `extra["account_id"]` representation is an
explicit architectural mapping over the already-certified `PROV-006` shape.

Direct Node v22 probes were used to distinguish the actual `atob`/`JSON.parse` boundary from the
candidate's Python approximation. They revealed active differences listed below.

## Evidence reviewed

- `spec/auth.md`
- `pi-parity-manifest.yaml::PROV-006/011/012/013`
- `assurance/layers/11-pass2-slice-a-codex-account-id-projection.md`
- all 17 `tests/auth/test_openai_codex.py` tests
- `minion_agent.auth.openai_codex`
- certified Rust auth credential/model-auth shapes in
  `minion-agent-rust/crates/minion-agent/src/auth/credential.rs`

Fresh checks on the exact code candidate:

- full Python tests without coverage: pass (1,315 passed / 19 expected failures by collected
  inventory)
- Slice A tests: 17 passed
- manifest validation: 8 passed
- Ruff: pass
- mypy: pass, 67 source files

Green existing tests do not close the discriminating Pi witnesses below.

## Findings

### L11-SA-R001 — `PI_PARITY_DEFECT` — `atob`/`JSON.parse` fidelity is incomplete

Affected:

- `minion-agent-python/src/minion_agent/auth/openai_codex.py::decode_jwt`
- `spec/auth.md`, Codex account-id projection
- `pi-parity-manifest.yaml::PROV-011`
- `tests/auth/test_openai_codex.py`

The candidate says it reproduces Pi's decode behavior exactly, but its combination of manual
padding, `base64.b64decode(validate=True)`, and default `json.loads` differs observably from the
pinned source. Independent witnesses against the exact candidate:

| payload segment | pinned Pi / Node | candidate Python |
|---|---|---|
| `eyJh IjoxfQ==` (ASCII whitespace) | parses as `{"a":1}` | returns `None` |
| `MTIzNA=` (invalid partial padding) | `atob` throws, returns absent | repairs padding and returns `1234` |
| `TmFO` (`NaN`) | `JSON.parse` throws, returns absent | returns `float('nan')` |
| `SW5maW5pdHk=` (`Infinity`) | `JSON.parse` throws, returns absent | returns `float('inf')` |
| `OTAwNzE5OTI1NDc0MDk5Mw==` (`9007199254740993`) | IEEE-754 result `9007199254740992` | exact Python integer `9007199254740993` |
| `LTA=` (`-0`) | preserves negative zero | returns integer zero |

The first two are WHATWG forgiving-base64 rules exercised by `atob`: ASCII whitespace is ignored,
missing padding may be tolerated, but already-present malformed padding is not silently repaired.
The remaining witnesses show that default Python `json.loads` is not JavaScript `JSON.parse` for
the function's public `JsonValue` result.

Minimal correction: specify and implement the real `atob` input grammar (including exact ASCII
whitespace and padding handling) and JavaScript-number/constant parsing at this observable
boundary, or narrow the shared/public surface so that the full decoded `JsonValue` is not claimed
as adopted behavior. Retain permanent witnesses for every competing behavior above. The fix must
continue rejecting base64url `-`/`_`, accepting genuinely omitted padding, and decoding bytes as
Latin-1.

### L11-SA-R002 — `CONTRACT_ASSURANCE_DEFECT` — current normative state is contradictory

Affected: `spec/auth.md`.

The new normative section marks `PROV-011` adopted, but the same current document still calls the
Codex `accountId` example "`PROV-011`, deferred" near the credential vocabulary. The introduction
also assigns the interaction vocabulary to `PROV-014`, although this Slice explicitly does not
create that row and the current manifest still assigns the vocabulary and orchestration together
to `PROV-013`.

Two independent implementers therefore cannot use the candidate alone to determine whether
`PROV-011` is current or deferred, or whether `PROV-014` exists. Minimal correction: change the
stale `PROV-011` reference to adopted/current and keep the interaction vocabulary attributed to
the actually-existing `PROV-013` until a separately reviewed Slice B contract formally performs
the split.

### L11-SA-R003 — `CONTRACT_ASSURANCE_DEFECT` — claimed owner provenance is not traceable

Affected:

- `pi-parity-manifest.yaml::PROV-011`
- `assurance/layers/11-pass2-slice-a-codex-account-id-projection.md`
- coordination issue `EGAILab/minion-agent#29`

The candidate repeatedly cites an owner-approved scope and names `LAYER 11 PASS 2 — OWNER SCOPE
DECISION` as its `GOVERNANCE_SOURCE`. The durable issue contains the author's fresh-audit proposal
and a later assertion that the proposal was approved, but no owner answer or traceable source for
that answer. Under workflow §11.10, another agent's assertion of approval is not approval and an
artifact cannot make that assertion self-authenticating.

The owner's current instruction authorizes Codex to review this exact Slice A, merge it only if
approved, and then begin Slice B contract-first. It does not independently establish every broader
semantic/scope decision the candidate attributes to the missing prior record (notably the exact
`PROV-013`/`PROV-014` split and Slice C transport choice).

Minimal correction: cite a durable owner-authored/owner-message record that actually contains each
claimed decision and exact scope, or remove/narrow unsupported owner-approval claims. Slice A's
routine implementation of the already-recorded `PROV-011` closure criterion need not invent a
governance claim. Future Slice B/C choices remain contract-first or blocked for owner action as
applicable.

## Rust implementability

The conceptual Slice A mapping is implementable over the certified Rust `OAuthCredential` and
`ModelAuth` types without changing a lower-layer contract. It is not independently implementable
from this candidate *faithfully*, however, because the written decoder rule and the Python
evidence currently certify behavior that differs from Pi and leave current requirement ownership
contradictory.

No Rust production or tests were modified. Slice B was not started.

## Verdict

```text
Layer 11 Pass 2 Slice A shared contract
    REJECTED @ code f7ba37ee164763dfd083c3df3a0d6d5e55261cf0
               docs 0715fae04c2d43c6fdbb5441cfa44bca25f1d9c9

Python Slice A
    REOPENED

Rust Slice A
    NOT_IMPLEMENTED / BLOCKED

Slice B
    NOT STARTED
```

Only the three narrow findings above require remediation. No quarantined artifact was reviewed as
a candidate or used as evidence.
