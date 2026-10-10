"""L12-D006 characterization: the pi-nul-probe.mjs matrix through Minion's REAL LocalFileSystem.

    PYTHONPATH=<minion-agent-python>/src python py-nul-probe.py <out.json>

Same case ids, fixture (file `f` = "x", directory `d`) and observation as the Pi probe, plus the
Minion-only operations (list_dir_raw, probe_dir_entry, check_readable, check_read_write, resolve)."""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import struct
import sys
import tempfile
from pathlib import Path
from typing import Any

from minion_agent.execution import LocalFileSystem, is_ok
from minion_agent.runtime.signal import RunAbortController, RunSignal

NUL = "\x00"
PATHS = {
    "begin": f"{NUL}f",
    "middle": f"f{NUL}x",
    "end": f"f{NUL}",
    "last_component_under_new_parent": f"new/a{NUL}b",
    "parent_component": f"p{NUL}q/child",
    "lone_surrogate_and_nul": f"\ud800{NUL}z",
}


def units(s: str) -> list[int]:
    data = s.encode("utf-16-le", "surrogatepass")
    return list(struct.unpack(f"<{len(data) // 2}H", data))


def aborted() -> RunSignal:
    controller = RunAbortController()
    controller.abort()
    return controller.signal


def left(directory: Path, base: Path | None = None) -> list[str]:
    base = base or directory
    out: list[str] = []
    for name in sorted(os.listdir(directory)):
        p = directory / name
        rel = p.relative_to(base).as_posix()
        if p.is_dir() and not p.is_symlink():
            out.append(rel + "/")
            out.extend(left(p, base))
        else:
            out.append(rel)
    return out


def rel(cwd: Path, value: str) -> str:
    return os.path.relpath(value, cwd) if os.path.isabs(value) else value


def observe(cwd: Path, result: Any) -> Any:
    if is_ok(result):
        v = result.value
        if isinstance(v, str):
            return {"ok": {"string": units(rel(cwd, v) if v.startswith(str(cwd)) else v)}}
        if isinstance(v, list):
            return {"ok": {"array": len(v)}}
        if isinstance(v, bytes):
            return {"ok": {"bytes": len(v)}}
        if v is None or isinstance(v, bool):
            return {"ok": v}
        return {"ok": {"object": type(v).__name__}}
    e = result.error
    return {"error": e.code.value, "path": None if e.path is None else units(rel(cwd, e.path))}


def ops() -> list[tuple[str, Any]]:
    out: list[tuple[str, Any]] = []
    for where, p in PATHS.items():
        out += [
            (f"absolutePath/{where}", lambda fs, p=p: fs.absolute_path(p)),
            (f"joinPath/{where}", lambda fs, p=p: fs.join_path(["d", p])),
            (f"readTextFile/{where}", lambda fs, p=p: fs.read_text_file(p)),
            (f"readTextLines/{where}", lambda fs, p=p: fs.read_text_lines(p)),
            (f"readTextLines-max0/{where}", lambda fs, p=p: fs.read_text_lines(p, max_lines=0)),
            (f"readBinaryFile/{where}", lambda fs, p=p: fs.read_binary_file(p)),
            (f"writeFile/{where}", lambda fs, p=p: fs.write_file(p, "w")),
            (f"appendFile/{where}", lambda fs, p=p: fs.append_file(p, "w")),
            (f"renameFile-source/{where}", lambda fs, p=p: fs.rename_file(p, "g")),
            (f"renameFile-destination/{where}", lambda fs, p=p: fs.rename_file("f", p)),
            (f"renameFile-both/{where}", lambda fs, p=p: fs.rename_file(p, p)),
            (f"fileInfo/{where}", lambda fs, p=p: fs.file_info(p)),
            (f"listDir/{where}", lambda fs, p=p: fs.list_dir(p)),
            (f"canonicalPath/{where}", lambda fs, p=p: fs.canonical_path(p)),
            (f"exists/{where}", lambda fs, p=p: fs.exists(p)),
            (f"createDir/{where}", lambda fs, p=p: fs.create_dir(p)),
            (f"createDir-nonrecursive/{where}", lambda fs, p=p: fs.create_dir(p, recursive=False)),
            (f"remove/{where}", lambda fs, p=p: fs.remove(p)),
            (f"remove-recursive/{where}", lambda fs, p=p: fs.remove(p, recursive=True)),
            (f"remove-force/{where}", lambda fs, p=p: fs.remove(p, force=True)),
            (f"remove-recursive-force/{where}", lambda fs, p=p: fs.remove(p, recursive=True, force=True)),
            (f"listDirRaw/{where}", lambda fs, p=p: fs.list_dir_raw(p)),
            (f"probeDirEntry/{where}", lambda fs, p=p: fs.probe_dir_entry(p)),
            (f"checkReadable/{where}", lambda fs, p=p: fs.check_readable(p)),
            (f"checkReadWrite/{where}", lambda fs, p=p: fs.check_read_write(p)),
            (f"resolve/{where}", lambda fs, p=p: fs.resolve(p)),
        ]
    m = PATHS["middle"]
    out += [
        ("readTextFile-aborted/middle", lambda fs: fs.read_text_file(m, signal=aborted())),
        ("readTextLines-aborted/middle", lambda fs: fs.read_text_lines(m, signal=aborted())),
        ("readTextLines-aborted-max0/middle", lambda fs: fs.read_text_lines(m, max_lines=0, signal=aborted())),
        ("readBinaryFile-aborted/middle", lambda fs: fs.read_binary_file(m, signal=aborted())),
        ("writeFile-aborted/last_component_under_new_parent",
         lambda fs: fs.write_file(PATHS["last_component_under_new_parent"], "w", signal=aborted())),
        ("renameFile-aborted-source/middle", lambda fs: fs.rename_file(m, "g", signal=aborted())),
        ("renameFile-aborted-destination/middle", lambda fs: fs.rename_file("f", m, signal=aborted())),
        ("listDir-aborted/middle", lambda fs: fs.list_dir(m, signal=aborted())),
        ("createTempDir-prefix/middle", lambda fs: fs.create_temp_dir(f"t{NUL}x")),
        ("createTempFile-prefix/middle", lambda fs: fs.create_temp_file(prefix=f"t{NUL}x")),
        ("createTempFile-suffix/middle", lambda fs: fs.create_temp_file(suffix=f"t{NUL}x")),
    ]
    return out


async def main() -> None:
    root = Path(tempfile.mkdtemp(prefix="l12d006-py-")).resolve()
    results = []
    for n, (case_id, run) in enumerate(ops()):
        cwd = root / str(n)
        (cwd / "d").mkdir(parents=True)
        (cwd / "f").write_text("x")
        fs = LocalFileSystem(str(cwd))
        try:
            observed = observe(cwd, await run(fs))
        except BaseException as error:  # noqa: BLE001 -- characterization records what escapes
            observed = {"threw": f"{type(error).__name__}: {error}"}
        results.append({"id": case_id, "observed": observed, "left": left(cwd)})
    shutil.rmtree(root, ignore_errors=True)
    with open(sys.argv[1], "w", encoding="utf-8") as handle:
        json.dump({"platform": sys.platform, "python": sys.version.split()[0], "results": results}, handle, indent=1)
        handle.write("\n")
    print(f"l12-d006 python probe ({sys.platform}): {len(results)} cases")


asyncio.run(main())
