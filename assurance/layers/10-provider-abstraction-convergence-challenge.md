# Layer 10 — convergence checkpoint challenge review

**Checkpoint reviewed:** docs PR #45 at
`405798a93dfe058f212072256b354985091c07af`

**Pinned Pi:** `b7bb00b936dbe21b8e160b3e89efdec361846699`

**Result:** `CHANGES REQUIRED`; the checkpoint is not yet `AGREED FOR IMPLEMENTATION`.

This is a workflow §11.8.4 challenge review, not a full contract re-review and not an
implementation pass. No shared candidate or Rust production file was modified.

## Accepted parts

The checkpoint correctly characterizes and proposes fixes for the findings already witnessed:

- narrow `AI-028` to the adopted `stream`/never-raises surface;
- move required-but-unimplemented `streamSimple` parity to a separate deferred row;
- relabel `AI-029` as `intentional divergence` because Minion's eager full-identity miss differs
  observably from Pi's in-band missing-API settlement;
- retain coherent Minion-only registration/withdrawal/introspection under `AI-030`;
- enforce `reject_message` in both directions with JSON Schema `if`/`then`/`else`;
- replace request-value equality with before/after request-log count observation;
- add the exact register-A, stream-A, replace-with-B, resolve-B witness;
- keep `L10-R003` outside this checkpoint as a disclosed Rust implementation obligation.

Pinned Pi independently confirms that `ProviderStreams.streamSimple` is a required, public
callable operation, not merely an internal helper, and that its implementations translate
`SimpleStreamOptions` before delegating to the same module's `stream`.

## Challenge C10-C001 — deferred `streamSimple` must retain the observable callable obligation

The proposed `AI-031` direction is correct, but its acceptance language must say that Layer 11
owes an externally invocable Minion equivalent of Pi's required:

```text
streamSimple(model, context, SimpleStreamOptions) -> AssistantMessageEventStream
```

Language-specific shape may differ, and the translation is per provider, but the parity
obligation is the callable behavior—not merely an internal "adapter-construction concern." A
deferred row that promises only internal option translation could later be marked complete while
Minion still exposes no equivalent operation. Record Layer 11 as the concrete owner and make this
observable closure criterion explicit; do not leave only a `PROV-###` placeholder.

## Challenge C10-C002 — registration-handle grammar remains ambiguous

`AI-030` normatively says every `register()` call returns its own withdrawal handle. The canonical
grammar addresses `withdraw` by adapter fixture id instead of registration/handle identity. It
therefore has no defined answer when the same adapter fixture is registered more than once. The
current Python runner stores every handle under that adapter id and a single `withdraw` invokes
all of them; an independent Rust runner could reasonably invoke only the latest handle. Both
interpretations fit the current schema.

Adjacent reference behavior is also undefined:

- duplicate adapter fixture ids are schema-valid and Python silently keeps the last one;
- `register` of an undeclared id raises `KeyError`;
- `withdraw` of an undeclared or never-registered id silently does nothing.

Choose and specify one coherent grammar before implementation. Two acceptable designs are:

1. make each registration action produce a unique handle id and have `withdraw` name that handle;
   or
2. constrain the finite DSL so adapter ids are unique, each fixture may be registered at most
   once, and every register/withdraw reference is declared and legal in sequence.

Convert duplicate-id, repeated-registration/ambiguous-withdrawal, and unknown-reference cases into
negative validation witnesses. These checks may be schema-shaped or an explicit shared semantic
fixture validator where JSON Schema cannot express cross-step uniqueness.

## Challenge C10-C003 — observation identifiers need one shared namespace and integrity rules

`queries[].id` and `steps[].stream.as` both write the same `observations` mapping, but neither the
schema nor runner requires uniqueness across that combined namespace. A later observation can
silently overwrite an earlier one, and different runners may reject, first-win, or last-win.
Likewise an `expect` key may name no declared observation, while executed observations may be left
unasserted without an explicit setup-only rule.

Define at least:

- all query ids and stream `as` ids are unique across one scenario;
- every expectation id names exactly one declared observation;
- whether unasserted observations are legal setup-only actions (if they are, state that
  explicitly; the proposed A-stream setup witness is the immediate example).

Add collision and dangling-expectation negative witnesses. This is the same canonical grammar
surface as `L10-R004`, not unrelated hardening.

## Challenge C10-C004 — count-delta observation must assert a sole owner

The proposed count snapshot is the correct observation mechanism, but using `next(...)` still
silently selects the first match if multiple request logs grow. Collect the changed adapter ids
and require exactly one. Zero or multiple deltas must fail the fixture explicitly rather than be
normalized into a plausible owner. This keeps the runner observational and prevents instrumentation
failure from masquerading as production resolution behavior.

## Required revision-2 checkpoint

Retain the four existing witnesses and add:

```text
streamSimple defer
    explicit public-callable Layer-11 closure criterion

adapter fixtures/handles
    duplicate fixture id rejected
    ambiguous repeated registration/withdrawal rejected or represented by explicit handle ids
    unknown register/withdraw references rejected consistently

observation namespace
    duplicate/colliding query-id and stream-as rejected
    dangling expectation rejected
    setup-only unasserted observation policy stated

owner observation
    exactly one request-count delta required
```

The revised checkpoint should remain mechanism-neutral where possible and state which constraints
belong to JSON Schema versus a shared semantic fixture validator. Both Python and Rust can
implement either accepted registration-handle design idiomatically. No lower certified layer needs
to reopen, and the root canonical DSL issue exists equally for both languages.

```text
CONVERGENCE CONTRACT
    CHANGES REQUIRED

OPEN FINDINGS
    L10-R001
    L10-R002
    L10-R004

NEXT OWNER
    Claude

NEXT ACTION
    Publish revision 2 addressing C10-C001..C004, then return for independent agreement.
```

Do not implement the checkpoint yet. Do not implement Rust Layer 10 and do not start Layer 11.
