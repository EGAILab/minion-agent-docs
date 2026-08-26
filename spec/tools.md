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
                             target capability shape; today's dispatch realizes only
                             a (params)/(params, on_update) subset, closing that gap
                             is Layer 06/Layer 09 (cancellation) territory (`TOOL-F003`)
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

After-hook waterfall: listeners run in registration order via `register_after_tool_call_hook`, the
only sanctioned way to extend `tools/post-execute` (`L06-R003`). Each listener receives the
current, already-merged `ToolResult` (read-only) and may return an `AfterToolCallOverride` (or
`None`/nothing for no change) -- **never** the whole result. `AfterToolCallOverride` carries
exactly Pi's five `AfterToolCallResult` fields (`content`/`details`/`is_error`/`usage`/`terminate`)
and structurally has no slot for `tool_call_id`, `tool_name`, or `added_tool_names`: hooks cannot
replace execution identity or `added_tool_names` by construction, not merely by convention (an
earlier, uncertified revision let a listener return/replace the entire `ToolResult`, which could
observably rewrite those fields -- a genuine `CONTRACT_ASSURANCE_DEFECT`, repaired this pass).
Each listener's override is merged into the accumulated result field-by-field before the next
listener runs (omitted fields keep their prior value; no deep merge -- removing a key requires
supplying the whole replacement value, matching pinned Pi's merge exactly), so listener 2 always
sees exactly what listener 1 produced. If any listener throws, the waterfall unwinds and the
**entire** prior result -- success or failure, with whatever `usage`/`details`/`terminate` it
carried -- is discarded and replaced with a plain error result; later listeners never run. This is
a replacement, not a merge (`TOOL-017`), and holds identically for one listener or many.

`execute(tool_call_id, arguments)` receives the pipeline's own real call id as its first argument,
plus an `update` callback appended when the tool declares a third parameter -- matching pinned Pi's
`(toolCallId, params, signal?, onUpdate?)` capability shape except for `signal`. Cross-language
signal state is asymmetric, not uniformly absent (`L06-R005`; an earlier revision incorrectly
claimed "no equivalent type exists in either language"): Python has no `AbortSignal`-equivalent
abstraction yet, but certified Rust Layer 05 already reserves one structurally
(`ToolExecutionSignal`, `ToolExecutionRequest.signal` in
`minion-agent-rust/crates/minion-agent/src/tools/definition.rs`) without exercising cancellation
behavior. The accepted defer is behavioral, not architectural: Layer 06 certifies **non-cancelled**
tool-execution semantics only; assurance Layer 09 owns cancellation propagation, abort timing,
sibling effects, and cancellation result semantics, and can add that behavior later without
changing any non-cancelled stage/ordering/result/event rule this document states, and without
requiring Rust to discard or redesign its existing signal-bearing capability seam. A
thrown/rejected `execute()` becomes a normal error outcome -- **not** an immediate one -- so it
still flows through the after-hook exactly like success would.

Live updates: `update(partial)` is silently ignored once `execute()`'s own call has settled
(succeeded or failed) -- pinned Pi's `AgentToolUpdateCallback`: "Calls made after the tool promise
settles are ignored." A tool that stashes its `update` callback and invokes it later produces no
observable effect.

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

Two orders are normative and different, matching pinned Pi's own `ToolExecutionMode` docstring
verbatim: `tool_execution_end` fires in actual **completion** order; the final `ToolResultMessage`
sequence preserves **source** `ToolCall` order regardless of completion order. Both are true
simultaneously in a parallel batch -- neither is sorted from the other after the fact. Per-call
failure is isolated: one call erroring does not prevent, cancel, or delay its siblings in the same
batch (parallel or sequential).

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
Layer-06 event or result.

### Explicitly not certified by Layer 06

Cancellation/abort propagation through `execute`/hooks (assurance Layer 09 -- Python has no
`AbortSignal`-equivalent type yet; certified Rust Layer 05 already reserves one structurally
without exercising cancellation behavior, `L06-R005`), provider-specific constrained-sampling
enforcement (Real Providers, assurance Layer 11), and everything the master's own agent run loop
owns: `prompt()`/`continue()` lifecycle, steering/follow-up message injection,
`shouldStopAfterTurn`/`prepareNextTurn`, and whether a `terminate=true` batch or any other
condition actually suppresses/continues the next model turn.
