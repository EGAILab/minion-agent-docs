# Minion Agent — Updated Design Review Feedback

**Date:** 2026-08-18  
**Source reviewed:** `Minion Agent — Design` (updated 2026-08-18)  
**Overall assessment:** Very close to implementation freeze. The updated design integrates the earlier review and workload-validation feedback well, but four design issues should be resolved before freezing the architecture.

## Summary

The updated design is substantially stronger. Earlier concerns around runtime naming, service resolution, scoped registration, `AgentDefinition` vs `AgentInstance`, causal provenance, session operations, content-addressed request state, decision algebra, `ctx.subprocess`, execution-world identity, telemetry, and conformance/spec normativity are now integrated cleanly.

Before declaring the design frozen, resolve four remaining issues:

1. Execution-world compatibility should be enforced by consumers requiring shared-world semantics, not by globally forbidding mixed-world providers.
2. Tool-specific in-flight disposal semantics should not live in the generic runtime scope contract.
3. Waterfall/around-middleware semantics need one precise definition that matches `pre-step`, `pre-execute`, and `post-execute`.
4. Image/media content is still missing from the provider-neutral LLM vocabulary.

There are also several smaller consistency/specification fixes worth making before implementation.

---

## 1. Execution-world validation is currently too global

The execution-world concept is correct and should remain.

The governing invariant is:

> A shell or subprocess may consume an FS-backed target only when the providers share an execution world.

The current wording goes further and says that mounting an incompatible set fails at activation. That is too strong.

A runtime may legitimately mount:

```text
local filesystem
remote shell
```

without ever passing an `FsTarget` between them.

The invalid condition is not:

```text
ctx.fs.world != ctx.shell.world
```

The invalid condition is:

```text
a consumer requires fs + shell to address the same resources
AND
fs.world != shell.world
```

### Recommendation

Providers declare opaque execution-world identities:

```text
FileSystemProvider
    execution_world

ShellProvider
    execution_world

SubprocessProvider
    execution_world
```

Consumers that require shared-world semantics validate compatibility during activation.

Examples:

```text
bash-tool
    requires fs + shell
    requires_same_world(fs, shell)

edit-via-process
    requires fs + subprocess
    requires_same_world(fs, subprocess)

mcp-stdio
    requires subprocess only

read-tool
    requires fs only
```

Recommended wording:

> Execution-capability providers declare an opaque execution-world identity. A component that requires multiple execution capabilities to address the same resources validates their execution-world identities during activation. Merely mounting capabilities from different worlds is not itself invalid. Cross-world resource transfer requires an explicit bridge capability.

**Severity:** Must fix before freeze.

---

## 2. Tool-specific lifecycle semantics do not belong in generic runtime scopes

The generic scoped-registration design is strong:

```text
arbitrary nesting

registration visibility:
    ancestor → descendant

event admission:
    descendant dispatch → ancestor listener

ownership:
    registration context owns disposal
```

However, the scope section currently adds the rule:

> Disposal never races an in-flight tool.

That introduces a tool-specific concept into `minion_agent.runtime`.

Conceptually it creates an undesirable dependency:

```text
runtime
    knows about
tools
```

when the intended direction is:

```text
tools
    built on
runtime
```

### Recommendation

Move the guarantee into the agent/tools layer:

> A turn-owned scope is not disposed until every tool execution started under that turn has settled.

The runtime scope contract should stay limited to nested visibility, ownership, descendant disposal, and deterministic effect reversal.

If a generic scope lease or active-use lease later becomes useful to multiple subsystems, introduce it then.

**Severity:** Must fix before freeze.

---

## 3. Waterfall semantics need one precise definition

The generic event section defines `waterfall` as around-middleware:

```text
listener receives next

listener may:
    call next() and delegate
    or
    not call next() and short-circuit
```

Later sections use wording such as:

```text
agent/pre-step:
    first returned decision wins

tools/pre-execute:
    first decision wins
```

That sounds like a different mechanism:

```text
ordered listeners
first non-empty decision wins
later listeners do not run
```

These models are not automatically equivalent.

A true around-middleware listener can do:

```python
result = await next(payload)
# inspect or transform downstream result
return result
```

The same ambiguity is stronger for `tools/post-execute`, which is called a waterfall but described as a forward transformation chain.

### Recommendation

Define generic waterfall once:

```text
listener(payload, next)

if listener does not call next:
    downstream listeners do not run
    listener's result becomes the chain result

if listener calls next:
    downstream chain executes
    its result is returned
    the current listener may return, replace, or transform that result
    according to the event's declared contract
```

Then specify each decision event in those terms.

If the intended behavior is instead strictly first-decision-wins, define a separate ordered-decision dispatch rather than calling it Cordis-style `waterfall`.

Phase 0 conformance should include:

- short-circuit before downstream listener,
- delegation to downstream listener,
- downstream result propagation,
- result replacement by upstream middleware,
- multi-listener `tools/post-execute` ordering,
- omitted-field preservation,
- no deep merge.

**Severity:** Must fix before freeze.

---

## 4. Image/media content is still missing from the LLM vocabulary

The provider-neutral LLM vocabulary currently lists:

```text
text
thinking
tool_call
```

but the harness already requires image support and built-in `read` is intended to handle images.

Without an image/media content block, the provider-neutral seam has no normative way to send image content back to a multimodal model.

### Recommendation

Extend the vocabulary at minimum to:

```text
ContentBlock =
    Text
  | Thinking
  | Image
  | ToolCall
```

A V1 `Image` contract should carry enough semantic information for providers to adapt it, for example:

```text
Image
    mime_type
    data/reference
```

The exact storage/transport representation can remain implementation-specific.

**Severity:** Must fix before freeze.

---

## 5. Tighten the `stream never raises` boundary

Keep the rule:

> the stream never raises

but define its boundary explicitly.

Recommended rule:

```text
Before a stream is successfully returned:
    local programming errors
    invalid arguments
    service-resolution failures
    configuration errors
    unsupported model/provider selections
may raise normally.

After a stream object has been returned:
    provider failures
    network failures
    model failures
    cancellation/abort
    runtime streaming failures
must never escape iteration as exceptions.

Instead:
    the stream terminates with an error/aborted final message.
```

**Severity:** Specification clarification.

---

## 6. Fix stale Result wording

The execution section correctly defines:

```text
Result[T, FsError]
Result[T, ShellError]
Result[T, SubprocessError]
```

but the traceability/open-questions section still says Result is at the fs and shell seams only.

Update it to:

> `Result` is confined to the filesystem, shell, and subprocess capability seams, using `FsError`, `ShellError`, and `SubprocessError` respectively.

---

## 7. Separate scope visibility from registration composition

The scope section currently says a child sees ancestor registrations with nearest shadowing farthest.

That makes sense for some registries, but not all.

Examples:

```text
tools
    keyed by tool name
    nearest same-name registration may shadow ancestor

system prompt
    multiple sections are additive

event listeners
    multiple admitted listeners all participate

telemetry sinks
    potentially additive
```

The generic runtime should decide:

```text
which registrations are eligible / visible
```

while the owning service decides:

```text
how those visible registrations compose
```

Recommended generic rule:

> A child scope can see registrations owned by itself and its ancestors. Ancestor contexts cannot see descendant registrations.

Then each registry defines collision/aggregation semantics.

**Severity:** Worth resolving before scoped registries are implemented.

---

## 8. Telemetry is now correctly a first-class package

Adding:

```text
minion_agent.telemetry
ctx.telemetry
```

is the correct change.

Keep the separation:

```text
session log
    semantic truth

runtime events
    extension/control surface

telemetry
    observational projection
```

The mandatory sanitization/redaction boundary before sinks is also correct.

### Build-order refinement

Telemetry currently appears in Phase 7, but it observes work implemented earlier:

```text
Phase 3:
    turn / step

Phase 4:
    tool execution

Phase 5:
    provider requests
```

A better split is:

```text
Phase 0 or 2:
    define telemetry vocabulary
    define sanitization contract
    implement no-op/recording telemetry service

Phases 3–6:
    emit telemetry as each subsystem lands

Phase 7:
    production sinks/adapters
    OpenTelemetry
    file/debug sinks
```

Telemetry remains optional at deployment time, but its vocabulary exists from the start.

---

## 9. Package coverage now looks complete

The foundation package set is coherent:

```text
runtime/
llm/
session/
agent/
agent_loop/
tools/
system_prompt/
fs/
shell/
subprocess/
builtin_tools/
skills/
compaction/
telemetry/
invariants/
testkit/
```

No additional Pi package currently appears to require another foundational Minion Agent package.

The deliberate omissions remain appropriate:

```text
coding-agent equivalent
    → application above Minion Agent

TUI
    → presentation layer

server
    → deployment/application layer

concrete SQLite storage package
    → backend implementation behind persistence seams

ctx.jobs
    → deferred until multiple consumers require shared scheduling semantics

isolation realms
    → deferred until different service implementations must coexist per realm

durable operation state machine
    → deferred until in-flight side effects must survive process death
```

---

## 10. Recommended pre-freeze checklist

### Required

1. **Execution-world compatibility**
   - Validate at consumers requiring same-world semantics.
   - Do not globally reject mixed-world capabilities.

2. **Runtime scope purity**
   - Move in-flight-tool disposal semantics out of `runtime`.

3. **Waterfall semantics**
   - Define one exact middleware contract.
   - Reconcile it with `pre-step`, `pre-execute`, and `post-execute`.
   - Add explicit Phase-0 conformance cases.

4. **Multimodal LLM vocabulary**
   - Add image/media content blocks.

### Specification consistency

5. Tighten the exact boundary of `stream never raises`.

6. Update stale Result wording to include `subprocess`.

7. Separate scope eligibility from service-specific registration composition.

### Build-plan refinement

8. Define telemetry vocabulary and no-op/recording implementation earlier; add production sinks later.

---

## Final assessment

The updated design is now approximately **9.3/10** as a foundation document.

The newer requirements fit the same core architecture rather than feeling bolted on:

```text
runtime
    ↓
services + scoped registrations
    ↓
agent instances
    ↓
imperative agent loop
    ↓
append-only session log
    ↓
invariants + conformance

orthogonal capabilities:
    execution seams
    telemetry
```

The architecture remains general rather than chatbot-specific or coding-agent-specific.

After the four required issues above are resolved, the design is in a strong enough state to move into **Phase 0: language-neutral conformance-format design** without carrying known structural ambiguity into implementation.
