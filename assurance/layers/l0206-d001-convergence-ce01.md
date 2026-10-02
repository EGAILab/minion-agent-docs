# CE-L0206-D001-01: the mutable argument-object observer chain (K1, `minion-agent#100`)

**Episode:** `CE-L0206-D001-01`. **Status:** `CONTRACT_CONVERGENCE`, checkpoint PROPOSED FOR IMPLEMENTATION (§9).
**Author:** Claude (characterization, challenge and proposal). **Independent checkpoint reviewer:** Codex.
**Pinned Pi:** `b7bb00b936dbe21b8e160b3e89efdec361846699`, Node v22.15.1.

## 0. Entry (§11.8)

Codex CHECKPOINT3 (code `92db98f9` / docs `f49be9c4`; docs #228 comment `5945597718`):
- **`R004` OPEN, refined.** A listener that mutates the shared raw object between the event-bus emit and the live callback, or between listeners, is not re-ordered for the next observer. The witness gives `start ['b','2','1']` and `update ['b','2','1']`; Pi gives `['1','2','b']`.
- **Trigger A fired:** `R004` survived two reviews.
- **Trigger C fired:** three rejected checkpoint reviews.

`R001`–`R003` stay closed.

## 1. Root-cause surface

**Pi.** A tool-argument object is a JavaScript object: its own keys **always** enumerate in ECMAScript order, after any mutation, for any code holding it. There is no "normalization point": the order is a property of the object.

**Python.** A `dict` orders by insertion. Every earlier pass ordered at selected **points**, the four checkpoints' "boundaries". Each review then found an observer reached between two points (a hook's later assignment, a raw mutation, an inter-observer mutation). So the defect is the **mechanism**, not a missing site.

## 2. The observer chain (complete inventory)

Every place a call's arguments reach code that can observe or mutate them:

| # | Observer | How it receives the object | Can it mutate for the next observer? |
|---|---|---|---|
| O1 | the provider / constructor | builds the value | yes, before construction |
| O2 | any holder of `ToolCallBlock.arguments` after construction | the raw object | yes (the R004 original) |
| O3 | session encoding / the tool-call record | serialization | no |
| O4 | `tools/execution-start` listeners (emit; the length-stop path too) | the raw object, positional 3 | yes |
| O5 | the `on_execution_start` live callback | the raw object | yes |
| O6 | agent lifecycle listeners (`ToolExecutionStart` / `ToolExecutionUpdate`, serial) | `event.arguments` (the raw object) | yes |
| O7 | the `prepare_arguments` shim | a copy (certified nonmutation mapping) | no, not upstream |
| O8 | `tools/pre-execute` listeners (waterfall) | the validated object | yes |
| O9 | `execute` | the validated or replacement object | yes, during its own run |
| O10 | `tools/update` listeners (emit) | the raw object | yes |
| O11 | the `on_execution_update` live callback | the raw object | yes |

Dispatch modes in use: `emit` (O4, O10), `serial` (O6), `waterfall` (O8). `parallel` carries no argument object today, but it is covered for completeness.

## 3. Observable rules (proposed, normative)

- **R-K1-O1 (pipeline-owned objects keep the rule at all times).**
  - Every object in a call's arguments, and every object the validated arguments contain, is owned by the binding.
  - Any mutation of an owned object, by any observer, leaves it in ECMAScript order immediately: that observer and every later one see the rule.
  - This is Pi's semantics exactly.
- **R-K1-O2 (objects an observer introduces).**
  - An object an observer assigns, appends or inserts is the **same** object downstream: no copy (`R002`).
  - It enumerates by the rule at every later observer invocation (O4–O11) and every serialization (O3), however its creator mutated it in between.
- **R-K1-O3 (serialization)** emits the rule's order as the object then stands.
- **Binding latitude (explicit).** An object an observer has itself just created, with its host language's native map type, is that observer's own value until it reaches another observer or a serialization. How that observer's own code sees it before then is host semantics, not a contract boundary. **This is the one point needing judgment** (§8 Q1).

## 4. The mechanism (prototype, local branch `ce/k1-observer-chain` @ `7fc226b`, not a candidate)

| Piece | Rule | What it does |
|---|---|---|
| `adopt` at construction | R-K1-O1 | Every object in the decoded raw value becomes a `JsObject`, recursively; lists are kept in place. A `JsObject` holds the rule on its own assignments, so O2's mutations are ordered immediately for everyone. |
| `EventBus.before_each(name, prepare)` | R-K1-O2 | An additive Layer-04 extension: runs `prepare(args)` before **each** admitted listener, in every dispatch mode. `tools/execution-start`, `tools/update` and `tools/pre-execute` order the payload's arguments in place. `agent/lifecycle-event` orders `event.arguments` (O6). |
| live callbacks | R-K1-O2 | `order_raw` immediately before `on_execution_start` (ordinary and length-stop) and before each `on_execution_update` delivery, after that event's listeners ran. |
| `execute` | R-K1-O2 | `order_in_place(arguments)` immediately before the tool runs. |
| serialization | R-K1-O3 | `order_raw` (the existing R004 sites). |
| `JsObject.__setitem__` | R002 | stores values as given; never copies. |

## 5. Witnesses (prototype results)

`tests/tools/test_key_order_observer_chain.py`, 11 tests:
- **Codex's start witness:** a start-emit listener mutates, and the start delivery sees `1,2,b`.
- **Codex's update witness:** the same through the update emit and delivery.
- **A plain child** assigned by one pre-execute listener and then mutated through its retained reference is ordered for the next listener; `execute` sees `b,o`.
- **An observer's own mutation of a pipeline object** is ordered at once (R-K1-O1).
- `before_each` runs before every listener in `emit`, `serial` and `parallel`; an undeclared event is refused.

**Single-seam controls**, each removing one delivery's ordering and each failing its witness:
- the start delivery unordered;
- the update delivery unordered;
- no `before_each`, so the next listener sees the unordered child.

The existing corpus (40) and its 10 controls still pass. The `top-level-only` control was updated to the new mechanism.

Full gates: `pytest` 4127 passed, 29 skipped, 19 xfailed; coverage 100.00%; `ruff` and `mypy` clean.

## 6. Conformance delta (with the implementation)

- **Language-neutral listener programs on the raw events.** Add `start_program` and `update_program` to the K1 grammar: the op grammar, run by a `tools/execution-start` (respectively `tools/update`) listener, observed by the live delivery.
- **Expected values:** the authority applies the same program to the raw object at that event and observes ES order. Pi has no separate callback, and the object's order is intrinsic.
- **The pre-execute plain-child-then-retained-mutation case** joins the corpus. `mutation/retained-child-set-later` already covers the assignment; the case adds a second listener.

## 7. Out of scope (unchanged)

- `#129`: value isolation.
- The prepare-shim nonmutation mapping.
- The typed-model rule.
- The diagnostic text.
- Tool-result details.
- Provider projection (Layer 11).

## 8. Challenge (§11.8.4)

- **Is the Pi mapping correct?** Yes. Order is intrinsic in Pi. R-K1-O1 reproduces it for every object the binding owns. R-K1-O2 covers objects introduced by observers at every point the binding hands control to other code.
- **Is the matrix complete?** Section 2 lists every argument-carrying path in the binding. The `before_each` mechanism applies per listener, so a new listener cannot fall between points.
- **Is any of it implementation mechanics?** `before_each` and `adopt` are Python mechanisms; the contract is R-K1-O1/O2/O3.
- **Does it reopen a lower layer?**
  - `EventBus.before_each` is additive in Layer 04: events without it are unchanged.
  - Construction-time adoption changes the **type** of `ToolCallBlock.arguments` to a `dict` subclass, and its identity relative to the caller's pre-construction dict. No certified contract fixes either. The raw value (L0206-D002) is unchanged.
- **Can Rust implement it idiomatically?** Yes, and more simply: Rust's object type is its own, so R-K1-O1 covers every object and R-K1-O2's latitude never arises.
- **Do all findings have acceptance criteria?**
  - `R001`–`R003`: existing.
  - `R004` original: the raw programs.
  - `R004` refined: the start and update witnesses and controls (§5), plus the corpus extension (§6).
- **Q1 (for the checkpoint reviewer, escalated to the Owner only if disputed).** R-K1-O2's latitude: an object an observer has just created, with Python's `dict`, is ordered when it next reaches an observer or a serialization. It is not ordered while that observer's own code is still iterating it. Pi's own literal would already be ordered. Is this a host-semantics boundary or an intentional divergence? If a divergence, it is the Owner's to decide.

## 9. Convergence checkpoint

```text
CONVERGENCE CHECKPOINT
    PROPOSED FOR IMPLEMENTATION

OPEN FINDINGS
    L0206-D001-R004 (refined: mutation between raw deliveries / between observers)

ROOT-CAUSE SURFACE
    point-wise ordering of a shared mutable object; replaced by R-K1-O1/O2/O3

ACCEPTANCE WITNESSES
    tests/tools/test_key_order_observer_chain.py (start/update/inter-listener/own-mutation/
        before_each per mode) + 3 single-seam controls
    corpus extension: start_program / update_program cases (section 6) + authority
    existing: key-order corpus 40 + 10 controls; R001-R003 witnesses

NORMATIVE DELTAS
    spec/llm.md key-order section: R-K1-O1/O2/O3 and the stated latitude (section 3)
    pi-parity-manifest AI-003 entry: evidence pointers

OPEN QUESTION
    Q1 (section 8)

NEXT_OWNER
    Codex (checkpoint review of exactly this proposal)
```
