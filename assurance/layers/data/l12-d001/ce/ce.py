"""CE-L12-D001-01: ce.mjs's programs through Minion's Python LocalFileSystem (same interleaving: the entry is removed
after enumeration, immediately before the provider's own lstat of it -- a real os.unlink, no fabricated errno).
    python ce.py <out.json>"""
import asyncio, json, os, stat, sys, tempfile
from minion_agent.execution.filesystem import LocalFileSystem
def U(s): b = s.encode("utf-16-le", "surrogatepass"); return [int.from_bytes(b[i:i + 2], "little") for i in range(0, len(b), 2)]
def rel(cwd, v): return None if not isinstance(v, str) else [U(c) for c in os.path.relpath(v, cwd).split(os.sep)]
def observe(cwd, r):
    e = getattr(r, "error", None)
    return {"ok": True} if e is None else {"error": str(e.code), "path": rel(cwd, e.path)}
async def main():
    results = []
    for variant, name in {"scalar": "b", "lone": "a" + chr(0xD800)}.items():
        native = name.replace(chr(0xD800), chr(0xFFFD))
        cwd = os.path.realpath(tempfile.mkdtemp(prefix="l12ce-")); fs = LocalFileSystem(cwd)
        await fs.write_file(f"{name}/child.txt", "x")
        original = os.lstat
        def lstat(p, *a, **k):
            if os.fspath(p).endswith("child.txt") and os.path.exists(p): os.unlink(p)
            return original(p, *a, **k)
        os.lstat = lstat
        try: results.append({"id": f"{variant}/entry-vanish", "observed": observe(cwd, await fs.list_dir(name))})
        finally: os.lstat = original
        if sys.platform == "win32":
            shapes = [("rm-readonly-file", lambda n: os.chmod(os.path.join(n, "sub", "f"), stat.S_IREAD),
                       lambda n: os.chmod(os.path.join(n, "sub", "f"), stat.S_IWRITE))]
        else:
            shapes = [("rm-inner", lambda n: os.chmod(os.path.join(n, "sub"), 0o555), lambda n: os.chmod(os.path.join(n, "sub"), 0o755)),
                      ("rm-unreadable-dir", lambda n: os.chmod(os.path.join(n, "sub"), 0o333), lambda n: os.chmod(os.path.join(n, "sub"), 0o755)),
                      ("rm-readonly-parent", lambda n: os.chmod(n, 0o555), lambda n: os.chmod(n, 0o755))]
        for shape, lock, unlock in shapes:
            cwd = os.path.realpath(tempfile.mkdtemp(prefix="l12ce-")); fs = LocalFileSystem(cwd)
            await fs.write_file(f"{name}/sub/f", "x")
            top = os.path.join(cwd, native)
            lock(top)
            results.append({"id": f"{variant}/{shape}", "observed": observe(cwd, await fs.remove(name, recursive=True))})
            try: unlock(top)
            except OSError: pass
        if sys.platform != "win32":
            cwd = os.path.realpath(tempfile.mkdtemp(prefix="l12ce-")); fs = LocalFileSystem(cwd)
            os.mkfifo(os.path.join(cwd, native))
            results.append({"id": f"{variant}/fifo-file-info", "observed": observe(cwd, await fs.file_info(name))})
    with open(sys.argv[1], "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"platform": sys.platform, "uid": getattr(os, "getuid", lambda: None)(), "results": results}, fh, indent=1)
        fh.write("\n")
asyncio.run(main())
