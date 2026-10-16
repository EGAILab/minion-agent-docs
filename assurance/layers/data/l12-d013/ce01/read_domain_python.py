"""CE-L12D013-01 read-domain characterization, Python side (win32 only; run on Windows). Pure and in-memory: no
filesystem access, no child. The rows of read_domain_node.mjs go through the REAL resolve_local_path of the given
candidate src. Its two native boundaries are replaced by counting fakes: the process-cwd view returns the
injected "E:\\proc", and the inherited-entry view returns the row's injected entry state. Output: JSON on stdout.
POSIX rows are not run: merged Python's POSIX branch contains no process-cwd read (source fact, record section
10.3).

    python -I -B read_domain_python.py <candidate src>

Importing the candidate reads its source and its dependencies; no bytecode is written (-B, and
dont_write_bytecode set before the import as a second guard). No resolver input touches the filesystem.
"""

import sys

sys.dont_write_bytecode = True
import json  # noqa: E402

sys.path.insert(0, sys.argv[1])
from minion_agent.execution import filesystem  # noqa: E402

assert sys.platform == "win32", "the win32 resolver branch runs only on win32"
PROVIDERS = ["C:\\base", "\\base", "C:base", "base", "", "\\\\srv\\share\\base", "\\\\?\\C:\\base"]
INPUTS = ["C:\\x", "\\\\srv\\share\\x", "\\leaf", "/leaf", "\\\\leaf", "\\\\srv\\", "a:leaf", "c:leaf", "leaf", "",
          "file:///C:/x", "file://srv/share/x"]
ENTRIES = {"absent": {}, "empty": {"A:": "", "C:": ""}, "same": {"A:": "A:\\deep", "C:": "C:\\deep"},
           "other": {"A:": "X:\\other", "C:": "X:\\other"}}

rows = []
for provider in PROVIDERS:
    for source in INPUTS:
        for state, entries in ENTRIES.items():
            reads: list[int] = []
            env_reads: list[str] = []

            def cwd_view() -> str:
                reads.append(1)
                return "E:\\proc"

            def inherited(device: str, entries: dict = entries) -> str | None:
                env_reads.append("=" + device)
                return entries.get(device.upper())

            filesystem._native_process_cwd_view = cwd_view
            filesystem._native_inherited_view = inherited
            row = {"platform": "win32", "provider": provider, "input": source, "entries": state}
            try:
                row["value"] = filesystem.resolve_local_path(provider, source)
            except Exception as exc:  # recorded, never swallowed silently
                row["error"] = f"{type(exc).__name__}: {exc}"
            row["cwdReads"] = len(reads)
            row["envReads"] = env_reads
            rows.append(row)
print(json.dumps({"python": sys.version.split()[0], "src": sys.argv[1], "rows": rows}, indent=1))
