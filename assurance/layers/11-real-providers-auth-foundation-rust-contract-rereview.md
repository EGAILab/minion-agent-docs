# Layer 11 Pass 1 — Auth Foundation — Independent Rust Contract Re-review

## 1. Exact target and verdict

```text
code PR #25
    0027bd75462c7b9b4c869569b67772cf45ef1b33

docs PR #54
    a389b284ac90f2b47d9d3b101da6681f899272dc

prior rejected review
    docs PR #55 @ a97a683ab11e7115074447672f7fa107f89c4de5

pinned Pi
    b7bb00b936dbe21b8e160b3e89efdec361846699
```

Both candidate PRs were fetched and verified open, Ready for Review, unmerged, and `CLEAN`. Issue
`EGAILab/minion-agent#24` named Codex and the exact heads above. The issue body was reconciled from
its stale Pass-1 rejection block to the current Pass-2 re-review target before substantive review.

```text
shared Layer-11 Pass-1 auth-foundation contract
    REJECTED

Python Layer 11 Pass 1
    REOPENED

Rust Layer 11
    BLOCKED / NOT_IMPLEMENTED

Layer 11 cross-language
    NOT CLOSED

Layer 12
    NOT STARTED
```

The remediation closes L11-R001 through L11-R005 and L11-R007. L11-R006 remains open with a
refined executable witness, and the AuthContext correction introduced new finding L11-R008.
Because the same material L11-R006 finding has now survived two independent reviews, the mandatory
`agent-workflow.md` §11.8 convergence trigger is met.

## 2. Independence and scope

Review only. No candidate code, shared semantic file, canonical file, or Rust implementation was
changed. Review order remained pinned Pi, spec, manifest, canonical evidence, certified Rust
architecture, Pass-2 assurance, then Python as secondary evidence.

Pinned Pi sources rechecked included:

- `packages/ai/src/auth/types.ts`
- `packages/ai/src/auth/context.ts`
- `packages/ai/src/auth/credential-store.ts`
- `packages/ai/src/auth/resolve.ts`
- `packages/ai/src/auth/oauth/device-code.ts`
- `packages/ai/src/utils/abort.ts`
- `packages/ai/src/models.ts`

## 3. Finding closure ledger

| Finding | Independent result | Status at exact candidate |
|---|---|---|
| L11-R001 | The new per-provider task chain has Pi's queued pre-task checkpoint, post-callback discard checkpoint, caller-visible abort race, failure isolation, and tail pruning. The original three witnesses pass and are discriminating. | PROVISIONALLY CLOSED |
| L11-R002 | `refresh` receives a live second `Abortable` combining the caller signal and an independently expiring 15-second budget. Tests prove both OR branches. Layer 09 is not modified. | PROVISIONALLY CLOSED |
| L11-R003 | Blank normalization is now correctly limited to `DefaultAuthContext`; an injected context may return an empty string. | PROVISIONALLY CLOSED |
| L11-R004 | Server `slow_down` interval selection now requires finite and positive; the exact infinity witness schedules 7 seconds from initial interval 2. | PROVISIONALLY CLOSED |
| L11-R005 | PROV-013 explicitly inventories and defers the generic login/provider/orchestration vocabulary to a real provider-integration slice. | PROVISIONALLY CLOSED |
| L11-R006 | The selected immutable-value contract is only shallowly implemented, the adopted PROV-006 row mixes dispositions, and no owner approval for the observable intentional divergence is recorded. | STILL OPEN / BLOCKING |
| L11-R007 | Production `list()` insertion order and delete/reinsert-to-tail behavior are normative and have exact ordered tests. | PROVISIONALLY CLOSED |

`PROVISIONALLY CLOSED` is exact-SHA finding closure, not final approval. A final complete review is
still required after convergence remediation.

## 4. L11-R001 through L11-R005 and L11-R007 evidence

### L11-R001 — closed

The exact original witnesses pass through the real `InMemoryCredentialStore`:

1. abort queued modify: its callback never runs;
2. abort queued delete: the removal never runs;
3. abort during an in-flight callback: caller returns with cancellation before callback release;
   background completion is retained and its result discarded.

The chain's `tail` consumes predecessor failure and prunes only if it remains the current tail,
matching Pi's observable FIFO/failure behavior. The Python mechanism need not be Rust's mechanism.

### L11-R002 — closed

`CombinedSignal` is auth-owned and structurally implements the single `aborted` observation. Its
deadline begins at the authoritative under-lock refresh attempt. `refresh_if_expiring` passes it
to the refresh callback. Caller abort and independent timeout tests both pass. No lower-layer
semantic delta is required.

### L11-R003 — closed, with an affected-surface regression

The exact blank-value defect is closed. The wider edit to the same `AuthContext` paragraph
incorrectly weakened `file_exists`; that is tracked separately as L11-R008 below rather than
reopening the already-closed blank-value sub-finding.

### L11-R004 — closed

The candidate uses `math.isfinite(server_interval) and server_interval > 0`, directly matching
Pi's `Number.isFinite(...) && ... > 0`. The new elapsed-time test is discriminating even though
the existing canonical scenario remains outcome-only.

### L11-R005 — closed

PROV-013 names the exact missing Pi types and Models orchestration, uses `deferred parity`, cites no
fabricated executable evidence, and binds closure to a future real-provider login integration.

### L11-R007 — closed

Spec and PROV-007 now require insertion order of current entries. Tests distinguish `b,a` from
lexical order and separately prove delete/reinsert moves a provider to the tail. Rust can implement
this with an ordered map or explicit order tracking.

## 5. Blocking findings

### L11-R006 — claimed deep immutable credential values remain shallow and ungoverned

Classification: `CONTRACT_ASSURANCE_DEFECT`

Pi/source basis: Pi stores mutable credential objects by reference. The Pass-2 contract instead
chooses an observable immutable-value model and calls it an `intentional divergence`.

Candidate rule: `spec/auth.md` and PROV-006 say a Credential is "fully immutable at every level"
and constructor mappings are snapshotted. Python wraps only a shallow `dict(...)` copy in
`MappingProxyType`. `OAuthCredential.extra` permits recursive JSON values, including dictionaries
and lists.

Minimal executable witness:

```python
source = {"nested": {"value": "A"}, "items": ["A"]}
credential = OAuthCredential(access="a", refresh="r", expires=1, extra=source)
source["nested"]["value"] = "B"
source["items"].append("B")
```

Expected under the candidate's own normative rule: `credential.extra` remains deeply equal to the
original value. Observed: it becomes `{"nested": {"value": "B"}, "items": ["A", "B"]}`.
Mutating `credential.extra["nested"]["value"]` and appending through
`credential.extra["items"]` also succeeds.

This is discriminating: the existing tests use only flat string values, so they prove outer-map
protection but not the contract's "every level" rule.

Two additional assurance problems remain:

1. PROV-006 has overall disposition `adopted` while embedding this explicit intentional
   divergence in the same semantic row. One row cannot coherently mean both.
2. No §11.7 owner approval is recorded for replacing Pi's observable live mutable references with
   immutable values. The shared-contract owner cannot self-approve an intentional Pi divergence.

Required convergence outcome: choose and govern either Pi-compatible live-reference behavior or a
deep immutable value model. If immutable values are approved, recursively snapshot/freeze every
JSON container, preserve the open JSON domain, add nested dict/list witnesses, and split the
divergence into its own coherent manifest row. Record explicit owner approval. Rust must receive a
language-neutral value rule, not `MappingProxyType` mechanics.

### L11-R008 — AuthContext remediation incorrectly weakens file_exists

Classification: `PI_PARITY_DEFECT`

Pi/source basis: `auth/types.ts:97-100` places this documentation on the `AuthContext` interface:

```text
Check whether a file exists. Supports a leading `~`. Always false in browsers.
```

Candidate observation: the remediated `spec/auth.md` and Python protocol docstring now call
leading-`~` support "specific to DefaultAuthContext" and explicitly say it is not a protocol-level
guarantee. This overcorrects L11-R003. Blank normalization is default-only; leading-`~` support is
stated on Pi's interface itself.

Minimal documentary witness: a non-browser `AuthContext` implementation treats `~/token` as a
literal relative path. The candidate calls it conforming; pinned Pi's interface contract does not.

Required remediation: keep the corrected default-only blank normalization, but restore
leading-`~` support to the language-neutral `file_exists` contract. Record browser behavior only
if Minion retains a browser target; otherwise state the native-only architectural scope without
weakening tilde support. Add a protocol-level conformance witness distinct from the default
implementation's existing test.

## 6. Contract convergence characterization

The dedicated convergence checkpoint in this review branch records the §11.8.3 behavior matrix,
witnesses, governance requirement, and implementation constraints for L11-R006/L11-R008:

`assurance/layers/11-auth-foundation-contract-checkpoint-r006-r008-convergence.md`

The root extensibility points exist in both languages: credentials carry recursive JSON values and
both languages expose an injectable AuthContext. Rust does not inherit Python's shallow-wrapper
mechanism, but it would be forced to guess deep-value versus live-reference semantics unless the
checkpoint is resolved.

## 7. Canonical and quality gates

Fresh checks against code candidate `0027bd75462c7b9b4c869569b67772cf45ef1b33`:

- full Python suite: exit 0; 1,286 tests collected, matching 1,267 passed plus 19 expected failures;
- source coverage: 100%;
- exact L11-R001–R007 remediation selection: 10/10 passed;
- Ruff: PASS;
- mypy: PASS on 66 source files;
- manifest/schema/device canonical selection: PASS;
- manifest: 92 rows / 92 unique ids;
- auth-device-code scenarios: 6 discovered and passing through the real poller;
- candidate Rust diff: none.

The deep-nested credential probe fails the candidate contract as reported above. Green committed
tests do not close that missing witness.

## 8. Rust feasibility and lower-layer impact

Rust can implement the provisionally closed R001-R005/R007 rules idiomatically with Tokio tasks,
typed auth values, an auth-local combined cancellation view, and deterministic ordered storage.
No certified Layer 01-10 semantic delta is required.

R006 must converge first. A deep owned JSON value is natural in Rust, but choosing it is a shared
semantic/governance decision, not a Rust implementation detail. R008 is documentary plus focused
evidence; the existing Rust architecture can implement it without redesign.

## 9. Findings summary

```text
PI_BEHAVIOR_UNCERTAIN
    none

PI_PARITY_DEFECT
    L11-R008 AuthContext.file_exists interface semantics weakened

CONTRACT_ASSURANCE_DEFECT
    L11-R006 credential value/reference semantics still unresolved in practice and governance

PARITY_NEUTRAL_HARDENING
    none active (the chain-pruning correction is closed)

PARITY_CONSTRAINED_RISK
    none
```

## 10. Next action

Enter `CONTRACT_CONVERGENCE` for L11-R006/L11-R008. The shared/Python owner should challenge the
companion characterization against Pi, obtain owner governance for any intentional immutable-value
divergence, record an agreed checkpoint, and only then implement the coherent fix. New exact code
and docs SHAs require targeted closure followed by one final complete review. Do not implement
Rust Layer 11 and do not start Layer 12.
