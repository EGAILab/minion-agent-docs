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
