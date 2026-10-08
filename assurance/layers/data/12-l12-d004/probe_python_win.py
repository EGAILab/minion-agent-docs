import asyncio, json, sys
from minion_agent.execution import LocalFileSystem, Ok
base, cases_path, out = sys.argv[1], sys.argv[2], sys.argv[3]
fs = LocalFileSystem(base)
async def main():
    rows = []
    for case in json.load(open(cases_path)):
        r = await fs.canonical_path(case["rel"])
        rows.append({"rel": case["rel"], "current": {"ok": r.value} if isinstance(r, Ok) else {"error": r.error.code.value}})
    json.dump(rows, open(out, "w"), indent=1)
asyncio.run(main())
