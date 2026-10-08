"""L12D004-R001 neighbourhood: paths containing NUL, through canonical_path and its consumers
(EXEC-003 resolve, TOOL-032 mutation queue key), on whichever minion_agent is on PYTHONPATH.
Usage: python probe_nul.py <base> <cases.json> <out.json>"""

import asyncio
import json
import re
import sys

from minion_agent.execution import LocalFileSystem, Ok
from minion_agent.tools.builtin.mutation_queue import mutation_queue_key

base, cases_path, out = sys.argv[1], sys.argv[2], sys.argv[3]
fs = LocalFileSystem(base)


def shown(value):
    return re.sub(r" at 0x[0-9a-f]+", "", repr(value))  # object addresses are not behaviour


async def outcome(call):
    try:
        result = await call()
    except Exception as exc:  # noqa: BLE001 -- the outcome itself is what is recorded
        return {"raises": type(exc).__name__, "text": str(exc)}
    if isinstance(result, Ok):
        return {"ok": shown(result.value)}
    if hasattr(result, "error"):
        return {"error": result.error.code.value}
    return {"ok": shown(result)}


async def main():
    rows = []
    for case in json.load(open(cases_path)):
        rel = case["rel"]
        rows.append({
            "rel": rel,
            "canonical_path": await outcome(lambda: fs.canonical_path(rel)),
            "resolve": await outcome(lambda: fs.resolve(rel)),
            "mutation_queue_key": await outcome(lambda: mutation_queue_key(fs, rel, rel)),
        })
    json.dump(rows, open(out, "w"), indent=1)


asyncio.run(main())
