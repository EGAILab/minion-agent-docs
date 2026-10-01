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

### Runtime-validation schema string domain (`TOOL-016` / `TOOL-003`, post-certification delta `L05-D001`)

**Status (`minion-agent#104`):** AGREED FOR IMPLEMENTATION. Contract code #106 → `ef7fe40c`, docs #211 → `c624330b`. Python: no production change, implementation review pending. Rust: NOT_IMPLEMENTED.

- **Authorization.** Owner decision on `L0506-D002-R001`, Option 1 (`minion-agent#99` comment `5926416181`). This is a separate Layer-05 delta. It is distinct from `L0506-D002` (prepared instance strings), `L0206-D002` (raw arguments) and `L0206-D001` (key order). No intentional divergence; no whole-Layer-05 reopen.
- **The rule.** A tool's `parameters` schema is a JavaScript object in pinned Pi. Wherever runtime argument validation (`TOOL-003`) consumes one of its string values or object keys, that string is a JavaScript String: any UTF-16 code units, unpaired surrogates included. Registration MUST accept such a schema, and validation MUST honor it as pinned Pi's `validateToolArguments` does, per role:

| Schema-string role | Pinned Pi operation (characterized) |
|---|---|
| `properties` keys and `required` entries | exact UTF-16 identity with the instance key |
| a declared property under `additionalProperties: false` | admits exactly the identical instance key |
| `const`, `enum` literals | exact code-unit sequence equality |
| `propertyNames: {const: S}` | exact code-unit equality of each key |
| `dependentRequired` keys | trigger on the exact instance key |
| `pattern` and `patternProperties` keys, anchored or not (an unanchored `patternProperties` key searches instance keys, `L05-D001-R001`) | a **Unicode-mode RegExp**, not code-unit equality. A valid pair is one code point, so neither half matches inside it (e.g. pattern `\uD83D` does not match the instance `😀`). An unpaired surrogate matches where it genuinely occurs |

Documentary fields (`title`, `description`, `examples`) are not consumed by validation and are outside this rule. `default` is not filled in by Pi's validator.

**Not changed.** Provider/wire schema transport (model-facing schema serialization, Layer 11). The four-domain split (`process/hazard-families.md` F7):

| Domain | Delta |
|---|---|
| this schema domain | `L05-D001` |
| the instance | `L0506-D002` / `L0206-D002` |
| the raw/wire values | `L0206-D002` |
| projections | their own boundaries |

**Representation.**
- **Python.** A `dict` schema holding `str` keys and values (valid pairs combined, unpaired surrogates as surrogate code points). Its validator (`TOOL-003`, Draft 2020-12 via `jsonschema`) already matches pinned Pi on every characterized cell.
- **Rust.** The certified `ToolDefinition.parameters` (`JsonSchemaObject(Map<String, serde_json::Value>)`) cannot hold an unpaired surrogate as a key or string value. A runtime-validation schema representation with a JavaScript-string-capable key and value domain is required. Its validator MUST implement the per-role operations above, including the Unicode-mode `pattern`. The type design is delegated to contract and implementation review (decision §8). `serde_json` limitations are not schema semantic authority.

**Evidence.**
- **Authority:** `minion-agent-docs` `assurance/layers/data/l05-d001-schema-domain/` (characterization `l05-d001-characterization.md`).
- **Canonical scenarios:** `minion-agent` `conformance/agent/schema-domain/` (shape `schema-domain-scenario.schema.json`): 810 cases, which is 10 roles × 9 schema members × 9 instance members. Each case carries its literal schema and arguments as UTF-16 code units, and the runner observes only accept/reject through the real Layer-06 pipeline.
- **Negative controls:**
  - a schema seam that rejects a lone surrogate at registration;
  - schema literals replaced with U+FFFD;
  - a code-unit (non-Unicode) `pattern` search;
  - instance property-name normalization.
- **WP-13.2:** independent. The `write`/`edit` schemas hold only ASCII names and unconstrained `Type.String` slots.

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

### Prepared runtime numeric domain (`TOOL-041`, post-certification delta `L0506-D001`)

**Status (`minion-agent#88`):** CERTIFIED_CLOSED. Python: code #90 → `a993f5d8`, docs #200 → `6076ad35`; RC002 shared correction #96/#205. Rust: code #94 → `ee87245b`, docs #203 → `82184134`, closure review on `minion-agent-docs#203`.

- **Authorization.** Owner decision `L13-WP132-I004`, Option 1 (`minion-agent#49` comment `5912178299`). This is a narrow post-certification extension of the Layer-05/06 runtime domain. Historical Layer-05/06 certification stands outside the surface below, and no intentional divergence is introduced.
- **Origin.** Implementation-review finding `L13-WP132-I004` (`minion-agent-docs#194`):
  - pinned Pi's `edit` preparation can produce a runtime ±Infinity that its before-hook observes;
  - Rust's certified argument type (`serde_json::Value`) cannot hold that value.

**Affected surface.**
- Layer 05: the representation of `prepare_arguments`' result.
- Layer 06: validation of the prepared arguments, the `tools/pre-execute` hook's `arguments`, and the arguments handed to `execute`.

Nothing else changes, in particular:
- the raw `ToolCall.arguments`;
- the original arguments carried by `tool_execution_start`/`tool_execution_update`/`tool_execution_end` (`IR-L06-005`);
- every serialization of a `ToolCall`.

**Two domains.**

```text
raw ToolCall arguments         JSON-compatible, unchanged: what the model sent, what
  (Layer 02 / Layer 05 input)   sessions persist, what tool_execution_* events carry
prepared runtime arguments     Pi's JavaScript runtime values after prepare_arguments:
  (Layer 06 validate -> hooks   the value validation checks, the pre-execute hook sees
   -> execute)                  and execute receives
```

> **Corrected by `L0206-D002`** (`minion-agent#103`; Owner decision `L0506-D002-Q001`). The "raw ToolCall arguments: JSON-compatible" line above is superseded. Pinned Pi's raw arguments are `JSON.parse`'s JavaScript value: unpaired surrogates, `-0` and ±Infinity can already be raw, reaching `tool_execution_*` and the hook with no `prepare_arguments` (`spec/llm.md`, "Raw tool-call argument value domain"). The line is kept as the historical D001 text; D001's prepared-domain rules are unchanged.

A number in the prepared runtime domain is one of:

```text
finite binary64      including -0, whose sign is preserved
+Infinity
-Infinity
NaN                  reachable ONLY through a tool's own prepare_arguments (below)
```

**Reachability, from pinned-Pi characterization** (`#88` comment `5912236809`; authority below).
- **Core preparation.** The only core-Pi preparation that decodes numbers is `edit`'s `prepareEditArguments`, via `JSON.parse`. It produces:
  - ±Infinity for an overflowing number, such as `1e999` or a 400-digit integer;
  - `-0` for `-0`;
  - correctly rounded binary64 otherwise.

  It never produces NaN: `JSON.parse("NaN")` is a `SyntaxError`.
- **A tool's own shim.** A tool's `prepare_arguments` (Pi's public `AgentTool.prepareArguments`) can return any runtime number. Pi's validator keeps NaN in an undeclared key, and the hook observes it. NaN is therefore included because pinned Pi can produce it at this boundary, not merely because a representation could hold it (Owner decision §4).
- **Out of scope.** Non-numeric runtime values a shim could return (`undefined`, functions, dates, big integers) stay outside this delta. The prepared value is otherwise the JSON-shaped object Layer 05 already certifies.

**Validation** (pinned `validateToolArguments`, `typebox` 1.3.7, characterized):

| Prepared value | declared `number` | declared `integer` | undeclared key |
|---|---|---|---|
| +Infinity, -Infinity, NaN | **rejected** | **rejected** | kept |
| -0 | accepted, sign kept | accepted, sign kept | kept |
| finite (e.g. 1e308) | accepted | accepted when integral | kept |

- A declared `number`/`integer` instance is finite-only, which is also JSON Schema's own data model: JSON has no non-finite numbers.
- A binding's validator MUST reject a non-finite value there. It MUST NOT reject, drop, clamp, stringify or null-map one in a position the schema leaves unconstrained.
- **Numeric keywords apply to finite numbers only** (`L0506-D001-RC002`). `minimum`, `maximum`, `exclusiveMinimum`, `exclusiveMaximum` and `multipleOf` constrain a finite number, as JSON Schema defines. A non-finite runtime number is outside them, as it is outside JSON's number model: in a position with no declared `number`/`integer` type, such a keyword neither accepts nor rejects it.
  - Pinned Pi accepts ±Infinity and NaN under `{maximum: 0}`, `{minimum: 0}`, either exclusive bound and `{multipleOf: 2}`. It rejects the finite controls `1`, `-1`, `0`/`-0` and `3`.
  - Through composition the branch verdicts follow. `{oneOf: [{maximum: 0}, {minimum: 1}]}` rejects ±Infinity and NaN, because both branches accept it. `{not: {maximum: 0}}` rejects +Infinity and NaN.
  - A declared type still governs: `{type: number, maximum: 0}` rejects ±Infinity and NaN.
  - A binding MUST NOT compare a non-finite value against a bound.
- Rejection is Layer 06's certified immediate argument-validation error (`TOOL-003`; its text is Layer 06's own).

**Hooks and execute.** The `tools/pre-execute` listener's `arguments` and `execute`'s arguments carry the prepared runtime value exactly, including the sign of zero and non-finite values. A hook's `Proceed(arguments=...)` replacement is certified Layer-06 behavior. It is not extended here beyond carrying the same domain.

**Serialization boundary** (corrected by `L0506-D001-R001`).
- **The successful path serializes no prepared value.** Validation, the hook and `execute` pass the runtime value through in memory. No projection such as `Infinity -> null` applies to them.
- **Pi's validation-failure diagnostic is the one place pinned Pi serializes the prepared value.** Pinned `validateToolArguments` builds its failure text with `JSON.stringify(toolCall.arguments, null, 2)`, and `agent-loop.ts` passes the prepared call. That diagnostic therefore shows ±Infinity and NaN as `null` and `-0` as `0`.
  - The characterization case `declared-number-diagnostic-projection` prepares `{limit: +Infinity, extra: NaN, negativeZero: -0}` against a declared `number` `limit`. Its diagnostic reads `{"limit": null, "extra": null, "negativeZero": 0}`.
  - The prepared runtime values are unchanged by it: still +Infinity, NaN and -0.
  - It is a diagnostic projection, not runtime corruption. Neither the hook nor `execute` runs on that failure.
- **Minion's diagnostic.** Minion's certified validation-error text is its validator's own message (`TOOL-003`). It is not Pi's `Validation failed ... Received arguments: <JSON>` text, and that text parity is not reopened here. Where a binding's validator message mentions a rejected value, it does so in that binding's own rendering, which is not part of the shared contract. No binding may derive a runtime value from that text.
- **Raw `ToolCall` JSON serialization is unchanged.** Any later boundary that serializes prepared values must characterize and specify its own projection.

**Representation.** The contract fixes values, not types.
- **Python.** An integral finite number decoded from JSON is an `int`, as Layer 02 decodes JSON integers. Every other runtime number is a `float`, including `-0.0`, ±`inf` and `nan`.
- **Rust.** It needs a prepared-runtime value representation able to carry these numbers through preparation, validation, hooks and `execute`. The API spelling is Rust's, delegated to its implementation review, and `serde_json::Value` is not the semantic authority for this domain (Owner decision §3).

**Pydantic-model parameters** (a Python-only Layer-05 representation, `TOOL-F010`).
- The same finite-only rule applies to the value Layer 06 delivers: the model's validated `model_dump()`, after the model's one ordinary validation including its own validators.
  - A non-finite number in any position the model's declared types make numeric (`float` or `int`) is rejected, independently of every other position.
  - Only an actual runtime number is judged: a delivered value of another type (for example the string `"Infinity"`) is never converted into one (`L0506-D001-I002`, `CE-L0506-D001-I001-01` rev 4).
  - A union position is numeric only when no finite-only alternative accepts the complete value.
  - Undeclared (extra) keys and positions typed `Any`/`object` are unconstrained. A value outside its declared type is not a numeric position.
  - The check runs no user code, so each user validator runs exactly once. A value a user callback makes finite is judged as delivered (`CE-L0506-D001-I001-01` rev 3).
- Pydantic's own coercion stays the certified, disclosed Layer-06 divergence. In particular, an `int` field coerces `-0.0` to `0`; this is pre-existing and unchanged here, and is disclosed.

**Disclosed cells under the existing `TOOL-003` mapping** ("arguments conform to the supplied JSON Schema", not TypeBox's exact pipeline). These are recorded by `L0506-D001-RC002`; no new divergence is introduced:
- **Number/string coercion**, by exact schema shape and value class:
  - `{type: string}`: pinned Pi coerces any number to its string, a finite `5` to `"5"` and a non-finite value to `"Infinity"`, `"-Infinity"` or `"NaN"`. Both bindings reject.
  - `{anyOf: [{type: number}, {type: string}]}`, in either branch order: a **finite** number already matches the numeric branch, and Pi (`validation.ts` `coerceWithUnionSchema` checks the original value against each branch first), Python and the contract all **accept it unchanged** as a number (e.g. `5`, `1e308`). A **non-finite** number matches no branch, and Pi coerces it to `"Infinity"`, `"-Infinity"` or `"NaN"`. Both bindings reject: these are the six characterized cells (`assurance/layers/data/l0506-d001-ce-i001-01/rev2/`).
  - Other spellings of a numeric/string union (e.g. `type: [number, string]`, which `validation.ts` handles through a distinct `matchesUnionMember` path) are not characterized here, and no claim is made for them.
- **`uniqueItems` with `[0, -0]`.** Pinned Pi accepts, because TypeBox equality distinguishes `-0`. Both bindings reject, as JSON Schema's numeric equality does: `0` and `-0` are equal. `uniqueItems` over repeated ±Infinity or NaN rejects in Pi and in both bindings.

**Evidence** (`assurance/layers/data/l0506-d001/`).
- The pinned-Pi authority covers 58 cases, including the diagnostic-projection case above and the 31 numeric-keyword cases (`L0506-D001-RC002`). For a failure, it records both Pi's diagnostic serialization and the unchanged runtime values. It runs:
  - `agent-loop.ts`'s preparation and `validateToolArguments` unmodified;
  - `edit.ts`'s `editSchema`, sliced from source;
  - the `prepareEditArguments` copy the WP-13.2 authority already uses;
  - `typebox` 1.3.7, SRI-checked.
- Canonical scenarios live in `minion-agent` `conformance/agent/prepared-runtime/`, shape `prepared-runtime-scenario.schema.json`: 5 documents, generated from the authority.
  - They cover the real `edit` path (±Infinity, -0, rounding, largest finite) and a custom shim against declared-number, declared-integer and undeclared positions (±Infinity, NaN, -0, large finite, 0).
  - The runner asserts that the hook and `execute` observe the same token and that the raw arguments are unchanged.
  - The shape has explicit `edit`/`custom` and prepared/failure forms, and a strict token grammar (`L0506-D001-R002`). Its language-neutral PREFLIGHT requires:
    - a prepared case's observed pointers to be exactly its `observe` pointers;
    - every finite literal to denote a finite binary64 value.

    A violation fails the document and is never defaulted.
- **Evidence staging** (`L0506-D001-R003`, acyclic). Every scenario document names its `gate`.
  - **`L0506-D001`: the delta's certification gate.** It is the four custom documents, with 50 cases. They use a tool's own `prepare_arguments` against declared-number, declared-integer and undeclared positions, and (`prepared-runtime-numeric-keyword-applicability`, 31 cases) positions constrained only by numeric keywords, so they run from the accepted Layer-05/06 baseline in every binding. The schema forbids an `edit` case in this gate.
  - **`WP-13.2`: the real-`edit` document, with 8 cases.** It is an integration witness through the real built-in `edit` tool, which lands with WP-13.2, and it is **not** part of this delta's certification.
    - Once `L0506-D001` is certified, WP-13.2's Python approval and Rust implementation reviews run it. It is recorded under `TOOL-030`.
    - Until then it counts as neither passed nor executed for this delta.
  - No runner skips, aliases or simulates a document of the other gate. The delta's runner selects gate `L0506-D001` explicitly.
  - The resulting order is:

    ```text
    L0506-D001 contract -> Python + Rust delta implementations (gate L0506-D001) -> certified
      -> WP-13.2 Python approval (runs gate WP-13.2) -> Rust WP-13.2 (runs gate WP-13.2) -> WP-13.2 closure
    ```
- The negative controls each binding's implementation review must run: Infinity rejected because a type cannot hold it; Infinity mapped to null; clamped to the largest finite value; stringified; `-0` collapsed to `+0`; a hook projection that loses a non-finite value; and a validator accepting a non-finite value in a declared `number` field.

**Known Python defect,** fixed by this delta's Python implementation (`L0506-D001-C001`). Certified Python Layer 06 accepts ±inf and NaN in a declared `number` field, because the `jsonschema` library's `number` admits non-finite floats. The declared-number scenario witnesses it.

### Prepared runtime string domain (`TOOL-041`, post-certification delta `L0506-D002`)

**Status (`minion-agent#99`):** CERTIFIED_CLOSED. Python: no production change; contract code #102 → `28d409d4`, docs #209 → `74f125e3`. Rust: code #108 → `ac661221`, docs #213 → `2d2ba5fc`, closure review on `minion-agent-docs#213`.

- **Authorization.** Owner decision on `WP132-RUST-C001`, Option 1 (`minion-agent#49` comment `5924605017`). This is a narrow post-certification extension of the Layer-05/06 runtime domain, the sibling of `L0506-D001` (numbers). Historical Layer-05/06 certification stands outside the surface below, D001's semantics are not reopened, and no intentional divergence is introduced.
- **Origin.** Rust WP-13.2 implementation finding `WP132-RUST-C001`:
  - pinned Pi's `edit` preparation turns an escaped `\ud800` inside a string `edits` into a lone UTF-16 surrogate;
  - Pi's hooks and `execute` observe it, and the file receives `EF BF BD`;
  - Rust's certified prepared string type cannot hold it.

**Affected surface.** As `L0506-D001`, applied to strings:
- Layer 05: the representation of `prepare_arguments`' result.
- Layer 06: validation of the prepared arguments, the `tools/pre-execute` listener's `arguments`, a listener's `Proceed(arguments=...)` replacement, and the arguments handed to `execute`.

Unchanged: the raw `ToolCall.arguments` (see "Raw domain" below), the original arguments carried by `tool_execution_*` (`IR-L06-005`), and every serialization of a `ToolCall`.

**The domain.** A string in the prepared runtime domain is a **JavaScript String**: a sequence of UTF-16 code units. It is not a Unicode scalar-value string, and no binding's native string type defines it. Every sequence pinned Pi can produce at this boundary is included:

```text
ASCII / BMP non-surrogate code units
a valid surrogate pair (high then low): one astral character
an unpaired high surrogate      at the start, middle, end, or alone
an unpaired low surrogate       at the start, middle, end, or alone
adjacent highs, adjacent lows, low-then-high, high-then-non-low
a pair next to an unpaired surrogate, in either order
the empty string, NUL (U+0000) alone or inside
```

The same domain applies to **object keys** in the prepared value.

**Reachability, from pinned-Pi characterization** (authority below):
- **Core preparation.** `edit`'s `prepareEditArguments` decodes a string `edits` with `JSON.parse`. That turns an escaped valid pair into one astral character, and keeps an escaped unpaired surrogate (`\ud800`, `\udc00`, in any position) as a lone code unit. All 20 neighborhood members are reachable this way.
- **A tool's own shim.** A tool's `prepare_arguments` (Pi's public `AgentTool.prepareArguments`) can return any string, in values and in keys. Pi's validator keeps it, and the hook observes it.

**Observers: one value, never re-encoded.** Pinned Pi hands the **same object** to `beforeToolCall` (`args`), to `execute`, and to `afterToolCall` (`args`). This is characterized by running `agent-loop.ts`' own `prepareToolCall`/`executePreparedToolCall`/`finalizeExecutedToolCall`, sliced from the pinned source.
- In Minion, the `tools/pre-execute` listener and `execute` MUST observe the prepared string's exact code units.
- A `Proceed(arguments=...)` replacement is Minion's own extension. It carries the same domain into `execute`: `execute` observes the replacement's exact code units.
- Minion's `tools/post-execute` carries no arguments (certified Layer-06 surface), so it adds no observer here.
- A binding MUST NOT, anywhere between preparation and `execute`:
  - replace an unpaired surrogate (with U+FFFD or anything else);
  - reject one;
  - re-encode the value through a lossy or strict UTF-8/UTF-16 conversion;
  - split a valid pair into two independent replacement characters;
  - treat high and low surrogates differently;
  - hand the hook and `execute` different values.

**Validation** (pinned `validateToolArguments`, `typebox` 1.3.7; 168 characterized cells):

| Keyword | Rule |
|---|---|
| `type: string` | every member is a string |
| `minLength` / `maxLength` | count **code points**: a valid pair counts 1, and each unpaired surrogate code unit counts 1 (the pair passes `maxLength: 1`; adjacent highs fail it) |
| `pattern` | Unicode mode: `.` matches a valid pair as one character and an unpaired surrogate as one character; NUL is a character |
| `const` / `enum` | exact code-unit sequence equality (the pair matches only the pair; `enum: [U+FFFD]` matches only the real U+FFFD and rejects every unpaired-surrogate instance) |

A rejection is Layer 06's certified immediate argument-validation error (`TOOL-003`). Producing that error MUST NOT fail for any prepared string.

**Instance domain, not schema domain** (`L0506-D002-R001`; Owner decision `minion-agent#99` comment `5926416181`).
- This delta owns the prepared **instance**. The schema it is validated against holds only scalar strings here.
- A non-scalar string **inside the schema** belongs to the separate Layer-05 delta `L05-D001` (`minion-agent#104`). That covers a property name, a `required` entry, a `const`/`enum` literal or a `pattern` holding an unpaired surrogate.
- No certification claim of this delta depends on such a schema literal.
- The scalar schema `enum: [U+FFFD]` is the instance-side discriminator against early replacement: a lone-surrogate instance stays distinct from the real U+FFFD.

**Projection boundaries.** Each conversion of a runtime string into another representation is its own boundary, and replacement happens only there:
- **UTF-8 encoding.** Node's `Buffer.from(s, "utf8")` is `fs.writeFile(path, s, "utf-8")`, which `edit`/`write` use. Each unpaired surrogate code unit becomes `EF BF BD`; a valid pair becomes its 4-byte UTF-8, and NUL becomes `00`. The WP-13.2 tools own this boundary (`spec/tools.md` String semantics).
- **Pi's validation-failure diagnostic** (`JSON.stringify(preparedToolCall.arguments, null, 2)`): each unpaired surrogate is escaped as `\udXXX` (well-formed `JSON.stringify`), NUL as `\u0000`, and a valid pair is emitted as the character itself.
  - The runtime values are unchanged by it. The case `diagnostic/lone-surrogates` records both.
  - Minion's `TOOL-003` text is its own, as for `L0506-D001`.
- **The successful path serializes no prepared string.**
- **Later boundaries, outside this delta.** A string that leaves Layer 06 inside a tool result crosses boundaries owned by later layers. Two are characterized but not certified here:
  - JSON persistence escapes it as above.
  - Pi's provider payloads (`sanitizeSurrogates`, Layer 11) **delete** unpaired surrogates from outbound text.

**Representation.** The contract fixes values, not types.
- **Python.** A `str` in which every valid pair is one astral code point and every unpaired surrogate is a surrogate code point. This is the canonical form `JSON.parse`-equivalent decoding and `utf-16-le`/`surrogatepass` produce. A `str` holding a valid pair as two separate surrogate code points is not a canonical value; it would count 2 under `maxLength`.
- **Rust.** It needs a prepared-runtime string, and a prepared object **key**, able to carry any UTF-16 code-unit sequence losslessly through preparation, validation, hooks and `execute`. Examples are UTF-16 code units, or a WTF-8/WTF-16-capable wrapper. The API spelling is Rust's, delegated to its implementation review. `String`, `String::from_utf16_lossy`, early U+FFFD replacement and rejection are not acceptable (Owner decision §3). Its validation MUST implement the keyword rules above over code units and code points, not over a lossy projection.

**Evidence** (`minion-agent-docs` `assurance/layers/data/l0506-d002/`).
- **The pinned-Pi authority** covers 198 cases:
  - the 21-member neighborhood (the Owner decision's 20 plus the real U+FFFD, `L0506-D002-R001`) × 8 schema kinds;
  - nested-object, array-element and two-string positions;
  - 5 key cases;
  - the diagnostic case;
  - the 21 real-`edit` cases.

  It runs `agent-loop.ts`' preparation/execute/finalize functions sliced from source, unmodified `validateToolArguments` (`typebox` 1.3.7, SRI-checked) and `edit.ts`' `prepareEditArguments`/`editSchema`, sliced from source.
- **Canonical scenarios** live in `minion-agent` `conformance/agent/prepared-runtime-string/`, shape `prepared-string-scenario.schema.json`: 8 documents.
  - Strings are written as arrays of UTF-16 code units, so unpaired surrogates survive the scenario file.
  - The runner asserts that the hook and `execute` observe the same code units (or, for a replacement, the replacement's), and that the raw arguments are unchanged.
  - Its language-neutral PREFLIGHT ties `observed`/`observed_keys`/`execute_observed` to the declared pointers.
- **Evidence staging**, as `L0506-D001-R003`:
  - **`L0506-D002`, the delta's certification gate:** 7 custom documents, 181 cases. That is 168 neighborhood × schema cells, 9 positions/keys/diagnostic cases, and 4 hook-replacement cases. The replacement cases are Minion's extension, and their expectations are the contract's, not Pi's.
  - **`WP-13.2`:** `prepared-string-edit-json-string`, 21 cases through the real `edit` tool, including the final file bytes. Rust WP-13.2's implementation review runs it once this delta is certified; it is **not** part of this delta's certification.
- **The negative controls each binding runs** (Owner decision §6):
  - an unpaired surrogate replaced with U+FFFD during preparation;
  - one rejected during preparation;
  - a strict UTF-8 string conversion failing;
  - a lossy conversion;
  - a valid pair held as two replacement characters;
  - only lone lows mishandled;
  - keys normalized while values are kept;
  - the hook seeing a normalized value while `execute` sees the original;
  - `execute` seeing a normalized value while the hook sees the original.

**Raw domain: outside this delta, an open question.** The Owner decision keeps the raw/wire JSON domain unchanged (§1). The characterization nevertheless shows a sibling hole:
- Pinned Pi's provider decoding (`parseStreamingJson` → `JSON.parse`) puts an escaped unpaired surrogate into the **raw** `ToolCall.arguments`, from which it reaches the hooks without any `prepare_arguments`.
- WP-13.2 already records "lone-surrogate argument decoding (Layer 02/05)" as not certified.
- Whether certified Layer 02/05 must carry such raw strings, and with them the `tool_execution_*` arguments and session persistence, is a governance question. It is raised with the Owner (`L0506-D002-Q001`) and not folded silently into this delta.

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

**Status: `WP-13.1` (`read`, `ls`; `TOOL-025`/`TOOL-026`/`TOOL-028`/`TOOL-039`/`TOOL-040`) CERTIFIED in both
languages (`CERTIFIED_CLOSED`); cross-language closure recorded in `minion-agent#48`.** `TOOL-027` remains
`NOT_ADOPTED_CORE`. Accepted implementations: Python at `minion-agent/main`
`b60f47157965c4aa81c96a20a6105758d33cbf9f` (`minion-agent#60`); Rust at `minion-agent/main`
`9802721fd4099ea6b6b1ecc1396f64889e4a1bc5` (`minion-agent#72`; assurance `minion-agent-docs#171`,
`master` `e2f35bfadb04bb77463f753ac955c6d4aa2f2ba0`). The representation-neutral `TOOL-025` image
correction (`L13-WP131-RUST-I001`) is merged at `master` `074b37f2593c9c87407b67bf6254783171fc4cc7`
(`minion-agent-docs#170`) and `main` `45579e1fe5279d2f2e06e2542fa4f08fdd31d418` (`minion-agent#71`).
This status paragraph is a documentary update only; the contract below is unchanged. The earlier status
record follows.

Earlier status: `WP-13.1` contract merged (docs `b1ed1530`, manifest `cb8ed1c1`); R005-A evidence merged
(`f46051fb`); Python implementation candidate pending independent review, with the
implementation-pass contract repairs `IMPL-C001`-`IMPL-C011` below (`minion-agent#48`). Earlier:
contract fully integrated, pending one complete final contract-convergence
review (`minion-agent#48`): `TOOL-025`/`TOOL-026` `CONTRACT_INTEGRATED` (integration approved,
`minion-agent-docs#156`), `TOOL-028` `CONTRACT_INTEGRATED` (this revision), `TOOL-027`
`NOT_ADOPTED_CORE` (unchanged, see below). The first independent review
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
   ctx.fs operation directly -- check_readable then read_binary_file for
   read (EXEC-008, spec/execution.md §12.5; see "`read`: operation mapping"
   below; L13-WP131-C012); probe_dir_entry / list_dir_raw (EXEC-007) for ls
   (Layer 12, FileSystem Protocol). Tilde expansion,
   absolute-path normalization, and cwd-relative resolution all happen
   INSIDE that provider call, via the SAME already-certified
   resolve_local_path logic every other execution-seam operation uses --
   this pipeline does not reimplement that part of it. (A non-`file://`
   input never reaches step 4's conversion at all; `resolve_local_path`'s
   OWN internal `file://` handling, §3.2, is therefore never exercised by
   this pipeline for a WP-13.1 caller -- step 4 always intercepts first.)
```

**Shared preprocessing versus tool-specific dispatch (`L13-WP132-R002`).**
- Steps 1-4 above are the **shared preprocessing**. Their output is the preprocessed path, and an `R002-A` rejection at step 4 answers before any `ctx.fs` access.
- Step 5 is **each tool's own dispatch**. `read` and `ls` use the read-only dispatch written in step 5, unchanged.
- `write` and `edit` (WP-13.2) consume steps 1-4 only and pass the preprocessed path to their own operations (see WP-13.2). They never go through step 5's read-only dispatch: a new-file `write` does not first ask `check_readable`.

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
            .data         the final image -- its semantic value is the exact
                          final encoded byte sequence; canonically
                          serialized as the standard base64 of those
                          bytes, which is Pi's `data` string. The
                          in-memory form is the Layer 02 binding's own
                          (see "Image representation" below;
                          L13-WP131-RUST-I001, superseding IMPL-C009's
                          bytes-only wording)
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
  `Math.min(startLine + limit, allLines.length)`, and the range is `allLines.slice(startLine,
  endLine)` with `Array.prototype.slice` semantics: fractional indices truncate toward zero and a
  NEGATIVE index counts from the end (IMPL-C008, correcting an earlier revision that said a negative
  `limit` always yields an empty range). A 10-line file with no `offset` and `limit=-3` selects
  lines 1-7 and appends `"[13 more lines in file. Use offset=-2 to continue.]"`; `offset=2.5,
  limit=-1` selects nothing and appends `"[9.5 more lines in file. Use offset=1.5 to continue.]"`.
  None of these is an error. This contract
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
  - "`details` ABSENT" (here and in `TOOL-028`) means the tool returns none of its own `details`
    keys (`truncation`, `entry_limit_reached`). Per Layer 06 (`IR-L06-004`, `CA-L06-007`) a host
    whose result type defaults `details` to an empty mapping satisfies it; canonical evidence
    asserts the absence of the keys, not a representation (IMPL-C007).
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
    the original image. A BMP-to-PNG conversion, independently, adds its own hint line,
    `"[Image converted from image/bmp to image/png.]"` -- base MIME types, exactly as pinned Pi's
    `conversionHint` renders them (IMPL-C011, correcting an earlier revision's `"bmp to png"`).
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
    support (`DIRECT_PI_PARITY`, `read.ts:250-270`). The note is exactly `"[Current model does not
    support images. The image will be omitted from this request.]"`, on both the success and the
    text-only-failure outputs.
  - **Where the model's image support comes from (IMPL-C001, `MINION_ARCHITECTURAL_MAPPING`).** Pi
    reads `ctx?.model` when `execute` runs and adds the note only for a KNOWN model whose `input`
    lacks `"image"` (`getNonVisionImageNote`: no model, no note). Minion tools receive no model
    context, so `read` is constructed with an optional model-capability provider: a function taking
    no arguments, called once per image result at execution time, returning `true` (accepts
    images), `false` (does not) or unknown. Only `false` adds the note; `true`, unknown, and no
    provider at all add none. Whoever composes the tools with an agent supplies the provider from
    the current request's model (Pi's `model.input.includes("image")`, Layer 04's
    `TargetModel.supports_images`).
- **Image representation (`L13-WP131-RUST-I001`, owner decision Option A, `minion-agent#48` comment
  `5852786213`).** The image result is defined by its semantic value -- the final MIME type plus
  the exact final encoded image byte sequence that the accepted image-processing semantics produce
  (including pinned Photon, where `R005-A` makes it authoritative). Two implementations are
  equivalent when they produce the same MIME type and byte-for-byte the same final bytes; a
  cryptographic digest of those exact bytes may serve as the comparison evidence, but the
  requirement is equality of the bytes themselves.
  - **Canonical serialization.** An inline image's serialized `data` is the standard base64
    (RFC 4648 section 4 alphabet, `=` padding, no line breaks or other characters) of exactly those
    bytes -- Pi's observable `ImageContent.data`. Bytes -> canonical base64 -> serialized `data` is
    deterministic.
  - **Binding freedom.** The in-memory representation is the Layer 02 binding's own, since
    `ImageBlock{mime_type,data|reference}` (`spec/llm.md`) does not prescribe it: e.g. Python's
    `ImageBlock.data` holds the decoded bytes, Rust's `ImageSource::Data` holds the canonical base64
    `String`. Any binding is valid if it represents exactly the semantic bytes and serializes them
    canonically. This rule changes no Layer 02 contract or implementation.
  - **Conformance normalization.** A canonical runner MAY convert a binding's certified
    representation to the semantic bytes for comparison (decode canonical base64; take bytes as
    they are). That is representation normalization only: a runner must not resize, transcode,
    repair, reinterpret or otherwise perform the tool's work.
  - **Canonical-serialization witness.** Byte equivalence alone is not enough: every binding's
    evidence must also show that its canonical serialization of the result emits exactly the
    canonical base64 of those bytes (strictly decodable, and re-encoding the decoded bytes
    reproduces the serialized string character for character), so a representation holding
    non-canonical base64 cannot pass because a permissive decoder recovers the same bytes.
- **Cancellation (`L13-WP131-R008` correction, `read`):** `read` accepts the Layer 09/Layer 06
  cancellation signal. An already-aborted signal at call start rejects immediately with
  `"Operation aborted"` before any filesystem access. Once started, the tool checks the signal
  after path resolution and after `check_readable` returns -- in both its NORMAL and FALLBACK modes
  (two explicit checkpoints, `read.ts:223-249`; `CE13-C005`) -- in addition to reacting to a live
  abort event; an abort that fires after the
  file content has already been fully read and processed does not retroactively discard that
  already-completed result -- the checkpoints are pre-completion only, not a post-hoc rejection of
  a settled success.
  **The rejection does not interrupt the work (`L13-WP131-I001`).** Pi rejects the tool's promise
  from the abort listener while its async work carries on: an in-flight `access`/`readFile` is
  neither cancelled nor given the signal, and when it completes the work stops at the next
  checkpoint (`if (aborted) return`), so a file whose access check was in flight at the abort is
  never read. An implementation MUST answer `"Operation aborted"` as soon as it observes the abort,
  MUST NOT cancel or signal the pending `ctx.fs` call (no `ctx.fs` call receives the signal), and
  MUST discard the work's eventual result or failure. (This also follows from the Layer 09 signal
  contract: tool work is never forcibly interrupted.)
  **The outcome is decided by order (`L13-WP131-I001`, `CE-L13-WP131-02`).** If the signal aborted
  before the work reached its settle point (the last synchronous step before its result or failure
  is delivered), the outcome is `"Operation aborted"` -- including when the work then fails (Pi:
  `if (!aborted) reject(error)`); if the work settled first, its result or error stands, even when
  the abort lands before the caller resumes. How soon the rejection is delivered is implementation
  latency and never changes which outcome stands. The same ordering applies to `ls`.
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
  error-text subsection below (and, by owner decision `L13-WP132-O1`, to every other Layer-13
  `ctx.fs`-derived raw or hybrid site -- WP-13.2's are listed in its own "Error text" subsection):

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
  access check fails (`ctx.fs.check_readable`, EXEC-008 -- Pi's `ops.access`;
  reachable codes: every code check_readable returns except not_supported;
  plus, on a provider WITHOUT EXEC-008 only, a content read's
  not_found/permission_denied/not_directory/invalid/unknown -- the
  disclosed fallback F-1):
      "Cannot access <path>: <cause phrase>"

  later content read fails (`read_binary_file`, after check_readable
  answered; reachable codes: all seven -- on a provider without EXEC-008,
  only is_directory and not_supported):
      "Cannot read <path>: <cause phrase>"
  ```

  Which `ctx.fs` failure lands at which of these two sites is fixed by the operation mapping in
  "`read`: operation mapping" below (`L13-WP131-C012`, owner decision `G1`): **the operation that
  failed owns the site, whatever the code** -- `check_readable` is Pi's access stage, so its failure
  is the access site; the content read is Pi's sniff + `readFile`, so its failure is the read site.
  Only a provider without `EXEC-008` falls back to recovering the site from the read's code (F-1).

  And to `TOOL-026`'s own step-4 rejection (`R002-A`, above) -- a malformed `file://` URL, reachable
  code `invalid` only: `"Cannot access <path>: invalid path"` (the SAME template shape as `read`'s
  existence/permission check, since it is architecturally the same kind of
  reject-before-`ctx.fs`-access checkpoint).

  `"Operation aborted"` (uniform, hand-authored, unchanged -- see the cancellation rule above) is
  the sole exception: it is one of Pi's own four stable templates (Lane E), preserved verbatim, not
  a raw/hybrid site subject to this vocabulary.

##### `read`: operation mapping, paths, text and numbers (implementation-pass repairs)

The WP-13.1 Python implementation pass (`minion-agent#48`) found that the integrated contract
left several `read` behaviors that an independent implementation must match either unstated or
misstated. Each is a `CONTRACT_ASSURANCE_DEFECT` (`IMPL-C001`-`IMPL-C011`), repaired here from the
pinned source; none changes an owner decision. Evidence: `assurance/layers/13-wp131-python-implementation.md`.

```text
1. Cancellation pre-check ("Operation aborted", no ctx.fs call).
2. Path: TOOL-026 steps 1-4. A step-4 rejection is "Cannot access <s>: invalid path", where <s>
   is the step-4 input string itself (no ctx.fs call has been made, so there is no resolved path).
   Abort checkpoint (read.ts:246): if the signal has aborted, the work stops here.
3. Access -- Pi's `access(absolutePath)` (read.ts:248), EXEC-008 (L13-WP131-C012, owner G1):
   ONE ctx.fs.check_readable(p) -- no signal (Pi passes none to access):
     Err(not_supported)  -> the provider lacks EXEC-008: FALLBACK mode
     Err(code)           -> "Cannot access <path>: <cause phrase>"    (every other code)
     Ok                  -> NORMAL mode
   Abort checkpoint (read.ts:249): one check, in BOTH modes, before any content work.
   A directory is not decided here: a readable directory passes, an unreadable one fails
   (permission_denied), exactly as Pi's access(R_OK).
4. Content -- Pi's sniff + readFile: ONE ctx.fs.read_binary_file(p) -- no signal:
     NORMAL mode:   Err(code) -> "Cannot read <path>: <cause phrase>"   (every code)
     FALLBACK mode: Err(is_directory | not_supported) -> "Cannot read <path>: <cause phrase>"
                    Err(any other code)               -> "Cannot access <path>: <cause phrase>"
   No other ctx.fs operation is used for access: no file_info, canonical_path, probe_dir_entry
   or list_dir_raw (EXEC-007 stays unused by read).
5. Sniff the first 4100 bytes (below): an image goes to image processing, anything else is text.

<path> = ctx.fs.absolute_path(<step-5 string>) -- Pi's `absolutePath`; if that call itself fails,
the step-5 string.
```

- **Access step history (`IMPL-C002`, then `L13-WP131-C012`).** The integrated contract listed
  `file_info` without saying which failures belong to which site; used alone as the check, a broken
  symlink would pass it and fail at the read, where Pi reports `"Cannot access <path>: no such file
  or directory"` (`IMPL-C002`). The first repair moved the check to `probe_dir_entry`, which
  follows symlinks -- but that is the additive `EXEC-007` extension, which a conforming provider
  may lack (`not_supported`) while still reading content, so `read` would have failed on such a
  provider without ever reading (`L13-WP131-C012`, independent review of docs #162 @ `388c8200`;
  Pi's `access` and `readFile` are independently pluggable, with no such dependency). The mapping
  above keeps `read` on core operations and recovers Pi's site split from the read's own error
  code instead. That code-to-site rule could not tell the two sites apart when the same code
  arises at both (`CE13-C001`..`C004`: an unsupported access step, a permission change or removal
  between the stages, an unreadable directory, a stable I/O error after a successful access), so
  the owner selected `G1` (`minion-agent#48` comment `5822609576`): a Layer-12 readability operation,
  `EXEC-008` `check_readable`, certified in both languages (`minion-agent#62`), now performs Pi's
  access stage, and the failing operation owns the site (`CE-L13-WP131-02` revision 6).
- **Disclosed divergences of that mapping (`CE-L13-WP131-02` revision 5).** On POSIX, and for every
  race between Pi's access and read stages, the sites equal pinned Pi's. W-1: on Windows the access
  site follows `EXEC-008`'s certified readability disposition (a deny ACL -> `permission_denied`, a
  dangling link -> `not_found`) where Pi's attribute-only `access` passes and Pi reports the read
  site. W-2: the Windows symlink-loop CODE is the Layer-12 mapper's (`minion-agent#69`), not
  remapped by `read`. W-3: certified Python `read_binary_file` on Windows classifies a directory read
  as `permission_denied` (Node: `EISDIR`; `minion-agent#67`), so a readable Windows directory reads
  `"Cannot read <path>: permission denied"` -- the site matches Pi, the phrase does not; `read` does
  not work around it. F-1: a provider without `EXEC-008` gets the fallback site mapping above, a
  provider-capability approximation, never Pi-equivalent.
- **Text decoding (`IMPL-C005`).** Text is Node's `Buffer.toString("utf-8")`: each maximal invalid
  UTF-8 subpart becomes one U+FFFD, a byte-order mark is kept, and CR / CRLF are NOT translated.
  Lines split on `"\n"` only, so a `"\r"` stays at the end of its line. (Python's text-mode file
  reading translates newlines; see the Layer 12 finding in the assurance record, which is why `read`
  decodes the bytes of `read_binary_file` itself.)
- **Numbers (`IMPL-C006`).** `offset`/`limit` are IEEE-754 doubles (JSON integers included).
  Every number `read` writes into text -- `"Offset N ..."`, `"Showing lines A-B ..."`,
  `"Use offset=N ..."`, `"[N more lines ...]"`, the first-line diagnostic's line number -- uses
  ECMAScript `Number::toString`: `offset=2.5` produces `"[Showing lines 2.5-..."`.
- **Two different paths in messages (`IMPL-C003`).** Error texts cite `<path>` as defined above.
  The first-line diagnostic's `sed -n '<n>p' <path> | head -c 51200` cites the RAW `path` argument
  exactly as the caller supplied it (`read.ts:300` uses `path`, not `absolutePath`).
- **Fractional offset whose first selected line is too long (`IMPL-C010`).** `read.ts:299` measures
  `allLines[startLine]`; with a fractional `startLine` that is `undefined`, and Node throws
  `TypeError: The "string" argument must be of type string or an instance of Buffer or ArrayBuffer.
  Received undefined`. The result is a tool error with exactly that message text (Node 22.15.1).

##### `read` image processing (normative; `R005-A`, `IMPL-C004`)

Pinned sources: `packages/coding-agent/src/utils/{mime,image-process,image-convert,image-resize,
image-resize-core,exif-orientation}.ts` at `b7bb00b9`. Photon calls go to the pinned
`photon_rs_bg.wasm` (sha256 `10468181565c56004c867f3a4af96f89a0ef5a63a72f2b5fb12c1f1992a3615c`),
which an implementation MUST verify before use and MUST NOT replace with another encoder
(`minion-agent-docs` `assurance/layers/data/13-wp131-ce-l13-wp131-01/r005-a-photon-differential/`).

```text
Sniff (mime.ts), on the first 4100 bytes only:
  FF D8 FF                      -> image/jpeg, except byte 3 == F7 -> not an image
  PNG signature                 -> image/png if bytes 8-11 (big-endian) == 13 and 12-15 == "IHDR"
                                   and no "acTL" chunk precedes the first "IDAT" in the chunk
                                   walk; otherwise not an image. The walk stops (still image)
                                   when the next chunk would start past the sniffed bytes.
  "GIF"                         -> image/gif
  "RIFF" at 0 and "WEBP" at 8   -> image/webp
  "BM" and a valid BMP header   -> image/bmp (length >= 26; declared size 0 or >= 26; pixel offset
                                   >= 14 + DIB size and < declared size when that is non-zero; DIB
                                   12 -> planes/bpp at 22/24, DIB 40..124 -> at 26/28 with length
                                   >= 30; one plane; bpp in {1,4,8,16,24,32})
  Integers are read unsigned; a byte past the end reads as 0.

processImage(bytes, sniffed):
  base = lowercase(trim(sniffed up to ";")); png/jpeg(jpg)/gif/webp are used as is.
  Anything else (BMP) -> convert: decode, EXIF-orient, re-encode as PNG. Failure ->
    "[Image omitted: could not be converted to a supported inline image format.]"
  autoResizeImages false -> the (converted) bytes, hints = [conversion hint] only.
  Otherwise resize (below). null ->
    "[Image omitted: could not be resized below the inline image size limit.]"
  hints, in order: "[Image converted from <base> to <final mime>.]" when converted and the MIME
  changed; then, when resized, "[Image: original WxH, displayed at wxh. Multiply coordinates by
  <toFixed(W/w, 2)> to map to original image.]" (ECMAScript toFixed: the exact binary value
  rounded half away from zero -- 2250/2000 = 1.125 -> "1.13").

resize (resizeImageInProcess; maxWidth = maxHeight = 2000, maxBytes = 4.5 MiB of base64,
jpegQuality = 80):
  decode (Photon new_from_byteslice) and EXIF-orient; W, H = the oriented dimensions.
  If W <= 2000 and H <= 2000 and ceil(len/3)*4 < maxBytes -> the INPUT bytes unchanged,
    not resized.
  Target: if W > maxWidth, h = Math.round(H*maxWidth/W), w = maxWidth; then if h > maxHeight,
    w = Math.round(w*maxHeight/h), h = maxHeight. (Math.round: halves toward +Infinity; exact,
    not floor(x + 0.5).)
  Loop: resize with Lanczos3 (sampling filter 5) to w x h; candidates in order PNG (get_bytes),
    then JPEG (get_bytes_jpeg) at each of [jpegQuality, 85, 70, 55, 40] de-duplicated keeping
    first occurrence; the FIRST whose base64 length is STRICTLY below maxBytes wins (not the
    smallest). None -> stop at 1x1, else w = max(1, floor(0.75w)), h likewise (a side already 1
    stays 1), and repeat.
  Any Photon failure -> null. This includes the zero-sized target: 8001x2 targets 2000x0
    (Math.round(4000/8001) = Math.round(0.49994) = 0), Photon's resize accepts it and the encode traps.

EXIF orientation (exif-orientation.ts): JPEG -- walk markers from offset 2 (skipping FF fill
  bytes); the first APP1 (FF E1) must hold "Exif\0\0", else no orientation; other segments are
  skipped by their big-endian length. WebP -- walk RIFF chunks from offset 12; an "EXIF" chunk's
  TIFF data starts after an optional "Exif\0\0". TIFF: "II" = little-endian; the IFD offset is a
  SIGNED 32-bit read when little-endian and unsigned when big-endian; tag 0x0112's value 1-8 is
  used, anything else is 1. A chunk walk advances by size + (size % 2) with JS `%`. Orientations
  2-8 map to Photon fliph/flipv and a 90-degree pixel rotation rebuilt with Photon new(raw, h, w),
  exactly as the pinned source does.
```

Each Photon operation may run on a fresh instance: the R005-A differential showed instance
lifecycle has no observable effect. A trap inside a borrowing call can leave wasm-bindgen's borrow
flag set on the long-lived instance Pi keeps, but that does not change any output.

`TOOL-025`'s image content block carries the resulting image -- semantically exactly those final
bytes, canonically serialized as their standard base64 -- with the final MIME ("Image
representation" above; `IMPL-C009` as corrected by `L13-WP131-RUST-I001`).

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

Two parts of this mapping go beyond the tuple's originally stated options. Both are now settled:

- **`NORMALIZATION_MODE = ON` (owner-ratified correction to `R006-C`,
  `minion-agent#48#issuecomment-5810098437`; it supersedes only the normalization bit of
  `minion-agent-docs#159`'s evidence).** ECMA-402 requires canonically-equivalent strings to compare
  equal. On this host (Node 22.15.1, ICU 76.1, `en-001`), Pi's `localeCompare` returns 0 for
  three non-FCD canonically-equivalent pairs. ICU 78.3 with normalization OFF (the setting the
  first differential used, since ICU's default is OFF) compares them as -1. With normalization
  ON it returns 0 for all of them. Without it, `R006-C` would not match Pi on an `en-001` host
  for a name whose combining marks are out of canonical order, contradicting the owner
  decision's own parity disposition. Raised as a `CONTRACT_ASSURANCE_DEFECT` in the ICU mapping
  (`INT-F1`); the owner-selected Intl-level options themselves are unchanged.
- **ICU root-locale lowercase (accepted by the independent final review, `INT-F2`).** Lane C
  revision 4, Correction 2, found real Unicode-version skew
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
  work is the sole interruptible span. As for `read` (`L13-WP131-I001`), the rejection does not
  interrupt that work: `ls` has no checkpoints at all, so its in-flight and remaining `ctx.fs` calls
  run to completion and the result is discarded. No `ctx.fs` call receives the signal (Pi's
  `exists`/`stat`/`readdir` take none).

Note, from the pinned source, adding no new rule: Pi attaches its abort listener before the
directory check and removes it only after the entry loop (`ls.ts:125`, `ls.ts:178`). The
interruptible span is therefore steps 3–6. An abort after step 6 completes does not change the
result. `EXEC-007`'s own primitives do not provide mid-call cancellation (spec/execution.md
§11.4), so the tool owns this outer race.

#### Witness matrix (`L13-WP131-R009`, part 1)

Discriminating scenarios an independent language implementation must reproduce; each corresponds
to a `pi-parity-manifest.yaml` `tests:` entry for its requirement. They now exist as canonical
`builtin_tool` scenarios, `minion-agent` `conformance/agent/builtin-*.yaml` (schema
`conformance/schema/builtin-tool-scenario.schema.json`), whose manifest entries name the files;
the implementation pass added `read_text_decoding_matches_node_utf8` and
`read_image_auto_resize_disabled` (TOOL-025), plus a post-Unicode-15.1 case-pair witness for
`ls_lowercase_key_uses_pinned_icu_root_mapping`:

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
    read access/read sites by provenance (L13-WP131-C012, owner G1;
    CE-L13-WP131-02 revision 6, W-G1..W-G16):
    read_error_text_matches_r010b_closed_vocabulary_per_fserrorcode
        check_readable fails with c (every code but not_supported) ->
        "Cannot access <path>: <c>", no content read; check_readable ok,
        then read_binary_file fails with c (all seven, incl. a removal,
        a permission change and a stable I/O error after the check) ->
        "Cannot read <path>: <c>"; real missing file / dangling symlink
        -> Cannot access; real symlink to a readable file -> its text
    read_provider_without_exec_008_uses_disclosed_fallback
        check_readable -> not_supported: a readable file reads normally;
        a failed read is Cannot read only for is_directory/not_supported
    read_abort_at_the_access_checkpoint_normal_mode / _fallback_mode
        the signal aborts as check_readable returns (Ok, or
        not_supported) -> "Operation aborted", no read_binary_file call
    read_does_not_depend_on_file_info_or_canonical_path
        file_info and canonical_path answer not_supported -> read still
        succeeds; ctx.fs calls are check_readable then read_binary_file
    (plus, per language: I001 ordering W-I1..W-I4 -- abort-then-settle is
    "Operation aborted", including a failure after the abort; settle-then-
    abort keeps the result -- and real-host W-G6/W-G11/W-G12)

TOOL-026 (path pipeline)
    read_leading_ascii_space_not_trimmed            two files " x.txt"/
        "x.txt" -> path=" x.txt" addresses the space-prefixed file
    read_unicode_space_normalized                   path uses U+00A0 in
        place of an ASCII space where the real file uses ASCII space ->
        still resolves to the same file
    malformed_file_url_rejected_before_ctx_fs_access_as_invalid
        a syntactically invalid file:// path (e.g. "file:///%ZZ") ->
        rejected at pipeline step 4 by the strict conversion, before
        any ctx.fs call is made (R002-A); classified FsErrorCode
        invalid; text "Cannot access <path>: invalid path"; details {}

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

### WP-13.2 — Filesystem mutation tools (`write`, `edit`) and the shared mutation queue

**Status: CONTRACT_DRAFT (`minion-agent#49`).**

**Requirements:**
- `TOOL-029`: `write`;
- `TOOL-030`: `edit` pipeline, multi-edit matching, diagnostics and result;
- `TOOL-031`: fuzzy matching, unchanged-line preservation, BOM and line endings;
- `TOOL-032`: mutation queue;
- `TOOL-033`: cancellation versus the queue lock.

It also broadens two existing rows:
- `TOOL-026`: `write` and `edit` resolve paths through the same pipeline;
- `TOOL-039`: raw/hybrid `ctx.fs` error projection, extended to Layer 13 by owner decision `L13-WP132-O1`.

**Authorities:**
- Pinned Pi `b7bb00b936dbe21b8e160b3e89efdec361846699`: `packages/coding-agent/src/core/tools/{write,edit,edit-diff,file-mutation-queue,path-utils}.ts` and `packages/coding-agent/src/utils/text.ts`.
- The pinned `diff` package 8.0.4 (Pi's `package-lock.json`, integrity `sha512-DPi0FmjiSU5EvQV0++GFDOJ9ASQUVFh5kD+OzOnYdi7n3Wpm9hWWGfB/O2blfHcMVTL5WkQXSnRiK9makhrcnw==`), specifically its `diffLines` and `createTwoFilesPatch`.
- The pinned runtime, Node 22.15.1 (ICU 76.1, Unicode 16.0), wherever Pi's behavior depends on the JavaScript runtime.

**Governance:**
- Owner decisions `L13-WP132-O1` (E-1) and `L13-WP132-O2` (A-1, refined), recorded at `minion-agent#49` comment `5881558193`.
- The routine lifecycle is delegated to Claude under `minion-agent#75`.

`edit`'s access stage consumes `EXEC-009` (`spec/execution.md` §13, `WP-12.E3`, `minion-agent#79`). WP-13.2 does not claim final `edit` certification before `EXEC-009` is certified.

Like WP-13.1, both tools reach the filesystem only through `ctx.fs` (Layer 12), never a direct host call (`MINION_ARCHITECTURAL_MAPPING`, stated above for all of Layer 13).

#### String semantics (both tools)

Pi's behavior is defined over JavaScript strings, which are sequences of UTF-16 code units. Every rule below is stated in those terms, and a binding MUST reproduce it exactly.

- **Lengths, indices and `indexOf`/`substring`/`slice`** are UTF-16 code-unit measures.
  - A binding with another native string unit MAY compute internally in its own unit only where the result is provably identical. A monotone position mapping preserves every comparison and slice below.
  - A binding MUST use code units wherever a count itself is observable: `write`'s reported length, and `split("")` in the occurrence count.
- **Decoding** file bytes to text is Node's `Buffer#toString("utf-8")`: WHATWG UTF-8 decode, each maximal invalid subpart becomes one U+FFFD, and the BOM is kept. This is the same rule `read` certifies (`IMPL-C005`).
- **Encoding** text to file bytes is Node's `fs.writeFile(path, string, "utf-8")`: WHATWG UTF-8 encode. An unpaired surrogate code unit is written as U+FFFD (`EF BF BD`).
- **Cross-language hazard, recorded rather than resolved here.** Whether a tool argument can contain an unpaired surrogate at all is decided below this layer, by Layer 02/05 argument decoding. The rules above are total for any string a binding does receive.

#### Tool definitions (`TOOL-029`, `TOOL-030`)

The model-visible strings below are verbatim from pinned Pi. They are part of the certified surface.

```text
write
    name         "write"
    label        "write"
    description  "Write content to a file. Creates the file if it doesn't exist, overwrites if it does. Automatically creates parent directories."
    parameters   object, required path and content:
        path     string  "Path to the file to write (relative or absolute)"
        content  string  "Content to write to the file"

edit
    name         "edit"
    label        "edit"
    description  "Edit a single file using exact text replacement. Every edits[].oldText must match a unique, non-overlapping region of the original file. If two changes affect the same block or nearby lines, merge them into one edit instead of emitting overlapping edits. Do not include large unchanged regions just to connect distant changes."
    parameters   object, required path and edits:
        path     string  "Path to the file to edit (relative or absolute)"
        edits    array   "One or more targeted replacements. Each edit is matched against the original file, not incrementally. Do not include overlapping or nested edits. If two changes touch the same block or nearby lines, merge them into one edit instead."
          item   object, required oldText and newText:
            oldText  string  "Exact text for one targeted replacement. It must be unique in the original file and must not overlap with any other edits[].oldText in the same call."
            newText  string  "Replacement text for this targeted edit."
    prepare_arguments  prepareEditArguments (below)
```

- **Schemas.** They follow Pi's TypeBox objects: no `additionalProperties` restriction, no `minItems`. Additional properties are therefore accepted, and an empty `edits` array passes schema validation. `validateEditInput` then rejects it in `execute` (below).
- **Prompt metadata.** `promptSnippet`, `promptGuidelines`, rendering hooks and `constrainedSampling` are Layer 14 (prompt assembly) or UI concerns, and are not certified here.

**`prepareEditArguments` (`edit.ts:116-147`, DIRECT_PI_PARITY).** It runs as Layer 06's `prepare_arguments`, before schema validation (Layer 06 certifies the call order). Given the raw arguments:

```text
1. not an object (or null) -> returned unchanged
2. edits is a string:  JSON-parse it; an array result replaces edits;
                       an object with string oldText and string newText replaces
                       edits with [that object]; a parse error or any other value
                       leaves edits unchanged
   else edits is a single object with string oldText and string newText:
                       edits becomes [edits]
3. top-level oldText and newText are BOTH strings:
       edits := (edits if it is an array else []) + [{oldText, newText}]
       and the top-level oldText/newText keys are removed
   otherwise the (possibly step-2-modified) object is returned as is
```

- A "single edit object" is a non-null, non-array object whose `oldText` and `newText` are both strings. Other keys are allowed and kept.
- Pi mutates the raw argument object in place at step 2. The observable result is the returned value, which Layer 06 then validates; the pre-`prepare_arguments` arguments Layer 06 reports to hooks are Layer 06's own certified concern.
- **Entry domain (`L13-WP132-R005`).** Layer 02/05's certified `ToolCall` arguments are a JSON object, so step 1's non-object branch is unreachable through the tool-call pipeline.
  - A binding's `prepare_arguments` callback still reproduces it when called directly.
  - The authority corpus records it as prepare-helper evidence, not as a canonical integration case.
  - This constrains the entry domain; it does not widen or change any lower-layer vocabulary.

#### Mutation queue (`TOOL-032`)

`write` and `edit` both run their filesystem work inside the shared mutation queue.
- `DIRECT_PI_PARITY` for ordering and key derivation (`file-mutation-queue.ts`).
- `MINION_ARCHITECTURAL_MAPPING` for provider scoping.

```text
with_mutation_queue(fs, p, fn):
  REGISTRATION -- one critical section, globally ordered across ALL pending
  write/edit calls of the process, in call order:
    k = fs.canonical_path(p)                   -- no signal
        Ok(k)                                  -> key = k
        Err(not_found | not_directory | not_supported)
                                               -> key = fs.absolute_path(p)   -- no signal;
                                                  an Err here fails registration
        Err(any other code)                    -> registration fails with it
    link a new entry onto the tail of queue[fs identity][key]
  (registration is SERIALIZED: a later call's registration -- including its
   canonical_path -- does not begin until every earlier registration has SETTLED,
   whether it succeeded or failed. A slow registration that eventually fails
   therefore delays later registrations until it settles (Pi's registrationQueue
   chain awaits it), then raises its error to its own caller, leaves NO entry
   behind, and does not block anything after it has settled -- L13-WP132-R003)
  WAIT until every earlier entry for the same (fs identity, key) has released
  RUN fn
  RELEASE the entry (whether fn returned or raised), and drop the key's queue
  once it is empty
```

- **Call order, not key-resolution order.** Registration takes one global critical section:
  - Two calls for the same target are queued in the order the calls reached registration, even though `canonical_path` is asynchronous I/O. Pi's `registrationQueue` chain serializes exactly the key derivation plus the tail link.
  - Only registration is global. After registration the operations themselves run concurrently for different keys.
- **Key derivation mirrors `getMutationQueueKey` exactly.**
  - It falls back to the lexical absolute path on `ENOENT` and `ENOTDIR`, which are Layer 12's `not_found` and `not_directory`.
  - It additionally falls back on `not_supported`, for a provider that cannot canonicalize (`MINION_EXTENSION`; Pi has no such provider).
  - It deliberately does NOT use Layer 12's `resolve()`, whose fallback set omits `not_directory` (`minion-agent#78`).
- **Provider scoping.** Queues are keyed by the pair (`ctx.fs` instance identity, key). Two different providers never share a queue even when their key strings are equal. Within one provider instance, equal keys share one FIFO.
- **What the key identifies** follows Pi: the canonical, symlink-resolved path when the target exists, and the lexical absolute path when it does not. A symlink and its target therefore share a queue; a not-yet-existing path whose ancestor is a symlink can change key once it is created, which Pi accepts too.
- **Registration failure** (a `canonical_path` or `absolute_path` failure not covered by the fallback) is the tool's error. Its text is under Error text below.
  - It happens before the lock and before any abort check.
  - It delays later registrations only until it settles, and leaves no queue entry (`L13-WP132-R003`).

#### Cancellation (`TOOL-033`, DIRECT_PI_PARITY)

- Neither tool registers an abort listener while it holds the queue lock. After registration and the wait, each tool checks the signal after every awaited step, as listed in its own algorithm (`throwIfAborted`, `"Operation aborted"`).
  - The lock is held until the in-flight filesystem operation has settled, then the abort surfaces.
  - The entry is released on the way out, so a later queued call never starts while an aborted call's own filesystem operation is still running.
- **No filesystem call receives the signal.** Pi passes none to `mkdir`, `writeFile`, `access` or `readFile`.
- **An abort that reaches the tool still registers and waits its turn.** The tool has no check before the lock. An abort arriving during registration or while the call is queued is therefore answered with `"Operation aborted"` only after the call acquires the lock. Registration, including a fallback-key `absolute_path`, completes first.
  - This is the direct `execute` semantics of pinned `write.ts`/`edit.ts`.
  - **Layer 06 boundary (`L13-WP132-R004`).** A signal that is already aborted when the tool call starts never reaches `execute`. Layer 06's certified preflight, mirroring Pi's `agent-loop.ts` `prepareToolCall`, answers `"Operation aborted"` first, with no `ctx.fs` call and no queue registration.
  - Canonical integration evidence therefore witnesses the tool-level rule with an abort that arrives after preflight: `abort_after`, or a queue abort step. It witnesses the preflight rule with a pre-aborted call that expects zero filesystem calls.
- **When a filesystem step fails, its own error wins**, unless the algorithm lists an abort check before that error, as `edit`'s access site does.

#### `write` (`TOOL-029`)

```text
execute(path, content):
  p = preprocess(path)                          -- TOOL-026 steps 1-4 only; an R002-A
                                                  rejection answers here, before registration
  with_mutation_queue(fs, p):                   -- NO provider await before registration
    check abort
    a   = fs.absolute_path(p)                   -- no signal; failure: "Cannot resolve <path>: <cause>"
    dir = the lexical parent directory of a     -- Pi's dirname(absolutePath)
    fs.create_dir(dir, recursive=True)          -- failure: "Cannot create parent directory of <path>: <cause>"
    check abort
    fs.write_file(p, content)                   -- failure: "Cannot write <path>: <cause>"
    check abort
    return text "Successfully wrote <n> bytes to <path>",  details {}
```

- **Where the parent directory comes from (`L13-WP132-R001`).**
  - Pi computes `dirname(resolveToCwd(path))` synchronously, before `withFileMutationQueue`, so nothing can reorder calls ahead of registration.
  - Minion's `absolute_path` is an asynchronous provider operation. Awaiting it before registration could let a later same-target call register first, so it runs INSIDE the lock, immediately after Pi's first abort checkpoint.
  - Pi has no await between that checkpoint and `mkdir`. An abort arriving during `absolute_path` is therefore observed at the next checkpoint after `create_dir`, exactly where Pi observes an abort arriving during `mkdir`.
  - Its failure is practically unreachable, because registration already resolved the same `p`. It uses the registration site's wrapper, `"Cannot resolve <path>: <cause>"`.
- `<n>` is `content`'s length in UTF-16 code units: Pi's `content.length`, even though the message says "bytes". Pi's quirk is reproduced verbatim (`DIRECT_PI_PARITY`, recorded as a known Pi misnomer).
- `<path>` is the argument exactly as given.
- The file is created or overwritten with the UTF-8 encoding of `content` (String semantics above). Missing parent directories are created.
- `details` is Pi's `undefined`, projected as `{}` in canonical evidence.
- Layer 12's `write_file` also creates missing parents. The explicit `create_dir` first keeps Pi's two separately checkpointed steps and their distinct failure sites.

#### `edit` (`TOOL-030`)

```text
execute(input):
  (prepare_arguments and schema validation already ran -- Layer 06)
  if input.edits is not an array or is empty:
      error "Edit tool input is invalid. edits must contain at least one replacement."
  p = preprocess(input.path)                    -- TOOL-026 steps 1-4 only, before registration
  with_mutation_queue(fs, p):
    check abort
    ACCESS  r = fs.check_read_write(p)          -- EXEC-009, no signal
            Err(not_supported)  -> FALLBACK mode (below)
            Err(c)              -> check abort; error "Could not edit file: <path>. <cause(c)>."
    check abort
    READ    bytes = fs.read_binary_file(p)      -- failure: "Cannot read <path>: <cause>"
            raw = UTF-8 decode(bytes)
    check abort
    (bom, content)  = split_bom(raw)
    ending          = detect_line_ending(content)
    normalized      = normalize_to_lf(content)
    (base, new)     = apply_edits(normalized, input.edits, <path>)   -- TOOL-030/031 diagnostics
    check abort
    WRITE   fs.write_file(p, bom + restore_line_endings(new, ending))  -- failure: "Cannot write <path>: <cause>"
    check abort
    return text "Successfully replaced <k> block(s) in <path>."   -- k = number of edits
           details { diff, patch, firstChangedLine }               -- below
```

**FALLBACK mode (provider without `EXEC-009`; `spec/execution.md` §13.5; owner-disclosed, never Pi-equivalent):**
- The access stage calls `check_readable` (EXEC-008) when the provider has it.
  - `Err(c)`, other than `not_supported`, gives the access-site error.
  - When `check_readable` is unsupported too, the access stage is skipped.
- A readable-but-unwritable file then fails at the WRITE site, not the access site.
- Certified first-party providers implement `EXEC-009`, so this mode never applies to them.

**`apply_edits(normalized, edits, path)`** (`applyEditsToNormalizedContent`, DIRECT_PI_PARITY). `n` is the number of edits and indices are 0-based.

```text
1. e[i].old = normalize_to_lf(edits[i].oldText); e[i].new = normalize_to_lf(edits[i].newText)
2. for i in order: e[i].old is empty -> error EMPTY(i)
3. initial[i] = fuzzy_find(normalized, e[i].old) for every i
   used_fuzzy = any(initial[i].used_fuzzy)
   base_for_replacement = fuzzy_normalize(normalized) if used_fuzzy else normalized
4. for i in order:
     m = fuzzy_find(base_for_replacement, e[i].old)
     not m.found                                   -> error NOT_FOUND(i)
     occurrences(base_for_replacement, e[i].old) > 1 -> error DUPLICATE(i, that count)
     record (i, m.index, m.length, e[i].new)
5. sort records by index (stable); for each adjacent pair, if
   prev.index + prev.length > cur.index        -> error OVERLAP(prev.i, cur.i)
6. new = preserve_unchanged_lines(normalized, base_for_replacement, records)  if used_fuzzy
         apply_replacements(base_for_replacement, records)                     otherwise
7. new == normalized                           -> error NO_CHANGE
8. return (base = normalized, new)
```

```text
fuzzy_find(content, old):
    j = content.indexOf(old)
    j >= 0 -> found, index j, length old.length, used_fuzzy = false
    otherwise: fc = fuzzy_normalize(content); fo = fuzzy_normalize(old); j = fc.indexOf(fo)
    j >= 0 -> found, index j, length fo.length, used_fuzzy = true
    else   -> not found

occurrences(content, old):
    = (number of pieces of fuzzy_normalize(content).split(fuzzy_normalize(old))) - 1
      -- ALWAYS counted in fuzzy space, even when the exact match succeeded: an exactly
         unique oldText can still be rejected as DUPLICATE when its normalized form
         repeats (DIRECT_PI_PARITY)
      -- JavaScript String.prototype.split semantics: non-overlapping occurrences, left to
         right. When fuzzy_normalize(old) is the EMPTY string (e.g. old is only
         trailing whitespace), split("") yields one piece per UTF-16 code unit, so
         occurrences = (code units of the normalized content) - 1, and -1 for empty content

apply_replacements(content, records):
    apply records in descending index order: content = content[..index] + new + content[index+length..]
```

**Diagnostics** (Pi's templates, verbatim; `<path>` is the argument as given):

```text
EMPTY(i)          n == 1: "oldText must not be empty in <path>."
                  n >  1: "edits[<i>].oldText must not be empty in <path>."
NOT_FOUND(i)      n == 1: "Could not find the exact text in <path>. The old text must match exactly including all whitespace and newlines."
                  n >  1: "Could not find edits[<i>] in <path>. The oldText must match exactly including all whitespace and newlines."
DUPLICATE(i, c)   n == 1: "Found <c> occurrences of the text in <path>. The text must be unique. Please provide more context to make it unique."
                  n >  1: "Found <c> occurrences of edits[<i>] in <path>. Each oldText must be unique. Please provide more context to make it unique."
OVERLAP(a, b)     "edits[<a>] and edits[<b>] overlap in <path>. Merge them into one edit or target disjoint regions."
NO_CHANGE         n == 1: "No changes made to <path>. The replacement produced identical content. This might indicate an issue with special characters or the text not existing as expected."
                  n >  1: "No changes made to <path>. The replacements produced identical content."
INTERNAL          "Replacement range is outside the base content."
                  "Cannot preserve unchanged lines because the base content has a different line count."
```

- The two INTERNAL texts are Pi's own guards in `preserve_unchanged_lines`. They are reproduced if reached, and the differential corpus looks for inputs that reach them.
  - The authority corpus reaches BOTH.
  - The range guard fires on an empty file whose `oldText` is only whitespace.
  - The line-count guard fires under fuzzy mode when the file ends in a whitespace-only line without `"\n"`: that line trims to nothing and `lines()` drops it, so the base has one line fewer. An ordinary edit therefore fails with Pi's internal text, e.g. `"a’\n   "` edited with `oldText` `"a'"`. This is `DIRECT_PI_PARITY` and is reproduced as is.
- Every diagnostic is an error result with `details: {}`.

#### Fuzzy matching, unchanged-line preservation, BOM and line endings (`TOOL-031`, DIRECT_PI_PARITY)

```text
split_bom(s):             s starts with U+FEFF -> ("﻿", s without it) else ("", s)
detect_line_ending(s):    no "\n" in s                     -> "\n"
                          no "\r\n" in s                   -> "\n"
                          first "\r\n" before first "\n"   -> "\r\n"   else "\n"
normalize_to_lf(s):       every "\r\n" -> "\n", then every remaining "\r" -> "\n"
restore_line_endings(s,e): e == "\r\n" -> every "\n" -> "\r\n"; else s unchanged
```

These reproduce Pi's quirks exactly:
- When CRLF comes first, every line break, including a lone CR that `normalize_to_lf` turned into LF, is written back as CRLF.
- When LF comes first, every CRLF in the file is written back as LF.

```text
fuzzy_normalize(s):
  1. NFKC normalization of s  -- Unicode 16.0 exactly (Node 22.15.1's ICU 76.1; see below)
  2. split on "\n"; remove trailing JavaScript whitespace from each line; join with "\n"
  3. U+2018 U+2019 U+201A U+201B                      -> "'"
  4. U+201C U+201D U+201E U+201F                      -> '"'
  5. U+2010 U+2011 U+2012 U+2013 U+2014 U+2015 U+2212 -> "-"
  6. U+00A0, U+2002..U+200A, U+202F, U+205F, U+3000   -> " "
```

- **"JavaScript whitespace"** (`String.prototype.trimEnd`) is exactly ECMAScript's WhiteSpace and LineTerminator set, and nothing else. That is: U+0009, U+000B, U+000C, U+0020, U+00A0, U+FEFF, the Unicode `Zs` characters (U+1680, U+2000..U+200A, U+202F, U+205F, U+3000), and U+000A, U+000D, U+2028, U+2029.
  - A binding's own "strip whitespace" routine MUST NOT be used unless it has exactly this set. For example, Python's `str.rstrip()` also strips U+001C..U+001F and U+0085, and differs.
- **Unicode authority.** Pi's `String.prototype.normalize("NFKC")` uses the runtime's ICU. The pinned runtime, Node 22.15.1, is ICU 76.1 / Unicode 16.0, and that is the required version.
  - Measured over every code point: Python's `unicodedata` (Unicode 15.1) differs on 36 code points (U+1CCD6..), and ICU 78.3 (Unicode 17.0) differs on exactly one (U+A7F1).
  - A conforming implementation uses the already-pinned ICU4C 78.3 (`R006-C`), restricted to Unicode 16.0: ICU's filtered normalizer over `[:age=16.0:]`, under which a code point unassigned in 16.0 passes through unchanged. Any other mechanism MUST be proven equal over all code points, and over the multi-code-point composition corpus below.

**`preserve_unchanged_lines(original, base, records)`** (`applyReplacementsPreservingUnchangedLines`). It is used only when `used_fuzzy`. `original` is the LF-normalized file text; `base` is its fuzzy-normalized form.

```text
lines(s)       = the regex match list /[^\n]*\n|[^\n]+/g over s -- each line WITH its "\n";
                 an empty s has no lines; a final line without "\n" is kept
O = lines(original); B = spans of lines(base) (start/end offsets in base)
|O| != |B|     -> error INTERNAL (line count)
group the records (sorted by index) by the base lines they touch:
    a record's line range = [the line containing its index,
                             the first line whose end >= index + length] (inclusive)
    -- no line contains the index, or none reaches the end -> error INTERNAL (range)
    groups use an EXCLUSIVE end line (last touched line + 1); a record whose start
    line < the current group's exclusive end line joins that group (the group's end
    becomes the max of both); otherwise it starts a new group
    -- a zero-length match (fuzzy_normalize(old) empty, index 0) against an EMPTY base
       lies in no line and raises INTERNAL (range): reachable (an empty file with an
       oldText of only trailing whitespace), and witnessed
output = for each group in order: the ORIGINAL lines before the group (verbatim),
         then apply_replacements over base[group start offset .. group end offset]
         (records rebased to the group's start offset);
         then every ORIGINAL line after the last group (verbatim)
```

Lines no edit touches are copied byte for byte from the original. Fuzzy normalization never rewrites them.

#### `edit` result details: `diff`, `patch`, `firstChangedLine`

- **`patch`** = `createTwoFilesPatch(<path>, <path>, base, new, undefined, undefined, {context: 4, headerOptions: FILE_HEADERS_ONLY})` of the pinned `diff` 8.0.4. This is Pi's `generateUnifiedPatch`.
- **`diff`** and **`firstChangedLine`** = Pi's `generateDiffString(base, new)` with 4 context lines, over that package's `diffLines(base, new)` with no options.
- Both are `DIRECT_PI_PARITY` and are reproduced as algorithms, not approximated:
  - the `diffLines` tokenizer: split on `\n`/`\r\n`, separators merged into the preceding line, a trailing empty token dropped, empty tokens removed;
  - its Myers search, including jsdiff's diagonal pruning (`minDiagonalToConsider`/`maxDiagonalToConsider`), the branch choice `!canRemove || (canAdd && removePath.oldPos < addPath.oldPos)`, and component merging in `addToPath`/`extractCommon`/`buildValues`;
  - `structuredPatch`'s hunk building: context 4, overlapping-context joins when a common run is at most 8 lines, and closing context;
  - its trailing-newline handling: `\ No newline at end of file`;
  - `formatPatch`: `--- <path>` / `+++ <path>` headers with no timestamps, the zero-length-hunk start adjustment, and a final `\n`;
  - Pi's own `generateDiffString` formatting: `+`/`-`/space marker; the line number right-aligned to the digit width of `max(base.split("\n").length, new.split("\n").length)`, a count that includes a trailing empty piece; the ellipsis line; and context trimming around each change.
- `firstChangedLine` is the new-file line number of the first added or removed part. It is always present: `NO_CHANGE` rules out an unchanged result.
- The package is used exactly as Pi calls it: synchronous, no timeout, no `maxEditLength`. The algorithm is deterministic.

#### Error text (`TOOL-039`, extended by `L13-WP132-O1`)

Pi-authored stable text stays verbatim: every diagnostic above, the input-validation text, both success texts, and `"Operation aborted"`.

Where Pi surfaces raw Node text or a hybrid, the raw part is replaced by the closed `R010-B` cause phrase for the failing operation's `FsErrorCode` (the table under `read`'s error text above). `details` is always `{}` for these generated errors.

```text
site                                          Pi                                              Minion
queue registration fails (canonical_path /    raw "<CODE>: <text>, realpath '<abs>'"          "Cannot resolve <path>: <cause>"
  absolute_path, non-fallback code); write's                                                   (site-specific wrapper)
  in-lock absolute_path fails (R001; no Pi
  site -- Pi's resolution is synchronous)
write: parent mkdir fails                     raw "<CODE>: <text>, mkdir '<abs dir>'"         "Cannot create parent directory of <path>: <cause>"
                                                                                              (site-specific wrapper)
write: write fails                            raw "<CODE>: <text>, open '<abs>'"              "Cannot write <path>: <cause>" (site-specific wrapper)
edit: access fails (EXEC-009, or EXEC-008     hybrid "Could not edit file: <path>. Error      "Could not edit file: <path>. <cause>."
  in FALLBACK mode)                             code: <CODE>."                                  (Pi's frame kept, raw fragment replaced)
edit: read fails                              raw "<CODE>: <text>, read"                      "Cannot read <path>: <cause>" (same template as read's)
edit: write fails                             raw "<CODE>: <text>, open '<abs>'"              "Cannot write <path>: <cause>" (same as write's)
TOOL-026 step-4 rejection (R002-A)            (as for read)                                   "Cannot access <path>: invalid path" (unchanged)
```

- `<path>` is the tool's `path` argument exactly as given, as in `read`'s templates.
- The three wrappers `Cannot resolve`, `Cannot create parent directory of` and `Cannot write` are Minion-defined under O1's delegation: each names the operation that failed, following C012/G1's provenance principle.
- This extension changes no WP-13.1 behavior, and WP-13.1's certified record is kept.

#### Witnesses and differential evidence (required before implementation approval)

1. **`edit` algorithm authority corpus.** Pinned Pi's `applyEditsToNormalizedContent`, `generateDiffString` and `generateUnifiedPatch` are executed unmodified under Node 22.15.1, in a disposable container with the SRI-checked `diff` 8.0.4, over a deterministic corpus. The corpus covers:
   - exact and fuzzy single and multi edits, and fuzzy mode spreading to every edit in the call;
   - duplicates counted in fuzzy space despite an exact match, and the empty-normalized-`oldText` `split("")` count including astral characters;
   - overlaps, including edits that are adjacent but not overlapping;
   - `NO_CHANGE` in both singular and plural forms;
   - CRLF-first and LF-first mixtures with lone CR, BOM files, and a file without a final newline;
   - trailing whitespace, smart quotes, dashes and special spaces;
   - NFKC-changing text, including sequences that compose and a code point new in Unicode 17 (U+A7F1), which must stay unchanged;
   - the JavaScript-whitespace set and the characters it excludes;
   - line groups merging, the INTERNAL guards where reachable, astral characters in every position, and large diffs that exercise the Myers pruning.

   Its results become canonical expectations: final file bytes, result text, `details.diff`, `details.patch` and `firstChangedLine`. Neither binding is an authority.
2. **Canonical `builtin_tool` scenarios** for `write`/`edit`, generated from that authority and from pinned-Pi templates. They include:
   - write creating parents, overwriting, reporting a UTF-16 length that differs from the byte length, and encoding a surrogate;
   - every `edit` diagnostic, BOM and line-ending round trips, and `details` equality;
   - every error site above, including `EXEC-009` access failures at the access site and a later read or write failure at its own site;
   - the provider-without-`EXEC-009` FALLBACK witness;
   - `prepare_arguments` coercions, and empty `edits`;
   - an abort arriving during registration or while queued answering only after acquiring the lock, and a pre-aborted call answered by Layer 06 preflight with no filesystem call (`L13-WP132-R004`);
   - an abort during each step, with the step's own error winning where Pi checks later.
3. **Queue witnesses:**
   - call-order FIFO when key resolution completes out of order, using a provider that delays `canonical_path`;
   - `write` A then `write` B for the same target, with only A's provider calls delayed. B's `canonical_path` is not invoked before A's registration settles, and A's write completes before B's. The witness asserts the provider-call and write order, not just final queue contents (`L13-WP132-R001`). The negative control is an implementation awaiting `absolute_path` before registration;
   - a symlink and its target sharing a queue;
   - different providers with equal keys not sharing;
   - different keys running concurrently;
   - a registration whose `canonical_path` is pending and then fails: a later registration for another key does not begin its key lookup until the failure settles, then proceeds; no entry for the failed call remains (`L13-WP132-R003`). The negative controls are an implementation starting B early and one leaving a lingering entry;
   - release after an error and after an abort;
   - a later call never starting before an aborted call's in-flight write settles;
   - the `not_directory` fallback (`notes.txt/child.md`), negative-controlled against `resolve()`.
4. **Negative controls.** Each material rule gets a single-point mutant that its witness must kill:
   - exact-only uniqueness counting;
   - fuzzy applied per edit rather than per call;
   - trimming with the binding's native whitespace set;
   - Unicode 15.1 or 17.0 NFKC;
   - line-ending restore, BOM, and the byte-length success count;
   - Myers tie-break, context joining, and the missing-newline marker;
   - a registration that is not globally serialized, and a global key without provider scoping;
   - abort-listener release;
   - a two-probe access check.

**Evidence inventory (candidate for contract review).** The evidence lives in `assurance/layers/data/13-wp132-evidence/`, whose `README.md` gives the pins, the reproduction commands and the results.

- **Items 1 and 4, corpus half.**
  - The pinned-Pi authority run covers 380 cases: 60 curated edit cases, 300 seeded random edit cases, 10 `prepareEditArguments` cases, 5 write cases and 5 `normalizeForFuzzyMatch` cases.
  - The corpus-level negative controls are 13 single-point mutants of copies of pinned `edit-diff.ts`, the `edit.ts`/`write.ts` glue and `diff` 8.0.4. All 13 are killed.
- **Item 3's ordering authority.** Pinned `file-mutation-queue.ts` runs unmodified, with a scripted `realpath`, across 9 traced scenarios.
- **Item 2 and item 3's scenarios.** They live in `minion-agent` `conformance/agent/builtin-mutation/`, in their own shape, `conformance/schema/builtin-mutation-scenario.schema.json` (key `builtin_mutation`). There are 26 documents:
  - 8 are generated from the authority run and cover 374 cases. Expectations are pinned Pi's text, final bytes and details, verbatim. The one non-object `prepareEditArguments` input stays prepare-helper evidence (`L13-WP132-R005`).
  - 7 are hand-authored case documents covering the error sites, the FALLBACK and cancellation.
  - 11 are queue scenarios.

  The shape's own comments define the runner protocol. A runner:
  - builds a fresh root for each case;
  - records the path each tool passed to `ctx.fs`;
  - runs gated provider invocations, with steps separated by quiescence;
  - checks ordering constraints over the event log;
  - fails any call still pending once the steps are exhausted. This catches a lingering entry.
- **Fuzzy-normalization replay.** `conformance/agent/fixtures/wp132-fuzzy-normalize/fuzzy_normalize.json` holds pinned Pi's `normalizeForFuzzyMatch` results. Each binding replays them against its own `fuzzy_normalize`.
- **Unpaired surrogates.** Cases whose arguments contain an unpaired surrogate are flagged `unpaired_surrogate_arguments`, per String semantics above.
  - A binding whose Layer 02/05 decoding carries such an argument MUST pass the case.
  - A binding whose decoding cannot represent it MUST show the argument is rejected before the tool runs. It records that as the Layer 02/05 hazard, not as a pass.
- **Binding-level negative controls.** The remaining item-4 controls are binding-level and run at each implementation review: Unicode 15.1/17.0 NFKC, a native whitespace set, non-serialized registration, no provider scoping, abort-listener release, and a two-probe access check. The corpus contains their killing inputs: U+1CCD6, U+A7F1, NEL, U+001C and U+FEFF, and the queue scenarios above.

#### Explicitly not certified by WP-13.2

- Pi's TUI rendering and preview (`renderCall`, `renderResult`, `computeEditsDiff`).
- `promptSnippet` and `promptGuidelines` (Layer 14).
- `constrainedSampling`.
- Pi's `WriteOperations`/`EditOperations` override seams: Minion's seam is `ctx.fs` (Layer 12).
- Lone-surrogate argument decoding (Layer 02/05).
- `bash` (`WP-13.3`) and `find`/`grep` (`WP-13.4`).
