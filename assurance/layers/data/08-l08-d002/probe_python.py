"""L08-D002 characterization (Python): the real AgentLoop, real Session log and artifact store, the
mock provider. For each scenario it records the exact session event-kind sequence, the provider
requests actually sent, and each header's reconstructed components, model and tool names.

Run from minion-agent-python/ with PYTHONPATH=src:tests-root: python probe_python.py <out.json>"""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Any

from minion_agent.agent import AGENT_PRE_STEP
from minion_agent.agent.events import AGENT_TRANSFORM_CONTEXT
from minion_agent.agent.decisions import Enter, Reject
from minion_agent.llm import ModelId, TextBlock, ToolCallBlock, UserMessage
from minion_agent.llm.adapters.mock import ScriptedResponse
from minion_agent.llm.errors import UnknownModelError
from minion_agent.llm.messages import StopReason
from minion_agent.session import EventKind, reconstruct_header, reconstruct_tools
from minion_agent.tools.definition import ToolDefinition
from tests.agent_loop.test_single_turn import _loop_with_adapter


def _say(text: str) -> UserMessage:
    return UserMessage(content=(TextBlock(text=text),), timestamp=1)


def _echo() -> ToolDefinition:
    return ToolDefinition(
        name="echo",
        description="echo",
        parameters={"type": "object", "properties": {}},
        execute=lambda tool_call_id, args: "ok",
        label="echo",
    )


def _done() -> ScriptedResponse:
    return ScriptedResponse((TextBlock(text="done"),), StopReason.STOP)


def _call() -> ScriptedResponse:
    return ScriptedResponse((ToolCallBlock(id="t1", name="echo", arguments={}),), StopReason.TOOL_USE)


def _error() -> ScriptedResponse:
    return ScriptedResponse((), StopReason.ERROR)


async def scenario(name: str) -> dict[str, Any]:
    responses = {
        "single-request": [_done()],
        "tool-call-two-requests": [_call(), _done()],
        "provider-error-stop": [_error()],
        "transform-context-raises": [_done()],
        "transform-context-raises-on-second": [_call(), _done()],
        "assembler-raises": [_done()],
        "pre-step-reject": [_done()],
        "per-step-override": [_done()],
        "unknown-model": [_done()],
        "aborted-during-tool": [_call(), _done()],
    }[name]
    loop, adapter = _loop_with_adapter(*responses)
    if name == "aborted-during-tool":

        def abort_then_ok(tool_call_id: str, args: Any) -> str:
            loop.instance.abort()
            return "ok"

        loop.tools.register(
            ToolDefinition(
                name="echo",
                description="echo",
                parameters={"type": "object", "properties": {}},
                execute=abort_then_ok,
                label="echo",
            )
        )
    else:
        loop.tools.register(_echo())
    escaped: str | None = None
    transform_calls = 0

    if name.startswith("transform-context-raises"):

        async def transform(instance: Any, messages: Any, signal: Any, next_: Any) -> Any:
            nonlocal transform_calls
            transform_calls += 1
            if name == "transform-context-raises" or transform_calls == 2:
                raise RuntimeError("transform failed")
            return await next_()

        loop.instance.ctx.events.on(AGENT_TRANSFORM_CONTEXT, transform)
    if name == "assembler-raises":

        def boom(base: str, tools: Any) -> str:
            raise RuntimeError("assembler failed")

        loop.prompt_assembler = boom
    if name in ("pre-step-reject", "per-step-override"):

        async def pre_step(instance: Any, reason: Any, messages: Any, next_: Any) -> Any:
            if name == "pre-step-reject":
                return Reject(reason="no")
            return Enter(messages=messages, system_override="one-off")

        loop.instance.ctx.events.on(AGENT_PRE_STEP, pre_step)
    if name == "unknown-model":
        loop.instance.model = ModelId("nobody", "nothing")
    try:
        await loop.prompt(_say("hi"))
    except UnknownModelError as error:
        escaped = f"UnknownModelError: {error}"
    events = [e.kind.value for e in loop.instance.log.events]
    headers = []
    for e in loop.instance.log.events:
        if e.kind == EventKind.REQUEST_HEADER:
            headers.append(
                {
                    "seq": loop.instance.log.events.index(e),
                    "model": e.data["model"],
                    "components": reconstruct_header(e, loop.artifacts),
                    "tools": [t.name for t in reconstruct_tools(e, loop.artifacts)],
                }
            )
    return {
        "scenario": name,
        "events": events,
        "requests_sent": len(adapter.requests),
        "request_systems": [r.system for r in adapter.requests],
        "request_tools": [[t.name for t in r.tools] for r in adapter.requests],
        "headers": headers,
        "escaped": escaped,
    }


async def main() -> None:
    names = [
        "single-request",
        "tool-call-two-requests",
        "provider-error-stop",
        "transform-context-raises",
        "transform-context-raises-on-second",
        "assembler-raises",
        "pre-step-reject",
        "per-step-override",
        "unknown-model",
        "aborted-during-tool",
    ]
    rows = [await scenario(n) for n in names]
    json.dump(rows, open(sys.argv[1], "w", encoding="utf-8"), indent=1)
    for r in rows:
        print(
            f"{r['scenario']:36} sent={r['requests_sent']} headers={len(r['headers'])}"
            f" escaped={r['escaped']} events={' '.join(r['events'])}"
        )


asyncio.run(main())
