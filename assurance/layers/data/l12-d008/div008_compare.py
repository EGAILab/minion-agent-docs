"""L12-D008 / DIV-008 acceptance comparator: pinned Pi's rows (div008-pi-probe.mjs) against a binding's rows
(div008_py_probe.py or the Rust equivalent), same matrix, same platform.

READINESS first (L12D008-C002): a pinned-Pi row that did not drain (`drained` false), whose held failures were
released by the timeout (`settle_incomplete`), or that left a planned injection unfired, is not an oracle; a
binding row that did not drain is not an observation. Such a row is INVALID -- never compared, never counted as a
match or as DIV-008 -- and makes the run fail. The code table (`codes` in the matrix) is checked against pinned Pi
itself: on every row where Pi selected an injected failure, Pi's reported code must be the table's code for it.

Then, per row and run:
  EXTENT (required parity, Owner decision #215 issuecomment-6118734550): the binding's remaining entries after
      remove() returns equal pinned Pi's AFTER ITS IN-FLIGHT REMOVALS DRAIN (`after_drain.remains`).
  COMPLETE: no binding-only unfired injection (no skipped sibling) and no late calls.
  SELECTION (DIV-008): the binding reports the FIRST FAILURE IT ENCOUNTERED -- its path is the entry of the first
      `settle` in its own call sequence -- WITH THAT FAILURE'S CODE (the code table's entry for the injected code).
      Pi's own selection is not required (Pi reports the first to settle); a row whose selection differs from Pi's
      is reported as DIV-008. DIV-008 permits a different failing ENTRY and that entry's correct code, never a
      different code for the same selected failure.
  OUTCOME: ok/failed agrees with Pi.
Natural rows (no injection): EXTENT and OUTCOME per run, and the binding's code must equal Pi's (the same host
failure); the path must be an entry that remains.

Exit 0 iff every row is ready and passes. Usage:
  python div008_compare.py <matrix.json> <pi.jsonl> <binding.jsonl>
  python div008_compare.py --self-test"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def load(path: str) -> dict[tuple[str, int], dict]:
    rows = [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
    return {(row["id"], row.get("run", 1)): row for row in rows}


def first_settled(row: dict) -> tuple[str, str] | None:
    """(op, rel) of the first injected failure in the row's own call sequence."""
    for item in row["seq"]:
        if item.startswith("settle "):
            _, op, rel = item.split(" ", 2)
            return op, rel
    return None


def injected_code(spec: dict, op: str, rel: str) -> str | None:
    for q in spec.get("inject", []):
        if (q["op"], q["rel"]) == (op, rel):
            return q["code"]
    return None


def readiness(pi: dict, b: dict) -> list[str]:
    problems = []
    if pi.get("drained") is not True:
        problems.append("oracle: pinned Pi's in-flight removals did not drain")
    if pi.get("settle_incomplete"):
        problems.append("oracle: held failures were released by the timeout, not in the settlement order")
    if pi.get("unfired"):
        problems.append(f"oracle: planned injections never fired in Pi {pi['unfired']}")
    if b.get("drained") is not True:
        problems.append("binding: the observation did not drain")
    return problems


def check(spec: dict, codes: dict, pi: dict, b: dict) -> tuple[str, list[str]]:
    invalid = readiness(pi, b)
    if invalid:
        return "INVALID", invalid
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
    if b["result"] != "ok" and pi["result"] != "ok":
        own = first_settled(b)
        if own is None:  # natural row: a real host failure
            if b["result"] != pi["result"]:
                problems.append(f"selection: binding code {b['result']}, Pi {pi['result']} for the same host failure")
            if b["path"] is not None and not any(r.rstrip("/") == b["path"] for r in b["after_drain"]["remains"]):
                problems.append(f"selection: binding reports {b['path']}, which does not remain")
        else:
            op, rel = own
            want = codes.get(injected_code(spec, op, rel) or "")
            if b["path"] != rel:
                problems.append(f"selection: binding reports {b['path']}, but its first encountered failure is {rel}")
            if want is None or b["result"] != want:
                problems.append(f"selection: binding code {b['result']} for its first failure {op} {rel}, expected {want}")
        if pi["path"] != b["path"] or pi["result"] != b["result"]:
            verdict = "DIV-008"
    return ("FAIL" if problems else verdict), problems


def codes_agree_with_pi(matrix: dict, pi_rows: dict) -> list[str]:
    """The code table must equal pinned Pi's own reported code wherever Pi selected an injected failure."""
    specs = {r["id"]: r for r in matrix["rows"]}
    problems = []
    for (row_id, run), row in pi_rows.items():
        sel = first_settled(row)
        if row["result"] == "ok" or sel is None or row["path"] != sel[1]:
            continue
        injected = injected_code(specs[row_id], *sel)
        if matrix["codes"].get(injected) != row["result"]:
            problems.append(f"code table: {injected} -> {matrix['codes'].get(injected)}, Pi reports {row['result']} ({row_id} run {run})")
    return problems


def compare(matrix: dict, pi_rows: dict, b_rows: dict) -> int:
    specs = {r["id"]: r for r in matrix["rows"]}
    failed = 0
    for p in codes_agree_with_pi(matrix, pi_rows):
        print(f"{'INVALID':8} {p}")
        failed += 1
    for key in pi_rows:
        if key not in b_rows:
            print(f"{'MISSING':8} {key[0]} run {key[1]}")
            failed += 1
            continue
        verdict, problems = check(specs[key[0]], matrix["codes"], pi_rows[key], b_rows[key])
        print(f"{verdict:8} {key[0]} run {key[1]}: Pi {pi_rows[key]['path']} / binding {b_rows[key]['path']}")
        for p in problems:
            print(f"           {p}")
        failed += verdict in ("FAIL", "INVALID")
    for key in sorted(set(b_rows) - set(pi_rows)):
        print(f"{'EXTRA':8} {key[0]} run {key[1]}")
        failed += 1
    return failed


def self_test() -> int:
    """Controls on synthetic rows: each must get its intended verdict for its intended reason."""
    codes = {"EACCES": "permission_denied", "EBUSY": "unknown"}
    spec = {"id": "x", "inject": [{"op": "unlink", "rel": "tree/a", "nth": 1, "code": "EACCES"},
                                  {"op": "unlink", "rel": "tree/b", "nth": 1, "code": "EBUSY"}]}
    pi = {"id": "x", "run": 1, "result": "unknown", "path": "tree/b", "unfired": [], "late_calls": ["settle unlink tree/a"],
          "drained": True, "settle_incomplete": False,
          "seq": ["unlink tree/a", "unlink tree/b", "settle unlink tree/b", "settle unlink tree/a"],
          "after_drain": {"remains": ["tree/", "tree/a", "tree/b"]}}
    good = {"id": "x", "run": 1, "result": "permission_denied", "path": "tree/a", "unfired": [], "late_calls": [],
            "drained": True, "settle_incomplete": False,
            "seq": ["unlink tree/a", "settle unlink tree/a", "unlink tree/b", "settle unlink tree/b"],
            "after_drain": {"remains": ["tree/", "tree/a", "tree/b"]}}
    cases = [
        ("positive: first encountered with its code, extent equal", pi, good, "DIV-008", None),
        ("false first-settled claim: binding reports Pi's path", pi, {**good, "path": "tree/b", "result": "unknown"}, "FAIL", "selection: binding reports"),
        ("wrong code for the right own-first failure", pi, {**good, "result": "not_supported"}, "FAIL", "selection: binding code"),
        ("Pi's code borrowed for the own-first failure", pi, {**good, "result": "unknown"}, "FAIL", "selection: binding code"),
        ("stop at first failure: sibling skipped", pi, {**good, "unfired": ["unlink tree/b #1"], "seq": ["unlink tree/a", "settle unlink tree/a"]}, "FAIL", "complete:"),
        ("extent differs", pi, {**good, "after_drain": {"remains": ["tree/", "tree/a", "tree/b", "tree/m"]}}, "FAIL", "extent:"),
        ("late calls after return", pi, {**good, "late_calls": ["unlink tree/m"]}, "FAIL", "complete:"),
        ("outcome differs", pi, {**good, "result": "ok", "path": None}, "FAIL", "outcome:"),
        ("binding did not drain", pi, {**good, "drained": False}, "INVALID", "binding:"),
        ("oracle did not drain", {**pi, "drained": False}, good, "INVALID", "oracle:"),
        ("oracle settled by timeout", {**pi, "settle_incomplete": True}, good, "INVALID", "oracle:"),
        ("oracle injection unfired", {**pi, "unfired": ["unlink tree/b #1"]}, good, "INVALID", "oracle:"),
    ]
    bad = 0
    for name, p, row, expect, reason in cases:
        verdict, problems = check(spec, codes, p, row)
        ok = verdict == expect and (reason is None or any(x.startswith(reason) for x in problems))
        bad += not ok
        print(f"{'PASS' if ok else 'FAIL'} {name}: {verdict} (expected {expect}{', ' + reason if reason else ''})")
    # The code table is checked against the oracle: a table that disagrees with Pi is refused.
    table_bad = codes_agree_with_pi({"rows": [spec], "codes": {"EACCES": "permission_denied", "EBUSY": "permission_denied"}},
                                    {("x", 1): pi})
    ok = bool(table_bad)
    bad += not ok
    print(f"{'PASS' if ok else 'FAIL'} code table disagreeing with Pi is refused: {table_bad}")
    print("COMPARATOR SELFTEST " + ("PASSED" if not bad else f"FAILED ({bad})"))
    return 1 if bad else 0


def real_controls(matrix: dict, pi_rows: dict, b_rows: dict) -> int:
    """Controls on REAL rows (L12D008-C002): the baseline must pass unmodified; then each control changes one thing
    in a copy of an actual row and must get its intended verdict for its intended reason."""
    specs = {r["id"]: r for r in matrix["rows"]}
    if compare(matrix, pi_rows, b_rows):
        print("CONTROLS INVALID: the unmodified baseline does not pass")
        return 2
    target = next(k for k in b_rows if k[0].startswith("M3"))  # two injected codes; binding selects its own first
    spec, pi, b = specs[target[0]], pi_rows[target], b_rows[target]
    cases = [
        ("wrong code, right own-first failure", pi, {**b, "result": "not_supported"}, "FAIL", "selection: binding code"),
        ("the other injection's code for the own-first failure", pi,
         {**b, "result": next(c for c in matrix["codes"].values() if c != b["result"])}, "FAIL", "selection: binding code"),
        ("binding did not drain", pi, {**b, "drained": False}, "INVALID", "binding:"),
        ("oracle did not drain", {**pi, "drained": False}, b, "INVALID", "oracle:"),
        ("oracle settled by timeout", {**pi, "settle_incomplete": True}, b, "INVALID", "oracle:"),
    ]
    bad = 0
    print(f"controls on {target[0]} run {target[1]} (baseline passed)")
    for name, p, row, expect, reason in cases:
        verdict, problems = check(spec, matrix["codes"], p, row)
        ok = verdict == expect and any(x.startswith(reason) for x in problems)
        bad += not ok
        print(f"{'PASS' if ok else 'FAIL'} {name}: {verdict} (expected {expect}, {reason})")
    print("REAL-ROW CONTROLS " + ("PASSED" if not bad else f"FAILED ({bad})"))
    return 1 if bad else 0


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        raise SystemExit(self_test())
    if "--controls" in sys.argv:
        a = [x for x in sys.argv[1:] if x != "--controls"]
        m = json.loads(Path(a[0]).read_text(encoding="utf-8"))
        raise SystemExit(real_controls(m, load(a[1]), load(a[2])))
    matrix = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    raise SystemExit(1 if compare(matrix, load(sys.argv[2]), load(sys.argv[3])) else 0)
