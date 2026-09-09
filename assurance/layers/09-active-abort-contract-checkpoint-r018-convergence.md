# Layer 09 — L09-R018 contract convergence (AGENT_TRANSFORM_CONTEXT delegation grammar)

**Revision 2, NOT yet approved.** Revision 1 (this same file) was independently challenged
(`assurance/layers/09-active-abort-contract-checkpoint-r018-rust-challenge.md`, docs PR #39,
review commit `a6c05675d85b76a01ce6ba1b6d0a0abdf1d37f80`): **CONVERGENCE CONTRACT — PROPOSED,
REVISION REQUIRED**. The core `{0, 1, 3}` legal-delegation-length grammar was ACCEPTED outright,
along with the structural-ambiguity diagnosis and the full re-audit of every other
authoritative-metadata waterfall. Three narrow corrections were required before explicit
agreement:

- **`C18-1`** (reject at the authority boundary, not downstream): revision 1's own pseudocode for
  the invalid length-2 case (`return current` unchanged, relying on the next listener's own fixed
  arity to reject it) does not structurally refuse the tuple -- `EventBus.waterfall` permits
  arbitrary registered callables, including a variadic listener or one with compatible defaults
  that could silently ABSORB a malformed 2-tuple instead of raising. Revision 2 raises directly
  inside `normalize_step` itself, before the malformed tuple is ever forwarded to `step(index + 1,
  ...)` -- see "Proposed design" below.
- **`C18-2`** (represented failure, not bare propagation): revision 1's own acceptance witness 1
  said to assert a bare `TypeError` "raises/propagates" out of the run. That is not what the
  already-certified Layer-08 contract actually does: `_transform_context` runs inside
  `_execute_run`'s own `try`/`except Exception` boundary, so ANY exception it raises (including
  the new `WaterfallError` this revision introduces) is caught and routed to `_settle_run_failure`
  -- `prompt()`/`continue_()` itself completes normally, with a synthesized terminal `error`
  assistant message, not an escaping exception. Revision 2's real-loop witnesses now assert that
  represented-failure outcome explicitly (and that no provider request was ever sent), reserving
  the bare exception assertion for the DIRECT unit-level witness only.
- **`C18-3`** (RED/regression accounting corrected): revision 1 mischaracterized the retired
  trailing-omission shape's own witness as "already passes today... a regression guard." It does
  not -- PASS 9's own `_restore_signal` currently ACCEPTS that shape (silently, via `current[1]`),
  so a new test asserting it is now REFUSED is a genuine RED witness against PASS 9, exactly like
  the leading-omission witness. Only the UNCHANGED full-length redirect test is an already-green
  regression guard. Corrected below.

**Trigger check (mandatory, `process/agent-workflow.md` §11.8):**

- The mandatory `§11.8.8` final complete review of the PASS-9 candidate explicitly invoked
  convergence itself, in its own words: "Because this is the same authority-normalization
  mechanism family as `L09-R006` and `L09-R015` after repeated review cycles, workflow
  convergence applies. A checkpoint/challenge should settle the payload grammar before further
  code changes; the reviewer must not author that shared repair." That is a direct, explicit
  invocation of `§11.8`, not merely my own inference.
- Independently, the finding-lineage evidence supports the same conclusion: the review's own
  finding ledger marks `L09-R006` -- an already-`CLOSED` finding from PASS 3 -- **`REOPENED BY
  L09-R018`**. `L09-R006` and `L09-R018` are the same underlying mechanism (authoritative-metadata
  restoration inside a waterfall payload) applied to the exact same event
  (`AGENT_TRANSFORM_CONTEXT`): `L09-R006` established that `signal` must survive a listener's own
  redirect/drop attempt; `L09-R018` shows the redirect half was correctly closed but the drop half
  was only ever tested for ONE of its two authoritative fields, and the untested direction
  (leading-field omission) corrupts the payload. A "closed" finding whose own closure is
  subsequently shown incomplete on the exact same mechanism is precisely the kind of repeat-cycle
  `§11.8`'s trigger language addresses, even though `L09-R018` is technically a fresh finding ID on
  its first rejection.
- `L09-R015` is the SIBLING instance of this exact failure MODE (a normalize_step that handled
  redirect but not true omission), on a DIFFERENT event (`AGENT_PRE_STEP`/`AGENT_PREPARE_NEXT_
  TURN`), closed in PASS 9 by making the fix arity-aware. `L09-R018` shows that fix pattern does
  not directly generalize when an event has MORE THAN ONE authoritative field -- arity alone
  becomes ambiguous rather than merely incomplete. This is a genuine, not cosmetic, design
  question the project has now hit twice on the same event and once on its close cousins.

**Determination:** enter `CONTRACT_CONVERGENCE` for the `AGENT_TRANSFORM_CONTEXT` delegation
grammar (`L09-R018`). This is a `§11.8.3` characterization pass, building on the final review's own
rich characterization (the exact corrupting witness, the required remediation shape, the explicit
prohibition on "type/position guessing that admits two valid interpretations"), followed by my own
`§11.8.4`-equivalent design pass, proposed here for Codex's own independent agreement. No
implementation in this artifact -- `§11.8.1`'s "freeze unrelated implementation work" applies.

## Exact state under convergence

- code PR: `EGAILab/minion-agent#17`, exact head: `e015c20c25b3506372c1887a6f7b079a7f8d9e7a`
- docs PR: `EGAILab/minion-agent-docs#26`, exact head: `7012b28ee5b8784a8b72367afd294a1b2b1ad99c`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- `L09-C001`-`C003`, `L09-R001`-`R005` (seam existence only), `L09-R007`-`R017`: `CLOSED`,
  unaffected, not reopened by this convergence. `L09-R006` is reopened ONLY insofar as it shares
  root cause with `L09-R018`; its own original redirect-half fix is independently reconfirmed
  correct by the final review ("blocked for the tested trailing-signal form") and needs no further
  change.

## Characterization: the four delegation shapes and why one collides

`AGENT_TRANSFORM_CONTEXT`'s own waterfall payload is `(instance, messages, signal)` -- three
positions, three fixed roles:

| Position | Field | Role |
|---|---|---|
| 0 | `instance` | authoritative -- Minion's own added architectural metadata, no Pi analogue |
| 1 | `messages` | the ONLY transformable field -- pinned Pi's own `transformContext(messages, signal)` first argument |
| 2 | `signal` | authoritative -- pinned Pi's own `transformContext(messages, signal)` second argument |

A listener delegates by calling `next_(*replacement)`. `EventBus.waterfall`'s own forwarding rule
(`forwarded = replacement or current`) means an EMPTY replacement (`next_()`) is a true no-op --
`current` (already full-length) passes through untouched, and `normalize_step` is applied to it
regardless (harmlessly, since it is already the full, correct shape). A NON-empty replacement of
any length is `forwarded` directly, THEN passed to `normalize_step`. There are therefore exactly
four semantically distinct delegation intents a listener might have, and the code must correctly
recognize each:

1. **Full, explicit** (`next_(a, b, c)`, length 3): every position given, whether original or a
   forgery at an authoritative position. UNAMBIGUOUS -- there is exactly one way to fill 3 fixed
   positions with 3 given values, so position 0 is always `instance`, 1 is always `messages`, 2 is
   always `signal`, regardless of content. The PASS-8/9 candidate handles this correctly today
   (`current[1]` is genuinely `messages`), and the final review's own ledger confirms it
   ("blocked for the tested trailing-signal form").
2. **Trailing omission** (conceptually `next_(instance_or_forgery, messages)`, length 2): the
   listener supplies what it believes are positions 0-1 and omits `signal` entirely, trusting
   `normalize_step` to restore it. This was the ORIGINAL, documented, tested convenience this
   event was built to support ("A listener no longer needs to re-supply `signal` when delegating
   with a replacement").
3. **Leading omission** (conceptually `next_(messages, signal)`, length 2): the listener supplies
   what it believes are the two genuinely PI-LEVEL arguments (`messages`, `signal`) and omits the
   MINION-ADDED `instance` entirely, on the reasonable assumption that an architectural-extension
   field it never asked for should not need restating either. This is the shape the final review's
   own witness constructs.
4. **Both omitted** (conceptually `next_(messages)`, length 1): the listener supplies only the one
   field it actually wants to transform, omitting both authoritative fields. NOT exercised by any
   existing test; the current implementation crashes on it (`current[1]` raises `IndexError` for a
   length-1 tuple).

**The collision:** shapes 2 and 3 are BOTH length-2 tuples. Nothing about a bare 2-tuple's own
length, position, or (without inspecting content) type distinguishes "the trailing field is
missing" from "the leading field is missing" -- they are structurally identical inputs to
`normalize_step`. The PASS-8/9 candidate's own `_restore_signal` silently commits to interpretation
2 unconditionally (`current[1]` is always treated as `messages`), which is correct for shape 2 and
SILENTLY WRONG for shape 3: under shape 3, `current[0]` (`messages`, the caller's real intent) is
discarded as though it were a forged `instance`, and `current[1]` (`signal`, a live `RunSignal`
object) is forwarded downstream AS IF it were `messages` -- the exact corruption the final review's
own witness reproduced (`downstream_messages_type RunSignal`, `request_messages_type RunSignal`).

This is a STRUCTURAL property of the payload shape, not an implementation oversight fixable by a
smarter conditional: `instance` (authoritative) and `signal` (authoritative) sit on OPPOSITE ends of
the single transformable field `messages`. Contrast with the already-fixed `L09-R015` events
(`AGENT_PRE_STEP`, `AGENT_PREPARE_NEXT_TURN`), which each have exactly ONE authoritative field,
always at position 0: a length one shorter than full can ONLY mean "the one authoritative field,
always known to be first, is missing" -- there is no second authoritative field whose OWN omission
could produce the identical length via a different position. Arity alone resolves the single-
authoritative-field case completely; it cannot resolve the two-authoritative-fields-on-opposite-
ends case, because two DIFFERENT single-field omissions (shape 2 vs shape 3) collapse to the same
observable length.

**Re-audit of every other authoritative-metadata waterfall (final review's own requirement 5):**

| Dispatch | Authoritative field(s) | Transformable field(s) | Same ambiguity? |
|---|---|---|---|
| `AGENT_PRE_STEP` | `instance` (position 0 only) | `reason`, `messages` | No -- single authoritative field, arity-aware fix (PASS 9) is complete and correct. |
| `AGENT_PREPARE_NEXT_TURN` | `instance` (position 0 only) | `message`, `tool_results`, `context`, `new_messages` | No -- same as above. |
| `AGENT_TRANSFORM_CONTEXT` | `instance` (0), `signal` (2) | `messages` (1, sandwiched between them) | **Yes -- this is the defect being remediated.** |
| `TOOLS_POST_EXECUTE` (`_finalize`) | `signal` (position 1, LAST) | `result` (position 0, ALWAYS first) | No -- single authoritative field, always trailing, transformable field always at a fixed leading position regardless of length; length 1 unambiguously means "signal omitted," length 2 unambiguously means "both given." No sandwiching. |
| `TOOLS_PRE_EXECUTE` | `signal` (position 3, LAST) | `call`, `definition`, `arguments` (positions 0-2) | No -- single authoritative field, always trailing; the existing `(*current[:3], signal)` formula is unambiguous for the one supported shorthand (signal omitted, all three transformable fields present) for the same reason as above. (A listener omitting one of ITS OWN three transformable fields too is not a documented convenience for this event and is out of this convergence's scope -- it is a pre-existing arity-robustness gap, not the multi-authoritative-slot ambiguity this convergence addresses.) |

**Conclusion:** `AGENT_TRANSFORM_CONTEXT` is the ONLY current waterfall dispatch with two
authoritative fields that sandwich a transformable field between them. No other dispatch needs a
grammar change under this convergence.

## Proposed design

**Core rule:** a partial (non-empty, non-full-length) delegation to `AGENT_TRANSFORM_CONTEXT` is
legal if and only if its length equals exactly the COUNT of transformable fields (here, exactly 1),
and such a delegation is interpreted as supplying ONLY the transformable fields, in their fixed
relative order -- `messages`, and nothing else. An authoritative field can NEVER be supplied
through a partial delegation, by construction: there is no length at which `normalize_step`
attempts to read a listener-supplied value out of an authoritative position. This directly
generalizes the rule PASS 9 already established for the single-authoritative events
(`AGENT_PRE_STEP`/`AGENT_PREPARE_NEXT_TURN`: "the only legal partial length is exactly the
transformable-field count") to the two-authoritative-field case, rather than inventing a new
principle.

Legal lengths for `AGENT_TRANSFORM_CONTEXT` are therefore exactly `{0, 1, 3}`:

- **0** (`next_()`): true no-op forward, already handled structurally by `EventBus.waterfall`
  itself before `normalize_step` is even meaningfully exercised.
- **1** (`next_(new_messages)`): the SOLE legal partial form. Both `instance` and `signal` are
  restored to their original values; `current[0]` becomes the new `messages`. This is a STRICT
  generalization of the original convenience ("no need to re-supply `signal`") to "no need to
  re-supply EITHER authoritative field" -- a listener that only cares about transforming `messages`
  states exactly that and nothing else.
- **3** (`next_(a, b, c)`): full explicit form, unchanged from today -- `current[1]` is `messages`;
  positions 0 and 2 are unconditionally forced back to original regardless of content.
- **Any other length (in practice, only 2)**: rejected DIRECTLY at this authority boundary --
  `normalize_step` itself raises, BEFORE the malformed tuple is ever forwarded to `step(index + 1,
  ...)` (revised under `C18-1`; revision 1's own "return `current` unchanged and rely on the next
  listener's own fixed arity" was rejected by the challenge review precisely because
  `EventBus.waterfall` permits arbitrary registered callables -- a variadic listener, one with
  compatible defaults, or one that accepts the malformed shape and short-circuits could silently
  ABSORB a 2-length tuple instead of erroring, making the "refusal" depend on downstream listener
  implementation details rather than being true by construction). Raising inside `normalize_step`
  closes that gap structurally: the raise happens synchronously inside `next_`'s own body, before
  `step` (and therefore any downstream listener, however permissive its own signature) is ever
  reached -- no listener registered after the offending one can ever observe the malformed tuple,
  regardless of its own arity or short-circuit behavior.

```python
def _restore_signal(current: tuple[object, ...]) -> tuple[object, ...]:
    if len(current) == 1:
        return (original_instance, current[0], original_signal)
    if len(current) == 3:
        return (original_instance, current[1], original_signal)
    raise WaterfallError(
        f"AGENT_TRANSFORM_CONTEXT: ambiguous delegation of length {len(current)} -- a partial "
        "replacement must supply exactly the transformable field (`messages` alone) or the full "
        "payload; a two-element replacement cannot be disambiguated between an omitted leading "
        "Agent and an omitted trailing signal"
    )
```

`WaterfallError` (`runtime/errors.py`, already certified -- "A waterfall listener misused its
`next` continuation") is the exact, already-established error type for this class of misuse; no
new exception type is introduced. Because `_transform_context` (and therefore this `normalize_step`
call) runs inside `AgentLoop._execute_run`'s own `try`/`except Exception` boundary (`L08-R002`,
unchanged, already certified), this `WaterfallError` is caught there and routed to
`_settle_run_failure` exactly like any other run-executor failure -- `prompt()`/`continue_()`
itself completes normally, with a synthesized terminal `error` assistant message (`stop_reason
is StopReason.ERROR`, `error_message` carrying this exception's own text), not an escaping
exception (`C18-2`; revision 1's own acceptance witness incorrectly described a bare `TypeError`
"raising/propagating" out of the run as the expected observable outcome -- that contradicts the
already-certified Layer-08 exception boundary every OTHER run-executor failure already goes
through, and this finding does not carve out an exception to it).

### Why this is a genuine, not merely mechanical, contract question

This retires a previously-documented, previously-tested convenience (shape 2, "trailing omission
only") in favor of a strictly MORE general one (shape 4, "both authoritative fields omitted
together") that happens to make shape 2's own OLD calling pattern (`next_(instance_attempt,
messages)`, length 2) illegal going forward, alongside shape 3. This is a genuine behavioral
change to an already-agreed contract (`L09-R006`), not a bugfix confined to previously-unspecified
territory -- exactly why `§11.8` applies rather than a direct patch. The alternative that preserves
BOTH shape 2 and shape 3 as independently valid, correctly-interpreted delegations would require
disambiguating two structurally identical length-2 tuples by some means OTHER than length -- e.g.
inspecting whether a given position's value is a `RunSignal` instance. I considered and REJECT that
alternative: it is exactly the "type/position guessing" the final review's own requirement 3
prohibits (a `RunSignal` subclass, a mock in a test, or a future refactor of what `signal` even IS
could silently break the heuristic in a way arity-based rejection cannot), it cannot be specified
language-neutrally without effectively re-deriving a discriminated union anyway (at which point
Rust would need an actual typed representation, not a positional tuple, while Python would need
runtime `isinstance` checks against a type this module does not otherwise need to import), and it
would leave the SAME ambiguity dormant for any future third authoritative field this event might
gain. A construction-based refusal -- an explicit, immediate `WaterfallError` raised at the
authority boundary itself, per `C18-1` -- closes the defect CLASS, not just this one witness, and
does so as a represented Layer-08 run failure rather than an escaping exception, per `C18-2` -- the
same standard already applied to the `L09-R012`/`R013`/`R014` `_Reservation` redesign.

A more conservative alternative, also considered: retire the shorthand ENTIRELY (`{0, 3}` only, no
length-1 form at all), requiring a listener to always restate all three positions (even though 0
and 2 are ignored) to change `messages`. This is strictly safer against any FUTURE authoritative-
field addition (no partial-length convention to reconsider each time) but discards more of the
existing ergonomic motivation for `normalize_step`'s own design than necessary -- a listener
wanting only to transform `messages` would have to know or forward its own received `instance`/
`signal` arguments verbatim, adding boilerplate `normalize_step` exists specifically to avoid. I
propose the `{0, 1, 3}` design above as the better balance, but note this conservative alternative
explicitly in case the independent review weighs the tradeoff differently.

## Required acceptance witnesses

Two levels, per `C18-2`: a DIRECT unit-level witness against `_restore_signal`/the waterfall
dispatch itself may assert the immediate typed exception; the real-Agent-loop witness must assert
the represented Layer-08 run-failure outcome, never a bare escaping exception.

1. **Direct, leading-omission shape, immediate rejection with proof of non-forwarding
   (`C18-1`)**: register two listeners on `AGENT_TRANSFORM_CONTEXT` directly against the real
   `EventBus`/`AgentLoop` machinery (not a bare call to `_restore_signal` in isolation, so the
   waterfall's own `step`/`next_` wiring is genuinely exercised) -- listener A delegates via
   `next_(new_messages, some_signal)` (length 2, leading-omission shape); listener B is
   deliberately VARIADIC/short-circuit-capable (e.g. `async def listener_b(*args): sneaky_calls.
   append(args); return "whatever"`), registered AFTER A, specifically chosen because its own
   permissive signature would happily absorb a malformed 2-tuple if the malformed tuple were ever
   forwarded to it. Assert `WaterfallError` is raised (propagating out of the `waterfall()` call
   itself, at this direct level) AND assert `sneaky_calls == []` -- listener B is never invoked at
   all, proving the rejection happens at the authority boundary itself, not merely because a FIXED
   next listener happened to have an incompatible arity.
2. **Direct, trailing-omission shape, same treatment**: the same structure as (1), but listener A
   delegates via `next_(some_instance_attempt, new_messages)` (length 2, the OLD convenience
   shape) -- assert the SAME `WaterfallError` and the SAME "listener B never invoked" proof. This
   demonstrates shape 2 and shape 3 (both length-2 readings) are refused IDENTICALLY, not
   selectively.
3. **Real-loop, leading-omission shape, represented failure (`C18-2`)**: through an actual
   `loop.prompt(...)` call, a listener on `AGENT_TRANSFORM_CONTEXT` delegates via
   `next_(new_messages, some_signal)`. Assert `await loop.prompt(...)` COMPLETES NORMALLY (no
   exception escapes it); assert the settled turn's own assistant message has `stop_reason is
   StopReason.ERROR` and `error_message` reflecting the `WaterfallError`'s own text (matching the
   established pattern `test_an_unrelated_exception_without_abort_is_still_settled_as_error`
   already uses); assert the mock adapter recorded NO request for that turn (or, if a prior turn's
   request already exists in `adapter.requests`, that no NEW request was appended) -- the malformed
   delegation must never reach the provider at all; assert the Agent's own `status` returns to
   `AgentStatus.IDLE` afterward, per the existing, unmodified `_run_wrapped`/`_execute_run`
   contract.
4. **Real-loop, trailing-omission shape, same treatment**: the same structure as (3), with the
   trailing-omission delegation shape.
5. **The new sole legal shorthand, positive case**: a listener delegates via
   `next_(new_messages)` (length 1) -- assert the NEXT listener observes the ORIGINAL `instance`
   and the ORIGINAL `signal` (not `None`, not a forgery), and observes the TRANSFORMED `messages`;
   assert the real provider request's own `Request.messages` reflects the transformed value.
6. **The already-passing full-length redirect witness** (`test_a_transform_listener_cannot_
   redirect_a_later_listener_to_a_replacement_signal`): re-run unchanged against the fixed
   implementation to confirm no regression -- length-3 handling is untouched by this design.
7. **A length-1 delegation with NO prior listener** (a single listener, `next_(new_messages)`,
   nothing upstream) -- confirms the shorthand works even as the very first step, not only when
   chained after a prior full-length or no-op step.

**Revert-and-confirm accounting, corrected (`C18-3`):** witnesses 1, 2, 3, 4, 5, and 7 are all
genuine RED witnesses against the current PASS-9 candidate:

- 1 and 3 (leading-omission shape) fail today by NOT raising at all -- `_restore_signal` silently
  treats the malformed tuple as `(instance_attempt, messages)` and corrupts the payload instead;
- 2 and 4 (trailing-omission shape) ALSO fail today, but for the OPPOSITE reason: PASS 9's own
  `_restore_signal` currently ACCEPTS this exact shape successfully (it is the shape the
  already-shipped code was designed to support), so asserting it is now REFUSED is a genuine RED
  test against PASS 9's own actual behavior, not a pre-passing regression guard -- revision 1's own
  claim that this witness "already passes today" was wrong;
- 5 and 7 (length-1 shorthand) fail today with `IndexError`, since `current[1]` assumes at least 2
  elements.

Only witness 6 (the unchanged full-length redirect test) is an already-GREEN regression guard, not
a RED witness -- it must remain passing throughout, unmodified, confirming length-3 handling is
untouched by this design.

All RED witnesses (1, 2, 3, 4, 5, 7) must PASS once the arity-aware, explicitly-rejecting
`_restore_signal` above is restored; witness 6 must remain passing throughout.

## Normative deltas required

- `minion-agent-docs/spec/agent.md`: `AGENT_TRANSFORM_CONTEXT`'s own section corrected to state the
  full delegation grammar precisely -- legal partial lengths are `{0, 1}` (in addition to the full
  length 3), a length-1 delegation supplies ONLY `messages`, and any other partial length is an
  explicitly-refused, represented failure, not a silently-guessed interpretation. The existing "A
  listener no longer needs to re-supply `signal` when delegating with a replacement" sentence is
  corrected to "a listener no longer needs to re-supply EITHER authoritative field," since the
  extension now covers `instance` too, not `signal` alone.
- `minion-agent-docs/assurance/layers/09-active-abort-python.md`: a new PASS section recording this
  convergence's own implementation once agreed.
- `minion-agent/pi-parity-manifest.yaml`, `AG-007`: a paragraph recording `L09-R018`'s own finding,
  root cause, and the `{0, 1, 3}` grammar decision -- `AG-023`'s own row (the `transformContext`
  requirement/traceability entry the final review scored `FAIL` against) needs the corresponding
  correction once implemented.

## Rust implementability

The `{0, 1, 3}`-legal-arity, refuse-everything-else rule is directly and IDIOMATICALLY expressible
in Rust without any positional-tuple ambiguity at all: Rust's own type system does not offer a
bare variadic `next(*args)` call in the first place, so a Rust port of this waterfall would
naturally express "the transformable fields only" as a distinct, explicitly-typed variant (e.g. an
enum `TransformDelegation { Unchanged, Messages(Vec<Message>), Full { instance, messages, signal }
}`, or simply two distinct typed `next` overloads/methods) rather than a length-inspected tuple --
the ambiguity this convergence resolves is a Python-positional-tuple-specific hazard that a typed
Rust design would not reproduce even without this fix, PROVIDED Rust does not attempt to mirror
Python's own bare-tuple delegation mechanism verbatim. This convergence's own normative rule (legal
partial delegations correspond 1:1 with "exactly the transformable fields, nothing else") is the
language-neutral invariant Rust must satisfy; the enum-or-typed-overload shape is one faithful,
idiomatic realization of it, not a divergence.

## Out of scope / deferred

- `TOOLS_PRE_EXECUTE`'s own pre-existing (not newly discovered) gap -- a listener omitting one of
  its OWN three transformable fields (`call`/`definition`/`arguments`) while supplying the others
  is not correctly reshaped by the current `(*current[:3], signal)` formula -- is NOT the
  multi-authoritative-slot ambiguity this convergence addresses (that dispatch has only one
  authoritative field, always trailing) and is left untouched. If it warrants a fix, it is a
  separate, narrower finding.
- No change to `AGENT_PRE_STEP`/`AGENT_PREPARE_NEXT_TURN`'s own already-agreed, already-closed
  (`L09-R015`) arity-aware design -- confirmed, via the re-audit above, to have no version of this
  ambiguity.
- Forced task cancellation, provider transport abort (`PROV-004`), tool batch/preflight changes,
  Layer 10, Rust implementation -- unchanged scope boundary from every prior Layer-09 pass.

```text
CONVERGENCE CONTRACT
    PROPOSED -- AWAITING INDEPENDENT AGREEMENT (revision 2)

OPEN FINDING
    L09-R018

CORE RULE RETAINED (accepted in revision 1, unchanged)
    legal external delegation shapes {0, 1, 3}
    length 1 means messages only
    full length restores authoritative Agent and signal

CHALLENGE FINDINGS ADDRESSED
    C18-1  reject at the authority boundary: normalize_step now raises WaterfallError directly,
           before the malformed tuple is ever forwarded to the next listener -- proven by a
           variadic/short-circuit-capable downstream listener that is never invoked (witnesses
           1-2), not merely relying on a fixed next listener's own incompatible arity
    C18-2  represented failure, not bare propagation: the direct unit-level witnesses (1-2) may
           assert the immediate WaterfallError; the real-Agent-loop witnesses (3-4) now assert
           the represented Layer-08 run-failure outcome (prompt() completes normally, terminal
           stop_reason is StopReason.ERROR, no provider request sent, status returns IDLE) --
           see the revised "Proposed design" and witnesses above
    C18-3  RED/regression accounting corrected: witnesses 1, 2, 3, 4, 5, and 7 are all genuine
           RED against PASS 9 (2 and 4 fail because PASS 9 currently ACCEPTS that shape, not
           because it already rejects it); only witness 6 (unchanged full-length redirect) is
           an already-green regression guard

ACCEPTANCE WITNESSES
    tests/agent_loop/test_active_abort.py (7 new/changed AGENT_TRANSFORM_CONTEXT witnesses --
      see "Required acceptance witnesses" above)
    -- none yet written; this is a contract/evidence checkpoint, not an implementation pass

NORMATIVE DELTAS
    minion-agent-docs/spec/agent.md (AGENT_TRANSFORM_CONTEXT delegation grammar corrected to the
      {0, 1, 3}-legal-arity rule, explicit rejection at the authority boundary via WaterfallError,
      and represented Layer-08 failure settlement for the rejected case; "no need to re-supply
      signal" corrected to "no need to re-supply either authoritative field")
    minion-agent-docs/assurance/layers/09-active-abort-python.md (new PASS section once
      implemented)
    minion-agent/pi-parity-manifest.yaml, AG-007 (L09-R018 paragraph) and AG-023 (FAIL corrected
      once implemented)
```
