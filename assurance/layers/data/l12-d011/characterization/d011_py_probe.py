"""L12-D011 (#224) characterization, Minion Python side (current main): ctx.subprocess.spawn and the find/bash tools
with NUL in the executable, argv, cwd, env name/value, plus a pre-aborted signal. Records the answer, the raised
exception or the tool result. Writes only <run>/py-<platform>.json (proven inside the run dir); the engine store and
cwd are created by the caller inside the run dir. No deletes.
Usage: python d011_py_probe.py <run dir with cwd/ and engines/ ready> <search-engine artifacts dir or "-">
"""
import asyncio
import json
import os
import sys
import traceback
from pathlib import Path

run = Path(sys.argv[1]).resolve(strict=True)
cwd = (run / "cwd").resolve(strict=True)
from minion_agent.execution import LocalFileSystem  # noqa: E402
from minion_agent.execution.subprocess import LocalSubprocess, SpawnOptions  # noqa: E402
from minion_agent.llm import TextBlock, ToolCallBlock  # noqa: E402
from minion_agent.runtime import Context, RunAbortController  # noqa: E402
from minion_agent.tools.builtin.bash import create_bash_tool  # noqa: E402
from minion_agent.tools.builtin.find import create_find_tool  # noqa: E402
from minion_agent.tools.builtin.search_engines import EngineStore, provision_search_engines  # noqa: E402
from minion_agent.tools.events import declare_tools_events  # noqa: E402
from minion_agent.tools.execute import execute_call  # noqa: E402

N = "\x00"
root = str(cwd)
PLATFORM = "win32" if os.name == "nt" else "linux"
rows = []


def norm(s):
    return s.replace(root, "<CWD>").replace(root.replace("\\", "/"), "<CWD>") if isinstance(s, str) else s


async def direct(case, argv, **opts):
    sub = LocalSubprocess(root)
    try:
        answer = await sub.spawn(argv, SpawnOptions(**opts))
    except BaseException as exc:
        rows.append({"id": case, "kind": "direct", "outcome": "exception", "type": type(exc).__name__,
                     "message": norm(str(exc)), "where": traceback.format_exc().strip().splitlines()[-2].strip()})
        return
    err = getattr(answer, "error", None)
    if err is not None:
        rows.append({"id": case, "kind": "direct", "outcome": "err", "code": str(getattr(err, "code", None)),
                     "message": norm(getattr(err, "message", str(err)))})
    else:
        proc = answer.value
        await proc.terminate() if hasattr(proc, "terminate") else None
        rows.append({"id": case, "kind": "direct", "outcome": "STARTED"})


async def tool(case, name, arguments, aborted=False, store=None):
    fs, sub = LocalFileSystem(root), LocalSubprocess(root)
    from minion_agent.tools.registry import ToolRegistry
    registry = ToolRegistry()
    registry.register(create_find_tool(fs, sub, store) if name == "find" else create_bash_tool(fs, sub))
    ctx = Context()
    declare_tools_events(ctx.events)
    controller = RunAbortController()
    if aborted:
        controller.abort()
    try:
        result = await execute_call(ToolCallBlock(id="c", name=name, arguments=arguments), registry=registry, ctx=ctx,
                                    signal=controller.signal)
    except BaseException as exc:
        rows.append({"id": case, "kind": "tool", "outcome": "exception", "type": type(exc).__name__, "message": str(exc)})
        return
    first = result.content[0]
    rows.append({"id": case, "kind": "tool", "outcome": "result", "is_error": result.is_error,
                 "text": norm(first.text if isinstance(first, TextBlock) else repr(first))})


async def main():
    py = sys.executable
    await direct("file", ["x" + N + "y"])
    await direct("args0", [py, "a" + N])
    await direct("args-first-vs-later", [py, "ok", "b" + N, "c" + N])
    await direct("cwd", [py, "ok"], cwd="d" + N)
    await direct("env-value", [py, "-c", "pass"], env={"K": "v" + N})
    await direct("env-name", [py, "-c", "pass"], env={"A" + N + "B": "v"})
    await direct("control-nonexistent-binary", ["minion-d011-nonexistent-binary", "ok"])
    store = None
    if sys.argv[2] != "-":
        store = EngineStore(root=run / "engines")
        provision_search_engines(store, source=sys.argv[2])
        nul_path = root.replace("\\", "/") + "/x" + N + "y"
        await tool("find-nul-search-path", "find", {"pattern": "*.ts", "path": nul_path}, store=store)
        await tool("find-nul-pattern", "find", {"pattern": "a" + N + "b"}, store=store)
        await tool("find-nul-pattern-pre-aborted", "find", {"pattern": "a" + N + "b"}, aborted=True, store=store)
    await tool("bash-nul-command", "bash", {"command": "echo a" + N + "b"})
    await tool("bash-nul-command-pre-aborted", "bash", {"command": "echo a" + N + "b"}, aborted=True)
    out = run / f"py-{PLATFORM}.json"
    assert out.resolve().parent == run
    out.write_text(json.dumps({"platform": PLATFORM, "rows": rows}, indent=1, ensure_ascii=True) + "\n", encoding="utf-8")
    print(f"d011 py probe: {PLATFORM}, {len(rows)} rows")


asyncio.run(main())
