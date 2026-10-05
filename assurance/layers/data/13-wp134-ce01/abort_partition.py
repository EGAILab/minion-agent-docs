"""CE-L13-WP134-01 characterization: abort timing partition for find and grep (candidate source).

A scripted engine process emits one result line, then EOF on both pipes, then exit 0. The call's
signal is aborted at one point of that sequence. Pi's semantics (find.ts / grep.ts):
  - before the listener exists (grep: before spawn) -> not observed;
  - after registration, before the child's `close` event (exit AND both stdio ends) -> aborted;
  - at/after `close` (the handler removes the listener and decides synchronously) -> not observed.
"""

import asyncio
import json
import sys
from pathlib import Path

from minion_agent.execution import LocalFileSystem
from minion_agent.execution.result import Ok
from minion_agent.execution.subprocess import ExitStatus, LocalSubprocess
from minion_agent.runtime import RunAbortController
from minion_agent.tools.builtin.find import create_find_tool
from minion_agent.tools.builtin.grep import create_grep_tool
from minion_agent.tools.builtin.paths import BuiltinToolError
from minion_agent.tools.builtin.search_engines import EngineOverride

OVERRIDE = EngineOverride({"fd": ["unused"], "rg": ["unused"]})
POINTS = [
    "spawn",  # during spawn (before grep's registration)
    "stdout_data",  # first stdout chunk read
    "stdout_eof",  # stdout EOF read
    "stderr_eof",  # stderr EOF read
    "wait",  # during wait() for exit
    "stdout_close",  # releasing stdout after exit + EOF
    "stderr_close",  # releasing stderr after exit + EOF
]


class Stream:
    def __init__(self, name, chunks, hook):
        self.name, self.chunks, self.hook = name, list(chunks), hook

    async def read_chunk(self):
        if self.chunks:
            self.hook(f"{self.name}_data")
            return Ok(self.chunks.pop(0))
        self.hook(f"{self.name}_eof")
        return Ok(None)

    async def close(self):
        self.hook(f"{self.name}_close")
        await asyncio.sleep(0)


class Process:
    def __init__(self, line, hook):
        self.stdout = Stream("stdout", [line], hook)
        self.stderr = Stream("stderr", [], hook)
        self.hook = hook

    async def wait(self):
        self.hook("wait")
        await asyncio.sleep(0)
        return Ok(ExitStatus(0))

    async def terminate(self):
        pass


class Sub(LocalSubprocess):
    def __init__(self, cwd, line, hook):
        super().__init__(cwd)
        self.line, self.hook = line, hook

    async def spawn(self, argv, options=None):
        self.hook("spawn")
        return Ok(Process(self.line, self.hook))


async def one(tool_name, point, root):
    controller = RunAbortController()
    fired = []

    def hook(at):
        if at == point and not fired:
            fired.append(at)
            controller.abort()

    if tool_name == "find":
        line = (str(root / "a.ts") + "\n").encode()
        tool = create_find_tool(LocalFileSystem(str(root)), Sub(str(root), line, hook), OVERRIDE)
        args = {"pattern": "*"}
    else:
        event = {"type": "match", "data": {"path": {"text": str(root / "a.ts")}, "line_number": 1, "lines": {"text": "x\n"}}}
        line = (json.dumps(event) + "\n").encode()
        tool = create_grep_tool(LocalFileSystem(str(root)), Sub(str(root), line, hook), OVERRIDE)
        args = {"pattern": "x"}
    try:
        result = await tool.execute("c", args, controller.signal)
        return result.content[0].text
    except BuiltinToolError as error:
        return "ERR " + str(error)


async def main():
    root = Path(sys.argv[1]).resolve()
    root.mkdir(parents=True, exist_ok=True)
    out = {}
    for tool_name in ("find", "grep"):
        for point in POINTS:
            out[f"{tool_name}/{point}"] = await one(tool_name, point, root)
    print(json.dumps(out, indent=1))


asyncio.run(main())
