"""CE-L12D007-02 acceptance comparator: pinned Pi's rows against a Python candidate's rows (same matrix, same
platform). A row MATCHes when the result code, the error path, what remains, and the per-path counts of the
child-walk calls (rmdir, unlink, readdir, and lstat of anything below `tree`) are equal. The top-level `lstat tree`
count (Node's rm validates first) and `stat` / `chmod` (fixWinEPERM mechanics) are not compared.
Exit 0 iff every row matches except those named in --expected-diff.

Usage: python ce02_compare.py <pi.jsonl> <py.jsonl> [--expected-diff ID ...]"""

from __future__ import annotations

import json
import sys
from pathlib import Path

COMPARED_OPS = ("rmdir", "unlink", "readdir", "lstat")


def load(path: str) -> dict[str, dict]:
    rows = [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
    return {row["id"]: row for row in rows}


def walk_calls(row: dict) -> dict[str, int]:
    return {
        key: n
        for key, n in row["calls"].items()
        if key.split(" ", 1)[0] in COMPARED_OPS and key != "lstat tree"
    }


def view(row: dict) -> dict:
    return {"result": row["result"], "path": row["path"], "remains": row["remains"], "calls": walk_calls(row)}


def main(argv: list[str]) -> int:
    pi, py = load(argv[0]), load(argv[1])
    expected = set(argv[argv.index("--expected-diff") + 1 :]) if "--expected-diff" in argv else set()
    assert pi.keys() == py.keys(), (sorted(pi), sorted(py))
    failed = 0
    for row_id in pi:
        same = view(pi[row_id]) == view(py[row_id])
        verdict = "MATCH" if same else ("EXPECTED-DIFF" if row_id in expected else "DIFF")
        print(f"{verdict:13} {row_id}")
        if not same:
            print(f"    pi: {view(pi[row_id])}\n    py: {view(py[row_id])}")
        failed += verdict == "DIFF" or (same and row_id in expected)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
