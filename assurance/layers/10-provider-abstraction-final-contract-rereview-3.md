# Layer 10 — approved final complete independent Rust contract review

**Review mode:** mandatory workflow §11.8.8 final complete exact-SHA review.

## Exact approved candidate

- code PR #20: `a7d05f26b22e1168c58578f5423d9a5c6f2ed0e3`
- docs PR #45: `7c8d8ed68d0c903b8262e82aca80537bd2267ed8`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- preceding rejection: docs PR #47 at
  `b41bcd982eb65072717a49b5c9214db1253893d7`

The remote heads matched coordination issue #19, both PRs were Ready for Review, open, unmerged,
and mergeable. This approval applies only to the exact candidate pair above.

## Independent complete audit

The review used the mandatory order: pinned Pi, normative spec, manifest, canonical evidence,
certified Rust architecture, assurance, then Python as secondary evidence.

Pinned source rechecked: `types.ts::ProviderStreams/StreamFunction/deferred options`,
`models.ts::ModelsImpl/MutableModels/createProvider/apiFor/dispatch`, `api/lazy.ts`, the compat API
registry and `registerFauxProvider`, and the faux registration/stream/deferred implementation.

The contract correctly distinguishes:

- required `stream` and `streamSimple` from optional deferred capabilities;
- represented returned-stream errors from eager unresolvable-identity behavior;
- Models-facing fetch/cancel capability failure asymmetry;
- `MutableModels`, compat's generic registry, and faux per-call unregister;
- Minion's owner-approved full-identity/per-registration-call registry divergence; and
- current Layer-10 obligations from explicitly deferred Layer-11 provider operations.

## Finding ledger

| Finding | Result |
|---|---|
| `L10-R001` | **CLOSED** |
| `L10-R002` | **CLOSED** |
| `L10-R003` | **OPEN RUST-ONLY IMPLEMENTATION TARGET**, correctly disclosed and not a shared-contract blocker |
| `L10-R004` | **CLOSED** |
| `C10-C005` | **CLOSED** |
| `L10-R005` | **CLOSED** |
| `L10-R006` | **CLOSED** |
| `L10-R007` | **CLOSED** |
| `L10-R008` | **CLOSED** |

`L10-R008` is now closed in both current data and permanent enforcement. The validator checks that
every row's `tests` value is a non-empty list before iterating it, then checks every member is a
non-empty string. Direct synthetic witnesses cover scalar string, empty list, non-string member,
and valid list. The exact prior scalar witness is rejected. The real manifest has 84 unique rows,
all `tests` fields satisfy the invariant, and `AI-028` links the nine-call `L10-R007` scenario.

## Requirements and evidence

```text
AI-012  adopted provider-stream settlement boundary                 PASS
AI-028  adopted Adapter.stream contract                             PASS
AI-029  intentional eager full-identity resolution divergence      PASS
AI-030  owner-approved registry/withdrawal/introspection divergence PASS
AI-031  streamSimple deferred to external Layer-11 operation       PASS
AI-032  deferred fetch/cancel four-boundary contract                PASS
```

No row counts placeholder evidence as satisfied. Each difference is adopted, explicitly deferred,
or intentionally diverged with the required governance record.

Seven direct Layer-10 canonical scenarios pass through real Python `LlmService`/`MockAdapter`
operations. Schema/reference validation is language-neutral. The runner observes rather than
implements registration, replacement, withdrawal, resolution, introspection, or stream settlement.
Scenario-derived response provisioning is non-predictive and imposes no hidden fixed call cap.

## Rust implementability

Existing typed Rust `ModelIdentity`, `LlmRequest`, `LlmAdapter`, `AssistantStream`,
`ScriptedAdapter`, and `LlmService` are sufficient. Rust can independently:

- remove the expected eager adapter-start error channel and settle it in-stream;
- add per-call, repeatable/idempotent withdrawal ownership and current-model introspection;
- wire the seven scenarios through real Rust seams; and
- leave `streamSimple` and deferred provider operations to their stated Layer-11 owner.

No certified lower-layer redesign is required. Rust need not reproduce Python's object-token or
runner mechanics.

## Contract-quality result

```text
Pi mapping complete and accurate?                         YES
spec / manifest / canonical semantics coherent?           YES
runner thin and language-neutral?                         YES
manifest structure permanently validated?                 YES
Python implementation/evidence consistent?                YES
Rust independently implementable?                         YES
lower-layer reopen required?                              NO
unapproved observable divergence?                         NO
```

## Fresh gates

```text
Python full suite                         1171 passed, 19 xfailed, 0 failed
coverage                                  100.00%
ruff                                      PASS
mypy                                      PASS, 58 source files
conformance                               337 passed, 19 xfailed, 0 failed
manifest validation                       8 passed
manifest rows / unique IDs                84 / 84
manifest malformed tests fields           0
Layer-10 canonical scenarios              7 passed
Layer-10 runner validation                12 passed
targeted current Rust LLM tests            6 passed
```

## Findings and verdict

```text
PI_BEHAVIOR_UNCERTAIN       none
CONTRACT_ASSURANCE_DEFECT   none
PARITY_CONSTRAINED_RISK     none
unapproved divergence       none

PI_PARITY_DEFECT             L10-R003 — Rust-only implementation target, not shared/Python
```

```text
shared Layer-10 contract    APPROVED FOR RUST IMPLEMENTATION
Python Layer 10             CERTIFIED
Rust Layer 10               NOT_IMPLEMENTED
Layer 10 cross-language     NOT CLOSED
Layer 11                    NOT STARTED
```

The approved shared/Python candidate may merge under the exact-SHA rule. After it is merged, issue
#19 should transfer to Codex for a separate Rust Layer-10 implementation/certification pass.
