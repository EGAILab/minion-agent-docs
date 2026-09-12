# Layer 11 Auth Foundation — L11-R006/L11-R008 Targeted Closure Review

## Review target

```text
code PR #25
    ffe43baf122e25156c6d206343fee07c3c849d6c

docs PR #54
    843b6581312c5dedece91beaae2eb9832fd29529

pinned Pi
    b7bb00b936dbe21b8e160b3e89efdec361846699

prior convergence characterization
    docs PR #56 @ 3d0f07e79b7a97b57e76e6417c9c3049daa06a66
```

Both candidate heads were fetched from GitHub, matched the handoff comment on coordination issue
`EGAILab/minion-agent#24`, were open, non-draft, and remote-reachable. This review is scoped by
`agent-workflow.md` §11.8.7 to L11-R006, L11-R008, the PROV-006/PROV-007 dependencies touched by
their convergence implementation, and directly affected evidence. No Rust implementation or
Layer-12 work was performed.

## Pi source re-audit

The review independently re-read pinned:

- `packages/ai/src/auth/types.ts::ProviderEnv` (`Record<string, string>`);
- `packages/ai/src/auth/types.ts::ApiKeyCredential/OAuthCredential/Credential/AuthContext`;
- `packages/ai/src/auth/credential-store.ts::InMemoryCredentialStore`.

Pi credential records and their nested objects are ordinary mutable JavaScript objects. The
in-memory store retains and returns the same credential references. `AuthContext.fileExists` places
leading-`~` support directly on the interface contract. `ProviderEnv`, however, is specifically a
string-to-string record; recursive arbitrary JSON belongs to OAuth's open extra fields, not API-key
`env` values.

## Targeted closure ledger

### L11-R006 — still open

Classification: `PI_PARITY_DEFECT` plus a contract/evidence dependency.

The convergence implementation correctly removes the shallow `MappingProxyType(dict(...))`
snapshot. Runtime probes confirmed that a mutable dictionary passed as `env` is retained by
identity and that top-level mutation is observable afterward. The constructor-aliasing tests also
distinguish the rejected shallow-copy candidate.

The public typed surface and permanent evidence do not yet implement the full agreed rule:

1. `ApiKeyCredential.env` remains annotated as read-only `Mapping[str, str]`, and
   `OAuthCredential.extra` as read-only `Mapping[str, JsonValue]`. A typed caller therefore cannot
   perform the contract-required top-level mutation through the returned credential. Candidate
   tests need `# type: ignore` even for the narrower nested operations. A direct mypy probe rejects
   `credential.env["NEW"] = "v"` as `Unsupported target for indexed assignment`.
2. None of W-R006-1/2/3 assigns a new top-level key through the returned `env`/`extra` mapping.
   That is the most direct witness distinguishing the agreed mutable mapping from the prior
   `MappingProxyType` surface. W-R006-2 mutates only nested containers, which the rejected shallow
   wrapper already permitted.

Minimal witness:

```text
setup
    credential = ApiKeyCredential(env={})

operation
    credential.env["NEW"] = "v" through the supported typed API

expected
    assignment is type-valid and succeeds; later credential/store reads observe "v"

candidate
    runtime dict mutation succeeds, but the declared Mapping API rejects the operation;
    no permanent witness exercises it
```

L11-R006 is therefore not provisionally closed at these SHAs.

### L11-R008 — still open

Classification: `CONTRACT_ASSURANCE_DEFECT`.

The normative spec, PROV-006, and `AuthContext` protocol documentation now correctly place
leading-`~` support at protocol level. The promised W-R008-1 evidence is non-discriminating:

```python
home_relative = os.path.expanduser("~")
await ctx.file_exists(home_relative)
```

The value passed to `file_exists` is already an absolute home path and no longer begins with `~`.
A deliberately non-conforming implementation that calls `Path(path).exists()` without expansion
passes this test. The same implementation returns false for the actual input `"~"` in the review
workspace.

Minimal witness:

```text
setup
    a non-default AuthContext implementation and a known existing home-relative target

operation
    call file_exists with an input that still begins with "~"

expected
    the implementation expands the leading tilde and reports the target correctly

candidate evidence
    expands before the call, so it cannot distinguish literal-path handling from compliant tilde
    expansion
```

Replace W-R008-1 with an actual leading-tilde input and retain the non-default implementation.

## New findings on the directly touched credential surface

### L11-R009 — frozen scalar credential fields contradict live-reference parity

Classification: `PI_PARITY_DEFECT`.

The corrected spec and manifest say Minion adopts Pi's plain mutable credential-object behavior,
but both Python credential dataclasses remain `frozen=True`. Pi's returned live credential permits
mutation of scalar fields such as API key, OAuth access token, refresh token, and expiry; a later
store read observes the same object. Python raises `FrozenInstanceError` before such a mutation.
No intentional divergence is dispositioned or approved for scalar fields.

Minimal witness:

```text
setup
    store an ApiKeyCredential(key="A") and retain/read the live credential

operation
    set key = "B" on that returned credential

Pi expected
    succeeds; later read sees "B"

candidate
    FrozenInstanceError: cannot assign to field 'key'
```

Either adopt Pi's complete mutable credential-record behavior or seek explicit owner approval and
a coherent manifest disposition for a narrower scalar-field divergence. The existing governance
decision explicitly approved no divergence.

### L11-R010 — API-key env domain is over-broadened in the convergence contract/tests

Classification: `PI_PARITY_DEFECT`.

Pinned `ProviderEnv` is `Record<string, string>`. The convergence agreement/spec repeatedly apply
recursive nested-dict/list and open-JSON requirements jointly to `env` and `extra`, and W-R006-1
constructs an `ApiKeyCredential.env` containing a nested object and list despite the candidate's
own `Mapping[str, str]` annotation. This is outside Pi's API-key environment domain. OAuth open
fields may contain recursive JSON; API-key `env` values may not.

Narrow remediation: split the language-neutral rules and evidence. Require a mutable outer
string-to-string mapping for API-key `env`; require recursive open-JSON live aliasing for OAuth
`extra`. Do not use statically invalid nested `env` fixtures as parity evidence.

## Directly affected regressions and gates

Fresh review observations at the exact candidate:

```text
credential/context/store focused tests
    40 passed with coverage enforcement disabled for the focused run

auth source mypy
    PASS (8 source files)

manifest validation
    8 passed

direct runtime env identity/top-level mutation probe
    PASS at runtime

typed top-level env mutation probe
    FAIL: Mapping does not support indexed assignment

R008 negative-control probe
    a literal, non-expanding implementation passes W-R008-1's already-expanded input
```

The focused suite's first invocation triggered the repository-wide 100% coverage threshold because
only auth tests were selected; it was rerun with coverage disabled and all 40 selected tests passed.
This is not a candidate test failure. Full release gates are deferred because the targeted closure
gate is already blocked.

PROV-007's serialized `modify()` guarantee and the provisionally closed R001/R007 store behavior
were not changed by the candidate and their selected tests remain green. No lower-layer semantic
reopen is required.

## Verdict

```text
L11-R006
    STILL OPEN / BLOCKING

L11-R008
    STILL OPEN / BLOCKING

L11-R009
    NEW / BLOCKING

L11-R010
    NEW / BLOCKING

shared Layer-11 Auth Foundation contract
    REJECTED AT TARGETED CLOSURE GATE

Rust Layer 11
    BLOCKED / NOT_IMPLEMENTED

Layer 11 cross-language
    NOT CLOSED

Layer 12
    NOT STARTED
```

Remain in `CONTRACT_CONVERGENCE`. Revise the agreed credential matrix to distinguish API-key env
from OAuth extra, align the Python typed/mutable record surface with the chosen Pi semantics,
replace the non-discriminating tilde witness, and cover scalar credential mutability or obtain the
required owner divergence decision. Return one exact remote candidate for another targeted closure
review. A final complete §11.8.8 review remains required only after all blockers are provisionally
closed.
