"""FS-PATH-JSSTRING (#123): certified Python's current behavior for path arguments holding unpaired UTF-16
surrogates, through the REAL built-in tools (write, edit, read, ls via execute_call over LocalFileSystem) and the
Layer-12 ctx.fs seam directly (write_file, read_text_file, list_dir, canonical_path). Characterization only.

    PYTHONPATH=<minion-agent-python>/src python py_path_probe.py <out.json>
"""

from __future__ import annotations

import asyncio
import json
import os
import struct
import sys
import tempfile
from typing import Any

from minion_agent.execution import LocalFileSystem
from minion_agent.llm import TextBlock, ToolCallBlock
from minion_agent.runtime import Context
from minion_agent.tools.builtin import create_edit_tool, create_ls_tool, create_read_tool, create_write_tool
from minion_agent.tools.events import declare_tools_events
from minion_agent.tools.execute import execute_call
from minion_agent.tools.registry import ToolRegistry


def units(s: str) -> list[int]:
    data = s.encode("utf-16-le", "surrogatepass")
    return list(struct.unpack(f"<{len(data) // 2}H", data))


def text(u: list[int]) -> str:
    return struct.pack(f"<{len(u)}H", *u).decode("utf-16-le", "surrogatepass")


NAMES = {
    "bmp": [0xE9],
    "pair": [0xD83D, 0xDE00],
    "lone-high-middle": [0x61, 0xD800, 0x62],
    "lone-low-end": [0x61, 0xDC00],
    "mixed-pair-then-lone": [0xD83D, 0xDE00, 0xD800],
}


def listing(path: str) -> Any:
    try:
        return [units(n) for n in os.listdir(path)]
    except Exception as e:  # noqa: BLE001
        return f"{type(e).__name__}"


async def tool(registry: ToolRegistry, name: str, args: dict[str, Any]) -> Any:
    ctx = Context()
    declare_tools_events(ctx.events)
    try:
        r = await execute_call(ToolCallBlock(id="c", name=name, arguments=args), registry=registry, ctx=ctx)
    except Exception as e:  # noqa: BLE001 -- an exception escaping the pipeline is itself an observation
        return {"escaped": f"{type(e).__name__}: {str(e)[:80]}"}
    first = r.content[0] if r.content else None
    t = first.text if isinstance(first, TextBlock) else ""
    return {"is_error": r.is_error, "text_has_input": None, "text_units": units(t)[:200]}


async def fs_op(coro: Any) -> Any:
    try:
        r = await coro
    except Exception as e:  # noqa: BLE001
        return {"raised": f"{type(e).__name__}: {str(e)[:80]}"}
    return {"result": type(r).__name__, "value": repr(getattr(r, "value", None))[:80],
            "error": repr(getattr(r, "error", None))[:120]}


async def main() -> None:
    out: dict[str, Any] = {"platform": sys.platform, "python": sys.version.split()[0], "results": []}
    for name, u in NAMES.items():
        root = tempfile.mkdtemp(prefix="pyfs-")
        fs = LocalFileSystem(root)
        registry = ToolRegistry()
        for create in (create_write_tool, create_edit_tool, create_read_tool, create_ls_tool):
            registry.register(create(fs))
        comp = text(u)
        rel = f"f{comp}.txt"
        res: dict[str, Any] = {"id": name, "input": units(rel)}
        res["tool_write"] = await tool(registry, "write", {"path": rel, "content": "content"})
        res["listing_after_write"] = listing(root)
        res["tool_read"] = await tool(registry, "read", {"path": rel})
        res["tool_edit"] = await tool(registry, "edit", {"path": rel, "edits": [{"oldText": "content",
                                                                                   "newText": "changed"}]})
        res["tool_ls"] = await tool(registry, "ls", {"path": "."})
        res["fs_write_file"] = await fs_op(fs.write_file(f"g{comp}.txt", b"x"))
        res["fs_read_text_file"] = await fs_op(fs.read_text_file(rel))
        res["fs_canonical_path"] = await fs_op(fs.canonical_path(rel))
        res["listing_final"] = listing(root)
        out["results"].append(res)
    with open(sys.argv[1], "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    print(len(out["results"]), "results", sys.platform)


asyncio.run(main())
