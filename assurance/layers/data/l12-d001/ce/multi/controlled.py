"""CE-L12-D001-01-C001 scope-boundary witness: the Python binding under the same two-failure tree. Both children's
unlink is refused (injected EACCES); the binding has no concurrency to order, so its answer cannot follow a
completion order -- it reports the first-ENUMERATED failure.   python controlled.py <out.json>"""
import asyncio, errno, json, os, sys, tempfile
from minion_agent.execution.filesystem import LocalFileSystem
def U(s): b = s.encode("utf-16-le", "surrogatepass"); return [int.from_bytes(b[i:i + 2], "little") for i in range(0, len(b), 2)]
async def main():
    results = []
    original = os.unlink
    for variant, name in {"scalar": "tree", "lone": "t" + chr(0xD800)}.items():
        root = os.path.realpath(tempfile.mkdtemp(prefix="l12mf-")); fs = LocalFileSystem(root)
        await fs.write_file(f"{name}/a", "a"); await fs.write_file(f"{name}/b", "b")
        entered = []
        def unlink(p, *a, **k):
            child = os.path.basename(os.fspath(p))
            if child in ("a", "b"):
                entered.append(child); raise PermissionError(errno.EACCES, "controlled unlink failure", p)
            return original(p, *a, **k)
        os.unlink = unlink
        try: r = await fs.remove(name, recursive=True)
        finally: os.unlink = original
        results.append({"id": f"{variant}/two-failures", "entered": entered,
                        "observed": {"error": str(r.error.code), "path": [U(c) for c in os.path.relpath(r.error.path, root).split(os.sep)]}})
    with open(sys.argv[1], "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"platform": sys.platform, "results": results}, fh, indent=1); fh.write("\n")
asyncio.run(main())
