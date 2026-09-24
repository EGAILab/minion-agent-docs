"""Certified Layer 12 LocalFileSystem on the same fixture: which FsErrorCode each candidate operation
returns. Prints JSON {case: {op: code|"ok[:detail]"}}."""

import asyncio
import json
import sys

from minion_agent.execution import Err, LocalFileSystem

CASES = ["f_ok", "f_000", "d_ok", "d_000", "d_x", "d_r", "d_x/inner", "d_r/inner", "lk_f_ok",
         "lk_f_000", "lk_d_ok", "lk_d_000", "dangling", "loop_a", "f_ok/x", "missing"]


async def main(root: str) -> None:
    fs = LocalFileSystem(root)
    out = {}
    for case in CASES:
        row = {}
        for name, call in [
            ("canonical_path", lambda: fs.canonical_path(case)),
            ("file_info", lambda: fs.file_info(case)),
            ("probe_dir_entry", lambda: fs.probe_dir_entry(case)),
            ("read_text_lines_1", lambda: fs.read_text_lines(case, 1)),
            ("read_binary_file", lambda: fs.read_binary_file(case)),
            ("list_dir", lambda: fs.list_dir(case)),
            ("list_dir_raw", lambda: fs.list_dir_raw(case)),
            ("exists", lambda: fs.exists(case)),
        ]:
            try:
                result = await call()
            except Exception as exc:  # a provider bug, recorded rather than hidden
                row[name] = f"RAISED {type(exc).__name__}"
                continue
            if isinstance(result, Err):
                row[name] = result.error.code.value
            else:
                value = result.value
                kind = getattr(value, "kind", None)
                row[name] = f"ok:{kind.value}" if kind is not None else ("ok:" + str(value) if isinstance(value, bool) else "ok")
        out[case] = row
    print(json.dumps({"python": sys.version.split()[0], "platform": sys.platform, "cases": out}))


asyncio.run(main(sys.argv[1]))
