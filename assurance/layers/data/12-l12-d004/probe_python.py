"""Python side: current certified LocalFileSystem.canonical_path vs the proposed libc realpath(3),
on the fixture. Usage: python probe_python.py <base> <cases.json> <out.json>"""

import asyncio
import ctypes
import ctypes.util
import errno
import json
import os
import sys

from minion_agent.execution import LocalFileSystem, Ok
from minion_agent.execution.errors import to_fs_error
from minion_agent.execution.filesystem import native_path, resolve_local_path

base, cases_path, out = sys.argv[1], sys.argv[2], sys.argv[3]
cases = json.load(open(cases_path))
fs = LocalFileSystem(base)


def libc_realpath(path: str):
    libc = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)
    libc.realpath.restype = ctypes.c_void_p
    libc.realpath.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
    libc.free.argtypes = [ctypes.c_void_p]
    ptr = libc.realpath(os.fsencode(path), None)
    if not ptr:
        e = ctypes.get_errno()
        mapped = to_fs_error(OSError(e, os.strerror(e)), path).code.value
        return {"error": errno.errorcode.get(e, str(e)), "mapped": mapped}
    try:
        return {"ok": os.fsdecode(ctypes.string_at(ptr))}
    finally:
        libc.free(ptr)


async def main():
    rows = []
    for case in cases:
        native = native_path(resolve_local_path(base, case["rel"]))
        cur = await fs.canonical_path(case["rel"])
        current = {"ok": cur.value} if isinstance(cur, Ok) else {"error": cur.error.code.value, "message": cur.error.message[:80]}
        try:
            raw = {"ok": os.path.realpath(native, strict=True)}
        except OSError as e:
            raw = {"error": errno.errorcode.get(e.errno, str(e.errno)), "mapped": to_fs_error(e, native).code.value}
        rows.append({"rel": case["rel"], "current": current, "os_path_realpath": raw, "libc_realpath": libc_realpath(native)})
    json.dump(rows, open(out, "w"), indent=1)


asyncio.run(main())
