import asyncio, os, tempfile, collections
from minion_agent.execution.filesystem import LocalFileSystem
async def main():
    tally = collections.Counter()
    for run in range(20):
        cwd = os.path.realpath(tempfile.mkdtemp(prefix="l12two-")); fs = LocalFileSystem(cwd)
        for d in "ab":
            await fs.write_file(f"t/{d}/locked", "x"); os.chmod(os.path.join(cwd, "t", d), 0o555)
        r = await fs.remove("t", recursive=True)
        tally[os.path.relpath(r.error.path, cwd)] += 1
        for d in "ab": os.chmod(os.path.join(cwd, "t", d), 0o755)
    print("py", dict(tally))
asyncio.run(main())
