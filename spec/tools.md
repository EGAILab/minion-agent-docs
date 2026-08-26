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
so nothing publishes as "no schema."

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

## Layer 06 — Tool execution pipeline (`NOT CERTIFIED BY LAYER 05`)

**This section describes pre-existing repository code and its intended Pi-parity rules. Its
correctness against pinned Pi is an independent Layer-06 audit obligation** (`process/
implementation-conformance-workflow.md` §6, item 6) — code existing and passing today's tests is
not certification evidence for this layer; those tests may still encode a superseded contract.

Pipeline:

```text
prepare_arguments -> schema validation -> before hook -> execute -> after hook -> finalized result
```

Every thrown/rejected value crossing this Pi-compatible extension boundary becomes an error tool
result. After-hook failure replaces the prior result.

If assistant stop reason is `length`, execute no tool calls; every call becomes an error result.

Sequential contagion: global sequential or any sequential tool => whole batch sequential; otherwise
parallel is allowed.

Parallel execution-end events follow completion order; conversational tool-result messages preserve
source call order. Late updates after settlement are ignored.

Batch `terminate=true` only when every finalized result terminates. It suppresses only tool-driven
automatic continuation; normal prepare/stop/steering/follow-up remains eligible.
