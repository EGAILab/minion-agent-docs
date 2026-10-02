"""Same step programs as probe.mjs, run through Minion's Python LocalFileSystem."""
import asyncio, json, os, sys, tempfile
from minion_agent.execution.filesystem import LocalFileSystem
def U(s): b = s.encode("utf-16-le", "surrogatepass"); return [int.from_bytes(b[i:i+2], "little") for i in range(0, len(b), 2)]
def rel(cwd, v):
    if not isinstance(v, str): return None
    r = os.path.relpath(v, cwd)
    return [] if r == "." else [U(c) for c in r.split(os.sep)]
NAMES = {"scalar": "b", "lone": "a" + chr(0xD800)}
def cases(N):
    P = lambda *xs: "/".join(xs)
    return {
    "parent-file/write": [["w", N], ["w", P(N, "child")]],
    "parent-file/append": [["w", N], ["a", P(N, "child")]],
    "grandparent-file/write": [["w", N], ["w", P(N, "x", "child")]],
    "grandparent-file/append": [["w", N], ["a", P(N, "x", "child")]],
    "parent-file/create-dir": [["w", N], ["mk", P(N, "x")]],
    "grandparent-file/create-dir": [["w", N], ["mk", P(N, "x", "y")]],
    "self-file/create-dir": [["w", N], ["mk", N]],
    "parent-file/create-dir-nonrecursive": [["w", N], ["mk1", P(N, "x")]],
    "parent-file/read": [["w", N], ["r", P(N, "child")]],
    "parent-file/read-lines": [["w", N], ["rl", P(N, "child")]],
    "parent-file/read-binary": [["w", N], ["rb", P(N, "child")]],
    "parent-file/file-info": [["w", N], ["fi", P(N, "child")]],
    "parent-file/exists": [["w", N], ["ex", P(N, "child")]],
    "self-file/list-dir": [["w", N], ["ls", N]],
    "parent-file/canonical": [["w", N], ["cp", P(N, "child")]],
    "parent-file/remove": [["w", N], ["rm", P(N, "child")]],
    "self-dir/write": [["mk", N], ["w", N]],
    "self-dir/append": [["mk", N], ["a", N]],
    "self-dir/read": [["mk", N], ["r", N]],
    "self-dir/read-lines": [["mk", N], ["rl", N]],
    "self-dir/read-binary": [["mk", N], ["rb", N]],
    "self-dir/remove": [["mk", N], ["rm", N]],
    "self-dir-nonempty/remove": [["w", P(N, "f")], ["rm", N]],
    "missing/read": [["r", N]],
    "missing/read-lines": [["rl", N]],
    "missing/read-binary": [["rb", N]],
    "missing/file-info": [["fi", N]],
    "missing/list-dir": [["ls", N]],
    "missing/canonical": [["cp", N]],
    "missing/remove": [["rm", N]],
    "missing-parent/create-dir-nonrecursive": [["mk1", P(N, "x")]],
    "missing-parent/canonical": [["cp", P(N, "x")]],
    "rename/missing-source": [["mv", N, "dst"]],
    "rename/missing-source-lone-dst": [["mv", "src", N]],
    "rename/dest-parent-file": [["w", "src"], ["w", N], ["mv", "src", P(N, "child")]],
    "rename/dest-parent-missing": [["w", "src"], ["mv", "src", P(N, "child")]],
    "rename/source-parent-file": [["w", N], ["mv", P(N, "child"), "dst"]],
    "rename/dest-nonempty-dir": [["w", "src"], ["w", P(N, "f")], ["mv", "src", N]],
    "rename/source-in-lone-dir-dest-missing": [["w", P(N, "s")], ["mv", P(N, "s"), P("q", "child")]],
    }
async def main():
    results = []
    for variant, N in NAMES.items():
        for cid, steps in cases(N).items():
            cwd = os.path.realpath(tempfile.mkdtemp(prefix="l12r-")); fs = LocalFileSystem(cwd); observed = []
            for op, a, *b in steps:
                r = await {"w": lambda: fs.write_file(a, "c"), "a": lambda: fs.append_file(a, "c"),
                    "mk": lambda: fs.create_dir(a), "mk1": lambda: fs.create_dir(a, recursive=False),
                    "r": lambda: fs.read_text_file(a), "rl": lambda: fs.read_text_lines(a),
                    "rb": lambda: fs.read_binary_file(a), "fi": lambda: fs.file_info(a), "ex": lambda: fs.exists(a),
                    "ls": lambda: fs.list_dir(a), "cp": lambda: fs.canonical_path(a), "rm": lambda: fs.remove(a),
                    "mv": lambda: fs.rename_file(a, b[0])}[op]()
                e = getattr(r, "error", None)
                observed.append({"ok": True} if e is None else {"error": e.code.value, "path": rel(cwd, e.path),
                    "node_code": type(e.cause).__name__, "node_has_path": getattr(e.cause, "filename", None) is not None, "node_dest": None})
            results.append({"id": f"{variant}/{cid}", "observed": observed})
    with open(sys.argv[1], "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"platform": sys.platform, "results": results}, fh, indent=1)
        fh.write("\n")
asyncio.run(main())
