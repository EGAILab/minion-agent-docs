# Layer 11 — L11-R006/L11-R008 convergence agreement

## Decision

```text
CONVERGENCE CONTRACT
    AGREED FOR IMPLEMENTATION
```

Exact checkpoint reviewed:

- code PR `EGAILab/minion-agent#25` at `0027bd75462c7b9b4c869569b67772cf45ef1b33`;
- docs PR `EGAILab/minion-agent-docs#54` at `a389b284ac90f2b47d9d3b101da6681f899272dc`;
- pinned Pi at `b7bb00b936dbe21b8e160b3e89efdec361846699`;
- originating re-review: docs PR #56 at `3d0f07e79b7a97b57e76e6417c9c3049daa06a66`;
- characterization checkpoint:
  `assurance/layers/11-auth-foundation-contract-checkpoint-r006-r008-convergence.md`.

The exact docs checkpoint and coordination issue #24 were fetched from GitHub. Issue #24 recorded
`STATUS = CONTRACT_CONVERGENCE` and `NEXT_OWNER = Claude`. This is convergence-challenge/agreement
evidence only; no candidate code, shared semantic file, or Rust production was changed by writing
this document.

## Trigger check (agent-workflow.md §11.8, mandatory)

`L11-R006`: this exact finding was raised by the Pass-1 review (docs PR #55) and survived
remediation to be raised again, in refined form, by the Pass-2 re-review (docs PR #56) --
`same material finding survives two independent reviews`, the first of the two OR conditions in
§11.8's own trigger. Convergence is therefore mandatory, not optional, and this document is that
convergence's own required checkpoint -- not a third ordinary point-fix pass.

`L11-R008` is a NEW finding (first raised by docs PR #56), below the two-repeat/three-rejection
threshold on its own. It is folded into this same convergence document because the characterization
checkpoint groups it with `L11-R006` as one tightly-coupled `AuthContext`/credential-boundary
surface (the §11.8 allowance for a reviewer to recommend early convergence when remaining blockers
form one semantic surface) -- not because `L11-R008` independently met the trigger.

## Challenge pass (§11.8.4)

Independently re-verified, this pass, directly against pinned Pi source (not merely trusted from
the characterization checkpoint's own prose):

- `packages/ai/src/auth/types.ts:24-29` (`OAuthCredentials`): a plain TypeScript interface with an
  open index signature (`[key: string]: unknown`) -- confirmed there is no `Object.freeze`,
  `Readonly<...>`, or any other immutability mechanism anywhere in this type or its own producers.
- `packages/ai/src/auth/credential-store.ts:9-36` (`InMemoryCredentialStore`): confirmed `read`,
  `list`, and `modify`'s own `current`/`next` all hold direct references into (or returned
  directly from) the SAME `Map<string, Credential>` -- no cloning, no snapshotting, at any point.
  A caller holding a reference obtained from `read()` and mutating a nested field on it directly
  WOULD observably affect a later `read()` for the same provider id, with nothing in Pi's own
  implementation preventing this.
- `packages/ai/src/auth/types.ts:65-94` (`CredentialStore`'s own doc comment): confirmed `modify`
  is documented as "the only write path," but this is a documented, INTENDED usage convention --
  not a technical enforcement mechanism. Pi's own plain-object credential type provides no
  structural barrier against a caller mutating a retained reference directly; the characterization
  checkpoint's own behavior-matrix row ("sole supported write authority... though raw JS
  references permit bypass") states this accurately.
- `packages/ai/src/auth/types.ts:97-101` (`AuthContext`): confirmed `fileExists`'s own doc comment
  -- `/** Check whether a file exists. Supports a leading `~`. Always false in browsers. */` -- is
  attached DIRECTLY to the interface method itself, unlike `env`, which carries NO interface-level
  comment about blank-value handling at all (that behavior is stated only on
  `defaultProviderAuthContext`, `context.ts:25-28`). The characterization checkpoint's own
  conclusion -- that leading-`~` support is an interface-level (protocol-level) contract, distinct
  from `env`'s default-only blank normalization -- is confirmed correct against this exact source
  placement, not merely plausible.

**Answering the §11.8.4 checklist:**

- *Is the Pi source mapping correct?* Yes, on both `L11-R006` and `L11-R008`, confirmed above.
- *Is the behavior matrix complete enough to distinguish realistic wrong implementations?* Yes --
  the checkpoint's own matrix (top-level mutation, outer-mapping aliasing, nested mutation, open
  JSON domain, write authority, manifest disposition; `env`/`fileExists` protocol-vs-default rows)
  covers every dimension the two rejected candidates actually got wrong.
- *Are any cases implementation mechanics rather than observable semantics?* Yes, one: the
  characterization checkpoint frames the choice as "`MappingProxyType` vs. deep freeze vs. cloning"
  -- but the actual decision is narrower and purely observable: does mutating a value reachable
  through a `Credential` (via the original constructor argument, or via a value returned by
  `read`/`modify`) remain observable through the credential afterward? The specific Python
  container mechanism used to express whichever answer is chosen is implementation detail, not
  part of the shared contract itself -- `spec/auth.md` must state the observable rule, never a
  Python type name.
- *Does any proposed fix silently reopen a lower certified layer?* No. Neither finding touches
  Layer 09's `RunSignal`, Layer 05's `runtime/` package, or any other certified layer.
- *Can both Python and Rust implement the rule idiomatically?* Yes for the OWNER-DECIDED resolution
  below (Pi's own live-reference/shared-mutation semantics): Python already stores/returns
  `Credential` objects by ordinary object reference with no copying, which is exactly this
  behavior with zero extra mechanism; Rust can express the same observable aliasing with an owned
  recursive JSON value type (e.g. `serde_json::Value`) passed/returned by ordinary Rust move/borrow
  semantics -- no `Arc<Mutex<...>>` or other shared-ownership machinery is required merely to
  satisfy this rule, since the rule only requires that a value's own nested mutable containers
  remain the SAME containers across the constructor-argument/store/return boundary within the
  lifetime of a single process, not genuine cross-owner shared mutability.
- *Does either defect's root cause depend on an extensibility point one language's own certified
  lower layers exposes and the other does not?* No -- this is pure vocabulary/value-representation
  semantics with no cross-layer extensibility point involved (unlike Layer 09's own reentrant
  observer-hook precedent this checklist item exists to guard against).
- *Are all previous review findings represented by an executable or documentary acceptance
  criterion?* Yes, via the checkpoint's own W-R006-1/W-R006-2/W-R006-3/W-R008-1 witnesses, adopted
  below with their EXPECTED OUTCOME reversed for `L11-R006` per the owner's own decision (see next
  section) -- the witnesses themselves (what to construct, what to mutate, what to observe) remain
  exactly as the checkpoint specified; only the REQUIRED RESULT column changes from "credential
  remains unchanged" to "credential observes the mutation," matching Pi.

No revision to the characterization checkpoint's own Pi/source audit or behavior matrix is
required -- the challenge confirms it. What was missing, and is what this document supplies, is
governance: `L11-R006` proposes a genuine INTENTIONAL DIVERGENCE from Pi's own observable behavior,
which `agent-workflow.md` §11.7 reserves to the repository owner, not the shared-contract owner.

## Owner governance decision (§11.7)

The repository owner was asked directly, framed as the two options the characterization checkpoint
itself lays out (adopt Pi's live-reference semantics vs. an owner-approved deep-immutable-value
intentional divergence), and returned an explicit, written decision:

```text
L11-R006 GOVERNANCE DECISION

DECISION
    ADOPT PINNED PI LIVE-REFERENCE SEMANTICS
    NO INTENTIONAL DIVERGENCE APPROVED.

    Credential.env / Credential.extra retain Pi-observable live-reference behavior.

REQUIRED OBSERVABLE SEMANTICS
    1. Constructor aliasing: if the caller supplies a mutable mapping/list inside
       env/extra, later mutation through that original object remains observable
       through the credential.
    2. Returned-value aliasing: if the credential exposes a mutable nested value
       and the caller mutates it, later reads observe that mutation.
    3. Nested aliasing: the rule applies recursively to nested mutable
       mappings/lists; a shallow outer copy/freeze is not sufficient.
    4. Open JSON domain: env/extra continue to admit the same arbitrary
       JSON-shaped values required by the shared contract.
    5. CredentialStore.modify() remains the serialized mutation path for callers
       using the store. Its concurrency guarantee must not be reinterpreted as a
       promise that credential objects are deeply immutable or that all possible
       state mutation can occur only through modify().

RATIONALE
    Pinned Pi behavior is now known, observable, and implementable. The
    project's frozen policy requires Pi-visible behavior to be adopted unless
    there is a sufficiently strong reason for an intentional divergence. Deep
    immutable values would improve encapsulation, but that is a design
    preference/hardening choice rather than a demonstrated incompatibility with
    Minion's architecture. Therefore Layer 11 should preserve Pi parity here.

SCOPE
    Applies only to Credential.env / Credential.extra value/reference semantics.
    Does not weaken: serialized CredentialStore.modify() behavior; credential
    ownership/refresh-authority rules; atomic persistence requirements;
    externally-owned credential mutation restrictions.
```

This closes the governance gap the characterization checkpoint itself identified ("No §11.7 owner
approval is recorded for replacing Pi's observable live mutable references with immutable
values"). `PROV-006`'s own disposition therefore correctly stays `adopted` -- this is NOT an
intentional divergence needing its own separate manifest row; it is corrected Pi-parity replacing
an unapproved, incompletely-implemented divergence the two rejected candidates each introduced.

## Agreed observable matrix (final, post-decision)

| Observation | Required result |
|---|---|
| mutate the original constructor mapping/list after construction | credential observes the mutation |
| mutate a nested dict/list value reached through `credential.extra`/`credential.env` | the mutation persists and is observed by a later access, including through `CredentialStore.read()` |
| assign a brand-new top-level key on `credential.extra`/`credential.env` itself (not merely a nested value) | succeeds, matching a plain Pi object field assignment |
| open JSON domain (nested objects, arrays, strings, numbers, booleans, null) | round-trips through construction/storage/retrieval unchanged, with no narrowing and no forced immutability |
| `CredentialStore.modify()` concurrency guarantee | UNCHANGED -- still serializes concurrent `modify()`/`delete()` calls for the same provider id exactly as `PROV-007` already specifies; a caller bypassing `modify()` by mutating a retained reference directly is possible (matching Pi exactly, including Pi's own documented bypassability) and is not this finding's concern |
| `AuthContext.file_exists`, protocol level | supports a leading `~`, expanded to the user's home directory, as part of the `AuthContext` protocol itself -- not merely `DefaultAuthContext`'s own concrete behavior |
| `AuthContext.env`, protocol level | UNCHANGED from the already-closed `L11-R003` fix -- blank/whitespace-to-absent normalization remains `DefaultAuthContext`-specific, not a protocol requirement |

## Agreed implementation and evidence constraints

The implementation pass must:

- remove `ApiKeyCredential.__post_init__`/`OAuthCredential.__post_init__`'s own defensive
  `MappingProxyType(dict(...))` snapshotting entirely -- store whatever mapping the caller passes
  exactly as given, with no copy and no freeze at any level;
- remove the now-incorrect "Credential value semantics (`L11-R006`, intentional divergence)"
  paragraph from `spec/auth.md` and the corresponding `PROV-006` manifest prose, replacing both
  with the corrected Pi-parity statement above;
- replace the two now-wrong tests (`test_api_key_credential_env_is_immutable_and_not_aliased...`,
  `test_oauth_credential_extra_is_immutable_and_not_aliased...`) with permanent regression
  witnesses for W-R006-1 (constructor aliasing, including a NESTED mutable value), W-R006-2
  (mutation through a returned value persists, including through a nested value), and W-R006-3
  (open JSON domain round-trips: object, array, string, number, boolean, null);
- add one `CredentialStore`-level integration witness proving the aliasing survives a
  `store.modify(...)`/`store.read(...)` round trip, not merely bare dataclass construction;
- restore `AuthContext`'s own protocol-level docstring to state leading-`~` support as part of the
  protocol contract (not default-only), correcting `L11-R008`'s overcorrection of the earlier
  `L11-R003` fix; add W-R008-1, a NON-DEFAULT `AuthContext` implementation proving tilde-expansion,
  distinct from `DefaultAuthContext`'s own existing test;
- state, in `spec/auth.md`, that Minion has no browser runtime target, so Pi's own "always false in
  browsers" `file_exists` clause is architecturally inapplicable here rather than silently dropped
  or misapplied;
- express every corrected rule in `spec/auth.md` language-neutrally (observable aliasing/mutation
  behavior), never citing a Python container type as the normative requirement;
- rerun the full suite, including every previously-provisionally-closed `L11-R001`/`R002`/`R003`/
  `R004`/`R005`/`R007` test, to confirm this pass does not regress any of them.

## Scope and feasibility

No certified lower layer needs reopening. Rust can implement the agreed live-reference/aliasing
behavior with an owned recursive JSON value (e.g. `serde_json::Value`) moved/borrowed by ordinary
Rust value semantics -- satisfying "mutate a nested value, observe it later" requires only that
Rust not defensively deep-clone on every store/return boundary, not that it introduce shared
mutable ownership (`Arc<Mutex<...>>`) purely to mimic this rule. No Rust implementation is
authorized by this document; Rust Layer 11 remains blocked until the remediated shared/Python
candidate is independently reviewed and approved under the normal workflow.

Real provider transport, browser OAuth, and Layer 12 remain out of scope and untouched by this
convergence episode.

## Agreement status

```text
CONVERGENCE CONTRACT
    AGREED FOR IMPLEMENTATION

OPEN FINDINGS
    L11-R006
    L11-R008

CHALLENGE FINDINGS
    (none -- the characterization checkpoint's own Pi/source audit and behavior matrix were
    confirmed correct on challenge; the only gap was governance, now closed by the owner decision
    recorded above)

NEXT OWNER
    Claude

NEXT ACTION
    Implement both findings as one convergence pass per the agreed matrix and constraints above,
    add the agreed witnesses, synchronize spec/manifest, rerun the full suite including every
    previously-closed L11-R001/R002/R003/R004/R005/R007 test, and return the exact remote
    candidate for a targeted provisional-closure review, followed by one final complete review
    once every blocking finding is provisionally closed.
```

This agreement is a convergence checkpoint, not final contract approval or Layer-11 certification.
A final complete exact-SHA review remains mandatory once every blocking finding is provisionally
closed.
