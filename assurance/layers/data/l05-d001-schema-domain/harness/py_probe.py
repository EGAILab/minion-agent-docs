"""L05-D001: certified Python's runtime validation over the same schema-domain cases (characterization only).

Each case's schema becomes a raw JSON-Schema `ToolDefinition.parameters` dict; the instance is the raw arguments of a
tool without prepare_arguments; one call goes through the real Layer-06 `execute_call`. Observation: accept/reject.

    python py_probe.py <cases.json> <out.json>
"""

import asyncio
import json
import struct
import sys
from typing import Any

from minion_agent.llm import TextBlock, ToolCallBlock
from minion_agent.runtime import Context
from minion_agent.tools.definition import ToolDefinition
from minion_agent.tools.events import declare_tools_events
from minion_agent.tools.execute import execute_call
from minion_agent.tools.registry import ToolRegistry
from minion_agent.tools.result import ToolResult


def string(units: list[int]) -> str:
    return struct.pack(f"<{len(units)}H", *units).decode("utf-16-le", "surrogatepass")


ROLES: dict[str, Any] = {
    "properties-required": lambda s: ({"type": "object", "properties": {s: {"type": "string"}}, "required": [s]},
                                      lambda i: {i: "x"}),
    "additional-properties-false": lambda s: ({"type": "object", "properties": {s: {"type": "string"}},
                                               "additionalProperties": False}, lambda i: {i: "x"}),
    "const": lambda s: ({"type": "object", "properties": {"t": {"const": s}}}, lambda i: {"t": i}),
    "enum": lambda s: ({"type": "object", "properties": {"t": {"enum": [s]}}}, lambda i: {"t": i}),
    "pattern": lambda s: ({"type": "object", "properties": {"t": {"type": "string", "pattern": "^" + s + "$"}}},
                          lambda i: {"t": i}),
    "pattern-unanchored": lambda s: ({"type": "object", "properties": {"t": {"type": "string", "pattern": s}}},
                                     lambda i: {"t": i}),
    "pattern-properties": lambda s: ({"type": "object", "patternProperties": {"^" + s + "$": {"type": "number"}}},
                                     lambda i: {i: "x"}),
    "property-names-const": lambda s: ({"type": "object", "propertyNames": {"const": s}}, lambda i: {i: 1}),
    "dependent-required": lambda s: ({"type": "object", "dependentRequired": {s: ["a"]}}, lambda i: {i: 1}),
}


async def run(case: dict[str, Any]) -> dict[str, Any]:
    schema, instance = ROLES[case["role"]](string(case["schema_units"]))

    async def execute(tool_call_id: str, arguments: dict[str, Any]) -> ToolResult:
        return ToolResult(tool_call_id=tool_call_id, content=(TextBlock(text="ok"),), tool_name="p")

    registry = ToolRegistry()
    try:
        registry.register(ToolDefinition(name="p", label="p", description="p", parameters=schema, execute=execute))
    except Exception as error:  # noqa: BLE001
        return {"id": case["id"], "verdict": "register-error", "message": f"{type(error).__name__}: {error!r}"[:160]}
    ctx = Context()
    declare_tools_events(ctx.events)
    call = ToolCallBlock(id="c", name="p", arguments=instance(string(case["instance_units"])))
    result = await execute_call(call, registry=registry, ctx=ctx)
    first = result.content[0]
    text = first.text if isinstance(first, TextBlock) else ""
    if not result.is_error:
        return {"id": case["id"], "verdict": "accept"}
    verdict = "reject" if "invalid arguments" in text else "error"
    return {"id": case["id"], "verdict": verdict, "message": ascii(text)[:160]}


async def main() -> None:
    cases = json.load(open(sys.argv[1], encoding="utf-8"))
    results = [await run(c) for c in cases]
    json.dump({"python": sys.version.split()[0], "results": results}, open(sys.argv[2], "w", encoding="utf-8"), indent=1)
    tally: dict[str, int] = {}
    for r in results:
        tally[r["verdict"]] = tally.get(r["verdict"], 0) + 1
    print(len(results), tally)


asyncio.run(main())
