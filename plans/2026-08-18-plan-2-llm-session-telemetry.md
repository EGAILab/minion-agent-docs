# Minion Agent — Plan 2: LLM Vocabulary, Session Log, and Telemetry

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the provider-neutral LLM vocabulary, the append-only session log that is the system's semantic truth, and the telemetry seam every later subsystem emits into — so Plan 3's agent loop has a model to talk to, a log to derive from, and somewhere to report.

**Architecture:** A message vocabulary mirroring Pi's semantics, behind an `ctx.llm` seam whose streams never raise once returned. An append-only, sequence-numbered log whose *surface* subset projects into model history via `derive_messages()`, with fork, reset, and compaction defined as log events rather than mutations. Request state is stored as content-addressed components so a months-long session does not re-snapshot a 15k-token prompt every step. Telemetry is an observational projection with a mandatory sanitize boundary ahead of sinks.

**Tech Stack:** Python 3.12+, `pydantic` v2, `pytest` + `pytest-asyncio`, `hypothesis`, `PyYAML`, `jsonschema`, `ruff`, `mypy`, `pytest-cov`. Everything mounts as a plugin on the runtime Plan 1 delivered.

**Spec:** `minion-agent-docs/design/2026-08-18-minion-agent-design.md`, **frozen** — read §4 (LLM seam), §5 (session log, session operations, content-addressed request state), §7 (telemetry), and §8 (validation) before starting.

**Prior plan:** `2026-08-18-plan-1-conformance-and-runtime.md`, complete. The runtime provides `Context`, `Fiber`, `ServiceRegistry`, `EventBus` (four dispatch modes, scope-filtered), `ScopeKey`/`Scope`, `ScopedRegistry`, and `@plugin`. Read `src/minion_agent/runtime/__init__.py` for the exact public surface before writing a plugin.

## Global Constraints

Everything in Plan 1's Global Constraints still applies — Python floor, interpreter rules, naming, the conformance rule, normativity, commit style. Additionally:

- **Coverage:** `src/minion_agent/llm/**`, `src/minion_agent/session/**`, and `src/minion_agent/telemetry/**` join the 100%-per-file gate alongside `runtime/**`.
- **Layer purity:** `llm/` knows nothing of sessions, agents, or tools. `session/` knows the LLM vocabulary (it stores messages) but nothing of agents or tools. Neither imports `agent`. Checked, not assumed.
- **The never-raises boundary** (§4) is normative and cuts at the moment a stream is returned. Caller bugs raise eagerly; in-band failures ride the stream.
- **Model-visible means logged.** Anything reaching a model request must be reconstructable from the log. Where a scenario covers reconstruction, it asserts the reconstructed input — never the storage shape.
- **Telemetry is observational.** No invariant, conformance case, or runtime behavior may depend on telemetry contents.
- **Deferred, do not implement:** the agent loop, tool registry, real providers, compaction *policy* (the trigger and cut-point search), telemetry sinks. Compaction *mechanics* — the event and its effect on derivation — are in scope.

---

## File Structure

```
minion-agent-python/
  src/minion_agent/
    llm/
      __init__.py            # public surface
      content.py             # Text, Thinking, Image, ToolCall blocks
      messages.py            # User, Assistant, ToolResult; StopReason; Usage
      stream.py              # stream chunks + the never-raises stream type
      service.py             # LlmService seam, model identity, adapter protocol
      errors.py              # eager-side errors (unknown model, bad config)
      adapters/
        __init__.py
        mock.py              # scripted adapter; drives every conformance case
    session/
      __init__.py
      events.py              # SessionEvent map: surface vs log-only
      artifacts.py           # content-addressed store
      log.py                 # append-only log, sequencing, JSON validation
      derive.py              # derive_messages() over the surface
      operations.py          # fork, reset, compact_now
      service.py             # SessionService plugin
    telemetry/
      __init__.py
      spans.py               # typed span vocabulary
      sanitize.py            # mandatory redaction boundary
      service.py             # TelemetryService plugin + recording sink
  conformance/
    session/*.yaml           # derivation after log operations
  tests/
    conformance/
      session_runner.py
      test_session_conformance.py
    llm/  session/  telemetry/
```

---

# Phase 2 — LLM vocabulary, session log, telemetry

## Task 1: LLM content blocks

**Files:**
- Create: `src/minion_agent/llm/content.py`
- Test: `tests/llm/test_content.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `@dataclass(frozen=True, slots=True) class TextBlock` with `text: str`
  - `ThinkingBlock` with `thinking: str`
  - `ImageBlock` with `mime_type: str`, `data: bytes | None = None`, `reference: str | None = None`
  - `ToolCallBlock` with `id: str`, `name: str`, `arguments: dict[str, Any]`
  - `type ContentBlock = TextBlock | ThinkingBlock | ImageBlock | ToolCallBlock`
  - `ImageBlock.__post_init__` raises `ValueError` unless exactly one of `data`/`reference` is set.

- [ ] **Step 1: Write the failing test**

Create `tests/llm/test_content.py`:

```python
"""Content blocks are the provider-neutral vocabulary a model sees."""

import pytest

from minion_agent.llm.content import ImageBlock, TextBlock, ThinkingBlock, ToolCallBlock


def test_text_block_carries_its_text() -> None:
    assert TextBlock(text="hello").text == "hello"


def test_thinking_block_is_distinct_from_text() -> None:
    assert ThinkingBlock(thinking="reasoning") != TextBlock(text="reasoning")


def test_tool_call_block_carries_id_name_and_arguments() -> None:
    call = ToolCallBlock(id="t1", name="bash", arguments={"command": "ls"})

    assert (call.id, call.name, call.arguments) == ("t1", "bash", {"command": "ls"})


def test_image_block_accepts_inline_data() -> None:
    block = ImageBlock(mime_type="image/png", data=b"\x89PNG")

    assert block.mime_type == "image/png"
    assert block.reference is None


def test_image_block_accepts_a_reference() -> None:
    block = ImageBlock(mime_type="image/png", reference="sha256:abc")

    assert block.data is None


def test_image_block_requires_exactly_one_source() -> None:
    """Neither is meaningless; both is ambiguous about what the model saw."""
    with pytest.raises(ValueError, match="exactly one"):
        ImageBlock(mime_type="image/png")

    with pytest.raises(ValueError, match="exactly one"):
        ImageBlock(mime_type="image/png", data=b"x", reference="sha256:abc")


def test_blocks_are_frozen() -> None:
    block = TextBlock(text="hello")

    with pytest.raises(Exception):
        block.text = "changed"  # type: ignore[misc]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/pytest tests/llm/test_content.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'minion_agent.llm'`

- [ ] **Step 3: Write the implementation**

Create `src/minion_agent/llm/__init__.py` as an empty module docstring for now, and `src/minion_agent/llm/content.py`:

```python
"""Provider-neutral content blocks.

These are what a model sees. An adapter translates them to and from its
provider's wire format; nothing above this layer knows that format exists.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class TextBlock:
    """Ordinary model-visible text."""

    text: str


@dataclass(frozen=True, slots=True)
class ThinkingBlock:
    """Reasoning content, when a provider exposes it separately from text."""

    thinking: str


@dataclass(frozen=True, slots=True)
class ImageBlock:
    """An image the model can see.

    Carries only what an adapter needs to translate it. Whether the bytes
    travel inline or by reference is an implementation choice; the mime type
    and the model-visible presence of an image are not.

    A logged reference must be immutable (design spec section 4) — a mutable
    path or URL would break request reconstruction silently, because the bytes
    the model saw and the bytes reconstruction fetches could differ with
    nothing detecting it. This type does not enforce immutability; the session
    layer resolves references to content-addressed artifacts before dispatch.
    """

    mime_type: str
    data: bytes | None = None
    reference: str | None = None

    def __post_init__(self) -> None:
        if (self.data is None) == (self.reference is None):
            raise ValueError(
                "ImageBlock requires exactly one of `data` or `reference`; "
                f"got data={self.data is not None}, reference={self.reference is not None}"
            )


@dataclass(frozen=True, slots=True)
class ToolCallBlock:
    """A tool invocation the model requested."""

    id: str
    name: str
    arguments: dict[str, Any]


type ContentBlock = TextBlock | ThinkingBlock | ImageBlock | ToolCallBlock
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/pytest tests/llm/test_content.py -v`
Expected: PASS — seven tests.

- [ ] **Step 5: Commit**

```bash
git add src/minion_agent/llm tests/llm
git commit -m "feat: add provider-neutral LLM content blocks"
```

---

## Task 2: Messages, stop reasons, and usage

**Files:**
- Create: `src/minion_agent/llm/messages.py`
- Test: `tests/llm/test_messages.py`

**Interfaces:**
- Consumes: `content.ContentBlock`.
- Produces:
  - `class StopReason(StrEnum)`: `PENDING`, `STOP`, `LENGTH`, `TOOL_USE`, `ERROR`, `ABORTED`
  - `@dataclass(frozen=True, slots=True) class Usage` with `input: int = 0`, `output: int = 0`, `cache_read: int = 0`, `cache_write: int = 0`, `reasoning: int | None = None`, and a `total` property
  - `UserMessage` with `content: tuple[ContentBlock, ...]`, `timestamp: int`
  - `AssistantMessage` with `content`, `stop_reason: StopReason`, `usage: Usage`, `model: str`, `provider: str`, `error_message: str | None = None`, `timestamp: int`
  - `ToolResultMessage` with `tool_call_id: str`, `content`, `is_error: bool = False`, `timestamp: int`
  - `type Message = UserMessage | AssistantMessage | ToolResultMessage`
  - `def text_of(message: Message) -> str` — concatenated text blocks, for tests and derivation

- [ ] **Step 1: Write the failing test**

Create `tests/llm/test_messages.py`:

```python
"""Messages carry content plus the accounting a caller needs."""

import pytest

from minion_agent.llm.content import TextBlock, ToolCallBlock
from minion_agent.llm.messages import (
    AssistantMessage,
    StopReason,
    ToolResultMessage,
    Usage,
    UserMessage,
    text_of,
)


def _assistant(**overrides: object) -> AssistantMessage:
    defaults: dict[str, object] = {
        "content": (TextBlock(text="hi"),),
        "stop_reason": StopReason.STOP,
        "usage": Usage(),
        "model": "mock-1",
        "provider": "mock",
        "timestamp": 1,
    }
    return AssistantMessage(**{**defaults, **overrides})  # type: ignore[arg-type]


def test_usage_total_sums_every_token_class() -> None:
    usage = Usage(input=10, output=5, cache_read=2, cache_write=3)

    assert usage.total == 20


def test_usage_defaults_to_zero() -> None:
    assert Usage().total == 0


def test_reasoning_is_optional_and_not_double_counted() -> None:
    """Reasoning tokens are a subset of output, never an extra class."""
    usage = Usage(input=1, output=10, reasoning=4)

    assert usage.total == 11


def test_user_message_carries_content_and_timestamp() -> None:
    message = UserMessage(content=(TextBlock(text="hello"),), timestamp=7)

    assert text_of(message) == "hello"
    assert message.timestamp == 7


def test_assistant_message_records_provider_identity() -> None:
    message = _assistant()

    assert (message.provider, message.model) == ("mock", "mock-1")
    assert message.stop_reason is StopReason.STOP


def test_assistant_message_may_carry_an_error() -> None:
    message = _assistant(stop_reason=StopReason.ERROR, error_message="upstream 500")

    assert message.error_message == "upstream 500"


def test_tool_result_message_links_to_its_call() -> None:
    message = ToolResultMessage(
        tool_call_id="t1", content=(TextBlock(text="ok"),), timestamp=2
    )

    assert message.tool_call_id == "t1"
    assert not message.is_error


def test_text_of_concatenates_only_text_blocks() -> None:
    message = _assistant(
        content=(
            TextBlock(text="a"),
            ToolCallBlock(id="t1", name="bash", arguments={}),
            TextBlock(text="b"),
        )
    )

    assert text_of(message) == "ab"


def test_messages_are_frozen() -> None:
    message = UserMessage(content=(), timestamp=1)

    with pytest.raises(Exception):
        message.timestamp = 2  # type: ignore[misc]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/pytest tests/llm/test_messages.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'minion_agent.llm.messages'`

- [ ] **Step 3: Write the implementation**

Create `src/minion_agent/llm/messages.py`:

```python
"""Messages, stop reasons, and token accounting.

Mirrors Pi's semantics: the same stop-reason vocabulary, the same treatment of
reasoning tokens as a subset of output rather than an extra class.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .content import ContentBlock, TextBlock


class StopReason(StrEnum):
    """Why a provider stopped generating."""

    PENDING = "pending"
    """Still streaming; never a settled message's reason."""

    STOP = "stop"
    """The model ended its turn."""

    LENGTH = "length"
    """The output token cap was reached."""

    TOOL_USE = "tool_use"
    """The model requested tools and expects results."""

    ERROR = "error"
    """The request failed. `error_message` says how."""

    ABORTED = "aborted"
    """The caller cancelled."""


@dataclass(frozen=True, slots=True)
class Usage:
    """Token accounting for one request.

    `reasoning` is a *subset* of `output` where a provider reports it, so it is
    deliberately excluded from `total` — counting it separately would
    double-count the same tokens.
    """

    input: int = 0
    output: int = 0
    cache_read: int = 0
    cache_write: int = 0
    reasoning: int | None = None

    @property
    def total(self) -> int:
        return self.input + self.output + self.cache_read + self.cache_write


@dataclass(frozen=True, slots=True)
class UserMessage:
    """Input from a user or an application."""

    content: tuple[ContentBlock, ...]
    timestamp: int


@dataclass(frozen=True, slots=True)
class AssistantMessage:
    """One settled model response."""

    content: tuple[ContentBlock, ...]
    stop_reason: StopReason
    usage: Usage
    model: str
    provider: str
    timestamp: int
    error_message: str | None = None


@dataclass(frozen=True, slots=True)
class ToolResultMessage:
    """The result of one tool call, linked by `tool_call_id`."""

    tool_call_id: str
    content: tuple[ContentBlock, ...]
    timestamp: int
    is_error: bool = False


type Message = UserMessage | AssistantMessage | ToolResultMessage


def text_of(message: Message) -> str:
    """Concatenate a message's text blocks, ignoring every other kind."""
    return "".join(
        block.text for block in message.content if isinstance(block, TextBlock)
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/pytest tests/llm/test_messages.py -v`
Expected: PASS — nine tests.

- [ ] **Step 5: Commit**

```bash
git add src/minion_agent/llm/messages.py tests/llm/test_messages.py
git commit -m "feat: add LLM messages, stop reasons, and usage accounting"
```

---

## Task 3: Stream chunks

**Files:**
- Create: `src/minion_agent/llm/stream.py`
- Test: `tests/llm/test_stream.py`

**Interfaces:**
- Consumes: `content`, `messages`.
- Produces:
  - Chunk dataclasses: `StreamStart`, `TextStart`, `TextDelta`, `TextEnd`, `ThinkingStart`, `ThinkingDelta`, `ThinkingEnd`, `ToolCallStart`, `ToolCallDelta`, `ToolCallEnd`, `StreamDone`, `StreamError`
  - Each carries `partial: AssistantMessage`, so a consumer can render any prefix. `StreamDone` carries `message`; `StreamError` carries `message` and `reason: StopReason`.
  - `type StreamChunk = ...` union
  - `type AssistantStream = AsyncIterator[StreamChunk]`
  - `async def collect(stream: AssistantStream) -> AssistantMessage` — drains a stream and returns its settled message, raising nothing.
- Note: images do not stream. There are no image delta chunks, by design (§4).

- [ ] **Step 1: Write the failing test**

Create `tests/llm/test_stream.py`:

```python
"""Stream chunks carry partials so a consumer can render any prefix."""

from collections.abc import AsyncIterator

from minion_agent.llm.content import TextBlock
from minion_agent.llm.messages import AssistantMessage, StopReason, Usage
from minion_agent.llm.stream import (
    StreamChunk,
    StreamDone,
    StreamError,
    StreamStart,
    TextDelta,
    collect,
)


def _message(text: str, reason: StopReason = StopReason.STOP) -> AssistantMessage:
    return AssistantMessage(
        content=(TextBlock(text=text),),
        stop_reason=reason,
        usage=Usage(),
        model="mock-1",
        provider="mock",
        timestamp=1,
    )


async def _stream(*chunks: StreamChunk) -> AsyncIterator[StreamChunk]:
    for chunk in chunks:
        yield chunk


async def test_collect_returns_the_settled_message() -> None:
    partial = _message("", StopReason.PENDING)
    final = _message("hello")

    result = await collect(
        _stream(
            StreamStart(partial=partial),
            TextDelta(content_index=0, delta="hello", partial=partial),
            StreamDone(message=final, partial=final),
        )
    )

    assert result is final


async def test_collect_returns_an_error_message_without_raising() -> None:
    """The stream never raises once returned; failures ride it (spec section 4)."""
    failed = _message("", StopReason.ERROR)

    result = await collect(
        _stream(StreamError(reason=StopReason.ERROR, message=failed, partial=failed))
    )

    assert result.stop_reason is StopReason.ERROR


async def test_collect_on_an_empty_stream_raises_a_protocol_error() -> None:
    """An adapter that yields nothing violated its contract; that is a bug in
    the adapter, not an in-band model failure, so it raises."""
    import pytest

    from minion_agent.llm.errors import AdapterProtocolError

    with pytest.raises(AdapterProtocolError, match="terminal chunk"):
        await collect(_stream())


async def test_deltas_carry_the_partial_message() -> None:
    partial = _message("he", StopReason.PENDING)
    chunk = TextDelta(content_index=0, delta="llo", partial=partial)

    assert chunk.partial.stop_reason is StopReason.PENDING
    assert chunk.delta == "llo"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/pytest tests/llm/test_stream.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'minion_agent.llm.stream'`

- [ ] **Step 3: Write the errors module**

Create `src/minion_agent/llm/errors.py`:

```python
"""Eager-side LLM errors.

These raise *before* a stream is returned. Once a stream exists, nothing
escapes iteration — failures ride the stream as a terminal error chunk
(design spec section 4).
"""


class LlmError(Exception):
    """Base for eager-side LLM errors."""


class UnknownModelError(LlmError):
    """A model or provider was requested that no adapter supplies."""


class AdapterProtocolError(LlmError):
    """An adapter violated the stream contract.

    Not an in-band model failure — a bug in the adapter — so it raises rather
    than being encoded as a stopped message.
    """
```

- [ ] **Step 4: Write the stream module**

Create `src/minion_agent/llm/stream.py`:

```python
"""Streaming chunk vocabulary and the never-raises collection helper.

Every chunk carries `partial`, the message as assembled so far, so a consumer
can render any prefix without tracking state of its own.

Images do not stream: there are no image delta chunks by design. An image is
present in a message or it is not.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass

from .content import ToolCallBlock
from .errors import AdapterProtocolError
from .messages import AssistantMessage, StopReason


@dataclass(frozen=True, slots=True)
class StreamStart:
    partial: AssistantMessage


@dataclass(frozen=True, slots=True)
class TextStart:
    content_index: int
    partial: AssistantMessage


@dataclass(frozen=True, slots=True)
class TextDelta:
    content_index: int
    delta: str
    partial: AssistantMessage


@dataclass(frozen=True, slots=True)
class TextEnd:
    content_index: int
    text: str
    partial: AssistantMessage


@dataclass(frozen=True, slots=True)
class ThinkingStart:
    content_index: int
    partial: AssistantMessage


@dataclass(frozen=True, slots=True)
class ThinkingDelta:
    content_index: int
    delta: str
    partial: AssistantMessage


@dataclass(frozen=True, slots=True)
class ThinkingEnd:
    content_index: int
    thinking: str
    partial: AssistantMessage


@dataclass(frozen=True, slots=True)
class ToolCallStart:
    content_index: int
    partial: AssistantMessage


@dataclass(frozen=True, slots=True)
class ToolCallDelta:
    content_index: int
    delta: str
    partial: AssistantMessage


@dataclass(frozen=True, slots=True)
class ToolCallEnd:
    content_index: int
    tool_call: ToolCallBlock
    partial: AssistantMessage


@dataclass(frozen=True, slots=True)
class StreamDone:
    message: AssistantMessage
    partial: AssistantMessage


@dataclass(frozen=True, slots=True)
class StreamError:
    reason: StopReason
    message: AssistantMessage
    partial: AssistantMessage


type StreamChunk = (
    StreamStart
    | TextStart
    | TextDelta
    | TextEnd
    | ThinkingStart
    | ThinkingDelta
    | ThinkingEnd
    | ToolCallStart
    | ToolCallDelta
    | ToolCallEnd
    | StreamDone
    | StreamError
)

type AssistantStream = AsyncIterator[StreamChunk]


async def collect(stream: AssistantStream) -> AssistantMessage:
    """Drain `stream` and return its settled message.

    Never raises for model, network, or cancellation failures — those arrive
    as a `StreamError` whose message carries the reason. Raises only when an
    adapter breaks its contract by ending without a terminal chunk.
    """
    async for chunk in stream:
        if isinstance(chunk, StreamDone | StreamError):
            return chunk.message
    raise AdapterProtocolError("stream ended without a terminal chunk")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/Scripts/pytest tests/llm/test_stream.py -v`
Expected: PASS — four tests.

- [ ] **Step 6: Commit**

```bash
git add src/minion_agent/llm/stream.py src/minion_agent/llm/errors.py tests/llm/test_stream.py
git commit -m "feat: add LLM stream chunk vocabulary and never-raises collection"
```

---

## Task 4: The LLM seam and its never-raises boundary

**Files:**
- Create: `src/minion_agent/llm/service.py`
- Test: `tests/llm/test_service.py`

**Interfaces:**
- Consumes: `stream`, `messages`, `errors`, runtime `Context`.
- Produces:
  - `@dataclass(frozen=True) class ModelId` with `provider: str`, `model: str`
  - `@dataclass(frozen=True) class Request` with `model: ModelId`, `system: str`, `messages: tuple[Message, ...]`, `max_output_tokens: int | None = None`
  - `class Adapter(Protocol)` with `provider: str`, `models: frozenset[str]`, and `def stream(self, request: Request) -> AssistantStream`
  - `class LlmService` with `__service_name__ = "llm"`, `register(adapter) -> Callable[[], None]`, `models() -> frozenset[ModelId]`, and `def stream(self, request: Request) -> AssistantStream`
  - `LlmService.stream` raises `UnknownModelError` **eagerly** for an unregistered model; every other failure rides the returned stream.

- [ ] **Step 1: Write the failing test**

Create `tests/llm/test_service.py`:

```python
"""The seam resolves adapters and enforces the never-raises boundary."""

from collections.abc import AsyncIterator

import pytest

from minion_agent.llm.content import TextBlock
from minion_agent.llm.errors import UnknownModelError
from minion_agent.llm.messages import AssistantMessage, StopReason, Usage
from minion_agent.llm.service import LlmService, ModelId, Request
from minion_agent.llm.stream import StreamChunk, StreamDone, StreamError, collect


def _settled(reason: StopReason = StopReason.STOP) -> AssistantMessage:
    return AssistantMessage(
        content=(TextBlock(text="ok"),),
        stop_reason=reason,
        usage=Usage(input=1, output=1),
        model="mock-1",
        provider="mock",
        timestamp=1,
    )


class GoodAdapter:
    provider = "mock"
    models = frozenset({"mock-1"})

    def stream(self, request: Request) -> AsyncIterator[StreamChunk]:
        async def run() -> AsyncIterator[StreamChunk]:
            message = _settled()
            yield StreamDone(message=message, partial=message)

        return run()


class FailingAdapter:
    """Fails the way an adapter must: in-band, never by raising."""

    provider = "mock"
    models = frozenset({"mock-1"})

    def stream(self, request: Request) -> AsyncIterator[StreamChunk]:
        async def run() -> AsyncIterator[StreamChunk]:
            message = _settled(StopReason.ERROR)
            yield StreamError(reason=StopReason.ERROR, message=message, partial=message)

        return run()


def _request(model: str = "mock-1") -> Request:
    return Request(model=ModelId("mock", model), system="", messages=())


async def test_a_registered_model_streams() -> None:
    service = LlmService()
    service.register(GoodAdapter())

    result = await collect(service.stream(_request()))

    assert result.stop_reason is StopReason.STOP


async def test_an_unknown_model_raises_eagerly() -> None:
    """A caller bug, discoverable immediately — not buried in the transcript."""
    service = LlmService()
    service.register(GoodAdapter())

    with pytest.raises(UnknownModelError, match="mock-9"):
        service.stream(_request("mock-9"))


async def test_provider_failures_ride_the_stream() -> None:
    service = LlmService()
    service.register(FailingAdapter())

    result = await collect(service.stream(_request()))

    assert result.stop_reason is StopReason.ERROR


def test_models_lists_every_registered_pair() -> None:
    service = LlmService()
    service.register(GoodAdapter())

    assert service.models() == frozenset({ModelId("mock", "mock-1")})


def test_unregistering_withdraws_the_models() -> None:
    service = LlmService()
    withdraw = service.register(GoodAdapter())

    withdraw()

    assert service.models() == frozenset()
    with pytest.raises(UnknownModelError):
        service.stream(_request())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/pytest tests/llm/test_service.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'minion_agent.llm.service'`

- [ ] **Step 3: Write the implementation**

Create `src/minion_agent/llm/service.py`:

```python
"""The `ctx.llm` seam: model identity, adapters, and the never-raises boundary.

The boundary cuts at the moment a stream is returned (design spec section 4):

* Before  — ordinary exceptions. Unknown models, bad configuration, and
  programming errors raise, because they are caller bugs discoverable
  immediately. Reporting a mistyped model name as a streamed error message
  would bury a caller bug in the transcript.
* After   — nothing escapes iteration. Provider, network, model, and
  cancellation failures terminate the stream with an error chunk.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from .errors import UnknownModelError
from .messages import Message
from .stream import AssistantStream


@dataclass(frozen=True, slots=True)
class ModelId:
    """A provider and one of its models."""

    provider: str
    model: str


@dataclass(frozen=True, slots=True)
class Request:
    """One logical request to a model."""

    model: ModelId
    system: str
    messages: tuple[Message, ...]
    max_output_tokens: int | None = None


class Adapter(Protocol):
    """A provider adapter.

    `stream` must not raise for provider, network, model, or cancellation
    failures; it encodes them in the returned stream instead.
    """

    provider: str
    models: frozenset[str]

    def stream(self, request: Request) -> AssistantStream: ...


class LlmService:
    """Resolves a request's model to an adapter."""

    __service_name__ = "llm"

    def __init__(self) -> None:
        self._adapters: dict[ModelId, Adapter] = {}

    def register(self, adapter: Adapter) -> Callable[[], None]:
        """Register every model `adapter` supplies; returns a withdrawal handle."""
        ids = [ModelId(adapter.provider, model) for model in adapter.models]
        for model_id in ids:
            self._adapters[model_id] = adapter

        def withdraw() -> None:
            for model_id in ids:
                if self._adapters.get(model_id) is adapter:
                    del self._adapters[model_id]

        return withdraw

    def models(self) -> frozenset[ModelId]:
        """Every currently resolvable model."""
        return frozenset(self._adapters)

    def stream(self, request: Request) -> AssistantStream:
        """Dispatch `request` to its adapter.

        Raises `UnknownModelError` eagerly when no adapter supplies the model.
        """
        adapter = self._adapters.get(request.model)
        if adapter is None:
            raise UnknownModelError(
                f"no adapter supplies {request.model.provider}/{request.model.model}"
            )
        return adapter.stream(request)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/pytest tests/llm/test_service.py -v`
Expected: PASS — five tests.

- [ ] **Step 5: Commit**

```bash
git add src/minion_agent/llm/service.py tests/llm/test_service.py
git commit -m "feat: add the LLM seam with its eager/in-band failure boundary"
```

---

## Task 5: The scripted mock adapter

Drives every conformance case. It is a first-class adapter, not a test double
bolted on — the conformance suite depends on it behaving exactly like a
provider that never raises.

**Files:**
- Create: `src/minion_agent/llm/adapters/__init__.py`
- Create: `src/minion_agent/llm/adapters/mock.py`
- Test: `tests/llm/test_mock_adapter.py`

**Interfaces:**
- Consumes: `content`, `messages`, `stream`, `service`.
- Produces:
  - `@dataclass class ScriptedResponse` with `content: tuple[ContentBlock, ...]`, `stop_reason: StopReason`, `usage: Usage = Usage()`, `error_message: str | None = None`
  - `class MockAdapter` with `provider = "mock"`, `models = frozenset({"mock-1"})`, `__init__(self, script: Sequence[ScriptedResponse])`, `requests: list[Request]` recording what it was asked
  - Emits `StreamStart`, one `TextDelta` per text block, then `StreamDone` (or `StreamError` when the scripted stop reason is `ERROR`/`ABORTED`).
  - Exhausting the script yields a `StreamError` rather than raising — a scenario that under-scripts gets a diagnosable in-band failure, not a crash mid-turn.

- [ ] **Step 1: Write the failing test**

Create `tests/llm/test_mock_adapter.py`:

```python
"""The scripted adapter behaves exactly like a provider that never raises."""

from minion_agent.llm.adapters.mock import MockAdapter, ScriptedResponse
from minion_agent.llm.content import TextBlock, ToolCallBlock
from minion_agent.llm.messages import StopReason, Usage
from minion_agent.llm.service import ModelId, Request
from minion_agent.llm.stream import StreamDone, StreamError, TextDelta, collect


def _request(text: str = "hello") -> Request:
    from minion_agent.llm.messages import UserMessage

    return Request(
        model=ModelId("mock", "mock-1"),
        system="be helpful",
        messages=(UserMessage(content=(TextBlock(text=text),), timestamp=1),),
    )


async def test_a_scripted_text_response_streams_and_settles() -> None:
    adapter = MockAdapter([ScriptedResponse((TextBlock(text="hi"),), StopReason.STOP)])

    chunks = [chunk async for chunk in adapter.stream(_request())]

    assert isinstance(chunks[-1], StreamDone)
    assert any(isinstance(chunk, TextDelta) for chunk in chunks)
    assert chunks[-1].message.stop_reason is StopReason.STOP


async def test_responses_are_returned_in_script_order() -> None:
    adapter = MockAdapter(
        [
            ScriptedResponse((TextBlock(text="first"),), StopReason.STOP),
            ScriptedResponse((TextBlock(text="second"),), StopReason.STOP),
        ]
    )

    first = await collect(adapter.stream(_request()))
    second = await collect(adapter.stream(_request()))

    assert (first.content[0].text, second.content[0].text) == ("first", "second")


async def test_a_tool_call_response_settles_with_tool_use() -> None:
    adapter = MockAdapter(
        [
            ScriptedResponse(
                (ToolCallBlock(id="t1", name="bash", arguments={"command": "ls"}),),
                StopReason.TOOL_USE,
            )
        ]
    )

    message = await collect(adapter.stream(_request()))

    assert message.stop_reason is StopReason.TOOL_USE
    assert message.content[0].name == "bash"


async def test_a_scripted_error_rides_the_stream() -> None:
    adapter = MockAdapter(
        [ScriptedResponse((), StopReason.ERROR, error_message="upstream 500")]
    )

    chunks = [chunk async for chunk in adapter.stream(_request())]

    assert isinstance(chunks[-1], StreamError)
    assert chunks[-1].message.error_message == "upstream 500"


async def test_exhausting_the_script_fails_in_band() -> None:
    """An under-scripted scenario gets a diagnosable failure, not a crash."""
    adapter = MockAdapter([])

    message = await collect(adapter.stream(_request()))

    assert message.stop_reason is StopReason.ERROR
    assert "exhausted" in (message.error_message or "")


async def test_the_adapter_records_what_it_was_asked() -> None:
    adapter = MockAdapter([ScriptedResponse((), StopReason.STOP)])

    await collect(adapter.stream(_request("remember me")))

    assert adapter.requests[0].system == "be helpful"
    assert len(adapter.requests) == 1


async def test_usage_is_carried_through() -> None:
    adapter = MockAdapter(
        [ScriptedResponse((), StopReason.STOP, usage=Usage(input=7, output=3))]
    )

    message = await collect(adapter.stream(_request()))

    assert message.usage.total == 10
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/pytest tests/llm/test_mock_adapter.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'minion_agent.llm.adapters'`

- [ ] **Step 3: Write the implementation**

Create `src/minion_agent/llm/adapters/__init__.py`:

```python
"""Provider adapters. The mock adapter drives conformance; real ones land later."""
```

Create `src/minion_agent/llm/adapters/mock.py`:

```python
"""A scripted adapter: deterministic responses, no network, no clock.

This is a real adapter, not a test double. Conformance depends on it honouring
the never-raises contract exactly — including when a scenario under-scripts it,
which fails in-band so the scenario reports a diagnosable model error rather
than crashing the run.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass

from ..content import ContentBlock, TextBlock
from ..messages import AssistantMessage, StopReason, Usage
from ..service import Request
from ..stream import (
    StreamChunk,
    StreamDone,
    StreamError,
    StreamStart,
    TextDelta,
)

_ERROR_REASONS = frozenset({StopReason.ERROR, StopReason.ABORTED})


@dataclass(frozen=True, slots=True)
class ScriptedResponse:
    """One response the adapter will return, in order."""

    content: tuple[ContentBlock, ...]
    stop_reason: StopReason
    usage: Usage = Usage()
    error_message: str | None = None


class MockAdapter:
    """Returns scripted responses in order, recording each request."""

    provider = "mock"
    models = frozenset({"mock-1"})

    def __init__(self, script: Sequence[ScriptedResponse]) -> None:
        self._script = list(script)
        self._next = 0
        self.requests: list[Request] = []

    def _take(self) -> ScriptedResponse:
        if self._next >= len(self._script):
            return ScriptedResponse(
                content=(),
                stop_reason=StopReason.ERROR,
                error_message=(
                    f"mock script exhausted after {len(self._script)} response(s); "
                    "the scenario asked for one more"
                ),
            )
        response = self._script[self._next]
        self._next += 1
        return response

    def stream(self, request: Request) -> AsyncIterator[StreamChunk]:
        self.requests.append(request)
        response = self._take()

        def build(reason: StopReason) -> AssistantMessage:
            return AssistantMessage(
                content=response.content,
                stop_reason=reason,
                usage=response.usage,
                model=request.model.model,
                provider=request.model.provider,
                timestamp=len(self.requests),
                error_message=response.error_message,
            )

        async def run() -> AsyncIterator[StreamChunk]:
            pending = build(StopReason.PENDING)
            yield StreamStart(partial=pending)

            for index, block in enumerate(response.content):
                if isinstance(block, TextBlock):
                    yield TextDelta(content_index=index, delta=block.text, partial=pending)

            settled = build(response.stop_reason)
            if response.stop_reason in _ERROR_REASONS:
                yield StreamError(
                    reason=response.stop_reason, message=settled, partial=settled
                )
            else:
                yield StreamDone(message=settled, partial=settled)

        return run()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/pytest tests/llm/test_mock_adapter.py -v`
Expected: PASS — seven tests.

- [ ] **Step 5: Commit**

```bash
git add src/minion_agent/llm/adapters tests/llm/test_mock_adapter.py
git commit -m "feat: add the scripted mock adapter"
```

---

## Task 6: Session events

**Files:**
- Create: `src/minion_agent/session/__init__.py`
- Create: `src/minion_agent/session/events.py`
- Test: `tests/session/test_events.py`

**Interfaces:**
- Consumes: `llm.messages`.
- Produces:
  - `class EventKind(StrEnum)` with the full map: `TURN_START`, `TURN_END`, `STEP_START`, `STEP_END`, `USER_MESSAGE`, `ASSISTANT_MESSAGE`, `TOOL_RESULT`, `ASSISTANT_CHUNK`, `TOOL_CALL`, `REQUEST_HEADER`, `SESSION_FORKED`, `SESSION_RESET`, `COMPACTION`
  - `SURFACE_KINDS: frozenset[EventKind]` — exactly `{USER_MESSAGE, ASSISTANT_MESSAGE, TOOL_RESULT}`
  - `@dataclass(frozen=True, slots=True) class SessionEvent` with `seq: int`, `kind: EventKind`, `data: dict[str, Any]`
  - `def is_surface(event) -> bool`

- [ ] **Step 1: Write the failing test**

Create `tests/session/test_events.py`:

```python
"""Two tiers of event: the surface projects to the model, the rest does not."""

from minion_agent.session.events import (
    SURFACE_KINDS,
    EventKind,
    SessionEvent,
    is_surface,
)


def test_the_surface_is_exactly_three_kinds() -> None:
    """Widening this set widens what the model sees, so it is pinned."""
    assert SURFACE_KINDS == {
        EventKind.USER_MESSAGE,
        EventKind.ASSISTANT_MESSAGE,
        EventKind.TOOL_RESULT,
    }


def test_lifecycle_events_are_not_surface() -> None:
    for kind in (
        EventKind.TURN_START,
        EventKind.STEP_START,
        EventKind.ASSISTANT_CHUNK,
        EventKind.TOOL_CALL,
        EventKind.REQUEST_HEADER,
    ):
        assert not is_surface(SessionEvent(seq=1, kind=kind, data={}))


def test_a_surface_event_reports_as_surface() -> None:
    event = SessionEvent(seq=1, kind=EventKind.USER_MESSAGE, data={"text": "hi"})

    assert is_surface(event)


def test_operation_events_exist_and_are_not_surface() -> None:
    """Fork, reset, and compaction change derivation without being messages."""
    for kind in (EventKind.SESSION_FORKED, EventKind.SESSION_RESET, EventKind.COMPACTION):
        assert not is_surface(SessionEvent(seq=1, kind=kind, data={}))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/pytest tests/session/test_events.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'minion_agent.session'`

- [ ] **Step 3: Write the implementation**

Create `src/minion_agent/session/__init__.py` with a module docstring, and
`src/minion_agent/session/events.py`:

```python
"""The session event vocabulary.

Two tiers (design spec section 5). The *surface* subset is what
`derive_messages()` projects into model history; everything else is log-only —
lifecycle, replay fidelity, and the operations that change how derivation
reads the surface.

Model-visible means logged: anything reaching a model request must be
reconstructable from these events.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class EventKind(StrEnum):
    """Every event a session log can carry."""

    # --- surface: projects into model history ---
    USER_MESSAGE = "user/message"
    ASSISTANT_MESSAGE = "assistant/message"
    TOOL_RESULT = "tool/result"

    # --- log-only: lifecycle ---
    TURN_START = "turn/start"
    TURN_END = "turn/end"
    STEP_START = "step/start"
    STEP_END = "step/end"

    # --- log-only: fidelity and request reconstruction ---
    ASSISTANT_CHUNK = "assistant/chunk"
    TOOL_CALL = "tool/call"
    REQUEST_HEADER = "request/header"

    # --- log-only: operations that change derivation ---
    SESSION_FORKED = "session/forked"
    SESSION_RESET = "session/reset"
    COMPACTION = "compaction"


SURFACE_KINDS: frozenset[EventKind] = frozenset(
    {EventKind.USER_MESSAGE, EventKind.ASSISTANT_MESSAGE, EventKind.TOOL_RESULT}
)
"""Exactly the kinds that project into model history.

Widening this set widens what the model sees, which is why it is stated once
here rather than inferred at each call site.
"""


@dataclass(frozen=True, slots=True)
class SessionEvent:
    """One appended event. `seq` is assigned by the log, never by a caller."""

    seq: int
    kind: EventKind
    data: dict[str, Any]


def is_surface(event: SessionEvent) -> bool:
    """Whether `event` projects into model history."""
    return event.kind in SURFACE_KINDS
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/pytest tests/session/test_events.py -v`
Expected: PASS — four tests.

- [ ] **Step 5: Commit**

```bash
git add src/minion_agent/session tests/session
git commit -m "feat: add the session event vocabulary with its surface subset"
```

---

## Task 7: The append-only log

**Files:**
- Create: `src/minion_agent/session/log.py`
- Test: `tests/session/test_log.py`

**Interfaces:**
- Consumes: `events`.
- Produces:
  - `class SessionLog` with `session_id: str`, `append(kind, data) -> SessionEvent`, `events: tuple[SessionEvent, ...]`, `__len__`, `surface() -> tuple[SessionEvent, ...]`
  - Sequence numbers start at 1 and strictly increase.
  - `append` validates that `data` is JSON-safe, raising `NotJsonSafeError` otherwise.
  - `class NotJsonSafeError(Exception)` in the same module.

- [ ] **Step 1: Write the failing test**

Create `tests/session/test_log.py`:

```python
"""The log is append-only, sequence-numbered, and JSON-validated at append."""

import pytest

from minion_agent.session.events import EventKind
from minion_agent.session.log import NotJsonSafeError, SessionLog


def test_sequence_numbers_start_at_one_and_increase() -> None:
    log = SessionLog("s1")

    first = log.append(EventKind.USER_MESSAGE, {"text": "a"})
    second = log.append(EventKind.USER_MESSAGE, {"text": "b"})

    assert (first.seq, second.seq) == (1, 2)


def test_events_are_returned_in_append_order() -> None:
    log = SessionLog("s1")
    log.append(EventKind.TURN_START, {"turn": 1})
    log.append(EventKind.USER_MESSAGE, {"text": "a"})

    assert [event.kind for event in log.events] == [
        EventKind.TURN_START,
        EventKind.USER_MESSAGE,
    ]


def test_surface_filters_to_model_visible_events() -> None:
    log = SessionLog("s1")
    log.append(EventKind.TURN_START, {"turn": 1})
    log.append(EventKind.USER_MESSAGE, {"text": "a"})
    log.append(EventKind.ASSISTANT_CHUNK, {"delta": "x"})
    log.append(EventKind.ASSISTANT_MESSAGE, {"text": "b"})

    assert [event.kind for event in log.surface()] == [
        EventKind.USER_MESSAGE,
        EventKind.ASSISTANT_MESSAGE,
    ]


def test_non_json_safe_data_is_rejected_at_append() -> None:
    """Rejecting at the source is what keeps the log replayable and portable."""
    log = SessionLog("s1")

    with pytest.raises(NotJsonSafeError, match="not JSON-safe"):
        log.append(EventKind.USER_MESSAGE, {"blob": object()})

    assert len(log) == 0


def test_nested_non_json_safe_data_is_also_rejected() -> None:
    log = SessionLog("s1")

    with pytest.raises(NotJsonSafeError):
        log.append(EventKind.USER_MESSAGE, {"outer": {"inner": {1, 2}}})


def test_bytes_are_rejected_because_json_has_no_bytes() -> None:
    log = SessionLog("s1")

    with pytest.raises(NotJsonSafeError):
        log.append(EventKind.USER_MESSAGE, {"image": b"\x89PNG"})


def test_the_log_reports_its_session_id_and_length() -> None:
    log = SessionLog("s1")
    log.append(EventKind.USER_MESSAGE, {"text": "a"})

    assert log.session_id == "s1"
    assert len(log) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/pytest tests/session/test_log.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'minion_agent.session.log'`

- [ ] **Step 3: Write the implementation**

Create `src/minion_agent/session/log.py`:

```python
"""The append-only session log.

Sequence-numbered and JSON-validated at append, because the log is the
system's semantic truth: it must replay exactly and port to another language
without carrying Python-only values.
"""

from __future__ import annotations

from typing import Any

from .events import SessionEvent, is_surface
from .events import EventKind

_JSON_SCALARS = (str, int, float, bool, type(None))


class NotJsonSafeError(Exception):
    """Event data contained a value JSON cannot represent."""


def _check_json_safe(value: Any, path: str = "data") -> None:
    """Raise unless `value` is representable in JSON.

    `bool` is checked before `int` implicitly by isinstance ordering in
    `_JSON_SCALARS`; both are acceptable, so no special case is needed.
    """
    if isinstance(value, _JSON_SCALARS):
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise NotJsonSafeError(f"{path}: object keys must be strings, got {key!r}")
            _check_json_safe(item, f"{path}.{key}")
        return
    if isinstance(value, list | tuple):
        for index, item in enumerate(value):
            _check_json_safe(item, f"{path}[{index}]")
        return
    raise NotJsonSafeError(f"{path}: {type(value).__name__} is not JSON-safe")


class SessionLog:
    """An ordered, append-only sequence of events."""

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self._events: list[SessionEvent] = []

    def __len__(self) -> int:
        return len(self._events)

    @property
    def events(self) -> tuple[SessionEvent, ...]:
        """Every event, in append order."""
        return tuple(self._events)

    def append(self, kind: EventKind, data: dict[str, Any]) -> SessionEvent:
        """Append one event, assigning the next sequence number.

        Validates before appending, so a rejected event leaves no trace.
        """
        _check_json_safe(data)
        event = SessionEvent(seq=len(self._events) + 1, kind=kind, data=dict(data))
        self._events.append(event)
        return event

    def surface(self) -> tuple[SessionEvent, ...]:
        """Only the events that project into model history."""
        return tuple(event for event in self._events if is_surface(event))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/pytest tests/session/test_log.py -v`
Expected: PASS — seven tests.

- [ ] **Step 5: Commit**

```bash
git add src/minion_agent/session/log.py tests/session/test_log.py
git commit -m "feat: add the append-only session log with JSON validation"
```

---

## Task 8: Derivation

**Files:**
- Create: `src/minion_agent/session/derive.py`
- Test: `tests/session/test_derive.py`

**Interfaces:**
- Consumes: `events`, `log`, `llm.messages`, `llm.content`.
- Produces:
  - `def derive_messages(log: SessionLog) -> tuple[Message, ...]`
  - Surface events carry their message under `data["message"]` in a serialised form; `derive.py` owns the encode/decode pair: `encode_message(Message) -> dict` and `decode_message(dict) -> Message`.
  - Round-tripping is exact for every message type and content block.
- Note: reset, fork, and compaction change derivation. This task derives the *unmodified* surface; Tasks 11–13 add each operation's effect, each with its own tests.

- [ ] **Step 1: Write the failing test**

Create `tests/session/test_derive.py`:

```python
"""Derivation projects the surface into model history."""

from minion_agent.llm.content import ImageBlock, TextBlock, ThinkingBlock, ToolCallBlock
from minion_agent.llm.messages import (
    AssistantMessage,
    StopReason,
    ToolResultMessage,
    Usage,
    UserMessage,
)
from minion_agent.session.derive import decode_message, derive_messages, encode_message
from minion_agent.session.events import EventKind
from minion_agent.session.log import SessionLog


def _user(text: str) -> UserMessage:
    return UserMessage(content=(TextBlock(text=text),), timestamp=1)


def _assistant(text: str) -> AssistantMessage:
    return AssistantMessage(
        content=(TextBlock(text=text),),
        stop_reason=StopReason.STOP,
        usage=Usage(input=1, output=1),
        model="mock-1",
        provider="mock",
        timestamp=2,
    )


def _append(log: SessionLog, kind: EventKind, message: object) -> None:
    log.append(kind, {"message": encode_message(message)})  # type: ignore[arg-type]


def test_an_empty_log_derives_nothing() -> None:
    assert derive_messages(SessionLog("s1")) == ()


def test_surface_events_derive_in_order() -> None:
    log = SessionLog("s1")
    _append(log, EventKind.USER_MESSAGE, _user("hello"))
    _append(log, EventKind.ASSISTANT_MESSAGE, _assistant("hi"))

    derived = derive_messages(log)

    assert [type(message).__name__ for message in derived] == [
        "UserMessage",
        "AssistantMessage",
    ]


def test_log_only_events_do_not_derive() -> None:
    log = SessionLog("s1")
    log.append(EventKind.TURN_START, {"turn": 1})
    _append(log, EventKind.USER_MESSAGE, _user("hello"))
    log.append(EventKind.ASSISTANT_CHUNK, {"delta": "h"})
    log.append(EventKind.REQUEST_HEADER, {"system": "x"})

    assert len(derive_messages(log)) == 1


def test_user_message_round_trips() -> None:
    message = _user("hello")

    assert decode_message(encode_message(message)) == message


def test_assistant_message_round_trips_with_accounting() -> None:
    message = _assistant("hi")

    restored = decode_message(encode_message(message))

    assert restored == message
    assert restored.usage.input == 1


def test_tool_result_message_round_trips() -> None:
    message = ToolResultMessage(
        tool_call_id="t1", content=(TextBlock(text="ok"),), timestamp=3, is_error=True
    )

    assert decode_message(encode_message(message)) == message


def test_every_content_block_round_trips() -> None:
    message = UserMessage(
        content=(
            TextBlock(text="t"),
            ThinkingBlock(thinking="r"),
            ImageBlock(mime_type="image/png", reference="sha256:abc"),
            ToolCallBlock(id="t1", name="bash", arguments={"command": "ls"}),
        ),
        timestamp=1,
    )

    assert decode_message(encode_message(message)) == message


def test_encoded_messages_are_json_safe() -> None:
    """Encoding must produce something the log will accept."""
    log = SessionLog("s1")

    log.append(EventKind.USER_MESSAGE, {"message": encode_message(_user("hello"))})

    assert len(log) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/pytest tests/session/test_derive.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'minion_agent.session.derive'`

- [ ] **Step 3: Write the implementation**

Create `src/minion_agent/session/derive.py`:

```python
"""Projecting the log's surface into model history.

Encoding lives here rather than on the message types because it is a property
of *storage*, not of the vocabulary: the LLM layer must not know a log exists.

Images encode by reference only when they already carry one; inline bytes are
base64-encoded so the log stays JSON-safe. The session service resolves inline
images to content-addressed references before dispatch, so a logged reference
is immutable (design spec section 4).
"""

from __future__ import annotations

import base64
from typing import Any

from ..llm.content import ContentBlock, ImageBlock, TextBlock, ThinkingBlock, ToolCallBlock
from ..llm.messages import (
    AssistantMessage,
    Message,
    StopReason,
    ToolResultMessage,
    Usage,
    UserMessage,
)
from .events import SessionEvent
from .log import SessionLog


def _encode_block(block: ContentBlock) -> dict[str, Any]:
    match block:
        case TextBlock():
            return {"type": "text", "text": block.text}
        case ThinkingBlock():
            return {"type": "thinking", "thinking": block.thinking}
        case ImageBlock():
            encoded: dict[str, Any] = {"type": "image", "mime_type": block.mime_type}
            if block.reference is not None:
                encoded["reference"] = block.reference
            else:
                assert block.data is not None  # guaranteed by ImageBlock.__post_init__
                encoded["data"] = base64.b64encode(block.data).decode("ascii")
            return encoded
        case ToolCallBlock():
            return {
                "type": "tool_call",
                "id": block.id,
                "name": block.name,
                "arguments": block.arguments,
            }


def _decode_block(raw: dict[str, Any]) -> ContentBlock:
    kind = raw["type"]
    if kind == "text":
        return TextBlock(text=raw["text"])
    if kind == "thinking":
        return ThinkingBlock(thinking=raw["thinking"])
    if kind == "image":
        if "reference" in raw:
            return ImageBlock(mime_type=raw["mime_type"], reference=raw["reference"])
        return ImageBlock(
            mime_type=raw["mime_type"], data=base64.b64decode(raw["data"])
        )
    if kind == "tool_call":
        return ToolCallBlock(id=raw["id"], name=raw["name"], arguments=raw["arguments"])
    raise ValueError(f"unknown content block type {kind!r}")


def encode_message(message: Message) -> dict[str, Any]:
    """Render `message` as JSON-safe data the log will accept."""
    content = [_encode_block(block) for block in message.content]
    match message:
        case UserMessage():
            return {"role": "user", "content": content, "timestamp": message.timestamp}
        case AssistantMessage():
            return {
                "role": "assistant",
                "content": content,
                "timestamp": message.timestamp,
                "stop_reason": message.stop_reason.value,
                "model": message.model,
                "provider": message.provider,
                "error_message": message.error_message,
                "usage": {
                    "input": message.usage.input,
                    "output": message.usage.output,
                    "cache_read": message.usage.cache_read,
                    "cache_write": message.usage.cache_write,
                    "reasoning": message.usage.reasoning,
                },
            }
        case ToolResultMessage():
            return {
                "role": "tool_result",
                "content": content,
                "timestamp": message.timestamp,
                "tool_call_id": message.tool_call_id,
                "is_error": message.is_error,
            }


def decode_message(raw: dict[str, Any]) -> Message:
    """Restore a message encoded by `encode_message`."""
    content = tuple(_decode_block(block) for block in raw["content"])
    role = raw["role"]
    if role == "user":
        return UserMessage(content=content, timestamp=raw["timestamp"])
    if role == "assistant":
        usage = raw["usage"]
        return AssistantMessage(
            content=content,
            stop_reason=StopReason(raw["stop_reason"]),
            usage=Usage(
                input=usage["input"],
                output=usage["output"],
                cache_read=usage["cache_read"],
                cache_write=usage["cache_write"],
                reasoning=usage["reasoning"],
            ),
            model=raw["model"],
            provider=raw["provider"],
            timestamp=raw["timestamp"],
            error_message=raw["error_message"],
        )
    if role == "tool_result":
        return ToolResultMessage(
            tool_call_id=raw["tool_call_id"],
            content=content,
            timestamp=raw["timestamp"],
            is_error=raw["is_error"],
        )
    raise ValueError(f"unknown message role {role!r}")


def messages_from(events: tuple[SessionEvent, ...]) -> tuple[Message, ...]:
    """Decode a run of surface events into messages."""
    return tuple(decode_message(event.data["message"]) for event in events)


def derive_messages(log: SessionLog) -> tuple[Message, ...]:
    """Project `log`'s surface into model history.

    Session operations (fork, reset, compaction) change which surface entries
    participate; those rules are layered on in `operations.py`.
    """
    return messages_from(log.surface())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/pytest tests/session/test_derive.py -v`
Expected: PASS — eight tests.

- [ ] **Step 5: Commit**

```bash
git add src/minion_agent/session/derive.py tests/session/test_derive.py
git commit -m "feat: add session message encoding and surface derivation"
```

---

## Task 9: The content-addressed artifact store

**Files:**
- Create: `src/minion_agent/session/artifacts.py`
- Test: `tests/session/test_artifacts.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `class ArtifactStore` with `put(content: str | bytes) -> str` returning `"sha256:<hex>"`, `get(ref) -> bytes`, `has(ref) -> bool`, `__len__`
  - `put` is idempotent: identical content yields the identical reference and stores one copy.
  - `get` on an unknown reference raises `MissingArtifactError`.
  - Artifacts are never deleted — there is no `delete`, by design (§5).

- [ ] **Step 1: Write the failing test**

Create `tests/session/test_artifacts.py`:

```python
"""Content-addressed storage: one copy per distinct content, never deleted."""

import pytest

from minion_agent.session.artifacts import ArtifactStore, MissingArtifactError


def test_put_returns_a_content_address() -> None:
    store = ArtifactStore()

    ref = store.put("hello")

    assert ref.startswith("sha256:")
    assert store.get(ref) == b"hello"


def test_identical_content_yields_one_copy() -> None:
    """The whole point: a stable 15k prompt block is stored once."""
    store = ArtifactStore()

    first = store.put("a large stable block")
    second = store.put("a large stable block")

    assert first == second
    assert len(store) == 1


def test_different_content_yields_different_references() -> None:
    store = ArtifactStore()

    assert store.put("a") != store.put("b")
    assert len(store) == 2


def test_text_and_its_utf8_bytes_are_the_same_artifact() -> None:
    store = ArtifactStore()

    assert store.put("hello") == store.put(b"hello")


def test_has_reports_membership() -> None:
    store = ArtifactStore()
    ref = store.put("hello")

    assert store.has(ref)
    assert not store.has("sha256:" + "0" * 64)


def test_missing_artifacts_raise() -> None:
    store = ArtifactStore()

    with pytest.raises(MissingArtifactError, match="sha256:"):
        store.get("sha256:" + "0" * 64)


def test_the_store_has_no_delete() -> None:
    """Artifacts holding model-visible content inherit the log's never-delete
    discipline (design spec section 5), so removal is not part of the API."""
    assert not hasattr(ArtifactStore, "delete")
    assert not hasattr(ArtifactStore, "remove")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/pytest tests/session/test_artifacts.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'minion_agent.session.artifacts'`

- [ ] **Step 3: Write the implementation**

Create `src/minion_agent/session/artifacts.py`:

```python
"""Content-addressed storage for large, mostly-stable request components.

A resident agent's system prompt is large, mostly stable, and partly dynamic.
Snapshotting it every step does not scale, and whole-header change detection
does not help — in practice something changes nearly every step, so a
530-token change would force a 19,000-token snapshot.

Storing components by content hash means a stable block is stored once for the
life of a session, however often its neighbours change.

Artifacts holding model-visible content are never deleted, inheriting the
discipline that governs the log itself. There is deliberately no removal API:
no artifact may be reclaimed while any request header references it, and the
log never stops referencing one.
"""

from __future__ import annotations

import hashlib

_PREFIX = "sha256:"


class MissingArtifactError(KeyError):
    """A reference named content this store does not hold."""


class ArtifactStore:
    """Maps content hashes to content."""

    def __init__(self) -> None:
        self._content: dict[str, bytes] = {}

    def __len__(self) -> int:
        return len(self._content)

    @staticmethod
    def _as_bytes(content: str | bytes) -> bytes:
        return content.encode("utf-8") if isinstance(content, str) else content

    def put(self, content: str | bytes) -> str:
        """Store `content` and return its reference. Idempotent."""
        raw = self._as_bytes(content)
        ref = _PREFIX + hashlib.sha256(raw).hexdigest()
        self._content.setdefault(ref, raw)
        return ref

    def get(self, ref: str) -> bytes:
        """Return the content `ref` names."""
        try:
            return self._content[ref]
        except KeyError:
            raise MissingArtifactError(f"no artifact for {ref}") from None

    def has(self, ref: str) -> bool:
        """Whether this store holds `ref`."""
        return ref in self._content
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/pytest tests/session/test_artifacts.py -v`
Expected: PASS — seven tests.

- [ ] **Step 5: Commit**

```bash
git add src/minion_agent/session/artifacts.py tests/session/test_artifacts.py
git commit -m "feat: add the content-addressed artifact store"
```

---

## Task 10: Request header composition and reconstruction

**Files:**
- Create: `src/minion_agent/session/request_header.py`
- Test: `tests/session/test_request_header.py`

**Interfaces:**
- Consumes: `artifacts`, `log`, `events`.
- Produces:
  - `@dataclass(frozen=True) class HeaderComponents` — a mapping of component name to text (`system_base`, `skills`, `tools`, `memory`, `task`, …); the names are open, the mechanism is not.
  - `def record_header(log, store, components: dict[str, str], model: str) -> SessionEvent` — puts each component, appends a `REQUEST_HEADER` event holding only references.
  - `def reconstruct_header(event, store) -> dict[str, str]` — resolves references back to content.
  - `def assemble_system(components: dict[str, str]) -> str` — the canonical join, so reconstruction and dispatch agree byte-for-byte.

- [ ] **Step 1: Write the failing test**

Create `tests/session/test_request_header.py`:

```python
"""Request state is reconstructable from content-addressed components."""

from minion_agent.session.artifacts import ArtifactStore
from minion_agent.session.events import EventKind
from minion_agent.session.log import SessionLog
from minion_agent.session.request_header import (
    assemble_system,
    reconstruct_header,
    record_header,
)

BOOTSTRAP = "a very large stable bootstrap block " * 100


def test_recording_a_header_logs_references_not_content() -> None:
    log, store = SessionLog("s1"), ArtifactStore()

    event = record_header(log, store, {"system_base": BOOTSTRAP}, model="mock-1")

    assert event.kind is EventKind.REQUEST_HEADER
    assert event.data["components"]["system_base"].startswith("sha256:")
    assert BOOTSTRAP not in str(event.data)


def test_a_stable_component_is_stored_once_across_many_steps() -> None:
    """The motivating case: a 15k block must not be re-snapshotted per step."""
    log, store = SessionLog("s1"), ArtifactStore()

    for step in range(10):
        record_header(
            log,
            store,
            {"system_base": BOOTSTRAP, "memory": f"recall for step {step}"},
            model="mock-1",
        )

    # One bootstrap plus ten distinct memory blocks.
    assert len(store) == 11
    assert len(log) == 10


def test_a_header_reconstructs_exactly() -> None:
    log, store = SessionLog("s1"), ArtifactStore()
    components = {"system_base": BOOTSTRAP, "memory": "recalled"}

    event = record_header(log, store, components, model="mock-1")

    assert reconstruct_header(event, store) == components


def test_reconstruction_matches_what_was_dispatched() -> None:
    """The property the invariant checks: the model saw what the log says."""
    log, store = SessionLog("s1"), ArtifactStore()
    components = {"system_base": "you are helpful", "memory": "user likes tea"}
    dispatched = assemble_system(components)

    event = record_header(log, store, components, model="mock-1")

    assert assemble_system(reconstruct_header(event, store)) == dispatched


def test_component_order_is_stable_regardless_of_insertion_order() -> None:
    """Byte-for-byte agreement requires a canonical order, not dict order."""
    one = assemble_system({"memory": "m", "system_base": "s"})
    two = assemble_system({"system_base": "s", "memory": "m"})

    assert one == two


def test_the_model_is_recorded_alongside_the_components() -> None:
    log, store = SessionLog("s1"), ArtifactStore()

    event = record_header(log, store, {"system_base": "s"}, model="mock-1")

    assert event.data["model"] == "mock-1"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/pytest tests/session/test_request_header.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'minion_agent.session.request_header'`

- [ ] **Step 3: Write the implementation**

Create `src/minion_agent/session/request_header.py`:

```python
"""Request headers as compositions of content-addressed components.

    Reconstruct request state from content-addressed components, never from
    repeated monolithic snapshots.  — design spec section 5

Component *names* are open: an application composes whatever sections it has.
The mechanism is not: every component is stored by hash, the header logs only
references, and reconstruction resolves them.

`assemble_system` is the canonical join. Dispatch and reconstruction must both
use it, or "the model saw what the log says" degrades to "the header we
recorded matches what we recorded".
"""

from __future__ import annotations

from .artifacts import ArtifactStore
from .events import EventKind, SessionEvent
from .log import SessionLog


def assemble_system(components: dict[str, str]) -> str:
    """Join components into the system prompt actually dispatched.

    Sorted by component name so the result depends on content alone, never on
    the order a caller happened to build the mapping.
    """
    return "\n\n".join(components[name] for name in sorted(components))


def record_header(
    log: SessionLog,
    store: ArtifactStore,
    components: dict[str, str],
    model: str,
) -> SessionEvent:
    """Store each component by hash and log the composition."""
    references = {name: store.put(text) for name, text in components.items()}
    return log.append(
        EventKind.REQUEST_HEADER, {"model": model, "components": references}
    )


def reconstruct_header(event: SessionEvent, store: ArtifactStore) -> dict[str, str]:
    """Resolve a logged header's references back to their content."""
    references: dict[str, str] = event.data["components"]
    return {
        name: store.get(ref).decode("utf-8") for name, ref in references.items()
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/pytest tests/session/test_request_header.py -v`
Expected: PASS — six tests.

- [ ] **Step 5: Commit**

```bash
git add src/minion_agent/session/request_header.py tests/session/test_request_header.py
git commit -m "feat: add content-addressed request header composition"
```

---

## Task 11: Reset

**Files:**
- Create: `src/minion_agent/session/operations.py`
- Modify: `src/minion_agent/session/derive.py`
- Test: `tests/session/test_reset.py`

**Interfaces:**
- Consumes: `log`, `events`, `derive`.
- Produces:
  - `def reset(log: SessionLog) -> SessionEvent` — appends `SESSION_RESET`.
  - `derive_messages` now excludes every surface entry at or before the latest reset.
- Semantics (§5): session identity is **preserved**; history remains readable for search and audit; only derivation changes.

- [ ] **Step 1: Write the failing test**

Create `tests/session/test_reset.py`:

```python
"""Reset changes derivation without changing identity or deleting history."""

from minion_agent.llm.content import TextBlock
from minion_agent.llm.messages import UserMessage, text_of
from minion_agent.session.derive import derive_messages, encode_message
from minion_agent.session.events import EventKind
from minion_agent.session.log import SessionLog
from minion_agent.session.operations import reset


def _say(log: SessionLog, text: str) -> None:
    message = UserMessage(content=(TextBlock(text=text),), timestamp=1)
    log.append(EventKind.USER_MESSAGE, {"message": encode_message(message)})


def test_reset_excludes_prior_surface_from_derivation() -> None:
    log = SessionLog("s1")
    _say(log, "before")
    reset(log)
    _say(log, "after")

    assert [text_of(m) for m in derive_messages(log)] == ["after"]


def test_reset_preserves_session_identity() -> None:
    """A session id is a durable external handle; clearing history must not
    invalidate the bindings an application holds against it."""
    log = SessionLog("s1")
    _say(log, "before")

    reset(log)

    assert log.session_id == "s1"


def test_reset_does_not_delete_history() -> None:
    log = SessionLog("s1")
    _say(log, "before")
    reset(log)

    assert len(log) == 2
    assert log.events[0].kind is EventKind.USER_MESSAGE


def test_a_second_reset_supersedes_the_first() -> None:
    log = SessionLog("s1")
    _say(log, "one")
    reset(log)
    _say(log, "two")
    reset(log)
    _say(log, "three")

    assert [text_of(m) for m in derive_messages(log)] == ["three"]


def test_reset_on_an_empty_log_is_harmless() -> None:
    log = SessionLog("s1")

    reset(log)
    _say(log, "after")

    assert [text_of(m) for m in derive_messages(log)] == ["after"]


def test_reset_appends_a_reset_event() -> None:
    log = SessionLog("s1")

    event = reset(log)

    assert event.kind is EventKind.SESSION_RESET
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/pytest tests/session/test_reset.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'minion_agent.session.operations'`

- [ ] **Step 3: Write the operations module**

Create `src/minion_agent/session/operations.py`:

```python
"""Session operations, defined as log events rather than mutations.

Under an append-only log none of these can be a method that edits history.
Each appends an event, and derivation reads that event — which is why the
effect on derivation is stated here alongside the operation.
"""

from __future__ import annotations

from .events import EventKind, SessionEvent
from .log import SessionLog


def reset(log: SessionLog) -> SessionEvent:
    """Exclude everything so far from future derivation.

    Session identity is preserved: a session id is a durable external handle
    that applications bind conversations to, so "start over" is a derivation
    change rather than a new conversation. History remains fully readable for
    search and audit.
    """
    return log.append(EventKind.SESSION_RESET, {})
```

- [ ] **Step 4: Teach derivation about reset**

In `src/minion_agent/session/derive.py`, replace `derive_messages` with:

```python
def effective_surface(log: SessionLog) -> tuple[SessionEvent, ...]:
    """The surface entries that still participate in derivation.

    A reset excludes everything at or before it; the latest one wins.

    Public because `operations.py` needs it to record what a compaction
    supersedes — a private cross-module import would be worse than a named
    seam.
    """
    from .events import EventKind

    reset_seq = max(
        (event.seq for event in log.events if event.kind is EventKind.SESSION_RESET),
        default=0,
    )
    return tuple(event for event in log.surface() if event.seq > reset_seq)


def derive_messages(log: SessionLog) -> tuple[Message, ...]:
    """Project `log`'s effective surface into model history."""
    return messages_from(effective_surface(log))
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/Scripts/pytest tests/session/ -v`
Expected: PASS — every session test, including the earlier derivation suite unchanged.

- [ ] **Step 6: Commit**

```bash
git add src/minion_agent/session tests/session/test_reset.py
git commit -m "feat: add session reset with append-only derivation semantics"
```

---

## Task 12: Compaction mechanics

Compaction *policy* — when to compact, and where to cut — is Plan 4's business.
This task is the mechanism: the event, and its effect on derivation.

**Files:**
- Modify: `src/minion_agent/session/operations.py`
- Modify: `src/minion_agent/session/derive.py`
- Test: `tests/session/test_compaction.py`

**Interfaces:**
- Consumes: `log`, `events`, `derive`.
- Produces:
  - `def compact(log, summary: str, keep: int) -> SessionEvent` — appends `COMPACTION` recording the superseded surface range, the summary, and the retained-tail provenance (the seqs kept).
  - Derivation replaces the superseded span with a synthetic user message carrying the summary, then the retained tail.
- The critical invariant: **the projection must never emit both an original entry and a copy carried forward in a retained tail.**

- [ ] **Step 1: Write the failing test**

Create `tests/session/test_compaction.py`:

```python
"""Compaction replaces a surface span in derivation without deleting anything."""

from minion_agent.llm.content import TextBlock
from minion_agent.llm.messages import UserMessage, text_of
from minion_agent.session.derive import derive_messages, encode_message
from minion_agent.session.events import EventKind
from minion_agent.session.log import SessionLog
from minion_agent.session.operations import compact, reset


def _say(log: SessionLog, text: str) -> None:
    message = UserMessage(content=(TextBlock(text=text),), timestamp=1)
    log.append(EventKind.USER_MESSAGE, {"message": encode_message(message)})


def _texts(log: SessionLog) -> list[str]:
    return [text_of(message) for message in derive_messages(log)]


def test_compaction_replaces_the_superseded_span_with_a_summary() -> None:
    log = SessionLog("s1")
    for text in ("one", "two", "three", "four"):
        _say(log, text)

    compact(log, summary="talked about numbers", keep=1)

    assert _texts(log) == ["talked about numbers", "four"]


def test_nothing_is_double_projected() -> None:
    """The retained tail is carried forward by reference, never duplicated —
    the failure mode provenance exists to prevent."""
    log = SessionLog("s1")
    for text in ("one", "two", "three"):
        _say(log, text)

    compact(log, summary="summary", keep=2)

    derived = _texts(log)

    assert derived == ["summary", "two", "three"]
    assert derived.count("two") == 1


def test_keeping_nothing_leaves_only_the_summary() -> None:
    log = SessionLog("s1")
    _say(log, "one")
    _say(log, "two")

    compact(log, summary="all of it", keep=0)

    assert _texts(log) == ["all of it"]


def test_messages_after_compaction_append_normally() -> None:
    log = SessionLog("s1")
    _say(log, "one")
    compact(log, summary="summary", keep=0)
    _say(log, "after")

    assert _texts(log) == ["summary", "after"]


def test_repeated_compaction_supersedes_the_earlier_summary() -> None:
    log = SessionLog("s1")
    _say(log, "one")
    _say(log, "two")
    compact(log, summary="first summary", keep=0)
    _say(log, "three")

    compact(log, summary="second summary", keep=1)

    assert _texts(log) == ["second summary", "three"]


def test_compaction_deletes_nothing_from_the_log() -> None:
    log = SessionLog("s1")
    _say(log, "one")
    _say(log, "two")

    compact(log, summary="summary", keep=0)

    assert len(log) == 3
    assert [event.kind for event in log.events][:2] == [
        EventKind.USER_MESSAGE,
        EventKind.USER_MESSAGE,
    ]


def test_reset_after_compaction_clears_the_summary_too() -> None:
    log = SessionLog("s1")
    _say(log, "one")
    compact(log, summary="summary", keep=0)
    reset(log)
    _say(log, "after")

    assert _texts(log) == ["after"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/pytest tests/session/test_compaction.py -v`
Expected: FAIL — `ImportError: cannot import name 'compact'`

- [ ] **Step 3: Add the operation**

Append to `src/minion_agent/session/operations.py`:

```python
def compact(log: SessionLog, summary: str, keep: int) -> SessionEvent:
    """Replace the current surface with a summary plus the last `keep` entries.

    Records three things, because repeated and nested compaction otherwise has
    no deterministic projection: the superseded range, the replacement content,
    and the retained tail's provenance — the exact seqs carried forward.

    Provenance is what prevents double projection. The retained entries are
    named by sequence rather than copied, so derivation can never emit both an
    original and a copy of it.
    """
    from .derive import effective_surface

    surface = effective_surface(log)
    retained = surface[len(surface) - keep :] if keep else ()
    return log.append(
        EventKind.COMPACTION,
        {
            "summary": summary,
            "superseded_through": surface[-1].seq if surface else 0,
            "retained": [event.seq for event in retained],
        },
    )
```

- [ ] **Step 4: Teach derivation about compaction**

In `derive.py`, replace `effective_surface` and `derive_messages`:

```python
def _latest(log: SessionLog, kind: EventKind) -> SessionEvent | None:
    for event in reversed(log.events):
        if event.kind is kind:
            return event
    return None


def effective_surface(log: SessionLog) -> tuple[SessionEvent, ...]:
    """Surface entries that still participate, ignoring compaction."""
    reset_event = _latest(log, EventKind.SESSION_RESET)
    floor = reset_event.seq if reset_event is not None else 0
    return tuple(event for event in log.surface() if event.seq > floor)


def derive_messages(log: SessionLog) -> tuple[Message, ...]:
    """Project `log` into model history, applying reset and compaction."""
    surface = effective_surface(log)

    compaction = _latest(log, EventKind.COMPACTION)
    reset_event = _latest(log, EventKind.SESSION_RESET)
    if compaction is not None and (
        reset_event is None or compaction.seq > reset_event.seq
    ):
        superseded = compaction.data["superseded_through"]
        retained = set(compaction.data["retained"])
        summary = UserMessage(
            content=(TextBlock(text=compaction.data["summary"]),),
            timestamp=0,
        )
        kept = tuple(
            event
            for event in surface
            if event.seq > superseded or event.seq in retained
        )
        return (summary, *messages_from(kept))

    return messages_from(surface)
```

Add `EventKind` and `TextBlock` to `derive.py`'s imports.

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/Scripts/pytest tests/session/ -v`
Expected: PASS — every session test.

- [ ] **Step 6: Commit**

```bash
git add src/minion_agent/session tests/session/test_compaction.py
git commit -m "feat: add compaction mechanics with retained-tail provenance"
```

---

## Task 13: Fork

**Files:**
- Modify: `src/minion_agent/session/operations.py`
- Modify: `src/minion_agent/session/derive.py`
- Test: `tests/session/test_fork.py`

**Interfaces:**
- Consumes: `log`, `events`, `derive`.
- Produces:
  - `def fork(source: SessionLog, session_id: str, at: int | None = None) -> SessionLog` — returns a new log whose first event is `SESSION_FORKED` recording `source` and the boundary seq. `at=None` forks at the source's head.
  - Derivation on a fork walks its ancestry: the source's effective surface up to the boundary, then the fork's own.
  - Forks **reference** rather than copy, so there is one place for one truth.
- Note: this requires `SessionLog` to hold an optional ancestor. Add `ancestor: SessionLog | None` and `boundary: int` to the log rather than threading them through every derive call.

- [ ] **Step 1: Write the failing test**

Create `tests/session/test_fork.py`:

```python
"""Forks reference their ancestor rather than copying it."""

from minion_agent.llm.content import TextBlock
from minion_agent.llm.messages import UserMessage, text_of
from minion_agent.session.derive import derive_messages, encode_message
from minion_agent.session.events import EventKind
from minion_agent.session.log import SessionLog
from minion_agent.session.operations import compact, fork, reset


def _say(log: SessionLog, text: str) -> None:
    message = UserMessage(content=(TextBlock(text=text),), timestamp=1)
    log.append(EventKind.USER_MESSAGE, {"message": encode_message(message)})


def _texts(log: SessionLog) -> list[str]:
    return [text_of(message) for message in derive_messages(log)]


def test_a_fork_inherits_its_ancestors_history() -> None:
    source = SessionLog("s1")
    _say(source, "shared")

    child = fork(source, "s2")

    assert _texts(child) == ["shared"]


def test_a_fork_has_its_own_identity() -> None:
    source = SessionLog("s1")

    child = fork(source, "s2")

    assert (source.session_id, child.session_id) == ("s1", "s2")


def test_writes_to_a_fork_do_not_reach_its_ancestor() -> None:
    source = SessionLog("s1")
    _say(source, "shared")

    child = fork(source, "s2")
    _say(child, "child only")

    assert _texts(source) == ["shared"]
    assert _texts(child) == ["shared", "child only"]


def test_writes_to_the_ancestor_after_a_fork_do_not_reach_the_child() -> None:
    """The boundary is fixed at fork time, not a live view."""
    source = SessionLog("s1")
    _say(source, "shared")
    child = fork(source, "s2")

    _say(source, "parent only")

    assert _texts(child) == ["shared"]


def test_forking_at_an_explicit_boundary_truncates_history() -> None:
    source = SessionLog("s1")
    _say(source, "first")
    boundary = len(source)
    _say(source, "second")

    child = fork(source, "s2", at=boundary)

    assert _texts(child) == ["first"]


def test_a_fork_records_its_ancestry() -> None:
    source = SessionLog("s1")
    _say(source, "shared")

    child = fork(source, "s2")

    assert child.events[0].kind is EventKind.SESSION_FORKED
    assert child.events[0].data["source"] == "s1"


def test_a_fork_copies_nothing() -> None:
    """One place for one truth: the child holds only its own events."""
    source = SessionLog("s1")
    for text in ("a", "b", "c"):
        _say(source, text)

    child = fork(source, "s2")

    assert len(child) == 1


def test_compaction_inside_a_fork_does_not_affect_the_ancestor() -> None:
    source = SessionLog("s1")
    _say(source, "one")
    _say(source, "two")
    child = fork(source, "s2")

    compact(child, summary="summarised", keep=0)

    assert _texts(source) == ["one", "two"]
    assert _texts(child) == ["summarised"]


def test_reset_inside_a_fork_clears_inherited_history() -> None:
    source = SessionLog("s1")
    _say(source, "inherited")
    child = fork(source, "s2")

    reset(child)
    _say(child, "fresh")

    assert _texts(child) == ["fresh"]
    assert _texts(source) == ["inherited"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/pytest tests/session/test_fork.py -v`
Expected: FAIL — `ImportError: cannot import name 'fork'`

- [ ] **Step 3: Give the log an ancestor**

In `src/minion_agent/session/log.py`, extend `__init__` and add two attributes:

```python
    def __init__(
        self,
        session_id: str,
        ancestor: SessionLog | None = None,
        boundary: int = 0,
    ) -> None:
        self.session_id = session_id
        self.ancestor = ancestor
        """The log this one forked from, or None for a root session."""
        self.boundary = boundary
        """The ancestor sequence number this fork branched at."""
        self._events: list[SessionEvent] = []
```

- [ ] **Step 4: Add the operation**

Append to `operations.py`:

```python
def fork(source: SessionLog, session_id: str, at: int | None = None) -> SessionLog:
    """Branch a new session from `source` at `at` (default: its head).

    The fork *references* its ancestor rather than copying it, for the same
    reason the log never deletes: copying would duplicate model-visible content
    and create two places for one truth. Derivation walks the ancestry chain.

    The boundary is fixed here, so later writes to either side stay private to
    that side.
    """
    boundary = len(source) if at is None else at
    child = SessionLog(session_id, ancestor=source, boundary=boundary)
    child.append(
        EventKind.SESSION_FORKED,
        {"source": source.session_id, "boundary": boundary},
    )
    return child
```

- [ ] **Step 5: Teach derivation to walk ancestry**

In `derive.py`, add an inherited-surface helper and use it in `effective_surface`:

```python
def _inherited_surface(log: SessionLog) -> tuple[SessionEvent, ...]:
    """The ancestor's effective surface up to this fork's boundary."""
    if log.ancestor is None:
        return ()
    inherited = effective_surface(log.ancestor)
    return tuple(event for event in inherited if event.seq <= log.boundary)
```

and change `effective_surface`'s return to prepend it:

```python
def effective_surface(log: SessionLog) -> tuple[SessionEvent, ...]:
    """Surface entries that still participate, ignoring compaction.

    A fork's own reset floors only its own events; inherited history is
    excluded by the reset too, because a reset means "start over" for the
    whole conversation this log represents.
    """
    own = tuple(event for event in log.surface() if event.seq > _reset_floor(log))
    if _latest(log, EventKind.SESSION_RESET) is not None:
        return own
    return (*_inherited_surface(log), *own)


def _reset_floor(log: SessionLog) -> int:
    reset_event = _latest(log, EventKind.SESSION_RESET)
    return reset_event.seq if reset_event is not None else 0
```

Note the subtlety this pins: a fork's sequence numbers restart at 1, so
inherited and own events can share seq values. Compaction's `superseded_through`
and `retained` therefore apply to a fork's *own* events only — which is exactly
what `test_compaction_inside_a_fork_does_not_affect_the_ancestor` checks.

- [ ] **Step 6: Run tests to verify they pass**

Run: `.venv/Scripts/pytest tests/session/ -v`
Expected: PASS — every session test.

If compaction inside a fork misbehaves, the cause is almost certainly the
shared-sequence subtlety above: compare against inherited entries by identity
rather than by seq.

- [ ] **Step 7: Commit**

```bash
git add src/minion_agent/session tests/session/test_fork.py
git commit -m "feat: add session fork with referenced ancestry"
```

---

## Task 14: The session conformance runner and scenarios

**Files:**
- Create: `tests/conformance/session_runner.py`
- Create: `tests/conformance/test_session_conformance.py`
- Create: `conformance/session/*.yaml` (four scenarios)
- Modify: `tests/conformance/test_schema_validation.py`

**Interfaces:**
- Consumes: `SessionLog`, `derive_messages`, the session operations.
- Produces:
  - `async def run_session_scenario(document) -> list[dict[str, str]]` — applies steps and returns the derived messages as `{role, text}` pairs.
  - Four executable cases: `fork-ancestry-derivation`, `reset-excludes-prior-surface`, `compact-now-then-derive`, `compaction-repeated-and-nested`.
  - `session` leaves `UNPOPULATED` in the schema-validation test.

- [ ] **Step 1: Write the runner**

Create `tests/conformance/session_runner.py`:

```python
"""Executes session conformance scenarios.

Log operations in, derived messages out, with no model in play — which is what
makes derivation after fork, reset, and repeated compaction assertable without
a provider.
"""

from __future__ import annotations

from typing import Any

from minion_agent.llm.content import TextBlock
from minion_agent.llm.messages import (
    AssistantMessage,
    Message,
    StopReason,
    ToolResultMessage,
    Usage,
    UserMessage,
    text_of,
)
from minion_agent.session.derive import derive_messages, encode_message
from minion_agent.session.events import EventKind
from minion_agent.session.log import SessionLog
from minion_agent.session.operations import compact, fork, reset

_KIND = {
    "user": EventKind.USER_MESSAGE,
    "assistant": EventKind.ASSISTANT_MESSAGE,
    "tool_result": EventKind.TOOL_RESULT,
}


def _message(role: str, text: str) -> Message:
    content = (TextBlock(text=text),)
    if role == "user":
        return UserMessage(content=content, timestamp=1)
    if role == "assistant":
        return AssistantMessage(
            content=content,
            stop_reason=StopReason.STOP,
            usage=Usage(),
            model="mock-1",
            provider="mock",
            timestamp=1,
        )
    return ToolResultMessage(tool_call_id="t1", content=content, timestamp=1)


def _role_of(message: Message) -> str:
    return {
        UserMessage: "user",
        AssistantMessage: "assistant",
        ToolResultMessage: "tool_result",
    }[type(message)]


def run_session_scenario(document: dict[str, Any]) -> list[dict[str, str]]:
    """Apply the scenario's steps and return the derived messages."""
    log = SessionLog("scenario")
    forks = 0

    for step in document["steps"]:
        if "append" in step:
            spec = step["append"]
            log.append(
                _KIND[spec["role"]],
                {"message": encode_message(_message(spec["role"], spec["text"]))},
            )
        elif "fork" in step:
            forks += 1
            log = fork(log, f"fork-{forks}", at=step["fork"].get("at"))
        elif "reset" in step:
            reset(log)
        elif "compact" in step:
            spec = step["compact"]
            compact(log, summary=spec["summary"], keep=spec.get("keep", 0))
        # "derive" is a no-op marker: derivation happens once, at the end.

    return [
        {"role": _role_of(message), "text": text_of(message)}
        for message in derive_messages(log)
    ]
```

- [ ] **Step 2: Write the test**

Create `tests/conformance/test_session_conformance.py`:

```python
"""Execute every conformance/session/*.yaml scenario."""

from pathlib import Path

import pytest
import yaml

from .session_runner import run_session_scenario

SCENARIOS = sorted(
    (Path(__file__).resolve().parents[2] / "conformance" / "session").glob("*.yaml")
)


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda path: path.stem)
def test_session_scenario(scenario: Path) -> None:
    document = yaml.safe_load(scenario.read_text(encoding="utf-8"))

    assert run_session_scenario(document) == document["expect_messages"]
```

- [ ] **Step 3: Write the scenarios**

Create `conformance/session/reset-excludes-prior-surface.yaml`:

```yaml
name: reset excludes prior surface from derivation
description: >
  Reset is a derivation change, not a deletion. Session identity is preserved
  and history stays readable; only what the model sees changes.
steps:
  - append: { role: user, text: before }
  - append: { role: assistant, text: answered }
  - reset: {}
  - append: { role: user, text: after }
  - derive: {}
expect_messages:
  - { role: user, text: after }
```

Create `conformance/session/compact-now-then-derive.yaml`:

```yaml
name: compaction replaces the superseded span and retains a tail
description: >
  Derivation yields the summary followed by exactly the retained entries.
  Nothing is emitted twice — the retained tail is carried forward by
  provenance rather than copied.
steps:
  - append: { role: user, text: one }
  - append: { role: assistant, text: two }
  - append: { role: user, text: three }
  - compact: { summary: discussed numbers, keep: 1 }
  - derive: {}
expect_messages:
  - { role: user, text: discussed numbers }
  - { role: user, text: three }
```

Create `conformance/session/compaction-repeated-and-nested.yaml`:

```yaml
name: repeated compaction supersedes the earlier summary
description: >
  The second compaction supersedes the first, so derivation never accumulates
  a chain of summaries. This is where independent implementations diverge
  unnoticed if replacement semantics are left implicit.
steps:
  - append: { role: user, text: one }
  - append: { role: user, text: two }
  - compact: { summary: first summary, keep: 0 }
  - append: { role: user, text: three }
  - compact: { summary: second summary, keep: 1 }
  - derive: {}
expect_messages:
  - { role: user, text: second summary }
  - { role: user, text: three }
```

Create `conformance/session/fork-ancestry-derivation.yaml`:

```yaml
name: a fork derives its ancestor's history then its own
description: >
  Forks reference rather than copy, so a fork's derivation walks its ancestry
  up to the boundary fixed at fork time, then its own surface.
steps:
  - append: { role: user, text: shared }
  - append: { role: assistant, text: shared reply }
  - fork: {}
  - append: { role: user, text: child only }
  - derive: {}
expect_messages:
  - { role: user, text: shared }
  - { role: assistant, text: shared reply }
  - { role: user, text: child only }
```

- [ ] **Step 4: Populate the session family in schema validation**

In `tests/conformance/test_schema_validation.py`, change `UNPOPULATED` to
`{"agent"}` so `session` is now required to have scenarios.

- [ ] **Step 5: Run the conformance suite**

Run: `.venv/Scripts/pytest tests/conformance -v`
Expected: PASS — seven runtime scenarios, four session scenarios, and schema
validation across all three families.

- [ ] **Step 6: Commit**

```bash
git add conformance/session tests/conformance
git commit -m "feat: add session conformance runner and derivation scenarios"
```

---

## Task 15: Telemetry spans and the sanitize boundary

**Files:**
- Create: `src/minion_agent/telemetry/__init__.py`
- Create: `src/minion_agent/telemetry/spans.py`
- Create: `src/minion_agent/telemetry/sanitize.py`
- Test: `tests/telemetry/test_sanitize.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `class SpanKind(StrEnum)`: `TURN`, `STEP`, `PROVIDER_REQUEST`, `TOOL_EXECUTION`
  - `@dataclass(frozen=True) class Span` with `kind`, `name: str`, `attributes: dict[str, Any]`, `duration_ms: int | None = None`, `error: str | None = None`
  - `class Sanitizer` with `add_secret(value: str)`, `remove_secret(value: str)`, `scrub(span: Span) -> Span`
  - Scrubbing is **known-value**: it masks configured secrets wherever they appear, including inside attribute values a caller did not originate.

- [ ] **Step 1: Write the failing test**

Create `tests/telemetry/test_sanitize.py`:

```python
"""Redaction is a boundary, not a listener — it runs before any sink sees a span."""

from minion_agent.telemetry.sanitize import REDACTED, Sanitizer
from minion_agent.telemetry.spans import Span, SpanKind


def _span(**attributes: object) -> Span:
    return Span(kind=SpanKind.PROVIDER_REQUEST, name="request", attributes=dict(attributes))


def test_a_configured_secret_is_masked() -> None:
    sanitizer = Sanitizer()
    sanitizer.add_secret("sk-abc123")

    scrubbed = sanitizer.scrub(_span(authorization="Bearer sk-abc123"))

    assert "sk-abc123" not in str(scrubbed.attributes)
    assert REDACTED in scrubbed.attributes["authorization"]


def test_a_secret_is_masked_wherever_it_appears() -> None:
    """Prompt content may carry a secret the runtime never issued."""
    sanitizer = Sanitizer()
    sanitizer.add_secret("hunter2")

    scrubbed = sanitizer.scrub(_span(prompt="the user pasted hunter2 into a note"))

    assert "hunter2" not in scrubbed.attributes["prompt"]


def test_nested_attribute_values_are_scrubbed() -> None:
    sanitizer = Sanitizer()
    sanitizer.add_secret("sk-abc123")

    scrubbed = sanitizer.scrub(_span(headers={"auth": ["Bearer sk-abc123"]}))

    assert "sk-abc123" not in str(scrubbed.attributes)


def test_non_secret_content_is_untouched() -> None:
    sanitizer = Sanitizer()
    sanitizer.add_secret("sk-abc123")

    scrubbed = sanitizer.scrub(_span(model="mock-1", tokens=42))

    assert scrubbed.attributes == {"model": "mock-1", "tokens": 42}


def test_removing_a_secret_stops_masking_it() -> None:
    sanitizer = Sanitizer()
    sanitizer.add_secret("sk-abc123")
    sanitizer.remove_secret("sk-abc123")

    scrubbed = sanitizer.scrub(_span(authorization="Bearer sk-abc123"))

    assert scrubbed.attributes["authorization"] == "Bearer sk-abc123"


def test_empty_secrets_are_ignored() -> None:
    """An empty string is a substring of everything; masking it would destroy
    every attribute."""
    sanitizer = Sanitizer()
    sanitizer.add_secret("")

    scrubbed = sanitizer.scrub(_span(model="mock-1"))

    assert scrubbed.attributes["model"] == "mock-1"


def test_the_error_field_is_scrubbed_too() -> None:
    sanitizer = Sanitizer()
    sanitizer.add_secret("sk-abc123")
    span = Span(
        kind=SpanKind.PROVIDER_REQUEST,
        name="request",
        attributes={},
        error="auth failed for sk-abc123",
    )

    assert "sk-abc123" not in (sanitizer.scrub(span).error or "")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/pytest tests/telemetry/test_sanitize.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'minion_agent.telemetry'`

- [ ] **Step 3: Write the span vocabulary**

Create `src/minion_agent/telemetry/__init__.py` with a docstring, and
`src/minion_agent/telemetry/spans.py`:

```python
"""The typed span vocabulary.

Covers the operations the runtime already owns. The vocabulary is
language-neutral, so a second implementation emits the same spans.

Telemetry is an observational projection, never a source of truth: the session
log is semantic truth, runtime events are the extension surface, and no
invariant or conformance case may depend on telemetry contents.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class SpanKind(StrEnum):
    """The operations telemetry describes."""

    TURN = "turn"
    STEP = "step"
    PROVIDER_REQUEST = "provider_request"
    TOOL_EXECUTION = "tool_execution"


@dataclass(frozen=True, slots=True)
class Span:
    """One completed operation."""

    kind: SpanKind
    name: str
    attributes: dict[str, Any] = field(default_factory=dict)
    duration_ms: int | None = None
    error: str | None = None
```

- [ ] **Step 4: Write the sanitizer**

Create `src/minion_agent/telemetry/sanitize.py`:

```python
"""The mandatory redaction boundary.

Ordering is the whole point (design spec section 7):

    core / provider data
       -> sanitize + redact      <- single mandatory boundary
       -> safe structured telemetry
       -> sinks

If redaction were a listener among listeners, a sink registered earlier would
observe raw secrets and the guarantee would depend silently on registration
order.

Redaction is known-value: the runtime scrubs credentials it has been told
about, wherever they appear — including inside prompt content, which may carry
secrets the runtime never issued. It cannot catch an arbitrary string nothing
has declared to be a secret.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from .spans import Span

REDACTED = "[redacted]"


class Sanitizer:
    """Masks configured secret values anywhere they appear in a span."""

    def __init__(self) -> None:
        self._secrets: set[str] = set()

    def add_secret(self, value: str) -> None:
        """Declare a value to be masked. Empty strings are ignored."""
        if value:
            self._secrets.add(value)

    def remove_secret(self, value: str) -> None:
        """Stop masking `value`."""
        self._secrets.discard(value)

    def _scrub_text(self, text: str) -> str:
        for secret in self._secrets:
            text = text.replace(secret, REDACTED)
        return text

    def _scrub_value(self, value: Any) -> Any:
        if isinstance(value, str):
            return self._scrub_text(value)
        if isinstance(value, dict):
            return {key: self._scrub_value(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._scrub_value(item) for item in value]
        if isinstance(value, tuple):
            return tuple(self._scrub_value(item) for item in value)
        return value

    def scrub(self, span: Span) -> Span:
        """Return `span` with every declared secret masked."""
        if not self._secrets:
            return span
        return replace(
            span,
            attributes=self._scrub_value(span.attributes),
            error=self._scrub_text(span.error) if span.error is not None else None,
        )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/Scripts/pytest tests/telemetry/test_sanitize.py -v`
Expected: PASS — seven tests.

- [ ] **Step 6: Commit**

```bash
git add src/minion_agent/telemetry tests/telemetry
git commit -m "feat: add telemetry spans and the mandatory sanitize boundary"
```

---

## Task 16: The telemetry service

**Files:**
- Create: `src/minion_agent/telemetry/service.py`
- Test: `tests/telemetry/test_service.py`

**Interfaces:**
- Consumes: `spans`, `sanitize`, runtime `Context`.
- Produces:
  - `class Sink(Protocol)` with `def emit(self, span: Span) -> None`
  - `class RecordingSink` with `spans: list[Span]` — the default, and what tests assert against
  - `class TelemetryService` with `__service_name__ = "telemetry"`, `sanitizer: Sanitizer`, `add_sink(sink) -> Callable[[], None]`, `emit(span) -> None`
  - `emit` scrubs **before** any sink sees the span.
  - A sink that raises must not break emission for other sinks or for the caller — telemetry is observational and never affects behavior.

- [ ] **Step 1: Write the failing test**

Create `tests/telemetry/test_service.py`:

```python
"""The service scrubs before sinks and never lets a sink affect behavior."""

from minion_agent.telemetry.sanitize import REDACTED
from minion_agent.telemetry.service import RecordingSink, TelemetryService
from minion_agent.telemetry.spans import Span, SpanKind


def _span(**attributes: object) -> Span:
    return Span(kind=SpanKind.STEP, name="step", attributes=dict(attributes))


def test_emitted_spans_reach_a_sink() -> None:
    service = TelemetryService()
    sink = RecordingSink()
    service.add_sink(sink)

    service.emit(_span(model="mock-1"))

    assert sink.spans[0].attributes["model"] == "mock-1"


def test_sinks_never_see_unscrubbed_spans() -> None:
    """The ordering guarantee: redaction is a boundary, not a listener."""
    service = TelemetryService()
    sink = RecordingSink()
    service.add_sink(sink)
    service.sanitizer.add_secret("sk-abc123")

    service.emit(_span(authorization="Bearer sk-abc123"))

    assert REDACTED in sink.spans[0].attributes["authorization"]


def test_every_sink_receives_every_span() -> None:
    service = TelemetryService()
    first, second = RecordingSink(), RecordingSink()
    service.add_sink(first)
    service.add_sink(second)

    service.emit(_span())

    assert len(first.spans) == len(second.spans) == 1


def test_removing_a_sink_stops_delivery() -> None:
    service = TelemetryService()
    sink = RecordingSink()
    remove = service.add_sink(sink)

    remove()
    service.emit(_span())

    assert sink.spans == []


def test_a_failing_sink_does_not_break_the_others() -> None:
    """Telemetry is observational: a broken sink must not change behavior."""

    class Broken:
        def emit(self, span: Span) -> None:
            raise RuntimeError("sink is down")

    service = TelemetryService()
    service.add_sink(Broken())
    healthy = RecordingSink()
    service.add_sink(healthy)

    service.emit(_span())

    assert len(healthy.spans) == 1


def test_emitting_with_no_sinks_is_harmless() -> None:
    TelemetryService().emit(_span())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/pytest tests/telemetry/test_service.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'minion_agent.telemetry.service'`

- [ ] **Step 3: Write the implementation**

Create `src/minion_agent/telemetry/service.py`:

```python
"""The `ctx.telemetry` seam.

Sinks are plugins; a deployment may mount none. Emission scrubs before any
sink runs, and a failing sink is contained — telemetry is an observational
projection, so nothing it does may change behavior.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from .sanitize import Sanitizer
from .spans import Span


class Sink(Protocol):
    """Somewhere scrubbed spans go."""

    def emit(self, span: Span) -> None: ...


class RecordingSink:
    """Keeps every span it receives. The default, and what tests assert on."""

    def __init__(self) -> None:
        self.spans: list[Span] = []

    def emit(self, span: Span) -> None:
        self.spans.append(span)


class TelemetryService:
    """Scrubs spans and fans them out to sinks."""

    __service_name__ = "telemetry"

    def __init__(self) -> None:
        self.sanitizer = Sanitizer()
        self.recording: RecordingSink | None = None
        """Set by the plugin when it mounts a default recording sink."""
        self._sinks: list[Sink] = []

    def add_sink(self, sink: Sink) -> Callable[[], None]:
        """Register `sink`; returns a handle that removes it."""
        self._sinks.append(sink)

        def remove() -> None:
            if sink in self._sinks:
                self._sinks.remove(sink)

        return remove

    def emit(self, span: Span) -> None:
        """Scrub `span`, then deliver it to every sink.

        A sink that raises is contained: the remaining sinks still receive the
        span, and the caller never learns. An observational projection must not
        be able to fail the thing it observes.
        """
        scrubbed = self.sanitizer.scrub(span)
        for sink in list(self._sinks):
            try:
                sink.emit(scrubbed)
            except Exception:  # noqa: BLE001 - telemetry must never affect behavior
                continue
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/pytest tests/telemetry/test_service.py -v`
Expected: PASS — six tests.

- [ ] **Step 5: Commit**

```bash
git add src/minion_agent/telemetry/service.py tests/telemetry/test_service.py
git commit -m "feat: add the telemetry service with contained sinks"
```

---

## Task 17: Mounting the services as plugins

Everything so far is plain Python. This task makes it a composition on the
runtime, which is the point of the architecture.

**Files:**
- Create: `src/minion_agent/llm/plugin.py`
- Create: `src/minion_agent/session/service.py`
- Create: `src/minion_agent/telemetry/plugin.py`
- Modify: the three `__init__.py` public surfaces
- Test: `tests/test_composition.py`

**Interfaces:**
- Consumes: runtime `@plugin`, `Context`; the three services.
- Produces:
  - `llm_plugin` — provides `llm`, registering nothing by default.
  - `mock_adapter_plugin` — injects `llm`, registers a `MockAdapter` as an effect, config `MockAdapterConfig(script=[])`.
  - `session_plugin` — provides `sessions`: a `SessionService` with `create(session_id) -> SessionLog`, `get(session_id)`, `fork(...)`, and a shared `ArtifactStore`.
  - `telemetry_plugin` — provides `telemetry`, with a `RecordingSink` mounted by default.
  - Withdrawing any plugin removes its service and its registrations.

- [ ] **Step 1: Write the failing test**

Create `tests/test_composition.py`:

```python
"""The services compose on the runtime as ordinary plugins."""

from minion_agent.llm.plugin import llm_plugin, mock_adapter_plugin
from minion_agent.llm.service import ModelId, Request
from minion_agent.llm.stream import collect
from minion_agent.runtime import Context, FiberState
from minion_agent.session.service import session_plugin
from minion_agent.telemetry.plugin import telemetry_plugin
from minion_agent.telemetry.spans import Span, SpanKind


async def _composed() -> Context:
    ctx = Context()
    await ctx.plugin(llm_plugin)
    await ctx.plugin(session_plugin)
    await ctx.plugin(telemetry_plugin)
    return ctx


async def test_the_services_resolve_by_name() -> None:
    ctx = await _composed()

    assert ctx.llm is not None
    assert ctx.sessions is not None
    assert ctx.telemetry is not None


async def test_an_adapter_plugin_waits_for_the_llm_service() -> None:
    """Reactive dependency, doing its job across package boundaries."""
    ctx = Context()

    adapter_fiber = await ctx.plugin(mock_adapter_plugin, {"script": []})
    assert adapter_fiber.state is FiberState.PENDING

    await ctx.plugin(llm_plugin)
    assert adapter_fiber.state is FiberState.ACTIVE


async def test_a_mounted_adapter_serves_requests() -> None:
    ctx = await _composed()
    await ctx.plugin(
        mock_adapter_plugin,
        {"script": [{"text": "hello", "stop_reason": "stop"}]},
    )

    message = await collect(
        ctx.llm.stream(Request(model=ModelId("mock", "mock-1"), system="", messages=()))
    )

    assert message.content[0].text == "hello"


async def test_unmounting_the_adapter_withdraws_its_models() -> None:
    ctx = await _composed()
    fiber = await ctx.plugin(mock_adapter_plugin, {"script": []})
    assert ctx.llm.models()

    await ctx.plugins.unmount(fiber)

    assert ctx.llm.models() == frozenset()


async def test_sessions_are_created_and_retrieved_by_id() -> None:
    ctx = await _composed()

    created = ctx.sessions.create("s1")

    assert ctx.sessions.get("s1") is created


async def test_the_session_service_shares_one_artifact_store() -> None:
    """Content addressing only pays off if the store is shared."""
    ctx = await _composed()
    ctx.sessions.create("s1")
    ctx.sessions.create("s2")

    first = ctx.sessions.artifacts.put("shared block")
    second = ctx.sessions.artifacts.put("shared block")

    assert first == second
    assert len(ctx.sessions.artifacts) == 1


async def test_telemetry_records_by_default() -> None:
    ctx = await _composed()

    ctx.telemetry.emit(Span(kind=SpanKind.STEP, name="step"))

    assert len(ctx.telemetry.recording.spans) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/pytest tests/test_composition.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'minion_agent.llm.plugin'`

- [ ] **Step 3: Write the LLM plugins**

Create `src/minion_agent/llm/plugin.py`:

```python
"""Mounting the LLM seam and adapters on the runtime."""

from __future__ import annotations

from pydantic import BaseModel

from ..runtime import Context, plugin
from .adapters.mock import MockAdapter, ScriptedResponse
from .content import TextBlock
from .messages import StopReason
from .service import LlmService


@plugin(name="llm", provides="llm")
async def llm_plugin(ctx: Context, config: None) -> None:
    """Provide the LLM seam. Adapters mount separately and register into it."""
    ctx.provide("llm", LlmService())


class ScriptedResponseConfig(BaseModel):
    """One scripted response, in the shape configuration carries."""

    text: str = ""
    stop_reason: StopReason = StopReason.STOP
    error_message: str | None = None


class MockAdapterConfig(BaseModel):
    script: list[ScriptedResponseConfig] = []


@plugin(name="llm-mock", inject=["llm"], config=MockAdapterConfig)
async def mock_adapter_plugin(ctx: Context, config: MockAdapterConfig) -> None:
    """Register a scripted adapter, withdrawn when this plugin unloads."""
    adapter = MockAdapter(
        [
            ScriptedResponse(
                content=(TextBlock(text=entry.text),) if entry.text else (),
                stop_reason=entry.stop_reason,
                error_message=entry.error_message,
            )
            for entry in config.script
        ]
    )
    ctx.effect(lambda: ctx.llm.register(adapter), "register(mock)")
```

- [ ] **Step 4: Write the session service**

Create `src/minion_agent/session/service.py`:

```python
"""The `ctx.sessions` seam."""

from __future__ import annotations

from ..runtime import Context, plugin
from .artifacts import ArtifactStore
from .log import SessionLog
from .operations import fork


class SessionService:
    """Owns every live session log and the shared artifact store."""

    __service_name__ = "sessions"

    def __init__(self) -> None:
        self.artifacts = ArtifactStore()
        """Shared across sessions: content addressing only pays off if a
        stable block is stored once for the deployment, not once per session."""
        self._logs: dict[str, SessionLog] = {}

    def create(self, session_id: str) -> SessionLog:
        """Create and register a new session log."""
        log = SessionLog(session_id)
        self._logs[session_id] = log
        return log

    def get(self, session_id: str) -> SessionLog | None:
        """The log for `session_id`, or None."""
        return self._logs.get(session_id)

    def fork(self, source_id: str, session_id: str, at: int | None = None) -> SessionLog:
        """Fork `source_id` into a new registered session."""
        source = self._logs[source_id]
        child = fork(source, session_id, at=at)
        self._logs[session_id] = child
        return child


@plugin(name="sessions", provides="sessions")
async def session_plugin(ctx: Context, config: None) -> None:
    ctx.provide("sessions", SessionService())
```

- [ ] **Step 5: Write the telemetry plugin**

Create `src/minion_agent/telemetry/plugin.py`:

```python
"""Mounting the telemetry seam on the runtime."""

from __future__ import annotations

from ..runtime import Context, plugin
from .service import RecordingSink, TelemetryService


@plugin(name="telemetry", provides="telemetry")
async def telemetry_plugin(ctx: Context, config: None) -> None:
    """Provide telemetry with a recording sink mounted.

    Recording by default keeps the seam useful in tests and development
    without a deployment having to configure anything. Production sinks land
    in a later phase.
    """
    service = TelemetryService()
    service.recording = RecordingSink()
    service.add_sink(service.recording)
    ctx.provide("telemetry", service)
```

This requires `TelemetryService.__init__` to declare
`self.recording: RecordingSink | None = None`, which Task 16 already does —
add it there rather than attaching the attribute dynamically here.

- [ ] **Step 6: Run tests to verify they pass**

Run: `.venv/Scripts/pytest tests/test_composition.py -v`
Expected: PASS — seven tests.

- [ ] **Step 7: Commit**

```bash
git add src/minion_agent tests/test_composition.py
git commit -m "feat: mount the LLM, session, and telemetry services as plugins"
```

---

## Task 18: Public surfaces, property tests, and the coverage gate

**Files:**
- Modify: `src/minion_agent/llm/__init__.py`, `session/__init__.py`, `telemetry/__init__.py`
- Modify: `pyproject.toml`
- Create: `tests/session/test_properties.py`
- Create: `tests/test_layering.py`

**Interfaces:**
- Consumes: everything.
- Produces: curated `__all__` per package; layering enforced by test; 100% coverage across all four packages.

- [ ] **Step 1: Write the layering test**

Create `tests/test_layering.py`:

```python
"""Layer purity, checked rather than assumed."""

from pathlib import Path

import minion_agent

FORBIDDEN = {
    "runtime": ("minion_agent.llm", "minion_agent.session", "minion_agent.telemetry",
                "minion_agent.agent", "minion_agent.tools"),
    "llm": ("minion_agent.session", "minion_agent.agent", "minion_agent.tools"),
    "session": ("minion_agent.agent", "minion_agent.tools"),
    "telemetry": ("minion_agent.session", "minion_agent.agent", "minion_agent.tools"),
}

ROOT = Path(minion_agent.__file__).parent


def test_no_package_imports_a_higher_layer() -> None:
    offenders: list[str] = []
    for package, forbidden in FORBIDDEN.items():
        for module in sorted((ROOT / package).rglob("*.py")):
            source = module.read_text(encoding="utf-8")
            offenders.extend(
                f"{package}/{module.name} imports {name}"
                for name in forbidden
                if name in source
            )

    assert not offenders, "; ".join(offenders)


def test_llm_does_not_know_sessions_exist() -> None:
    """Stated separately because it is the boundary most likely to erode:
    the session layer stores messages, so the pull is toward the reverse."""
    for module in sorted((ROOT / "llm").rglob("*.py")):
        assert "session" not in module.read_text(encoding="utf-8")
```

Note the `plugin.py` modules import from `..runtime`, which is *downward* and
therefore allowed; `FORBIDDEN` lists only upward dependencies.

- [ ] **Step 2: Write the property tests**

Create `tests/session/test_properties.py`:

```python
"""Properties that must hold for any sequence of session operations."""

from hypothesis import given
from hypothesis import strategies as st

from minion_agent.llm.content import TextBlock
from minion_agent.llm.messages import UserMessage, text_of
from minion_agent.session.derive import derive_messages, encode_message
from minion_agent.session.events import EventKind
from minion_agent.session.log import SessionLog
from minion_agent.session.operations import compact, fork, reset

texts = st.lists(st.text(min_size=1, max_size=6), min_size=0, max_size=20)


def _say(log: SessionLog, text: str) -> None:
    message = UserMessage(content=(TextBlock(text=text),), timestamp=1)
    log.append(EventKind.USER_MESSAGE, {"message": encode_message(message)})


@given(texts)
def test_derivation_preserves_order_and_content(items: list[str]) -> None:
    log = SessionLog("s1")
    for text in items:
        _say(log, text)

    assert [text_of(m) for m in derive_messages(log)] == items


@given(texts)
def test_reset_always_yields_an_empty_derivation(items: list[str]) -> None:
    log = SessionLog("s1")
    for text in items:
        _say(log, text)

    reset(log)

    assert derive_messages(log) == ()


@given(texts, st.integers(min_value=0, max_value=5))
def test_compaction_never_exceeds_summary_plus_keep(
    items: list[str], keep: int
) -> None:
    log = SessionLog("s1")
    for text in items:
        _say(log, text)

    compact(log, summary="s", keep=keep)

    assert len(derive_messages(log)) <= 1 + min(keep, len(items))


@given(texts)
def test_appending_never_shrinks_derivation(items: list[str]) -> None:
    log = SessionLog("s1")
    previous = 0
    for text in items:
        _say(log, text)
        current = len(derive_messages(log))
        assert current >= previous
        previous = current


@given(texts)
def test_a_fork_starts_from_its_ancestors_derivation(items: list[str]) -> None:
    source = SessionLog("s1")
    for text in items:
        _say(source, text)

    child = fork(source, "s2")

    assert derive_messages(child) == derive_messages(source)


@given(texts)
def test_the_log_never_shrinks(items: list[str]) -> None:
    """Append-only means append-only: no operation reduces the event count."""
    log = SessionLog("s1")
    sizes = [len(log)]
    for text in items:
        _say(log, text)
        sizes.append(len(log))
    reset(log)
    sizes.append(len(log))
    compact(log, summary="s", keep=0)
    sizes.append(len(log))

    assert sizes == sorted(sizes)
```

- [ ] **Step 3: Write the public surfaces**

Give each package an `__all__` re-exporting its vocabulary — `llm` exports the
content blocks, messages, stop reason, usage, stream chunks, `collect`,
`LlmService`, `ModelId`, `Request`, and the errors; `session` exports
`SessionLog`, `SessionEvent`, `EventKind`, `SURFACE_KINDS`, `derive_messages`,
`encode_message`, `decode_message`, `ArtifactStore`, the operations, and
`SessionService`; `telemetry` exports `Span`, `SpanKind`, `Sanitizer`,
`REDACTED`, `TelemetryService`, `RecordingSink`, and `Sink`.

Add a test asserting each `__all__` resolves, mirroring
`tests/runtime/test_public_surface.py`.

- [ ] **Step 4: Extend the coverage gate**

In `pyproject.toml`, extend the coverage source:

```toml
[tool.coverage.run]
source = [
    "src/minion_agent/runtime",
    "src/minion_agent/llm",
    "src/minion_agent/session",
    "src/minion_agent/telemetry",
]
```

- [ ] **Step 5: Reach 100%**

Run: `.venv/Scripts/pytest`

Expect gaps on first run — misuse guards, the `decode_message` and
`_decode_block` error branches, and adapter edges. Write tests for reachable
lines; use `# pragma: no cover` only with a written reason on the same line.

- [ ] **Step 6: Run lint and types**

Run: `.venv/Scripts/ruff check . && .venv/Scripts/ruff format --check . && .venv/Scripts/mypy`
Expected: clean.

- [ ] **Step 7: Commit and push**

```bash
git add -A
git commit -m "test: add session property tests, layering checks, and coverage gate"
git push origin main
```

---

## Definition of done

- [ ] `pytest` passes with 100% coverage of `runtime/`, `llm/`, `session/`, and `telemetry/`
- [ ] `ruff check`, `ruff format --check`, and `mypy` are clean
- [ ] Seven runtime scenarios and four session scenarios execute and pass
- [ ] All three JSON Schemas validate; `runtime/` and `session/` families are populated
- [ ] `llm/` contains no reference to sessions, agents, or tools; `session/` none to agents or tools — checked by test
- [ ] The mock adapter honours the never-raises contract, including when under-scripted
- [ ] A stable request component is stored once across many steps, verified by test
- [ ] Work is pushed to `origin/main`

## What Plan 3 picks up

The agent loop: `AgentDefinition` and `AgentInstance`, the agents registry with
owning handles, the inbox with `InputEnvelope` provenance and `Turn.causes[]`,
turn and step lifecycle, the decision events over Plan 1's waterfall contract,
`agent/status` settlement, cancellation, and the Pi event-stream projection. It
writes `conformance/agent/*.yaml` against the format fixed in Plan 1, driving
everything through the mock adapter this plan delivers.

Tool execution — the registry, batching, execution modes, streaming results,
and `terminate` folding — follows in Plan 4, with a trivial mock tool service
in Plan 3 so the loop can complete a tool round-trip before the real registry
exists.
