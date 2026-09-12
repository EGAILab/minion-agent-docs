# Layer 11 Pass 1 — Auth Foundation — Independent Rust Contract Review

## 1. Verdict

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

This verdict applies only to these exact, remote-reachable candidate commits:

```text
minion-agent PR #25
    56c8ae44029cd151d5ac68f0a0a2d97a449c216d

minion-agent-docs PR #54
    95a3715e11637561fbd2fb4f740a1aee514a6a51

pinned Pi
    b7bb00b936dbe21b8e160b3e89efdec361846699
```

The PR heads were fetched and rechecked before review. Both PRs were open, Ready for Review,
unmerged, and `CLEAN`. Issue `EGAILab/minion-agent#24` named these exact heads and
`NEXT_OWNER = Codex`. Default branches at review start were code
`ee2e046b1837b1b1107fbacfda6cc05db8af035a` and docs
`89ddc775bb826bace41abce97301a178382fdeef`.

## 2. Review mode and authority

This was review-only. No Rust, Python, shared spec, manifest, schema, or canonical candidate file
was changed. The review order was pinned Pi, normative spec, manifest, canonical evidence,
certified Rust architecture, assurance, then Python as secondary evidence.

Pinned Pi files read directly included:

- `packages/ai/src/auth/types.ts`
- `packages/ai/src/auth/context.ts`
- `packages/ai/src/auth/credential-store.ts`
- `packages/ai/src/auth/resolve.ts`
- `packages/ai/src/auth/oauth/pkce.ts`
- `packages/ai/src/auth/oauth/device-code.ts`
- `packages/ai/src/auth/oauth/openai-codex.ts`
- `packages/ai/src/models.ts`
- `packages/ai/src/utils/abort.ts`
- relevant auth/device-code tests and call sites

No Pi behavior remains uncertain for the findings below.

## 3. Manifest row review

| Row | Pi/source result | Contract/evidence result | Rust implementability | Verdict |
|---|---|---|---|---|
| PROV-006 | Basic credential/result vocabulary is source-grounded, but Pi's `AuthContext` interface does not normalize blank values. | The row/spec incorrectly promote the default context's trimming into the protocol contract. The broader public auth vocabulary is also not dispositioned. | Typed Rust values are feasible once the boundary is corrected and completed. | FAIL |
| PROV-007 | Per-provider serialized mutation, queued abort checkpoint, post-callback abort checkpoint, prompt public-wait cancellation, and nonserialized reads are clear in Pi. | Existing tests omit three discriminating cancellation cases; Python violates them. Value/reference and list-order observations are unspecified. | A per-key async serializer is feasible, but Rust must not guess the omitted observations. | FAIL |
| PROV-008 | Double-checked refresh, five-minute trigger, explicit post-refresh minimum, caller cancellation plus a 15-second refresh timeout, and error-class split are clear. | The callback type/spec/Python omit Pi's combined refresh signal and timeout. | Feasible once the shared signal/timeout rule is specified. | FAIL |
| PROV-009 | 32 random bytes, unpadded base64url verifier, SHA-256 challenge. | Spec, tests, and implementation agree. | Straightforward with existing Rust dependencies. | PASS |
| PROV-010 | State machine is mostly correct; Pi accepts a server interval only when finite and positive. | Spec/Python omit the finite check. The canonical runner is thin, but the server-interval scenario openly does not discriminate interval selection; language tests must carry that rule. | Feasible with typed outcomes and an injected clock/sleeper. | FAIL |
| PROV-011 | Codex account-id projection is a real later Layer-11 obligation. | Explicit deferred-parity row and closure criterion are credible. | Feasible later. | PASS (deferred) |
| PROV-012 | Codex browser/device transport behavior is a real later Layer-11 obligation. | Explicit deferred-parity row and closure criterion are credible. | Feasible later. | PASS (deferred) |

## 4. Canonical review

Six `auth_device_code` scenarios were discovered. The schema requires exactly one scripted poll
outcome and exactly one terminal expected result. The Python runner constructs typed outcomes,
calls the real `poll_device_code_flow`, injects only a clock/sleeper and scripted transport, and
normalizes the result. It does not implement retry, interval, deadline, or error semantics itself.

Runner thinness therefore passes. Coverage quality is narrower: the scenario
`auth-device-code-slow-down-prefers-server-interval` explicitly cannot distinguish use of the
server interval from ignoring it or adding five seconds. That is acceptable only if each language
has discriminating language evidence. It cannot compensate for L11-R004.

## 5. Blocking findings

### L11-R001 — CredentialStore cancellation does not match Pi

Classification: `PI_PARITY_DEFECT`

Pi/source basis:

- `auth/credential-store.ts:14-27` waits for the preceding mutation, checks the operation signal
  before invoking the queued task, and returns `raceWithAbortSignal(queued, signal)`.
- `modify` checks again after its callback and before commit.
- `delete` uses the same queued pre-task checkpoint.
- `utils/abort.ts::raceWithAbortSignal` rejects the caller-visible promise on abort while safely
  observing the abandoned operation.

Minimal executable witnesses against the exact candidate:

1. Hold modify A; queue modify B with a signal; abort B while queued; release A.
   Expected: B's callback is never called and A remains. Candidate: B's callback was called, then
   `CredentialStoreOperationCancelled` was raised.
2. Seed A; hold a modify; queue delete with a signal; abort delete while queued; release the hold.
   Expected: delete never runs and A remains. Candidate: the credential became absent.
3. Start a blocked modify callback; abort it while its callback remains blocked.
   Expected: the caller-visible wait rejects promptly, while the callback may continue in the
   background and its result is discarded. Candidate: after two event-loop turns the public task
   was still pending and rejected only after the callback was released.

Why discriminating: a check only before entering `asyncio.Lock` is not the Pi checkpoint after the
queue wait, and a post-callback check is not Pi's prompt caller-visible abort race.

Required remediation: specify and implement all three observations; add these exact permanent
regressions. The implementation mechanism need not copy JavaScript promise chains.

### L11-R002 — Refresh callback omits Pi's cancellation/timeout signal

Classification: `PI_PARITY_DEFECT`

Pi/source basis: `auth/types.ts::OAuthAuth.refresh` requires `(credential, signal)`. In
`resolve.ts:149-153`, `resolveStoredOAuth` passes a combined signal containing the caller signal
and `AbortSignal.timeout(15_000)`.

Candidate observation: `refresh_if_expiring` accepts
`Callable[[OAuthCredential], Awaitable[OAuthCredential]]` and invokes `refresh(current)`. Neither
PROV-008 nor `spec/auth.md` defines the combined caller/timeout signal or the 15-second bound.

Minimal witness: store an expiring credential and supply a refresh spy. Expected: the spy receives
a live signal which aborts on caller cancellation and independently after the 15-second refresh
budget. Candidate: no signal argument exists, so neither observation can be expressed.

Required remediation: add the language-neutral refresh-signal/budget rule to spec and manifest,
implement it without importing provider transport, and add caller-abort and timeout witnesses.
If the certified poll-only `RunSignal` cannot represent the required behavior, characterize the
smallest additive auth-owned signal/composition seam rather than omitting the Pi behavior.

### L11-R003 — AuthContext confuses the interface with its default implementation

Classification: `PI_PARITY_DEFECT`

Pi/source basis: `auth/types.ts:97-100` permits `env(name)` to resolve any `string | undefined`.
Only `auth/context.ts::defaultProviderAuthContext` trims and maps blank/whitespace values to
absence.

Candidate observation: PROV-006 and `spec/auth.md` require every `AuthContext.env` implementation
to normalize blank/whitespace to absent, and explicitly claim this is not merely default behavior.

Minimal witness: inject a custom context whose `env("TOKEN")` returns `""`. Pi's interface passes
that value through; the candidate contract declares the implementation nonconforming.

Required remediation: scope blank normalization to `DefaultAuthContext`. Keep the injectable
protocol's return domain `string | absent` without adding normalization that Pi does not require.

### L11-R004 — Device slow-down accepts a non-finite server interval

Classification: `PI_PARITY_DEFECT`

Pi/source basis: `auth/oauth/device-code.ts:81-86` adopts a server interval only when it is a
number, finite, and positive; otherwise it increments the current interval by five seconds.

Candidate observation: Python checks only `interval_seconds is not None and > 0`. With an infinite
server interval, a direct probe of the real poller scheduled `inf`; Pi would use current interval
plus five seconds. The shared spec omits the finite condition.

Minimal witness: initial interval 2, first result `slow_down(infinity)`, then complete. Expected
next scheduled interval: 7 seconds. Candidate scheduled interval: infinity.

Required remediation: pin finite-and-positive selection in spec/manifest and add a direct language
test using a non-finite typed input. Canonical JSON need not encode infinity.

### L11-R005 — The Layer-11 auth surface inventory is incomplete

Classification: `CONTRACT_ASSURANCE_DEFECT`

Pinned Pi's public auth vocabulary also contains `AuthPrompt`, `AuthInfoLink`, `AuthEvent`,
`AuthInteraction`, `ProviderAuthInteraction`, `ApiKeyAuth`, `OAuthAuth`, and `ProviderAuth`.
`Models` exposes the associated `checkAuth`, `getAuth`, `login`, and `logout` orchestration, and
`resolveProviderAuth` composes the resolution path.

The candidate's Layer-11 slice map accounts for auth foundation, Codex OAuth transport, two wire
adapters, `streamSimple`, deferred execution, and live verification, but assigns none of these
generic public auth surfaces to a later slice or manifest disposition. This is not a demand to
implement them in Pass 1. It is a demand not to silently lose discovered Pi public behavior.

Documentary witness: two independent Rust implementers following the current slice map can
reasonably choose either (a) to make Pass-1 vocabulary extensible for login interactions and
provider auth methods, or (b) to omit those types entirely because no future slice owns them.
Both choices satisfy the current artifacts but produce incompatible Layer-11 APIs.

Required remediation: add an explicit Layer-11 slice/requirement disposition and closure owner for
the missing generic auth/provider orchestration surface. Implement now only what the corrected
Pass-1 boundary actually owns.

### L11-R006 — Credential alias/copy semantics are undefined

Classification: `CONTRACT_ASSURANCE_DEFECT`

Pi's in-memory store holds mutable credential objects and `read`/`modify` expose those references.
Python uses frozen top-level dataclasses (with potentially mutable nested mappings). A Rust value
implementation will naturally tend to clone or share immutable values. The contract's claim that
`modify` is the only write path does not state whether credentials crossing the store boundary are
snapshots/values or live aliases, nor does it explicitly approve an architectural hardening away
from Pi's observable reference behavior.

Documentary witness: read a credential, mutate a returned top-level field, then read again. Pi's
in-memory implementation observes the mutation; Python rejects it; a reasonable Rust clone-based
implementation observes neither. The current spec permits all three answers.

Required remediation: explicitly choose value/snapshot or live-reference semantics and record the
Pi mapping/disposition. If value semantics are chosen, state that `modify` is the sole supported
mutation authority and classify the architectural difference accurately.

### L11-R007 — CredentialStore.list ordering is unspecified

Classification: `CONTRACT_ASSURANCE_DEFECT`

Pi's reference store iterates its insertion-ordered `Map`; Python iterates its insertion-ordered
`dict`; the test weakens the result to a set. Rust's existing architecture commonly uses hash maps,
whose iteration order is not stable. `spec/auth.md` exposes a list but says neither insertion order
nor explicitly unspecified order.

Documentary witness: insert providers `b`, then `a`, and call `list()`. A Rust implementation may
return insertion order, lexical order, or hash iteration while still satisfying the written rule.

Required remediation: pin the production order or explicitly declare it non-normative. If an
ordered canonical observation is later added, keep its evidence-only canonical sort separate from
the production API rule.

## 6. Non-blocking hardening

`PARITY_NEUTRAL_HARDENING`: the Pass-1 assurance says Pi's per-provider promise-chain map is
"never pruned", but `credential-store.ts:24-26` deletes the tail when it is still current. The
Python code's own docstring states the source behavior correctly. Correct the assurance source
audit without rewriting historical facts.

The candidate also discloses that the poll-only Minion signal checks a long device wait in 50 ms
slices rather than using Pi's push-triggered abort listener. The terminal outcome is specified,
but exact latency is not. This review does not add a blocker for timing precision; the accepted
contract should avoid claiming literal instant interruption.

## 7. Rust architecture feasibility

The certified Rust tree already provides typed runtime signals, Tokio async synchronization,
typed model/LLM vocabulary, deterministic test infrastructure, SHA-256 support, and canonical
runner conventions. A typed auth module, per-provider mutation serializer, PKCE helper, and device
poller can be implemented without redesigning Layers 01-10.

No lower-layer reopen is currently required. L11-R002 may require an additive auth-owned timeout
or signal-composition capability, but the candidate must first specify the observable boundary.
No Rust implementation should begin against the current incomplete contract.

## 8. Fresh evidence and gates

Executed against code candidate `56c8ae44029cd151d5ac68f0a0a2d97a449c216d`:

- full `uv run --project minion-agent-python pytest minion-agent-python/tests -q`: exit 0; the
  candidate's reported 1,251 passed / 19 xfailed profile was reproduced, with source coverage at
  100%;
- focused auth + device canonical + manifest suite: 78 passed;
- `ruff check` on changed auth/test runner surfaces: PASS;
- `mypy` on the auth package: PASS;
- manifest/schema tests: PASS;
- six auth-device-code scenarios discovered and executed through the real Python poller.

Green candidate tests do not close the discriminating gaps above; the current suite lacks those
witnesses.

## 9. Findings summary

```text
PI_BEHAVIOR_UNCERTAIN
    none

PI_PARITY_DEFECT
    L11-R001 CredentialStore cancellation boundary
    L11-R002 refresh signal and timeout
    L11-R003 AuthContext default/protocol distinction
    L11-R004 finite slow-down interval

CONTRACT_ASSURANCE_DEFECT
    L11-R005 incomplete generic auth surface disposition
    L11-R006 credential alias/copy semantics undefined
    L11-R007 CredentialStore.list ordering undefined

PARITY_NEUTRAL_HARDENING
    assurance incorrectly says Pi's chain map is never pruned

PARITY_CONSTRAINED_RISK
    none
```

## 10. Narrow next action

Return the exact candidate to the shared/Python owner. Remediate L11-R001 through L11-R007,
convert the executable witnesses into permanent regressions, correct the assurance statement, and
push new exact PR heads. Any changed candidate SHA requires a new independent Rust contract
review. Do not implement Rust Layer 11 and do not start Layer 12.
