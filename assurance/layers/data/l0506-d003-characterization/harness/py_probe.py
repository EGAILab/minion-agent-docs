"""Certified Python's tool-result boundaries over the L0506-D003 cases (characterization only, not a canonical runner).

Seams probed, each the real project seam:
    tool return       a registered ToolDefinition whose execute returns ToolResult(content, details) or raises
    after-hook        register_after_tool_call_hook: what the hook receives; AfterToolCallOverride replacement
    execution end     the tools/execution-end event payload (pinned Pi's tool_execution_end)
    message           ToolResult.to_message() -- the agent-loop driver's own projection to ToolResultMessage
    session append    SessionLog.append(EventKind.TOOL_RESULT, {"message": encode_message(message)}) (driver.py)
    session replay    decode_message of the logged data

Python has no `undefined`: a case whose value contains one is reported as `unrepresentable`, not coerced.
Observations use the Pi probe's tagged form, so the two outputs compare directly.
"""

from __future__ import annotations

import asyncio
import json
import math
import struct
import sys
from typing import Any

from minion_agent.llm import TextBlock, ToolCallBlock
from minion_agent.runtime import Context
from minion_agent.session.derive import decode_message, encode_message
from minion_agent.session.events import EventKind
from minion_agent.session.log import SessionLog
from minion_agent.tools.decisions import AfterToolCallOverride
from minion_agent.tools.definition import ToolDefinition
from minion_agent.tools.events import TOOLS_EXECUTION_END, declare_tools_events
from minion_agent.tools.execute import execute_call, register_after_tool_call_hook
from minion_agent.tools.registry import ToolRegistry
from minion_agent.tools.result import ToolResult


class Unrepresentable(Exception):
    pass


def units(s: str) -> list[int]:
    data = s.encode("utf-16-le", "surrogatepass")
    return list(struct.unpack(f"<{len(data) // 2}H", data))


def text_of(u: list[int]) -> str:
    return struct.pack(f"<{len(u)}H", *u).decode("utf-16-le", "surrogatepass")


def number(t: str) -> float:
    return {"NaN": math.nan, "+Infinity": math.inf, "-Infinity": -math.inf, "-0": -0.0}.get(t) or float(t)


def value(t: dict[str, Any]) -> Any:
    if "u" in t:
        return text_of(t["u"])
    if "n" in t:
        return number(t["n"])
    if "a" in t:
        return [value(x) for x in t["a"]]
    if "o" in t:
        return {text_of(k): value(v) for k, v in t["o"]}
    if "undef" in t:
        raise Unrepresentable
    return t["v"]


def token(v: float | int) -> str:
    if isinstance(v, float):
        if math.isnan(v):
            return "NaN"
        if math.isinf(v):
            return "+Infinity" if v > 0 else "-Infinity"
        if v == 0 and math.copysign(1.0, v) < 0:
            return "-0"
        return repr(int(v)) if v.is_integer() and abs(v) < 1e21 else repr(v)
    return repr(v)


def obs(v: Any) -> Any:
    if isinstance(v, str):
        return {"u": units(v)}
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return {"n": token(v)}
    if isinstance(v, (list, tuple)):
        return {"a": [obs(x) for x in v]}
    if isinstance(v, dict):
        return {"o": [[units(k), obs(x)] for k, x in v.items()]}
    return {"v": v}


def text(content: Any) -> list[Any]:
    return [obs(block.text) for block in content]


async def run(case: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {"id": case["id"]}
    tool = case.get("tool", {})
    hook = case.get("hook", {"mode": "none"})
    try:
        details = value(tool["details"]) if "details" in tool else None
        replace = {k: value(v) for k, v in hook.items() if k in ("details", "text", "message")}
    except Unrepresentable:
        return {**out, "python": "unrepresentable (undefined)"}
    seen: dict[str, Any] = {}

    async def execute(tool_call_id: str, arguments: dict[str, Any]) -> ToolResult:
        if "throws" in tool:
            raise RuntimeError(text_of(tool["throws"]["u"]))
        result = ToolResult(tool_call_id=tool_call_id, tool_name="probe",
                            content=(TextBlock(text=text_of(tool["text"]["u"])),), details=details)
        seen["returned"] = result
        return result

    registry = ToolRegistry()
    registry.register(ToolDefinition(name="probe", label="probe", description="p",
                                     parameters={"type": "object", "properties": {}}, execute=execute))
    ctx = Context()
    declare_tools_events(ctx.events)
    mode = hook["mode"]
    if mode != "none":
        def after(result: ToolResult) -> AfterToolCallOverride | None:
            seen["hook"] = {"content": text(result.content), "details": obs(result.details),
                            "isError": result.is_error, "same_object_as_returned": result is seen.get("returned")}
            if mode == "observe":
                return None
            if mode == "same":
                return AfterToolCallOverride(content=result.content, details=result.details)
            if mode == "null":
                return AfterToolCallOverride(details=None)
            if mode == "throws":
                raise RuntimeError(replace["message"])
            return AfterToolCallOverride(
                content=(TextBlock(text=replace["text"]),) if "text" in replace else None,
                details=replace.get("details"))
        register_after_tool_call_hook(ctx, after)

    def on_end(call_id: str, name: str, result: ToolResult, *rest: Any) -> None:
        seen["end"] = result

    ctx.events.on(TOOLS_EXECUTION_END, on_end)
    result = await execute_call(ToolCallBlock(id="call-1", name="probe", arguments={}), registry=registry, ctx=ctx)
    end = seen["end"]
    message = result.to_message()
    try:
        log = SessionLog(session_id="s")
        event = log.append(EventKind.TOOL_RESULT, {"message": encode_message(message)})
        replayed = decode_message(event.data["message"])
        session: Any = {"content": text(replayed.content), "details": obs(replayed.details),
                        "json_dumps_details": json.dumps(event.data["message"].get("details"))}
    except Exception as error:  # noqa: BLE001
        session = f"error {type(error).__name__}: {str(error)[:120]}"
    return {**out,
            "hook": seen.get("hook"),
            "end": {"content": text(end.content), "details": obs(end.details), "isError": end.is_error,
                    "same_object_as_final": end is result},
            "message": {"content": text(message.content), "details": obs(message.details),
                        "isError": message.is_error},
            "session": session}


async def main() -> None:
    cases = json.load(open(sys.argv[1], encoding="utf-8"))
    results = [await run(c) for c in cases]
    with open(sys.argv[2], "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"python": sys.version.split()[0], "results": results}, fh, indent=1)
        fh.write("\n")
    print(len(results), "results")


asyncio.run(main())
