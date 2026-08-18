# Minion Agent — Plan 3: The Agent Loop

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the agent loop — definitions and live instances, an inbox that carries provenance, the turn/step lifecycle, the decision events, cancellation, and the Pi-compatible event stream — so that by the end a mock model can request a tool, receive its result, and be asked again, with every step reconstructable from the log.

**Architecture:** An `AgentDefinition` is reusable configuration; an `AgentInstance` is one live execution identity with its own inbox, session log, and turn state. `ctx.agents` creates instances and hands out owning handles. The driver is an imperative async class with an explicit phase union — neither reference factors the live loop as a pure reducer, and this design does not invent one. Extension points are Cordis events using Plan 1's waterfall contract, with decision payloads typed as closed unions.

**Tech Stack:** As Plan 2. Everything mounts as a plugin on the runtime; the model is Plan 2's scripted mock adapter.

**Spec:** `minion-agent-docs/design/2026-08-18-minion-agent-design.md`, **frozen** — read §6 in full (definitions and instances, the loop, input provenance, the inbox, preserving pi's semantics, decision algebra, agent progress isolation, tool batch execution) plus §8's conformance families.

**Prior plans:** Plan 1 (runtime) and Plan 2 (LLM, session, telemetry), both complete. Read `src/minion_agent/runtime/__init__.py`, `llm/__init__.py`, `session/__init__.py`, and `telemetry/__init__.py` for the exact surfaces before writing anything.

## Global Constraints

Plan 2's Global Constraints carry over unchanged — Python floor, uv project mode, `uv run <tool>`, naming, the conformance rule, normativity, commit style. Additionally:

- **Coverage:** `src/minion_agent/agent/**` and `src/minion_agent/agent_loop/**` join the 100%-per-file gate.
- **Layer purity:** `agent/` may import `runtime`, `llm`, `session`, and `telemetry`. Nothing may import `agent_loop` except its own tests — the driver is package-internal, and the `agent` package holds the interface.
- **Pi semantics are the compatibility target.** Where this plan and §6's mapping table disagree, the table wins.
- **One active turn per instance.** Concurrency lives *across* instances, never within one. Both references arrived at this independently.
- **No wall-clock time.** Settlement is observed through `agent/status`, never by sleeping. A test that sleeps is wrong even when it passes.
- **Deferred to Plan 4:** the real tool registry, `tools/pre-execute` and `tools/post-execute`, parallel batching, execution modes, streaming tool results, and the full `terminate` fold. This plan ships a trivial tool service and the *sequential* single-call path, which is what the loop needs to close a round trip.

---

## File Structure

```
minion-agent-python/
  src/minion_agent/
    agent/
      __init__.py          # public surface
      identity.py          # AgentDefinition, AgentInstanceId, AgentStatus
      envelope.py          # InputEnvelope, InboxTarget, ClaimPolicy
      inbox.py             # the two queues and their claim rules
      decisions.py         # Reject | Enter, PreStepReason, TurnStopping
      events.py            # agent/* event names and declared modes
      instance.py          # AgentInstance: identity, inbox, log, status
      registry.py          # AgentRegistry (ctx.agents) + AgentHandle
      projection.py        # the Pi-compatible AgentEvent stream
      tools.py             # trivial tool service; Plan 4 replaces it
    agent_loop/
      __init__.py          # the plugin; the driver is package-internal
      driver.py            # the imperative loop
  conformance/
    agent/*.yaml           # turn lifecycle, provenance, tools, cancellation
  tests/
    agent/  agent_loop/
    conformance/agent_runner.py, test_agent_conformance.py
```

---

# Phase 3 — The agent loop

## Task 1: Identity — definitions and instances

**Files:**
- Create: `src/minion_agent/agent/__init__.py`, `src/minion_agent/agent/identity.py`
- Test: `tests/agent/test_identity.py`

**Interfaces:**
- Produces:
  - `type AgentInstanceId = str`
  - `@dataclass(frozen=True, slots=True) class AgentDefinition` with `name: str`, `model: ModelId`, `system: str = ""`, `max_steps: int = 16`
  - `class AgentStatus(StrEnum)`: `IDLE`, `RUNNING`
  - `AgentDefinition.scope_name` → `f"agent-definition:{self.name}"`, the key an application uses when scoping definition-level registrations.

- [ ] **Step 1: Write the failing test**

Create `tests/agent/test_identity.py`:

```python
"""One definition, many live instances — the distinction §6 fixes first."""

import pytest

from minion_agent.agent.identity import AgentDefinition, AgentStatus
from minion_agent.llm import ModelId


def _definition(**overrides: object) -> AgentDefinition:
    defaults: dict[str, object] = {
        "name": "ada",
        "model": ModelId("mock", "mock-1"),
        "system": "be helpful",
    }
    return AgentDefinition(**{**defaults, **overrides})  # type: ignore[arg-type]


def test_a_definition_carries_reusable_configuration() -> None:
    definition = _definition()

    assert definition.name == "ada"
    assert definition.model == ModelId("mock", "mock-1")
    assert definition.system == "be helpful"


def test_a_definition_holds_no_conversation_state() -> None:
    """Anything conversational belongs to an instance, so a definition can be
    shared by many of them without coupling them together."""
    fields = set(AgentDefinition.__dataclass_fields__)

    assert fields == {"name", "model", "system", "max_steps"}


def test_max_steps_bounds_a_runaway_turn() -> None:
    assert _definition().max_steps == 16
    assert _definition(max_steps=2).max_steps == 2


def test_the_scope_name_is_derived_from_the_definition_name() -> None:
    """Definition-scoped registrations are shared by every instance of it."""
    assert _definition().scope_name == "agent-definition:ada"


def test_definitions_are_frozen() -> None:
    definition = _definition()

    with pytest.raises(Exception):  # noqa: B017
        definition.name = "changed"  # type: ignore[misc]


def test_status_has_exactly_two_states() -> None:
    """A third state would mean the settle signal has more than one meaning."""
    assert {status.value for status in AgentStatus} == {"idle", "running"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/agent/test_identity.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'minion_agent.agent'`

- [ ] **Step 3: Write the implementation**

Create `src/minion_agent/agent/__init__.py` with a docstring, and
`src/minion_agent/agent/identity.py`:

```python
"""Agent identity: reusable definitions and live instances.

Two things are routinely called "the agent", and §6 separates them before
anything else is unambiguous:

* An **AgentDefinition** is reusable configuration — persona, model, policy.
  It holds no conversation state, so many instances can share one.
* An **AgentInstance** (see `instance.py`) is one live execution identity: one
  inbox, one active-turn state, one session log, one lifecycle owner.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from ..llm import ModelId

type AgentInstanceId = str


class AgentStatus(StrEnum):
    """Whether an instance is currently working.

    Exactly two states: `agent/status` is the settle signal, and a third value
    would give that signal more than one meaning.
    """

    IDLE = "idle"
    RUNNING = "running"


@dataclass(frozen=True, slots=True)
class AgentDefinition:
    """Reusable configuration shared by every instance of a named agent."""

    name: str
    model: ModelId
    system: str = ""
    max_steps: int = 16
    """Upper bound on steps in one turn, so a tool-calling loop cannot run away."""

    @property
    def scope_name(self) -> str:
        """The scope key for registrations shared by all instances of this
        definition. Instances mint children of it (design spec section 3)."""
        return f"agent-definition:{self.name}"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/agent/test_identity.py -v`
Expected: PASS — six tests.

- [ ] **Step 5: Commit**

```bash
git add src/minion_agent/agent tests/agent
git commit -m "feat: add agent definitions and status"
```

---

## Task 2: Input envelopes and the inbox

The provenance model of §6. Provenance attaches to *inputs* rather than turns,
because under the `all` claim policy one turn provably has several causes.

**Files:**
- Create: `src/minion_agent/agent/envelope.py`, `src/minion_agent/agent/inbox.py`
- Test: `tests/agent/test_inbox.py`

**Interfaces:**
- Produces:
  - `class InboxTarget(StrEnum)`: `NEXT_TURN`, `NEXT_STEP`
  - `class ClaimPolicy(StrEnum)`: `ALL`, `ONE_AT_A_TIME`
  - `@dataclass(frozen=True, slots=True) class InputEnvelope` with `id: str`, `message: UserMessage`, `origin: JsonValue`
  - `type JsonValue = str | int | float | bool | None | list[JsonValue] | dict[str, JsonValue]`
  - `class Inbox` with `send(message, target, wakeup, origin=None) -> InputEnvelope`, the aliases `followup` / `steer` / `inject`, `claim(target, policy) -> tuple[InputEnvelope, ...]`, `pending(target) -> tuple[InputEnvelope, ...]`, and `wake_requested: bool` (cleared by `take_wake()`).
- `origin` is **opaque** — never inspected — and must be **JSON-safe**, because it travels in the log and must survive a reimplementation in another language. `Inbox.send` validates this eagerly.

- [ ] **Step 1: Write the failing test**

Create `tests/agent/test_inbox.py`:

```python
"""The inbox carries provenance and claims by policy."""

import pytest

from minion_agent.agent.envelope import ClaimPolicy, InboxTarget
from minion_agent.agent.inbox import Inbox, NotJsonSafeOriginError
from minion_agent.llm import TextBlock, UserMessage


def _message(text: str) -> UserMessage:
    return UserMessage(content=(TextBlock(text=text),), timestamp=1)


def test_followup_queues_for_the_next_turn_and_wakes() -> None:
    inbox = Inbox()

    inbox.followup(_message("hello"))

    assert len(inbox.pending(InboxTarget.NEXT_TURN)) == 1
    assert inbox.wake_requested


def test_steer_queues_for_the_next_step_and_wakes() -> None:
    inbox = Inbox()

    inbox.steer(_message("actually, stop"))

    assert len(inbox.pending(InboxTarget.NEXT_STEP)) == 1
    assert inbox.wake_requested


def test_inject_queues_for_the_next_step_without_waking() -> None:
    """Silent context: it rides along with the next thing that does wake."""
    inbox = Inbox()

    inbox.inject(_message("file changed on disk"))

    assert len(inbox.pending(InboxTarget.NEXT_STEP)) == 1
    assert not inbox.wake_requested


def test_taking_the_wake_signal_clears_it() -> None:
    inbox = Inbox()
    inbox.followup(_message("hello"))

    assert inbox.take_wake()
    assert not inbox.wake_requested
    assert not inbox.take_wake()


def test_one_at_a_time_claims_only_the_oldest() -> None:
    inbox = Inbox()
    inbox.followup(_message("first"))
    inbox.followup(_message("second"))

    claimed = inbox.claim(InboxTarget.NEXT_TURN, ClaimPolicy.ONE_AT_A_TIME)

    assert len(claimed) == 1
    assert len(inbox.pending(InboxTarget.NEXT_TURN)) == 1


def test_all_claims_everything_queued() -> None:
    inbox = Inbox()
    inbox.followup(_message("first"))
    inbox.followup(_message("second"))

    claimed = inbox.claim(InboxTarget.NEXT_TURN, ClaimPolicy.ALL)

    assert len(claimed) == 2
    assert inbox.pending(InboxTarget.NEXT_TURN) == ()


def test_claiming_removes_what_it_claimed() -> None:
    inbox = Inbox()
    inbox.followup(_message("only"))

    inbox.claim(InboxTarget.NEXT_TURN, ClaimPolicy.ALL)

    assert inbox.claim(InboxTarget.NEXT_TURN, ClaimPolicy.ALL) == ()


def test_the_two_queues_are_independent() -> None:
    inbox = Inbox()
    inbox.followup(_message("turn"))
    inbox.steer(_message("step"))

    claimed = inbox.claim(InboxTarget.NEXT_STEP, ClaimPolicy.ALL)

    assert len(claimed) == 1
    assert len(inbox.pending(InboxTarget.NEXT_TURN)) == 1


def test_every_envelope_gets_a_unique_id() -> None:
    inbox = Inbox()

    first = inbox.followup(_message("a"))
    second = inbox.followup(_message("b"))

    assert first.id != second.id


def test_origin_is_carried_verbatim() -> None:
    inbox = Inbox()
    origin = {"channel": "matrix", "room": "!abc:example.org"}

    envelope = inbox.followup(_message("hello"), origin=origin)

    assert envelope.origin == origin


def test_origin_defaults_to_none() -> None:
    assert Inbox().followup(_message("hello")).origin is None


def test_a_non_json_safe_origin_is_rejected_eagerly() -> None:
    """Origin travels in the log and must survive another language."""
    inbox = Inbox()

    with pytest.raises(NotJsonSafeOriginError, match="JSON-safe"):
        inbox.followup(_message("hello"), origin=object())

    assert inbox.pending(InboxTarget.NEXT_TURN) == ()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/agent/test_inbox.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'minion_agent.agent.envelope'`

- [ ] **Step 3: Write the envelope module**

Create `src/minion_agent/agent/envelope.py`:

```python
"""Input envelopes: the unit provenance attaches to.

Provenance attaches to *inputs* rather than turns because a turn can have more
than one cause. Under the `all` claim policy one turn consumes several queued
inputs with different origins, so a single `turn.origin` would not be well
defined (design spec section 6).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from ..llm import UserMessage

type JsonValue = str | int | float | bool | None | list["JsonValue"] | dict[str, "JsonValue"]


class InboxTarget(StrEnum):
    """Which boundary an input waits for."""

    NEXT_TURN = "next-turn"
    """A queued prompt: claimed when a turn opens."""

    NEXT_STEP = "next-step"
    """Steering or injected context: claimed at the next step boundary."""


class ClaimPolicy(StrEnum):
    """How many queued inputs a boundary takes.

    Pi's `steeringMode` and `followUpMode`, one policy per boundary.
    """

    ALL = "all"
    ONE_AT_A_TIME = "one-at-a-time"


@dataclass(frozen=True, slots=True)
class InputEnvelope:
    """One queued input plus the provenance its sender attached.

    `origin` is opaque to the runtime — never inspected, matched, or
    interpreted — and must be JSON-safe so it survives the log and a
    reimplementation in another language.
    """

    id: str
    message: UserMessage
    origin: JsonValue = None
```

- [ ] **Step 4: Write the inbox**

Create `src/minion_agent/agent/inbox.py`:

```python
"""The inbox: two queues, three aliases, and a wake signal.

DSH's `send(message, target, wakeup)` generalizes pi's two queues, and the
three aliases are its fixed presets:

    followup  next-turn  wakes
    steer     next-step  wakes
    inject    next-step  silent
"""

from __future__ import annotations

import uuid

from ..llm import UserMessage
from .envelope import ClaimPolicy, InboxTarget, InputEnvelope, JsonValue

_JSON_SCALARS = (str, int, float, bool, type(None))


class NotJsonSafeOriginError(TypeError):
    """An origin was supplied that JSON cannot represent."""


def _check_json_safe(value: object, path: str = "origin") -> None:
    if isinstance(value, _JSON_SCALARS):
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise NotJsonSafeOriginError(f"{path}: keys must be strings, got {key!r}")
            _check_json_safe(item, f"{path}.{key}")
        return
    if isinstance(value, list | tuple):
        for index, item in enumerate(value):
            _check_json_safe(item, f"{path}[{index}]")
        return
    raise NotJsonSafeOriginError(f"{path}: {type(value).__name__} is not JSON-safe")


class Inbox:
    """Queued input for one agent instance."""

    def __init__(self) -> None:
        self._queues: dict[InboxTarget, list[InputEnvelope]] = {
            InboxTarget.NEXT_TURN: [],
            InboxTarget.NEXT_STEP: [],
        }
        self._wake = False

    @property
    def wake_requested(self) -> bool:
        """Whether input has arrived that should start or continue work."""
        return self._wake

    def take_wake(self) -> bool:
        """Consume the wake signal, returning whether one was pending."""
        pending, self._wake = self._wake, False
        return pending

    def send(
        self,
        message: UserMessage,
        target: InboxTarget,
        wakeup: bool,
        origin: JsonValue = None,
    ) -> InputEnvelope:
        """Queue `message`, validating its origin before anything is stored."""
        _check_json_safe(origin)
        envelope = InputEnvelope(id=str(uuid.uuid4()), message=message, origin=origin)
        self._queues[target].append(envelope)
        if wakeup:
            self._wake = True
        return envelope

    def followup(self, message: UserMessage, origin: JsonValue = None) -> InputEnvelope:
        """Queue a prompt for the next turn and wake the driver."""
        return self.send(message, InboxTarget.NEXT_TURN, wakeup=True, origin=origin)

    def steer(self, message: UserMessage, origin: JsonValue = None) -> InputEnvelope:
        """Queue input for the next step boundary and wake the driver."""
        return self.send(message, InboxTarget.NEXT_STEP, wakeup=True, origin=origin)

    def inject(self, message: UserMessage, origin: JsonValue = None) -> InputEnvelope:
        """Queue context for the next step boundary without waking.

        It rides along with whatever wakes the driver next, which is what makes
        it usable for ambient context that should not itself start work.
        """
        return self.send(message, InboxTarget.NEXT_STEP, wakeup=False, origin=origin)

    def pending(self, target: InboxTarget) -> tuple[InputEnvelope, ...]:
        """What is queued at `target`, unclaimed."""
        return tuple(self._queues[target])

    def claim(
        self, target: InboxTarget, policy: ClaimPolicy
    ) -> tuple[InputEnvelope, ...]:
        """Remove and return queued input according to `policy`."""
        queue = self._queues[target]
        if not queue:
            return ()
        if policy is ClaimPolicy.ALL:
            claimed, queue[:] = tuple(queue), []
            return claimed
        return (queue.pop(0),)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/agent/test_inbox.py -v`
Expected: PASS — twelve tests.

- [ ] **Step 6: Commit**

```bash
git add src/minion_agent/agent tests/agent/test_inbox.py
git commit -m "feat: add input envelopes and the two-queue inbox"
```

---

## Task 3: Decision types

**Files:**
- Create: `src/minion_agent/agent/decisions.py`
- Test: `tests/agent/test_decisions.py`

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) class Reject` with `reason: str = ""`
  - `@dataclass(frozen=True) class Enter` with `messages: tuple[UserMessage, ...]`, `system_override: str | None = None`, `history_window: int | None = None`
  - `type PreStepDecision = Reject | Enter`
  - `class PreStepReason(StrEnum)`: `INITIAL`, `TOOL_RESULTS`, `STEERING`, `NEXT_TURN`, `CONTINUATION`
  - `class TurnStopping(StrEnum)`: `NO_OPINION`, `CONTINUE`, `STOP`
  - `def resolve_stopping(decisions: Iterable[TurnStopping]) -> TurnStopping` — first non-`NO_OPINION` wins; all-`NO_OPINION` yields `CONTINUE`.

- [ ] **Step 1: Write the failing test**

Create `tests/agent/test_decisions.py`:

```python
"""Closed decision unions, with their combination rules stated."""

from minion_agent.agent.decisions import (
    Enter,
    PreStepReason,
    Reject,
    TurnStopping,
    resolve_stopping,
)
from minion_agent.llm import TextBlock, UserMessage


def _message(text: str = "hi") -> UserMessage:
    return UserMessage(content=(TextBlock(text=text),), timestamp=1)


def test_enter_carries_the_messages_entering_the_step() -> None:
    decision = Enter(messages=(_message(),))

    assert len(decision.messages) == 1


def test_enter_may_override_the_system_prompt_for_one_step() -> None:
    assert Enter(messages=(), system_override="different").system_override == "different"


def test_enter_may_limit_the_history_window_for_one_step() -> None:
    assert Enter(messages=(), history_window=6).history_window == 6


def test_reject_carries_a_reason() -> None:
    assert Reject(reason="not now").reason == "not now"


def test_pre_step_reasons_cover_pi_call_sites() -> None:
    """Derived from pi's actual call sites; not open for plugins to extend."""
    assert {reason.value for reason in PreStepReason} == {
        "initial",
        "tool_results",
        "steering",
        "next_turn",
        "continuation",
    }


def test_all_no_opinion_continues() -> None:
    """Matching pi's boolean default of false."""
    assert resolve_stopping([TurnStopping.NO_OPINION] * 3) is TurnStopping.CONTINUE


def test_an_empty_chain_continues() -> None:
    assert resolve_stopping([]) is TurnStopping.CONTINUE


def test_the_first_opinion_wins() -> None:
    decisions = [TurnStopping.NO_OPINION, TurnStopping.STOP, TurnStopping.CONTINUE]

    assert resolve_stopping(decisions) is TurnStopping.STOP


def test_a_later_stop_cannot_override_an_earlier_continue() -> None:
    """The trade-off recorded in §6: order-dependent, consistent with the
    short-circuit pattern used by every other decision event."""
    decisions = [TurnStopping.CONTINUE, TurnStopping.STOP]

    assert resolve_stopping(decisions) is TurnStopping.CONTINUE
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/agent/test_decisions.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'minion_agent.agent.decisions'`

- [ ] **Step 3: Write the implementation**

Create `src/minion_agent/agent/decisions.py`:

```python
"""Closed decision unions for the loop's extension points.

Pi's hooks are single-valued with precise semantics; multi-listener dispatch
would diffuse them. The answer (design spec section 6) is to type each decision
payload as a closed union and let Plan 1's waterfall short-circuit decide which
listener owns the call.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum

from ..llm import UserMessage


@dataclass(frozen=True, slots=True)
class Reject:
    """Do not run a step. The turn closes having spent none."""

    reason: str = ""


@dataclass(frozen=True, slots=True)
class Enter:
    """Run a step with these messages.

    `system_override` and `history_window` apply to this step alone, which is
    how pi's per-call `system_suffix` and `max_history_turns` are expressed.
    """

    messages: tuple[UserMessage, ...]
    system_override: str | None = None
    history_window: int | None = None


type PreStepDecision = Reject | Enter


class PreStepReason(StrEnum):
    """Why a pre-step is happening.

    Pi's `transformContext` and `prepareNextTurn` fire at different lifecycle
    points — the first before every request including the first, the second
    only between turns. Collapsing both into one undifferentiated event would
    make `prepareNextTurn` impossible to replicate.
    """

    INITIAL = "initial"
    TOOL_RESULTS = "tool_results"
    STEERING = "steering"
    NEXT_TURN = "next_turn"
    CONTINUATION = "continuation"


class TurnStopping(StrEnum):
    """A listener's opinion on whether the turn should continue."""

    NO_OPINION = "no_opinion"
    CONTINUE = "continue"
    STOP = "stop"


def resolve_stopping(decisions: Iterable[TurnStopping]) -> TurnStopping:
    """First non-`NO_OPINION` decision wins; otherwise continue.

    Order-dependent by design. An order-independent "any STOP wins" rule was
    considered and rejected: it collapses CONTINUE into NO_OPINION and diverges
    from the short-circuit pattern every other decision event uses.
    """
    for decision in decisions:
        if decision is not TurnStopping.NO_OPINION:
            return decision
    return TurnStopping.CONTINUE
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/agent/test_decisions.py -v`
Expected: PASS — nine tests.

- [ ] **Step 5: Commit**

```bash
git add src/minion_agent/agent/decisions.py tests/agent/test_decisions.py
git commit -m "feat: add closed decision unions and the stopping fold"
```

---

## Task 4: Agent events

**Files:**
- Create: `src/minion_agent/agent/events.py`
- Test: `tests/agent/test_agent_events.py`

**Interfaces:**
- Produces:
  - Name constants: `AGENT_STATUS`, `AGENT_PRE_STEP`, `AGENT_TURN_STOPPING`, `AGENT_INBOX_INSERTED`, `AGENT_INBOX_CLAIMED`
  - `AGENT_EVENT_MODES: dict[str, DispatchMode]` declaring each
  - `def declare_agent_events(bus: EventBus) -> None`
- Modes: `agent/status` and both inbox events are `emit`; `agent/pre-step` is `waterfall`; `agent/turn-stopping` is `serial`.

- [ ] **Step 1: Write the failing test**

Create `tests/agent/test_agent_events.py`:

```python
"""Dispatch mode is part of each event's public contract."""

import pytest

from minion_agent.agent.events import (
    AGENT_EVENT_MODES,
    AGENT_PRE_STEP,
    AGENT_STATUS,
    AGENT_TURN_STOPPING,
    declare_agent_events,
)
from minion_agent.runtime import DispatchMode, EventBus, EventModeError


def test_declaring_registers_every_agent_event() -> None:
    bus = EventBus()

    declare_agent_events(bus)

    for name, mode in AGENT_EVENT_MODES.items():
        assert bus.mode_of(name) is mode


def test_pre_step_is_a_waterfall() -> None:
    """It carries a closed decision union and must support short-circuiting."""
    assert AGENT_EVENT_MODES[AGENT_PRE_STEP] is DispatchMode.WATERFALL


def test_turn_stopping_is_serial() -> None:
    assert AGENT_EVENT_MODES[AGENT_TURN_STOPPING] is DispatchMode.SERIAL


def test_status_is_emit() -> None:
    """The settle signal must not be able to block the loop it reports on."""
    assert AGENT_EVENT_MODES[AGENT_STATUS] is DispatchMode.EMIT


def test_declaring_twice_is_harmless() -> None:
    bus = EventBus()

    declare_agent_events(bus)
    declare_agent_events(bus)

    assert bus.mode_of(AGENT_STATUS) is DispatchMode.EMIT


def test_dispatching_in_the_wrong_mode_still_raises() -> None:
    bus = EventBus()
    declare_agent_events(bus)

    with pytest.raises(EventModeError):
        bus.emit(AGENT_PRE_STEP)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/agent/test_agent_events.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'minion_agent.agent.events'`

- [ ] **Step 3: Write the implementation**

Create `src/minion_agent/agent/events.py`:

```python
"""The `agent/*` event vocabulary and its declared dispatch modes."""

from __future__ import annotations

from ..runtime import DispatchMode, EventBus

AGENT_STATUS = "agent/status"
"""Emitted on every idle<->running transition. The settle signal."""

AGENT_PRE_STEP = "agent/pre-step"
"""Waterfall returning `Reject | Enter`, terminal `Enter(claimed messages)`."""

AGENT_TURN_STOPPING = "agent/turn-stopping"
"""Serial, returning `TurnStopping`. Not dispatched when hard termination fires."""

AGENT_INBOX_INSERTED = "agent/inbox/inserted"
AGENT_INBOX_CLAIMED = "agent/inbox/claimed"

AGENT_EVENT_MODES: dict[str, DispatchMode] = {
    AGENT_STATUS: DispatchMode.EMIT,
    AGENT_PRE_STEP: DispatchMode.WATERFALL,
    AGENT_TURN_STOPPING: DispatchMode.SERIAL,
    AGENT_INBOX_INSERTED: DispatchMode.EMIT,
    AGENT_INBOX_CLAIMED: DispatchMode.EMIT,
}


def declare_agent_events(bus: EventBus) -> None:
    """Declare every agent event. Idempotent for matching modes."""
    for name, mode in AGENT_EVENT_MODES.items():
        bus.declare(name, mode)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/agent/test_agent_events.py -v`
Expected: PASS — six tests.

- [ ] **Step 5: Commit**

```bash
git add src/minion_agent/agent/events.py tests/agent/test_agent_events.py
git commit -m "feat: declare the agent event vocabulary"
```

---

## Task 5: The trivial tool service

Plan 4 replaces this with the real registry, waterfalls, and batching. This is
the minimum the loop needs to close a round trip.

**Files:**
- Create: `src/minion_agent/agent/tools.py`
- Test: `tests/agent/test_tools.py`

**Interfaces:**
- Produces:
  - `type ToolFn = Callable[[dict[str, Any]], Awaitable[str] | str]`
  - `class ToolService` with `__service_name__ = "tools"`, `register(name, fn) -> Callable[[], None]`, `names() -> frozenset[str]`, `async execute(call: ToolCallBlock) -> ToolResultMessage`
  - An unknown tool yields an **error tool result**, not an exception — the model must see a result for every call it made, or the transcript stops being coherent.
  - A tool that raises likewise yields an error result carrying the message.

- [ ] **Step 1: Write the failing test**

Create `tests/agent/test_tools.py`:

```python
"""Every tool call gets a result, even when it fails."""

from minion_agent.agent.tools import ToolService
from minion_agent.llm import ToolCallBlock, text_of


def _call(name: str = "echo", **arguments: object) -> ToolCallBlock:
    return ToolCallBlock(id="t1", name=name, arguments=dict(arguments))


async def test_a_registered_tool_runs_and_returns_its_output() -> None:
    service = ToolService()
    service.register("echo", lambda args: str(args["value"]))

    result = await service.execute(_call(value="hello"))

    assert text_of(result) == "hello"
    assert not result.is_error
    assert result.tool_call_id == "t1"


async def test_async_tools_are_awaited() -> None:
    service = ToolService()

    async def slow(args: dict[str, object]) -> str:
        return "async result"

    service.register("slow", slow)

    assert text_of(await service.execute(_call("slow"))) == "async result"


async def test_an_unknown_tool_yields_an_error_result_not_an_exception() -> None:
    """The model must see a result for every call it made, or the transcript
    stops being coherent."""
    service = ToolService()

    result = await service.execute(_call("missing"))

    assert result.is_error
    assert "missing" in text_of(result)


async def test_a_raising_tool_yields_an_error_result() -> None:
    service = ToolService()

    def broken(args: dict[str, object]) -> str:
        raise RuntimeError("disk on fire")

    service.register("broken", broken)

    result = await service.execute(_call("broken"))

    assert result.is_error
    assert "disk on fire" in text_of(result)


def test_names_lists_registered_tools() -> None:
    service = ToolService()
    service.register("echo", lambda args: "")

    assert service.names() == frozenset({"echo"})


def test_unregistering_withdraws_the_tool() -> None:
    service = ToolService()
    withdraw = service.register("echo", lambda args: "")

    withdraw()

    assert service.names() == frozenset()


def test_withdrawing_twice_is_harmless() -> None:
    service = ToolService()
    withdraw = service.register("echo", lambda args: "")

    withdraw()
    withdraw()

    assert service.names() == frozenset()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/agent/test_tools.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'minion_agent.agent.tools'`

- [ ] **Step 3: Write the implementation**

Create `src/minion_agent/agent/tools.py`:

```python
"""A trivial tool service: enough for the loop to close a round trip.

Plan 4 replaces this with the real registry — scoped registration, the
`tools/*` waterfalls, batching, execution modes, streaming results, and the
`terminate` fold. What matters here is the contract the loop depends on:

    every tool call produces exactly one tool result

A failure is an error *result*, never an exception. A call without a result
leaves the transcript incoherent, and the model would be asked to continue
from a conversation that does not make sense.
"""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from typing import Any

from ..llm import TextBlock, ToolCallBlock, ToolResultMessage

type ToolFn = Callable[[dict[str, Any]], Awaitable[str] | str]


class ToolService:
    """Maps tool names to callables."""

    __service_name__ = "tools"

    def __init__(self) -> None:
        self._tools: dict[str, ToolFn] = {}

    def register(self, name: str, fn: ToolFn) -> Callable[[], None]:
        """Register `fn` under `name`; returns a withdrawal handle."""
        self._tools[name] = fn

        def withdraw() -> None:
            if self._tools.get(name) is fn:
                del self._tools[name]

        return withdraw

    def names(self) -> frozenset[str]:
        return frozenset(self._tools)

    @staticmethod
    def _result(call: ToolCallBlock, text: str, *, is_error: bool) -> ToolResultMessage:
        return ToolResultMessage(
            tool_call_id=call.id,
            content=(TextBlock(text=text),),
            timestamp=0,
            is_error=is_error,
        )

    async def execute(self, call: ToolCallBlock) -> ToolResultMessage:
        """Run `call`, returning a result whether it succeeds or fails."""
        fn = self._tools.get(call.name)
        if fn is None:
            return self._result(
                call, f"unknown tool {call.name!r}", is_error=True
            )
        try:
            outcome = fn(call.arguments)
            text = await outcome if inspect.isawaitable(outcome) else outcome
        except Exception as error:  # noqa: BLE001 - surfaced to the model, not raised
            return self._result(call, f"{type(error).__name__}: {error}", is_error=True)
        return self._result(call, str(text), is_error=False)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/agent/test_tools.py -v`
Expected: PASS — seven tests.

- [ ] **Step 5: Commit**

```bash
git add src/minion_agent/agent/tools.py tests/agent/test_tools.py
git commit -m "feat: add a trivial tool service with total result coverage"
```

---

## Task 6: The agent instance

**Files:**
- Create: `src/minion_agent/agent/instance.py`
- Test: `tests/agent/test_instance.py`

**Interfaces:**
- Produces:
  - `class AgentInstance` with `id`, `definition`, `log: SessionLog`, `inbox: Inbox`, `status: AgentStatus`, `scope: Scope`, and `on_status_change` hook
  - `set_status(status)` emits `agent/status` scoped to the instance and fires the hook
  - `instance_scope_key(definition, instance_id) -> ScopeKey` — a child of the definition's scope

- [ ] **Step 1: Write the failing test**

Create `tests/agent/test_instance.py`:

```python
"""An instance is one live execution identity."""

from minion_agent.agent.identity import AgentDefinition, AgentStatus
from minion_agent.agent.instance import AgentInstance, instance_scope_key
from minion_agent.llm import ModelId
from minion_agent.runtime import Context, scope_of
from minion_agent.session import SessionLog


def _definition() -> AgentDefinition:
    return AgentDefinition(name="ada", model=ModelId("mock", "mock-1"))


def _instance(ctx: Context | None = None) -> AgentInstance:
    context = ctx or Context()
    return AgentInstance(
        instance_id="room-a",
        definition=_definition(),
        log=SessionLog("room-a"),
        ctx=context,
    )


def test_an_instance_starts_idle() -> None:
    assert _instance().status is AgentStatus.IDLE


def test_an_instance_owns_its_log_and_inbox() -> None:
    first, second = _instance(), _instance()

    first.inbox.followup.__self__  # smoke: each has its own inbox
    assert first.inbox is not second.inbox
    assert first.log is not second.log


def test_instances_of_one_definition_share_its_configuration() -> None:
    first, second = _instance(), _instance()

    assert first.definition.name == second.definition.name


def test_the_instance_scope_is_a_child_of_the_definition_scope() -> None:
    """So definition-level registrations are visible to every instance, and
    instance-level ones are not visible to siblings."""
    key = instance_scope_key(_definition(), "room-a")

    assert key.name == "agent-instance:room-a"
    assert key.parent is not None
    assert key.parent.name == "agent-definition:ada"


def test_the_instance_context_carries_its_scope() -> None:
    instance = _instance()

    assert scope_of(instance.scope.ctx) is instance.scope.key


def test_status_changes_fire_the_hook() -> None:
    instance = _instance()
    seen: list[AgentStatus] = []
    instance.on_status_change = seen.append

    instance.set_status(AgentStatus.RUNNING)
    instance.set_status(AgentStatus.IDLE)

    assert seen == [AgentStatus.RUNNING, AgentStatus.IDLE]


def test_setting_the_same_status_twice_reports_once() -> None:
    """A transition signal must signal transitions, not assignments."""
    instance = _instance()
    seen: list[AgentStatus] = []
    instance.on_status_change = seen.append

    instance.set_status(AgentStatus.RUNNING)
    instance.set_status(AgentStatus.RUNNING)

    assert seen == [AgentStatus.RUNNING]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/agent/test_instance.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'minion_agent.agent.instance'`

- [ ] **Step 3: Write the implementation**

Create `src/minion_agent/agent/instance.py`:

```python
"""One live execution identity: inbox, log, turn state, scope."""

from __future__ import annotations

from collections.abc import Callable

from ..runtime import Context, ScopeKey
from ..session import SessionLog
from .events import AGENT_STATUS, declare_agent_events
from .identity import AgentDefinition, AgentInstanceId, AgentStatus
from .inbox import Inbox


def instance_scope_key(definition: AgentDefinition, instance_id: str) -> ScopeKey:
    """The scope an instance registers through.

    A child of the definition's scope, so definition-level registrations are
    visible to every instance while instance-level ones stay private to one
    (design spec section 3).
    """
    return ScopeKey(
        f"agent-instance:{instance_id}", parent=ScopeKey(definition.scope_name)
    )


class AgentInstance:
    """One conversation with one agent."""

    def __init__(
        self,
        *,
        instance_id: AgentInstanceId,
        definition: AgentDefinition,
        log: SessionLog,
        ctx: Context,
    ) -> None:
        self.id = instance_id
        self.definition = definition
        self.log = log
        self.inbox = Inbox()
        self._status = AgentStatus.IDLE
        self.on_status_change: Callable[[AgentStatus], None] | None = None

        declare_agent_events(ctx.events)
        self.scope = ctx.scope(instance_scope_key(definition, instance_id))
        self._ctx = self.scope.ctx

    @property
    def ctx(self) -> Context:
        """This instance's scoped context."""
        return self._ctx

    @property
    def status(self) -> AgentStatus:
        return self._status

    def set_status(self, status: AgentStatus) -> None:
        """Record a status transition and announce it.

        A no-op when the status is unchanged: `agent/status` is a transition
        signal, and emitting it for an assignment would make "settled" mean
        two different things.
        """
        if status is self._status:
            return
        self._status = status
        self._ctx.events.emit(AGENT_STATUS, self, status, scope=self.scope.key)
        if self.on_status_change is not None:
            self.on_status_change(status)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/agent/test_instance.py -v`
Expected: PASS — seven tests.

- [ ] **Step 5: Commit**

```bash
git add src/minion_agent/agent/instance.py tests/agent/test_instance.py
git commit -m "feat: add the agent instance with its scope and status signal"
```

---

## Task 7: The agents registry and handles

**Files:**
- Create: `src/minion_agent/agent/registry.py`
- Test: `tests/agent/test_registry.py`

**Interfaces:**
- Produces:
  - `class AgentHandle` with `instance: AgentInstance` and `async dispose() -> None` (idempotent)
  - `class AgentRegistry` with `__service_name__ = "agents"`, `create(instance_id, definition) -> AgentHandle`, `get(instance_id) -> AgentInstance | None`, `instances() -> tuple[AgentInstance, ...]`
  - `create` raises `DuplicateInstanceError` for an id already live.
  - Disposing a handle removes the instance and disposes its scope.

- [ ] **Step 1: Write the failing test**

Create `tests/agent/test_registry.py`:

```python
"""The registry owns instances; a handle owns exactly one instance's teardown."""

import pytest

from minion_agent.agent.identity import AgentDefinition
from minion_agent.agent.registry import AgentRegistry, DuplicateInstanceError
from minion_agent.llm import ModelId
from minion_agent.runtime import Context
from minion_agent.session import SessionService


def _definition(name: str = "ada") -> AgentDefinition:
    return AgentDefinition(name=name, model=ModelId("mock", "mock-1"))


def _registry() -> AgentRegistry:
    return AgentRegistry(ctx=Context(), sessions=SessionService())


async def test_create_returns_a_handle_to_a_live_instance() -> None:
    registry = _registry()

    handle = registry.create("room-a", _definition())

    assert handle.instance.id == "room-a"
    assert registry.get("room-a") is handle.instance


async def test_many_instances_share_one_definition() -> None:
    registry = _registry()
    definition = _definition()

    first = registry.create("room-a", definition)
    second = registry.create("room-b", definition)

    assert first.instance.definition is second.instance.definition
    assert first.instance is not second.instance


async def test_each_instance_gets_its_own_session_log() -> None:
    registry = _registry()

    first = registry.create("room-a", _definition())
    second = registry.create("room-b", _definition())

    assert first.instance.log is not second.instance.log
    assert first.instance.log.session_id == "room-a"


async def test_a_duplicate_id_is_rejected() -> None:
    registry = _registry()
    registry.create("room-a", _definition())

    with pytest.raises(DuplicateInstanceError, match="room-a"):
        registry.create("room-a", _definition())


async def test_disposing_a_handle_removes_the_instance() -> None:
    registry = _registry()
    handle = registry.create("room-a", _definition())

    await handle.dispose()

    assert registry.get("room-a") is None
    assert registry.instances() == ()


async def test_disposing_twice_is_harmless() -> None:
    registry = _registry()
    handle = registry.create("room-a", _definition())

    await handle.dispose()
    await handle.dispose()


async def test_disposing_one_instance_leaves_its_siblings_alone() -> None:
    registry = _registry()
    first = registry.create("room-a", _definition())
    registry.create("room-b", _definition())

    await first.dispose()

    assert registry.get("room-b") is not None


async def test_disposing_unwinds_instance_scoped_registrations() -> None:
    registry = _registry()
    handle = registry.create("room-a", _definition())
    order: list[str] = []
    handle.instance.ctx.effect(lambda: lambda: order.append("scoped"), "scoped")

    await handle.dispose()

    assert order == ["scoped"]


async def test_the_id_becomes_reusable_after_disposal() -> None:
    registry = _registry()
    handle = registry.create("room-a", _definition())
    await handle.dispose()

    reborn = registry.create("room-a", _definition())

    assert reborn.instance is not handle.instance
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/agent/test_registry.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'minion_agent.agent.registry'`

- [ ] **Step 3: Write the implementation**

Create `src/minion_agent/agent/registry.py`:

```python
"""`ctx.agents`: creating instances and owning their teardown."""

from __future__ import annotations

from ..runtime import Context
from ..session import SessionService
from .identity import AgentDefinition, AgentInstanceId
from .instance import AgentInstance


class DuplicateInstanceError(ValueError):
    """An instance id was reused while the first one is still live."""


class AgentHandle:
    """The teardown capability for exactly one instance.

    Bound to the instance it was issued for, so a stale handle cannot remove a
    later instance that happens to reuse the id.
    """

    __slots__ = ("_disposed", "_registry", "instance")

    def __init__(self, registry: AgentRegistry, instance: AgentInstance) -> None:
        self._registry = registry
        self.instance = instance
        self._disposed = False

    async def dispose(self) -> None:
        """Remove the instance and unwind its scope. Idempotent."""
        if self._disposed:
            return
        self._disposed = True
        await self._registry._detach(self.instance)


class AgentRegistry:
    """Owns every live agent instance."""

    __service_name__ = "agents"

    def __init__(self, ctx: Context, sessions: SessionService) -> None:
        self._ctx = ctx
        self._sessions = sessions
        self._instances: dict[AgentInstanceId, AgentInstance] = {}

    def create(
        self, instance_id: AgentInstanceId, definition: AgentDefinition
    ) -> AgentHandle:
        """Create a live instance of `definition` under `instance_id`."""
        if instance_id in self._instances:
            raise DuplicateInstanceError(f"instance {instance_id!r} is already live")

        instance = AgentInstance(
            instance_id=instance_id,
            definition=definition,
            log=self._sessions.create(instance_id),
            ctx=self._ctx,
        )
        self._instances[instance_id] = instance
        return AgentHandle(self, instance)

    def get(self, instance_id: AgentInstanceId) -> AgentInstance | None:
        return self._instances.get(instance_id)

    def instances(self) -> tuple[AgentInstance, ...]:
        return tuple(self._instances.values())

    async def _detach(self, instance: AgentInstance) -> None:
        """Remove `instance` if it is still the live one for its id."""
        if self._instances.get(instance.id) is instance:
            del self._instances[instance.id]
        await instance.scope.dispose()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/agent/test_registry.py -v`
Expected: PASS — nine tests.

- [ ] **Step 5: Commit**

```bash
git add src/minion_agent/agent/registry.py tests/agent/test_registry.py
git commit -m "feat: add the agents registry with owning handles"
```

---

## Task 8: The driver — one turn, one step

The smallest complete loop: claim a prompt, run one model request, log it,
close the turn. Tools, steering, and cancellation layer on in Tasks 9–12.

**Files:**
- Create: `src/minion_agent/agent_loop/__init__.py`, `src/minion_agent/agent_loop/driver.py`
- Test: `tests/agent_loop/test_single_turn.py`

**Interfaces:**
- Produces:
  - `class AgentLoop` with `__init__(self, *, instance, llm, tools, artifacts, telemetry=None)`, `async run_until_idle() -> None`, and `next_turn_policy` / `next_step_policy` (both `ONE_AT_A_TIME` by default)
  - `run_until_idle` drains the inbox: it opens turns while input is pending, then returns with the instance idle.
- Log shape per turn: `turn/start` (carrying `causes`), `step/start`, `request/header`, `assistant/message`, `step/end`, `turn/end`. Claimed prompts are appended as `user/message` before the request.

- [ ] **Step 1: Write the failing test**

Create `tests/agent_loop/test_single_turn.py`:

```python
"""One prompt in, one model request, one logged turn."""

from minion_agent.agent.identity import AgentDefinition, AgentStatus
from minion_agent.agent.registry import AgentRegistry
from minion_agent.agent.tools import ToolService
from minion_agent.agent_loop.driver import AgentLoop
from minion_agent.llm import LlmService, ModelId, TextBlock, UserMessage, text_of
from minion_agent.llm.adapters.mock import MockAdapter, ScriptedResponse
from minion_agent.llm.messages import StopReason
from minion_agent.runtime import Context
from minion_agent.session import ArtifactStore, EventKind, SessionService, derive_messages


def _loop(*responses: ScriptedResponse) -> AgentLoop:
    ctx = Context()
    sessions = SessionService()
    llm = LlmService()
    llm.register(MockAdapter(list(responses)))
    registry = AgentRegistry(ctx=ctx, sessions=sessions)
    handle = registry.create(
        "room-a",
        AgentDefinition(name="ada", model=ModelId("mock", "mock-1"), system="be helpful"),
    )
    return AgentLoop(
        instance=handle.instance,
        llm=llm,
        tools=ToolService(),
        artifacts=sessions.artifacts,
    )


def _say(text: str) -> UserMessage:
    return UserMessage(content=(TextBlock(text=text),), timestamp=1)


async def test_a_prompt_produces_one_assistant_message() -> None:
    loop = _loop(ScriptedResponse((TextBlock(text="hi there"),), StopReason.STOP))
    loop.instance.inbox.followup(_say("hello"))

    await loop.run_until_idle()

    derived = derive_messages(loop.instance.log)
    assert [text_of(message) for message in derived] == ["hello", "hi there"]


async def test_the_turn_is_logged_in_order() -> None:
    loop = _loop(ScriptedResponse((TextBlock(text="hi"),), StopReason.STOP))
    loop.instance.inbox.followup(_say("hello"))

    await loop.run_until_idle()

    kinds = [event.kind for event in loop.instance.log.events]
    assert kinds == [
        EventKind.TURN_START,
        EventKind.USER_MESSAGE,
        EventKind.STEP_START,
        EventKind.REQUEST_HEADER,
        EventKind.ASSISTANT_MESSAGE,
        EventKind.STEP_END,
        EventKind.TURN_END,
    ]


async def test_the_instance_returns_to_idle() -> None:
    loop = _loop(ScriptedResponse((), StopReason.STOP))
    loop.instance.inbox.followup(_say("hello"))

    await loop.run_until_idle()

    assert loop.instance.status is AgentStatus.IDLE


async def test_status_transitions_are_announced_once_each_way() -> None:
    loop = _loop(ScriptedResponse((), StopReason.STOP))
    seen: list[AgentStatus] = []
    loop.instance.on_status_change = seen.append
    loop.instance.inbox.followup(_say("hello"))

    await loop.run_until_idle()

    assert seen == [AgentStatus.RUNNING, AgentStatus.IDLE]


async def test_an_empty_inbox_runs_nothing() -> None:
    loop = _loop()

    await loop.run_until_idle()

    assert len(loop.instance.log) == 0
    assert loop.instance.status is AgentStatus.IDLE


async def test_the_request_carries_the_definition_system_prompt() -> None:
    loop = _loop(ScriptedResponse((), StopReason.STOP))
    loop.instance.inbox.followup(_say("hello"))

    await loop.run_until_idle()

    header = next(
        event
        for event in loop.instance.log.events
        if event.kind is EventKind.REQUEST_HEADER
    )
    assert header.data["components"]["system_base"].startswith("sha256:")


async def test_the_logged_header_reconstructs_what_was_dispatched() -> None:
    """The invariant §5 exists for: the model saw what the log says."""
    from minion_agent.session import assemble_system, reconstruct_header

    store = ArtifactStore()
    ctx = Context()
    sessions = SessionService()
    llm = LlmService()
    adapter = MockAdapter([ScriptedResponse((), StopReason.STOP)])
    llm.register(adapter)
    registry = AgentRegistry(ctx=ctx, sessions=sessions)
    handle = registry.create(
        "room-a",
        AgentDefinition(name="ada", model=ModelId("mock", "mock-1"), system="be helpful"),
    )
    loop = AgentLoop(
        instance=handle.instance, llm=llm, tools=ToolService(), artifacts=store
    )
    handle.instance.inbox.followup(_say("hello"))

    await loop.run_until_idle()

    header = next(
        event
        for event in handle.instance.log.events
        if event.kind is EventKind.REQUEST_HEADER
    )
    assert assemble_system(reconstruct_header(header, store)) == adapter.requests[0].system
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/agent_loop/test_single_turn.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'minion_agent.agent_loop'`

- [ ] **Step 3: Write the driver**

Create `src/minion_agent/agent_loop/__init__.py` with a docstring, and
`src/minion_agent/agent_loop/driver.py`:

```python
"""The concrete agent loop.

Imperative and package-internal, following DSH's `ReactLoopAgent`: a stateful
class with an explicit phase. Neither pi nor DSH factors the live loop as a
pure reducer, and this design does not invent one.

A **step** is one model request plus the tools it calls. A **turn** is zero or
more steps.
"""

from __future__ import annotations

from ..agent.decisions import Enter, PreStepReason
from ..agent.envelope import ClaimPolicy, InboxTarget, InputEnvelope
from ..agent.identity import AgentStatus
from ..agent.instance import AgentInstance
from ..agent.tools import ToolService
from ..llm import LlmService, Request, collect
from ..session import ArtifactStore, EventKind, encode_message, record_header
from ..session.derive import derive_messages
from ..telemetry import TelemetryService


class AgentLoop:
    """Drives one agent instance through turns and steps."""

    def __init__(
        self,
        *,
        instance: AgentInstance,
        llm: LlmService,
        tools: ToolService,
        artifacts: ArtifactStore,
        telemetry: TelemetryService | None = None,
    ) -> None:
        self.instance = instance
        # Collaborators are public: tests configure them directly, and Plan 4
        # replaces the tool service outright.
        self.llm = llm
        self.tools = tools
        self.artifacts = artifacts
        self.telemetry = telemetry
        self.next_turn_policy = ClaimPolicy.ONE_AT_A_TIME
        self.next_step_policy = ClaimPolicy.ONE_AT_A_TIME
        self._cancelled = False

    async def run_until_idle(self) -> None:
        """Open turns while input is pending, then settle idle."""
        inbox = self.instance.inbox
        if not inbox.pending(InboxTarget.NEXT_TURN):
            inbox.take_wake()
            return

        self.instance.set_status(AgentStatus.RUNNING)
        try:
            while inbox.pending(InboxTarget.NEXT_TURN):
                await self._run_turn()
        finally:
            inbox.take_wake()
            self.instance.set_status(AgentStatus.IDLE)

    async def _run_turn(self) -> None:
        log = self.instance.log
        claimed = self.instance.inbox.claim(
            InboxTarget.NEXT_TURN, self.next_turn_policy
        )
        log.append(
            EventKind.TURN_START,
            {"causes": [{"id": e.id, "origin": e.origin} for e in claimed]},
        )

        decision = Enter(messages=tuple(envelope.message for envelope in claimed))
        await self._run_step(decision, PreStepReason.INITIAL)

        log.append(EventKind.TURN_END, {"reason": "completed"})

    async def _run_step(self, decision: Enter, reason: PreStepReason) -> None:
        log = self.instance.log
        log.append(EventKind.STEP_START, {"reason": reason.value})

        for message in decision.messages:
            log.append(EventKind.USER_MESSAGE, {"message": encode_message(message)})

        components = {
            "system_base": decision.system_override
            if decision.system_override is not None
            else self.instance.definition.system
        }
        record_header(
            log, self.artifacts, components, model=self.instance.definition.model.model
        )

        from ..session.request_header import assemble_system

        history = derive_messages(log)
        if decision.history_window is not None:
            history = history[-decision.history_window :]

        message = await collect(
            self.llm.stream(
                Request(
                    model=self.instance.definition.model,
                    system=assemble_system(components),
                    messages=history,
                )
            )
        )
        log.append(EventKind.ASSISTANT_MESSAGE, {"message": encode_message(message)})
        log.append(EventKind.STEP_END, {})
```

Note the import of `assemble_system` inside the method is a placeholder for
readability while the module is small; hoist it to the module imports and
confirm ruff is clean.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/agent_loop/test_single_turn.py -v`
Expected: PASS — seven tests.

The derivation ordering is the subtle part: the claimed prompt must be logged
*before* the request is built, or the model will not see it. The first test
catches this directly.

- [ ] **Step 5: Commit**

```bash
git add src/minion_agent/agent_loop tests/agent_loop
git commit -m "feat: add the agent loop driver for a single-step turn"
```

---

## Task 9: Turn provenance

**Files:**
- Modify: `src/minion_agent/agent_loop/driver.py`
- Test: `tests/agent_loop/test_provenance.py`

**Interfaces:**
- Produces: `turn/start` carries `causes: [{id, origin}, …]` for every claimed envelope; `turn/end` repeats them so a consumer reading only completions can route.
- Under `ClaimPolicy.ALL`, one turn carries several causes — the case a singular `turn.origin` could not express.

- [ ] **Step 1: Write the failing test**

Create `tests/agent_loop/test_provenance.py`:

```python
"""Inputs carry provenance; turns carry their causal inputs."""

from minion_agent.agent.envelope import ClaimPolicy
from minion_agent.llm.messages import StopReason
from minion_agent.llm import TextBlock, UserMessage
from minion_agent.llm.adapters.mock import ScriptedResponse
from minion_agent.session import EventKind

from .test_single_turn import _loop


def _say(text: str) -> UserMessage:
    return UserMessage(content=(TextBlock(text=text),), timestamp=1)


def _causes(loop, kind=EventKind.TURN_START) -> list[dict]:  # noqa: ANN001
    return [
        event.data["causes"] for event in loop.instance.log.events if event.kind is kind
    ]


async def test_a_turn_records_the_origin_of_its_input() -> None:
    loop = _loop(ScriptedResponse((), StopReason.STOP))
    loop.instance.inbox.followup(_say("hello"), origin={"channel": "matrix"})

    await loop.run_until_idle()

    assert _causes(loop)[0][0]["origin"] == {"channel": "matrix"}


async def test_claim_all_gives_one_turn_several_causes() -> None:
    """The case a singular turn.origin could not express."""
    loop = _loop(ScriptedResponse((), StopReason.STOP))
    loop.next_turn_policy = ClaimPolicy.ALL
    loop.instance.inbox.followup(_say("one"), origin="a")
    loop.instance.inbox.followup(_say("two"), origin="b")
    loop.instance.inbox.followup(_say("three"), origin="c")

    await loop.run_until_idle()

    causes = _causes(loop)
    assert len(causes) == 1
    assert [cause["origin"] for cause in causes[0]] == ["a", "b", "c"]


async def test_one_at_a_time_gives_each_turn_one_cause() -> None:
    loop = _loop(
        ScriptedResponse((), StopReason.STOP), ScriptedResponse((), StopReason.STOP)
    )
    loop.instance.inbox.followup(_say("one"), origin="a")
    loop.instance.inbox.followup(_say("two"), origin="b")

    await loop.run_until_idle()

    causes = _causes(loop)
    assert [[c["origin"] for c in turn] for turn in causes] == [["a"], ["b"]]


async def test_causes_survive_to_turn_end() -> None:
    """A consumer reading only completions can still route the result."""
    loop = _loop(ScriptedResponse((), StopReason.STOP))
    loop.instance.inbox.followup(_say("hello"), origin={"room": "!abc"})

    await loop.run_until_idle()

    assert _causes(loop, EventKind.TURN_END)[0][0]["origin"] == {"room": "!abc"}


async def test_envelope_ids_are_carried_alongside_origins() -> None:
    loop = _loop(ScriptedResponse((), StopReason.STOP))
    envelope = loop.instance.inbox.followup(_say("hello"))

    await loop.run_until_idle()

    assert _causes(loop)[0][0]["id"] == envelope.id


async def test_a_turn_with_no_origin_still_records_its_cause() -> None:
    """A proactive turn has provenance even when the origin is null."""
    loop = _loop(ScriptedResponse((), StopReason.STOP))
    loop.instance.inbox.followup(_say("scheduled work"))

    await loop.run_until_idle()

    assert _causes(loop)[0][0]["origin"] is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/agent_loop/test_provenance.py -v`
Expected: FAIL — `turn/end` carries no `causes` yet.

- [ ] **Step 3: Carry causes through the turn**

In `driver.py`'s `_run_turn`, hold the causes and log them at both ends:

```python
    async def _run_turn(self) -> None:
        log = self.instance.log
        claimed = self.instance.inbox.claim(
            InboxTarget.NEXT_TURN, self.next_turn_policy
        )
        causes = [{"id": envelope.id, "origin": envelope.origin} for envelope in claimed]
        log.append(EventKind.TURN_START, {"causes": causes})

        decision = Enter(messages=tuple(envelope.message for envelope in claimed))
        await self._run_step(decision, PreStepReason.INITIAL)

        # Repeated at the end so a consumer reading only completions can route
        # a result without replaying the whole turn.
        log.append(EventKind.TURN_END, {"reason": "completed", "causes": causes})
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/agent_loop -v`
Expected: PASS — the provenance suite plus the single-turn suite.

- [ ] **Step 5: Commit**

```bash
git add src/minion_agent/agent_loop tests/agent_loop/test_provenance.py
git commit -m "feat: carry input provenance through the turn"
```

---

## Task 10: The tool round trip

The milestone §9 names: mock LLM → tool_call → loop → mock tool result →
second request.

**Files:**
- Modify: `src/minion_agent/agent_loop/driver.py`
- Test: `tests/agent_loop/test_tool_round_trip.py`

**Interfaces:**
- Produces: when an assistant message stops with `TOOL_USE`, the loop logs one `tool/call` per call, executes each sequentially, logs each `tool/result`, and runs another step with reason `TOOL_RESULTS`.
- `definition.max_steps` bounds the loop; exceeding it ends the turn with reason `max_steps`.

- [ ] **Step 1: Write the failing test**

Create `tests/agent_loop/test_tool_round_trip.py`:

```python
"""The Phase 3 milestone: a tool call closes and the model is asked again."""

from minion_agent.llm import TextBlock, ToolCallBlock, UserMessage, text_of
from minion_agent.llm.adapters.mock import ScriptedResponse
from minion_agent.llm.messages import StopReason
from minion_agent.session import EventKind, derive_messages

from .test_single_turn import _loop


def _say(text: str) -> UserMessage:
    return UserMessage(content=(TextBlock(text=text),), timestamp=1)


def _tool_call(name: str = "echo", **arguments: object) -> ScriptedResponse:
    return ScriptedResponse(
        (ToolCallBlock(id="t1", name=name, arguments=dict(arguments)),),
        StopReason.TOOL_USE,
    )


async def test_a_tool_call_is_executed_and_answered() -> None:
    loop = _loop(
        _tool_call(value="pong"),
        ScriptedResponse((TextBlock(text="all done"),), StopReason.STOP),
    )
    loop.tools.register("echo", lambda args: str(args["value"]))
    loop.instance.inbox.followup(_say("ping"))

    await loop.run_until_idle()

    assert [text_of(m) for m in derive_messages(loop.instance.log)] == [
        "ping",
        "",
        "pong",
        "all done",
    ]


async def test_the_model_is_asked_again_after_the_result() -> None:
    loop = _loop(
        _tool_call(value="pong"),
        ScriptedResponse((TextBlock(text="done"),), StopReason.STOP),
    )
    loop.tools.register("echo", lambda args: str(args["value"]))
    loop.instance.inbox.followup(_say("ping"))

    await loop.run_until_idle()

    steps = [e for e in loop.instance.log.events if e.kind is EventKind.STEP_START]
    assert [step.data["reason"] for step in steps] == ["initial", "tool_results"]


async def test_the_call_and_its_result_are_both_logged() -> None:
    loop = _loop(
        _tool_call(value="pong"), ScriptedResponse((), StopReason.STOP)
    )
    loop.tools.register("echo", lambda args: str(args["value"]))
    loop.instance.inbox.followup(_say("ping"))

    await loop.run_until_idle()

    kinds = [e.kind for e in loop.instance.log.events]
    assert EventKind.TOOL_CALL in kinds
    assert EventKind.TOOL_RESULT in kinds
    assert kinds.index(EventKind.TOOL_CALL) < kinds.index(EventKind.TOOL_RESULT)


async def test_an_unknown_tool_still_closes_the_loop() -> None:
    """Every call gets a result, so the transcript stays coherent."""
    loop = _loop(
        _tool_call("missing"), ScriptedResponse((TextBlock(text="ok"),), StopReason.STOP)
    )
    loop.instance.inbox.followup(_say("ping"))

    await loop.run_until_idle()

    derived = derive_messages(loop.instance.log)
    assert "unknown tool" in text_of(derived[2])
    assert text_of(derived[-1]) == "ok"


async def test_several_calls_in_one_message_each_get_a_result() -> None:
    loop = _loop(
        ScriptedResponse(
            (
                ToolCallBlock(id="t1", name="echo", arguments={"value": "one"}),
                ToolCallBlock(id="t2", name="echo", arguments={"value": "two"}),
            ),
            StopReason.TOOL_USE,
        ),
        ScriptedResponse((), StopReason.STOP),
    )
    loop.tools.register("echo", lambda args: str(args["value"]))
    loop.instance.inbox.followup(_say("ping"))

    await loop.run_until_idle()

    results = [e for e in loop.instance.log.events if e.kind is EventKind.TOOL_RESULT]
    assert len(results) == 2


async def test_max_steps_bounds_a_runaway_tool_loop() -> None:
    """A model that only ever calls tools must not spin forever."""
    loop = _loop(*[_tool_call(value="again") for _ in range(20)])
    loop.instance.definition = type(loop.instance.definition)(  # rebuild frozen
        name="ada",
        model=loop.instance.definition.model,
        system="",
        max_steps=3,
    )
    loop.tools.register("echo", lambda args: "again")
    loop.instance.inbox.followup(_say("ping"))

    await loop.run_until_idle()

    steps = [e for e in loop.instance.log.events if e.kind is EventKind.STEP_START]
    assert len(steps) == 3

    end = next(e for e in loop.instance.log.events if e.kind is EventKind.TURN_END)
    assert end.data["reason"] == "max_steps"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/agent_loop/test_tool_round_trip.py -v`
Expected: FAIL — the loop runs one step and stops.

- [ ] **Step 3: Loop over steps**

Replace `_run_turn` so it iterates, and have `_run_step` report whether tools
owe another request:

```python
    async def _run_turn(self) -> None:
        log = self.instance.log
        claimed = self.instance.inbox.claim(
            InboxTarget.NEXT_TURN, self.next_turn_policy
        )
        causes = [{"id": envelope.id, "origin": envelope.origin} for envelope in claimed]
        log.append(EventKind.TURN_START, {"causes": causes})

        decision = Enter(messages=tuple(envelope.message for envelope in claimed))
        reason = PreStepReason.INITIAL
        steps = 0
        end_reason = "completed"

        while True:
            owed = await self._run_step(decision, reason)
            steps += 1
            if not owed:
                break
            if steps >= self.instance.definition.max_steps:
                end_reason = "max_steps"
                break
            decision = Enter(messages=())
            reason = PreStepReason.TOOL_RESULTS

        log.append(EventKind.TURN_END, {"reason": end_reason, "causes": causes})
```

and in `_run_step`, after logging the assistant message:

```python
        calls = [
            block for block in message.content if isinstance(block, ToolCallBlock)
        ]
        for call in calls:
            log.append(
                EventKind.TOOL_CALL,
                {"id": call.id, "name": call.name, "arguments": call.arguments},
            )
            result = await self.tools.execute(call)
            log.append(EventKind.TOOL_RESULT, {"message": encode_message(result)})

        log.append(EventKind.STEP_END, {})
        return bool(calls)
```

Change `_run_step`'s return type to `bool` and import `ToolCallBlock`.

Sequential execution is deliberate: parallel batching, execution modes, and the
`terminate` fold are Plan 4's, and the single-call path is what closes the round
trip.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/agent_loop -v`
Expected: PASS — six round-trip tests plus the earlier suites.

- [ ] **Step 5: Commit**

```bash
git add src/minion_agent/agent_loop tests/agent_loop/test_tool_round_trip.py
git commit -m "feat: close the tool round trip and bound runaway turns"
```

---

## Task 11: Steering, injection, and the pre-step decision

**Files:**
- Modify: `src/minion_agent/agent_loop/driver.py`
- Test: `tests/agent_loop/test_pre_step.py`

**Interfaces:**
- Produces: at each step boundary the loop claims `NEXT_STEP` input by `next_step_policy` and dispatches `agent/pre-step` as a waterfall with terminal `Enter(claimed messages)`, carrying the `PreStepReason`.
- A `Reject` closes the turn with no further step; a first-claim rejection still logs a durable turn that spent no step.
- `Enter.system_override` and `Enter.history_window` apply to that step alone.

- [ ] **Step 1: Write the failing test**

Create `tests/agent_loop/test_pre_step.py`:

```python
"""agent/pre-step decides what the model sees."""

from minion_agent.agent.decisions import Enter, PreStepReason, Reject
from minion_agent.agent.events import AGENT_PRE_STEP
from minion_agent.llm import TextBlock, UserMessage, text_of
from minion_agent.llm.adapters.mock import MockAdapter, ScriptedResponse
from minion_agent.llm.messages import StopReason
from minion_agent.session import EventKind, derive_messages

from .test_single_turn import _loop


def _say(text: str) -> UserMessage:
    return UserMessage(content=(TextBlock(text=text),), timestamp=1)


async def test_the_terminal_enters_the_claimed_messages() -> None:
    """No listener at all still runs the step with what was claimed."""
    loop = _loop(ScriptedResponse((TextBlock(text="ok"),), StopReason.STOP))
    loop.instance.inbox.followup(_say("hello"))

    await loop.run_until_idle()

    assert text_of(derive_messages(loop.instance.log)[0]) == "hello"


async def test_a_listener_may_rewrite_the_entering_messages() -> None:
    loop = _loop(ScriptedResponse((), StopReason.STOP))

    async def rewrite(instance, reason, messages, next_):  # noqa: ANN001
        return await next_(instance, reason, (_say("rewritten"),))

    loop.instance.ctx.events.on(AGENT_PRE_STEP, rewrite)
    loop.instance.inbox.followup(_say("original"))

    await loop.run_until_idle()

    assert text_of(derive_messages(loop.instance.log)[0]) == "rewritten"


async def test_a_rejection_closes_the_turn_with_no_step() -> None:
    loop = _loop()

    async def veto(instance, reason, messages, next_):  # noqa: ANN001
        return Reject(reason="not now")

    loop.instance.ctx.events.on(AGENT_PRE_STEP, veto)
    loop.instance.inbox.followup(_say("hello"))

    await loop.run_until_idle()

    kinds = [event.kind for event in loop.instance.log.events]
    assert EventKind.STEP_START not in kinds
    assert kinds[0] is EventKind.TURN_START
    assert kinds[-1] is EventKind.TURN_END


async def test_a_rejected_turn_still_records_that_it_happened() -> None:
    """The log records the attempt, so a rejection is auditable."""
    loop = _loop()

    async def veto(instance, reason, messages, next_):  # noqa: ANN001
        return Reject(reason="quiet hours")

    loop.instance.ctx.events.on(AGENT_PRE_STEP, veto)
    loop.instance.inbox.followup(_say("hello"))

    await loop.run_until_idle()

    end = next(e for e in loop.instance.log.events if e.kind is EventKind.TURN_END)
    assert end.data["reason"] == "rejected"


async def test_the_first_step_reports_reason_initial() -> None:
    loop = _loop(ScriptedResponse((), StopReason.STOP))
    seen: list[str] = []

    async def observe(instance, reason, messages, next_):  # noqa: ANN001
        seen.append(reason.value)
        return await next_()

    loop.instance.ctx.events.on(AGENT_PRE_STEP, observe)
    loop.instance.inbox.followup(_say("hello"))

    await loop.run_until_idle()

    assert seen == [PreStepReason.INITIAL.value]


async def test_steering_is_claimed_at_the_step_boundary() -> None:
    loop = _loop(ScriptedResponse((), StopReason.STOP))
    loop.instance.inbox.followup(_say("first"))
    loop.instance.inbox.steer(_say("steered"))

    await loop.run_until_idle()

    texts = [text_of(m) for m in derive_messages(loop.instance.log)]
    assert "steered" in texts


async def test_injected_context_does_not_start_work_on_its_own() -> None:
    """Silent by design: it waits for something that does wake the driver."""
    loop = _loop()
    loop.instance.inbox.inject(_say("file changed"))

    await loop.run_until_idle()

    assert len(loop.instance.log) == 0


async def test_a_system_override_applies_to_one_step_only() -> None:
    ctx_adapter = MockAdapter(
        [ScriptedResponse((), StopReason.STOP), ScriptedResponse((), StopReason.STOP)]
    )
    loop = _loop()
    loop.llm.register(ctx_adapter)

    async def override(instance, reason, messages, next_):  # noqa: ANN001
        return Enter(messages=messages, system_override="one-off")

    dispose = loop.instance.ctx.events.on(AGENT_PRE_STEP, override)
    loop.instance.inbox.followup(_say("first"))
    await loop.run_until_idle()

    dispose()
    loop.instance.inbox.followup(_say("second"))
    await loop.run_until_idle()

    assert ctx_adapter.requests[0].system == "one-off"
    assert ctx_adapter.requests[1].system != "one-off"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/agent_loop/test_pre_step.py -v`
Expected: FAIL — no `agent/pre-step` dispatch exists yet.

- [ ] **Step 3: Dispatch pre-step**

In `_run_turn`, replace the direct `Enter` construction with a dispatch, and
handle `Reject`:

```python
        decision = await self._pre_step(
            tuple(envelope.message for envelope in claimed), PreStepReason.INITIAL
        )
        if isinstance(decision, Reject):
            log.append(
                EventKind.TURN_END,
                {"reason": "rejected", "causes": causes, "detail": decision.reason},
            )
            return
```

and before each subsequent step, claim step input and dispatch again:

```python
            step_input = self.instance.inbox.claim(
                InboxTarget.NEXT_STEP, self.next_step_policy
            )
            reason = (
                PreStepReason.STEERING if step_input else PreStepReason.TOOL_RESULTS
            )
            decision = await self._pre_step(
                tuple(envelope.message for envelope in step_input), reason
            )
            if isinstance(decision, Reject):
                end_reason = "rejected"
                break
```

Add the dispatch helper:

```python
    async def _pre_step(
        self, messages: tuple[UserMessage, ...], reason: PreStepReason
    ) -> PreStepDecision:
        """Ask listeners what should enter this step.

        The terminal continuation is `Enter(messages)` — a chain whose
        listeners all delegate runs the step with exactly what was claimed.
        """
        return await self.instance.ctx.events.waterfall(
            AGENT_PRE_STEP,
            self.instance,
            reason,
            messages,
            terminal=Enter(messages=messages),
            scope=self.instance.scope.key,
        )
```

Note the first turn also claims `NEXT_STEP` input, so steering queued before a
turn opens enters the first step rather than waiting for a second.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/agent_loop -v`
Expected: PASS — eight pre-step tests plus the earlier suites.

- [ ] **Step 5: Commit**

```bash
git add src/minion_agent/agent_loop tests/agent_loop/test_pre_step.py
git commit -m "feat: dispatch agent/pre-step with steering and per-step overrides"
```

---

## Task 12: Turn stopping and hard termination precedence

**Files:**
- Modify: `src/minion_agent/agent_loop/driver.py`
- Test: `tests/agent_loop/test_turn_stopping.py`

**Interfaces:**
- Produces: after a step whose tools owe another request, the loop dispatches `agent/turn-stopping` (serial) and folds with `resolve_stopping`.
- **Hard termination precedes it.** When the loop must stop — `max_steps` reached, or no tools owed — the event is *not dispatched at all*, and no `Continue` can override it.

- [ ] **Step 1: Write the failing test**

Create `tests/agent_loop/test_turn_stopping.py`:

```python
"""Stopping decisions, and what cannot be overridden."""

from minion_agent.agent.decisions import TurnStopping
from minion_agent.agent.events import AGENT_TURN_STOPPING
from minion_agent.llm import TextBlock, ToolCallBlock, UserMessage
from minion_agent.llm.adapters.mock import ScriptedResponse
from minion_agent.llm.messages import StopReason
from minion_agent.session import EventKind

from .test_single_turn import _loop


def _say(text: str) -> UserMessage:
    return UserMessage(content=(TextBlock(text=text),), timestamp=1)


def _tool_call() -> ScriptedResponse:
    return ScriptedResponse(
        (ToolCallBlock(id="t1", name="echo", arguments={}),), StopReason.TOOL_USE
    )


def _steps(loop) -> int:  # noqa: ANN001
    return len([e for e in loop.instance.log.events if e.kind is EventKind.STEP_START])


async def test_a_stop_decision_ends_the_turn_early() -> None:
    loop = _loop(_tool_call(), ScriptedResponse((), StopReason.STOP))
    loop.tools.register("echo", lambda args: "done")
    loop.instance.ctx.events.on(AGENT_TURN_STOPPING, lambda *_: TurnStopping.STOP)
    loop.instance.inbox.followup(_say("go"))

    await loop.run_until_idle()

    assert _steps(loop) == 1


async def test_no_opinion_continues() -> None:
    loop = _loop(_tool_call(), ScriptedResponse((), StopReason.STOP))
    loop.tools.register("echo", lambda args: "done")
    loop.instance.ctx.events.on(AGENT_TURN_STOPPING, lambda *_: TurnStopping.NO_OPINION)
    loop.instance.inbox.followup(_say("go"))

    await loop.run_until_idle()

    assert _steps(loop) == 2


async def test_no_listeners_continues() -> None:
    loop = _loop(_tool_call(), ScriptedResponse((), StopReason.STOP))
    loop.tools.register("echo", lambda args: "done")
    loop.instance.inbox.followup(_say("go"))

    await loop.run_until_idle()

    assert _steps(loop) == 2


async def test_a_stopped_turn_records_why() -> None:
    loop = _loop(_tool_call(), ScriptedResponse((), StopReason.STOP))
    loop.tools.register("echo", lambda args: "done")
    loop.instance.ctx.events.on(AGENT_TURN_STOPPING, lambda *_: TurnStopping.STOP)
    loop.instance.inbox.followup(_say("go"))

    await loop.run_until_idle()

    end = next(e for e in loop.instance.log.events if e.kind is EventKind.TURN_END)
    assert end.data["reason"] == "stopped"


async def test_the_event_is_not_dispatched_when_nothing_is_owed() -> None:
    """Hard termination precedes the decision: a turn the loop was already
    going to end never asks."""
    loop = _loop(ScriptedResponse((TextBlock(text="done"),), StopReason.STOP))
    asked: list[str] = []
    loop.instance.ctx.events.on(
        AGENT_TURN_STOPPING, lambda *_: asked.append("asked") or TurnStopping.CONTINUE
    )
    loop.instance.inbox.followup(_say("go"))

    await loop.run_until_idle()

    assert asked == []


async def test_continue_cannot_override_max_steps() -> None:
    """max_steps is a loop invariant; a plugin must not be able to defeat it."""
    loop = _loop(*[_tool_call() for _ in range(10)])
    loop.instance.definition = type(loop.instance.definition)(
        name="ada", model=loop.instance.definition.model, system="", max_steps=2
    )
    loop.tools.register("echo", lambda args: "again")
    loop.instance.ctx.events.on(AGENT_TURN_STOPPING, lambda *_: TurnStopping.CONTINUE)
    loop.instance.inbox.followup(_say("go"))

    await loop.run_until_idle()

    assert _steps(loop) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/agent_loop/test_turn_stopping.py -v`
Expected: FAIL — no stopping dispatch exists.

- [ ] **Step 3: Add the dispatch with precedence**

In `_run_turn`'s loop, after `owed` is known:

```python
            if not owed:
                break                       # hard: nothing is owed
            if steps >= self.instance.definition.max_steps:
                end_reason = "max_steps"    # hard: the bound is a loop invariant
                break

            # Only now is there a decision to make. Hard termination has
            # already been resolved, so no listener can override it.
            if await self._should_stop():
                end_reason = "stopped"
                break
```

and the helper:

```python
    async def _should_stop(self) -> bool:
        """Ask listeners whether to stop, folding by first-opinion-wins."""
        decision = await self.instance.ctx.events.serial(
            AGENT_TURN_STOPPING, self.instance, scope=self.instance.scope.key
        )
        if decision is None:
            return False
        return resolve_stopping([decision]) is TurnStopping.STOP
```

Because `serial` returns the last listener's value, `resolve_stopping` is
applied to that single value here; the fold matters once Plan 4 collects
several opinions.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/agent_loop -v`
Expected: PASS — six stopping tests plus the earlier suites.

- [ ] **Step 5: Commit**

```bash
git add src/minion_agent/agent_loop tests/agent_loop/test_turn_stopping.py
git commit -m "feat: add turn stopping with hard-termination precedence"
```

---

## Task 13: Cancellation and progress isolation

**Files:**
- Modify: `src/minion_agent/agent_loop/driver.py`
- Test: `tests/agent_loop/test_cancellation.py`

**Interfaces:**
- Produces: `AgentLoop.cancel()` requests a stop; the loop ends the current turn at the next boundary with reason `cancelled`. `cancelled` is a hard stop and precedes `agent/turn-stopping` exactly as `max_steps` does.
- Plus the normative guarantee: awaiting inside one instance must not block another. Verified by a test in which one loop blocks on a tool while a second completes a full turn.

- [ ] **Step 1: Write the failing test**

Create `tests/agent_loop/test_cancellation.py`:

```python
"""Cancellation, and the guarantee that one agent cannot stall another."""

import asyncio

from minion_agent.agent.identity import AgentDefinition
from minion_agent.agent.registry import AgentRegistry
from minion_agent.agent.tools import ToolService
from minion_agent.agent_loop.driver import AgentLoop
from minion_agent.llm import LlmService, ModelId, TextBlock, ToolCallBlock, UserMessage
from minion_agent.llm.adapters.mock import MockAdapter, ScriptedResponse
from minion_agent.llm.messages import StopReason
from minion_agent.runtime import Context
from minion_agent.session import EventKind, SessionService

from .test_single_turn import _loop


def _say(text: str) -> UserMessage:
    return UserMessage(content=(TextBlock(text=text),), timestamp=1)


def _tool_call() -> ScriptedResponse:
    return ScriptedResponse(
        (ToolCallBlock(id="t1", name="echo", arguments={}),), StopReason.TOOL_USE
    )


async def test_cancelling_ends_the_turn_at_the_next_boundary() -> None:
    loop = _loop(*[_tool_call() for _ in range(5)])
    loop.tools.register("echo", lambda args: (loop.cancel(), "done")[1])
    loop.instance.inbox.followup(_say("go"))

    await loop.run_until_idle()

    steps = [e for e in loop.instance.log.events if e.kind is EventKind.STEP_START]
    assert len(steps) == 1

    end = next(e for e in loop.instance.log.events if e.kind is EventKind.TURN_END)
    assert end.data["reason"] == "cancelled"


async def test_a_cancelled_turn_still_records_its_tool_result() -> None:
    """Cancellation stops the next request, not the work already in flight."""
    loop = _loop(_tool_call())
    loop.tools.register("echo", lambda args: (loop.cancel(), "finished")[1])
    loop.instance.inbox.followup(_say("go"))

    await loop.run_until_idle()

    results = [e for e in loop.instance.log.events if e.kind is EventKind.TOOL_RESULT]
    assert len(results) == 1


async def test_cancelling_clears_so_the_next_turn_runs() -> None:
    loop = _loop(
        _tool_call(),
        ScriptedResponse((TextBlock(text="second turn"),), StopReason.STOP),
    )
    loop.tools.register("echo", lambda args: (loop.cancel(), "done")[1])
    loop.instance.inbox.followup(_say("first"))
    await loop.run_until_idle()

    loop.instance.inbox.followup(_say("second"))
    await loop.run_until_idle()

    ends = [e for e in loop.instance.log.events if e.kind is EventKind.TURN_END]
    assert [end.data["reason"] for end in ends] == ["cancelled", "completed"]


async def test_a_blocked_agent_does_not_stall_another() -> None:
    """The normative progress guarantee (§6). An await inside one instance
    must never occupy a runtime-global critical section."""
    ctx = Context()
    sessions = SessionService()
    llm = LlmService()
    llm.register(MockAdapter([ScriptedResponse((), StopReason.STOP)] * 8))
    registry = AgentRegistry(ctx=ctx, sessions=sessions)
    definition = AgentDefinition(name="ada", model=ModelId("mock", "mock-1"))

    released = asyncio.Event()
    blocked_tools = ToolService()

    async def wait_for_release(args: dict[str, object]) -> str:
        await released.wait()
        return "released"

    blocked_tools.register("echo", wait_for_release)

    blocked = AgentLoop(
        instance=registry.create("blocked", definition).instance,
        llm=llm,
        tools=blocked_tools,
        artifacts=sessions.artifacts,
    )
    free = AgentLoop(
        instance=registry.create("free", definition).instance,
        llm=llm,
        tools=ToolService(),
        artifacts=sessions.artifacts,
    )

    blocked.instance.inbox.followup(_say("blocked"))
    free.instance.inbox.followup(_say("free"))

    blocked_task = asyncio.create_task(blocked.run_until_idle())
    await free.run_until_idle()          # completes while the other is stuck

    assert len(free.instance.log) > 0
    assert not blocked_task.done()

    released.set()
    await blocked_task
```

The blocked agent's model must return a tool call for it to reach the tool; adjust
the script in `_loop` accordingly if the fixture does not already.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/agent_loop/test_cancellation.py -v`
Expected: FAIL — `AttributeError: 'AgentLoop' object has no attribute 'cancel'`

- [ ] **Step 3: Add cancellation**

`AgentLoop.__init__` already declares `self._cancelled = False` (Task 8). Add
the request method:

```python
    def cancel(self) -> None:
        """Request that the current turn end at its next boundary.

        Work already in flight — a running tool, an open request — is allowed
        to finish, so the transcript stays coherent. Cancellation stops the
        *next* request, not the current one.
        """
        self._cancelled = True
```

In `_run_turn`'s loop, check it alongside the other hard stops, before the
stopping dispatch:

```python
            if self._cancelled:
                end_reason = "cancelled"
                break
```

and clear it when the turn ends, so a cancelled turn does not poison the next:

```python
        self._cancelled = False
        log.append(EventKind.TURN_END, {"reason": end_reason, "causes": causes})
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/agent_loop -v`
Expected: PASS — four cancellation tests plus the earlier suites.

- [ ] **Step 5: Commit**

```bash
git add src/minion_agent/agent_loop tests/agent_loop/test_cancellation.py
git commit -m "feat: add cancellation and prove agent progress isolation"
```

---

## Task 14: Telemetry from the loop

**Files:**
- Modify: `src/minion_agent/agent_loop/driver.py`
- Test: `tests/agent_loop/test_telemetry.py`

**Interfaces:**
- Produces: when a telemetry service is supplied, the loop emits a `TURN` span per turn and a `STEP` span per step, carrying the instance id and the end reason. Emission is best-effort and never affects control flow.

- [ ] **Step 1: Write the failing test**

Create `tests/agent_loop/test_telemetry.py`:

```python
"""The loop reports; telemetry never reports back."""

from minion_agent.llm import TextBlock, UserMessage
from minion_agent.llm.adapters.mock import ScriptedResponse
from minion_agent.llm.messages import StopReason
from minion_agent.telemetry import SpanKind, TelemetryService
from minion_agent.telemetry.service import RecordingSink

from .test_single_turn import _loop


def _say(text: str) -> UserMessage:
    return UserMessage(content=(TextBlock(text=text),), timestamp=1)


def _with_telemetry(loop):  # noqa: ANN001, ANN202
    service = TelemetryService()
    service.recording = RecordingSink()
    service.add_sink(service.recording)
    loop.telemetry = service
    return service


async def test_a_turn_emits_a_turn_span() -> None:
    loop = _loop(ScriptedResponse((), StopReason.STOP))
    telemetry = _with_telemetry(loop)
    loop.instance.inbox.followup(_say("hello"))

    await loop.run_until_idle()

    kinds = [span.kind for span in telemetry.recording.spans]
    assert SpanKind.TURN in kinds
    assert SpanKind.STEP in kinds


async def test_spans_identify_their_instance() -> None:
    loop = _loop(ScriptedResponse((), StopReason.STOP))
    telemetry = _with_telemetry(loop)
    loop.instance.inbox.followup(_say("hello"))

    await loop.run_until_idle()

    turn = next(s for s in telemetry.recording.spans if s.kind is SpanKind.TURN)
    assert turn.attributes["instance"] == "room-a"
    assert turn.attributes["reason"] == "completed"


async def test_a_failing_sink_cannot_break_a_turn() -> None:
    """Telemetry is an observational projection: it must not be able to fail
    the thing it observes."""

    class Broken:
        def emit(self, span: object) -> None:
            raise RuntimeError("sink down")

    loop = _loop(ScriptedResponse((TextBlock(text="ok"),), StopReason.STOP))
    telemetry = _with_telemetry(loop)
    telemetry.add_sink(Broken())
    loop.instance.inbox.followup(_say("hello"))

    await loop.run_until_idle()

    assert len(loop.instance.log) > 0


async def test_no_telemetry_service_is_harmless() -> None:
    loop = _loop(ScriptedResponse((), StopReason.STOP))
    loop.instance.inbox.followup(_say("hello"))

    await loop.run_until_idle()

    assert len(loop.instance.log) > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/agent_loop/test_telemetry.py -v`
Expected: FAIL — no spans are emitted.

- [ ] **Step 3: Emit spans**

Add a helper and call it at each boundary:

```python
    def _span(self, kind: SpanKind, name: str, **attributes: object) -> None:
        """Emit a span if telemetry is mounted. Never affects control flow."""
        if self.telemetry is None:
            return
        self.telemetry.emit(
            Span(
                kind=kind,
                name=name,
                attributes={"instance": self.instance.id, **attributes},
            )
        )
```

Call `self._span(SpanKind.STEP, "step", reason=reason.value)` at the end of
`_run_step`, and `self._span(SpanKind.TURN, "turn", reason=end_reason)` just
before `turn/end` is appended.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/agent_loop -v`
Expected: PASS — four telemetry tests plus the earlier suites.

- [ ] **Step 5: Commit**

```bash
git add src/minion_agent/agent_loop tests/agent_loop/test_telemetry.py
git commit -m "feat: emit turn and step spans from the loop"
```

---

## Task 15: The Pi-compatible event stream

Pi's `AgentEvent` union is its public API. The log is the source of truth here,
and this projection rebuilds Pi's observable semantics from it (§6).

**Files:**
- Create: `src/minion_agent/agent/projection.py`
- Test: `tests/agent/test_projection.py`

**Interfaces:**
- Produces:
  - Event dataclasses: `AgentStart`, `AgentEnd`, `TurnStart`, `TurnEnd`, `MessageStart`, `MessageEnd`, `ToolExecutionStart`, `ToolExecutionEnd`
  - `type AgentEvent = …`
  - `def project(log: SessionLog) -> tuple[AgentEvent, ...]`
- `message_update` is deliberately absent: it requires `assistant/chunk` events the loop does not yet write. Recorded so the gap is a decision, not an oversight.

- [ ] **Step 1: Write the failing test**

Create `tests/agent/test_projection.py`:

```python
"""Pi's event stream, rebuilt from the log."""

from minion_agent.agent.projection import (
    AgentEnd,
    AgentStart,
    MessageEnd,
    MessageStart,
    ToolExecutionEnd,
    ToolExecutionStart,
    TurnEnd,
    TurnStart,
    project,
)
from minion_agent.llm import TextBlock, UserMessage
from minion_agent.session import EventKind, SessionLog, encode_message


def _log_turn(*, with_tool: bool = False) -> SessionLog:
    log = SessionLog("s1")
    log.append(EventKind.TURN_START, {"causes": []})
    log.append(
        EventKind.USER_MESSAGE,
        {"message": encode_message(UserMessage((TextBlock(text="hi"),), 1))},
    )
    log.append(EventKind.STEP_START, {"reason": "initial"})
    if with_tool:
        log.append(EventKind.TOOL_CALL, {"id": "t1", "name": "echo", "arguments": {}})
        log.append(
            EventKind.TOOL_RESULT,
            {
                "message": {
                    "role": "tool_result",
                    "content": [{"type": "text", "text": "ok"}],
                    "timestamp": 0,
                    "tool_call_id": "t1",
                    "is_error": False,
                }
            },
        )
    log.append(EventKind.STEP_END, {})
    log.append(EventKind.TURN_END, {"reason": "completed", "causes": []})
    return log


def test_a_projection_is_bracketed_by_agent_start_and_end() -> None:
    events = project(_log_turn())

    assert isinstance(events[0], AgentStart)
    assert isinstance(events[-1], AgentEnd)


def test_turns_are_bracketed() -> None:
    events = project(_log_turn())
    kinds = [type(event) for event in events]

    assert kinds.index(TurnStart) < kinds.index(TurnEnd)


def test_messages_are_bracketed_by_start_and_end() -> None:
    events = project(_log_turn())

    assert any(isinstance(event, MessageStart) for event in events)
    assert any(isinstance(event, MessageEnd) for event in events)


def test_tool_execution_is_bracketed() -> None:
    events = project(_log_turn(with_tool=True))
    kinds = [type(event) for event in events]

    assert kinds.index(ToolExecutionStart) < kinds.index(ToolExecutionEnd)


def test_a_tool_execution_event_carries_its_call_id() -> None:
    events = project(_log_turn(with_tool=True))

    start = next(e for e in events if isinstance(e, ToolExecutionStart))
    assert (start.tool_call_id, start.tool_name) == ("t1", "echo")


def test_an_empty_log_projects_to_a_bare_bracket() -> None:
    assert [type(e) for e in project(SessionLog("s1"))] == [AgentStart, AgentEnd]


def test_turn_end_carries_its_causes() -> None:
    log = SessionLog("s1")
    log.append(EventKind.TURN_START, {"causes": [{"id": "e1", "origin": "matrix"}]})
    log.append(
        EventKind.TURN_END,
        {"reason": "completed", "causes": [{"id": "e1", "origin": "matrix"}]},
    )

    end = next(e for e in project(log) if isinstance(e, TurnEnd))

    assert end.causes[0]["origin"] == "matrix"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/agent/test_projection.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'minion_agent.agent.projection'`

- [ ] **Step 3: Write the projection**

Create `src/minion_agent/agent/projection.py`:

```python
"""Pi's observable event stream, rebuilt from the log.

The log is the source of truth (design spec section 5); Pi's `AgentEvent`
union is a *derived view* of it. Conformance asserts this projection, which is
what keeps Pi's observable semantics pinned while the internals follow DSH.

`message_update` is deliberately absent. It carries streaming deltas, which
requires `assistant/chunk` events the loop does not yet write; Plan 4 adds
them. Recorded here so the gap reads as a decision rather than an oversight.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..llm import Message
from ..session import EventKind, SessionLog, decode_message


@dataclass(frozen=True, slots=True)
class AgentStart:
    """The projection opens. Always first."""


@dataclass(frozen=True, slots=True)
class AgentEnd:
    """The projection closes. Always last."""


@dataclass(frozen=True, slots=True)
class TurnStart:
    causes: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True, slots=True)
class TurnEnd:
    reason: str
    causes: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True, slots=True)
class MessageStart:
    message: Message


@dataclass(frozen=True, slots=True)
class MessageEnd:
    message: Message


@dataclass(frozen=True, slots=True)
class ToolExecutionStart:
    tool_call_id: str
    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ToolExecutionEnd:
    tool_call_id: str
    is_error: bool


type AgentEvent = (
    AgentStart
    | AgentEnd
    | TurnStart
    | TurnEnd
    | MessageStart
    | MessageEnd
    | ToolExecutionStart
    | ToolExecutionEnd
)

_MESSAGE_KINDS = frozenset(
    {EventKind.USER_MESSAGE, EventKind.ASSISTANT_MESSAGE, EventKind.TOOL_RESULT}
)


def project(log: SessionLog) -> tuple[AgentEvent, ...]:
    """Rebuild the Pi event stream from `log`."""
    events: list[AgentEvent] = [AgentStart()]

    for entry in log.events:
        if entry.kind is EventKind.TURN_START:
            events.append(TurnStart(causes=tuple(entry.data.get("causes", ()))))

        elif entry.kind is EventKind.TURN_END:
            events.append(
                TurnEnd(
                    reason=entry.data.get("reason", "completed"),
                    causes=tuple(entry.data.get("causes", ())),
                )
            )

        elif entry.kind is EventKind.TOOL_CALL:
            events.append(
                ToolExecutionStart(
                    tool_call_id=entry.data["id"],
                    tool_name=entry.data["name"],
                    arguments=entry.data.get("arguments", {}),
                )
            )

        elif entry.kind in _MESSAGE_KINDS:
            message = decode_message(entry.data["message"])
            # A tool result closes its execution before it appears as a message,
            # matching pi's ordering: the execution ends, then its artifact is
            # emitted.
            if entry.kind is EventKind.TOOL_RESULT:
                events.append(
                    ToolExecutionEnd(
                        tool_call_id=entry.data["message"]["tool_call_id"],
                        is_error=entry.data["message"]["is_error"],
                    )
                )
            events.append(MessageStart(message=message))
            events.append(MessageEnd(message=message))

    events.append(AgentEnd())
    return tuple(events)


def event_names(events: tuple[AgentEvent, ...]) -> list[str]:
    """Snake-case names, the form conformance scenarios assert against."""
    import re

    return [
        re.sub(r"(?<!^)(?=[A-Z])", "_", type(event).__name__).lower()
        for event in events
    ]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/agent/test_projection.py -v`
Expected: PASS — seven tests.

- [ ] **Step 5: Commit**

```bash
git add src/minion_agent/agent/projection.py tests/agent/test_projection.py
git commit -m "feat: project the Pi-compatible event stream from the log"
```

---

## Task 16: The agent loop plugin

**Files:**
- Modify: `src/minion_agent/agent_loop/__init__.py`
- Create: `src/minion_agent/agent/plugin.py`
- Test: `tests/test_agent_composition.py`

**Interfaces:**
- Produces:
  - `agents_plugin` — injects `sessions`, provides `agents`
  - `tools_plugin` — provides `tools` (the trivial service)
  - `agent_loop_plugin` — injects `agents`, `llm`, `tools`, `sessions`; provides `agent_loop`, a factory with `for_instance(instance) -> AgentLoop`
  - Mounting order is irrelevant: reactive dependency settles it.

- [ ] **Step 1: Write the failing test**

Create `tests/test_agent_composition.py`:

```python
"""The whole stack composes, in any mounting order."""

from minion_agent.agent.identity import AgentDefinition
from minion_agent.agent.plugin import agents_plugin, tools_plugin
from minion_agent.agent_loop import agent_loop_plugin
from minion_agent.llm import ModelId, TextBlock, UserMessage, text_of
from minion_agent.llm.plugin import llm_plugin, mock_adapter_plugin
from minion_agent.runtime import Context, FiberState
from minion_agent.session import derive_messages
from minion_agent.session.service import session_plugin
from minion_agent.telemetry.plugin import telemetry_plugin


async def _stack(script: list[dict] | None = None) -> Context:
    ctx = Context()
    await ctx.plugin(agent_loop_plugin)     # mounted first, on purpose
    await ctx.plugin(session_plugin)
    await ctx.plugin(llm_plugin)
    await ctx.plugin(tools_plugin)
    await ctx.plugin(agents_plugin)
    await ctx.plugin(telemetry_plugin)
    await ctx.plugin(mock_adapter_plugin, {"script": script or []})
    return ctx


async def test_the_loop_plugin_waits_for_its_dependencies() -> None:
    ctx = Context()

    fiber = await ctx.plugin(agent_loop_plugin)
    assert fiber.state is FiberState.PENDING

    await ctx.plugin(session_plugin)
    await ctx.plugin(llm_plugin)
    await ctx.plugin(tools_plugin)
    await ctx.plugin(agents_plugin)

    assert fiber.state is FiberState.ACTIVE


async def test_a_full_turn_runs_through_the_composed_stack() -> None:
    ctx = await _stack([{"text": "hello there", "stop_reason": "stop"}])
    handle = ctx.agents.create(
        "room-a", AgentDefinition(name="ada", model=ModelId("mock", "mock-1"))
    )
    loop = ctx.agent_loop.for_instance(handle.instance)

    handle.instance.inbox.followup(
        UserMessage(content=(TextBlock(text="hi"),), timestamp=1)
    )
    await loop.run_until_idle()

    assert [text_of(m) for m in derive_messages(handle.instance.log)] == [
        "hi",
        "hello there",
    ]


async def test_two_instances_of_one_definition_keep_separate_logs() -> None:
    ctx = await _stack(
        [
            {"text": "to a", "stop_reason": "stop"},
            {"text": "to b", "stop_reason": "stop"},
        ]
    )
    definition = AgentDefinition(name="ada", model=ModelId("mock", "mock-1"))
    first = ctx.agents.create("room-a", definition)
    second = ctx.agents.create("room-b", definition)

    for handle, text in ((first, "from a"), (second, "from b")):
        handle.instance.inbox.followup(
            UserMessage(content=(TextBlock(text=text),), timestamp=1)
        )
        await ctx.agent_loop.for_instance(handle.instance).run_until_idle()

    assert text_of(derive_messages(first.instance.log)[0]) == "from a"
    assert text_of(derive_messages(second.instance.log)[0]) == "from b"


async def test_unmounting_the_llm_unloads_the_loop() -> None:
    """Reactive dependency reaches all the way up the stack."""
    ctx = Context()
    await ctx.plugin(session_plugin)
    llm_fiber = await ctx.plugin(llm_plugin)
    await ctx.plugin(tools_plugin)
    await ctx.plugin(agents_plugin)
    loop_fiber = await ctx.plugin(agent_loop_plugin)
    assert loop_fiber.state is FiberState.ACTIVE

    await ctx.plugins.unmount(llm_fiber)

    assert loop_fiber.state is FiberState.PENDING
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_agent_composition.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'minion_agent.agent.plugin'`

- [ ] **Step 3: Write the plugins**

Create `src/minion_agent/agent/plugin.py`:

```python
"""Mounting the agents registry and the trivial tool service."""

from __future__ import annotations

from ..runtime import Context, plugin
from .registry import AgentRegistry
from .tools import ToolService


@plugin(name="agents", inject=["sessions"], provides="agents")
async def agents_plugin(ctx: Context, config: None) -> None:
    """Provide the agents registry.

    Injects `sessions` because every instance owns a session log, and the
    registry mints one per instance.
    """
    ctx.provide("agents", AgentRegistry(ctx=ctx, sessions=ctx.sessions))


@plugin(name="tools", provides="tools")
async def tools_plugin(ctx: Context, config: None) -> None:
    """Provide the trivial tool service. Plan 4 replaces this."""
    ctx.provide("tools", ToolService())
```

Then replace `src/minion_agent/agent_loop/__init__.py`:

```python
"""The agent loop plugin.

The driver is package-internal: only this module's factory constructs one, so
nothing above can reach past the `agent` package's interface into loop
internals.
"""

from __future__ import annotations

from ..agent.instance import AgentInstance
from ..runtime import Context, plugin
from .driver import AgentLoop


class AgentLoopFactory:
    """Builds a driver for an instance, wired to the mounted services."""

    __service_name__ = "agent_loop"

    def __init__(self, ctx: Context) -> None:
        self._ctx = ctx

    def for_instance(self, instance: AgentInstance) -> AgentLoop:
        """A driver for `instance`, sharing this context's services."""
        return AgentLoop(
            instance=instance,
            llm=self._ctx.llm,
            tools=self._ctx.tools,
            artifacts=self._ctx.sessions.artifacts,
            telemetry=getattr(self._ctx, "telemetry", None),
        )


@plugin(
    name="agent-loop",
    inject=["agents", "llm", "tools", "sessions"],
    provides="agent_loop",
)
async def agent_loop_plugin(ctx: Context, config: None) -> None:
    """Provide the loop factory once every service it drives exists.

    Telemetry is deliberately *not* injected: it is observational, so the loop
    must run without it rather than wait for it.
    """
    ctx.provide("agent_loop", AgentLoopFactory(ctx))


__all__ = ["AgentLoopFactory", "agent_loop_plugin"]
```

Telemetry is resolved with `getattr` rather than injected, because injecting it
would make an observational projection a *precondition* for running — the
opposite of what §7 says it is.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_agent_composition.py -v`
Expected: PASS — four tests.

- [ ] **Step 5: Commit**

```bash
git add src/minion_agent tests/test_agent_composition.py
git commit -m "feat: mount the agents registry, tools, and loop as plugins"
```

---

## Task 17: Agent conformance

**Files:**
- Create: `tests/conformance/agent_runner.py`, `tests/conformance/test_agent_conformance.py`
- Create: `conformance/agent/*.yaml` (eleven scenarios)
- Modify: `tests/conformance/test_schema_validation.py` (drop `agent` from `UNPOPULATED`)

**Interfaces:**
- Produces: `async def run_agent_scenario(document) -> dict` returning `{"events": [...], "messages": [...]}` — the projected Pi event stream and the derived messages, which are the two observable surfaces §8 names.
- Six loop scenarios: `turn-lifecycle`, `origin-survives-one-at-a-time`, `causes-preserved-under-claim-all`, `proactive-turn-carries-provenance`, `tool-round-trip`, `max-steps-bounds-a-turn`.
- Five **stream-boundary** scenarios (Step 4): `premature-eof-synthesizes-error-terminal`, `premature-eof-preserves-partial-message`, `public-stream-fuses-after-first-terminal`, `eager-invalid-model-fails-before-stream`, `represented-provider-error-rides-stream`.

**Why the stream cases live here.** §4's boundary is currently pinned only by
Python tier-2 tests, which a second-language implementation cannot run. The
cases belong in `conformance/agent/` because the agent family asserts the log
projection, and a settled error surfaces there as an assistant message — but
that family has no runner until this task builds one, which is why they were
deferred to this plan rather than landed with the fix. Leaving them out would
mean the never-raises contract stays unverifiable across languages.

- [ ] **Step 1: Write the runner**

Create `tests/conformance/agent_runner.py`:

```python
"""Executes agent conformance scenarios against the composed stack.

Asserts the two observable surfaces §8 names: the derived Pi event stream and
the log's message projection. Nothing here inspects loop internals.
"""

from __future__ import annotations

from typing import Any

from minion_agent.agent.identity import AgentDefinition
from minion_agent.agent.plugin import agents_plugin, tools_plugin
from minion_agent.agent.projection import event_names, project
from minion_agent.agent_loop import agent_loop_plugin
from minion_agent.llm import (
    AssistantMessage,
    ModelId,
    TextBlock,
    ToolResultMessage,
    UserMessage,
    text_of,
)
from minion_agent.llm.plugin import llm_plugin, mock_adapter_plugin
from minion_agent.runtime import Context
from minion_agent.session import derive_messages
from minion_agent.session.service import session_plugin

_ROLE = {
    UserMessage: "user",
    AssistantMessage: "assistant",
    ToolResultMessage: "tool_result",
}


def _script(document: dict[str, Any]) -> list[dict[str, Any]]:
    """Translate scripted responses into the mock adapter's config shape."""
    out: list[dict[str, Any]] = []
    for response in document["provider_script"]:
        blocks = response.get("content", [])
        text = "".join(b.get("text", "") for b in blocks if b["type"] == "text")
        entry: dict[str, Any] = {"text": text, "stop_reason": response["stop_reason"]}
        if response.get("error_message"):
            entry["error_message"] = response["error_message"]
        out.append(entry)
    return out


def _tool_calls(document: dict[str, Any]) -> dict[int, dict[str, Any]]:
    """Scripted tool calls, keyed by their index in the provider script."""
    calls: dict[int, dict[str, Any]] = {}
    for index, response in enumerate(document["provider_script"]):
        for block in response.get("content", []):
            if block["type"] == "tool_call":
                calls[index] = block
    return calls


async def run_agent_scenario(document: dict[str, Any]) -> dict[str, Any]:
    """Run the scenario and return its observable surfaces."""
    ctx = Context()
    await ctx.plugin(session_plugin)
    await ctx.plugin(llm_plugin)
    await ctx.plugin(tools_plugin)
    await ctx.plugin(agents_plugin)
    await ctx.plugin(agent_loop_plugin)
    await ctx.plugin(mock_adapter_plugin, {"script": _script(document)})

    # Scripted tool calls need a richer adapter than the config plugin builds,
    # so a scenario using them registers them directly.
    calls = _tool_calls(document)
    if calls:
        from minion_agent.llm.adapters.mock import MockAdapter, ScriptedResponse
        from minion_agent.llm.content import ToolCallBlock
        from minion_agent.llm.messages import StopReason

        script = []
        for index, response in enumerate(document["provider_script"]):
            call = calls.get(index)
            if call is not None:
                content: tuple[Any, ...] = (
                    ToolCallBlock(
                        id=call["id"],
                        name=call["name"],
                        arguments=call.get("arguments", {}),
                    ),
                )
            else:
                content = tuple(
                    TextBlock(text=b.get("text", ""))
                    for b in response.get("content", [])
                    if b["type"] == "text"
                )
            script.append(
                ScriptedResponse(content, StopReason(response["stop_reason"]))
            )
        ctx.llm.register(MockAdapter(script))

    for name, stub in document.get("tools", {}).items():
        result = stub.get("result", {}).get("text", "")
        ctx.tools.register(name, lambda args, text=result: text)

    config = document.get("config", {})
    definition = AgentDefinition(
        name="scenario",
        model=ModelId("mock", "mock-1"),
        system=config.get("system", ""),
        max_steps=config.get("max_steps", 16),
    )
    handle = ctx.agents.create("scenario", definition)
    loop = ctx.agent_loop.for_instance(handle.instance)

    if "next_turn_policy" in config:
        from minion_agent.agent.envelope import ClaimPolicy

        loop.next_turn_policy = ClaimPolicy(config["next_turn_policy"])

    for step in document["steps"]:
        for alias in ("followup", "steer", "inject"):
            if alias in step:
                spec = step[alias]
                text = spec if isinstance(spec, str) else spec["text"]
                origin = None if isinstance(spec, str) else spec.get("origin")
                message = UserMessage(content=(TextBlock(text=text),), timestamp=1)
                getattr(handle.instance.inbox, alias)(message, origin=origin)
        if step.get("await_idle"):
            await loop.run_until_idle()

    events = project(handle.instance.log)
    return {
        "events": event_names(events),
        "messages": [
            {"role": _ROLE[type(m)], "text": text_of(m)}
            for m in derive_messages(handle.instance.log)
        ],
        "causes": [
            list(event.causes)
            for event in events
            if type(event).__name__ == "TurnEnd"
        ],
    }
```

- [ ] **Step 2: Write the test**

Create `tests/conformance/test_agent_conformance.py`:

```python
"""Execute every conformance/agent/*.yaml scenario."""

from pathlib import Path

import pytest
import yaml

from .agent_runner import run_agent_scenario

SCENARIOS = sorted(
    (Path(__file__).resolve().parents[2] / "conformance" / "agent").glob("*.yaml")
)


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda path: path.stem)
async def test_agent_scenario(scenario: Path) -> None:
    document = yaml.safe_load(scenario.read_text(encoding="utf-8"))
    outcome = await run_agent_scenario(document)

    assert outcome["events"] == document["expect_events"]

    if "expect_messages" in document:
        assert outcome["messages"] == document["expect_messages"]

    if "expect_causes" in document:
        observed = [
            [cause["origin"] for cause in turn] for turn in outcome["causes"]
        ]
        assert observed == document["expect_causes"]
```

`expect_causes` is a scenario-format extension this task adds; update
`conformance/schema/agent-scenario.schema.json` to allow it alongside
`expect_events` and `expect_messages`, and allow `config` to carry
`next_turn_policy`, `max_steps`, and `system`.

- [ ] **Step 3: Write the scenarios**

Create `conformance/agent/turn-lifecycle.yaml`:

```yaml
name: one prompt produces one bracketed turn
description: >
  The observable shape of a turn: agent start, turn start, the user message,
  the assistant reply, turn end, agent end.
provider_script:
  - content: [{ type: text, text: hello there }]
    stop_reason: stop
steps:
  - followup: hi
  - await_idle: true
expect_events:
  - agent_start
  - turn_start
  - message_start
  - message_end
  - message_start
  - message_end
  - turn_end
  - agent_end
expect_messages:
  - { role: user, text: hi }
  - { role: assistant, text: hello there }
```

Create `conformance/agent/causes-preserved-under-claim-all.yaml`:

```yaml
name: one turn under claim-all carries every cause
description: >
  The case a singular turn origin could not express: three inputs with
  distinct origins enter one turn, and all three survive to its completion.
config: { next_turn_policy: all }
provider_script:
  - content: [{ type: text, text: answered }]
    stop_reason: stop
steps:
  - followup: { text: one, origin: a }
  - followup: { text: two, origin: b }
  - followup: { text: three, origin: c }
  - await_idle: true
expect_events:
  - agent_start
  - turn_start
  - message_start
  - message_end
  - message_start
  - message_end
  - message_start
  - message_end
  - message_start
  - message_end
  - turn_end
  - agent_end
expect_causes:
  - [a, b, c]
```

Create `conformance/agent/origin-survives-one-at-a-time.yaml`:

```yaml
name: each turn under one-at-a-time carries exactly its own cause
description: >
  The default policy. Two queued prompts produce two turns, each reporting the
  single input it claimed.
provider_script:
  - content: [{ type: text, text: first reply }]
    stop_reason: stop
  - content: [{ type: text, text: second reply }]
    stop_reason: stop
steps:
  - followup: { text: one, origin: a }
  - followup: { text: two, origin: b }
  - await_idle: true
expect_causes:
  - [a]
  - [b]
expect_messages:
  - { role: user, text: one }
  - { role: assistant, text: first reply }
  - { role: user, text: two }
  - { role: assistant, text: second reply }
```

Omit `expect_events` here; the causes and messages are what this case pins,
and listing the full bracket twice would obscure that.

Create `conformance/agent/proactive-turn-carries-provenance.yaml`:

```yaml
name: a turn nobody prompted still carries provenance
description: >
  A scheduler starts work with no user in the loop. The runtime never
  interprets the origin — it only carries it — so a delivery layer can route
  the result.
provider_script:
  - content: [{ type: text, text: nothing to report }]
    stop_reason: stop
steps:
  - followup: { text: heartbeat, origin: { scheduler: heartbeat } }
  - await_idle: true
expect_causes:
  - [{ scheduler: heartbeat }]
```

Create `conformance/agent/tool-round-trip.yaml`:

```yaml
name: a tool call closes and the model is asked again
description: >
  The Phase 3 milestone. The model requests a tool, the loop executes it and
  logs the result, and the model is asked again with that result in history.
provider_script:
  - content: [{ type: tool_call, id: t1, name: echo, arguments: { value: pong } }]
    stop_reason: tool_use
  - content: [{ type: text, text: all done }]
    stop_reason: stop
tools:
  echo: { result: { text: pong } }
steps:
  - followup: ping
  - await_idle: true
expect_events:
  - agent_start
  - turn_start
  - message_start
  - message_end
  - message_start
  - message_end
  - tool_execution_start
  - tool_execution_end
  - message_start
  - message_end
  - message_start
  - message_end
  - turn_end
  - agent_end
expect_messages:
  - { role: user, text: ping }
  - { role: assistant, text: "" }
  - { role: tool_result, text: pong }
  - { role: assistant, text: all done }
```

Create `conformance/agent/max-steps-bounds-a-turn.yaml`:

```yaml
name: max_steps bounds a turn that only ever calls tools
description: >
  A hard loop invariant. The model requests a tool every time; the turn ends
  at the bound rather than running forever, and no listener can override it.
config: { max_steps: 2 }
provider_script:
  - content: [{ type: tool_call, id: t1, name: echo, arguments: {} }]
    stop_reason: tool_use
  - content: [{ type: tool_call, id: t2, name: echo, arguments: {} }]
    stop_reason: tool_use
  - content: [{ type: tool_call, id: t3, name: echo, arguments: {} }]
    stop_reason: tool_use
tools:
  echo: { result: { text: again } }
steps:
  - followup: go
  - await_idle: true
expect_messages:
  - { role: user, text: go }
  - { role: assistant, text: "" }
  - { role: tool_result, text: again }
  - { role: assistant, text: "" }
  - { role: tool_result, text: again }
```

Two assistant messages and two results, not three: the bound stops the turn
after the second step.

- [ ] **Step 4: Write the stream-boundary scenarios**

These pin §4's contract — eager on one side of the stream's return, in-band on
the other. The mock adapter's `stop_reason: error` produces a settled error
message; a `provider_script` entry with `truncated: true` ends the raw stream
without a terminal, which the service must settle rather than raise.

Extend the mock adapter config and `agent-scenario.schema.json` with that
`truncated` flag, then create `conformance/agent/premature-eof-synthesizes-error-terminal.yaml`:

```yaml
name: a truncated provider stream settles instead of raising
description: >
  §4 is absolute after the stream is returned: nothing escapes iteration. A
  provider stream that ends before emitting a terminal is a runtime streaming
  failure -- a truncated response is the ordinary case -- so it settles as an
  error rather than propagating an exception through the loop.
provider_script:
  - content: [{ type: text, text: half a sen }]
    stop_reason: stop
    truncated: true
steps:
  - followup: hello
  - await_idle: true
expect_events:
  - agent_start
  - turn_start
  - message_start
  - message_end
  - message_start
  - message_end
  - turn_end
  - agent_end
expect_assistant_stop_reason: error
```

Create `premature-eof-preserves-partial-message.yaml`: the same shape, asserting
`expect_messages` still carries the partial text rather than an empty message —
replacing a real partial response with an unrelated empty one loses what the
model actually produced.

Create `public-stream-fuses-after-first-terminal.yaml`: a script whose entry
emits a terminal and then further chunks, asserting exactly one assistant
message reaches the log.

Create `represented-provider-error-rides-stream.yaml`: a `stop_reason: error`
entry, asserting the turn completes with an error-stopped assistant message and
no exception.

Create `eager-invalid-model-fails-before-stream.yaml`: config naming a model no
adapter supplies, asserting the scenario raises rather than settling the failure
into history —

```yaml
expect_error:
  type: UnknownModelError
  message_contains: no-such-model
expect_messages:
  - { role: user, text: hello }
expect_assistant_stop_reasons: []
```

> **Deviation, recorded during execution.** This step originally specified
> `before_any_event: true`, which the loop cannot satisfy: a turn opens, claims
> its prompt, and records its request header *before* the model is resolved, so
> those entries exist by the time `UnknownModelError` is raised. The eager
> contract is about where the failure surfaces, not about the log being empty.
> The shape above pins it without the false claim, and `before_any_event` was
> never added to the schema.

The last one is the only agent scenario that asserts a raised error, and
deliberately so: it is the *other* side of the boundary. Add `expect_error` and
`expect_assistant_stop_reason` to `agent-scenario.schema.json`, and teach
`test_agent_conformance.py` to honour both.

- [ ] **Step 5: Run the conformance suite**

Run: `uv run pytest tests/conformance -v`
Expected: PASS — seven runtime, nine session, and eleven agent scenarios.

- [ ] **Step 6: Commit**

```bash
git add conformance/agent tests/conformance
git commit -m "feat: add agent conformance runner and lifecycle scenarios"
```

---

## Task 18: Public surface, property tests, and the coverage gate

**Files:**
- Modify: `src/minion_agent/agent/__init__.py`, `src/minion_agent/agent_loop/__init__.py`, `pyproject.toml`, `tests/test_layering.py`
- Create: `tests/agent/test_properties.py`

**Interfaces:**
- Produces: curated `__all__` for `agent`; `agent_loop` exports only its plugin and factory, keeping the driver package-internal. Coverage extends to both packages.

- [ ] **Step 1: Write the property tests**

Create `tests/agent/test_properties.py`:

```python
"""Properties that must hold for any inbox and turn sequence."""

from hypothesis import given
from hypothesis import strategies as st

from minion_agent.agent.envelope import ClaimPolicy, InboxTarget
from minion_agent.agent.inbox import Inbox
from minion_agent.llm import TextBlock, UserMessage

texts = st.lists(st.text(min_size=1, max_size=6), min_size=0, max_size=20)
policies = st.sampled_from([ClaimPolicy.ALL, ClaimPolicy.ONE_AT_A_TIME])


def _message(text: str) -> UserMessage:
    return UserMessage(content=(TextBlock(text=text),), timestamp=1)


def _drain(inbox: Inbox, target: InboxTarget, policy: ClaimPolicy) -> list[str]:
    seen: list[str] = []
    while True:
        claimed = inbox.claim(target, policy)
        if not claimed:
            return seen
        seen.extend(envelope.id for envelope in claimed)


@given(texts, policies)
def test_every_sent_message_is_claimed_exactly_once(
    items: list[str], policy: ClaimPolicy
) -> None:
    inbox = Inbox()
    sent = [inbox.followup(_message(text)).id for text in items]

    drained = _drain(inbox, InboxTarget.NEXT_TURN, policy)

    assert drained == sent


@given(texts, texts)
def test_the_two_queues_never_leak_into_each_other(
    turn_items: list[str], step_items: list[str]
) -> None:
    inbox = Inbox()
    turn_ids = {inbox.followup(_message(t)).id for t in turn_items}
    step_ids = {inbox.steer(_message(t)).id for t in step_items}

    drained = set(_drain(inbox, InboxTarget.NEXT_TURN, ClaimPolicy.ALL))

    assert drained == turn_ids
    assert not (drained & step_ids)


@given(texts)
def test_one_at_a_time_preserves_send_order(items: list[str]) -> None:
    inbox = Inbox()
    sent = [inbox.followup(_message(text)).id for text in items]

    drained = _drain(inbox, InboxTarget.NEXT_TURN, ClaimPolicy.ONE_AT_A_TIME)

    assert drained == sent


@given(texts)
def test_claiming_never_invents_input(items: list[str]) -> None:
    inbox = Inbox()
    sent = {inbox.followup(_message(text)).id for text in items}

    drained = set(_drain(inbox, InboxTarget.NEXT_TURN, ClaimPolicy.ALL))

    assert drained <= sent


@given(texts)
def test_injection_alone_never_requests_a_wake(items: list[str]) -> None:
    """Silent by construction, however much is injected."""
    inbox = Inbox()
    for text in items:
        inbox.inject(_message(text))

    assert not inbox.wake_requested


@given(st.integers(min_value=1, max_value=8))
def test_a_drained_inbox_stays_drained(rounds: int) -> None:
    inbox = Inbox()
    inbox.followup(_message("only"))
    _drain(inbox, InboxTarget.NEXT_TURN, ClaimPolicy.ALL)

    for _ in range(rounds):
        assert inbox.claim(InboxTarget.NEXT_TURN, ClaimPolicy.ALL) == ()
```

Create `tests/agent_loop/test_loop_properties.py`:

```python
"""Properties of the loop over any number of turns."""

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from minion_agent.agent.identity import AgentStatus
from minion_agent.llm import TextBlock, UserMessage
from minion_agent.llm.adapters.mock import ScriptedResponse
from minion_agent.llm.messages import StopReason
from minion_agent.session import EventKind

from .test_single_turn import _loop

turn_counts = st.integers(min_value=1, max_value=6)


def _say(text: str) -> UserMessage:
    return UserMessage(content=(TextBlock(text=text),), timestamp=1)


@given(turn_counts)
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
async def test_status_always_alternates(turns: int) -> None:
    """A transition signal must never report the same state twice in a row."""
    loop = _loop(*[ScriptedResponse((), StopReason.STOP) for _ in range(turns)])
    seen: list[AgentStatus] = []
    loop.instance.on_status_change = seen.append

    for index in range(turns):
        loop.instance.inbox.followup(_say(f"turn {index}"))
    await loop.run_until_idle()

    assert all(a is not b for a, b in zip(seen, seen[1:], strict=False))
    assert seen[0] is AgentStatus.RUNNING
    assert seen[-1] is AgentStatus.IDLE


@given(turn_counts)
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
async def test_every_turn_is_bracketed(turns: int) -> None:
    loop = _loop(*[ScriptedResponse((), StopReason.STOP) for _ in range(turns)])
    for index in range(turns):
        loop.instance.inbox.followup(_say(f"turn {index}"))

    await loop.run_until_idle()

    kinds = [e.kind for e in loop.instance.log.events]
    assert kinds.count(EventKind.TURN_START) == kinds.count(EventKind.TURN_END) == turns


@given(turn_counts)
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
async def test_a_turn_records_exactly_the_causes_it_claimed(turns: int) -> None:
    loop = _loop(*[ScriptedResponse((), StopReason.STOP) for _ in range(turns)])
    sent = [
        loop.instance.inbox.followup(_say(f"turn {index}"), origin=index).id
        for index in range(turns)
    ]

    await loop.run_until_idle()

    recorded = [
        cause["id"]
        for event in loop.instance.log.events
        if event.kind is EventKind.TURN_START
        for cause in event.data["causes"]
    ]
    assert recorded == sent
```

- [ ] **Step 2: Extend layering**

Add to `FORBIDDEN` in `tests/test_layering.py`:

```python
    "agent": ("agent_loop",),
    "agent_loop": (),
```

`agent` must not import `agent_loop`: the driver is package-internal, and the
interface lives in `agent`. Nothing else may import `agent_loop` either — add a
test asserting that only its own tests do.

- [ ] **Step 3: Extend the coverage gate**

Add `src/minion_agent/agent` and `src/minion_agent/agent_loop` to
`[tool.coverage.run] source`.

- [ ] **Step 4: Reach 100%**

Run: `uv run pytest`

Expect gaps on the driver's branch coverage — rejected turns, cancelled turns,
and the no-telemetry path. Write tests for reachable lines; use
`# pragma: no cover` only with a written reason on the same line.

- [ ] **Step 5: Run lint and types**

Run: `uv run ruff check . && uv run ruff format --check . && uv run mypy`

- [ ] **Step 6: Commit and push**

```bash
git add -A
git commit -m "test: add agent property tests, layering, and coverage gate"
git push origin main
```

---

## Definition of done

- [ ] `uv run pytest` passes with 100% coverage of `runtime`, `llm`, `session`, `telemetry`, `agent`, and `agent_loop`
- [ ] `uv run ruff check`, `ruff format --check`, and `mypy` are clean
- [ ] Seven runtime, nine session, and eleven agent scenarios execute and pass
- [ ] §4's stream boundary is pinned by conformance, not only by Python tests: a truncated stream settles in-band, and an unknown model raises rather than settling the failure into history (see the deviation note in Task 17, Step 4)
- [ ] The Phase 3 milestone runs end to end: mock LLM → tool_call → loop → mock tool result → second request
- [ ] A turn's `causes` match its claimed envelopes under both claim policies
- [ ] Hard termination (`max_steps`, `cancelled`, nothing owed) precedes `agent/turn-stopping`, verified by a test asserting the event is not dispatched
- [ ] One agent blocked in a tool does not prevent another completing a turn
- [ ] `agent` does not import `agent_loop` — checked, not assumed
- [ ] Work is pushed to `origin/main`

## What Plan 4 picks up

The real tool subsystem: a scope-aware registry replacing `agent/tools.py`, the
`tools/pre-execute` and `tools/post-execute` waterfalls with their decision and
transformation patterns, parallel batching with pi's batch-contagion rule,
per-tool execution modes, streaming partial results, and the `terminate` fold —
stop only when *every* finalized result sets it, evaluated before
`agent/turn-stopping`.

It also picks up `assistant/chunk` logging, which unlocks the `message_update`
event this plan's projection deliberately omits.
