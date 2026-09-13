# Layer 11 — L11-R014 convergence agreement

## Decision

```text
CONVERGENCE CONTRACT
    AGREED FOR IMPLEMENTATION
```

Exact checkpoint reviewed:

- code PR `EGAILab/minion-agent#25` at `658028decd8f86dfd4229693a4719c7fd06ca652`;
- docs PR `EGAILab/minion-agent-docs#54` at `1e111b9e1742954eb40d24dfb755dafcd0bbfec8`;
- pinned Pi at `b7bb00b936dbe21b8e160b3e89efdec361846699`;
- originating third final-complete review: docs PR #62 at
  `2d9062bded434e10054a7374509efa41ece257db`, whose own embedded characterization is the §11.8.3
  artifact this document challenges and agrees.

The exact docs checkpoint and coordination issue #24 were fetched from GitHub. Issue #24 recorded
`STATUS = CONTRACT_CONVERGENCE` and `NEXT_OWNER = Claude`. This is convergence-challenge/agreement
evidence only; no candidate, shared semantic file, or Rust production was changed by writing this
document.

## Trigger check (agent-workflow.md §11.8, mandatory)

`L11-R014` was first raised by the second final-complete review (docs PR #61, as a regression the
`L11-R012` fix itself introduced), remediated once (a non-throwing pass-through for non-finite
input at setup time), and found STILL OPEN by the third final-complete review (docs PR #62) for a
DIFFERENT, refined reason -- the setup-time crash is fixed, but a non-finite interval that is
actually USED to schedule a sleep (after a `pending` response, not an immediate `complete`) still
diverges observably from Pi. `Same material finding survives two independent reviews` -- the first
§11.8 trigger condition is met.

## Challenge pass (§11.8.4)

Independently re-verified, this pass, directly against pinned Pi source (not merely trusted from
the review's own embedded characterization):

- `packages/ai/src/auth/oauth/device-code.ts:46-97` (`pollOAuthDeviceCodeFlow`, full re-read):
  confirmed `intervalMs = Math.max(MINIMUM_INTERVAL_MS, Math.floor((options.intervalSeconds ??
  DEFAULT_POLL_INTERVAL_SECONDS) * 1000))` -- pure ECMAScript arithmetic, which (per the ECMAScript
  specification's own defined behavior for `Math.floor`/`Math.max`) NEVER throws and PROPAGATES
  `NaN`/`Infinity` through both operations unchanged (`Math.floor(Infinity) === Infinity`,
  `Math.floor(NaN) === NaN`, and `Math.max` returns `NaN` if EITHER argument is `NaN`, per the
  spec's own "if any value is NaN, return NaN" step -- unlike Python's own two-argument `max`/`min`,
  which instead perform an ordinary `>`/`<` comparison that silently treats `NaN` as "not greater/
  less," producing an ORDER-DEPENDENT, non-`NaN`-propagating result).
- `packages/ai/src/auth/oauth/device-code.ts:26-44` (`abortableSleep`): confirmed the computed
  `intervalMs` (or `Math.min(intervalMs, remainingMs)`) is handed directly to `setTimeout(callback,
  ms)` -- a HOST (Node/browser) API, not further ECMAScript-level arithmetic. Node's own documented
  `setTimeout` behavior (stable, non-version-specific Node.js API contract): "When delay is larger
  than 2147483647 or less than 1, the delay will be set to 1" -- meaning a delay of `Infinity`
  (which fails the upper-bound check) or `NaN` (which fails BOTH bound checks, since any comparison
  against `NaN` is `false`) is silently CLAMPED to a delay of 1 millisecond, not scheduled
  literally and not left to hang. This confirms the review's own central claim: Pi's own observed
  "next poll happens promptly" behavior for a used non-finite interval is a HOST-TIMER clamping
  effect, not something derivable from `pollOAuthDeviceCodeFlow`'s own pure-arithmetic layer alone.

**Answering the §11.8.4 checklist:**

- *Is the Pi source mapping correct?* Yes, confirmed above -- both the pure-arithmetic layer's own
  non-throwing special-value propagation and the HOST-timer clamping layer are independently
  verified against source (the former) and stable, documented host behavior (the latter, since
  `setTimeout`'s own internal clamping is implemented in Node's native bindings, not TypeScript
  source available in this pinned checkout).
- *Is the behavior matrix complete enough to distinguish realistic wrong implementations?* Yes --
  it directly separates "does setup throw" (already closed) from "does a USED non-finite interval
  eventually reach the next poll" (the open half), which is exactly the dimension the second
  remediation missed.
- *Are any cases implementation mechanics rather than observable semantics?* Yes, one, which the
  review's own text already flags: the EXACT clamped delay (Node's ~1ms) is a host-timer mechanism
  detail, not a portable observable contract -- Pi's own supported hosts (browsers, other JS
  runtimes) are not guaranteed to clamp to exactly 1ms, only to SOME small, finite, schedulable
  value that lets the timer fire. The only genuinely portable, source-grounded observable
  requirement is: a non-finite USED interval must resolve to A FINITE, PROGRESS-MAKING wait, not a
  literal, un-clamped `Infinity`/`NaN` duration.
- *Does any proposed fix silently reopen a lower certified layer?* No. Nothing here touches Layer
  09's `RunSignal` or any other certified layer; `abortable_sleep`'s own signal-checking contract
  is unaffected.
- *Can both Python and Rust implement the rule idiomatically?* Yes -- clamping a non-finite
  duration to a fixed, already-established floor (`MINIMUM_INTERVAL_SECONDS`) before scheduling a
  real sleep is trivial in both languages, and neither language needs to reproduce Node's own
  internal `setTimeout` clamping mechanism to satisfy the portable requirement above.
- *Does the defect's own root cause depend on an extensibility point one language's own certified
  lower layers exposes and the other does not?* No -- this is a pure numeric-edge-case handling
  question local to this module, with no cross-layer extensibility point involved.
- *Are all previous review findings represented by an executable or documentary acceptance
  criterion?* Yes, via the two required witnesses below (adopted from the characterization, made
  concrete with an exact clamped value rather than left as "some deterministic non-hanging
  observation").

**Refinement over the proposed characterization:** the characterization's own witnesses ask for "a
deterministic non-hanging observation" without committing to an exact clamped value. This
agreement makes that concrete: BOTH `NaN` and `Infinity`, when actually used to schedule a sleep,
clamp to `MINIMUM_INTERVAL_SECONDS` (the SAME pre-existing floor every other too-small interval
already clamps to, RFC 8628's own "never poll faster than this" concept extended to cover "cannot
tell how long to wait" too) -- not a new, additional magic constant, and not two DIFFERENT values
for `NaN` vs `Infinity` (Pi's own host-timer clamping treats both identically, per the Node
`setTimeout` contract quoted above, which fails BOTH numbers on the same bounds check). This
refinement is offered because leaving the exact clamp value unspecified would itself repeat this
same finding's own root problem (an under-specified contract two different implementers could
satisfy incompatibly) at one layer of abstraction lower.

## Agreed observable matrix (final)

| Observation | Required result |
|---|---|
| finite initial interval, used | floors to whole milliseconds, clamped to the 1-second minimum if smaller (unchanged, `L11-R012`) |
| non-finite (`NaN`/`Infinity`) initial interval, poll completes on the FIRST attempt | returns the completed value; the interval is never touched or clamped (unchanged, `L11-R014`'s own first remediation) |
| non-finite (`NaN`/`Infinity`) initial interval, poll returns `pending` first | the loop reaches and calls the SECOND poll attempt -- clamped to exactly `MINIMUM_INTERVAL_SECONDS` before the intervening sleep, under a fully deterministic fake clock |
| non-finite server-provided `slow_down` interval | UNCHANGED, `L11-R004`: ignored outright in favor of the +5s fallback increment -- never reaches this clamp at all |

## Agreed implementation and evidence constraints

The implementation pass must:

- clamp a non-finite duration to `MINIMUM_INTERVAL_SECONDS` at the point where a sleep is actually
  SCHEDULED (inside `abortable_sleep`, the module's own analog of Pi's host-timer boundary), not
  inside `_floor_to_whole_milliseconds` (which correctly remains a pure, non-clamping floor -- its
  own already-closed "pass through unchanged" contract for the not-yet-used, immediate-complete
  case must not regress);
- treat `NaN` and `Infinity` identically (both clamp to the SAME `MINIMUM_INTERVAL_SECONDS`), not
  via Python's own order-dependent `min`/`max` NaN comparison quirks, which must not be relied upon
  as the mechanism (an explicit `math.isfinite` check, not incidental comparison behavior);
- preserve every already-closed `L11-R004`/`L11-R012` behavior exactly (finite flooring, the
  finite/positive server-interval guard, the fixed slow_down fallback increment);
- add both required witnesses (`NaN`, `pending -> complete`; `Infinity`, `pending -> complete`) as
  permanent regression evidence, each asserting BOTH that the second poll is reached (`poll.
  call_count == 2`) and the exact deterministic elapsed simulated time (`MINIMUM_INTERVAL_SECONDS`);
- update `spec/auth.md`/`PROV-010` to state the finalized "used non-finite interval clamps to the
  minimum" rule, explicitly disclaiming exact host-timer sub-millisecond latency as normative.

## Scope and feasibility

No certified lower layer needs reopening. Rust can implement the agreed clamp-to-minimum rule
trivially (an `is_finite()` check before scheduling a `tokio::time::sleep`), with no need to
reproduce Node's own internal timer-clamping mechanism. No Rust implementation is authorized by
this document; Rust Layer 11 remains blocked until the remediated shared/Python candidate is
independently reviewed and approved under the normal workflow.

Real provider transport, browser OAuth, and Layer 12 remain out of scope and untouched.

## Agreement status

```text
CONVERGENCE CONTRACT
    AGREED FOR IMPLEMENTATION

OPEN FINDING
    L11-R014

CHALLENGE FINDINGS
    (one refinement, not a correction: the exact clamp value -- MINIMUM_INTERVAL_SECONDS, uniform
    for NaN and Infinity -- is made concrete rather than left as "some deterministic value," to
    avoid leaving this finding's own under-specification problem unresolved one layer down)

NEXT OWNER
    Claude

NEXT ACTION
    Implement the agreed clamp inside abortable_sleep, add both required witnesses, synchronize
    spec/manifest, rerun the full suite including every previously-closed L11-R001 through
    L11-R013 test, and return the exact remote candidate for a new complete review.
```

This agreement is a convergence checkpoint, not final contract approval or Layer-11 certification.
A new complete exact-SHA review remains mandatory once this fix is implemented.
