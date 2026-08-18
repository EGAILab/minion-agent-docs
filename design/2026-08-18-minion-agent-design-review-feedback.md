# Minion Agent Design Review Feedback

**Reviewed:** 2026-08-18  
**Source:** `Minion Agent — Design`  
**Overall assessment:** Architecturally coherent and close to implementation-ready, but a few semantic contracts should be made explicit before implementation begins.

## Summary

The design is strong in its overall direction:

- Pi semantics remain the compatibility target.
- Cordis semantics define composition and lifecycle.
- The live loop stays imperative rather than introducing an unvalidated pure reducer.
- The append-only session log is the source of truth.
- Runtime invariants independently verify request reconstruction.
- Conformance is designed to be language-neutral for a future Rust implementation.
- Provider quirks are deferred until after mock-driven agent semantics are stable.

The main remaining work is not a redesign. It is to tighten several contracts so implementation does not accidentally define behavior that later becomes difficult to change or reproduce in Rust.

---

# Blocking design clarifications

## 1. Extend language-neutral conformance to the Cordis/plugin kernel

The current conformance layer mainly targets agent/session behavior, while Phase 1 — plugin runtime — is Tier 2 only.

That leaves important Cordis semantics Python-specific:

- reactive activation when dependencies appear
- unload when dependencies disappear
- reverse-order effect disposal
- double-dispose behavior
- effect creation after disposal
- service appearance/disappearance
- waterfall short-circuiting
- event ordering
- provider replacement/shadowing

These semantics will matter just as much to a future Rust implementation as the agent loop semantics.

### Recommendation

Split language-neutral conformance into at least two families:

```text
conformance/
  cordis/
    reactive-dependency.yaml
    effect-reversal.yaml
    waterfall-short-circuit.yaml
    service-replacement.yaml

  agent/
    turn-lifecycle.yaml
    steering.yaml
    tools.yaml
    cancellation.yaml
```

Cordis scenarios can assert a generic lifecycle/effect trace instead of a session log.

Tier 2 Python tests should still cover Python-specific behavior such as:

- `Context.__getattr__`
- `ctx.require(...)`
- pydantic integration
- `@contextmanager` effect syntax
- asyncio-specific cancellation details

The key rule should become:

> Any semantic behavior intended to be shared by Python and Rust belongs in language-neutral conformance.

---

## 2. Define service identity, multiplicity, replacement, and shadowing

The design defines `Context` as a service repository and fibers as reactively dependent on services, but service-resolution semantics are not fully specified.

Questions that need explicit answers:

- Can multiple plugins provide the same service in one context?
- If so, which provider wins?
- Is resolution based on registration order, priority, nearest context, or another rule?
- If the active provider disappears, does an older provider automatically become visible again?
- Does a dependent fiber unload/reload when the selected provider changes?
- Can child contexts shadow parent services?
- What is the stable runtime identity of a service?
- Is `Protocol` itself the key, or is there a language-neutral service key beneath it?

### Recommendation

Keep both ergonomic and typed access:

```python
ctx.tools
ctx.require(ToolService)
```

but make them two views over one canonical service-resolution mechanism.

Conceptually, use a stable service identity such as:

```text
ServiceKey[T]
```

even if most plugin authors never interact with it directly.

Reactive dependency behavior must be defined in terms of the resolved service identity/provider.

---

## 3. Clarify the filesystem ↔ shell execution-world contract

Splitting `ctx.fs` and `ctx.shell` is the right architectural choice, but independent swappability does not mean arbitrary combinations are automatically coherent.

Example:

```text
ctx.fs    = local Windows filesystem
ctx.shell = remote Linux sandbox
```

A filesystem path returned by `ctx.fs` cannot automatically be opened by `ctx.shell`.

The current `process_path(target)` concept therefore needs an explicit definition of whose execution world the returned path belongs to.

### Required invariant

> A shell may consume an FS-backed target only when the two providers share an execution world or an explicit bridge exists between them.

Possible implementations include:

```text
shell.resolve_target(fs_target)

fs.process_path(target, execution_world)

shared Workspace / ExecutionWorld identity

activation-time compatibility validation
```

The exact API can remain an implementation decision, but the compatibility relationship must be part of the design.

---

## 4. Tighten the `Result` vs exception boundary

The design currently says:

> filesystem and shell operations never raise; every failure, including unexpected backend failures, returns a typed error value

but also says:

> tool failed becomes a model-visible result, while harness bugs crash loudly

Those statements need a precise boundary.

### Recommended rule

Expected operational/environmental failures are values:

```text
not found
permission denied
invalid path
stale version
timeout
abort
process exit
I/O failure
remote unavailable
```

Framework/provider invariant violations remain exceptions:

```text
invalid internal state
impossible enum/state transition
broken provider implementation
assertion failure
programming error
```

Generic backend errors such as ordinary `OSError` should normally be mapped into the capability error vocabulary.

Also prefer separate error domains:

```text
Result[T, FsError]
Result[T, ShellError]
```

rather than using `FileError` for both.

---

# Session/log refinements

## 5. Reword `convertToLlm` compatibility

The design currently says the behavior is "equivalent and strictly more inspectable," but immediately identifies a Pi behavior that has no direct equivalent: arbitrary message rewriting through `convertToLlm`.

A more precise statement is:

> Filtering/projection behavior is equivalent and more inspectable. Rewrite behavior moves to `agent/pre-step` and is pinned separately by compatibility conformance.

This avoids claiming full structural equivalence where the extension mechanism intentionally changes.

---

## 6. Define portability of plugin-declared surface events

The design allows plugin-declared session events to join the model-visible surface.

That is fine in Python, but a future Rust implementation cannot automatically reproduce an arbitrary Python projection function.

Distinguish:

```text
core surface event semantics
    → language-neutral normative contract

plugin-defined surface projections
    → plugin-specific contract, not automatically cross-language
```

If cross-language third-party plugins become a requirement later, their projection format will need its own portable schema/contract.

---

# Agent-loop refinements

## 7. Distinguish the reasons for `agent/pre-step`

Both Pi `transformContext` and `prepareNextTurn` currently map to `agent/pre-step`.

That may be correct, but the event should expose why the pre-step is happening.

Conceptually:

```text
PreStepReason =
  initial
  tool_results
  steering
  next_turn
  continuation
```

The exact values should come from Pi conformance behavior.

This preserves one extensibility point without erasing lifecycle distinctions that plugins may care about.

---

## 8. Specify the decision algebra for `agent/turn-stopping`

`serial` defines execution order, but not semantic combination.

The design should explicitly define something like:

```text
NoOpinion
Continue
Stop
```

and answer:

- Does `Stop` short-circuit?
- Do all listeners run?
- Can a later `Continue` override an earlier `Stop`?
- What value is returned when nobody has an opinion?

Similarly, `tools/post-execute` should explicitly state how multiple listeners compose.

For example:

> Each listener receives the finalized output of the previous listener. Fields explicitly returned by the listener replace those fields; omitted fields remain unchanged. No deep merge occurs.

---

# Harness refinements

## 9. Avoid duplicate ownership of tool schemas

The design says:

- `ctx.tools` owns executable tools and their pydantic/JSON schemas.
- plugins also register tool schemas through the system-prompt service.

That risks two independent sources of truth.

### Recommendation

Use:

```text
ctx.tools
    = authoritative executable tool registry

request assembly
    → obtains currently-visible tool schemas from ctx.tools

ctx.system_prompt
    = textual/system prompt sections only
```

If the current wording merely means both contribute to request construction, rewrite it so implementers do not create duplicate schema registration.

---

## 10. Make compaction replacement semantics explicit

The append-only compaction model is strong, but repeated/nested compaction needs deterministic projection semantics.

The design should state:

> A compaction event identifies the exact surface range it supersedes and the replacement surface. `derive_messages()` applies replacements deterministically, including repeated or nested compactions.

A compaction event will likely need concepts such as:

```text
superseded surface range
summary/replacement content
retained-tail provenance
```

The raw log must never double-project both the original tail and a copied retained tail.

This should become a dedicated conformance family.

---

# Conformance/spec wording

## 11. Avoid making finite scenario files the only possible semantic specification

The document currently says:

> `conformance/` is the specification; `spec/` is only a prose companion.

The intent is good, but finite example scenarios cannot exhaustively define all behavior of a reactive plugin runtime.

A safer division is:

```text
minion-agent-docs/spec/
    normative semantic rules

conformance/
    normative executable compatibility cases
```

with the rule:

> For behavior covered by a conformance scenario, the executable result is the compatibility oracle. The prose spec defines the general semantic rule and behavior that cannot be exhaustively enumerated.

This avoids creating accidental "unspecified" behavior simply because a particular edge case has not yet been encoded in YAML.

---

# What should remain unchanged

The following decisions are strong and should be retained:

## Imperative agent-loop driver

Keep the DSH/Pi-style stateful imperative async driver. Do not introduce a pure reducer architecture merely for theoretical cleanliness.

## Log-as-truth

Keep:

> model-visible means logged

and independently reconstruct model requests from the durable session log.

## Runtime invariants

Keep `ctx.invariants` as a central registry with package-owned checks.

## Pi event-stream compatibility projection

Keep the native runtime/log model independent, with a projection plugin rebuilding Pi's observable `AgentEvent` stream for conformance.

## Inbox model

Keep the generalized DSH-style:

```text
send(message, target, wakeup)

followup = next-turn + wake
steer    = next-step + wake
inject   = next-step + no wake
```

while retaining Pi-compatible claim policies.

## Pi batch-contagion semantics

For the Pi-compatibility implementation, preserve:

> if any tool in a batch is sequential, the entire batch runs sequentially

even though DSH's barrier/grouping scheduler may be a better future policy.

Also retain:

- tool execution end events in completion order
- tool-result messages in assistant source order

## `Result` only at capability seams

Do not spread Rust-style `Result` throughout the Python plugin/tool ecosystem.

## Mock-first build order

Keep Phases 1–4 provider-independent and mock-driven. Real provider integration should not define or contaminate core runtime semantics.

## Deferred features

Continue deferring:

- isolation realms
- declarative loader
- HMR
- durable crash-recovery state machine
- `ctx.subprocess` until a non-shell process consumer appears

The documented triggers are appropriately concrete.

---

# Recommended priority before Phase 1 implementation

Resolve these in order:

1. **Language-neutral conformance for the Cordis/plugin kernel**
2. **Service identity, replacement, and context-shadowing semantics**
3. **Filesystem/shell execution-world compatibility**
4. **Operational `Result` vs programming-exception boundary**

After those four are explicit, the remaining refinements can safely be handled during detailed implementation planning without destabilizing the foundational APIs.

---

# Overall assessment

The architecture is strong and no longer has a major conceptual conflict.

The remaining risks are mostly semantic underspecification at foundational boundaries rather than architectural flaws.

**Assessment: ~8.5/10 architecturally, with the design ready to move into implementation planning once the four blocking contracts above are resolved.**
