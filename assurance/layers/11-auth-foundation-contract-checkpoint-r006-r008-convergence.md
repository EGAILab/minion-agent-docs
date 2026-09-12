# Layer 11 Auth Foundation — L11-R006/R008 Contract Convergence Characterization

```text
STATUS
    PROPOSED — AWAITING SHARED-OWNER CHALLENGE AND OWNER GOVERNANCE

OPEN FINDINGS
    L11-R006
    L11-R008

PINNED PI
    b7bb00b936dbe21b8e160b3e89efdec361846699

REJECTED CANDIDATE
    code 0027bd75462c7b9b4c869569b67772cf45ef1b33
    docs a389b284ac90f2b47d9d3b101da6681f899272dc
```

## Open surface

L11-R006 has survived two independent reviews, automatically triggering §11.8 convergence. It
concerns the semantic identity of a credential crossing constructor/store boundaries: mutable live
reference versus deeply immutable value. L11-R008 is the adjacent AuthContext protocol/default
mapping regression introduced by Pass 2.

## Pi symbols audited

- `packages/ai/src/auth/types.ts::ApiKeyCredential/OAuthCredential/Credential/AuthContext`
- `packages/ai/src/auth/credential-store.ts::InMemoryCredentialStore`
- `packages/ai/src/auth/context.ts::defaultProviderAuthContext`

## Observable rules and behavior matrix

### Credential policy decision

| Observation | Pi live-reference baseline | Proposed immutable-value alternative | Pass-2 candidate |
|---|---|---|---|
| mutate top-level field after read | later read observes mutation | mutation unavailable | unavailable |
| mutate original outer mapping after construction | credential observes same reference | credential unchanged | credential unchanged |
| mutate nested dict/list in original `extra` | credential observes mutation | credential unchanged | **credential changes** |
| mutate nested dict/list through returned `extra` | later reads observe mutation | mutation unavailable | **mutation succeeds** |
| open arbitrary JSON domain retained | yes | must remain yes | yes, but mutable nested containers |
| sole supported write authority | intended `modify`, though raw JS references permit bypass | `modify` structurally enforced | outer layer only |
| manifest disposition | adopted baseline | intentional divergence, owner-approved | mixed into adopted PROV-006 |

The convergence decision is not whether to use `MappingProxyType`, `Arc`, cloning, or another
mechanism. It is whether Minion adopts Pi's live-reference observation or intentionally chooses
deep immutable JSON values. The latter requires explicit §11.7 owner approval.

### AuthContext boundary

| Method/rule | Pi interface | Pi default implementation | Correct shared mapping |
|---|---|---|---|
| `env` returns blank | permitted | blank/whitespace normalized absent | protocol permits; default normalizes |
| `fileExists` leading `~` | supported by interface | expands and checks native filesystem | protocol supports leading `~` |
| browser file existence | always false | browser branch returns false | disposition only if Minion has browser target |
| injected test double | may be scripted | N/A | may avoid real I/O but must model the call's contract when used as semantic implementation |

## Minimal acceptance witnesses

### W-R006-1 — nested constructor alias

Construct `OAuthCredential.extra` with nested dictionary and list values. Mutate both nested
containers through the original constructor input.

- Pi-live-reference choice: mutations remain observable.
- approved immutable-value choice: credential remains unchanged.
- Pass-2 candidate: mutations remain observable despite claiming deep immutability.

### W-R006-2 — nested returned-value mutation

Attempt to mutate a nested dictionary and append to a nested list through `credential.extra`.

- Pi-live-reference choice: succeeds and remains observable.
- approved immutable-value choice: structurally rejected, or mutates only a detached value whose
  later credential observation remains unchanged, according to the agreed language-neutral rule.
- Pass-2 candidate: succeeds and changes the credential.

### W-R006-3 — open JSON preservation

Round-trip nested objects, arrays, strings, numbers, booleans, and null through the selected
credential representation. No deep-freeze mechanism may narrow PROV-006's open JSON domain.

### W-R008-1 — tilde-aware protocol implementation

Provide a non-default native `AuthContext`, call `file_exists("~/credential")`, and prove the path
is interpreted with home-directory semantics rather than as a literal relative filename. This is
separate from testing `DefaultAuthContext` itself.

## Current candidate failures

- W-R006-1: FAIL — shallow outer copy retains nested aliases.
- W-R006-2: FAIL — `MappingProxyType` does not freeze nested values.
- W-R006-3: PASS for domain breadth, but no deep immutable realization.
- W-R008-1: contract says the contrary behavior is conforming; no protocol-level witness exists.

## Normative/evidence deltas needed

1. Give credential value/reference semantics one coherent manifest subject and disposition.
2. If immutable values are chosen, record owner approval and specify recursive JSON value behavior
   without prescribing a language container mechanism.
3. Add W-R006-1 through W-R006-3 as permanent language evidence.
4. Correct `spec/auth.md`, PROV-006/AuthContext evidence, and protocol documentation so blank-env
   normalization remains default-only while leading-tilde support remains interface-level.
5. Add W-R008-1 or an equivalent discriminating protocol-level witness.

## Implementation constraints

- Do not narrow `OAuthCredential.extra` from arbitrary JSON.
- Do not place both `adopted` behavior and an intentional divergence under one row disposition.
- Do not treat a shallow read-only outer map as a deep immutable value.
- Do not copy Python container mechanics into Rust.
- Do not reopen Layer 09; neither finding requires a signal change.
- Do not implement real provider transport, browser OAuth, or Layer 12.

## Convergence checkpoint state

```text
CONVERGENCE CONTRACT
    NOT YET AGREED

NEXT OWNER
    Claude

NEXT ACTION
    Challenge this Pi mapping and behavior matrix, obtain owner approval if choosing the
    immutable-value divergence, then record AGREED FOR IMPLEMENTATION before changing code.
```
