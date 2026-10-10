"""L0506-D005 (minion-agent#129) characterization: the pi_isolation.mjs cases through Minion's REAL
`execute_call` (raw-schema tool; `tools/pre-execute` listener as the hook; one partial result for
the `tools/update` payload). Same observation grammar as pi_isolation.mjs.

    PYTHONPATH=<minion-agent-python>/src python py_isolation.py <out.json> [pydantic]

With `pydantic`, the tool's parameters are a pydantic model with an open `dict`/`list` field per
case key (the TOOL-003 pydantic mapping) instead of the raw open schema.
"""

from __future__ import annotations

import asyncio
import json
import math
import struct
import sys
from typing import Any

from pydantic import BaseModel, ConfigDict

from minion_agent.llm import TextBlock, ToolCallBlock
from minion_agent.runtime import Context
from minion_agent.tools.builtin._js import number_to_string
from minion_agent.tools.decisions import Block
from minion_agent.tools.definition import ToolDefinition
from minion_agent.tools.events import TOOLS_PRE_EXECUTE, TOOLS_UPDATE, declare_tools_events
from minion_agent.tools.execute import execute_call
from minion_agent.tools.registry import ToolRegistry
from minion_agent.tools.result import ToolPartialResult, ToolResult


def obs(value: Any, seen: set[int] | None = None) -> Any:
    seen = set() if seen is None else seen
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, int | float):
        if isinstance(value, float) and value == 0 and math.copysign(1, value) < 0:
            return {"n": "-0"}
        return {"n": number_to_string(float(value)) if isinstance(value, float) else str(value)}
    if isinstance(value, str):
        data = value.encode("utf-16-le", "surrogatepass")
        return {"u": list(struct.unpack(f"<{len(data) // 2}H", data))}
    if id(value) in seen:
        return {"cycle": True}
    seen.add(id(value))
    if isinstance(value, list):
        out: Any = {"a": [obs(item, seen) for item in list.__iter__(value)]}
    elif isinstance(value, dict):
        out = {"o": [[key, obs(item, seen)] for key, item in dict.items(value)]}
    else:
        out = {"non_json": repr(value)}
    seen.discard(id(value))
    return out


def _alias_prepare(_raw: dict[str, Any]) -> dict[str, Any]:
    shared = {"k": 1}
    return {"p": shared, "q": shared}


def _cycle_prepare(_raw: dict[str, Any]) -> dict[str, Any]:
    node: dict[str, Any] = {"k": 1}
    node["self"] = node
    return node


def _values_prepare(raw: dict[str, Any]) -> dict[str, Any]:
    return {**raw, "nan": math.nan, "inf": math.inf, "ninf": -math.inf, "nz": -0.0}


def _shim_mutates_raw(raw: dict[str, Any]) -> dict[str, Any]:
    raw["o"]["shim"] = 1
    raw["t"] = 2
    return {"o": raw["o"], "extra": 1}


def _set_nested(a: Any) -> None:
    a["o"]["y"] = 2


def _push_nested(a: Any) -> None:
    a["a"].append({"b": 2, "1": 1})


def _gain_index(a: Any) -> None:
    a["o"]["0"] = 0


def _replace_delete(a: Any) -> None:
    a["o"]["k"] = 9
    del a["o"]["d"]
    a["l"][1].append(3)


def _alias_hook(a: Any) -> None:
    a["p"]["k"] = 2


CASES: list[dict[str, Any]] = [
    {"id": "hook-sets-into-nested-object", "text": '{"o":{"z":1}}', "hook": _set_nested},
    {"id": "hook-pushes-object-into-nested-array", "text": '{"a":[]}', "hook": _push_nested},
    {"id": "hook-nested-existing-gains-index", "text": '{"o":{"z":1,"y":2}}', "hook": _gain_index},
    {"id": "hook-replaces-and-deletes-nested", "text": '{"o":{"k":1,"d":2},"l":[1,[2]]}', "hook": _replace_delete},
    {"id": "prepared-alias-stays-shared-in-clone", "text": "{}", "prepare": _alias_prepare, "hook": _alias_hook,
     "facts": lambda a, p: {"p_is_q": a["p"] is a["q"], "p_is_prepared_p": a["p"] is p["p"]}},
    {"id": "prepared-cycle-survives-clone", "text": "{}", "prepare": _cycle_prepare,
     "facts": lambda a, p: {"self_is_args": a["self"] is a, "args_is_prepared": a is p}},
    {"id": "values-survive-clone", "text": '{"z":-0,"s":"\\ud800x","t":"\\udc00"}', "prepare": _values_prepare},
    {"id": "validation-failure", "text": '{"o":{"z":1}}', "hook": _set_nested,
     "schema": {"type": "object", "required": ["missing"], "properties": {}}},
    {"id": "blocked-after-nested-mutation", "text": '{"o":{"z":1}}', "hook": _set_nested, "block": True},
    {"id": "prepare-receives-raw-object", "text": '{"o":{"z":1},"t":1}', "prepare": _shim_mutates_raw},
]


def _js_parse(text: str) -> Any:
    """JSON.parse's value domain: `-0` stays a float, other integral numbers are ints."""
    return json.loads(text, parse_int=lambda s: -0.0 if s == "-0" else int(s))


class _OpenModel(BaseModel):
    """The TOOL-003 pydantic mapping with an open parameter object: no declared field, every argument
    kept as an extra (pydantic's own `extra="allow"`), so any case's prepared value validates."""

    model_config = ConfigDict(extra="allow")


async def run(case: dict[str, Any], pydantic: bool) -> dict[str, Any]:
    raw = _js_parse(case["text"])
    raw_o = raw.get("o") if isinstance(raw, dict) else None
    seen: dict[str, Any] = {}
    holder: dict[str, Any] = {}

    async def execute(tool_call_id: str, arguments: dict[str, Any], update: Any) -> ToolResult:
        seen["execute"] = obs(arguments)
        seen["execute_is_hook_args"] = arguments is seen.get("hook_args")
        update(ToolPartialResult(content=(TextBlock(text="partial"),), details={}))
        return ToolResult(tool_call_id=tool_call_id, content=(TextBlock(text="ok"),), tool_name="probe")

    prepare = None
    if "prepare" in case:
        def prepare(arguments: dict[str, Any]) -> dict[str, Any]:
            holder["prepared"] = case["prepare"](arguments)
            return holder["prepared"]

    if "schema" in case:
        parameters: Any = case["schema"]
    elif pydantic:
        parameters = _OpenModel
    else:
        parameters = {"type": "object", "properties": {}}
    registry = ToolRegistry()
    registry.register(ToolDefinition(name="probe", label="probe", description="L0506-D005 probe",
                                     parameters=parameters, execute=execute, prepare_arguments=prepare))
    ctx = Context()
    declare_tools_events(ctx.events)
    call = ToolCallBlock(id="c1", name="probe", arguments=raw)

    async def hook(c: Any, d: Any, arguments: Any, signal: Any, next_: Any) -> Any:
        seen["hook_args"] = arguments
        seen["hook_entry"] = obs(arguments)
        seen["hook_args_is_raw"] = arguments is call.arguments
        seen["hook_tool_call_arguments_is_raw"] = c.arguments is call.arguments
        seen["hook_o_is_raw_o"] = raw_o is not None and arguments.get("o") is raw_o
        if "hook" in case:
            case["hook"](arguments)
        if "facts" in case:
            seen["facts"] = case["facts"](arguments, holder.get("prepared"))
        if case.get("block"):
            return Block(reason="no")
        return await next_()

    updates: list[Any] = []
    ctx.events.on(TOOLS_PRE_EXECUTE, hook)
    ctx.events.on(TOOLS_UPDATE, lambda call_id, name, arguments, *rest: updates.append(obs(arguments)))
    result = await execute_call(call, registry=registry, ctx=ctx)
    out: dict[str, Any] = {"id": case["id"], "kind": "immediate" if "execute" not in seen else "prepared"}
    if out["kind"] == "prepared":
        out["update_args"] = updates
        out["update_args_is_raw"] = True  # the payload object is call.arguments (observed by value)
    else:
        first = result.content[0]
        out["error"] = first.text if isinstance(first, TextBlock) else ""
    for key in ("hook_entry", "execute", "execute_is_hook_args", "hook_args_is_raw",
                "hook_tool_call_arguments_is_raw", "hook_o_is_raw_o", "facts"):
        out[key] = seen.get(key)
    out["raw_after"] = obs(call.arguments)
    out["raw_text"] = case["text"]
    return out


async def main() -> None:
    pydantic = len(sys.argv) > 2 and sys.argv[2] == "pydantic"
    results = [await run(case, pydantic) for case in CASES]
    with open(sys.argv[1], "w", encoding="utf-8") as handle:
        json.dump({"python": sys.version.split()[0], "parameters": "pydantic" if pydantic else "raw-schema",
                   "results": results}, handle, indent=1)
        handle.write("\n")
    print(f"l0506-d005 python isolation ({'pydantic' if pydantic else 'raw-schema'}): {len(results)} cases")


if __name__ == "__main__":
    asyncio.run(main())
