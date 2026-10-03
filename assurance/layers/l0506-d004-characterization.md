# L0506-D004: per-call tool execution context — characterization

**Work package:** `minion-agent#131` (CONTRACT_DRAFT), requirement `TOOL-042` (proposed).
**Authorization:** Owner decision `WP133-F3` = A (`minion-agent#50` comment `5951046523`, §§14–29).
**Consumer:** WP-13.3 `bash` (`minion-agent#50`); not bash-specific.
**Author:** Claude. **Pinned Pi:** `b7bb00b936dbe21b8e160b3e89efdec361846699`.

## 1. How pinned Pi delivers the context (source audit)

| Step | Pi source | Behavior |
|---|---|---|
| core loop invokes a tool | `agent/src/agent-loop.ts:679` `executePreparedToolCall` | `prepared.tool.execute(toolCallId, args, signal, onUpdate)`. **Four arguments**: the core loop passes no context |
| the coding-agent wrapper adds it | `coding-agent/src/core/tools/tool-definition-wrapper.ts:17-18` `wrapToolDefinition(definition, ctxFactory?)` | `execute: (id, params, signal, onUpdate, ctx?) => definition.execute(id, params, signal, onUpdate, ctx ?? ctxFactory?.())`. The factory is called **once per `execute` invocation** |
| the session supplies the factory | `coding-agent/src/core/extensions/wrapper.ts:18` `wrapRegisteredTool(registeredTool, runner)`; `agent-session.ts:2642-2643` wraps both extension and **built-in** tools with `wrapRegisteredTools(..., runner)` | `ctxFactory = () => runner.createContext()` |
| the context's fields | `coding-agent/src/core/extensions/runner.ts:690-712` `createContext()` | **live getters**: `sessionManager` (→ `getSessionId()`, `getSessionFile()`; `session-manager.ts:1007-1011`), `model` (`getModel()` → `AgentSession.model`, `agent-session.ts:2543`), `thinkingLevel` (`runtime.getThinkingLevel()` → `AgentSession.thinkingLevel`, `agent-session.ts:2539`) |
| a standalone tool | `coding-agent/src/core/tools/bash.ts:504` `createBashTool` (and `read`/`write`/`edit`/`ls`/`find`/`grep`, lines cited in the wrapper grep) | `wrapToolDefinition(definition)` with **no factory**: `ctx` is `undefined`. Pi's `bash` then strips its session keys and injects nothing (`bash.ts:169-174`) |

**Observable consequences:**
1. **Per call.** Each `execute` gets the context of the session that owns the tool registration, evaluated when `execute` starts.
   - Pi's getters are live, but its `bash` reads them in `resolveSpawnContext`, the first statement of `execute`. So the observable values are those at `execute` start.
2. **Absent outside a session.** A tool used without a session has no context.
3. **Values:**
   - `sessionId`: always present when a context exists.
   - `sessionFile`: may be `undefined` (an in-memory session).
   - `model`: may be `undefined`.
   - `thinkingLevel`: always one of `"off" | "minimal" | "low" | "medium" | "high" | "xhigh" | "max"` (`agent/src/types.ts:300`). `"off"` is a **truthy** string, so Pi's `bash` exports `PI_REASONING_LEVEL=off`.
4. **Hooks do not receive this context through `execute`.** Pi's `beforeToolCall` / `afterToolCall` take `(context, signal)`, and that `context` is the tool-call context, not `ExtensionContext`. Owner F3 §25 keeps hooks out of scope.

## 2. Minion today (Python, `main` `d81edb0a`; Rust read-only)

| Item | State |
|---|---|
| `ToolDefinition.execute` delivery | `(tool_call_id, arguments[, signal][, update])`, dispatched by `wants_signal` plus arity (`spec/tools.md` Layer 06, `L09-R003`). **No context** |
| `execute_call` / `execute_batch` | receive `ctx` (the runtime `Context`; the agent loop passes `instance.ctx`, `agent_loop/driver.py:1250-1259`). It is **not** passed to `execute` |
| session id | `SessionLog.session_id` (`session/log.py:54`), reachable as `AgentInstance.log` |
| session file | **none**: no persisted session form exists (`spec/session.md`, "future persisted form") |
| model | `AgentInstance.model: ModelId` (`provider`, `model`, `api`), always set (`agent/instance.py:58`) |
| reasoning level | `AgentInstance.thinking_level: ThinkingLevel`, Pi's seven-value union adopted verbatim, initially `OFF` (`agent/instance.py:59`) |
| Rust | `ToolExecutionRequest` (typed request, `tools/definition.rs`) already carries `signal`. A `context: Option<…>` field is the natural shape (Owner F3 §23) |

The values exist; only the delivery is missing. This is the feasibility gap `WP133-F3`.

## 3. Choices the contract must make (routine; delegated by F3 §§15, 23)

- **Snapshot point:** when the pipeline invokes `execute`, after preflight, preparation, validation and the before-hooks. That is Pi's point (factory called at `execute` invocation; `bash` reads at `execute` start).
  - The Owner's "at call start" (F3 §16) is read as the start of the tool's execution.
  - `RunConfigUpdate` overrides are per-step provider settings, not the agent's authoritative current model (F3 §22). The context reads `AgentInstance.model` / `thinking_level`.
- **Python opt-in:** an explicit `ToolDefinition.wants_context: bool = False`. When it is true, `execute` additionally receives `context=` as a **keyword** argument, which never shifts the certified positional `signal`/`update` dispatch (F3 §23). It is `None` when absent.
- **Delivery to the pipeline:** the agent loop passes a per-call context provider into `execute_batch` / `execute_call`. The pipeline calls it immediately before `execute`, for that call only.
  - It is explicit, not ambient (F3 §19).
  - A pipeline call without a provider means the context is absent (F3 §20).
- **Field domain:**
  - `session_id: str`;
  - `session_file: str | None` (always `None` today, F3 §21);
  - `provider: str | None` and `model: str | None` (present whenever an agent runs);
  - `reasoning_level: str | None`, the `ThinkingLevel` value: `"off"` is present, not absent.
  - The object is immutable.

## 4. Contract checkpoint and Python implementation

**Codex contract checkpoint review** (docs #233 @ `7b12f9d0`; comment `5969835839`, verbatim): **APPROVED**, no findings. Codex executed pinned Pi's real `tool-definition-wrapper.ts`. It found the factory called once per `execute`, the explicit-`ctx` path, and no context for a standalone tool.

Its implementation reminders, and how they were met:
- **Arity.** `_arity` excludes a `context` parameter only when `wants_context` is set. The context-only, update+context, signal+context and signal+update+context dispatch tests pass. A control that counts `context` as positional fails the context-only dispatch.
- **Snapshot point.** A before-hook changes the source, and `execute` sees the post-hook value. The call order is hook, then provider, then execute. Between two agent-run calls, a change is reflected in the later call, and the earlier snapshot stays frozen. A blocked call never calls the provider. A tool that did not opt in never calls it either.
- **Isolation.**
  - `ToolExecutionContext` is a frozen dataclass: setting a field raises.
  - It holds no agent reference.
  - Two agents sharing one registration see their own contexts. The registration-time-capture control fails.

**Python candidate:** code `minion-agent#137` @ `9ced384e`. Gates: `pytest` 4204 passed, 29 skipped, 19 xfailed; coverage 100.00%; `ruff` and `mypy` clean.

## 5. Implementation review 1 and remediation

**Codex Python implementation review 1** (code #137 @ `9ced384e` / docs #233 @ `e1cbb5c1`; comment `5969963662`, verbatim): **CHANGES REQUIRED**.

- **`L0506-D004-I001`** (PI_PARITY_DEFECT): `context_provider()` ran before the `try` around `execute`, so a failing provider escaped `execute_call`. Pinned Pi calls the factory inside the wrapped `execute`, which `executePreparedToolCall` guards, so a factory failure is an ordinary per-call execution failure.
- **`L0506-D004-I002`** (CONTRACT_ASSURANCE_DEFECT): the per-call evidence used separate batches, so a once-per-batch capture survived all 14 tests.

**Remediation:** code #137 @ `fcb08ca0`.

- **I001.** The provider is now evaluated inside the execute failure boundary, at the same snapshot point. Witnesses:
  - a direct `execute_call` with a raising provider settles as an error result carrying the message; the tool body does not run, and `on_execution_end` runs with `is_error`;
  - in a sequential batch, the first call's provider fails and only that call errors, while the healthy sibling runs.
- **I001 control.** Evaluating the provider outside the boundary (the rejected placement) lets `RuntimeError` escape. Both I001 witnesses **fail at the rejected source `9ced384e`** (§11.8.7.1).
- **I002.** Two calls in **one** sequential batch, through real `execute_batch`, observe `["first", "second"]` with the provider called twice. The once-per-batch control observes `["first", "first"]`, called once.
- **I002, agent-driven variant.** One model reply carries two calls to a sequential tool, and the second call sees the model the first call set.
- **Unchanged.** I002 needed no production change: the per-call sampling was already correct, as Codex observed.

**Gates:** `pytest` 4210 passed, 29 skipped, 19 xfailed; coverage 100.00%; `ruff` and `mypy` clean.
