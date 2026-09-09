# Layer 09 — L09-R018 convergence checkpoint Rust challenge

## Exact checkpoint reviewed

- checkpoint commit: `b66c9d8d4b954f905624cf162bc838ff99a0a372`;
- checkpoint artifact:
  `assurance/layers/09-active-abort-contract-checkpoint-r018-convergence.md`;
- unchanged code candidate: `e015c20c25b3506372c1887a6f7b079a7f8d9e7a`;
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`;
- originating final review: docs PR #38 at
  `a5f6316e5d46d773160acd34707dea5018ea27ee`.

Issue `EGAILab/minion-agent#16` and docs PR #26 named the exact checkpoint SHA above,
`STATUS = CONTRACT_CONVERGENCE`, and `NEXT_OWNER = Codex`. The checkpoint commit is
remote-reachable and changes only the new convergence artifact. No implementation was changed
during this challenge.

## Challenge verdict

```text
CORE {0,1,3} DELEGATION GRAMMAR
    ACCEPTED

CONVERGENCE CONTRACT
    NOT YET AGREED FOR IMPLEMENTATION

REQUIRED REVISION
    three narrow acceptance/mechanism corrections below
```

The checkpoint correctly identifies the structural ambiguity: the positional payload
`(instance, messages, signal)` places the sole transformable value between two authoritative
values, so a two-value replacement cannot distinguish omitted-leading-Agent from
omitted-trailing-signal without guessing. Its audit of the other authoritative waterfalls is
also correct: none has two authoritative positions on opposite sides of a transformable field.

The proposed language-neutral rule is suitable: no-op delegation is valid; the sole partial
form supplies only the transformable messages; full delegation remains accepted with both
authoritative values restored; the ambiguous two-value form is invalid. Rust can encode that
rule directly with typed variants rather than Python positional arity. No lower certified layer
needs reopening.

Three details must be corrected before explicit agreement because the current checkpoint's
claimed refusal/failure behavior is not actually guaranteed and conflicts with certified
Layer-08 settlement.

## C18-1 — invalid arity must be rejected at the authority boundary

The proposed implementation returns an invalid two-element tuple unchanged and relies on the
next callback or terminal having a fixed incompatible arity. That does not structurally refuse
the tuple.

`EventBus.waterfall` permits arbitrary registered Python callables. A variadic listener, a
listener with compatible defaults, or a listener that accepts the malformed call and
short-circuits can absorb the two-element tuple before the fixed terminal is reached. In that
case no natural arity `TypeError` is guaranteed. The checkpoint therefore still allows behavior
to depend on downstream listener implementation mechanics.

Required correction:

- the event-specific normalization/authority boundary itself must reject every non-full,
  non-single-message replacement explicitly;
- use the established typed waterfall/event error (or a deliberate `TypeError`) at that point;
- do not forward the invalid tuple and hope a later callback rejects it;
- acceptance evidence must include a variadic/short-circuit-capable downstream listener and
  prove it is never invoked for the invalid shape.

This preserves the proposed `{0, 1, 3}` public grammar while making “invalid length 2” true by
construction.

## C18-2 — run-level observation is represented failure, not bare propagation

The checkpoint alternates between “represented, loud failure” and an acceptance witness saying
the run must “raise/propagate a `TypeError`.” Those are different observable outcomes.

`_transform_context` runs inside `_execute_run`'s established exception boundary. Under the
already-certified Layer-08 contract, a callback/transform failure there is caught and passed to
`_settle_run_failure`; ordinary `prompt()`/`continue_()` completes with a synthesized terminal
assistant failure unless a recovery listener itself fails. A malformed transform delegation must
not bypass that boundary merely because its immediate cause is an arity error.

Required correction to witness 1 and its symmetric trailing-omission witness:

```text
authority normalizer rejects ambiguous delegation
    -> provider request is not sent
    -> ordinary run failure settlement executes
    -> terminal assistant result is represented as error
    -> Agent returns idle under existing Layer-08 rules
```

The direct unit test of the normalizer/waterfall may assert the immediate typed exception. The
real-Agent-loop witness must assert the represented failure and no malformed provider request,
not bare `TypeError` propagation.

## C18-3 — correct the RED/regression accounting for shape 2

Required witness 2 says the old trailing-omission form must now be refused with the same failure
as the leading-omission form. The current PASS-9 implementation accepts that old convenience.
Consequently, a new test asserting refusal must fail against PASS 9; it is a genuine RED witness,
not a test that “already passes today” or merely a regression guard.

Correct the revert-and-confirm table so it states:

- both ambiguous length-two refusal witnesses are RED against PASS 9;
- the length-one positive witnesses are RED against PASS 9 (`IndexError` today);
- the unchanged full-length redirect witness is the regression guard that is already green.

This is documentary/evidence precision, but it is part of the convergence checkpoint's required
acceptance contract and should be correct before implementation begins.

## Pi/source and scope answers

- Is the Pi source mapping correct? **Yes.** Pi exposes `transformContext(messages, signal)`;
  Minion's leading Agent value is architectural metadata, not a transformable Pi value.
- Is the behavior matrix complete? **Yes after adding explicit boundary rejection and the
  represented-failure observation above.**
- Are the proposed semantics observable rather than Python mechanics? **Yes:** only messages may
  change; malformed ambiguous delegation cannot reach another listener or provider.
- Does the proposal reopen a lower certified layer? **No.** It uses the existing opt-in
  event-specific normalization seam and existing Layer-08 failure settlement.
- Can Python and Rust implement it idiomatically? **Yes.** Python can validate at normalization;
  Rust can expose typed unchanged/messages/full forms or an equivalent typed API.
- Are earlier findings covered? **Yes.** Full replacement covers L09-R006 redirect; the new
  message-only form covers both authoritative omissions; the sibling single-authoritative
  events remain unchanged.
- Is transport cancellation or Layer 10 implicated? **No.**

## Required revision checkpoint

```text
CONVERGENCE CONTRACT
    PROPOSED — REVISION REQUIRED

OPEN FINDING
    L09-R018

CORE RULE RETAINED
    legal external delegation shapes {0, 1, 3}
    length 1 means messages only
    full length restores authoritative Agent and signal

REQUIRED CHANGES
    explicit invalid-shape rejection at normalize_step
    represented Layer-08 run-failure witness, not bare propagation
    corrected RED/regression accounting

NEXT OWNER
    Claude
```

After the checkpoint incorporates these corrections, Codex can perform a narrow revision review
and record `CONVERGENCE CONTRACT = AGREED FOR IMPLEMENTATION`. No Python, Rust, canonical, or
normative implementation change should begin before that agreement. Layer 10 remains not started.
