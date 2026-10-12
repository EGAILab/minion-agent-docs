"""L12-D008 / DIV-008 acceptance comparator: pinned Pi's rows (div008-pi-probe.mjs) against a binding's rows
(div008_py_probe.py or the Rust equivalent), same matrix, same platform. Per row and run:

  EXTENT (required parity, Owner decision #215 issuecomment-6118734550): the binding's remaining entries after
      remove() returns equal pinned Pi's AFTER ITS IN-FLIGHT REMOVALS DRAIN (`after_drain.remains`). Pi's state
      at settlement is not the comparison point: Pi may return before its other removals finish.
  COMPLETE: every injection the binding could make fired (a binding-only UNFIRED means a sibling was skipped);
      the binding has no late calls (it returns after every child was attempted).
  SELECTION (DIV-008): the binding reports the FIRST FAILURE IT ENCOUNTERED: its path is the first `settle` in its
      own call sequence, and its code is the code of that injected failure as the binding maps it. Equality with
      Pi's reported path is NOT required (Pi reports the first failure to settle); a row where they differ is
      reported as DIV-008, never as a match of Pi's rule.
  OUTCOME: ok/failed agrees with Pi.
Natural rows (no injection) compare EXTENT and OUTCOME per run; SELECTION is checked against the binding's own
first host failure in its sequence when one is recorded.

Exit 0 iff every row passes. Usage: python div008_compare.py <pi.jsonl> <binding.jsonl> [--self-test]"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def load(path: str) -> dict[tuple[str, int], dict]:
    rows = [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
    return {(row["id"], row.get("run", 1)): row for row in rows}


def first_settled(row: dict) -> str | None:
    for item in row["seq"]:
        if item.startswith("settle "):
            return item.split(" ", 2)[2]
    return None


def check(pi: dict, b: dict) -> tuple[str, list[str]]:
    problems: list[str] = []
    if (pi["result"] == "ok") != (b["result"] == "ok"):
        problems.append(f"outcome: Pi {pi['result']}, binding {b['result']}")
    if b["after_drain"]["remains"] != pi["after_drain"]["remains"]:
        problems.append(f"extent: binding leaves {b['after_drain']['remains']}, Pi after drain {pi['after_drain']['remains']}")
    skipped = sorted(set(b.get("unfired", [])) - set(pi.get("unfired", [])))
    if skipped:
        problems.append(f"complete: binding never made {skipped}")
    if b.get("late_calls"):
        problems.append(f"complete: binding made calls after returning {b['late_calls']}")
    verdict = "MATCH"
    if b["result"] != "ok":
        own_first = first_settled(b)
        if own_first is not None and b["path"] != own_first:
            problems.append(f"selection: binding reports {b['path']}, but its first encountered failure is {own_first}")
        if pi["path"] != b["path"] or pi["result"] != b["result"]:
            verdict = "DIV-008"
    return ("FAIL" if problems else verdict), problems


def compare(pi_rows: dict, b_rows: dict) -> int:
    failed = 0
    for key in pi_rows:
        if key not in b_rows:
            print(f"{'MISSING':8} {key[0]} run {key[1]}")
            failed += 1
            continue
        verdict, problems = check(pi_rows[key], b_rows[key])
        print(f"{verdict:8} {key[0]} run {key[1]}: Pi {pi_rows[key]['path']} / binding {b_rows[key]['path']}")
        for p in problems:
            print(f"           {p}")
        failed += verdict == "FAIL"
    extra = sorted(set(b_rows) - set(pi_rows))
    for key in extra:
        print(f"{'EXTRA':8} {key[0]} run {key[1]}")
        failed += 1
    return failed


def self_test() -> int:
    """Negative controls on synthetic rows: each must be rejected (FAIL), the positives accepted."""
    pi = {"id": "x", "run": 1, "result": "permission_denied", "path": "tree/b", "unfired": [], "late_calls": ["settle unlink tree/a"],
          "seq": ["unlink tree/a", "unlink tree/b", "settle unlink tree/b", "settle unlink tree/a"],
          "after_drain": {"remains": ["tree/", "tree/a", "tree/b"]}}
    good = {"id": "x", "run": 1, "result": "permission_denied", "path": "tree/a", "unfired": [], "late_calls": [],
            "seq": ["unlink tree/a", "settle unlink tree/a", "unlink tree/b", "settle unlink tree/b"],
            "after_drain": {"remains": ["tree/", "tree/a", "tree/b"]}}
    cases = [
        ("positive: first encountered, extent equal (DIV-008 selection)", good, "DIV-008"),
        ("false first-settled claim: binding reports Pi's path, not its own first", {**good, "path": "tree/b"}, "FAIL"),
        ("stop at first failure: sibling skipped", {**good, "unfired": ["unlink tree/b #1"],
            "seq": ["unlink tree/a", "settle unlink tree/a"]}, "FAIL"),
        ("extent differs", {**good, "after_drain": {"remains": ["tree/", "tree/a", "tree/b", "tree/m"]}}, "FAIL"),
        ("late calls after return", {**good, "late_calls": ["unlink tree/m"]}, "FAIL"),
        ("outcome differs", {**good, "result": "ok", "path": None}, "FAIL"),
    ]
    bad = 0
    for name, row, expect in cases:
        verdict, _ = check(pi, row)
        ok = verdict == expect
        bad += not ok
        print(f"{'PASS' if ok else 'FAIL'} {name}: {verdict} (expected {expect})")
    print("COMPARATOR SELFTEST " + ("PASSED" if not bad else f"FAILED ({bad})"))
    return 1 if bad else 0


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        raise SystemExit(self_test())
    raise SystemExit(1 if compare(load(sys.argv[1]), load(sys.argv[2])) else 0)
