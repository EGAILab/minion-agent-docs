"""Certified Python's raw ToolCall.arguments boundaries over the L0206 raw-boundary cases (characterization only).

Raw decode: Minion has no provider decoder yet (Layer 11); the closest certified decoder of JSON text into raw
arguments is Python's `json.loads` (what a Layer-11 provider or a JSON session import would use) -- recorded as a
REFERENCE, not as a Minion seam. The certified seams probed: ToolCallBlock construction, session append
(`SessionLog.append` + `encode_message`), replay (`decode_message` of the logged data), the `tools/execution-start`
event payload, and the no-prepare_arguments Layer-06 path (`execute_call`, pre-execute hook, execute).
"""

import asyncio
import json
import math
import struct
import sys
from typing import Any

from minion_agent.llm import TextBlock, ToolCallBlock
from minion_agent.llm.messages import AssistantMessage, StopReason, Usage
from minion_agent.runtime import Context
from minion_agent.session.derive import decode_message, encode_message
from minion_agent.session.events import EventKind
from minion_agent.session.log import SessionLog
from minion_agent.tools.definition import ToolDefinition
from minion_agent.tools.events import TOOLS_EXECUTION_START, TOOLS_PRE_EXECUTE, declare_tools_events
from minion_agent.tools.execute import execute_call
from minion_agent.tools.registry import ToolRegistry
from minion_agent.tools.result import ToolResult


def units(s: str) -> list[int]:
    data = s.encode("utf-16-le", "surrogatepass")
    return list(struct.unpack(f"<{len(data) // 2}H", data))


def token(v: Any) -> str:
    if isinstance(v, bool):
        return repr(v)
    if isinstance(v, float):
        if math.isnan(v):
            return "NaN"
        if math.isinf(v):
            return "+Infinity" if v > 0 else "-Infinity"
        if v == 0 and math.copysign(1.0, v) < 0:
            return "-0"
        return repr(v) + "(float)"
    return repr(v) + f"({type(v).__name__})"


def obs(v: Any) -> Any:
    if isinstance(v, str):
        return {"u": units(v)}
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return {"n": token(v)}
    if isinstance(v, list):
        return {"a": [obs(x) for x in v]}
    if isinstance(v, dict):
        return {"o": [[units(k), obs(x)] for k, x in v.items()]}
    return {"v": v}


async def run(case: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {"id": case["id"]}
    try:
        raw = json.loads(case["text"])
    except Exception as error:  # noqa: BLE001
        return {**out, "reference_json_loads": f"error {type(error).__name__}"}
    out["reference_json_loads"] = obs(raw)
    call = ToolCallBlock(id="call-1", name="probe", arguments=raw)
    try:
        log = SessionLog(session_id="s")
        message = AssistantMessage(content=(call,), stop_reason=StopReason.TOOL_USE, usage=Usage(), model="m", provider="p",
                                   timestamp=0)
        event = log.append(EventKind.ASSISTANT_MESSAGE, {"message": encode_message(message)})
        replayed = decode_message(event.data["message"])
        out["session_append"] = "ok"
        out["replay"] = obs(replayed.content[0].arguments)
        out["replay_json_dumps"] = json.dumps(event.data["message"]["content"][0]["arguments"], ensure_ascii=True)
    except Exception as error:  # noqa: BLE001
        out["session_append"] = f"error {type(error).__name__}: {str(error)[:120]}"
    seen: dict[str, Any] = {}

    async def execute(tool_call_id: str, arguments: dict[str, Any]) -> ToolResult:
        seen["execute"] = obs(arguments)
        return ToolResult(tool_call_id=tool_call_id, content=(TextBlock(text="ok"),), tool_name="probe")

    registry = ToolRegistry()
    registry.register(ToolDefinition(name="probe", label="probe", description="p",
                                     parameters={"type": "object", "properties": {}}, execute=execute))
    ctx = Context()
    declare_tools_events(ctx.events)

    async def hook(c: Any, d: Any, arguments: Any, signal: Any, next_: Any) -> Any:
        seen["hook"] = obs(arguments)
        return await next_()

    def on_start(call_id: str, name: str, arguments: Any, *rest: Any) -> None:
        seen["execution_start"] = obs(arguments)

    ctx.events.on(TOOLS_PRE_EXECUTE, hook)
    ctx.events.on(TOOLS_EXECUTION_START, on_start)
    result = await execute_call(call, registry=registry, ctx=ctx)
    first = result.content[0]
    out["pipeline"] = {"is_error": result.is_error, "text": first.text if isinstance(first, TextBlock) else "",
                       **seen}
    return out


async def main() -> None:
    cases = json.load(open(sys.argv[1], encoding="utf-8"))
    results = [await run(c) for c in cases]
    json.dump({"python": sys.version.split()[0], "results": results}, open(sys.argv[2], "w", encoding="utf-8"),
              indent=1)
    print(len(results), "results")


asyncio.run(main())
