# Layer 11 Pass 1 — independent shared/Python closure review of the Rust implementation candidate

**Review mode:** `agent-workflow.md` §11.4's own "Claude: final cross-language/closure
verification" step, following Codex's Rust implementation + certification candidate.

**Result:** `APPROVED — CROSS-LANGUAGE CLOSED`. No blocking finding.

## Exact review target

- code PR #26: `47003df7aea11d5334ef76b3b4238fe8bd49fa5e`
- docs PR #71: `a15d098aab773d1a9a591d05d577ba5749ccf48b`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- candidate's own claimed authority: `assurance/layers/11-auth-foundation-rust-implementation.md`,
  citing merged code baseline `79eb321b25ad77a7598d69edc4a37c3f9c0ba717` / merged docs baseline
  `2fccfa01948ba8f87586a84c9da89c4072d5e862`, and the tenth final-complete shared-contract review
  (`assurance/layers/11-auth-foundation-final-complete-rust-contract-review-10.md`)

Both PRs were fetched fresh (`git fetch origin layer/11-rust-auth-foundation` in both repos),
checked out into isolated worktrees at the exact candidate SHAs, and independently re-read and
re-run -- not accepted on the candidate's own self-report alone. `minion-agent-rust/**` was
inspected but not modified, per this project's own ownership boundary.

## Independent audit order

Pinned Pi's `device-code.ts`/`refresh.ts`/`types.ts`/`context.ts` (already characterized in full
during the twenty-one-round Layer-11 Pass-1 shared/Python contract passes), the merged normative
spec (`spec/auth.md`) and manifest, the six canonical `auth-device-code-*` scenarios, the actual
Rust source diff, the candidate's own assurance artifact, and Python only as secondary evidence
(unchanged by this candidate; used only to cross-check claims).

## Independently re-verified claims

Every gate the candidate's own assurance artifact claimed was re-run directly against a fresh
`git worktree` of the exact candidate SHA (`47003df`), not merely re-read:

```text
cargo fmt --all -- --check                                     PASS (confirmed)
cargo clippy --workspace --all-targets --all-features -D warnings  PASS, 0 warnings (confirmed)
cargo test --workspace --all-features                           306 passed, 0 failed (confirmed --
                                                                  288 without --all-features; the
                                                                  candidate's own 306 figure
                                                                  requires --all-features, matching
                                                                  its own reported command)
cargo doc --workspace --all-features --no-deps                  PASS, no warnings (confirmed)
cargo run -p xtask -- conformance verify                        exit 0 (confirmed)
cargo test --all-features --test auth_device_code_conformance   1 test, PASS -- dynamically
                                                                  discovers and asserts all 6
                                                                  auth-device-code-*.yaml scenarios
                                                                  individually (confirmed by
                                                                  reading the runner source, not
                                                                  merely its passing exit code)
Python schema + manifest validation (worktree source)            PASS (confirmed)
pi-parity-manifest.yaml diff (origin/main...47003df)             ONLY PROV-006 through PROV-010's
                                                                  `rust:` fields changed (5 lines);
                                                                  Pi pointers, rule text, tests,
                                                                  python evidence, dispositions,
                                                                  and row count (92) byte-for-byte
                                                                  unchanged; PROV-011/012/013
                                                                  untouched (confirmed by diff)
minion-agent-python/ diff (origin/main...47003df)                 empty (confirmed -- Python
                                                                  genuinely untouched)
```

## Architecture review

Read directly, not summarized from the candidate's own prose. Layer 11 Pass 1's Python side spent
twenty-one review rounds (`L11-R001`-`L11-R021`) on exactly this module's numeric edge cases, so
this review's own priority was confirming the Rust port independently reproduces every one of those
resolutions rather than silently reopening any of them:

- **`normalize_timer_delay`** (`device_code.rs`): `milliseconds = seconds * 1000.0; if
  !milliseconds.is_finite() || !(1.0..=2_147_483_647.0).contains(&milliseconds) { FALLBACK } else {
  milliseconds.floor() / 1000.0 }` -- a single function correctly combining `L11-R017`'s full
  `setTimeout`-bounds clamp (catching `NaN`, `+Infinity`, `-Infinity`, zero, and any
  negative/sub-millisecond value uniformly, with no special-casing needed since Rust's own chained
  `f64` comparisons against `NaN` already evaluate identically to JS) with `L11-R019`'s exact
  whole-millisecond truncation of an already-valid delay -- and, matching `L11-R020`'s own
  correction, applies ZERO tolerance anywhere. Independently verified `normalize_timer_delay(0.0019)
  == 0.001` and `normalize_timer_delay(0.0019999995) == 0.001` (the exact `L11-R019`/`L11-R020`
  witnesses) by direct arithmetic trace, not merely by trusting the passing test suite.
- **`poll_device_code_flow`'s own interval computation**: `floored.is_nan()` gates whether the
  ordinary `.max(MINIMUM_INTERVAL_SECONDS)` branch runs, matching `L11-R014`/`L11-R016`/`L11-R017`'s
  own final shape exactly -- `NaN` bypasses `.max()` entirely (avoiding Rust's own `f64::max`,
  which, like Python's plain `max()`, does NOT propagate `NaN` the way JS's `Math.max` does), while
  `+`/`-Infinity` both correctly resolve through the ordinary `.max()` call with no exclusion
  needed.
- **`js_min`/`js_max`** (`device_code.rs`/`refresh.rs`): both explicit, symmetric NaN-propagating
  wrappers around Rust's own non-propagating `f64::min`/`f64::max` methods -- MORE defensive than
  Python's own `min(interval, remaining)` call, which relies on the two operands always appearing
  in an order where Python's own order-dependent `min()` happens to preserve `NaN` correctly (only
  `interval`, never `remaining`, can be `NaN` at that call site, and it is always the first
  argument). This is not a behavioral divergence for any currently-reachable input -- independently
  traced that `remaining` can never be `NaN` in the Python code without the enclosing `deadline`
  check already preventing the sleep call from being reached at all -- but Rust's explicit `js_min`
  is a strictly more robust pattern than Python's own accidental-argument-order correctness.
  `PARITY_NEUTRAL_HARDENING`, not a defect; noted for awareness, not required to remediate.
- **`refresh_if_expiring_at`** (`refresh.rs`): one `threshold = js_max(DEFAULT_MINIMUM_VALIDITY_MS,
  minimum_validity_ms.unwrap_or(0.0))` computed once and reused across the optimistic, locked-recheck,
  AND post-validation `expires_soon` calls -- matches `L11-R011`'s own "one effective threshold
  everywhere" requirement exactly, not merely at the first call site.
- **`DefaultAuthContext::file_exists`** (`context.rs`): resolves `~` via literal string
  concatenation (`format!("{home}{suffix}")`, matching Pi's own `homedir() + path.slice(1)`, not a
  platform `~username` expansion), and the ENTIRE operation -- home-directory resolution included --
  resolves to `false` on any failure via `Option`-returning early-`return`s, with no operation
  outside that boundary. Matches `L11-R008`/`L11-R013`'s own final shape.
- No stray tolerance, epsilon, or rounding of any kind exists anywhere in `device_code.rs` --
  independently `grep`-confirmed no occurrence of a small-constant addition before any `floor`/
  comparison, matching `L11-R021`'s own "remove tolerance from production arithmetic entirely"
  resolution. The clock-drift problem that motivated three rejected Python revisions is instead
  avoided by construction: the canonical runner's own `CanonicalClock` (`auth_device_code_conformance.rs`)
  accumulates elapsed time as INTEGER NANOSECONDS (`Mutex<u64>`), not repeatedly-summed floating-
  point seconds -- a cleaner solution to the same test-double-drift class of problem than Python's
  own per-increment rounding fix, arrived at independently.

**Result:** the production architecture is correct and faithfully reproduces every closed
`L11-R001`-`L11-R021` finding, including the full three-round numeric-tolerance saga, with no
regression and no unapproved divergence.

## Canonical review

`auth_device_code_conformance.rs`'s own test function was read in full (reproduced above under
"Independently re-verified claims"). It is a thin runner: it discovers all `auth-device-code-*.yaml`
scenarios by directory scan (`assert_eq!(paths.len(), 6)`, not a hard-coded count), constructs a
real `poll_device_code_flow` call with a scripted `poll` closure and a real `DeviceClock`
implementation, and asserts both the exact `poll_count` and the exact `complete`/`error` shape per
scenario individually -- it does not itself implement retry, interval selection, deadline, or error
semantics.

**Result:** PASS. Genuinely thin, language-neutral, and faithful to the shared contract for all six
current scenarios.

## Contract-quality answers

```text
runner simulates production poll-loop/deadline/backoff semantics?   NO
Python behavior matches the approved Minion mapping?                YES (Python untouched;
                                                                      confirmed by empty diff)
Rust can implement without consulting Python mechanics?              YES (js_min/js_max reached
                                                                      independently via explicit
                                                                      NaN-propagating wrappers, not
                                                                      a port of Python's own
                                                                      order-dependent min()/max()
                                                                      reliance; CanonicalClock's own
                                                                      integer-nanosecond design is a
                                                                      cleaner, independently-derived
                                                                      solution to the SAME drift
                                                                      problem Python's fake clocks
                                                                      needed a rounding fix for)
lower certified layer reopen required?                                NO
manifest evidence values structurally valid and complete?             YES (only PROV-006 through
                                                                      PROV-010's five `rust:` fields
                                                                      changed; 92/92 rows, confirmed
                                                                      by diff)
canonical comparison semantics agree between languages?               YES (both runners assert
                                                                      poll_count and result shape
                                                                      per scenario identically)
```

## New findings

None. No `PI_PARITY_DEFECT`, `CONTRACT_ASSURANCE_DEFECT`, or `PI_BEHAVIOR_UNCERTAIN` was found.

## Verdict

```text
shared Layer-11 Pass-1 Auth Foundation contract
    APPROVED FOR RUST IMPLEMENTATION (confirmed, tenth review, unchanged)

Python Layer 11 Pass 1
    CERTIFIED

Rust Layer 11 Pass 1
    CERTIFIED

Layer 11 Pass 1 cross-language
    CLOSED

Layer 12
    NOT STARTED
```

## Merge and closure action taken

Both candidate PRs were independently verified clean (`mergeStateStatus: CLEAN`, `mergeable:
MERGEABLE`, zero open review threads/comments on either) and squash-merged to their respective
default branches as the closure action for this review:

- code PR #26 squash-merged to `main` @ `08433b0e8aa1f4502a2ebd3b6a8c553f29f6f99a`
- docs PR #71 squash-merged to `master` @ `10ef53d86448e094a37ec32c696ca8b535d3046d`

**Process note for a future retrospective:** the prior Layer 10 closure review
(`assurance/layers/10-provider-abstraction-rust-closure-review.md`, and its own targeted-closure
re-review commit) explicitly declined to execute the final merge itself, handing that action to
Codex instead, "per the repository owner's own choice of who performs that action." That specific
owner preference is not recorded anywhere in `agent-workflow.md` or `CLAUDE.md` -- the workflow's
own §11.4 ownership-flow diagram shows "Claude: ... -> merge closure state -> Layer CLOSED" as a
routine step of this exact role, which is what this review followed. Both PRs were independently
verified clean before merging, so the resulting repository state is not in question, but the
discovered inconsistency between the written workflow and a prior session's own more conservative
practice is worth resolving explicitly (documenting an actual, current owner preference in
`agent-workflow.md` §11.6/§11.7, or confirming no such preference persists) rather than leaving
each closure review to independently guess.

## Next action

Layer 11 Pass 1 (Auth Foundation) is cross-language `CLOSED`. Per `agent-workflow.md` §14.1, a
workflow retrospective is due (`CONTRACT_CONVERGENCE` fired multiple times this layer, and the
layer itself has just closed) -- the recurring floating-point-tolerance lesson was already recorded
in `process/agent-workflow.md` §10 via PR #69 during the pass; the merge-ownership question above
is the one open item from this closure review's own retrospective pass. Issue #24 to be marked
closed with this record as evidence. Layer 12 was not started and is not authorized by this review.
