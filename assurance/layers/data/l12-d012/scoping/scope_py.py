"""L12-D012 scoping: Python's certified resolve_local_path against the pinned-Pi win32 column (pure computation)."""

import json
import sys
from pathlib import Path

ROOT = Path("E:/AI/Projects/OpenMinds/Minions/Minion-Agent")
sys.path.insert(0, str(ROOT / "review-worktrees/claude-d011-py/minion-agent-python/src"))
from minion_agent.execution.filesystem import resolve_local_path  # noqa: E402

rows = json.load(open(Path(__file__).with_name("scope-node.json"), encoding="utf-8"))["rows"]
diff = 0
for row in rows:
    got = resolve_local_path("C:\\x", row["input"])
    ok = got == row["win32"]
    diff += not ok
    print("OK  " if ok else "DIFF", repr(row["input"]), repr(got), "" if ok else f"(pi {row['win32']!r})")
print(f"{len(rows) - diff}/{len(rows)} equal on win32")
