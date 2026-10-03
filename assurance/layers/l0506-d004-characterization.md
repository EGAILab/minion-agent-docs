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
