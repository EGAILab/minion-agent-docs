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
    parameters              JSON Schema object
    constrained_sampling?   absent | false | json_schema{strict: prefer|require}
                             | grammar{variants: open-string-keyed map}

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

`constrained_sampling`'s `variants` map is keyed by an open grammar-format string (pinned Pi's own
known values are provider-specific, e.g. `"openai_lark"`/`"openai_regex"`) — never a closed enum,
matching this project's `api`/`provider` rule. Provider-specific enforcement/fallback for
constrained sampling is Real Providers (assurance Layer 11) territory; Layer 05 owns only
preserving the metadata end to end, unmodified, into the model-facing schema.

A tool with no parameter schema still publishes an empty-object schema (`{type: object, properties:
{}}`), never nothing — a model told a tool has no schema has no defined way to call it.

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
section 3). Unloading the owning plugin, or disposing the scope registration
went through, withdraws the tool.

Visibility follows the certified Runtime's own scope rules (section 3),
unmodified by this registry: nearest scope first, then ancestors outward,
untagged (global) registrations last. This order is normative and
observable -- it becomes the tools list in provider request context
(`TOOL-F008`) -- not incidental container iteration order.

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
