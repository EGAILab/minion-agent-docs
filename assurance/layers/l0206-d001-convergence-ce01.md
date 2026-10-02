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

---

## 10. Checkpoint review 1 → Owner Q1 → revision 2

**Codex.** Checkpoint review 1 (docs #228 comment `5945709684`) **REJECTED** the checkpoint on **`CE-L0206-D001-01-C001`**: same-observer read-after-attachment.
- Codex's witness: a hook assigns `args.o = {b, "2", "1"}`, reads `args.o`'s keys and decides block or proceed.
- Pi gives `1,2,b` and proceeds. The §3 latitude gives `b,2,1` and blocks.
- Codex judged the Q1 latitude an observable divergence and escalated it.

**Owner decision K1 Q1** (`#100` comment `5947071963`, verbatim): Option 1, strengthened. It **supersedes §3's latitude and §4's mechanism**:
- **Required (exact parity):** every Minion-mediated attachment and observation of an object reachable through the tool-argument graph exposes ECMAScript order.
  - **Attachment:** a plain `dict` attached through a Minion-owned seam is ordered **in place, before the operation returns**, and keeps its identity (`args["o"] is child`).
  - **Reads:** every graph-mediated read orders what it exposes, in place, so a retained alias mutated out of order is repaired by the next read.
  - The same-hook read-back (C001) is required parity.
- **Approved `INTENTIONAL_BOUNDED_DIVERGENCE`, Python only.** A plain `dict` already attached, then mutated directly through a retained native alias and enumerated directly through that same alias, inside the same uninterrupted callback, before any further Minion-mediated graph operation, may show insertion order. It must not leak past the next framework boundary.
- **Rejected:** Option 2 (`ctypes` type-pointer rewriting) and Option 3 (the wider latitude). Rust: exact parity.

### 10.1 Revised rules (proposed normative text for `spec/llm.md`)

> Objects reachable through the Minion tool-argument graph are normalized to ECMAScript own-property order at every Minion-mediated attachment and observation boundary: an object attached through a graph seam (object field assignment; array append, insert, replacement, extend; a hook's replacement result; nested attachment) is ordered in place before the operation returns, keeping its identity; every graph-mediated read (indexing, iteration, the next listener, validation and execute handoff, `tool_execution_*` observation, serialization and persistence, nested traversal) orders what it exposes, in place.
>
> Python cannot intercept arbitrary direct mutation and enumeration performed solely through an externally retained plain-dict alias during an uninterrupted callback; that narrow interval is an approved Python-specific divergence (Owner decision K1 Q1). Rust: no such interval.

**Classification (decision §16):**

| Part | Classification |
|---|---|
| the key-order target | DIRECT_PI_PARITY |
| the Python graph-mediated mechanism | MINION_ARCHITECTURAL_MAPPING |
| the retained-native-alias interval | INTENTIONAL_BOUNDED_DIVERGENCE (observable; it can change a hook decision) |
| Rust | DIRECT_PI_PARITY |

### 10.2 Revised mechanism (prototype, local branch `ce/k1-observer-chain` @ `f166140`, not a candidate)

| Piece | Rule |
|---|---|
| `JsObject` | `__setitem__` orders the attached value in place (no copy). `__getitem__`, `get`, `values`, `items` and `setdefault` order what they return, in place. Its own index-key ordering is kept |
| `JsArray` (new, a `list` subclass) | the array seam. `append`, `insert`, `extend`, `+=`, and element or slice replacement order the attached value in place. Element reads, slices and iteration order what they expose |
| `adopt` at construction | the raw value's objects and arrays become `JsObject` / `JsArray` once, before the pipeline owns them. Afterwards no object is replaced |
| framework boundaries (§4, unchanged) | `EventBus.before_each` before every listener in every dispatch mode; ordering before each live delivery, before `execute`, and at every serialization. These hold the "no leak past callback control" rule (decision §9) for anything a retained alias disordered |

### 10.3 Evidence (decision §12–§14), prototype results

**`tests/tools/test_key_order_observer_chain.py`** runs every witness through real hooks of the real `execute_call` pipeline.

| Witness | Result |
|---|---|
| A | attach, then read through `args` → `1,2,b`, no block |
| B | identity kept; a later alias mutation is visible at `execute` |
| C | mutated alias, then read through `args` → repaired |
| D | mutated alias, then the next listener → ordered |
| E | mutated alias, then `execute` → ordered |
| F | nested attachment → ordered at once |
| G / H / I / J | array append, insert, replacement, extend: the element is ordered before the call returns, identity kept |
| K | a hook replacement reaches `execute` ordered (same object) |
| L | raw start and update deliveries after a listener mutation → ordered |

**Divergence witness (documentary).**
- A direct alias enumeration gives `b,2,1`: the approved gap, exactly bounded.
- A read through `args` then gives `1,2,b`.
- The alias, repaired in place, then gives `1,2,b`.

**Controls (decision §14).** Each control kills at least one matrix witness:
- copy-on-assignment;
- normalize only before `execute`;
- normalize only before the next listener;
- normalize only during serialization;
- top level but not nested;
- array insertion bypass;
- the same-hook `args` read returning insertion order;
- identity loss.

**Corpus (40) and its 10 controls:** all pass. The `raw-boundaries-unordered` control now also removes adoption, and kills 3.

**Gates:** `pytest` 4146 passed, 29 skipped, 19 xfailed; coverage 100.00%; `ruff` and `mypy` clean.

**Not used:** no interpreter-object surgery (decision §10).

### 10.4 Conformance delta (with the implementation)

§6 is unchanged (`start_program` / `update_program`). In addition, the matrix's language-neutral rows A–K join the corpus as hook programs, observed both in-hook and downstream:
- an in-hook read-back observation;
- array `insert` / `replace` / `extend` ops in the op grammar.

The divergence witness stays a Python binding test; it is not a corpus case.

## 11. Convergence checkpoint (revision 2)

```text
CONVERGENCE CHECKPOINT
    PROPOSED FOR IMPLEMENTATION (revision 2; revision 1 REJECTED on C001)

OPEN FINDINGS
    L0206-D001-R004 (convergence root)
    CE-L0206-D001-01-C001: REQUIRED PARITY, resolved by attachment + read normalization (Owner Q1)

GOVERNANCE
    Owner K1 Q1 (#100 comment 5947071963): bounded Python divergence approved; options 2/3 rejected

ACCEPTANCE WITNESSES
    matrix A-L + divergence witness + 8 controls (section 10.3)
    corpus 40 + 10 controls; corpus extension (sections 6, 10.4)
    R001-R003 closures preserved

NORMATIVE DELTAS
    spec/llm.md key-order section: section 10.1 wording + classification
    manifest AI-003: evidence pointers and the divergence disclosure

NEXT_OWNER
    Codex (checkpoint re-review of exactly this revision)
```

---

## 12. Checkpoint review 2 → Owner Q2 → revision 3

**Codex.** Checkpoint revision-2 review (docs #228 comment `5947216500`) **REJECTED** the checkpoint on **`CE-L0206-D001-01-C002`**: containers introduced after construction.
- Under the identity rule, a hook-introduced `dict` or `list` stays native.
- So a child attached **through** it (`args["a"].append(child)`, `args["o"]["n"] = child`) is not ordered at its attachment.

**Owner decision K1 Q2** (`#100` comment `5948712829`, verbatim): **Option 1.**
- **"Minion-mediated" = the mutation itself dispatches through a Minion-owned seam:** `JsObject.__setitem__`, `JsArray` mutators, hook replacement processing, graph normalization or traversal. Merely reaching a native container through `args` does not make the operation mediated.
- **Identity stays mandatory.**
- **The approved bounded Python divergence is extended** to a child attached through a hook-introduced native container and observed directly through the hook's own alias before the next graph read or framework boundary. All six conditions of decision §5 are required.
- **Reads through `args`, the next listener, validation, `execute`, events and persistence stay exact.**
- **Copy, wrappers and interpreter surgery are rejected. Rust is exact.**

### 12.1 Revised semantic model (decision §12), the normative basis for `spec/llm.md`

```text
A. construction-owned containers                  -> JsObject/JsArray; exact Pi order
B. native object attached through a Minion seam    -> same object; ordered in place immediately
C. native parent container introduced later        -> identity retained (stays native)
D. mutation through that parent's own native API   -> not intercepted (not Minion-mediated)
E. any later Minion-mediated traversal/boundary    -> recursive in-place normalization before exposure
F. direct native-alias observation in the D->E gap -> approved bounded Python divergence
```

The §10.1 wording still holds, with "Minion-mediated" read per the decision §15 correction. The divergence paragraph covers both approved intervals: Q1's retained-alias interval and Q2's native-container interval. Rust has neither.

### 12.2 Mechanism

The mechanism is unchanged from §10.2: the prototype already realizes A–F.
- `JsObject` / `JsArray` are the seams for A and B.
- Recursive in-place `order_in_place` runs on every graph read (`JsObject.__getitem__` / `get` / `values` / `items`, `JsArray` reads and iteration) and at every framework boundary (E).

The local prototype is `ce/k1-observer-chain` @ `f43432a`; it is not a candidate.

### 12.3 Evidence (decision §13–§14), prototype results

**`tests/tools/test_key_order_native_containers.py`** keeps matrix A–L and adds:

| Witness | Pairs |
|---|---|
| M/N/T/U | a native list parent with `append`: the direct alias shows `b,2,1` (the approved divergence, documentary); the read through `args`, the next listener and `execute` are exact; identity is kept for both parent and child |
| O / P / Q | `insert` / replacement / `extend` through a native list: the same pairs |
| R/S/T/U | a native dict parent with a nested assignment: the same pairs |
| deeper descendants | attached through native containers and repaired by one read through `args` |
| V | event and serialization: a start-event listener builds native containers on the **raw** object and attaches through them, and the live start delivery is exact. A native attachment after construction, never read through the graph, is still ordered in the session encoding |

**Controls (decision §14).** Each kills at least one witness of A–V:
- copying hook-introduced parents;
- identity-replacing wrappers;
- normalize only at `execute`;
- normalize only between listeners;
- no recursive normalization on a graph read;
- disorder leaking into `execute`;
- dicts but not lists;
- direct children but not deeper descendants.

The Q1 controls (8) and the corpus controls (10) are kept.

**Gates:** `pytest` 4161 passed, 29 skipped, 19 xfailed; coverage 100.00%; `ruff` and `mypy` clean.

## 13. Convergence checkpoint (revision 3)

```text
CONVERGENCE CHECKPOINT
    PROPOSED FOR IMPLEMENTATION (revision 3; revisions 1 and 2 REJECTED on C001 and C002)

OPEN FINDINGS
    L0206-D001-R004 (convergence root)
    C001: RESOLVED by Owner Q1 (#100 comment 5947071963)
    C002: RESOLVED by Owner Q2 semantic-boundary clarification (#100 comment 5948712829)

ACCEPTANCE WITNESSES
    matrix A-L (sections 10.3) + M-V (section 12.3) + the two documentary divergence witness families
    controls: Q1 (8) + Q2 (8) + corpus (10); corpus 40 + extension (sections 6, 10.4)
    R001-R003 closures preserved

NORMATIVE DELTAS
    spec/llm.md key-order section: section 10.1 wording + section 12.1 model + both divergence intervals
    manifest AI-003: evidence pointers and the divergence disclosure

NEXT_OWNER
    Codex (checkpoint re-review of exactly this revision)
```

---

## 14. Agreed checkpoint and implementation candidate

**Checkpoint.**
- Codex **APPROVED** checkpoint revision 3 (docs #228 comment `5948883823`).
- The control record reads CONVERGENCE CONTRACT AGREED FOR IMPLEMENTATION (`#100` comment `5948884466`), recorded on that verdict.

**Implementation candidate:** code #128 @ `57b35bc4`, a fast-forward from the reviewed `92db98f9`:
- **Mechanism (§10.2 / §12.2):**
  - `JsObject` / `JsArray` attach and read seams, adopted at construction;
  - `EventBus.before_each`;
  - ordering at the live deliveries, before `execute`, and at serialization.
- **`spec/llm.md`:** the §10.1 wording, the §12.1 model, both divergence intervals and their classification.
- **Manifest `AI-003`:** the divergence disclosure.
- **Corpus, now 49 cases.** The §6 / §10.4 extension adds:
  - the `read` op (in-hook read-back through `args`, `hook_reads`);
  - array `replace` / `extend`;
  - attachment through hook-introduced native lists and dicts;
  - `start_program` / `update_program`, observed at the live deliveries.

  The authority (`harness/run.sh`) regenerates the corpus, and `k1.json` is byte-unchanged.
- **Runner:** observes natively (`dict` / `list` iteration), so the observer never orders anything. The live deliveries are the observation points for start and update.

**Fresh results:**

| Check | Result |
|---|---|
| corpus | **49/49**; reviewed head `92db98f9` fails exactly the 9 new cases |
| corpus controls (10) | killed |
| matrix A–L + M–V | pass |
| controls Q1 (8) + Q2 (8) | killed |
| documentary divergence witnesses | at the approved boundary |
| `pytest` | **4170 passed**, 29 skipped, 19 xfailed; coverage **100.00%** |
| `ruff` / `mypy` | clean |

**R004 stays open** until the targeted closure review (§11.8.7).
