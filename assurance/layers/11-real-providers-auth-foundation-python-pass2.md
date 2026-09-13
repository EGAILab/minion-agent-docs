# Layer 11 (Real providers) — Auth Foundation, Python/shared certification, PASS 2 (remediation)

## 1. Starting state

Resuming from `EGAILab/minion-agent#24`'s own recorded `STATUS = PYTHON_REMEDIATION`,
`NEXT_OWNER = Claude`, following an independent Rust contract review that REJECTED the Pass-1
candidate:

- Reviewed candidates: code `56c8ae44029cd151d5ac68f0a0a2d97a449c216d` (PR #25), docs
  `95a3715e11637561fbd2fb4f740a1aee514a6a51` (PR #54), pinned Pi
  `b7bb00b936dbe21b8e160b3e89efdec361846699` (unchanged).
- Review evidence: `assurance/layers/11-real-providers-auth-foundation-rust-contract-review.md`,
  branch `review/11-rust-auth-contract`, commit `a97a683ab11e7115074447672f7fa107f89c4de5`, docs
  review PR #55.
- Verdict: `shared Layer-11 Pass-1 auth-foundation contract: REJECTED`; `Python Layer 11 Pass 1:
  REOPENED`; `Rust Layer 11: BLOCKED / NOT_IMPLEMENTED`; `Layer 11 cross-language: NOT CLOSED`.
- Seven blocking/documentary findings: `L11-R001` through `L11-R007` (four `PI_PARITY_DEFECT`,
  three `CONTRACT_ASSURANCE_DEFECT`), plus one `PARITY_NEUTRAL_HARDENING` note.

This pass 1) re-verified every finding directly against pinned Pi source (not merely trusted the
review's own paraphrase), 2) fixed each one in the shared contract and Python implementation,
3) added a permanent regression witness for each, and 4) re-ran every quality gate fresh. The
Pass-1 assurance document (`11-real-providers-auth-foundation-python.md`) is left byte-for-byte
unchanged, per this project's own "preserve historical review artifacts, append remediation
evidence instead of rewriting history" rule; this is a NEW, separate file for Pass 2.

## 2. Independent re-verification against pinned Pi

Every finding was re-derived directly from pinned Pi source before any fix was written, not
implemented from the review's own prose alone:

- `packages/ai/src/auth/credential-store.ts` (full re-read): confirmed `enqueue`'s own queued
  pre-task checkpoint (`await previous.catch(()=>{}); signal.throwIfAborted(); return task();`),
  `modify`'s own post-`fn` checkpoint (`options?.signal?.throwIfAborted()` immediately after
  `await fn(current)`, BEFORE `this.credentials.set(...)`), and the chain-pruning done-callback
  (`void tail.then(() => { if (this.chains.get(providerId) === tail) this.chains.delete(providerId); })`)
  -- confirming the chain genuinely IS pruned, contradicting the Pass-1 assurance's own "never
  pruned" claim (`PARITY_NEUTRAL_HARDENING`).
- `packages/ai/src/utils/abort.ts` (full re-read): confirmed `raceWithAbortSignal`'s own exact
  behavior -- rejects the CALLER's own promise on abort while the raced operation itself keeps
  running unaffected, its own eventual settlement observed only by the internal `.catch(()=>{})`
  chain, never by the caller who already moved on.
- `packages/ai/src/auth/resolve.ts:122-179` (re-read): confirmed
  `AbortSignal.any([signal, AbortSignal.timeout(DEFAULT_OAUTH_REFRESH_TIMEOUT_MS)])` (15_000 ms)
  is passed as `refreshSignal` to `oauth.refresh(current, refreshSignal)`.
- `packages/ai/src/auth/types.ts` (re-read in full): confirmed `AuthContext.env` carries NO
  blank-normalization requirement at the interface level (`types.ts:97-100`); confirmed the full
  `AuthPrompt`/`AuthInfoLink`/`AuthEvent`/`AuthInteraction`/`ProviderAuthInteraction`/`ApiKeyAuth`/
  `OAuthAuth`/`ProviderAuth` vocabulary (`types.ts:112-241`), previously unaudited by Pass 1.
- `packages/ai/src/auth/context.ts` (re-read): confirmed the blank-trim normalization is specific
  to `defaultProviderAuthContext`, not the `AuthContext` interface itself.
- `packages/ai/src/auth/oauth/device-code.ts` (re-read): confirmed the exact guard
  `typeof result.intervalSeconds === "number" && Number.isFinite(result.intervalSeconds) &&
  result.intervalSeconds > 0` gating server-interval trust.
- `packages/ai/src/models.ts` (targeted read, `checkAuth`/`getAuth`/`login`/`logout` call sites):
  confirmed real `Models`-level orchestration built on `resolveProviderAuth`, previously
  undispositioned by Pass 1.

No finding required a `PI_BEHAVIOR_UNCERTAIN` classification -- every one was independently
confirmable from source with no ambiguity, matching the review's own "no Pi behavior remains
uncertain" statement.

## 3. Remediation, per finding

### `L11-R001` — CredentialStore cancellation (`PI_PARITY_DEFECT`, fixed)

`InMemoryCredentialStore` (`store.py`) redesigned from a per-provider `asyncio.Lock` to a
per-provider FIFO chain of `asyncio.Task`s, matching Pi's own `enqueue`/`raceWithAbortSignal`
composition:

- `_enqueue`: captures the current chain entry as `previous`, schedules a `queued()` task that
  awaits `previous` (already exception-swallowing by construction -- see the dead-code note
  below), THEN checks the signal (the "queued pre-task" checkpoint), THEN runs the caller's own
  `task`. A `tail()` task wraps `queued()`, swallowing its exception so the NEXT queued call's own
  `await previous` never sees it, and republishes/prunes `self._chains[provider_id]` once done --
  restoring genuine pruning (see `PARITY_NEUTRAL_HARDENING` below).
- `_race_with_abort`: polls the signal (poll-only `RunSignal`, Layer 09, no push mechanism) at a
  fixed 50 ms interval against the `queued_task`, exactly mirroring `abortable_sleep`'s own
  established polling convention. Returns/raises based on whichever settles first -- if the
  signal aborts first, raises immediately WITHOUT cancelling `queued_task`, which keeps running.
- `modify`'s own existing post-`fn` checkpoint (`self._check_not_aborted(options)` immediately
  after `await fn(current)`) was ALREADY correct before this pass and is unchanged -- it is what
  actually discards a too-late `fn` result once the caller has already raced away.

Three new permanent regression witnesses, `tests/auth/test_store.py`:
`test_modify_queued_behind_another_never_runs_its_fn_once_aborted_while_still_queued`,
`test_delete_queued_behind_a_modify_never_runs_once_aborted_while_still_queued`,
`test_modify_wait_rejects_promptly_when_aborted_mid_callback_and_result_is_discarded` -- each
directly modeled on the review's own three minimal witnesses. A fourth witness,
`test_a_queued_modify_still_runs_after_an_earlier_queued_modify_raised`, proves the
"one caller's error never sours the chain" property this redesign depends on.

**Dead-code correction found during implementation:** an initial draft of `queued()` wrapped
`await previous` in its own `try/except Exception: pass`, mirroring Pi's own `.catch(() => {})` at
that exact call site. Direct analysis showed this is UNREACHABLE in this design: `previous` is
always a `tail()` task, and `tail()` already swallows every exception before ever being published
to `self._chains`, so `await previous` can never raise. Removed per this project's own "don't add
error handling for scenarios that can't happen" principle, rather than fabricating a test for dead
code (Pi's own redundancy here is harmless defensive duplication, not a behavior this port needs
to reproduce structurally).

### `L11-R002` — Refresh callback signal/timeout (`PI_PARITY_DEFECT`, fixed)

New module `auth/signal.py`: `Abortable` (a structural protocol every poll-based signal, including
`RunSignal`, already satisfies) and `CombinedSignal` (aborts when EITHER an optional caller signal
aborts OR a fixed budget elapses, matching `AbortSignal.any([signal, AbortSignal.timeout(ms)])`).
This is an ADDITIVE, auth-owned seam -- certified Layer 09's own `RunSignal` is untouched and not
reopened.

`refresh_if_expiring`'s own `refresh` parameter signature changed from
`Callable[[OAuthCredential], Awaitable[OAuthCredential]]` to
`Callable[[OAuthCredential, Abortable], Awaitable[OAuthCredential]]`; a new
`refresh_timeout_seconds: float = DEFAULT_REFRESH_TIMEOUT_SECONDS` (15.0) parameter and a new,
independently injectable `timeout_now: Callable[[], float] = time.monotonic` parameter (distinct
from the existing `now_ms` wall-clock-epoch-milliseconds expiry clock) were added so the budget is
deterministically testable with no real waiting.

New tests: `tests/auth/test_signal.py` (5 tests, `CombinedSignal`'s own budget/caller-signal OR
composition, fully clock-injected). `tests/auth/test_refresh.py`:
`test_refresh_receives_a_combined_signal_reflecting_caller_abort` (proves the caller's own signal
flows through, and that aborting it mid-refresh correctly discards the eventual result via the
SAME `L11-R001` post-`fn` checkpoint -- these two findings compose correctly, not in tension);
`test_refresh_signal_aborts_on_its_own_after_the_timeout_budget_elapses` (proves the 15-second
budget fires with no caller signal at all, via injected `timeout_now`). Every pre-existing
`refresh` test callable updated to the new two-argument signature.

### `L11-R003` — AuthContext protocol vs. default implementation (`PI_PARITY_DEFECT`, fixed)

`credential.py::AuthContext`'s own docstring corrected: the prior claim that "this protocol's own
contract preserves" blank-to-absent normalization was wrong -- Pi's own `AuthContext` INTERFACE
makes no such promise; only `defaultProviderAuthContext` (ported here as `DefaultAuthContext`)
does. The corrected docstring states the normalization is specific to the default implementation,
not a protocol-level guarantee, and the same for `file_exists`'s own concrete filesystem behavior.
No implementation code changed (`DefaultAuthContext` was already correctly scoped); this was a
documentation-only defect, but a load-bearing one, since a Rust implementer building strictly from
this contract would otherwise have wrongly required every `AuthContext` to normalize.

New test: `tests/auth/test_context.py::test_a_custom_context_may_return_a_blank_value_unchanged`,
using a new `_BlankPassthroughAuthContext` fixture proving a non-normalizing implementation is
conforming.

### `L11-R004` — Non-finite `slow_down` interval (`PI_PARITY_DEFECT`, fixed)

`device_code.py`'s own slow_down branch gained `math.isfinite(server_interval)` alongside the
existing `> 0` check, exactly matching Pi's own `Number.isFinite(result.intervalSeconds) &&
result.intervalSeconds > 0` guard. A non-finite value (e.g. `float("inf")`) now falls back to the
fixed +5s increment exactly like an absent one, never scheduled as an actual sleep duration.

New test:
`tests/auth/test_device_code.py::test_slow_down_with_a_non_finite_server_interval_falls_back_to_the_fixed_increment`.
The one affected canonical scenario (`auth-device-code-slow-down-prefers-server-interval`) is
UNCHANGED and remains a legitimate, if narrower, canonical witness for the "prefer the server
interval when finite and positive" branch -- the review's own §4 explicitly noted the canonical
shape cannot by itself discriminate "used the server interval" from "ignored it," and that this is
acceptable exactly because language-level unit evidence (this new test) carries the discriminating
proof, which it now does.

### `L11-R005` — Incomplete generic auth surface disposition (`CONTRACT_ASSURANCE_DEFECT`, fixed)

New manifest row `PROV-013`, `disposition: deferred parity`, covering Pi's `AuthPrompt`/
`AuthInfoLink`/`AuthEvent`/`AuthInteraction`/`ProviderAuthInteraction`/`ApiKeyAuth`/`OAuthAuth`/
`ProviderAuth` vocabulary and `Models.checkAuth`/`getAuth`/`login`/`logout` orchestration (built on
`resolveProviderAuth`). New `spec/auth.md` section "Deferred generic auth/provider orchestration
surface" states explicitly that this is NOT a demand to implement in any particular pass, only a
demand not to silently lose track of the discovered surface, with a closure criterion binding a
future provider-integration pass to audit and either adopt or disclose a deliberate divergence
from this exact vocabulary before inventing an ad hoc login/prompt shape.

### `L11-R006` — Credential alias/copy semantics (`CONTRACT_ASSURANCE_DEFECT`, fixed)

`credential.py`: `ApiKeyCredential.env` and `OAuthCredential.extra` both gained a `__post_init__`
(using `object.__setattr__`, valid on a frozen dataclass) that snapshots any mapping passed to the
constructor into a `MappingProxyType(dict(...))` -- breaking aliasing from the caller's own
original dict AND rejecting later item assignment on the stored mapping itself. `spec/auth.md` and
`pi-parity-manifest.yaml`'s own `PROV-006` row now explicitly document this as an intentional,
disclosed architectural hardening (full immutable-VALUE semantics) rather than a literal port of
Pi's own mutable-reference behavior -- and explicitly note that since a `Credential` is now fully
immutable at every level, "by reference" vs. "by value" is not an observable distinction, which is
what actually resolves the ambiguity the review found, not the specific container type chosen.

New tests:
`test_api_key_credential_env_is_immutable_and_not_aliased_to_the_constructor_argument`,
`test_oauth_credential_extra_is_immutable_and_not_aliased_to_the_constructor_argument` --
each proves both halves: mutating the original dict after construction does not affect the stored
credential, and item-assignment on the stored mapping itself raises `TypeError`.

### `L11-R007` — CredentialStore.list ordering (`CONTRACT_ASSURANCE_DEFECT`, fixed)

`spec/auth.md`'s `CredentialStore` section and `pi-parity-manifest.yaml`'s `PROV-007` row now
explicitly PIN insertion order (of each provider's own CURRENT entry) as a normative production
rule, not merely an incidental property of Python's own `dict` (which already happens to preserve
it) -- a hash-map-based Rust implementation with no stable iteration order does NOT satisfy this
contract without tracking insertion order separately. The existing
`test_list_reports_every_provider_without_secrets` test, which had weakened its own assertion to a
set comparison (unable to catch an order regression at all), was renamed
`test_list_reports_every_provider_without_secrets_in_insertion_order` and now asserts the exact
ordered list. A new test, `test_list_order_follows_the_current_entry_not_the_original_insertion`,
proves the delete-then-reinsert-moves-to-the-end case explicitly.

### `PARITY_NEUTRAL_HARDENING` — "never pruned" assurance correction (fixed)

The Pass-1 assurance document's own claim that Pi's per-provider promise-chain map is "never
pruned" was independently re-verified as WRONG against `credential-store.ts:24-26`'s own
done-callback (`if (this.chains.get(providerId) === tail) this.chains.delete(providerId)`) --
Pi's own chain map IS pruned when the tail is still current, and the store's redesigned Python
`_enqueue`/`tail`/`_prune` mechanism (`L11-R001` above) now does the exact same thing. The
INCORRECT claim is left untouched in the Pass-1 assurance file itself (preserving historical
review artifacts, per this project's own rule); `store.py`'s own class docstring now correctly
states the chain "genuinely is [pruned], both here and in Pi," with a note that an earlier
revision's own docstring claimed otherwise.

## 4. Contract-quality re-check

Re-answering the subset of the owner's own §14 checklist any finding above touches:

- **Can Rust independently implement from spec+manifest without reading Python mechanics?** Yes,
  unchanged from Pass 1's own answer -- every corrected rule above is stated in `spec/auth.md` as
  an observable contract, not Python-specific mechanics (`asyncio.Task`, `MappingProxyType`, etc.
  are cited only as this project's OWN chosen mechanism, never as the normative requirement).
  Pi's exact `raceWithAbortSignal`/queued-checkpoint semantics are now stated in prose Rust can
  implement with its own idiomatic concurrency primitives (a channel, a `tokio::sync::Mutex`
  queue, etc.) -- nothing requires literally porting an `asyncio.Task` chain.
  - **Does CredentialStore define serialization strongly enough to prevent double-refresh but not
  falsely promise cross-process locking, AND correctly characterize cancellation?** Yes -- the
  corrected `spec/auth.md` now states all four cancellation checkpoints explicitly, distinguishing
  "never ran" from "ran but discarded" from "caller stopped waiting but the operation didn't."
- **Is credential ownership explicit enough, INCLUDING value semantics?** Yes -- `L11-R006`'s own
  resolution is now explicit in both `spec/auth.md` and the `PROV-006` manifest row.
- **Does the generic device poller fully characterize timing/error/abort semantics, including the
  finite-interval edge case?** Yes -- `L11-R004`'s own fix is reflected in `spec/auth.md`'s device-
  code section.
- **Are all discovered Pi auth/provider surfaces given an explicit disposition, even if deferred?**
  Yes, now including `PROV-013` (`L11-R005`), closing the one gap the review found.
- **Did any runner acquire production semantics?** No change from Pass 1's own answer -- no
  canonical runner was touched this pass; the one affected canonical scenario
  (`auth-device-code-slow-down-prefers-server-interval`) is unchanged, its own known
  non-discriminating limitation now explicitly cross-referenced to the language-level test that
  actually discriminates it.

No unresolved question remains from this re-check.

## 5. Fresh quality gates (Pass 2)

Executed fresh, this pass, against the remediated candidate:

- `pytest` (full suite, with coverage): 1267 passed, 19 xfailed (pre-existing `TO_BE_FILLED`
  placeholder scenarios, unrelated to this pass), 65 skipped, 0 failed.
- Coverage: 100.00% (`TOTAL` 3133 statements, 0 missed) -- every `auth/*.py` file individually at
  100%, including the new `signal.py`.
- `ruff check .`: clean.
- `mypy`: clean, 66 source files (up from 65, the new `auth/signal.py`).
- `ruff format --check .`: the SAME pre-existing 7-file drift Layer 10's own closure already
  disclosed -- one transient 8th-file drift in `store.py`, introduced mid-remediation by this
  pass's own edits, was caught and reformatted back to the baseline before this final run.
- `tests/test_layering.py`: 5/5 (unchanged -- no new package boundary introduced this pass).
- `tests/conformance/test_manifest_validation.py`: 8/8, confirming the corrected `PROV-006`
  through `PROV-010` rows and the new `PROV-013` row are all structurally sound (unique ids,
  required fields, valid disposition, well-formed non-empty `tests:` lists).
- `tests/conformance/test_schema_validation.py`: clean, unchanged (no schema touched this pass).
- `tests/conformance/test_auth_device_code_conformance.py`: 6/6, unchanged (no canonical scenario
  content changed this pass, only the language-level unit test that discriminates `L11-R004`).
- Manual secret scan of every changed/added `auth/`, `tests/auth/` file: only the same two
  synthetic `"sk-test"` placeholders already present before this pass -- no real credential.

No lower-layer regression was run beyond the full suite above, since no lower-layer file was
touched by this remediation.

## 6. Findings disposition summary

```text
L11-R001  CredentialStore cancellation boundary          FIXED (store.py redesign + 3 witnesses)
L11-R002  refresh signal and timeout                     FIXED (auth/signal.py + refresh.py + tests)
L11-R003  AuthContext default/protocol distinction        FIXED (docstring correction + test)
L11-R004  finite slow-down interval                       FIXED (math.isfinite guard + test)
L11-R005  incomplete generic auth surface disposition      FIXED (PROV-013 + spec section)
L11-R006  credential alias/copy semantics undefined        FIXED (MappingProxyType + tests)
L11-R007  CredentialStore.list ordering undefined          FIXED (spec/manifest pin + test rename)
PARITY_NEUTRAL_HARDENING (never-pruned assurance error)    FIXED (store.py docstring corrected)
```

No new findings surfaced during remediation beyond the dead-code removal noted under `L11-R001`
above (itself not a Pi-parity defect, a code-quality correction made during the fix).

## 7. Remote state and next action

Pushed updated commits to the SAME candidate branches this pass started from
(`layer-11-pass1-auth-foundation` in both repos), updating the existing PRs (#25, #54) in place --
NOT new branches/PRs, since the coordination issue's own review requested remediation of the exact
same candidate lineage, not a fresh submission. Both updated heads confirmed reachable on GitHub
before requesting re-review.

`STATUS = RUST_CONTRACT_REVIEW` (re-requested; the previous approval of the pre-remediation SHAs is
stale and does not carry over). `NEXT_OWNER = Codex`. `NEXT_ACTION`: independently re-review the
remediated auth contract -- specifically confirm `L11-R001` through `L11-R007` are each actually
closed (not merely asserted closed), that the corresponding new/renamed tests actually exercise
the exact witnesses the original review specified, and that no new gap was introduced by this
remediation. Do NOT implement Rust yet. This pass does not proceed automatically into Codex browser
OAuth, real HTTP transport, either real provider adapter, `streamSimple`, `fetchDeferred`/
`cancelDeferred`, or Layer 12 -- it stops at this handoff gate.
