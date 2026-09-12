# Layer 10 — independent shared/Python closure review of the Rust implementation candidate

**Review mode:** `agent-workflow.md` §11.4's own "Claude: final cross-language/closure
verification" step, following Codex's Rust implementation + certification candidate.

**Result:** `REJECTED — ONE NARROW FINDING REQUIRED`. Everything else independently confirmed.

## Exact review target

- code PR #22: `feda44dcecc24eb03c8e531a9aa60f2c23d71f58`
- docs PR #50: `3c80d7b9e44703ab2436d7ce6e29427d7a3627e1`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- candidate's own claimed authority: `assurance/layers/10-provider-abstraction-rust-implementation.md`,
  citing merged code baseline `f12c0e37f8d33ca8be78028ab4ec9bd2b59c9eb8` / merged docs baseline
  `8e18072666c104369cbed2922e7d9084a090af9d`

Both PRs were fetched fresh before review (`git fetch origin impl/10-provider-abstraction-rust`,
`git fetch origin assurance/rust-layer-10-certification`), diffed against the current merged
`main`/`master`, and independently re-read line by line -- not accepted on the candidate's own
self-report alone. `minion-agent-rust/**` was inspected but not modified, per this project's own
ownership boundary.

## Independent audit order

Pinned Pi (`ref-repos/pi` at the exact pinned SHA, already characterized in full during the
shared/Python passes this layer went through -- `AI-012`/`AI-028`/`AI-029`/`AI-030`/`AI-031`/
`AI-032`), the merged normative spec (`spec/llm.md`) and manifest, the seven canonical `llm-service`
scenarios, the actual Rust source diff, the candidate's own assurance artifact, and Python only as
secondary evidence (unchanged by this candidate; used only to cross-check claims).

## Independently re-verified claims

Every gate the candidate's own assurance artifact claimed was re-run directly against a fresh
`git worktree` of the exact candidate SHA (`feda44d`), not merely re-read:

```text
cargo fmt --all -- --check                                    PASS (confirmed)
cargo clippy --workspace --all-targets --all-features -D warnings   PASS, 0 warnings (confirmed)
cargo test --workspace --all-features                          292 passed, 0 failed (confirmed)
RUSTDOCFLAGS="-D warnings" cargo doc --workspace --no-deps      PASS (confirmed)
cargo run -p xtask -- conformance verify                        exit 0 (confirmed)
Python schema + manifest validation (worktree source)           205 passed (confirmed)
pi-parity-manifest.yaml diff (main...feda44d)                   ONLY AI-028/AI-030 `rust:` fields
                                                                  changed; Pi pointers, rule text,
                                                                  tests, python evidence, and
                                                                  dispositions byte-for-byte
                                                                  unchanged (confirmed by diff)
minion-agent-python/ diff (main...feda44d)                       empty (confirmed -- Python
                                                                  genuinely untouched)
```

## Architecture review

Read directly, not summarized from the candidate's own prose:

- **`LlmAdapter::start`** (`adapter.rs`) now returns `RawAssistantStream` unconditionally -- the
  `AdapterStartError`/eager-error channel is REMOVED, not merely deprecated. Matches `AI-028`'s
  own never-raises requirement exactly: once a resolved adapter is invoked, there is no expected-
  failure return channel at all, only in-band stream settlement.
- **`ScriptedAdapter::start`** (`scripted.rs`): an exhausted script now returns a stream that
  yields one `AdapterStreamError` (kind `Runtime`) instead of eagerly returning `Err(...)` --
  matches Python's already-certified `MockAdapter._take()` own in-band exhaustion behavior exactly
  (`llm_adapter.rs::exhausted_scripted_adapter_settles_in_band`, independently re-run, confirmed
  passing).
- **`LlmService::register`/`register_models`/`LlmRegistration::withdraw`** (`service.rs`): each
  call allocates a fresh `Arc<()>` ownership token, stored alongside the adapter in the registry;
  `withdraw` takes `&self` (NOT `self` -- it does NOT consume the handle) and checks
  `Arc::ptr_eq(&entry.owner, &self.owner)` before removing an entry, exactly matching Python's own
  token-based design (`AI-030`/`C10-C005`) and, critically, correctly avoiding the "consuming,
  move-only handle" shape the convergence agreement's own binding clarification explicitly ruled
  non-conforming (a `withdraw(&self)` design remains safely repeat-callable; a consuming
  `withdraw(self)` would not). Independently re-run `llm_adapter.rs::
  registration_handles_are_repeatable_stale_safe_and_owned_per_call` (the exact same-object-
  registered-twice case `C10-C005` was raised over) -- confirmed passing.
- **`LlmService::models()`** (`service.rs`): returns a `Vec<ModelIdentity>` sorted by `(provider,
  api, model_id)` -- deterministic, but see `L10-C001` below.
- No registry lock is held across adapter invocation (`self.adapters.read().get(...).map(|entry|
  Arc::clone(...))` releases the read guard before `adapter.start(request)` runs) -- matches the
  binding "no lock across adapter/provider code" constraint the checkpoint and preflight both
  required.
- `minion-agent-python/` diff is empty; `pi-parity-manifest.yaml` diff is confined to the two
  `rust:` evidence fields (confirmed above) -- Python was genuinely not modified, only cited as
  evidence, matching the candidate's own claim.

**Result:** the production architecture is correct and faithfully implements `AI-028`/`AI-030`/
`C10-C005` as agreed. `L10-R003` is genuinely resolved.

## Canonical review

`llm_service_conformance.rs`'s own `run_scenario` was read in full. It is a thin runner: it
constructs real `LlmService`/`CanonicalAdapter` objects, dispatches through the real typed
`register`/`register_models`/`stream`/`models` API, and normalizes observations into the same
`{observation_id: {...}}` shape the Python runner produces -- it does not itself implement
registration, replacement, withdrawal, introspection, or settlement semantics. `validate_references`
mirrors the Python `_validate_references` function's own structural checks closely. The `resolve`
query's own ownership detection uses the SAME count-delta-with-exactly-one-owner design `C10-C004`
established (`owners.len() != 1` is an error, never a first-match fallback). All seven current
scenarios are discovered by directory scan and asserted individually (`assert_eq!(actual,
scenario.expect, "{}", path.display())`), not merely counted.

**Result:** PASS. Genuinely thin, language-neutral, and faithful to the shared contract for every
CURRENTLY exercised case.

## Contract-quality answers

```text
runner simulates production registry/settlement semantics?      NO
runner imposes a hidden numeric call cap?                       NO (no finite script at all --
                                                                  CanonicalAdapter's own "ok" arm
                                                                  succeeds unconditionally on every
                                                                  call, structurally avoiding the
                                                                  entire class of bug L10-R007 was)
Python behavior matches the approved Minion mapping?             YES (Python untouched; confirmed
                                                                  by empty diff)
Rust can implement without consulting Python mechanics?          YES (token-based ownership reached
                                                                  independently via idiomatic
                                                                  Arc::ptr_eq, not a port of
                                                                  Python's own object() token)
lower certified layer reopen required?                           NO
manifest evidence values structurally valid and complete?        YES (only two rust: fields
                                                                  changed, confirmed by diff)
canonical comparison semantics agree between languages?           NO -- see L10-C001, L10-C002
```

## New findings

### `L10-C001` — canonical `introspect: models` observation used the wrong sort key (Rust-side; requires a narrow Rust fix)

**Classification:** `CONTRACT_ASSURANCE_DEFECT` -- blocking, narrow.

`LlmService::models()`'s own return order was never part of the observable contract -- nothing in
`spec/llm.md` or `pi-parity-manifest.yaml::AI-030` said any implementation owed a specific order,
which is itself a genuine gap this review closes (see remediation below). In that gap, the Rust
canonical runner (`llm_service_conformance.rs`) reported `service.models()`'s own raw return order
directly; `LlmService::models()` happens to sort by `(provider, api, model_id)`. The Python
canonical runner has always sorted its own `introspect: models` observation by `(provider, model,
api)` -- a DIFFERENT key -- before comparing against `expect.models`.

No currently-merged canonical scenario exposed this: all seven pre-existing `llm-service-*.yaml`
scenarios that use `introspect: models` register at most one resolvable identity at the point of
observation, so no ordering ever differs. A minimal discriminating witness constructs two
identities whose own `api`/`model` values cross under the two keys:

```text
adapter-a: provider=mock, api=zzz-api, model=aaa-model
adapter-b: provider=mock, api=aaa-api, model=zzz-model

sorted by (provider, model, api):  [a (model=aaa-model), b (model=zzz-model)]
sorted by (provider, api, model):  [b (api=aaa-api), a (api=zzz-api)]   -- OPPOSITE order
```

This is now a permanent canonical witness: `conformance/agent/llm-service-introspection-order-
does-not-depend-on-api-first-sort.yaml`. Independently RED-confirmed against the Python runner
(temporarily reverted to the wrong `(provider, api, model)` key, confirmed the new scenario fails
exactly as this finding predicts, then restored) before being committed as permanent evidence.

**Remediation applied this pass (shared/Python side, already pushed):**

1. `spec/llm.md`'s own `AI-030` section gains an explicit new paragraph: `models()`'s own return
   order is NOT part of the observable contract for any implementation, but the CANONICAL EVIDENCE
   FORMAT requires every conformance runner, in any language, to sort an `introspect: models`
   observation by `(provider, model, api)` before comparing against `expect.models` -- the one
   required tooling-level canonicalization.
2. `pi-parity-manifest.yaml::AI-030`'s own `rule:` field mirrors the same requirement and cites
   this finding.
3. The new discriminating scenario above, plus a one-line comment in the Python runner's own
   `introspect` branch stating the sort is now normative, not incidental convenience.

**Narrow remediation still required (Rust side, NOT applied here -- outside this review's own
ownership boundary):** `llm_service_conformance.rs`'s own `introspect: models` branch must sort its
own collected `Vec<Value>` by `(provider, model, api)` before inserting into `actual`, instead of
trusting `service.models()`'s own raw order directly (which may keep its own internal `(provider,
api, model_id)` key for `LlmService::models()`'s own production return -- that is unaffected;
ONLY the canonical-evidence-comparison step needs to canonicalize). This is a one-line, test-only
change; no production Rust semantics require modification, since `models()`'s own order was never
part of the contract.

### `L10-C002` — an unasserted canonical query was a latent grammar ambiguity (closed entirely on the shared/Python side; no Rust change required)

**Classification:** `CONTRACT_ASSURANCE_DEFECT` -- narrow, now CLOSED.

Python's own `_validate_references` permitted a `queries[].id` that `expect` never names (treating
it the same as a legitimate "setup-only" `steps[].stream` action). Rust's own
`llm_service_conformance.rs` test performs a full bidirectional `assert_eq!(actual, scenario.expect)`
and would reject any such scenario with a spurious extra-key mismatch. No current scenario exercises
this (every declared query is currently asserted), but the two languages' own interpretation of the
same declarative grammar genuinely disagreed.

Independently assessed which interpretation is correct: unlike a `steps[].stream` action (which can
legitimately serve a dual "mutate state, and maybe also get checked" role), a `queries[].id` exists
for NO purpose OTHER than being observed -- a query nothing ever asserts on is far more likely a
scenario-authoring mistake than an intentional setup-only case. Rust's own stricter interpretation
is the CORRECT one; Python's own validator was too permissive.

**Remediation applied this pass (shared/Python side only):** `llm_service_runner.py::
_validate_references` now rejects any `queries[].id` `expect` does not name, with a new direct
negative-witness unit test (`test_an_unasserted_query_is_rejected`) and an updated positive
counterpart already covering the (still-legal) setup-only stream case. RED-confirmed (reverted the
new check, confirmed the new test fails, restored) before being committed. This closes the finding
entirely on the shared/Python side; Rust's own existing behavior was already correct and needs no
change.

## Findings and boundary

```text
PI_BEHAVIOR_UNCERTAIN       none
PI_PARITY_DEFECT             none -- L10-R003 genuinely resolved by this candidate
CONTRACT_ASSURANCE_DEFECT   L10-C001 (narrow Rust-side fix still required), L10-C002 (CLOSED)
PARITY_CONSTRAINED_RISK     none
```

## Verdict

```text
shared Layer-10 contract    REOPENED narrowly for L10-C001/L10-C002 (this pass closes L10-C002 and
                               the contract-side half of L10-C001; one narrow Rust-only test fix
                               remains)
Python Layer 10              CERTIFIED, unaffected (no production file touched)
Rust Layer 10                CERTIFICATION CANDIDATE, one narrow fix required before re-review
Layer 10 cross-language      NOT CLOSED
Layer 11                     NOT STARTED
```

## Next action (superseded -- see targeted closure re-review below)

Codex applies the one narrow fix `L10-C001` still requires (sort the `introspect: models`
observation by `(provider, model, api)` in `llm_service_conformance.rs` before comparison; run the
new `llm-service-introspection-order-does-not-depend-on-api-first-sort.yaml` scenario against it to
confirm), pushes the updated exact candidate SHA, and returns for a targeted closure re-review
limited to `L10-C001`. `L10-C002` needs no further Rust action -- it closed entirely on the
shared/Python side. `L10-R003` is closed; do not reopen it. Layer 11 remains not started.

---

## Targeted closure re-review — code `82a7a74`, docs `a39f121`

**Exact code SHA:** `82a7a74988fbd0d2480cee090417968a04dad043`

**Exact docs SHA:** `a39f121494615b81b5a1ea25f6f211b63d28efdd`

**Result:** `APPROVED -- ALL FINDINGS CLOSED`.

Independently re-verified before approving, not accepted on the candidate's own self-report:

- Diffed `6452679` (the reviewed Rust implementation commit) against `82a7a74` (this fix) directly:
  the ENTIRE change is 10 lines in `llm_service_conformance.rs`'s own `introspect: models` branch --
  `service.models()`'s own output is now re-sorted by `(left.provider(), left.model_id(),
  left.api())` before mapping to the canonical JSON observation, and the scenario-count assertion
  updated from `7` to `8`. No other file changed in this commit. `minion-agent-rust/crates/
  minion-agent/src/llm/service.rs` (the production `LlmService::models()` implementation) is
  untouched -- confirmed by the diff itself, not merely by the candidate's own claim.
- Re-ran every gate against a FRESH worktree of the exact new candidate SHA: `cargo fmt --check`
  (clean), `cargo clippy --workspace --all-targets --all-features -D warnings` (0 warnings),
  `cargo test --workspace --all-features` (292 passed, 0 failed, independently summed from the raw
  per-crate output), specifically `cargo test --test llm_service_conformance` (both of its own
  tests pass, including `all_layer_10_scenarios_drive_the_real_rust_llm_service` now asserting and
  exercising 8 scenarios), `RUSTDOCFLAGS="-D warnings" cargo doc --workspace --no-deps` (clean),
  `cargo run -p xtask -- conformance verify` (exit 0).
- Re-ran the Python-side gates from the same worktree: `test_schema_validation.py` +
  `test_manifest_validation.py` together report `206 passed` (up from `205`, the new scenario's own
  schema-validation parametrization), and the manifest parses to `84 rows / 84 unique IDs`.
- Read the updated `10-provider-abstraction-rust-implementation.md`'s own diff (`0acc9a0..a39f121`):
  accurately records the new candidate SHA, the scenario count change, the gate-count change, and
  explicitly states "Production `LlmService::models()` remains unchanged because its return order
  is explicitly outside the observable contract" -- matching what the diff itself shows, not an
  unverified claim.

`L10-C001` is CLOSED: the shared contract-side requirement (pinned `(provider, model, api)` as the
required canonicalization) and the Rust-side fix (apply that exact key in the conformance runner's
own comparison step) are both now in place and independently confirmed correct. `L10-C002` and
`L10-R003` remain closed, unaffected by this narrow commit. No finding remains open on Layer 10.

```text
CLOSURE REVIEW
    APPROVED -- ALL FINDINGS CLOSED

CLOSED
    L10-R001, L10-R002, L10-R003, L10-R004, L10-R005, L10-R006, L10-R007, L10-R008
    C10-C005
    L10-C001, L10-C002

NEXT OWNER
    Codex

NEXT ACTION
    Merge minion-agent PR #22 (code, exact head 82a7a74988fbd0d2480cee090417968a04dad043) and
    minion-agent-docs PR #50 (docs, exact head a39f121494615b81b5a1ea25f6f211b63d28efdd) using the
    normal exact-SHA merge policy (agent-workflow.md §11.6/§11.8.8 step 5), then update
    coordination issue #19 to record Layer 10 cross-language CLOSED. The repository owner has asked
    that Codex (not the shared/Python owner) execute this merge. Layer 11 remains not started; do
    not start it as part of this closure.
```

## Verdict (final)

```text
shared Layer-10 contract    APPROVED, no findings open
Python Layer 10              CERTIFIED
Rust Layer 10                APPROVED CERTIFICATION CANDIDATE at 82a7a74 / a39f121, ready to merge
Layer 10 cross-language      READY TO CLOSE (pending Codex's own merge of the approved candidate)
Layer 11                     NOT STARTED
```
