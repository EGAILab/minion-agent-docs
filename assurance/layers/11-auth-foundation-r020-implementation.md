# Layer 11 — L11-R020 implementation

## Candidates

```text
prior rejected candidate (eighth final-complete review)
    code 769af8be33caff97a5483ee3c3abbb14f8dbbc78 (L11-R019 fix)
    docs 914a318dd183cd5257c9931dc223a3150d22a763 (L11-R019 implementation record)
    docs PR #67 @ 6120bb4c03ff71eeeffee2c064c458f6b2a8485d

eighth final-complete review (rejecting)
    assurance/layers/11-auth-foundation-final-complete-rust-contract-review-8.md
    (Codex's own review branch/PR #67 -- not merged into this branch; referenced by SHA only)
```

## §11.8 trigger-check statement

Layer 11's "three rejected reviews" trigger has been continuously active since the fifth review
(eight rejections accumulated). `L11-R020` is a first occurrence, found on the SAME
`_floor_to_whole_milliseconds`/deadline-remainder surface `L11-R019` just introduced -- this
document proceeds as a continuation of the same special-number/boundary-precision convergence
episode, per the same discipline as every prior `1X-auth-foundation-r0*-implementation.md` record in
this series, rather than opening an independent standalone agreement checkpoint.

## What the eighth review found, and why it is correct

`L11-R019`'s own remediation added a `1e-6` ms epsilon tolerance directly inside the SHARED
`_floor_to_whole_milliseconds` helper -- the same helper `L11-R012` already used for every genuine,
caller/server-supplied interval. That epsilon was reasoned as "many orders of magnitude smaller than
the smallest genuinely-fractional delay any caller passes," but this reasoning only checked delay
values THIS PROJECT'S OWN EXISTING TESTS happened to exercise, not the full space of values pinned
Pi's real runtime must handle correctly. `1.9999995` ms is a valid public value in that space -- a
delay `_needs_setimeout_clamp` accepts outright (well inside `[1, 2147483647]` ms) -- and Node's real
`setTimeout` (`Math.trunc`, which rounds toward zero, never to nearest) truncates it DOWN to `1` ms.
The global epsilon instead rounded it UP to `2` ms: a genuine, silent, cross-language-observable
divergence for a real input, not merely a correction of internal clock-drift noise. The review's own
framing ("the epsilon therefore changes genuine public inputs, not merely internal clock drift") is
exactly right, and independently re-confirmed here by direct computation before implementing any fix
(see below).

## Independent re-verification

- Computed directly: `0.0019999995 * 1000 = 1.9999995`; `math.floor(1.9999995) == 1`, matching
  Node's own documented truncate-toward-zero contract exactly.
- Computed directly: `math.floor(1.9999995 + 1e-6) == math.floor(2.0000005) == 2` -- confirming the
  prior epsilon-tolerant helper produces the WRONG answer (`2` instead of `1`) for this exact input,
  reproducing the review's own claim independently rather than trusting its prose alone.
- Re-read `_floor_to_whole_milliseconds`'s own callers before deciding where the fix belongs:
  `L11-R012`'s two upstream call sites (initial-interval setup, slow_down server-interval flooring)
  always receive a LITERAL, caller/server-supplied value -- never a value derived from this module's
  own clock arithmetic. `L11-R019`'s own `abortable_sleep` call site receives whatever raw delay a
  DIRECT caller passes -- also always a genuine external value, by definition (that is the entire
  point of the exported function). The ONLY value in this entire module actually at risk of
  floating-point drift is `poll_device_code_flow`'s own `remaining = deadline - now()`, which is
  never itself a public API parameter -- it is entirely internal. This confirms the review's own
  required remediation ("isolate floating-point deadline-drift handling to the internally derived
  deadline remainder") identifies the one and only place tolerance is actually justified.

**Answering the §11.8.4-equivalent checklist:**

- *Is the Pi source mapping correct?* Yes -- `Math.trunc` never rounds to nearest; it always
  truncates toward zero, for every input, with no tolerance of any kind.
- *Is the behavior matrix complete enough?* Yes, now distinguishing three classes of value at this
  boundary: invalid (clamped, `L11-R017`), genuine valid (exact truncation, `L11-R012`/`L11-R019`),
  and internally-derived-with-drift (epsilon-snapped, isolated to one call site, `L11-R020`).
- *Are any cases implementation mechanics rather than observable semantics?* The epsilon-snapped
  case (`remaining`) IS purely implementation mechanics -- it exists solely to compensate for this
  module's OWN Python-only slicing mechanic (`abortable_sleep`'s signal-polling loop), never a Pi
  behavior; keeping it isolated to that one internal value, rather than the shared public-delay
  helper, is precisely what keeps it from leaking into observable semantics.
- *Can both Python and Rust implement the rule idiomatically?* Yes -- an exact truncation helper
  plus one separately-named, narrowly-scoped tolerant helper used only where drift can occur is a
  direct, unambiguous shape in either language.
- *Does this reopen `L11-R019`'s own core decision?* No -- the DECISION that a valid delay must
  truncate to a whole millisecond, and that `poll_device_code_flow`'s own deadline remainder can
  legitimately need tolerance, are both UNCHANGED. Only the epsilon's SCOPE is corrected.

## Agreed correction

| Value | Source | Prior (rejected) | Corrected |
|---|---|---|---|
| Caller `interval_seconds` / server `slow_down` interval | Genuine public input | epsilon-tolerant floor (`L11-R012` path) | EXACT floor, no tolerance |
| `abortable_sleep` direct-call delay | Genuine public input | epsilon-tolerant floor (`L11-R019` path) | EXACT floor, no tolerance |
| `poll_device_code_flow`'s own `remaining = deadline - now()` | Internal, drift-prone | epsilon-tolerant floor (same shared helper) | EXACT tolerance still applied, but via a SEPARATE, narrowly-named helper used only here |
| `1.9999995` ms, direct call | Genuine public input (new witness) | rounded UP to `2` ms (bug) | truncates DOWN to `1` ms |

## Implementation

`device_code.py`:

- `_floor_to_whole_milliseconds` restored to EXACT truncation (`math.floor(seconds * 1000) / 1000`,
  no epsilon) -- used for `L11-R012`'s two upstream call sites and `L11-R019`'s `abortable_sleep`
  direct-call truncation, all genuine public delays.
- New `_snap_deadline_remainder_to_whole_milliseconds(remaining: float) -> float`, carrying the
  SAME `1e-6` ms epsilon tolerance `L11-R019` originally added, but used ONLY at the two call sites
  that compute `poll_device_code_flow`'s own deadline remainder (the `wait_before_first_poll`
  branch and the main loop's own retry-sleep computation) -- never reachable from any genuine
  caller/server-supplied delay.

`tests/auth/test_device_code.py`: one new permanent witness --
`test_abortable_sleep_direct_call_near_millisecond_boundary_truncates_exactly` -- calling
`abortable_sleep(0.0019999995, ...)` directly and asserting the total elapsed time is
`pytest.approx(0.001)` (1 ms), proving the exact-truncation contract holds for a genuine
near-boundary public delay, per the review's own explicit requirement.

**Independently confirmed discriminating by revert-and-confirm (both directions)**:

1. Reverted `_floor_to_whole_milliseconds` back to the epsilon-tolerant form while leaving the new
   witness test in place: it failed with the EXACT symptom the review reported (`0.002 == 0.001`,
   i.e. rounded UP instead of truncated DOWN). Restored the exact form; the witness (and the full
   32-test-plus-witness suite) passed.
2. Reverted the main poll loop's own call to `_snap_deadline_remainder_to_whole_milliseconds` back
   to a direct, un-snapped `remaining`: the pre-existing `auth-device-code-expiry-without-slow-down`
   conformance scenario reproduced the EXACT original `L11-R019` regression symptom
   (`IndexError: list index out of range`, one extra unscripted `poll()` call from an undershot
   deadline). Restored the snap call; the scenario passed again.

Both revert-and-confirm passes prove the fix is genuinely load-bearing on both sides of the
boundary-isolation split the review required.

## Normative deltas

- `spec/auth.md`: unchanged -- the epsilon tolerance was never a normative, cross-language-observable
  rule (it is a Python-implementation-only numerical-robustness detail confined to one internal
  value), so `L11-R019`'s own spec paragraph (which already only described the exact-truncation
  contract, never mentioning any tolerance) required no correction.
- `pi-parity-manifest.yaml`: `PROV-010`'s rule text gains a `L11-R020` correction paragraph
  appended after the (now-superseded) `L11-R019` epsilon-neutrality claim, preserving that claim's
  own history per this project's append-only remediation-history convention rather than rewriting
  it; test count updated to 33.

## Fresh quality gates

- `tests/auth/test_device_code.py` (targeted, `--no-cov`): 33 passed, 0 failed.
- `tests/conformance/test_auth_device_code_conformance.py` (targeted, `--no-cov`): all scenarios
  passing, including `auth-device-code-expiry-without-slow-down` (re-confirmed via the
  revert-and-confirm pass above).
- `tests/conformance/test_manifest_validation.py`: 8/8.
- Full `pytest` suite (fresh, with coverage): 1297 passed, 19 xfailed (pre-existing, unrelated), 0
  failed.
- Coverage: 100.00% (`TOTAL` 3158 statements, 0 missed).
- `ruff check .`: clean.
- `mypy` (default gate, `files = ["src/minion_agent"]`): clean, 66 source files.
- `mypy` including all three permanent typing fixtures: clean, 69 source files.
- `ruff format --check .`: back to the same pre-existing 7-file drift baseline, no new drift.

## Next action

Push to the same candidate branches, updating PRs #25/#54 in place. `STATUS = RUST_CONTRACT_REVIEW`,
requesting a NEW complete exact-SHA review per §11.8.8. `NEXT_OWNER = Codex`. Do not implement Rust
yet. Do not start Layer 12.
