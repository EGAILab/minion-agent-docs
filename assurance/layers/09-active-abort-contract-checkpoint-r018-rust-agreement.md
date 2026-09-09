# Layer 09 — L09-R018 convergence checkpoint Rust agreement

## Exact checkpoint reviewed

- checkpoint revision 2: docs PR #26 at
  `f774a22cf22505d89241d936e2dcf6de0cb67d8c`;
- unchanged code baseline: code PR #17 at
  `e015c20c25b3506372c1887a6f7b079a7f8d9e7a`;
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`;
- originating final-review rejection: docs PR #38 at
  `a5f6316e5d46d773160acd34707dea5018ea27ee`;
- revision-1 Rust challenge: docs PR #39 at
  `a6c05675d85b76a01ce6ba1b6d0a0abdf1d37f80`.

The exact revision-2 checkpoint was fetched from GitHub and matched coordination issue #16.
Docs PR #26 remained open, ready, and unmerged. Revision 2 changes only the convergence artifact;
no Python, Rust, canonical, manifest, or normative specification implementation was changed.

## Verdict

```text
CONVERGENCE CONTRACT
    AGREED FOR IMPLEMENTATION

OPEN FINDING
    L09-R018

AGREEMENT SCOPE
    exact checkpoint f774a22cf22505d89241d936e2dcf6de0cb67d8c
```

This is the workflow §11.8.5 checkpoint agreement. It is not final Layer-09 approval and does not
authorize Rust Layer-09 implementation. It authorizes the shared/Python owner to implement only
the agreed L09-R018 remediation and evidence.

## Independent challenge closure

### C18-1 — reject at the authority boundary

**CLOSED.** Revision 2 no longer forwards an invalid two-element payload and relies on a later
callable's arity. The event-specific normalizer itself raises the existing `WaterfallError` for
every non-full, non-message-only replacement. Rejection therefore happens before any downstream
listener, including a variadic or short-circuit-capable listener, can observe or absorb the
malformed tuple.

The required negative witness explicitly registers such a permissive downstream listener and
asserts it is never invoked. This closes the implementation-mechanics dependency identified by
the revision-1 challenge.

### C18-2 — represented Layer-08 failure

**CLOSED.** Revision 2 distinguishes direct dispatch observation from real-run observation:

- a direct `_transform_context`/waterfall witness observes immediate `WaterfallError`;
- a real `AgentLoop.prompt()` witness observes the already-certified Layer-08 catch boundary:
  the provider is not called, the exception is represented as a terminal assistant error, the
  prompt completes normally, and the Agent settles idle.

No special escape path is introduced for this validation error.

### C18-3 — RED/regression accounting

**CLOSED.** Revision 2 correctly identifies both newly-invalid length-two forms as RED against
PASS 9 because PASS 9 accepts one and silently misinterprets the other. Both message-only
length-one positive forms are also RED against PASS 9. The unchanged full-length redirect test is
the sole already-green regression guard.

## Agreed observable contract

`AGENT_TRANSFORM_CONTEXT` has one transformable value (`messages`) and two authoritative values
(`instance`, `signal`). Its delegation grammar is:

| External delegation | Meaning | Boundary result |
|---|---|---|
| `next_()` | no change | current full payload continues |
| `next_(messages)` | replace only messages | original Agent and original signal restored |
| `next_(instance, messages, signal)` | full explicit form | messages taken from the middle slot; original Agent and signal restored |
| any other arity, notably two | ambiguous/invalid | immediate `WaterfallError` before downstream delivery |

Only messages can change. Neither authoritative value can be redirected, dropped, shifted into
the messages position, or inferred through type guessing. The real provider sees only the valid
message projection. An invalid delegation follows ordinary Layer-08 run-failure settlement.

This rule is language-neutral. Python may enforce the event grammar in `normalize_step`; Rust may
use typed delegation variants or an equivalent typed API and need not reproduce variadic tuple
mechanics.

## Acceptance evidence agreed

The implementation pass must provide all seven checkpoint witnesses:

1. direct leading-omission rejection, with a variadic downstream listener never invoked;
2. direct trailing-omission rejection with the same non-forwarding proof;
3. real-loop leading-omission represented failure and no provider request;
4. real-loop trailing-omission represented failure and no provider request;
5. chained message-only delegation preserving original Agent/signal and replacing messages;
6. unchanged full-length redirect regression witness;
7. first-listener message-only delegation reaching the provider correctly.

Revert-and-confirm must show witnesses 1–5 and 7 fail against the PASS-9 implementation and pass
after remediation; witness 6 must remain green throughout.

## Required synchronized deltas

The implementation owner may now make the checkpoint's narrow changes:

- Python `_transform_context` normalization and the agreed tests;
- `spec/agent.md` delegation grammar and represented-failure statement;
- `pi-parity-manifest.yaml` AG-007/AG-023 evidence and current rule;
- Layer-09 Python assurance history.

No other waterfall behavior, lower-layer contract, Rust implementation, provider transport
cancellation, or Layer-10 behavior is included.

## Agreement checks

- Pi mapping correct: **YES** — Pi's semantic values are messages and signal; Minion's Agent is
  authoritative architectural metadata.
- Matrix distinguishes realistic wrong implementations: **YES**.
- Invalid shape rejected without downstream-callable assumptions: **YES**.
- Existing Layer-08 failure settlement preserved: **YES**.
- Lower certified layer reopened: **NO**.
- Python and Rust can implement idiomatically: **YES**.
- Previous L09-R006 redirect protection retained: **YES**.
- Sibling L09-R015 events changed: **NO**.
- Layer 10 started: **NO**.

## Next action

```text
CONVERGENCE CONTRACT
    AGREED FOR IMPLEMENTATION

NEXT OWNER
    Claude

NEXT ACTION
    Implement the exact L09-R018 revision-2 matrix, tests, and synchronized evidence;
    push exact candidate SHAs; request targeted finding closure under §11.8.7.
```

After targeted provisional closure, workflow §11.8.8 still requires one final complete exact-SHA
Layer-09 review before merge or Rust implementation.
