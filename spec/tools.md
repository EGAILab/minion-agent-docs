# Tool Semantics

This document owns two distinct, independently certified layers (`process/implementation-
conformance-workflow.md` §6): **Layer 05 — Tool model + registry** (this section) and
**Layer 06 — Tool execution pipeline** (below, `NOT CERTIFIED BY LAYER 05`). Layer 05 answers what
a tool *is* and who owns/publishes it; Layer 06 answers what happens when the model actually calls
one. Existing execution code in the repository predates this split and is not certified by it —
see the Layer-06 section's own header.

## Layer 05 — Tool model + registry

Mirrors pinned Pi's `Tool`/`AgentTool` (`packages/ai/src/types.ts`, `packages/agent/src/types.ts`)
for the tool definition's own fields, and the frozen master's `ctx.tools` architecture (design
spec section 7) for ownership/registration/visibility — an intentional Minion divergence, since Pi
itself has no registry concept at all (`AgentState.tools` is a plain mutable `AgentTool[]`
property, no scoping).

### Tool definition (Pi-derived)

```text
Tool
    name                    string
    description             string
    parameters              object-valued JSON Schema, REQUIRED -- missing/null are not
                             aliases for "no parameters" (`L05-R005`); a no-argument tool
                             supplies the explicit empty schema {type: object, properties: {}}
    constrained_sampling?   absent | false | json_schema{strict: prefer|require}
                             | grammar{variants: closed to openai_lark/openai_regex,
                             each independently optional, `L05-R001`}

AgentTool extends Tool
    label                   string, REQUIRED (not optional -- `TOOL-F001`)
    prepare_arguments?      (args) -> args -- field/signature only; when/whether it
                             runs is Layer 06 (`TOOL-F002`)
    execute                 (tool_call_id, params, signal?, on_update?) -> result --
                             target capability shape (`TOOL-F003`); Layer 06 closed the
                             tool_call_id/on_update half (`TOOL-017`, `TOOL-018`), and
                             Layer 09 has since closed the cancellation-signal half too
                             (`ToolDefinition.wants_signal`, `L09-R003` -- see `AG-007`/
                             `TOOL-024`): all four combinations (neither, update-only,
                             signal-only, both) are now realized; corrected here after a
                             stale-documentation finding (`L09-R016`) found this row still
                             describing the signal half as open
    execution_mode?          parallel | sequential -- per-tool override; absent means
                             "no per-tool preference," defers to the run-level default
                             (`TOOL-F004`), never itself contributes contagion exclusivity
```

`constrained_sampling`'s grammar variants are exactly the two independently-optional formats
pinned Pi's own `GrammarFormat` union defines — `openai_lark` and `openai_regex` — a closed
2-value domain, not an open string-keyed map (`L05-R001`; an earlier draft of this spec falsely
attributed an open map to Pi, matching `packages/ai/src/types.ts`'s `GrammarFormat` and
`GrammarVariants = Partial<Record<GrammarFormat, string>>` at the pinned commit exactly). Both
formats may be set simultaneously; each is independently optional, including both being unset at
once (`variants: {}`) -- Pi's own `Partial<Record<...>>` type statically permits this, so Layer 05
accepts it too; Pi's own rejection of a grammar config with no variant selected happens at provider
request-construction time (`packages/ai/src/api/constrained-sampling.ts::
resolveGrammarConstrainedSampling`), which is Real Providers (assurance Layer 11) territory, not a
Layer-05 rule. On the wire, an unset format is omitted entirely (mirroring Pi's own
`Partial<Record<...>>` object-literal semantics — an unset key is genuinely absent, not present
with a null value), never emitted as an explicit `null`. `constrained_sampling` itself has exactly
four states -- absent, `false`, `json_schema` config, `grammar` config -- and explicit `null` is not
a fifth alias for absent (`L05-R006`): the canonical absent state omits the field entirely; a
scenario, request, or stored value carrying an explicit `null` for this field is malformed, not a
synonym. (The model-facing *projected* JSON's own `null`-for-absence convention, matching this
project's established optional-field pattern, is the output side and is unaffected by this rule.)
Provider-specific enforcement/fallback for constrained sampling is Real Providers (assurance
Layer 11) territory; Layer 05 owns only preserving the metadata end to end, unmodified, into the
model-facing schema.

`parameters` is required and contains an object-valued JSON Schema representation. A tool with no
parameters uses the explicit empty-object schema (`{type: object, properties: {}}`) -- the tool
author supplies this directly; missing and `null` are not semantic aliases for it (`L05-R005`,
previously conflated at the canonical-fixture layer, and previously left unenforced at the public
`ToolDefinition` boundary itself). A model told a tool has no schema has no defined way to call it,
so nothing publishes as "no schema." "Object-valued" describes the JSON *representation* of the
schema itself (the value is a mapping/object, not the JSON-Schema-spec boolean shorthand) -- it does
not require the schema to *describe an object instance* by containing a top-level `type: object`
keyword. Pinned Pi's `Tool<TParameters extends TSchema>` is generic over TypeBox's whole `TSchema`
domain, not narrowed to `TObject`: a non-object-instance schema (`{type: string}`) and a top-level
combinator (`{oneOf: [...]}`) are equally valid tool parameter schemas (`L05-R005` round 2 --
conflating these two meanings of "object-valued" was the exact bug the first repair introduced).

The model-facing schema's own host-language representation (a validated schema-authoring class vs.
a raw JSON Schema value) is implementation policy, not a semantic rule — the *observable projected
JSON* is the contract, not any one library's construction path (`TOOL-F010`).

### Registry (Minion architecture, not Pi-derived)

```text
ctx.tools is the sole authoritative registry of executable tools and their
model-facing schemas. ctx.system_prompt may describe tools textually but
never owns or registers a schema. Request construction obtains visible tool
schemas from ctx.tools, not from any duplicated storage.

Registration is a reversible effect: tool visibility and lifecycle both follow
the registering context exactly as any other effect does (design spec
section 3), which means ownership -- not "plugin or scope, whichever comes
first" -- decides what withdraws a registration (`L05-R003`, previously
underspecified as an either/or). An *unscoped* registration (made directly
against a plugin's own context) is fiber-owned: unloading the registering
plugin withdraws it. A *scoped* registration (made through `ctx.scope(key)`)
is owned by that scope from the moment of registration onward: only that
scope's own disposal, or an explicit withdrawal of the registration's own
handle, withdraws it -- unloading the plugin that happened to perform the
registration does not, even if that plugin is the scope's sole occupant.
This is not a Layer-05 policy choice; it is certified Runtime effect-ownership
behavior (`Context.effect()` routes to the nearest enclosing scope's own
disposables whenever one is present, never to the fiber's, independent of
which plugin is currently executing), which this registry inherits
unmodified. A tool definition's `execute`/`prepare_arguments` callbacks may
therefore still be reachable after their originating plugin has unmounted, for
as long as the owning scope remains active; tool authors must not close over
state whose own lifetime is tied to the originating plugin's mount (rather
than to the scope), since nothing withdraws the registration on that account.

Visibility follows the certified Runtime's own scope rules (section 3),
unmodified by this registry: nearest scope first, then ancestors outward,
untagged (global) registrations last. This order is normative and
observable -- it becomes the tools list in provider request context
(`TOOL-F008`) -- not incidental container iteration order.

A disposed/inactive requesting scope is never a valid observation point
(`TOOL-015`, `L05-R002`, previously untraced): `visible_from`/`resolve`/`schemas`
given a disposed scope return no visible tools at all, regardless of ancestor or
untagged/global registrations that would otherwise be eligible from a live scope
at the same tree position. A live descendant is unaffected by an unrelated
disposed scope elsewhere in the tree (a disposed sibling or disposed child) and
still observes its own eligible ancestor/global registrations normally. This
reuses the already-certified `Scope.disposed` property at the query boundary,
unmodified Layer 01 -- `ScopedRegistry`'s own key-chain-only visibility
algorithm has no liveness concept and is not changed by this rule. The query
methods accept a bare `ScopeKey` (no liveness information, preserves the prior
key-chain-only behavior) or a live `Scope` object; passing the `Scope` itself is
what allows this rule to engage.

Same-name composition: a nearer visible registration shadows a farther one.
This is a keyed-registry composition rule specific to tools, deliberately
different from Runtime *service* registration (which prohibits duplicate
providers with no fallback stack) -- shadowing, not conflict. Withdrawing the
nearer registration restores the farther visible one; the name is never left
absent while any visible registration for it still exists.

Same-scope duplicate name (`TOOL-F009`, previously underspecified): the
earliest-registered entry for a name wins within one scope; a later
same-scope, same-name registration is composed but never observably visible
unless the earlier one is withdrawn.

Tool identity is by string value, matching the project's named-extension
identity rule elsewhere -- never language object/pointer identity.

resolve(name, scope): an unknown name has no definition -- absent, not an
error. What a caller does with that absence (e.g. a model-facing error
result) is Layer 06, not certified here.
```

### Explicitly not certified by Layer 05

`prepare_arguments`'s actual invocation timing/ordering, `execute`'s actual invocation
(`tool_call_id`/`signal` wiring, argument validation, error conversion), `AgentToolResult`'s
partial-result/usage/`added_tool_names`/`terminate` handling, and any provider-specific
constrained-sampling enforcement are Layer 06 (or Real Providers, assurance Layer 11) territory —
recorded as their own audit obligations, not implemented or certified by this section.

---

## Layer 06 — Tool execution pipeline

Owns how already-produced `ToolCall`s execute through the Layer-05 `ToolDefinition`/`ToolRegistry`
surface, mirroring pinned Pi's `prepareToolCall` + `executePreparedToolCall` +
`finalizeExecutedToolCall` (`packages/agent/src/agent-loop.ts`). Explicitly does **not** own: the
full Agent run loop, `prompt()`/`continue()` lifecycle, steering/follow-up messages, or whether the
Agent performs another model turn after a batch (`process/implementation-conformance-workflow.md`
§6, item 6; a later Agent-loop layer's territory even where the same pinned Pi function also
contains that logic).

### Per-call pipeline

```text
resolve -> prepare_arguments -> validate -> before-hook -> execute (+ live updates) -> after-hook
```

`tool_execution_start`/`tool_execution_end` (`tools/execution-start`/`tools/execution-end`) bracket
every call unconditionally, regardless of outcome. An outcome decided before `execute()` runs --
unknown tool, a `prepare_arguments`/validation/before-hook exception, or an explicit before-hook
block -- is **immediate**: `execute()` and the after-hook (`tools/post-execute`) are never invoked
for it. Pinned Pi's `finalizeExecutedToolCall` (the after-hook) is only ever invoked for an outcome
that actually reached `execute()`, success or failure alike -- an earlier, uncertified revision of
this pipeline ran the after-hook uniformly on every outcome, including immediate ones; that is a
genuine Pi-parity defect, not an acceptable hardening (`TOOL-017`).

`resolve` uses the certified Layer-05 `ToolRegistry.resolve(name, scope)` (Minion architecture);
pinned Pi resolves by a linear `Array.find` over `AgentState.tools` instead, since Pi has no
registry at all -- the *lookup outcome* (found/absent) is the shared contract, not the mechanism.
An absent tool's model-visible text is pinned Pi's own exact string, not a host-specific rewording
(`IR-L06-003`, `PI_PARITY_DEFECT`): `` `Tool ${toolCall.name} not found` ``
(`packages/agent/src/agent-loop.ts::prepareToolCall`) -- for a call naming `foo`, the text is
exactly `Tool foo not found`. A prior revision used different wording entirely, asserted only by
substring containment, which never caught the divergence; the corrected text is asserted by exact
equality.

`prepare_arguments` (pinned Pi's `AgentTool.prepareArguments`) always runs before validation, never
after -- reordering these is a `PI_PARITY_DEFECT`, not a stylistic choice. It receives a fresh copy
of the arguments so an in-place-mutating shim cannot corrupt the source `ToolCall.arguments`
(nonmutation discipline, matching XFORM's own rule).

Validation checks the prepared arguments against the tool's schema, with no exemption for either
representation (`L06-R001`; an earlier revision skipped validation entirely for a raw JSON-Schema
`dict`, a genuine `PI_PARITY_DEFECT` -- pinned Pi's `validateToolArguments` validates every
`Tool.parameters: TSchema`). A pydantic-model-backed `ToolDefinition.parameters` gets real pydantic
validation (including its default-filling); a raw, object-valued JSON-Schema `dict` (`TOOL-F010`)
is validated for real too, via the general `jsonschema` library against the exact schema Layer 05
approved. Neither path reproduces pinned Pi's TypeBox-specific coercion/conversion algorithm
(`packages/ai/src/utils/validation.ts`) byte-for-byte -- that remains a disclosed, intentional
divergence: the shared contract is "arguments conform to the supplied JSON Schema," not "TypeBox's
exact clone/convert/coerce pipeline," and Layer 05 deliberately declined to make Layer 06 into a
general JSON-Schema-dialect-feature-complete validator. A raw-schema tool's arguments pass through
unchanged when they already validate (no JSON-Schema-only defaults are filled in, unlike pydantic's
own default-filling for its models).

The before-hook and after-hook are Minion's own `tools/pre-execute` and `tools/post-execute`
waterfall events. Pinned Pi defines exactly **one** callback per stage
(`beforeToolCall`/`afterToolCall`); the single-callback case is directly Pi-compatible (same input,
same allowed replacement surface, same failure semantics as Pi's own callback). Minion additionally
supports **N** ordered listeners per stage, composed as a deterministic, registration-order fold --
this is an **intentional Minion architectural extension** pinned Pi does not itself define, not a
"parity-neutral" implementation detail: with more than one listener, execution is observably
different from what a single Pi callback could express, and the disposition is named accordingly
(`L06-R006`; an earlier revision described this inconsistently across the spec, assurance record,
and manifest, sometimes as hardening, sometimes as bare Pi adoption).

Before-hook waterfall: listeners run in registration order; each sees the current validated
arguments (or a prior listener's `Proceed(arguments=...)` replacement) and either delegates
(`next()`, optionally narrowing the arguments) or returns a decision (`Block`/`Proceed`) directly,
short-circuiting the remaining listeners. Pi's own `prepareToolCall` wraps `prepareArguments` +
`validateToolArguments` + `beforeToolCall` in **one** try/catch: a before-hook listener that throws
(rather than returning a structured block) collapses to the same generic error result as a
prepare/validation failure, not a distinct failure class -- true for both the single- and
multi-listener case, since a raised exception unwinds the whole waterfall regardless of how many
listeners were registered. `tools/pre-execute` may additionally replace the arguments a listener
sees (`Proceed(arguments=...)`, e.g. for sandboxing) -- an intentional Minion addition pinned Pi's
`BeforeToolCallResult` has no equivalent for, since Pi's hook can only block or pass through
unchanged; this addition applies identically whether one listener or several are registered.

After-hook waterfall: listeners run in registration order. The recommended registration path,
`register_after_tool_call_hook`, gives each listener the current, already-merged `ToolResult`
(read-only) -- and, when the listener declares its own second parameter for it, the active run's
`signal` too (`L09-R008`: pinned Pi's own `afterToolCall(context, signal)` delivers `signal`
unconditionally; an independent Rust review found the recommended helper delivered it to raw
`tools/post-execute` listeners but not to hooks registered through this constrained path, so a
caller using the intended API could not observe cancellation at all -- arity alone decides which
form a given hook wants, unambiguous here since a hook has only one optional second slot, unlike
`execute()`'s own `wants_signal`/arity split above) -- and expects an `AfterToolCallOverride` (or
`None`/nothing for no change) in return -- **never** the whole result. A one-parameter hook (every
hook written before Layer 09) is called exactly as before, unaffected. `AfterToolCallOverride`
carries exactly Pi's five `AfterToolCallResult`
fields (`content`/`details`/`is_error`/`usage`/`terminate`) and structurally has no slot for
`tool_call_id`, `tool_name`, or `added_tool_names`, so a hook written against this API cannot even
attempt to touch them. But `tools/post-execute` remains a public Runtime event, and a caller may
also register a raw listener directly against it, returning (or short-circuiting with) a whole
`ToolResult` -- the constrained helper alone cannot prevent that (`L06-R003`; an earlier revision
believed it could, which was itself the defect: the helper is a convenience, not enforcement). The
actual authoritative boundary is the production dispatcher itself, and it holds at **every**
listener-to-listener handoff, not only once the whole waterfall finishes: `tool_call_id`,
`tool_name`, and `added_tool_names` are restored from the pre-hook result before each next listener
runs, so no listener -- first, last, or in between, helper-registered or raw -- ever observes a
predecessor's unauthorized replacement of those three fields, even transiently (`L06-R003`, closed
a second time; a still-earlier revision restored them only once, after the entire waterfall
completed, which protected the final result but let an intermediate listener read -- and act on,
e.g. by copying into its own `details` override -- a forged value a prior listener had delegated).
Each listener's override (or a raw listener's own returned value, for the fields it's still allowed
to change) is merged into the accumulated result field-by-field before the next listener runs
(omitted fields keep their prior value; no deep merge -- removing a key requires supplying the
whole replacement value, matching pinned Pi's merge exactly), so listener 2 always sees exactly what
listener 1 produced, **with `tool_call_id`/`tool_name`/`added_tool_names` already normalized back to
their protected values** regardless of what listener 1 attempted. If any listener throws, the
waterfall unwinds and the **entire** prior result -- success or failure, with whatever
`usage`/`details`/`terminate` it carried -- is discarded and replaced with a plain error result;
later listeners never run. This is a replacement, not a merge (`TOOL-017`), and holds identically
for one listener or many, for a helper-registered or raw listener alike, and regardless of
registration order.

`execute(tool_call_id, arguments)` receives the pipeline's own real call id as its first argument,
plus `signal`/`update` parameters when the tool declares them -- matching pinned Pi's
`(toolCallId, params, signal?, onUpdate?)` capability shape and positional order (Layer 09,
`L09-C001`..`L09-C003`, `L09-R001`, `L09-R003`). `signal` is a `RunSignal` (`runtime/signal.py`,
RT-024) -- the READ-ONLY view (`L09-R004`); a tool cannot itself trigger cancellation merely by
holding it.

Capability is DECLARED EXPLICITLY, not inferred from arity alone (`ToolDefinition.wants_signal:
bool = False`, Layer 05, `L09-R003`): pinned Pi's own `signal`/`onUpdate` are INDEPENDENT optional
parameters -- a tool may want either, both, or neither -- and Python's own pre-existing arity-based
`update` detection (3 parameters means `update`, unchanged since before Layer 09) cannot by itself
also distinguish "this 3rd parameter is `signal`" without breaking that established meaning. An
earlier revision tried arity alone (a 4th parameter always meant "signal then update") and could
not represent a tool wanting `signal` WITHOUT `update` at all -- Pi's own signal-only tool had no
Python equivalent, a `PI_PARITY_DEFECT`. The corrected dispatch:

```text
wants_signal   arity   execute(...) receives
False          2       (tool_call_id, arguments)                    -- neither
False          3       (tool_call_id, arguments, update)             -- update only (unchanged)
True           3       (tool_call_id, arguments, signal)             -- signal only
True           4       (tool_call_id, arguments, signal, update)     -- both
```

`wants_signal=False` (every pre-Layer-09 tool) preserves the existing arity dispatch exactly for
both rows; `wants_signal=True` shifts the 3rd-parameter meaning to `signal`, with a 4th (if
declared) receiving `update`. Certified Rust Layer 05 already reserves the matching seam
(`ToolExecutionSignal`, `ToolExecutionRequest.signal` in `minion-agent-rust/crates/minion-agent/
src/tools/definition.rs`), independently of `update` -- Rust's own typed request already
represents all four combinations; Python's `wants_signal` flag closes the same gap.

Before-hook and after-hook waterfalls ALSO receive `signal` explicitly, as a payload argument
before `next_` (`L09-R001`) -- pinned Pi's own `beforeToolCall(context, signal)`/
`afterToolCall(context, signal)` pass it as their own second parameter; Layer 06 has no `instance`
access at all (architecturally below Layer 07, where `AGENT_LIFECYCLE_EVENT`-style listeners
instead read `instance.signal` directly -- see `spec/agent.md`), so this seam threads it
explicitly. `signal` is AUTHORITATIVE event metadata, not a listener's own to replace, redirect, or
drop (`L09-R006`): both waterfalls supply `normalize_step` (`tools/pre-execute`'s own
`_restore_signal`; `tools/post-execute`'s own `_restore`, extended from its pre-existing
`L06-R003` identity restoration) that forces `signal` back to the run's ORIGINAL value at every
listener-to-listener handoff, regardless of what a listener passes when it delegates -- a listener
does not need to re-supply `signal` to preserve it, and cannot override it for a later listener even
by supplying a replacement or omitting it entirely. `register_after_tool_call_hook`'s own wrapper
relies on this: it never re-supplies `signal` when delegating.

A thrown/rejected `execute()` becomes a normal error outcome -- **not** an immediate one -- so it
still flows through the after-hook exactly like success would, and the after-hook runs
UNCONDITIONALLY once `execute()` has been reached, regardless of the signal's own state at any
point during or after `execute()`.

**Preflight abort/error priority (`L09-C002`):** the active run's own signal is checked exactly
ONCE per call, immediately after the before-hook waterfall resolves (whichever decision it
produced), before that decision is examined -- in this exact priority order, earlier wins:

```text
1. tool not found                                     -> "Tool <name> not found"
2. prepare_arguments/validate throws                   -> the exception's own message
3. a before-hook listener throws                       -> the exception's own message
4. before-hook waterfall resolves AND signal is aborted -> "Operation aborted"
   (wins over the waterfall's own Block decision -- the discriminating case is an
   aborted signal plus a Block, not plus a Proceed, since Proceed would reach
   step 6 anyway)
5. before-hook waterfall resolves to Block, not aborted -> the Block's own reason/terminate
6. no listener aborted/blocked                          -> proceeds to execute()
```

Steps 1-3 are checked/raised BEFORE the signal is ever read, so an unknown tool, a validation
failure, or a throwing before-hook listener all keep their own specific error regardless of the
signal's state. Pinned Pi's own `prepareToolCall` has an independent SECOND abort check for the
"no `beforeToolCall` configured at all" case its own single, nullable hook creates; Minion's
`tools/pre-execute` waterfall always runs the same code path whether zero or more listeners are
registered, so ONE checkpoint here covers both of Pi's two -- an intentional, disclosed
architectural mapping, not an observable divergence (the two Pi-distinguishable states, "hook
absent" and "hook ran without blocking/aborting," are the same code path in Minion).

Live updates: `update(partial)` is silently ignored once `execute()`'s own call has settled
(succeeded or failed) -- pinned Pi's `AgentToolUpdateCallback`: "Calls made after the tool promise
settles are ignored." A tool that stashes its `update` callback and invokes it later produces no
observable effect. The update event's payload adopts pinned Pi's own `tool_execution_update`
`AgentEvent` fields verbatim (`IR-L06-005`; a prior revision carried only the call id and the
partial value, exposing strictly less than Pi's own live event stream for no stated architectural
reason): `tool_call_id`, `tool_name`, `arguments`, and the partial value. `arguments` is the
**original**, pre-`prepare_arguments`/validation arguments -- pinned Pi's own
`PreparedToolCall.toolCall.arguments`, confirmed by direct source inspection to be the untouched
call `prepareToolCall` was given, not the `prepareArguments`-shimmed value or the validated one
`execute()` actually runs with.

`partial` itself is **structured** -- `ToolPartialResult` (`tools/result.py`), pinned Pi's own
`AgentToolResult<T>` EXACTLY (`content`/`details` required, `usage`/`added_tool_names`/`terminate`
genuinely optional -- `None` when the tool did not set them, distinguishable from an explicit
falsy/empty value the same way Pi's own `usage?`/`addedToolNames?`/`terminate?` are `undefined`,
not defaulted, when omitted), never a bare string (`L08-R011`, `PI_PARITY_DEFECT` and
`CONTRACT_ASSURANCE_DEFECT`). `ToolPartialResult` is DELIBERATELY NOT `ToolResult` (this module's
own pipeline-level FINALIZED-outcome type): it has NO `tool_call_id`, `tool_name`, or `is_error`
field of its own -- pinned Pi's own `AgentToolResult<T>` has none of those either, since call
identity already lives on the enclosing `tool_execution_update` event
(`tool_call_id`/`tool_name`), and Pi's own `execute()` throws on failure rather than encoding an
error inside its returned/reported value ("Execute the tool call. Throw on failure instead of
encoding errors in `content`," `AgentTool.execute`'s own docstring).

An earlier revision narrowed `ToolUpdate` to `Callable[[str], None]` (a real payload reduction
pinned Pi does not have), then over-corrected to `Callable[[ToolResult], None]`, reusing the
pipeline-level type and normalizing spoofed identity onto it -- an independent Rust re-review
caught this as observably LARGER than Pi's own type, not a harmless superset: a tool could report
an `is_error` or identity pinned Pi has no way to express on a partial value at all. Certified Rust
Layer 06 already used the correct, narrower `AgentToolResult` shape throughout -- Python was the
side that needed correcting, not Rust.

`details` is genuinely required at the Python type level, not merely in prose: `ToolPartialResult`
carries no dataclass default for it, so construction fails without an explicit value (an earlier
revision defaulted it to `{}`, letting `ToolPartialResult(content=())` build successfully and
silently treating "required" as "optional in practice"). Canonical evidence encodes `details`
unconditionally -- a required-but-empty `{}` is always present in observed output, never omitted
as if unset -- and the canonical schema's own `toolPartialResult` definition is CLOSED
(`required: [text, details]`, `additionalProperties: false`), rejecting any shape carrying a
forbidden field (`is_error`, `tool_call_id`, `tool_name`) or missing a required one.

### Batch execution

Effective mode is decided by the batch, not stored on `ToolDefinition` (Layer 05 intentionally
leaves a tool's own `execution_mode: None` to mean "no per-tool preference," never "parallel" --
resolving that fallback is execution's job). The run-level default is `parallel`, matching pinned
Pi's `AgentLoopConfig.toolExecution?` ("Default: parallel"). Contagion: the run-level default being
`sequential`, **or** any tool call in the batch resolving to a tool whose own `execution_mode` is
`sequential`, forces the **entire** batch to run one call at a time in source order -- not merely
that one exclusive call, and not DSH-style partial grouping around it. An unresolvable name is
never exclusive (it never runs, so it has no exclusivity to spread); one typo cannot serialize an
otherwise parallel batch.

**Parallel mode has two phases, not one** (`IR-L06-001`, `CONTRACT_ASSURANCE_DEFECT` +
`PI_PARITY_DEFECT` -- found by independent review against a candidate both languages had already
certified): resolve/`prepare_arguments`/validate/before-hook ("preflight") for **every** call runs
strictly **sequentially**, in source order -- `tool_execution_start` for call 2 never fires before
call 1's own preflight has fully settled -- and only once **every** call in the batch has survived
preflight does `execute()`/the after-hook begin, **concurrently**, for the calls that survived it.
"Parallel" therefore does not mean "every call's complete pipeline begins concurrently"; the
concurrency boundary sits after the before-hook, not before resolution. For two calls A and B:

```text
tool_execution_start(A)
preflight(A)  -- resolve, prepare_arguments, validate, before-hook
tool_execution_start(B)
preflight(B)
-- barrier: every call has now survived (or immediately failed) preflight --
execute(A) / execute(B)  -- concurrent from here
```

An immediate outcome (unknown tool, a prepare/validate/before-hook exception, or an explicit
before-hook block) finalizes -- and emits `tool_execution_end` -- right there in the sequential
phase, before the barrier; it does not enter the concurrent phase, and does not block, delay, or
serialize behind it any later call's own preflight. A prior candidate wrapped each call's entire
pipeline (resolve through after-hook) in one concurrency primitive (Python's `asyncio.gather`,
matching pinned Pi's own `Promise.all` structurally but applied one stage too early) -- which
preflights every call concurrently too, observably different from pinned Pi whenever a before-hook
(or, in principle, `prepare_arguments`/validation) is slow, asynchronous, or order-sensitive across
calls. Both Python and Rust implementations agreed with each other under that candidate, and both
disagreed with Pi -- the reason prior cross-language certification is evidence of implementation
agreement, never semantic authority on its own.

**Abort polling differs by mode (`L09-C001`).** A generic "stop the batch" rule is wrong for
either mode alone -- the two modes poll the active run's own signal at genuinely different points,
matching pinned Pi's own `executeToolCallsSequential`/`executeToolCallsParallel` exactly:

- **Sequential:** the signal is checked AFTER each call's own COMPLETE preflight-through-finalize
  lifecycle, before starting the next call. A call already started always finishes; only calls not
  yet reached are skipped -- the batch's own result count can be shorter than the source call count.
- **Parallel:** preflight remains fully sequential (above, unchanged); the signal is checked after
  EACH call's own preflight OUTCOME (immediate or prepared) is recorded, deciding whether to
  preflight the NEXT source call -- NOT after execution. Every prepared outcome retained BEFORE
  the poll still starts its own `execute()`/after-hook phase afterward, via the same concurrent
  barrier described above, receiving the already-aborted signal cooperatively; an abort arising
  DURING one prepared call's own execution cannot stop a sibling already committed to that barrier.
  Immediate and prepared outcomes remain interleaved in the returned result set in retained SOURCE
  order regardless of which finishes first (unchanged from the ordering rule below).

Discriminating witness (source calls A, B, C; A has no before-hook issue; B's own before-hook
calls `abort()` and returns normally -- a RETURNING hook, not a throwing one, and not a `Block`,
since either of those would win over abort per the preflight priority order above regardless):

```text
tool_execution_start(A)                      -- A preflights normally, retained as prepared
tool_execution_start(B)
  B's before-hook runs, calls abort(), returns
  B's own preflight priority step 4 fires: signal now aborted -> immediate "Operation aborted"
tool_execution_end(B)                        -- emitted inline, during the sequential preflight phase
-- poll after B: signal aborted -> stop preflighting; C's tool_execution_start never fires --
-- barrier: A's retained closure starts, receiving the already-aborted signal cooperatively --
execute(A) / after-hook(A)                   -- A does not check the signal; completes normally
tool_execution_end(A)
-- returned results: A, B in source order; C is entirely absent --
```

Two further orders are normative and different, matching pinned Pi's own `ToolExecutionMode`
docstring verbatim, and apply to the concurrent phase described above: `tool_execution_end` fires
in actual **completion** order; the final `ToolResultMessage` sequence preserves **source**
`ToolCall` order regardless of completion order. Both are true simultaneously in a parallel batch
-- neither is sorted from the other after the fact. Per-call failure is isolated: one call erroring
does not prevent, cancel, or delay its siblings in the same batch (parallel or sequential).

If the originating assistant message's stop reason is `length` (the output was cut off by the
token limit, so every tool call it carries may itself have truncated arguments), **no** tool call
in the batch is resolved, prepared, validated, or executed -- not even an unknown-tool lookup runs.
Each becomes the identical error result, in source order, `tool_execution_start`/`tool_execution_end`
still firing for each; `terminate` is unconditionally `False` for this batch (pinned Pi's
`failToolCallsFromTruncatedMessage` never folds these results through the terminate rule at all).

Batch `terminate=true` only when every finalized result in a non-empty batch sets `terminate` --
an empty batch never terminates (vacuous agreement is not consent). What `terminate=true` does
(suppressing only tool-driven automatic continuation, never normal prepare/stop/steering/follow-up)
is a later Agent-loop layer's obligation, not certified here; Layer 06 only produces and preserves
the flag.

`usage` on a tool result (pinned Pi's `AgentToolResult.usage?`) is preserved end to end into
`ToolResultMessage.usage` and is never folded into main LLM context token accounting (the
already-certified Layer-02 rule). `added_tool_names`, `details`, and `namespace` (pinned Pi's
`ToolCall.namespace?`) are pass-through metadata Layer 06 neither interprets nor requires: a tool
result declaring `added_tool_names` reports what it *registered itself*, through the real
`ToolRegistry`, in the same call -- the field is evidence, not an instruction the pipeline acts on;
`namespace`, if present on a `ToolCall`, is not consulted for resolution and is not echoed into any
Layer-06 event or result. `details` passes through **without collapsing the empty-but-present
state** (`IR-L06-004`, `PI_PARITY_DEFECT`): pinned Pi's `AgentToolResult.details: T` is **required**,
not optional, and `createToolResultMessage` copies it verbatim with no conditional logic at all.
This rule has two distinct halves, and only the first synthesizes a value at all (`CA-L06-007`,
`CONTRACT_ASSURANCE_DEFECT` -- a prior revision of this document conflated them, implying Layer 06
itself derives `{}` for an undeclared *successful* result, which nothing in Pi's execution
pipeline does):

- **Generated errors** (unknown tool, prepare/validate/before-hook failure, after-hook failure,
  length-stop): these are Layer 06's own synthesized `ToolResult`s, built through pinned Pi's
  `createErrorToolResult`, which sets `details: {}` (an empty object, not absent) unconditionally.
  That `{}` survives, unchanged, all the way into `ToolResultMessage.details` for every one of
  these outcomes -- a prior revision's projection instead wrote the equivalent of "empty dict
  becomes absent," which observably diverged from Pi for every such result.
- **Successful results**: `details` is whatever the tool itself returned in its own
  `AgentToolResult` -- preserved verbatim, never synthesized, never defaulted by the execution
  pipeline. A tool that returns no `details` of its own is not a case pinned Pi's own execution
  code assigns any particular value to; a host implementation's own result type may still default
  the field to something (an empty mapping, say) for its own internal convenience, but that is a
  host API choice, not a shared, Pi-derived rule, and canonical evidence must not assert it as one.

`added_tool_names` is the opposite case from `details` and is unaffected by either half above: Pi's
own `createToolResultMessage` conditionally *omits* that key entirely when the array is empty
(`addedToolNames?.length ? {...} : {}`), which Minion's "empty tuple becomes absent" already
matches.

### Explicitly not certified by Layer 06

Cancellation/abort propagation through `execute`/hooks was assurance Layer 09's territory, not
Layer 06's, at THIS row's own Layer-06 certification -- Python then had no `AbortSignal`-equivalent
type at all; certified Rust Layer 05 already reserved one structurally without exercising
cancellation behavior (`L06-R005`). Layer 09 has since REALIZED it (`ToolDefinition.wants_signal`,
`RunSignal`, `L09-R003` -- see `spec/agent.md`'s own consumer/settlement matrix and `AG-007`); this
note is corrected for present tense (`L09-R016`) rather than left describing a gap that no longer
exists. Also not certified by Layer 06: provider-specific constrained-sampling enforcement (Real
Providers, assurance Layer 11), and everything the master's own agent run loop owns:
`prompt()`/`continue()` lifecycle, steering/follow-up message injection,
`shouldStopAfterTurn`/`prepareNextTurn`, and whether a `terminate=true` batch or any other
condition actually suppresses/continues the next model turn.

---

## Layer 13 — Built-in tools

**Status: `WP-13.1` contract fully integrated, pending one complete final contract-convergence
review (`minion-agent#48`): `TOOL-025`/`TOOL-026` `CONTRACT_INTEGRATED` (integration approved,
`minion-agent-docs#156`), `TOOL-028` `CONTRACT_INTEGRATED` (this revision), `TOOL-027`
`NOT_ADOPTED_CORE` (unchanged, see below).** The first independent review
(`minion-agent-docs#133`) returned `CHANGES REQUIRED` with nine findings, `L13-WP131-R001`-`R009`;
the Layer 12 boundary was confirmed `CLEAR`. All nine were remediated across `CE-L13-WP131-01`'s
five-lane convergence episode. Owner decisions: `R002-A`, `R005-A`, and `R010-B` (integrated
into `TOOL-025`/`TOOL-026`, and `R010-B` also into `TOOL-028`); `R007-b` (certified and merged as
`WP-12.E1`/`EXEC-007`); and `R006-C` (collation, owner-selected after an independently replayed
differential). `spec/tools.md` is a single evolving specification; git history is its record,
unlike the revision-numbered `assurance/layers/` artifacts. Owns the
concrete
built-in tools themselves -- their argument schemas, path-argument handling, output/truncation
shapes, and same-target mutation serialization -- as opposed to Layer 05/06's generic
tool-definition/execution framework above, which any tool (built-in or extension-registered) goes
through uniformly. Scoping history, independent review chain, and owner governance decisions live
in `minion-agent#47` (`WP-13.SCOPE`, CLOSED) and its four downstream per-work-package coordination
issues (`minion-agent#48`-`#51`); this section is filled in per work package as each is drafted.

Mirrors pinned Pi's `packages/coding-agent/src/core/tools/` (the full product-level tool set:
`read`, `bash`, `edit`, `write`, `grep`, `find`, `ls` -- `index.ts`'s `allToolNames`), not the
smaller `packages/agent/src/harness/tools/` SDK subset (`bash`/`edit`/`read`/`write` only, built
directly on `ExecutionEnv`). Pi's own `coding-agent` tools do not route through that harness
`ExecutionEnv` abstraction at all -- they call `node:fs/promises` directly, with their own separate
path-resolution pipeline (`utils/paths.ts`), distinct from the harness/`nodejs.ts` resolver Layer
12's `resolve_local_path` already mirrors. Minion's built-in tools intentionally diverge here
(`MINION_ARCHITECTURAL_MAPPING`, not `DIRECT_PI_PARITY`): every built-in tool that touches the
filesystem goes through `ctx.fs` (the certified Layer 12 seam), never a direct local-filesystem
call, because Minion's local/remote/virtual/swappable provider model makes that seam load-bearing
in a way Pi's own single-environment CLI never needed it to be. This is a deliberate design
choice, not an oversight or an incomplete port of Pi's own (itself inconsistent) two-tier
structure.

### WP-13.1 — Native filesystem query tools (`read`, `ls`)

Requirements `TOOL-025`-`TOOL-028` (`minion-agent#48`). No mutation-queue participation, no
`ctx.subprocess` dependency, no external-binary dependency -- the lowest-risk, most independently
certifiable Layer 13 surface (`assurance/layers/13-built-in-tools-scoping-v4.md`).

#### Shared path-argument pipeline (`TOOL-026`)

Every `read`/`ls` `path` argument is resolved through one pipeline before reaching `ctx.fs`:

```text
1. Normalize Unicode space variants -- the CLOSED set U+00A0, U+2000..U+200A,
   U+202F, U+205F, U+3000 -- to ASCII space (U+0020). No other character is
   affected; ordinary ASCII leading/trailing whitespace is NOT trimmed
   (`L13-WP131-R001` correction -- see below).
2. Strip exactly one leading "@", if present.
3. On Windows only: rewrite a Git-Bash/MSYS/Cygwin/WSL-style POSIX drive path
   ("/c/...", "/mnt/c/...", "/cygdrive/c/...") to its native Windows form
   ("C:\...").
4. If the result starts with "file://" (`R002-A`, integrated below): call
   Layer 12's already-certified `_file_url_to_path` conversion DIRECTLY,
   UNWRAPPED -- no exception-suppressing wrapper. A conversion failure
   REJECTS THE CALL IMMEDIATELY, right here in the pipeline, BEFORE any
   `ctx.fs`/provider access is attempted -- it does NOT fall through to
   step 5 with the literal string. A successful conversion replaces the
   pipeline's working value with the converted path and continues to
   step 5 normally.
5. Pass the result as the `path` argument to the appropriate READ-ONLY
   ctx.fs operation directly -- read_text_file / read_binary_file /
   file_info for read; probe_dir_entry / list_dir_raw (EXEC-007) for ls
   (Layer 12, FileSystem Protocol). Tilde expansion,
   absolute-path normalization, and cwd-relative resolution all happen
   INSIDE that provider call, via the SAME already-certified
   resolve_local_path logic every other execution-seam operation uses --
   this pipeline does not reimplement that part of it. (A non-`file://`
   input never reaches step 4's conversion at all; `resolve_local_path`'s
   OWN internal `file://` handling, §3.2, is therefore never exercised by
   this pipeline for a WP-13.1 caller -- step 4 always intercepts first.)
```

**`L13-WP131-R001` correction:** an earlier revision of this pipeline added a mandatory trim step
and described the whole sequence as mirroring `utils/paths.ts:normalizePath`'s option set "exactly."
Pinned Pi's own tool call sites never set `trim: true` -- `path-utils.ts:40-49`/`utils/
paths.ts:75-84` -- so Pi itself preserves leading/trailing ASCII whitespace in a `path` argument;
only the closed Unicode-space set above is normalized. A caller-supplied `" report.txt"` and
`"report.txt"` are two different Pi paths (a directory containing both files makes this
observable: Pi's `read " report.txt"` addresses the space-prefixed file; a version of this
pipeline that trims would silently redirect to the other one). The trim step is removed entirely;
this is `DIRECT_PI_PARITY`, not `MINION_ARCHITECTURAL_MAPPING` -- there was never a reason to
diverge here.

**`L13-WP131-R002` correction:** an earlier revision named `ctx.fs.resolve(path)` (`EXEC-003`) as
the call every preprocessed path goes through. That call is Layer 12's `FsTarget` identity bridge
-- it returns an opaque `target_key` for later same-target comparison (the mechanism `WP-13.2`'s
mutation queue needs), not a resolved path string, and it is not the seam `read_text_file`/
`read_binary_file`/`file_info`/`list_dir` themselves consume (verified directly against
`FileSystem`'s Protocol definition, `minion-agent-python/src/minion_agent/execution/
filesystem.py:487-553`: each of those four operations takes `path: str` directly and performs its
own lexical resolution internally -- `LocalFileSystem.read_text_file`/`list_dir`/etc. all resolve
via `resolve_local_path(self.cwd, path)` exactly as `absolute_path` does). `WP-13.1` has no need
for `FsTarget`/`resolve()`/`process_path()` at all: it calls the four read-only operations directly
with the pipeline's own preprocessed string. `MINION_ARCHITECTURAL_MAPPING`, corrected; no Layer
12 change required -- the defect was entirely in which already-certified operation this contract
named.

**Owner-decided divergence (`TOOL-026`, `R002-A` -- integration of the resolved `CE-L13-WP131-01`
Lane B decision, `minion-agent#48`; corrected this revision, independent review
`minion-agent-docs#156`, `L13-WP131-INT-R002` -- an earlier integration pass conflated `R002-A`
with the rejected `R002-B` alternative's own outcome):** pinned Pi's own two path-resolution
implementations disagree on a malformed `file://` URL. The harness-level resolver Layer 12's
`resolve_local_path` mirrors (`packages/agent/src/harness/env/nodejs.ts:57-62`) catches a
`fileURLToPath` failure and falls through with the literal string unchanged. The `coding-agent`
tool layer's own resolver (`utils/paths.ts:95-97`) does **not** catch that failure --
`fileURLToPath(normalized)` is called unguarded, so pinned Pi's actual `read`/`ls` tools reject
with a raw URL-parsing error for a malformed `file://` path.

**The owner's exact governance text (`minion-agent#48` comment `5769645809`) selected `R002-A`**:
"preserve pinned coding-agent behavior by REJECTING malformed `file://` input through the
already-certified STRICT conversion boundary BEFORE `ctx.fs` filesystem access." This is `R002-A`'s
defining property: the malformed input is rejected IMMEDIATELY, at the pipeline step (step 4,
above) -- it never reaches an ordinary provider filesystem lookup at all. **Mechanism**: Layer 12's
existing, already-certified `_file_url_to_path` conversion function (`filesystem.py:190`, Rust's
equivalent conversion function) is called DIRECTLY, without the exception-suppressing wrapper
`resolve_local_path` normally applies around it -- reusing the identical, unmodified,
already-certified conversion logic, not a new independently-written parser; this requires only that
Layer 12 make the existing function visibility-exposable (e.g. re-exported without its leading
underscore), not a behavioral change or a reopening of Layer 12's own certified characterization.

**Classification**: `_file_url_to_path`'s own failure (a `ValueError`/`OSError` from URL parsing,
never an OS-level filesystem errno at all, since no filesystem call has been made yet) maps to
`FsErrorCode.INVALID` -- the malformed-input condition the certified taxonomy's `invalid` code
exists to represent (`spec/execution.md` §2.1), distinct from a genuine OS-level `not_found`/
`permission_denied`/etc. outcome. Lane B's own characterization explicitly deferred this exact
code/text choice to Lane E (`R002-A`'s "error projection: deferred to `L13-WP131-R010`"); this
integration pass makes that deferred choice concrete now that `R010-B` is decided, rather than
leaving it unresolved. **Final message text** follows `TOOL-025`'s `R010-B` integration below
(governed by manifest row `TOOL-039`, `disposition: intentional divergence`, not by this row's own
`adopted` disposition): the existence/permission-check template, `"Cannot access <path>: invalid
path"` -- this is the SAME "reject before touching `ctx.fs`" checkpoint shape `read`'s own earlier
site uses, applied here to the pipeline's own step-4 rejection.

**`R002-B` (NOT selected -- the platform-dependent fall-through alternative, disclosed for
contrast, not part of this contract):** had the owner instead chosen to let a malformed `file://`
URL fall through to an ordinary provider filesystem lookup (i.e. NOT reject at step 4, matching
`resolve_local_path`'s own default suppress-and-continue behavior), the resulting classification
would have been platform-dependent, confirmed directly on both platforms: Windows -- the malformed
literal fall-through path contains a colon outside drive-letter position, an illegal character at
the OS level, `errno.EINVAL` -> `FsErrorCode.INVALID` (verified directly); POSIX -- the identical
literal fall-through path is an ordinary, syntactically legal (if nonsensical) path component,
`ENOENT` -> `FsErrorCode.NOT_FOUND` (independently verified on Linux/WSL). This platform split is
`R002-B`'s own disclosed consequence, NOT `R002-A`'s -- `WP-13.1` does not reproduce it, since
`R002-A` rejects uniformly (as `invalid`) on every platform, before any platform-dependent
filesystem call would occur.

`@`-prefix stripping happens unconditionally on any leading `@`, matching Pi's CLI `@file`
convention exactly -- a path whose caller genuinely intends a literal leading `@` character has no
way to express that through this pipeline, matching Pi's own behavior (`PI_SOURCE_ALGORITHM`, no
narrower Minion-specific carve-out).

#### `read` (`TOOL-025`)

```text
Input
    path      string, REQUIRED
    offset?   number -- unconstrained (not integer-only, not
              minimum-constrained); see numeric-domain note below
    limit?    number -- same unconstrained domain as offset

Output -- exactly one of the two shapes below, never both, never neither

Text result
    content_blocks
        [0]  text            the model-visible text (selected content,
                              PLUS any continuation/overflow notice
                              appended per the rules below -- one
                              combined string, matching Pi's own single
                              text content block, not a separate
                              "notice" field)
    details.truncation?      present ONLY for automatic truncation or a
                              first-line-byte-overflow outcome (see
                              below); ABSENT for the "user limit stopped
                              early, more remains" outcome even though
                              that outcome also appends a continuation
                              notice to the text
        .truncated           bool
        .truncated_by        "lines" | "bytes" | null
        .total_lines         integer -- line count of the content that
                              was PASSED INTO truncation (i.e. after
                              offset/limit already selected a range) --
                              NOT the whole file's line count
        .total_bytes          integer, same selected-range scope
        .first_line_exceeds_limit  bool

Image result
    content_blocks
        [0]  text     "Read image file [<final mime type after any
                      conversion>]" + hint lines (conversion / resize
                      dimension notes, each its own line) + an optional
                      non-vision note -- ALWAYS present, even on success
        [1]  image    -- ABSENT if image processing failed (see below);
                      present otherwise
            .data         base64-encoded string (NOT raw bytes)
            .mime_type    the FINAL mime type after any BMP-to-PNG
                          conversion and/or resize re-encode -- may
                          differ from the sniffed mime type
```

- **Numeric domain (`L13-WP131-R003` correction):** `offset`/`limit` are pinned Pi's own
  unconstrained `number` schema (`read.ts:21-25`) -- not narrowed to non-negative integers. A
  fractional, zero, or negative value is a VALID input that reaches ordinary array-slice
  arithmetic: `offset` undergoes `Math.max(0, offset - 1)` (so `offset <= 1` and any negative
  value behave identically -- start at line 1; a fractional `offset` like `2.5` produces a
  fractional 0-indexed start that JS array slicing then floors); `limit`, if given, computes
  `Math.min(startLine + limit, allLines.length)` (a negative `limit` can therefore produce an end
  index before the start index, yielding an empty selected range, not an error). This contract
  reproduces that exact unconstrained domain and JS-arithmetic-shaped edge behavior rather than
  narrowing it -- narrowing without owner governance was the defect; matching Pi exactly avoids
  needing a separate governance round.
- `offset`/`limit` are 1-indexed line semantics, applied BEFORE truncation, exactly as in the
  narrowed-domain draft's ordering description (`DIRECT_PI_PARITY`, `read.ts:277-322`): an
  `offset` at or beyond the file's actual line count (post the `Math.max(0, offset-1)` coercion
  above) is a distinguishable input error citing the file's total line count -- this is the ONE
  place a genuinely out-of-range `offset` is rejected rather than silently coerced.
- **Two distinct line-count meanings (`L13-WP131-R004` correction):** Pi's own source has two
  different counts that an earlier revision of this contract collapsed into one `total_lines`
  field. `totalFileLines = allLines.length` is the WHOLE FILE's line count, used only inside the
  continuation-notice TEXT (e.g. `"...Use offset=61 to continue."` math). `details.truncation
  .total_lines` (when present) is the count of the SELECTED range already handed to truncation --
  i.e. AFTER `offset`/`limit` already cut it down -- and can be far smaller than the whole-file
  count. This contract keeps them as two separately-named, separately-scoped values; a language
  implementation MUST NOT conflate them into one field.
- **Result-shape rules, by outcome (`L13-WP131-R004` correction):**
  - Automatic truncation occurred (the selected range exceeds `DEFAULT_MAX_LINES`/
    `DEFAULT_MAX_BYTES`): text is the truncated content plus an exact continuation notice citing
    the shown line range and the whole-file `totalFileLines`; `details.truncation` is present.
  - The single first line alone exceeds the byte limit: text is Pi's actionable diagnostic
    (`"[Line <n> is <size>, exceeds <limit> limit. Use bash: sed -n '<n>p' <path> | head -c
    <limit>]"`) -- NOT empty content, correcting an earlier revision's claim that content is empty
    in this case; `details.truncation.first_line_exceeds_limit` is `true`.
  - A caller-supplied `limit` stopped the selection early AND the file still has more content
    beyond it: text is the selected content plus a DIFFERENT continuation notice (`"[<n> more
    lines in file. Use offset=<next> to continue.]"`); `details.truncation` is **ABSENT** for this
    outcome specifically -- it is a caller-limit boundary, not an automatic-truncation event, and
    Pi's own source does not attach truncation details to it.
  - None of the above: text is exactly the selected content, no notice, no `details`.
- Truncation, when it applies, is from the **head** (keep the first N lines/bytes, never a partial
  line except the single-line-exceeds-limit case above), using the same two-limit-whichever-first
  ceiling as every other Layer 13 tool: `DEFAULT_MAX_LINES = 2000`, `DEFAULT_MAX_BYTES = 51200`
  (50 KiB), both measured UTF-8-byte-accurate, not UTF-16-code-unit-accurate (`DIRECT_PI_PARITY`,
  `truncate.ts`). These two constants are shared Layer 13 constants, not `read`-specific -- restated
  once here, referenced by `TOOL-028`/(bash `TOOL-034`/`TOOL-035`) rather than redefined per tool.
- **Image handling (`L13-WP131-R005` correction):** detection is MIME-sniffed from the first ~4100
  bytes of file content (magic-byte signatures), not the file extension -- the closed sniffed-format
  set is JPEG (a specific malformed-marker byte pattern is explicitly rejected back to non-image),
  non-animated PNG (an `acTL` chunk before any `IDAT` chunk marks an animated PNG, which sniffs as
  NOT an image), GIF, WEBP (RIFF+WEBP container check), and BMP (`detectSupportedImageMimeType`,
  `mime.ts`). Of those five, four (PNG/JPEG/GIF/WEBP) are directly usable inline; BMP is always
  converted to PNG first (`image-process.ts:normalizeImage`); any other sniffed-but-unhandled case
  is unreachable given the closed sniff set above.
  - If conversion (BMP only) or resize (see below) fails, the result is a **text-only success**,
    not a tool error: `content_blocks[0].text` is `"Read image file [<sniffed mime type>]\n[Image
    omitted: could not be converted to a supported inline image format.]"` or the equivalent
    resize-failure message; there is no `content_blocks[1]`.
  - Auto-resize (`autoResizeImages`, default `true`) targets 2000x2000 max dimensions and a 4.5 MiB
    base64-payload ceiling (`image-resize-core.ts` defaults); EXIF orientation is applied before
    measuring/resizing. When resize actually changes dimensions, a hint line states the original
    and displayed dimensions and the scale factor needed to map a model-reported coordinate back to
    the original image. A BMP-to-PNG conversion, independently, adds its own hint line
    (`"[Image converted from bmp to png.]"`).
  - **Semantic authority (`R005-A` -- integration of the resolved `CE-L13-WP131-01` Lane A decision,
    `minion-agent#48` comment `5760619717`; corrected this revision, independent review
    `minion-agent-docs#156`, `L13-WP131-INT-R001` -- an earlier integration pass left the OPPOSITE,
    pre-decision "implementation-delegated" rule in place instead of integrating this one):** the
    owner selected `R005-A`, `semantic authority: PINNED_PHOTON_COMPATIBLE`, pinned Pi dependency
    `@silvia-odwyer/photon-node 0.3.4` and its corresponding `photon_rs_bg.wasm` artifact, with the
    explicit intent of MAXIMUM observable Pi fidelity on `read` image processing -- **NOT**
    implementation-delegated, and **NOT** satisfied by mere visual equivalence or "produces a valid
    image." Scope is the COMPLETE Photon-dependent observable surface: decoder acceptance/rejection,
    EXIF orientation, BMP-to-PNG conversion and its own failure mode, the resize-path's independent
    re-decode, the no-resize fast-path success boundary, the resize/re-encode candidate search, the
    success-versus-text-only-failure boundary, MIME, dimensions, `wasResized`, and the encoded data
    itself -- every one of these is Photon-authoritative, not merely "a reasonable approximation."
    Python and Rust MAY use different binding mechanics ONLY when each mechanically demonstrates
    genuine compatibility with the pinned Photon semantics -- ordinary visual similarity is
    EXPRESSLY insufficient. Before implementation authorization, checkpoint evidence must pin the
    engine/package and underlying artifact, an integrity hash where applicable, and
    behavior-affecting wrapper/runtime versions, plus a differential corpus covering PNG/JPEG/GIF/
    WebP/BMP; boundary dimensions and encoded sizes; EXIF; sniff-positive malformed/rejected inputs;
    BMP conversion failure; both the no-resize and resize paths; multiple resize candidates; and
    candidate-search success/exhaustion -- comparing success/failure branch, MIME, dimensions,
    `wasResized`, and encoded data wherever exact Photon output is authoritative. **If either
    implementation cannot reproduce pinned Photon semantics maintainably, implementation STOPS and
    returns to the owner** -- no silent fallback to a looser fidelity standard is authorized without
    a new governance decision. This decision authorizes contract/checkpoint integration only; it
    does not itself authorize Python implementation, Rust implementation, Layer-12 changes, or
    Layer-14 work.
  - A non-vision-model note, when present, is appended as an additional line in
    `content_blocks[0].text` -- it never replaces or suppresses `content_blocks[1]`; a successfully
    processed image is returned to every requesting model regardless of that model's own vision
    support (`DIRECT_PI_PARITY`, `read.ts:250-270`).
- **Cancellation (`L13-WP131-R008` correction, `read`):** `read` accepts the Layer 09/Layer 06
  cancellation signal. An already-aborted signal at call start rejects immediately with
  `"Operation aborted"` before any filesystem access. Once started, the tool checks the signal
  after path resolution and after the readability-access check (two explicit checkpoints,
  `read.ts:223-249`) in addition to reacting to a live abort event; an abort that fires after the
  file content has already been fully read and processed does not retroactively discard that
  already-completed result -- the checkpoints are pre-completion only, not a post-hoc rejection of
  a settled success.
- `path` not resolving to an existing, readable file is a distinguishable error, separate from any
  truncation/offset outcome (`DIRECT_PI_PARITY`).
- **Error text (`R010-B` -- integration of the resolved `CE-L13-WP131-01` Lane E decision,
  `minion-agent#48`; scope corrected this revision, independent review `minion-agent-docs#156`,
  `L13-WP131-INT-R004` -- an earlier integration pass normatively cross-referenced `TOOL-028`, which
  was then still frozen pending `R006` and was not integrated by that pass; `TOOL-028`'s own
  integration is now in its section below):** pinned Pi's `read.ts`
  authors NO hand-authored error text at all -- every distinguishable `read` failure is a raw or
  hybrid site under Lane E's own characterization
  (`assurance/layers/13-wp131-ce-l13-wp131-01-r010-error-projection.md`). The owner selected
  `R010-B`: raw/hybrid sites use a deterministic, closed Layer-13 vocabulary selected from the
  certified `FsErrorCode` (`spec/execution.md` §2.1) as an internal dispatch key -- never Pi's own
  raw, platform-dependent OS/provider text, and never exposed as a separate structured field
  (`details` remains `{}`, per every generated tool error).

  **Disposition (`L13-WP131-INT-R003`, machine-readable separation -- an earlier revision only
  disclaimed this in prose within `TOOL-025`'s own row, which independent review correctly found
  insufficient):** this error-TEXT normalization on raw/hybrid sites is governed by its OWN,
  SEPARATE manifest row, **`TOOL-039`** (`disposition: intentional divergence`; renumbered from
  `TOOL-029`, which the Layer 13 scoping allocates to `WP-13.2`'s `write` -- an ID correction
  only), NOT by
  `TOOL-025`'s or `TOOL-026`'s own `disposition: adopted`, which describe those tools' core
  Pi-mirroring behavior (schema, truncation, image handling under `R005-A`, cancellation, path
  preprocessing/routing) only. A parity audit checking "does Minion reproduce Pi's error text"
  must consult `TOOL-039`'s own row, not `TOOL-025`/`TOOL-026`'s.

  The closed cause-phrase vocabulary below applies to `TOOL-025`/`read`, to `TOOL-026`'s own
  `R002-A` step-4 rejection above (part of `read`'s and `ls`'s shared pipeline), and to
  `TOOL-028`/`ls`'s raw and hybrid sites, whose exact templates are specified in `TOOL-028`'s own
  error-text subsection below:

  ```text
  FsErrorCode        -> cause phrase
  not_found          -> "no such file or directory"
  permission_denied  -> "permission denied"
  not_directory      -> "not a directory"
  is_directory       -> "is a directory"
  invalid            -> "invalid path"
  not_supported      -> "not supported by this provider"
  unknown            -> "unknown filesystem error"
  ```

  Applied to `read`'s two raw sites (Lane E's own site split):

  ```text
  existence/permission check fails (the earlier, `ops.access`-equivalent site;
  reachable codes: not_found, permission_denied, not_directory, invalid,
  not_supported, unknown):
      "Cannot access <path>: <cause phrase>"

  later content-read step fails (`read_text_file`/`read_binary_file` itself;
  reachable codes: is_directory (the specific addressed-path-is-a-directory
  subcase), plus not_found/permission_denied/not_directory/invalid/
  not_supported/unknown for every other cause):
      "Cannot read <path>: <cause phrase>"
  ```

  And to `TOOL-026`'s own step-4 rejection (`R002-A`, above) -- a malformed `file://` URL, reachable
  code `invalid` only: `"Cannot access <path>: invalid path"` (the SAME template shape as `read`'s
  existence/permission check, since it is architecturally the same kind of
  reject-before-`ctx.fs`-access checkpoint).

  `"Operation aborted"` (uniform, hand-authored, unchanged -- see the cancellation rule above) is
  the sole exception: it is one of Pi's own four stable templates (Lane E), preserved verbatim, not
  a raw/hybrid site subject to this vocabulary.

`TOOL-027` -- Pi's macOS-specific filename-fallback heuristics (narrow-no-break-space AM/PM
substitution, NFD normalization, straight-to-curly-apostrophe substitution, and their
combination, tried in that order only when the initially resolved path does not exist) -- carry
**owner disposition `NOT_ADOPTED_CORE`**, recorded in the shared manifest as `intentional
divergence` (`minion-agent#47`, `minion-agent#48` -- `NOT_ADOPTED_CORE` itself is an owner-facing
label, not a manifest disposition; `pi-parity-manifest.yaml`'s `TOOL-027` row is the binding
record, `L13-WP131-R009` correction). They are `MINION_EXTENSION`/optional UX behavior, not part
of this certified contract. `read` MUST NOT perform these fallback probes as part of its core
behavior. The identifier is reserved, not implemented, so a future optional local-macOS provider
extension can reference it without an ID collision; it imposes no obligation on this contract's
`ctx.fs`-based implementation, which has no inherent concept of "the local machine's own
filename-encoding quirks" for an arbitrary provider.

#### `ls` (`TOOL-028`)

**Status: `CONTRACT_INTEGRATED`, pending the complete `WP-13.1` final contract-convergence review.**
This section integrates three settled decisions: `R006-C` for collation (owner-selected,
`minion-agent#48#issuecomment-5808308811`), `R007-b` for enumeration and the cap, now certified as
`WP-12.E1`/`EXEC-007`, and `R010-B` for error text, plus the frozen `R003` numeric-domain and
`R008` cancellation rules. It replaces the pre-convergence draft, which called `ctx.fs.list_dir`
and disclosed two per-entry divergences. `R007-b` exists to remove those divergences, and this
revision does.

Pinned Pi source: `packages/coding-agent/src/core/tools/ls.ts` at `b7bb00b9`.

```text
Input
    path?     string, default: cwd. An explicit empty string "" is
              equivalent to omitted (Pi: `path || "."`).
    limit?    number, default 500. R003's unconstrained JSON number domain,
              defaulted by nullish coalescing (`limit ?? 500`): only an
              absent/null value takes the default; 0, negatives, and
              fractions are honored literally.

Output (success)
    content_blocks
        [0]  text  -- "(empty directory)" when no entry survives,
                      otherwise the listing plus any notice suffix (below)
    details        -- ABSENT unless a notice applies; then an object with
                      only the fields that apply:
        entry_limit_reached?  number -- the effective limit, verbatim;
                              may be fractional (1.5), never rounded and
                              never the listed count
        truncation?           TruncationResult (same shape as read's
                              details.truncation) -- only when the byte
                              ceiling was hit
```

##### Algorithm

```text
1. Cancellation pre-check (R008, below).
2. Path: run `path` (or "." when omitted or "") through TOOL-026's shared
   pipeline. <path> in every message below is the resolved absolute path of
   the addressed directory, i.e. what ctx.fs.absolute_path returns for the
   pipeline's step-5 string. This corresponds to Pi's `dirPath`.
3. Directory check: ONE ctx.fs.probe_dir_entry(p) call (EXEC-007; follows
   symlinks to classify):
     Ok, kind in {directory, symlink_to_directory}  -> continue
     Ok, any other kind                             -> error "Not a directory: <path>"
     Err(not_supported)                             -> error "Cannot access <path>: not supported by this provider"
     Err(any other code)                            -> error "Path not found: <path>"
4. Enumeration: ctx.fs.list_dir_raw(p) (EXEC-007) returns raw names in
   provider order with no per-entry work.
     Err(aborted)                                   -> "Operation aborted" (R008)
     Err(any other code)                            -> error "Cannot read directory: <cause phrase>"
5. Sort: STABLE sort of the raw names by comparing key(a) with key(b) using
   the pinned collator (Collation, below), where key(x) = the pinned ICU
   root-locale lowercase of x. Ties (compare == 0) keep list_dir_raw order.
6. Entry loop (spec/execution.md §11.5, R007-b), over sorted names in order:
     a. if results.length >= effective_limit: set entry_limit_reached and
        STOP -- this name and every later name are never probed;
     b. otherwise probe_dir_entry(join_path([resolved directory, name])):
          Ok  -> append name + "/" if kind in {directory,
                 symlink_to_directory}, else name alone
          Err -> skip silently; not counted, never surfaced as text
   The appended name is always the RAW list_dir_raw name, never its
   lowercase key.
7. Zero results -> text "(empty directory)", details ABSENT. This holds even
   when 6a fired (limit <= 0 on a non-empty directory): Pi returns before
   building details (ls.ts:180-183).
8. Listing: join results with "\n"; head-truncate to DEFAULT_MAX_BYTES
   (read's shared constant) with no line ceiling (Pi calls truncateHead with
   maxLines = Number.MAX_SAFE_INTEGER, ls.ts:187).
9. Notices, in this order, only those that apply:
     "<L> entries limit reached. Use limit=<2L> for more"   when 6a fired;
                                          sets details.entry_limit_reached = L
     "50.0KB limit reached"               when step 8 truncated; sets
                                          details.truncation (Pi's
                                          formatSize(DEFAULT_MAX_BYTES))
   L is the effective limit. Both L and 2L (computed in IEEE-754 double
   arithmetic) render with ECMAScript Number::toString, e.g. 1.5 -> "1.5",
   3 -> "3". When any notice applies:
     text = truncated listing + "\n\n[" + notices joined by ". " + "]"
   Notices are appended after truncation and are never truncated themselves
   (ls.ts:190-202).
```

**Why one probe reproduces Pi's two-step directory check (step 3).** Pi first calls
`pathExists` (`path-utils.ts:31-38`), which is `access(F_OK)` inside a try/catch. It follows
symlinks and turns every failure into `false`, so Pi reports `"Path not found: <path>"` alike for
a missing path, a broken symlink, a non-directory path component, a component without search
permission, and a symlink loop. A following `stat` fails under those same conditions, so mapping
every `probe_dir_entry` failure to `"Path not found"` reproduces Pi's output
(`DIRECT_PI_PARITY`). Pi's next call, an unwrapped `stat(dirPath)` (`ls.ts:139`), can only fail
if the path changes between the two calls, and then Pi surfaces raw Node text. Minion determines
existence and kind in a single probe, so that race-only raw site has no counterpart
(`MINION_ARCHITECTURAL_MAPPING`). `not_supported` also has no Pi counterpart: it means the
provider lacks the `EXEC-007` extension. It is reported with `R010-B`'s vocabulary instead of
being disguised as a missing path.

**Per-entry parity (step 6).** `probe_dir_entry` follows symlinks exactly as Pi's per-entry
`stat` does (`ls.ts:166-174`). So the two divergences the pre-convergence draft disclosed are
gone:
- A broken symlink or a looping entry fails its probe and is skipped, as in Pi.
- One entry failing no longer fails the whole call.

An entry whose kind is not a directory (a regular file, a symlink to a file, or `other` such as a
FIFO) is listed without `"/"`, as in Pi. The cap is checked before each probe, so a cap can be
reported even when the next, unprobed entry would itself have been skipped. `EXEC-007`'s §11.6
lazy-cap witness makes probing beyond the cap a discriminating failure.

##### Collation (`R006-C`)

Pi sorts with `entries.sort((a, b) => a.toLowerCase().localeCompare(b.toLowerCase()))`
(`ls.ts:155`). No locale is passed, so Pi's order depends on the host's Node/ICU default locale.
Minion pins every part of that comparator:

```text
engines       Python: PyICU 2.16.2.   Rust: rust_icu_ucol 5.8.0, with every
              rust_icu_* crate at 5.8.0.
ICU           ONE build of the official icu4c-78.3-sources.tgz whose SHA-512
              matches the release's own SHASUM512.txt, linked by both
              engines. An implementation MUST fail rather than fall back if
              it would link or load any other ICU. The differential run found
              a stock Debian image silently linking its own ICU 72 development
              library ahead of the pinned build.
collator      locale "en-001"; STRENGTH = TERTIARY   (Intl sensitivity "variant")
                               NUMERIC_COLLATION = OFF (numeric false)
                               CASE_FIRST = OFF        (caseFirst "false")
                               NORMALIZATION_MODE = ON
              default collation, usage "sort"
lowercase     ICU root-locale full lowercase from the same pinned build
              (u_strToLower with locale ""), not the host language's own
              lowercase function
sort          stable; compare(key(a), key(b)); ties keep enumeration order
```

Two parts of this mapping go beyond the owner-selected tuple's stated options. Both are
integration findings, flagged for review, and not yet approved:

- **`NORMALIZATION_MODE = ON`.** ECMA-402 requires canonically-equivalent strings to compare
  equal. On this host (Node 22.15.1, ICU 76.1, `en-001`), Pi's `localeCompare` returns 0 for
  three non-FCD canonically-equivalent pairs. ICU 78.3 with normalization OFF (the setting the
  first differential used, since ICU's default is OFF) compares them as -1. With normalization
  ON it returns 0 for all of them. Without it, `R006-C` would not match Pi on an `en-001` host
  for a name whose combining marks are out of canonical order, contradicting the owner
  decision's own parity disposition. Classified `CONTRACT_ASSURANCE_DEFECT` in the ICU mapping
  of the owner's Intl-level options; those options themselves are unchanged.
- **ICU root-locale lowercase.** Lane C revision 4, Correction 2, found real Unicode-version skew
  in the `toLowerCase` step across Node, Python, and Rust, and required it to be pinned or
  disclosed. ECMA-262 defines `toLowerCase` as Unicode Default Case Conversion, which ICU's
  root-locale lowercase implements. Taking it from the same pinned ICU removes the skew without
  any crate beyond the tuple (`rust_icu_sys` 5.8.0 exposes `u_strToLower`).

Evidence: the first differential (`minion-agent-docs#159`, raw and pre-lowercased 24-name
corpus) and the supplementary v2 differential in
`assurance/layers/data/13-wp131-ce-l13-wp131-01/r006-c-differential-v2/`. v2 used both settings
above with lowercasing done inside each engine, over the 24-name corpus plus 12 normalization and
case-mapping witnesses, and found 0 disagreements across 1,296 ordered pairs per mode. Negative
controls fail as expected. Informationally (Node carries ICU 76.1), the pinned end-to-end order
also equals Pi's own comparator output on this `en-001` host for all 36 strings.

**Parity disposition.** On a host whose effective default locale is `en-001`, this ordering is
intended to match Pi, and the evidence above supports it. Pi itself orders differently on hosts
with another default locale, and Minion does not follow. That is a deliberate, deterministic
`MINION_ARCHITECTURAL_MAPPING`, recorded in its own manifest row `TOOL-040`
(`disposition: intentional divergence`), not inside `TOOL-028`'s `adopted` row.

##### Error text (`R010-B`)

```text
site                                        text                                                 source
directory check fails (step 3, any code     "Path not found: <path>"                            Pi template, verbatim
  except not_supported)
path is not a directory (step 3)            "Not a directory: <path>"                           Pi template, verbatim
directory check Err(not_supported)          "Cannot access <path>: not supported by this        R010-B vocabulary
                                              provider"                                           (Minion-only outcome)
enumeration fails (step 4)                  "Cannot read directory: <cause phrase>"             Pi's wrapper verbatim; its
                                                                                                  embedded raw OS text is
                                                                                                  replaced by the R010-B
                                                                                                  cause phrase
cancellation (R008)                         "Operation aborted"                                 Pi template, verbatim
one entry's probe fails (step 6b)           none -- the entry is skipped
```

`<cause phrase>` comes from the closed `FsErrorCode` table under `read`'s `R010-B` text above,
so `"Cannot read directory: permission denied"` is an example. Every generated `ls` error keeps
the certified `details: {}` shape. The three `ls`-specific templates and the shared abort
template are `TOOL-028`'s own adopted content. The two replacements of raw or hybrid provider
wording (the `not_supported` directory-check text and the `"Cannot read directory"` cause
phrase) are governed by manifest row `TOOL-039` (`disposition: intentional divergence`), the
same row that governs `read`'s raw sites.

##### Cancellation (`R008`, frozen)

- **Cancellation (`L13-WP131-R008` correction, `ls`):** same signal contract as `read` -- an
  already-aborted signal at call start rejects immediately with `"Operation aborted"`; a live abort
  during directory enumeration or per-entry classification rejects the same way (`ls.ts:111-125`).
  `ls` has no equivalent of `read`'s explicit post-access checkpoint; its own listing/classification
  work is the sole interruptible span.

Note, from the pinned source, adding no new rule: Pi attaches its abort listener before the
directory check and removes it only after the entry loop (`ls.ts:125`, `ls.ts:178`). The
interruptible span is therefore steps 3–6. An abort after step 6 completes does not change the
result. `EXEC-007`'s own primitives do not provide mid-call cancellation (spec/execution.md
§11.4), so the tool owns this outer race.

#### Witness matrix (`L13-WP131-R009`, part 1)

Discriminating scenarios an independent language implementation must reproduce; each corresponds
to a `pi-parity-manifest.yaml` `tests:` entry for its requirement (planned canonical scenarios --
no implementation exists yet to run them against, so none are claimed as passing evidence):

```text
TOOL-025 (read)
    read_offset_limit_then_truncation_ordering    100-line file, offset=41,
        limit=20 -> lines 41-60 + "[40 more lines in file. Use offset=61
        to continue.]", details ABSENT (caller-limit-stopped-early case)
    read_first_line_exceeds_byte_limit             single line > 50 KiB ->
        Pi's sed/head diagnostic text, NOT empty content;
        details.truncation.first_line_exceeds_limit = true
    read_offset_out_of_bounds                      offset beyond EOF ->
        distinguishable input error citing total line count
    read_fractional_and_negative_numeric_inputs     offset=2.5, limit=-1 ->
        JS-arithmetic-shaped coercion, not a schema-validation error
    read_image_success_includes_image_for_non_vision_model
        valid PNG + a non-vision model -> content_blocks has BOTH the
        text block (with non-vision note) AND the image block
    read_image_bmp_converts_and_resizes             valid BMP larger than
        2000x2000 -> converted to PNG, resized, both hints present in
        that order
    read_image_processing_failure_is_text_only_success
        an image that sniffs as supported but fails conversion/resize ->
        single text block, no image block, NOT a tool error

TOOL-026 (path pipeline)
    read_leading_ascii_space_not_trimmed            two files " x.txt"/
        "x.txt" -> path=" x.txt" addresses the space-prefixed file
    read_unicode_space_normalized                   path uses U+00A0 in
        place of an ASCII space where the real file uses ASCII space ->
        still resolves to the same file
    read_malformed_file_url_surfaces_as_not_found    a syntactically
        invalid file:// path -> an ordinary FsError, not a URL-parse
        exception (the disclosed divergence above)

TOOL-028 (ls)
    ls_lazy_cap_never_probes_beyond_limit           raw order [z_slow, a_ok],
        limit=1 -> only a_ok is probed; listing "a_ok"; notice "1 entries
        limit reached. Use limit=2 for more"; entry_limit_reached = 1
        (EXEC-007 §11.6 LAZY CAP BOUNDARY)
    ls_entry_limit_checked_before_next_probe        limit=1, the second sorted
        entry would itself fail its probe -> cap still reported after the
        first entry
    ls_zero_limit_on_nonempty_dir_no_details        limit=0, non-empty dir ->
        "(empty directory)", details ABSENT
    ls_fractional_limit_verbatim                    limit=1.5, 3 entries -> 2
        listed; entry_limit_reached = 1.5; "1.5 entries limit reached. Use
        limit=3 for more"
    ls_broken_symlink_entry_skipped                 a broken-symlink entry ->
        absent from the listing and not counted (Pi parity via
        probe_dir_entry)
    ls_symlinked_entries_follow_target_kind         symlink -> directory is
        listed "name/"; symlink -> file is listed "name"
    ls_special_entry_listed_without_slash           a FIFO or other special
        entry (or a provider stand-in reporting kind other) -> listed, no "/"
    ls_path_symlink_to_directory_is_listed          `path` is a symlink to a
        directory -> the target's entries are listed
    ls_missing_path_and_broken_link_path_not_found  missing path, and a path
        that is a broken symlink -> "Path not found: <path>"
    ls_file_path_not_a_directory                    `path` is a regular file
        -> "Not a directory: <path>"
    ls_enumeration_failure_cannot_read_directory    unreadable directory ->
        "Cannot read directory: permission denied", details {}
    ls_provider_without_extension_not_supported     provider lacking EXEC-007
        -> "Cannot access <path>: not supported by this provider"
    ls_byte_truncation_then_notice                  listing over 50 KiB ->
        head-truncated listing + "\n\n[50.0KB limit reached]";
        details.truncation present
    ls_both_notices_in_order                        entry cap and byte ceiling
        both hit -> "[<L> entries limit reached. Use limit=<2L> for more.
        50.0KB limit reached]"
    ls_pre_aborted_signal                           already-aborted signal ->
        "Operation aborted" before any ctx.fs call
    ls_collation_r006c_corpus_order                 the 24-name Part 6 corpus
        in its recorded enumeration order -> the exact order recorded in
        r006-c-differential/results (lowercased mode)
    ls_collation_case_ties_keep_enumeration_order   "apple"/"Apple"/"APPLE"
        in two different enumeration orders -> each order preserved
    ls_collation_canonical_equivalents_tie          a non-FCD canonically-
        equivalent pair keeps enumeration order (compares equal; requires
        NORMALIZATION_MODE = ON)
    ls_lowercase_key_uses_pinned_icu_root_mapping   final sigma, U+0130,
        U+1E9E, U+01C5 -> sort keys equal ICU 78.3 root-locale lowercase
```

### Explicitly not certified by WP-13.1

`write`, `edit`, and the shared mutation queue (`WP-13.2`, `minion-agent#49`); `bash` and its
`ctx.subprocess`-based kill/wait lifecycle (`WP-13.3`, `minion-agent#50`); `find`/`grep` and the
owner-decided exact-pinned-engine strategy (`WP-13.4`, `minion-agent#51`, `TOOL-038`); and every
Layer 06 concern (tool registration/visibility, the per-call pipeline, hook ordering) a built-in
tool participates in identically to any other registered tool, already certified above and not
restated here.
