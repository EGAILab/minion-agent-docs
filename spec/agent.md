# Agent Semantics

A run is one high-level prompt/continue invocation. A turn is one assistant response plus tool
calls/results caused by it.

Prompt-run order:

```text
agent_start
turn_start
initial prompt message lifecycle
initial steering poll + claimed-message lifecycle
first provider request
assistant/tool lifecycle
turn_end
```

`prompt()` while active is rejected. `continue()` while active or with no transcript is rejected.
When the last message is assistant, `continue()` drains eligible steering, else follow-up, else
rejects; if it pre-drained steering, the run suppresses duplicate initial steering polling.

After a normally completed turn:

```text
turn_end -> prepareNextTurn -> shouldStopAfterTurn -> steering poll
```

Follow-up is polled only when the run would otherwise stop.

`agent_end.messages` is invocation-local. Prompt runs include initial prompt + newly produced/consumed
queue messages; continuation runs exclude pre-existing context.

Abort actively signals the running provider/tools/hooks. Idle is reached only after terminal run
settlement and awaited `agent_end` listeners.

Unexpected high-level transform/queue callback failure produces terminal assistant failure lifecycle,
then `turn_end`, `agent_end`, then idle, subject to listener-failure behavior.
