"""L0506-D001: certified Python Layer 06 with prepared non-finite numbers in declared vs undeclared fields."""
import asyncio
import math
from typing import Any

from minion_agent.llm import TextBlock, ToolCallBlock
from minion_agent.runtime import Context
from minion_agent.tools.definition import ToolDefinition
from minion_agent.tools.events import TOOLS_PRE_EXECUTE, declare_tools_events
from minion_agent.tools.execute import execute_call
from minion_agent.tools.registry import ToolRegistry
from minion_agent.tools.result import ToolResult

VALUES = {"+inf": math.inf, "-inf": -math.inf, "-0.0": -0.0, "nan": math.nan, "1e308": 1e308}


async def run(label: str, parameters: dict[str, Any], field: str, value: float) -> str:
    seen: list[Any] = []

    async def execute(tool_call_id: str, arguments: dict[str, Any]) -> ToolResult:
        seen.append(("execute", arguments.get(field)))
        return ToolResult(tool_call_id=tool_call_id, content=(TextBlock(text="ok"),), tool_name="t")

    definition = ToolDefinition(
        name="t", label="t", description="d", parameters=parameters, execute=execute,
        prepare_arguments=lambda args: {**args, field: value},
    )
    registry = ToolRegistry()
    registry.register(definition)
    ctx = Context()
    declare_tools_events(ctx.events)

    async def hook(call: Any, d: Any, arguments: Any, signal: Any, next_: Any) -> Any:
        seen.append(("hook", arguments.get(field)))
        return await next_()

    ctx.events.on(TOOLS_PRE_EXECUTE, hook)
    result = await execute_call(ToolCallBlock(id="c", name="t", arguments={}), registry=registry, ctx=ctx)
    first = result.content[0]
    text = first.text if isinstance(first, TextBlock) else ""
    return f"{label:40} {'error' if result.is_error else 'ok'} {text[:60]!r} {seen}"


async def main() -> None:
    declared = {"type": "object", "properties": {"limit": {"type": "number"}}, "required": ["limit"]}
    declared_int = {"type": "object", "properties": {"limit": {"type": "integer"}}, "required": ["limit"]}
    open_schema = {"type": "object", "properties": {}}
    for name, value in VALUES.items():
        print(await run(f"declared number limit={name}", declared, "limit", value))
        print(await run(f"declared integer limit={name}", declared_int, "limit", value))
        print(await run(f"undeclared extra={name}", open_schema, "extra", value))


asyncio.run(main())
