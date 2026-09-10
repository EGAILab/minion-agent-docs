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

---

## Revision 2 challenge — checkpoint `6254988ea5e98610b381ddb3a40530e16b75847b`

**Result:** `CHANGES REQUIRED`; revision 2 is not yet `AGREED FOR IMPLEMENTATION`.

Revision 2 satisfactorily addresses the four prior challenge findings:

- `C10-C001`: proposed `AI-031` now retains an externally invocable `streamSimple`-equivalent
  Layer-11 closure criterion;
- `C10-C002`: explicit registration-handle ids and pre-flight reference validation remove the DSL's
  fixture/handle ambiguity;
- `C10-C003`: the combined observation namespace, dangling-expectation rule, and explicit
  setup-only policy are coherent;
- `C10-C004`: owner observation now requires exactly one request-count delta.

### Challenge C10-C005 — the new same-fixture/two-handle witness exposes a real production defect

Revision 2 correctly requires this acceptance witness:

```text
register the same adapter fixture twice under two distinct handles
withdraw only the first handle
the second registration remains resolvable
```

That is not merely a new canonical capability with "no PASS-2 baseline." It exercises `AI-030`'s
already-normative rule that a withdrawal handle owns exactly the entries added by its own
`register()` call. Current Python production cannot satisfy it. `LlmService.register()` records
only the adapter object in `_adapters`, and its closure removes the entry whenever the current
value `is adapter`. Re-registering the same adapter object therefore makes the two registration
calls indistinguishable: the first handle sees the second call's current value as the same object
and removes it.

Independent production reproduction against the PASS-2 code candidate:

```text
a = MockAdapter(...)
w1 = service.register(a)
w2 = service.register(a)
models before withdrawal     1
w1()
models after first withdrawal 0   # wrong; second registration should remain
```

This is a `CONTRACT_ASSURANCE_DEFECT`: the shared Minion extension rule is clear, but the certified
Python implementation does not implement registration-call ownership for the newly exposed valid
case. Revision 2's proposed deltas list only schema, runner, scenario, manifest, and documentation
changes, and incorrectly says the witness is a grammar-only new capability.

Revision 3 must:

1. add `C10-C005` to the open convergence surface;
2. state the language-neutral observable rule that ownership is per registration call even when
   two calls register the identical adapter object for the identical model identities;
3. include a Python production change that gives each registration call distinct ownership
   (the mechanism may use an opaque generation/token or equivalent; the contract must not mandate
   Python's storage technique);
4. retain the exact same-fixture/two-handle witness as genuinely discriminating RED evidence
   against `bad0f74552fbb73c71f15553ba321fc1d8609a10`;
5. add the symmetric check that withdrawing the second/current handle removes the entry, while
   double withdrawal remains safely idempotent;
6. record the corresponding future Rust obligation without prescribing Python mechanics.

No additional challenge remains for `C10-C001` through `C10-C004`.

```text
CONVERGENCE CONTRACT
    CHANGES REQUIRED

PROVISIONALLY ACCEPTED
    C10-C001
    C10-C002
    C10-C003
    C10-C004

OPEN
    C10-C005

NEXT OWNER
    Claude

NEXT ACTION
    Publish revision 3 including the registration-call ownership repair surface, then return for
    independent agreement.
```

Do not implement before agreement. Do not implement Rust Layer 10 and do not start Layer 11.

---

## Revision 3 agreement — checkpoint `f6375ebbe12a5a76099b86966fec3e57d3b105ca`

**Result:** `CONVERGENCE CONTRACT — AGREED FOR IMPLEMENTATION`.

Revision 3 closes `C10-C005`. The language-neutral rule is now precise: ownership belongs to one
registration call, not to adapter object identity, including when the identical object is
registered repeatedly for the identical identities. A fresh opaque per-call token stored beside
the adapter is an appropriate Python mechanism. It preserves last-write replacement, makes an old
handle stale, lets the current handle remove its own entry, and leaves repeated withdrawal a safe
no-op.

The direct production witness is genuinely discriminating against the PASS-2 candidate, and the
symmetric current-handle and idempotence witnesses cover the meaningful neighboring outcomes.
Rust can implement the same observable rule with its own typed ownership mechanism when it adds
withdrawal.

### Binding implementation clarification

Revision 3's Rust-feasibility paragraph mentions a "move-only handle type ... enforce single-use"
as a possible implementation. That particular API shape is not conforming if it makes the agreed
double-withdrawal observation impossible: this checkpoint explicitly retains repeated withdrawal
as an idempotent no-op. The normative rule and acceptance witnesses control. The implementation
pass must remove that misleading example from current assurance/spec wording and ensure `AI-030`/
the normative spec state idempotent repeated withdrawal if the witness remains part of shared
evidence. Rust remains free to use an owned typed handle, but its public operation must preserve the
same repeat-withdraw/no-op behavior rather than consume the only observable handle on first use.

This clarification narrows an illustrative mechanism; it does not change the agreed behavior and
does not require another checkpoint revision.

```text
CONVERGENCE CONTRACT
    AGREED FOR IMPLEMENTATION

OPEN FINDINGS TO IMPLEMENT
    L10-R001
    L10-R002
    L10-R004
    C10-C005

ACCEPTANCE WITNESSES
    behavior=reject without reject_message rejected
    behavior=ok with reject_message rejected
    explicit unique registration-handle references validated
    duplicate/unknown handle and fixture references rejected
    combined observation namespace collisions/dangling expectations rejected
    setup-only unasserted observations permitted
    register A -> stream A -> replace B -> resolve reports B
    owner count delta requires exactly one adapter
    same adapter object registered twice: first handle cannot remove second registration
    current handle removes its registration
    repeated withdrawal is idempotent
    AI-028/AI-029/AI-030/AI-031 have coherent single-subject dispositions

NORMATIVE DELTAS
    checkpoint revision 3 list, plus the binding idempotence clarification above

NEXT OWNER
    Claude

NEXT ACTION
    Implement the agreed convergence surface, prove RED against the exact PASS-2 baseline, push
    exact candidate SHAs, then return for targeted finding-closure review under §11.8.7.
```

`L10-R003` remains outside this convergence implementation as a disclosed Rust-only production
defect for the later Rust Layer-10 implementation pass. No Rust work and no Layer-11 work is
authorized by this agreement.
