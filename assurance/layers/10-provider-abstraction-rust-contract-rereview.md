# Layer 10 — targeted independent Rust contract re-review, PASS 2

**Verdict:** `REJECTED` for the exact candidate pair below. Rust Layer 10 remains blocked; Layer
11 was not started.

## Exact review target

- code PR #20: `bad0f74552fbb73c71f15553ba321fc1d8609a10`
- docs PR #45: `558c03e4b0e67f162fee669e8f9c7c08747bebf3`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- prior rejected review: docs PR #46 at
  `d43559dfbc1770bb8508fcb2f27a88c0f5a4530c`
- coordination issue: `EGAILab/minion-agent#19`, independently verified at review start with
  `STATUS = RUST_CONTRACT_REVIEW` and `NEXT_OWNER = Codex`

Both candidate PRs were open, Ready for Review, unmerged, cleanly mergeable, and their actual
remote heads matched issue #19. Review used detached candidate worktrees and a separate evidence
branch. Neither candidate branch nor Rust production was modified.

## Independent authority audit

The review proceeded in the required order: pinned Pi, manifest, normative spec, canonical
schema/scenarios, certified Rust architecture, assurance, then Python only as secondary evidence.

Pinned Pi independently reconfirms:

```text
ProviderStreams
    stream(...)       required
    streamSimple(...) required
    fetchDeferred?    optional
    cancelDeferred?   optional

StreamFunction
    after invocation, expected request/model/runtime failures are represented in-band

createProvider/apiFor/dispatch
    selects one ProviderStreams or an API-keyed implementation
    a missing API implementation becomes a lazy/in-band stream failure
```

Current Rust independently reconfirms:

```text
LlmAdapter::start(request) -> Result<RawAssistantStream, AdapterStartError>
    permits an eager expected failure after resolution and adapter invocation

LlmService::register(identity, adapter)
    exact three-part identity
    last-write replacement
    no withdrawal handle
    no stale-withdrawal protection
    no models() introspection
```

The permanent Rust test `adapter_start_failure_remains_eager_and_typed` still proves the current
`L10-R003` behavior. That is a Rust implementation defect, not a reason to obscure the approved
target.

## L10-R001 through L10-R004 closure ledger

### L10-R001 — required `streamSimple`

**Result: PARTIALLY RESOLVED, BLOCKING contract disposition remains.** PASS 2 corrected the source
fact: `streamSimple` is required, not optional. It also names Layer 11 as the intended owner of the
per-provider simple-options translation. That semantic defer is plausible because its content is
provider-specific.

The manifest does not record that defer coherently, however. `AI-028` combines the adopted
`stream`/never-raises contract and the explicitly deferred required `streamSimple` surface while
the row-level disposition remains solely `adopted`. A required Pi surface cannot simultaneously be
absent until Layer 11 and be represented by an unqualified adopted disposition. Split the deferred
`streamSimple` obligation into its own row (with a concrete Layer-11/PROV owner), or otherwise make
the machine-readable disposition unambiguous without weakening the source fact.

### L10-R002 — resolution versus Minion registry architecture

**Result: PARTIALLY RESOLVED, BLOCKING.** `AI-030` is a good split: registration, replacement,
withdrawal, and introspection are now one coherent Minion-only subject with `intentional
divergence`, and Python's temporary `api="mock"` default is no longer universalized to Rust.

`AI-029` still carries the same disposition conflict on the remaining subject. Pinned Pi's missing
provider-API implementation settles in-band; Minion deliberately collapses it with a missing full
identity and rejects eagerly. The rule correctly calls this an intentional architectural
simplification, but the row still says `disposition: adopted`. Either isolate the genuinely
adopted routing rule from the observably divergent failure boundary, or give the combined subject
the correct intentional-divergence disposition. Master-design authorization can justify the
difference; it does not turn different observable behavior into adopted Pi behavior.

### L10-R003 — current Rust eager adapter-start failure

**Result: CONFIRMED OPEN RUST IMPLEMENTATION DEFECT; contract disclosure corrected.** `AI-028`,
the spec, and PASS-2 assurance now accurately say current Rust permits the forbidden eager typed
failure and needs later Rust remediation. The new failure scenario's expected outcome is the right
discriminator: a resolved adapter-detected expected failure must yield a returned stream settled
with an error terminal.

The scenario is not yet executable by current Rust. Rust's Agent conformance discovery classifies
all four new `llm_service` documents as unclassified and fails before reaching `L10-R003`; `xtask
conformance verify` only validates layout and exits successfully. That is expected implementation
work for a future Rust Layer-10 pass, but claims that the current Rust runner already reproduces
the semantic failure would be inaccurate.

### L10-R004 — direct language-neutral evidence

**Result: STILL OPEN.** The four scenarios cover the intended finite behaviors and dispatch real
Python `LlmService` operations. The runner does not implement registration, replacement,
withdrawal, or stream settlement itself. Two discriminating defects remain in the new shared seam:

1. The schema says `reject_message` is required for `behavior: reject`, but does not enforce it.
   A reject adapter without the field validates, then `_build_adapter` raises `KeyError`.
   Conversely an `ok` adapter may carry an inapplicable `reject_message`. Independent runners may
   reject, default, or ignore the same schema-valid document.
2. Resolution ownership is inferred by searching for the first adapter whose last recorded
   request equals the current request. That is not a reliable observation of which request log
   grew. A schema-valid sequence `register A -> stream identical request through A -> register B
   for the same identity -> resolve` is actually routed by the service to B, but the canonical
   runner reports A because both logs end with value-equal requests.

Concrete review probes produced:

```text
reject adapter without reject_message
    schema result: VALID

ok adapter with reject_message
    schema result: VALID

register A; stream alpha; replace with B; resolve alpha
    real current owner: B
    runner observation: adapter-a
```

Required repair is narrow: enforce the behavior-dependent adapter-entry grammar, and observe the
specific request log that grew (for example by snapshotting per-adapter counts) rather than using
value equality over historical requests. Add both witnesses as permanent schema/runner tests.

## Canonical scenario audit

| Scenario | Intended rule | Real Python seam | Result |
|---|---|---|---|
| `llm-service-registration-and-replacement` | replacement, independence, missing identity | `LlmService.register/stream` | finite scenario passes; runner ownership observation is not generally sound |
| `llm-service-withdrawal-does-not-remove-a-later-replacement` | stale withdrawal and ordinary withdrawal | returned withdrawal handles | passes |
| `llm-service-introspection-reflects-current-registrations` | current model identities | `LlmService.models` | passes |
| `llm-service-adapter-detected-failure-settles-in-band` | resolved adapter failure is in-band | `LlmService.stream` + `MockAdapter` | Python passes; current Rust has no runner and production has the expected `L10-R003` mismatch |

The schema is language-neutral in vocabulary, but not yet deterministic for all documents it
accepts. The runner remains thin in operation dispatch, but its adapter-owner normalization can
produce a false observation.

## Evidence and test observations

- four current Python `llm_service` scenarios plus candidate schema validation: PASS, 194 tests
  (4 scenario executions + 190 schema tests; focused run, coverage gate disabled);
- manifest parse/uniqueness: PASS, 82 rows / 82 unique IDs;
- focused existing Rust LLM suites: PASS, 11 tests;
- Rust `agent_loop_conformance` against this candidate: FAIL, four new `llm_service` documents
  unclassified (expected missing Rust runner work, not an `L10-R003` semantic execution);
- direct malformed-schema and stale-request-log probes: reproduced both blockers above.

Green finite candidate scenarios do not close a canonical grammar/observation defect.

## Findings

### L10-R001 — `CONTRACT_ASSURANCE_DEFECT` (refined)

The Pi source fact is corrected, but `AI-028` still places adopted and explicitly deferred required
surfaces under one `adopted` row disposition.

### L10-R002 — `CONTRACT_ASSURANCE_DEFECT` (still open)

`AI-030` is coherent, but `AI-029` still labels an observably eager Minion simplification of Pi's
in-band missing-API behavior as wholly `adopted`.

### L10-R003 — `PI_PARITY_DEFECT` (current Rust only, accurately disclosed)

Current Rust retains an eager adapter-start error channel. This is the narrow production repair
for the eventual Rust Layer-10 implementation pass; it is not fixed or certified by this review.

### L10-R004 — `CONTRACT_ASSURANCE_DEFECT` (still open; refined witnesses)

The new direct canonical family exists, but its schema accepts an incomplete reject adapter and
its runner can misidentify the adapter that actually served a resolution query.

No `PI_BEHAVIOR_UNCERTAIN` remains.

## Convergence trigger

`L10-R002` and `L10-R004` have now survived two consecutive independent rejection reviews under
the same finding IDs. Per `process/agent-workflow.md` §11.8, the automatic repeated-finding trigger
is met. The next owner must enter `CONTRACT_CONVERGENCE`, characterize the remaining disposition
and canonical-grammar/observation surfaces with the witnesses above, and obtain the required
challenge/checkpoint agreement before another implementation remediation.

## Verdict and next action

```text
shared Layer-10 contract   REJECTED
Python Layer 10            REOPENED
Rust Layer 10              BLOCKED
Layer 10 cross-language    NOT CLOSED
Layer 11                   NOT STARTED
```

Return to the shared/Python owner for the narrow convergence process described above. Preserve
`L10-R003` as an explicit Rust implementation obligation; do not attempt it until the corrected
shared contract is independently approved. Any candidate SHA change requires exact-SHA re-review.

STOP. Do not implement Rust Layer 10 and do not start Layer 11.
