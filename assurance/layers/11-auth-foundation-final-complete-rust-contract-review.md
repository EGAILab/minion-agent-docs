# Layer 11 Auth Foundation — Final Complete Independent Rust Contract Review

## Exact review target

```text
code PR #25
    15c75983fd2b233c036a05f9d0b9f86c3b087b73

docs PR #54
    74ee233b3bdb3a9d386088ea24082befcaec09da

pinned Pi
    b7bb00b936dbe21b8e160b3e89efdec361846699

targeted L11-R006 closure evidence
    docs PR #59 @ 5c0bc599ba7d2319e6f756f86c40f8473d96e848
```

Both candidate heads were fetched from GitHub and matched the latest handoff on coordination
issue `EGAILab/minion-agent#24`. Both PRs were open, Ready for Review, unmerged, and remotely
reachable. This is the mandatory `agent-workflow.md` §11.8.8 complete review after every prior
finding was provisionally closed. Review order was pinned Pi, normative spec, manifest, canonical
evidence, certified Rust architecture, assurance, then Python as secondary evidence.

No candidate code, shared semantic file, canonical file, or Rust implementation was changed.

## Prior-finding closure ledger

The final review rechecked the source/contract/evidence for every previous finding rather than
carrying the targeted verdicts forward as final certification:

| Finding | Final-review result at exact candidate |
|---|---|
| L11-R001 | CLOSED — queued pre-task cancellation, post-callback discard, caller-visible wait race, and chain pruning match Pi. |
| L11-R002 | CLOSED — refresh receives a caller-or-timeout combined signal; Layer 09 is not modified. |
| L11-R003 | CLOSED — blank normalization is correctly default-context-only. |
| L11-R004 | CLOSED — server slow-down interval must be finite and positive. |
| L11-R005 | CLOSED — generic auth/provider orchestration has an explicit deferred owner and closure criterion in PROV-013. |
| L11-R006 | CLOSED — credential mappings and scalar fields are mutable through the typed API, retain live references, and now have a permanent mypy fixture. |
| L11-R007 | CLOSED — production `list()` insertion order and delete/reinsert behavior are normative and tested. |
| L11-R008 | CLOSED for its stated finding — leading-tilde support is protocol-level and the literal `"~"` witness discriminates. The newly discovered exact default-context behavior is separately L11-R013 below. |
| L11-R009 | CLOSED — both credential records permit scalar reassignment. |
| L11-R010 | CLOSED — API-key `env` is flat string-to-string; OAuth `extra` owns recursive open JSON. |

The Round-3 fixture was freshly checked with both its dedicated 67-file mypy command and the
combined 69-file typing-fixture command. It covers top-level `env`/`extra` assignment and API-key/
OAuth scalar reassignment without suppressions.

## Independent pinned-Pi audit

Files read directly at the pinned revision included:

- `packages/ai/src/auth/types.ts`
- `packages/ai/src/auth/context.ts`
- `packages/ai/src/auth/credential-store.ts`
- `packages/ai/src/auth/resolve.ts`
- `packages/ai/src/auth/oauth/pkce.ts`
- `packages/ai/src/auth/oauth/device-code.ts`
- relevant `models-runtime.test.ts` and `oauth-device-code.test.ts` call sites/tests

Three new mismatches surfaced only in the final whole-contract audit.

### L11-R011 — explicit refresh post-validation uses the wrong threshold

Classification: `PI_PARITY_DEFECT`.

Pinned Pi computes one effective threshold:

```text
minimumValidityMs = max(300000, minOAuthValidityMs ?? 0)
expiresSoon = now + minimumValidityMs >= expires
```

The same `expiresSoon` closure is used for the initial trigger, the under-lock recheck, and the
post-refresh rejection when an explicit minimum was supplied. The candidate correctly uses the
effective maximum for the first two checks, but post-validates with the raw caller value.

Discriminating witness run against the real candidate:

```text
now                         0 ms
stored expiry               0 ms
explicit requested minimum  60000 ms
refreshed expiry             120000 ms

pinned Pi
    rejects: 120000 is inside the effective 300000 ms window

candidate
    accepted 120000
```

`spec/auth.md`, PROV-008, and the helper docstring also describe the candidate's raw-explicit-
minimum interpretation, so this is a shared rule defect as well as a Python implementation defect.

Required remediation: use the effective `max(default, explicit-or-zero)` threshold for the
post-refresh check whenever an explicit value is present; correct spec/manifest prose; add the
smaller-than-default explicit witness above as permanent evidence. The existing longer-than-default
test is not discriminating for this case.

### L11-R012 — device-code intervals omit Pi's whole-millisecond floor

Classification: `PI_PARITY_DEFECT`.

Pinned Pi floors both the caller's initial interval and a finite positive server-provided
`slow_down` interval with `Math.floor(seconds * 1000)` before scheduling. The candidate carries
fractional seconds directly. Real-candidate probes using `1.2349` seconds observed total scheduled
waits of `1.2348999999999997` seconds for both paths; pinned Pi schedules exactly `1.234` seconds.

The current spec and PROV-010 pin the one-second minimum and finite/positive server selection but
omit the integer-millisecond floor. Two reasonable Rust/Python implementations can therefore
differ observably while satisfying the written rule.

Required remediation: state the whole-millisecond floor language-neutrally for both initial and
server-provided intervals; implement it; add discriminating fractional-interval language evidence
(or extend the existing fake-clock canonical observation to expose elapsed time). The current
canonical server-interval scenario explicitly cannot distinguish timing and does not close this.

### L11-R013 — DefaultAuthContext does not match Pi's fileExists failure/tilde behavior

Classification: `PI_PARITY_DEFECT`.

Pinned Pi wraps module resolution, home resolution, and filesystem access in one `try/catch` and
returns `false` on every failure. It also treats *any* string beginning with `~` as
`homedir() + path.slice(1)`.

The candidate calls `Path(path).expanduser().exists` without a failure boundary. Patching the real
`Path.exists` seam to raise `OSError("denied")` made candidate `file_exists` propagate `OSError`;
Pi returns `false`. Python's conventional `expanduser` also does not implement Pi's any-leading-
tilde concatenation: on the review platform `Path("~suffix").expanduser()` resolved to
`C:\\Users\\suffix`, whereas Pi concatenates the current home directory with `suffix`.

L11-R008 remains closed: it established protocol ownership and a literal `"~"` witness. L11-R013
is the newly audited complete behavior of the default implementation.

Required remediation: specify and implement false-on-resolution/access-failure; pin Pi's exact
any-leading-tilde mapping rather than relying on platform `expanduser` conventions; add an access-
error witness and a nontrivial leading-tilde witness such as `~suffix` with an injected/known home.

## Manifest and contract ledger

| Row | Pi / shared / evidence result | Verdict |
|---|---|---|
| PROV-006 | Credential vocabulary, mutable credential semantics, env/extra domain split, and protocol-level tilde ownership are accounted for. Default `file_exists` failure and exact expansion behavior are incomplete (L11-R013). | FAIL |
| PROV-007 | Store ordering, mutation serialization, cancellation checkpoints, and reference behavior are complete. | PASS |
| PROV-008 | Ownership, double-checking, combined signal, and error split are present; post-refresh threshold semantics are wrong (L11-R011). | FAIL |
| PROV-009 | PKCE entropy, encoding, SHA-256 derivation, and evidence agree with Pi. | PASS |
| PROV-010 | Poll outcomes, backoff selection, cancellation points, and timeout split are represented; millisecond flooring is absent (L11-R012). | FAIL |
| PROV-011 | Codex account-id/auth projection is explicitly deferred with a concrete future closure criterion. | PASS (deferred) |
| PROV-012 | Codex browser/device endpoint integration is explicitly deferred with a concrete future closure criterion. | PASS (deferred) |
| PROV-013 | Generic login/provider orchestration vocabulary is explicitly deferred with a concrete future closure criterion. | PASS (deferred) |

Manifest structure is sound: 92 rows, 92 unique IDs, and all manifest validation tests pass. The
problem is semantic content, not YAML structure.

## Canonical evidence and Rust feasibility

Six `auth_device_code` scenarios are discovered. Their schema is language-neutral and the Python
runner is thin: it builds typed outcomes, injects a fake clock/sleeper and scripted poll transport,
calls the real poller, and normalizes the result. It does not implement polling decisions itself.

The canonical set proves outcome sequencing, retry/terminal behavior, poll counts, and the timeout
message split. It intentionally does not observe elapsed time, so it cannot prove server interval
selection or the newly found millisecond floor. Language tests may carry that distinction if the
spec pins it precisely.

The certified Rust tree has no auth implementation yet, but it already provides typed signals,
Tokio synchronization, ordered/testable infrastructure, SHA-256 dependencies, and canonical
runner conventions. Rust can implement the corrected store, refresh, PKCE, device poller, and
context rules idiomatically. None of L11-R011–R013 requires changing a certified Layer 01–10
observable contract. No lower-layer reopen is required.

The current contract is not independently implementable without guessing: a Rust author cannot
derive the raw-vs-effective refresh postcheck, fractional scheduling, or default file-failure rule
from the current normative artifacts and would reasonably reproduce the same mismatches.

## Fresh gates at the exact candidate

```text
full Python suite
    1278 passed, 19 xfailed, 0 failed

coverage
    100.00% — 3127 statements, 0 missed

auth tests
    91 passed

schema + manifest + auth canonical + layering selection
    224 passed

ruff
    PASS

mypy including all three permanent typing fixtures
    PASS — 69 source files

manifest
    92 rows / 92 unique IDs

candidate Rust diff
    none
```

Green existing tests do not exercise the three new discriminating witnesses above.

## Findings and verdict

```text
PI_BEHAVIOR_UNCERTAIN
    none

PI_PARITY_DEFECT
    L11-R011 refresh post-validation uses raw explicit minimum instead of Pi's effective threshold
    L11-R012 device-code interval scheduling omits Pi's whole-millisecond floor
    L11-R013 DefaultAuthContext propagates file errors and uses non-Pi tilde expansion semantics

CONTRACT_ASSURANCE_DEFECT
    none separate from the shared-rule omissions embodied by L11-R011 through L11-R013

PARITY_NEUTRAL_HARDENING
    none

PARITY_CONSTRAINED_RISK
    none
```

```text
shared Layer-11 Auth Foundation contract
    REJECTED

Python Layer 11 Pass 1
    REOPENED

Rust Layer 11
    BLOCKED / NOT_IMPLEMENTED

Layer 11 cross-language
    NOT CLOSED

Layer 12
    NOT STARTED
```

L11-R001 through L11-R010 remain closed at this exact candidate. Remediate only L11-R011 through
L11-R013 and their directly affected spec/manifest/evidence. These are new findings from the final
complete review; the repeated-finding convergence trigger has not yet been met for them individually.
Do not implement Rust Layer 11 or start Layer 12.
