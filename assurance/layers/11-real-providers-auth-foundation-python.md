# Layer 11 (Real providers) — Auth Foundation, Python/shared certification, PASS 1

## 1. STARTING STATE

Fetched and pruned both repos before any work began.

- `minion-agent` @ `main` — `ee2e046b1837b1b1107fbacfda6cc05db8af035a` (Layer 10 Code PR #22's own
  merged head, matching the Layer-10 closure issue's own recorded `CODE` line exactly).
- `minion-agent-docs` @ `master` — `89ddc775bb826bace41abce97301a178382fdeef` (Layer 10's own
  workflow-retrospective PR #53 merge, matching the Layer-10 closure issue's own recorded `DOCS`
  line exactly).

Confirmed via `gh issue view 19` (the Layer 10 coordination issue): `STATUS
CROSS_LANGUAGE_CERTIFIED / CLOSED`, `NEXT_ACTION: Layer 11 is ELIGIBLE / NOT STARTED. Begin it only
under a separate kickoff and coordination issue.` Confirmed via `gh issue list --search "Layer 11"`
that no Layer-11 coordination issue existed yet before this pass. No unrelated working-tree changes
were present in either repo at the start of this pass; every file this pass touches is listed under
"IMPLEMENTATION" and "CANONICAL EVIDENCE" below.

## 2. PINNED PI AUDIT

Pinned Pi revision: `b7bb00b936dbe21b8e160b3e89efdec361846699` (unchanged from Layer 10; confirmed
matching `pi-parity-manifest.yaml`'s own `pi_revision` field). Full-text read, this pass, before any
spec/manifest/implementation change:

- `packages/ai/src/auth/types.ts` (full) — `ApiKeyCredential`, `OAuthCredential` (including its own
  open `[key: string]: unknown` index signature), `Credential`, `CredentialInfo`,
  `AuthOperationOptions`, `ModelAuth`, `AuthResult`, `AuthCheck`, `AuthContext`, `CredentialStore`
  (lines 65-94, its own full read/list/modify/delete contract documentation).
- `packages/ai/src/auth/context.ts` (full) — `defaultProviderAuthContext`'s own `env`/`file_exists`
  behavior, including the blank-value-treated-as-absent rule.
- `packages/ai/src/auth/credential-store.ts` (full) — `InMemoryCredentialStore`'s own exact
  per-provider-serialized `modify()`/`delete()` mechanism (a promise-chain map, one chain per
  provider id, never pruned).
- `packages/ai/src/auth/resolve.ts` (full) — `resolveProviderAuth`'s own "a stored credential owns
  the provider, no silent env fallback" comment (lines 44-49) and `resolveStoredOAuth`'s own
  double-checked-locking refresh sequence (lines 122-179), plus the `ModelsError("oauth", ...)` vs
  `ModelsError("auth", ...)` code split.
- `packages/ai/src/auth/oauth/pkce.ts` (full) — `generatePKCE`'s own entropy size, base64url
  encoding, and SHA-256 challenge derivation.
- `packages/ai/src/auth/oauth/device-code.ts` (full) — `pollOAuthDeviceCodeFlow`'s own
  interval/backoff/deadline/cancellation state machine and `abortableSleep`'s own signal-checking
  behavior; the two-message timeout split (plain vs. clock-drift-actionable) and RFC 8628 section
  3.2/3.5 citations in Pi's own comments.
- `packages/ai/src/auth/oauth/openai-codex.ts` (full) — the Codex-specific browser/device OAuth
  flows, PKCE usage, JWT decode for `chatgpt_account_id`, and the bare-pasted-code
  state-validation exception, read to correctly SCOPE what this pass defers (`PROV-011`,
  `PROV-012`) without implementing any of it.

Also re-read (retained from the prior kickoff discussion, not re-fetched): `design/2026-08-20-
minion-agent-design.md` (master design Phase 5 text), `process/agent-workflow.md`, `process/
implementation-conformance-workflow.md` §6/§8.1, `pi-parity-manifest.yaml`'s pre-pass state, and
the Layer-10 closure assurance chain (not merely its final summary).

## 3. EXISTING CODE AUDIT

Per the project's own existing-code rule, `minion-agent-python/src/minion_agent/` was inspected
from scratch before assuming Layer 11 starts at zero. Finding: it genuinely does start at zero for
this surface. The only pre-existing LLM-adapter code is `llm/adapters/mock.py` (`MockAdapter`,
Layer 10's own certified reference implementation) — no `auth/` package, no `codex_responses/` or
`openai_completions` adapter directory, and no OAuth/credential-store code of any kind existed
anywhere in the tree before this pass.

## 4. EXISTING PROV-001..005 INVENTORY

Audited before writing any new manifest row (`pi-parity-manifest.yaml` lines 3693-3745, pre-pass).
All five rows are pre-existing placeholders from the original bulk realignment pass, `phase: 5`,
`disposition: adopted`, each targeting `src/minion_agent/llm/adapters/codex_responses/` or an
`openai_completions` adapter — and each covers ONLY wire-protocol behavior, with NO auth coverage
at all:

- `PROV-001` — Responses thinking-signature replay (`convertResponsesMessages`).
- `PROV-002` — Responses text-signature V1/legacy encoding (`encodeTextSignatureV1`/
  `parseTextSignature`).
- `PROV-003` — reasoning summary/text projection (`processResponsesStream`).
- `PROV-004` — active transport abort (`openai-codex-responses.ts::stream`).
- `PROV-005` — OpenAI-completions reasoning replay (`openai-completions.ts::stream`/
  `convertMessages`).

None of the five overlaps this pass's own scope. They are left untouched, not repurposed. New rows
begin at `PROV-006`, the next available id.

## 5. LAYER-11 SLICE MAP

A planning map, not a frozen mandatory order — later passes may resequence within it as real
provider integration work clarifies what is actually needed next:

- **11A — Auth foundation** (THIS PASS): vocabulary, `CredentialStore`, ownership/refresh
  authority, generic PKCE, generic RFC 8628 device-code polling.
- **11B — Codex OAuth network integration** (not started): real browser/PKCE callback flow, real
  device-code endpoint calls, JWT account-id projection, bare-pasted-code handling (`PROV-011`,
  `PROV-012`).
- **11C — codex-responses wire adapter** (not started): the Responses wire-protocol behavior
  `PROV-001`-`PROV-004` already placeholder, implemented against real transport once 11A/11B exist.
- **11D — openai-completions wire adapter** (not started): `PROV-005`'s own wire-protocol behavior.
- **11E — streamSimple** (not started): `AI-031`, explicitly carried forward as Layer-11-owned, NOT
  implemented in this pass.
- **11F — fetchDeferred/cancelDeferred** (not started): `AI-032`, explicitly carried forward as
  Layer-11-owned, NOT implemented in this pass.
- **11G — fixture/live/manual provider verification** (not started): end-to-end checks against a
  real Codex/OpenAI account, necessarily manual/opt-in, not part of any automated gate.

`AI-031` and `AI-032` remain recorded in `pi-parity-manifest.yaml` exactly as Layer 10 left them
(`disposition: deferred parity`, `python`/`rust` both `NOT YET IMPLEMENTED -- deferred to Layer 11
(PROV-###)`) — unchanged by this pass, since neither is in Pass-1 scope; both remain visible Layer-
11 obligations for slice 11E/11F.

## 6. PASS-1 SCOPE

Built this pass, per the owner's own Pass-1 specification: the auth vocabulary (`PROV-006`), the
`CredentialStore` protocol and its in-memory reference implementation (`PROV-007`), refresh/
ownership authority (`PROV-008`), generic PKCE (`PROV-009`), and the generic RFC 8628 device-code
poller (`PROV-010`). Every one of these is provider-neutral: none of them performs a real network
call, and none of them is specific to Codex or any other single provider.

## 7. OUT-OF-SCOPE

Explicitly not attempted this pass: real `auth.openai.com` HTTP requests, real token exchange, a
local OAuth callback HTTP server, browser launching or interactive browser login, live device-code
HTTP calls, the Codex CLI credential-file loader, real OpenAI/Codex provider transport, the
`codex-responses`/`openai-completions` wire adapters themselves, `streamSimple`, `fetchDeferred`/
`cancelDeferred`, and any live/manual OAuth check. Layer 09's active-cancellation abstraction
(`RunSignal`) is reused exactly as already certified, via `AuthOperationOptions.signal` and the
device poller's own `signal` parameter — this pass does not redesign or extend Layer-09 semantics
in any way.

## 8. MANIFEST ROWS

Seven new rows added, `pi-parity-manifest.yaml`, immediately following `PROV-005` and before
`MINION-001`:

- `PROV-006` — auth vocabulary + `AuthContext` seam. `adopted`.
- `PROV-007` — `CredentialStore` serialized read-modify-write semantics. `adopted`.
- `PROV-008` — credential ownership / refresh mutation authority. `adopted`.
- `PROV-009` — generic PKCE (RFC 7636). `adopted`.
- `PROV-010` — generic RFC 8628 device-code poll state machine. `adopted`.
- `PROV-011` — Codex OAuth account-id projection (pure, non-network semantics). `deferred parity`,
  with an explicit closure trigger: the future pass implementing the codex-responses adapter's own
  auth resolution (slice 11C or later).
- `PROV-012` — Codex browser callback / device-code endpoint integration. `deferred parity`, with
  an explicit closure trigger: the future pass integrating real Codex browser/device network
  transport (slice 11B).

Every row cites: the exact pinned-Pi path/symbol, the observable rule, a non-empty list of genuine
test-name/canonical-scenario evidence (or, for the two deferred rows, an explicit "no fabricated
evidence for behavior not yet implemented" placeholder matching the SAME wording convention
`AI-031`/`AI-032` already use), the Python implementation path (or `NOT YET IMPLEMENTED` for the
deferred rows), and a `rust:` field naming this as pending independent Rust contract review (never
claiming Rust implementation or certification). `AI-031`/`AI-032` themselves are left byte-for-byte
unchanged — this pass does not resolve either row, since neither `streamSimple` nor
`fetchDeferred`/`cancelDeferred` is in scope. Verified via `tests/conformance/
test_manifest_validation.py` (all 8 structural checks pass): row-id uniqueness, required-field
presence, valid disposition, and well-formed `tests:` list structure all hold across the full
manifest, not merely the seven new rows in isolation.

## 9. SPEC TRACEABILITY

New dedicated file `minion-agent-docs/spec/auth.md`, per the owner's own guidance that auth has
enough independent semantics to warrant its own file rather than a section folded into `spec/
llm.md`. Covers: the auth vocabulary and its exact field/openness rules, the `AuthContext` seam,
the full `CredentialStore` contract (including what the in-memory reference implementation does
and does NOT prove), refresh/ownership authority and its double-checked-locking mechanism, generic
PKCE, the full device-code poll state machine (transitions, expiry-message split, abort
observation points), Pass-1's own explicit network exclusions, and the deferred Codex-specific
behavior list with its own closure criteria. No Python implementation mechanic (asyncio locks,
dataclass field defaults, exception class names) is made normative in this document — every
normative statement is phrased as an observable contract, matching the project's own shared-
contract authoring rule.

## 10. BEHAVIOR MATRICES

**`CredentialStore` (six cases, built before implementation, matching §8 of the owner's own
Pass-1 specification):**

1. Single `modify`: initial absent/A -> `modify` -> B -> read returns B.
2. `modify` callback raises: stored state is UNCHANGED from before the failed attempt; the
   exception propagates to the caller.
3. Two concurrent `modify` calls for the same provider id: the second's own callback observes the
   first's own committed result, never the original pre-first-call state.
4. `read` racing an in-flight `modify`: NOT serialized — observes whatever is currently stored at
   the moment it runs (Pi-observable contract, confirmed by direct source read, not invented).
5. `modify` on an absent credential: callback observes absent, not an error.
6. `modify` returning absent (`None`): the entry is left UNCHANGED, distinct from `delete`, which
   is the dedicated removal primitive.

All six proved directly against the real `InMemoryCredentialStore`, `tests/auth/test_store.py`
(`test_case1_*` through `test_case6_*`), plus additional cases beyond the minimum six: `delete`'s
own serialization against `modify` for the same provider id, non-serialization across different
provider ids, `list()`'s own no-secrets guarantee, and `AuthOperationOptions.signal` cancellation
at each of the two checked boundaries.

**Device-code poller (built before implementation, matching §9 of the owner's own Pass-1
specification):** immediate success; pending-then-success; pending-pending-then-success;
slow_down-then-success with a server-provided interval; slow_down-then-success with no server
interval (fixed +5s fallback); pending-then-slow_down-then-success; terminal protocol error;
expiry with no slow_down (plain message); expiry after a slow_down (clock-drift message); abort
before the first poll; abort during an inter-attempt sleep; abort during an in-flight `poll()`
call (proven NOT to interrupt that call — cancellation is observed only at the next loop-top
check); `wait_before_first_poll`; interval clamping to the 1-second minimum; the 5-second default
interval; a deliberately-sequenced `now()` probe proving the mid-iteration `break` guard fires
before any non-positive sleep is attempted. All 19 cases live in `tests/auth/test_device_code.py`,
driven by a fake, instantly-advancing clock and injected `sleep` — no real waiting, no live
network, matching the specification's own explicit requirement.

## 11. IMPLEMENTATION

New package `minion-agent-python/src/minion_agent/auth/`:

- `__init__.py` — module docstring recording Pass-1 scope and exclusions.
- `credential.py` — `JsonValue`, `AuthType`, `ApiKeyCredential`, `OAuthCredential`, `Credential`,
  `CredentialInfo`, `AuthOperationOptions`, `ModelAuth`, `AuthResult`, `AuthCheck`, `AuthContext`
  (Protocol).
- `context.py` — `DefaultAuthContext`.
- `store.py` — `CredentialStoreOperationCancelled`, `CredentialStore` (Protocol),
  `InMemoryCredentialStore`.
- `pkce.py` — `PkcePair`, `derive_pkce_challenge`, `generate_pkce`.
- `device_code.py` — `DevicePollPending`/`DevicePollSlowDown`/`DevicePollFailed`/
  `DevicePollComplete`, `DevicePollResult`, `DeviceFlowError`/`DeviceFlowCancelled`/
  `DeviceFlowTimedOut`/`DeviceFlowFailed`, `abortable_sleep`, `poll_device_code_flow`.
- `refresh.py` — `AuthorityError`/`OAuthRefreshError`/`CredentialStoreError`,
  `refresh_if_expiring`.

Layering: `tests/test_layering.py`'s own `FORBIDDEN` map extended with an `auth` entry, forbidden
from importing `llm`/`session`/`telemetry`/`agent`/`agent_loop`/`tools` — auth sits alongside
`runtime`, below the LLM vocabulary layer, and knows nothing about messages/streams itself. `llm`
is left free to import `auth` in a future pass (not yet exercised, since no adapter consumes it
yet). Confirmed via `tests/test_layering.py`, 5/5 passing.

Coverage configuration: `pyproject.toml`'s `[tool.coverage.run]` `source` allowlist extended with
`"src/minion_agent/auth"` — omitting this would have silently excluded the entire new package from
coverage measurement (see "FINDINGS/TAXONOMY" below).

Protocol stub methods (`AuthContext.env`/`file_exists`, all four `CredentialStore` methods) are
written single-line (`async def env(self, name: str) -> str | None: ...`), matching the existing
codebase convention (`Adapter` in `llm/service.py`, `Sink` in `telemetry/service.py`) — a
multi-line docstring-then-`...` body on a Protocol stub never executes, and therefore never
registers as covered, since Protocol methods are structural and never literally invoked.

## 12. CANONICAL EVIDENCE

One new canonical family, matching the established tool-registry/agent-inbox/llm-service
convention exactly: a new discriminator key `auth_device_code` under `conformance/agent/`, its own
schema `conformance/schema/auth-device-code-scenario.schema.json`, a thin runner
(`minion-agent-python/tests/conformance/auth_device_code_runner.py`) that drives the real
`poll_device_code_flow` function directly through a scripted `poll` sequence and an instantly-
advancing fake clock (implementing no interval/backoff/deadline logic itself), and a discovery-
based test file (`test_auth_device_code_conformance.py`).

Six scenarios: `auth-device-code-immediate-success`, `auth-device-code-pending-then-slow-down-
then-success`, `auth-device-code-slow-down-prefers-server-interval`, `auth-device-code-terminal-
failure-stops-immediately`, `auth-device-code-expiry-without-slow-down`, `auth-device-code-expiry-
after-slow-down-reports-clock-drift`. Each pins an exact `poll_count` (the number of scripted
`poll()` attempts the deterministic schedule consumes), computed by hand against the real
interval/deadline arithmetic before being written into the scenario, not merely asserted after the
fact against whatever the runner happened to produce.

Per the owner's own explicit §10 caution, this canonical shape deliberately does NOT attempt to
represent real-time precision or cancellation: only the discrete, deterministic mapping from a
scripted sequence of poll outcomes to a final result (`poll_count` plus `complete`/`error`) is
expressed in the language-neutral format — the same property `FakeClock`-based Python unit tests
already prove, replayed here through a shared, cross-language-checkable shape. `CredentialStore`
concurrency and PKCE derivation remain Python-only evidence for the same reason: a canonical
runner would otherwise have to reimplement lock/timing/entropy semantics itself to represent them,
which is exactly the "runner secretly implements the semantics under test" defect class `L10-R004`/
`C10-C004`/`L10-R007` caught repeatedly during Layer 10. The corresponding future Rust evidence
requirement for `CredentialStore` concurrency and PKCE is recorded under "RUST HANDOFF
REQUIREMENTS" below.

`test_schema_validation.py` and `test_agent_conformance.py` both updated to route/exclude the new
`auth_device_code` key exactly the way `llm_service` is already routed/excluded, preserving every
existing discriminator unchanged.

## 13. PYTHON TEST EVIDENCE

- `tests/auth/test_credential.py` — 9 tests, vocabulary shapes.
- `tests/auth/test_context.py` — 6 tests, `DefaultAuthContext`.
- `tests/auth/test_store.py` — 13 tests, the full six-case matrix plus delete/list/signal cases.
- `tests/auth/test_pkce.py` — 7 tests, including the independently-recomputed RFC 7636 Appendix B
  known vector.
- `tests/auth/test_device_code.py` — 19 tests, the full device-flow behavior matrix.
- `tests/auth/test_refresh.py` — 10 tests, including the double-checked-locking proof
  (`test_two_concurrent_expiring_callers_refresh_exactly_once`, asserting exactly one actual
  refresh call across two concurrent callers) and the corrected `test_logged_out_meanwhile_
  returns_none` (uses `store.delete`, not `store.modify(..., lambda _c: _set(None))` — the latter
  is a no-op under `CredentialStore`'s own contract, not a logout).
- `tests/conformance/test_auth_device_code_conformance.py` — 6 tests, one per canonical scenario.

Fresh full-suite counts (this pass, not reused from any earlier layer): `pytest` — 1251 passed, 19
xfailed (pre-existing `TO_BE_FILLED` placeholder scenarios, unrelated to this pass), 64 skipped,
0 failed; coverage — 100.00% (`TOTAL` 3074 statements, 0 missed), gated by `pytest-cov`'s own
`fail_under=100`; `ruff check .` — clean; `mypy` — clean, 65 source files; `ruff format --check .`
— the same pre-existing 7-file drift Layer 10's own closure already disclosed, unchanged by this
pass; `tests/test_layering.py` — 5/5; `tests/conformance/test_manifest_validation.py` — 8/8;
`tests/conformance/test_schema_validation.py` — clean, including the new `auth-device-code-
scenario.schema.json`; a manual secret scan (`grep` for token/key-shaped literals across every new
`auth/`, `tests/auth/`, and `auth-device-code-*` file) found only the two synthetic `"sk-test"`
placeholders already present in `test_credential.py` — no real credential of any kind.

## 14. RUST HANDOFF REQUIREMENTS

Independent of this pass's own Python implementation, a future Rust implementation of this
contract must produce its own evidence for:

- The full `CredentialStore` six-case matrix (§10 above) against its own concurrency primitive —
  Python-only unit-test evidence here is not a substitute for Rust's own proof of the same
  observable properties.
- RFC 7636 PKCE derivation against the SAME Appendix B known vector pinned in `tests/auth/
  test_pkce.py` (`RFC7636_APPENDIX_B_VERIFIER`/`RFC7636_APPENDIX_B_CHALLENGE`).
- The full device-code poll state machine, provable directly through the six auth-device-code-
  *.yaml canonical scenarios this pass adds — these ARE cross-language-checkable evidence, unlike
  the two items above, and a Rust runner should be built to execute them exactly as Python's own
  `auth_device_code_runner.py` does.
- Ownership/refresh-authority double-checked-locking behavior equivalent to `test_two_concurrent_
  expiring_callers_refresh_exactly_once` — provable in whatever idiom Rust's own concurrency
  primitives make natural, not required to mirror Python's `asyncio.Lock`-per-provider-id
  mechanism.

## 15. DEFERRED LAYER-11 ITEMS

`PROV-011` (Codex OAuth account-id projection), `PROV-012` (Codex browser callback / device-code
endpoint integration), `AI-031` (`streamSimple`, untouched, carried forward exactly as Layer 10
left it), `AI-032` (`fetchDeferred`/`cancelDeferred`, untouched, carried forward exactly as Layer
10 left it). None of the four is implemented, characterized-as-complete, or silently dropped by
this pass; each has an explicit closure criterion recorded either in `pi-parity-manifest.yaml`
directly (`PROV-011`, `PROV-012`) or unchanged from its own pre-existing closure criterion (`AI-
031`, `AI-032`).

## 16. FINDINGS/TAXONOMY

**Finding 1 — coverage silently excluded the entire new package.**
Classification: `CONTRACT_ASSURANCE_DEFECT`-adjacent process gap, not a semantic defect. After
writing all five `src/minion_agent/auth/*.py` files and running the full suite, the coverage
report's `TOTAL` line was byte-identical to its pre-pass value — `pyproject.toml`'s `[tool.coverage.
run]` `source` list is an explicit allowlist that did not yet include `"src/minion_agent/auth"`, so
pytest-cov silently tracked zero lines of the new package, which would have reported a misleadingly
-passing 100% total. Remediation: added the missing entry; this immediately surfaced genuine,
real gaps (each file below 100% individually) that had been silently hidden. Caught by manually
diffing the coverage report's own line count against the pre-pass baseline rather than trusting the
percentage alone — recorded here as a reusable check for any future new-package pass.

**Finding 2 — Protocol stub methods do not register as covered when written multi-line.**
Classification: implementation-mechanics defect, not semantic. `AuthContext.env`/`file_exists` and
all four `CredentialStore` methods, originally written with a docstring followed by a separate `...`
statement, showed as uncovered even after Finding 1's fix, since a Protocol is never literally
invoked and a standalone `...` line's coverage is execution-based. Remediation: collapsed to
single-line stubs, matching the codebase's own existing convention (confirmed against `Adapter`/
`Sink`), with explanatory prose moved to the enclosing class docstring.

**Finding 3 — dead/unreachable exception clause in `refresh.py`.**
Classification: code-quality, caught before commit, not a released defect. An `except
OAuthRefreshError: raise` clause wrapped `store.read()`, but `OAuthRefreshError` can only ever
originate from `attempt_refresh` (passed only to `store.modify()`, never to `store.read()`),
making the clause genuinely unreachable. Removed rather than fabricating a test to force coverage
of dead code, per this project's own "don't add error handling for scenarios that can't happen"
principle.

**Finding 4 — test design bug, not implementation bug.**
An early draft of `test_logged_out_meanwhile_returns_none` attempted to simulate a concurrent
logout via `store.modify("p", lambda _c: _set(None))`, which is a no-op under `CredentialStore`'s
own documented contract (`fn` returning absent leaves the entry unchanged, distinct from deletion)
— not a production defect, since the real `InMemoryCredentialStore` behaved exactly as specified;
the test itself was wrong. Fixed by using `store.delete("p")`, the actual dedicated removal
primitive.

No `PI_BEHAVIOR_UNCERTAIN` classification was needed this pass — every observable rule implemented
was confirmed directly against a full-text pinned-Pi read before being written into `spec/auth.md`
or `pi-parity-manifest.yaml`.

## 17. CONTRACT-QUALITY CHECK

Answering the owner's own §14 checklist directly:

- **Can Rust independently implement from spec+manifest without reading Python mechanics?** Yes —
  `spec/auth.md` states every rule as an observable contract (types/shapes/state transitions/
  error-class distinctions), never in terms of `asyncio.Lock`, Python exception classes, or
  dataclass mechanics.
- **Does `CredentialStore` define serialization strongly enough to prevent double-refresh without
  falsely promising cross-process locking?** Yes — `spec/auth.md`'s own `CredentialStore` section
  states the in-process serialization guarantee precisely and explicitly disclaims cross-process/
  filesystem/distributed locking in the same paragraph, not merely in Python docstrings.
- **Is credential ownership explicit enough that a future Codex CLI/external credential
  integration cannot accidentally gain refresh authority?** Yes — the "Refresh authority" section
  states the ownership rule (stored credential owns the provider; refresh happens ONLY through
  `modify()`) as a normative constraint, not an implementation incidental.
- **Does the generic device poller fully characterize timing/error/abort semantics before network
  integration begins?** Yes — every state transition, both timeout messages, and both abort-
  observation points are specified in `spec/auth.md` and proven by the behavior matrix (§10 above)
  before any real transport exists to drive it.
- **Are Codex-specific pure semantics explicitly tracked even though browser network integration
  is deferred?** Yes — `PROV-011`/`PROV-012`, each with its own closure criterion, plus a dedicated
  "Deferred Codex-specific behavior" section in `spec/auth.md`.
- **Are `AI-031` and `AI-032` still visible as Layer-11 obligations?** Yes — both rows are
  unchanged from Layer 10's own closure state, and both are named explicitly in the slice map
  above (11E/11F).
- **Did any runner acquire production semantics?** No — `auth_device_code_runner.py` drives the
  real `poll_device_code_flow` function directly and implements no interval/backoff/deadline logic
  of its own; `CredentialStore` concurrency and PKCE were deliberately kept out of canonical form
  for exactly this reason (see "CANONICAL EVIDENCE" above).
- **Did this pass accidentally freeze an old Codex CLI file path as the auth API?** No —
  `DefaultAuthContext` reads only generic environment variables and generic filesystem existence;
  it reads no provider-specific credential file, and `spec/auth.md`'s own `AuthContext` section
  states this exclusion explicitly.

No unresolved question remains from this checklist; nothing here is an open blocker.

## 18. REMOTE STATE

Pushed to short-lived candidate branches in both repos (see the coordination issue for exact head
SHAs and PR links) before requesting review. Both repos' candidate heads are confirmed reachable on
GitHub prior to review request, per `agent-workflow.md` §12's own mandatory remote-handoff rule.

## 19. NEXT ACTION

Requesting independent Rust contract review of: the auth vocabulary (`PROV-006`), `CredentialStore`
serialized-modify semantics (`PROV-007`), ownership/refresh authority (`PROV-008`), generic PKCE
(`PROV-009`), the generic RFC 8628 device-code poller (`PROV-010`), the two deferred Codex-specific
rows and their closure criteria (`PROV-011`, `PROV-012`), and this pass's own Layer-11 slice
coverage (§5 above) — NOT a request to implement Rust yet. `NEXT_OWNER = Codex`. This pass does
NOT proceed automatically into Codex browser OAuth, real HTTP transport, either real provider
adapter, `streamSimple`, `fetchDeferred`/`cancelDeferred`, or Layer 12; it stops at this handoff
gate per the owner's own explicit instruction.
