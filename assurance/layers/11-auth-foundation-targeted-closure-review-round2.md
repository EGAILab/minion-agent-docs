# Layer 11 Auth Foundation — Targeted Closure Review, Round 2

## Exact target

```text
code PR #25
    f7a754038063f35be7aa87641a29d883243475f1

docs PR #54
    8883ce6c29396d3fb0f25899aa706055c9fc63f8

pinned Pi
    b7bb00b936dbe21b8e160b3e89efdec361846699

prior targeted review
    docs PR #57 @ b3e6a88cfa1f0399cf02a7f53287e9c09af7ac37
```

The paired candidates were fetched from GitHub and matched the latest handoff on coordination
issue `EGAILab/minion-agent#24`. Both PRs were open, non-draft, and remote-reachable. This is the
`agent-workflow.md` §11.8.7 targeted re-review of L11-R006/L11-R008/L11-R009/L11-R010 and their
direct PROV-006/PROV-007 dependencies. No Rust implementation or Layer-12 work was performed.

## Independent Pi recheck

The review rechecked pinned:

- `packages/ai/src/types.ts::ProviderEnv` — `Record<string, string>`;
- `packages/ai/src/auth/types.ts::ApiKeyCredential/OAuthCredential/AuthContext`;
- `packages/ai/src/auth/credential-store.ts::InMemoryCredentialStore`.

Pi uses mutable credential records and retains/returns their references from its in-memory store.
API-key `env` is a mutable flat string-to-string record. OAuth's open index signature carries the
recursive provider-specific value domain. `AuthContext.fileExists` requires leading-tilde support
at interface level.

## Finding closure ledger

### L11-R006 — still open, evidence-only remainder

Classification: `CONTRACT_ASSURANCE_DEFECT`.

The production/API correction itself is now right:

- `env` is `dict[str, str] | None`;
- `extra` is `dict[str, JsonValue]`;
- both retain constructor identity and permit new top-level keys;
- store reads expose those mutations;
- a direct reviewer mypy probe accepting `credential.env["NEW"] = "v"` now passes.

The permanent regression evidence does not run the relevant static check. The normal configured
mypy gate checks `src/minion_agent` only. The new assignments live in pytest files, which pytest
executes dynamically but mypy does not inspect. Reverting the public annotations from mutable
`dict` to read-only `Mapping` would leave the reported standard source-mypy gate and runtime tests
green—the exact typed-surface regression that triggered L11-R006 would silently recur.

This violates the reviewer-witness rule: the implementation owner must turn the exact typed
observation into permanent regression evidence, not only state that an ad-hoc positive check was
run. Add an auth typing fixture following the existing `tests/typing/valid_*_construction.py`
convention and execute it in the recorded typing gate. It must cover, without `type: ignore`:

```text
ApiKeyCredential.env new-key assignment
OAuthCredential.extra new-key assignment
ApiKeyCredential.key reassignment
OAuthCredential access/refresh/expires reassignment
```

No production or semantic change is otherwise required for L11-R006.

### L11-R008 — provisionally closed

The protocol/spec/manifest rule remains correct. W-R008-1 now passes the literal string `"~"` to
a non-default implementation. The paired negative-control implementation omits expansion and
returns false for the same literal input in the review workspace. This directly distinguishes the
previous already-expanded-input defect.

Status: `PROVISIONALLY CLOSED @ code f7a754038063f35be7aa87641a29d883243475f1 / docs
8883ce6c29396d3fb0f25899aa706055c9fc63f8`.

Non-blocking hardening: the negative control depends on the working directory not containing an
entry literally named `~`. A temporary/home-injected known target would make the witness fully
hermetic, but the present witness exercised the required distinction and passed.

### L11-R009 — provisionally closed

Both credential dataclasses are no longer frozen. Direct tests cover API-key and all required OAuth
scalar fields; a store integration test proves mutation of a returned credential is observed by a
later read. The remediation adopts Pi rather than introducing a divergence.

Status: `PROVISIONALLY CLOSED @ code f7a754038063f35be7aa87641a29d883243475f1 / docs
8883ce6c29396d3fb0f25899aa706055c9fc63f8`.

### L11-R010 — provisionally closed

The normative and typed domains are now separated correctly:

- API-key `env`: `dict[str, str]`, with only flat string fixtures;
- OAuth `extra`: recursive `JsonValue`, with nested alias/mutation evidence.

The spec and PROV-006 agree, and no nested API-key env fixture remains in the changed evidence.

Status: `PROVISIONALLY CLOSED @ code f7a754038063f35be7aa87641a29d883243475f1 / docs
8883ce6c29396d3fb0f25899aa706055c9fc63f8`.

## Fresh targeted gates

```text
credential/context/store tests
    47 passed

auth source mypy
    PASS — 8 source files

manifest validation
    8 passed

ad-hoc exact positive mypy witness
    PASS — 1 source snippet

permanent typed-witness gate
    ABSENT
```

The selected tests were run with coverage disabled because a focused subset cannot satisfy the
repository-wide 100% threshold. This is not a candidate failure. Full release gates remain for the
mandatory §11.8.8 complete review after the last blocker closes.

PROV-007's serialized store semantics remain unchanged and its affected tests pass. No certified
lower-layer delta is required.

## Findings

```text
PI_BEHAVIOR_UNCERTAIN
    none

PI_PARITY_DEFECT
    none active on the remediated runtime semantics

CONTRACT_ASSURANCE_DEFECT
    L11-R006 — exact typed mutable-surface witness is not permanent or part of a gate

PARITY_NEUTRAL_HARDENING
    make the R008 negative control independent of the process working directory

PARITY_CONSTRAINED_RISK
    none
```

## Verdict and next action

```text
L11-R006
    STILL OPEN / BLOCKING

L11-R008
    PROVISIONALLY CLOSED

L11-R009
    PROVISIONALLY CLOSED

L11-R010
    PROVISIONALLY CLOSED

shared Layer-11 Auth Foundation contract
    NOT YET APPROVED FOR RUST IMPLEMENTATION

Rust Layer 11
    BLOCKED / NOT_IMPLEMENTED

Layer 11 cross-language
    NOT CLOSED

Layer 12
    NOT STARTED
```

Remain in the existing convergence episode. Add and actually execute the permanent positive auth
typing fixture; no further semantic redesign is requested. Return exact remote SHAs for one more
targeted L11-R006 closure check. Only after that finding is provisionally closed should the
mandatory final complete §11.8.8 review begin.
