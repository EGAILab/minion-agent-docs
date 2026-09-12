# Layer 11 Auth Foundation — final-complete-review remediation (L11-R011, L11-R012, L11-R013)

## Review target rejected by this remediation

```text
code PR #25
    15c75983fd2b233c036a05f9d0b9f86c3b087b73

docs PR #54
    74ee233b3bdb3a9d386088ea24082befcaec09da

review PR #60
    3a32162bf3fb82ab680781927996b644c56169bf

verdict
    L11-R001 through L11-R010  all CLOSED (rechecked, not merely carried forward)
    L11-R011  PI_PARITY_DEFECT -- new
    L11-R012  PI_PARITY_DEFECT -- new
    L11-R013  PI_PARITY_DEFECT -- new

    shared Layer-11 Auth Foundation contract: REJECTED
```

This was the mandatory `agent-workflow.md` §11.8.8 "final complete review" -- every previously
provisionally-closed finding was independently rechecked from source rather than carried forward,
and the whole-contract audit surfaced three genuinely new mismatches that no prior targeted review
(each scoped to a narrower finding set) had occasion to find.

## Trigger check (agent-workflow.md §11.8, mandatory)

`L11-R011`, `L11-R012`, and `L11-R013` are each NEW findings, first raised by this exact review.
None has yet met either §11.8 trigger condition (a repeated finding, or a third rejected review on
the SAME finding) individually. This remediation therefore proceeds as an ordinary point-fix pass,
not a new convergence episode -- consistent with the review's own closing statement: "the
repeated-finding convergence trigger has not yet been met for them individually."

## Independent re-verification against pinned Pi source

Each finding was re-derived directly from source before being fixed, not implemented from the
review's own prose alone:

- `packages/ai/src/auth/resolve.ts:122-179` (re-read in full): confirmed `resolveStoredOAuth`
  builds exactly ONE `expiresSoon` closure, capturing the EFFECTIVE `minimumValidityMs =
  Math.max(DEFAULT_OAUTH_MINIMUM_VALIDITY_MS, minOAuthValidityMs ?? 0)`, and reuses that SAME
  closure for the initial trigger check, the under-lock recheck inside `modify()`'s own callback,
  AND the post-refresh validation (`if (minOAuthValidityMs !== undefined && expiresSoon(credential))
  { throw ... }`) -- there is no second, raw-value-based check anywhere in Pi.
- `packages/ai/src/auth/oauth/device-code.ts:51-86` (re-read): confirmed `Math.floor((options.
  intervalSeconds ?? DEFAULT_POLL_INTERVAL_SECONDS) * 1000)` for the initial interval and
  `Math.floor(result.intervalSeconds * 1000)` for a finite/positive server-provided `slow_down`
  interval -- both floors apply BEFORE the `Math.max(MINIMUM_INTERVAL_MS, ...)` clamp.
- `packages/ai/src/auth/context.ts:23-45` (re-read): confirmed `defaultProviderAuthContext`'s own
  `fileExists` wraps module import, tilde resolution, AND the `fs.access` call in one `try { ... }
  catch { return false; }`, and that its own tilde handling is literal string concatenation
  (`resolved.startsWith("~") ? homedir() + resolved.slice(1) : resolved`) with no path-join
  insertion and no other-user (`~username`) lookup.

No finding required a `PI_BEHAVIOR_UNCERTAIN` classification -- all three were unambiguous once
re-read directly against source.

## Remediation, per finding

### `L11-R011` — refresh post-validation used the raw explicit minimum

`refresh.py::refresh_if_expiring`'s own post-refresh check changed from
`_expires_soon(result, minimum_validity_ms, now_ms())` to
`_expires_soon(result, trigger_validity_ms, now_ms())` -- reusing the SAME effective (`max`'d)
threshold the initial trigger and under-lock recheck already use, matching Pi's own single-closure
design exactly. Docstring corrected to state there is only ever one threshold value per call.

New test: `test_explicit_minimum_smaller_than_default_still_uses_the_effective_threshold` -- the
review's own exact witness (now=0, stored expiry=0, explicit minimum=60_000ms, refreshed
expiry=120_000ms; must reject since 120_000 is inside the EFFECTIVE 300_000ms window). The
pre-existing `..._rejects_a_too_short_refresh` test uses an explicit minimum EQUAL to the default
and was confirmed (by inspection) unable to discriminate raw-vs-effective on its own.

**Independently confirmed discriminating by revert-and-confirm**: temporarily reverted the fix
(restored the raw `minimum_validity_ms` reference), ran the new test, confirmed it failed with
"DID NOT RAISE OAuthRefreshError", then restored the fix and confirmed the full suite passes again.

### `L11-R012` — device-code intervals omitted the whole-millisecond floor

New `device_code.py::_floor_to_whole_milliseconds(seconds) -> float` helper
(`math.floor(seconds * 1000) / 1000`), applied at both interval-computation sites: the initial
interval (`interval_seconds` or the 5-second default) and a finite/positive server-provided
`slow_down` interval. `DevicePollSlowDown`'s own docstring updated to note the floor applies to a
valid server interval before scheduling.

New tests: `test_fractional_initial_interval_is_floored_to_whole_milliseconds` and
`test_fractional_server_slow_down_interval_is_floored_to_whole_milliseconds`, both using
`interval_seconds=1.2349` and asserting the scheduled wait equals exactly `1.234` (not the raw
fractional value's own float representation, which drifts).

**Independently confirmed discriminating by revert-and-confirm**: temporarily removed the floor
calls at both sites, ran the two new tests, confirmed both failed with the exact drifted value the
review itself reported (`1.2348999999999999`), then restored the fix.

### `L11-R013` — `DefaultAuthContext.file_exists` didn't match Pi's failure/tilde behavior

`context.py::DefaultAuthContext.file_exists` rewritten to match Pi's exact two properties: (1)
tilde expansion is now literal string concatenation (`os.path.expanduser("~") + path[1:]`) rather
than `Path(path).expanduser()`, whose own platform-specific `~username`/Windows conventions do not
match Pi's naive rule; (2) the whole operation (path resolution plus the filesystem check) is
wrapped in `try/except OSError: return False`, matching Pi's own blanket failure-to-`false` rule
rather than letting a filesystem error propagate.

New tests: `test_file_exists_naive_leading_tilde_concatenation_for_a_nontrivial_suffix` (an
injected, known home directory plus a `~suffix`, no-separator input, proving literal concatenation
rather than path-join or username-lookup semantics) and
`test_file_exists_returns_false_on_a_filesystem_access_error` (a monkeypatched `Path.exists` that
raises `OSError`, proving `file_exists` resolves `False` rather than propagating).

Also corrected the `AuthContext` protocol docstring (`credential.py`) to note that
`DefaultAuthContext`'s own exact expansion algorithm and failure boundary are that implementation's
concrete fidelity to Pi, not a mechanism the protocol itself mandates for every implementation --
the protocol-level `L11-R008` requirement (any leading `~` means "the user's home directory," in
SOME form) is unaffected and remains closed.

**Independently confirmed discriminating by revert-and-confirm**: temporarily reverted
`file_exists` to `Path(path).expanduser().exists()` with no failure boundary, ran the two new
tests, confirmed both failed (the tilde witness resolved to the wrong path; the error witness
propagated the raised `OSError` uncaught), then restored the fix.

## Normative deltas

- `spec/auth.md`: the "Refresh / ownership authority" section now states the effective-threshold
  rule governs all three checks explicitly, with the `L11-R011` history noted. The device-code
  section gained a new "Millisecond flooring" paragraph. The `AuthContext` section gained a new
  "The default reference implementation's own exact `file_exists` behavior" paragraph, explicitly
  distinguishing the protocol-level tilde requirement (unchanged, `L11-R008`) from the default
  implementation's own concrete algorithm and failure boundary (`L11-R013`).
- `pi-parity-manifest.yaml`: `PROV-008` (refresh) and `PROV-010` (device-code) rule text extended
  with the `L11-R011`/`L11-R012` history and corrected evidence lists; `PROV-006` extended with the
  `L11-R013` paragraph and corrected `test_context.py` evidence description. All three rows keep
  `disposition: adopted` -- these are corrections to already-adopted Pi-parity rules, not new
  divergences.

## Fresh quality gates

- `pytest` (full suite, with coverage): 1283 passed, 19 xfailed (pre-existing, unrelated), 65
  skipped, 0 failed.
- Coverage: 100.00% (`TOTAL` 3135 statements, 0 missed).
- `ruff check .`: clean.
- `mypy` (default gate): clean, 66 source files.
- `mypy` including all three permanent typing fixtures: clean, 69 source files.
- `ruff format --check .`: the same pre-existing 7-file drift, unchanged.
- `tests/test_layering.py`: 5/5.
- `tests/conformance/test_manifest_validation.py`: 8/8.
- `tests/conformance/test_schema_validation.py`: clean, unchanged (no schema touched).
- `tests/conformance/test_auth_device_code_conformance.py`: 6/6, unchanged (no canonical scenario
  content changed -- `L11-R012`'s discriminating evidence lives in the new Python unit tests, per
  the review's own note that the canonical set "intentionally does not observe elapsed time").
- Manual secret scan of every changed `auth/`/`tests/auth/` file: clean, only the same two
  synthetic `"sk-test"` placeholders already present.
- Every fix independently confirmed discriminating via revert-and-confirm (documented per finding
  above), each restored to the exact intended state afterward (confirmed via `git diff`/re-run).

## Next action

Push the fixes to the same candidate branches, updating PRs #25/#54 in place. `STATUS =
RUST_CONTRACT_REVIEW`. `NEXT_OWNER = Codex`. Per §11.8.8, since every finding through this pass
(L11-R001 through L11-R013) will have been closed or remediated at a fresh exact candidate SHA,
request ONE new final complete review of that exact candidate rather than a targeted one -- the
prior "final complete" designation was rejected, so the next review is again a full, exact-SHA
complete review, not a narrower targeted-closure pass. Do not implement Rust yet. Do not start
Layer 12.
