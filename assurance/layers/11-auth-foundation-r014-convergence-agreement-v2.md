# Layer 11 — L11-R014 convergence agreement, revision 2

## Decision

```text
CONVERGENCE CONTRACT
    AGREED FOR IMPLEMENTATION
```

Exact checkpoint reviewed:

- code PR `EGAILab/minion-agent#25` at `bbc06e97e1c0db3b0ece798841c15ea80540d6f8`;
- docs PR `EGAILab/minion-agent-docs#54` at `4965f37c2dbbe91682f14244a52ad14c0bbda60e`;
- pinned Pi at `b7bb00b936dbe21b8e160b3e89efdec361846699`;
- revision-1 agreement: `11-auth-foundation-r014-convergence-agreement.md`;
- originating fourth final-complete review: docs PR #63 at
  `3698582a40df491afb888094b6e725dfd0bffcb1`.

This is revision 2 of the L11-R014 convergence checkpoint -- revision 1's own agreed decision
(clamp a non-finite USED interval so the loop makes progress rather than hanging) is UNCHANGED and
remains correct. What revision 1 got wrong was the SPECIFIC clamp value, not the decision to clamp
at all.

## What the fourth review found

Revision 1's own implementation closed the permanent-hang witness completely (independently
reconfirmed by this review). But revision 1's own agreement text made an unforced choice: reuse
`MINIMUM_INTERVAL_SECONDS` (the project's own pre-existing one-second RFC-8628 polling floor) as
the fallback value for a non-finite interval, reasoning that "exact host-timer latency need not be
normative" gave latitude to pick any convenient, already-established constant.

The fourth review correctly identifies this as an overreach of that latitude: "exact latency need
not be normative" means Rust and Python need not reproduce Node's own internal `setTimeout`
mechanics bit-for-bit -- it does NOT mean the shared contract may adopt a value three orders of
magnitude different from Pi's own real, independently-confirmed observable behavior (Node's
documented `setTimeout` clamp: "If delay is larger than 2147483647 or less than 1, the delay will
be set to 1" -- i.e. exactly one millisecond) while still calling `PROV-010` `adopted` (Pi-parity)
rather than an intentional divergence. A choice that materially changes Pi-visible behavior by
1000x is not "some deterministic, non-normative latency" -- it is a different rule.

## Challenge pass (§11.8.4), confirming the correction

Re-verified, this pass, directly against pinned Pi source and Node's own documented `setTimeout`
contract (already independently confirmed once during revision 1's own challenge pass; re-confirmed
here since the review's own probe measured it live against a real Node process, which this
document treats as authoritative corroboration of the documented contract, not a new independent
claim requiring further verification):

- `packages/ai/src/auth/oauth/device-code.ts:26-44,51-53` (`abortableSleep`,
  `pollOAuthDeviceCodeFlow`'s own interval setup): unchanged from revision 1's own audit -- Pi's
  own pure arithmetic never throws and faithfully propagates `NaN`/`Infinity`; the actual clamp
  happens at the HOST-timer boundary (`setTimeout`), not in `pollOAuthDeviceCodeFlow` itself.
- Node's own documented `setTimeout(callback, delay)` contract: a `delay` that is `NaN` (fails
  every numeric comparison) or exceeds the maximum representable delay (`Infinity` always does) is
  clamped to `1`. This is Node's own STABLE, long-documented API contract, not a version-specific
  implementation detail -- reasonable to treat as durable, cross-version Pi-adjacent behavior for
  the lifetime of this project's own pinned revision.

**Answering the §11.8.4 checklist (delta from revision 1 only):**

- *Is the Pi source mapping correct?* Yes -- unchanged from revision 1, re-confirmed.
- *Is the behavior matrix complete enough?* Yes, with ONE correction: the required clamp VALUE is
  now stated concretely as Pi's own real magnitude (one millisecond), not left as "some minimum
  interval," closing the exact gap the fourth review found.
- *Are any cases implementation mechanics rather than observable semantics?* The exact clamp value
  itself is genuinely, unavoidably a magnitude choice -- but "roughly Pi's own real magnitude" is
  the OBSERVABLE requirement; the Python scheduler's own inability to guarantee true sub-
  millisecond precision is the implementation-mechanics part, already disclosed and unchanged.
- *Can both Python and Rust implement the rule idiomatically?* Yes -- a `0.001`-second (or
  equivalent `Duration::from_millis(1)`) clamp is trivial in both languages; neither needs Node's
  own internal timer machinery.
- *Does this reopen any certified lower layer or the revision-1 hang fix itself?* No -- the
  `math.isfinite` clamp-point DESIGN (inside `abortable_sleep`, not the pure-arithmetic helper) is
  unchanged; only the numeric VALUE it clamps to changes.

## Agreed correction

| Observation | Revision 1 (rejected) | Revision 2 (agreed) |
|---|---|---|
| non-finite interval, actually used | clamps to `MINIMUM_INTERVAL_SECONDS` (1.0s) | clamps to `NON_FINITE_INTERVAL_FALLBACK_SECONDS` (0.001s), a NEW, dedicated constant |
| relationship to the ordinary too-small-interval floor | conflated with it (same constant reused) | kept SEPARATE -- `MINIMUM_INTERVAL_SECONDS` remains RFC 8628's own unrelated floor for ordinary finite intervals |
| `PROV-010` disposition | `adopted`, inconsistent with a 1000x-larger-than-Pi value | `adopted`, now actually consistent (Pi's own real magnitude) |

Additionally required (found during re-implementation, not by the review itself, but the SAME bug
class): the initial-interval SETUP computation (`max(MINIMUM_INTERVAL_SECONDS, floored)`) and the
slow_down fallback increment (`max(MINIMUM_INTERVAL_SECONDS, interval + 5.0)`) both independently
risked the SAME Python `max()`-NaN-neutralization hazard `abortable_sleep`'s own revision-1 fix
already corrected at ITS call site -- a `NaN` interval could be silently turned into
`MINIMUM_INTERVAL_SECONDS` at either of those TWO OTHER call sites before ever reaching
`abortable_sleep`'s own explicit check, bypassing it entirely. Both are now fixed the same way
(explicit `math.isfinite` check, deferring to `abortable_sleep`'s own single clamp point) for
INTERNAL consistency -- not because the review's own probe exercised them, but because leaving
them unfixed would reproduce this exact finding's own root cause at a different call site the next
time someone probed a NaN-then-slow_down combination.

## Agreed implementation and evidence constraints

- introduce `NON_FINITE_INTERVAL_FALLBACK_SECONDS = 0.001`, distinct from
  `MINIMUM_INTERVAL_SECONDS`, with a docstring explaining both why it exists and why it is a
  SEPARATE concept from the ordinary polling floor;
- `abortable_sleep` clamps to the NEW constant, not the old one;
- fix the two additional `max()` call sites identified above for internal consistency;
- rename/refine the existing revision-1 tests to assert the corrected value (`0.001`, not `1.0`)
  and add one new test proving the nested NaN-then-slow_down case stays non-finite until clamped;
- update `spec/auth.md`/`PROV-010` to state the corrected magnitude and the two-revision history
  (so a future reader understands why the exact value changed, not just what it currently is).

## Scope and feasibility

No certified lower layer needs reopening. This is a pure constant-value and internal-consistency
correction; the `abortable_sleep` clamp-point DESIGN from revision 1 is retained unchanged. Rust
can implement the corrected magnitude trivially. No Rust implementation is authorized by this
document.

## Agreement status

```text
CONVERGENCE CONTRACT
    AGREED FOR IMPLEMENTATION

OPEN FINDING
    L11-R014 (revision 2)

CHALLENGE FINDINGS
    (none -- the fourth review's own finding is confirmed correct on independent re-verification;
    this document's own job is recording the corrected value, not disputing the finding)

NEXT OWNER
    Claude

NEXT ACTION
    Implement the corrected constant and the two additional consistency fixes, update the
    revision-1 tests to the corrected value, add the nested NaN-then-slow_down witness,
    synchronize spec/manifest, rerun the full suite including every previously-closed
    L11-R001 through L11-R013 test, remediate the co-located new L11-R015 finding in the same
    pass, and return the exact remote candidate for a new complete review.
```

This agreement is a convergence checkpoint, not final contract approval or Layer-11 certification.
A new complete exact-SHA review remains mandatory once this fix is implemented.
