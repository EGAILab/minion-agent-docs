"""L12-D008 / DIV-008 acceptance comparator v3 (CE-L12D008-01, agreed checkpoint #215 issuecomment-6122626197):
pinned Pi's rows (div008-pi-probe.mjs) against a binding's rows (div008_py_probe.py or the Rust equivalent), same
matrix, same platform.

Trace grammar (both probes): a call `op rel`; an injected fault `settle op rel CODE`; a native failure
`fail op rel CODE` (raw native codes are per-layer provenance labels, never compared across runtimes).

R1  DECLARATIONS, verified against pinned Pi on every row (INVALID otherwise). Each injection declares `outcome`
    terminal|recovered; each natural row declares its terminal `signature` {op, code}. (a) Pi's reported failure is
    a declared-terminal injection (or a native failure matching the signature) with the code table's code for it;
    (b) a row whose injections are all recovered is ok in Pi; (c) a terminal injection's entry remains in Pi's
    drained state; a recovered injection's entry does not, unless it is the ancestor of a remaining entry;
    (d) a natural row's Pi path is the rel of a matching `fail` event in Pi's trace.
R2  COMPLETE TRACES BY ROW KIND (INVALID otherwise). The kind comes from the matrix, never from the trace.
    Controlled: the multiset of `settle` events equals the fired injections (injections minus `unfired`), each with
    its matrix code -- no omission, forgery or duplication. Natural: at least one matching `fail` event.
R3  SELECTION. Controlled: the first `settle` of a declared-terminal injection in the binding's OWN trace, with
    `codes[code]`; natural: the first `fail` matching the signature, with `codes[signature.code]`. Recovered faults
    and routine native failures are never selected. The binding must report that origin and code. A selection
    different from Pi's is DIV-008 (selection/timing only), never a code or origin latitude.
R4  READINESS (INVALID: an oracle that did not drain, settled by the timeout, or left an injection unfired; a binding
    that did not drain), EXTENT against Pi's drained state, COMPLETENESS (no binding-only unfired injection, no late
    calls), OUTCOME agreement.

Exit 0 iff every row is ready, valid and passes. Usage:
  python div008_compare.py <matrix.json> <pi.jsonl> <binding.jsonl>
  python div008_compare.py --controls <matrix.json> <pi.jsonl> <binding.jsonl>
  python div008_compare.py --self-test"""

from __future__ import annotations

import copy
import json
import sys
from collections import Counter
from pathlib import Path


def load(path: str) -> dict[tuple[str, int], dict]:
    rows = [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
    return {(row["id"], row.get("run", 1)): row for row in rows}


def events(row: dict, kind: str) -> list[tuple[str, str, str]]:
    """(op, rel, code) of every `settle` or `fail` event, in trace order."""
    out = []
    for item in row["seq"]:
        parts = item.split(" ")
        if parts[0] == kind and len(parts) == 4:
            out.append((parts[1], parts[2], parts[3]))
    return out


def natural(spec: dict) -> bool:
    return not spec.get("inject")


def remains_has(remains: list[str], rel: str) -> bool:
    return any(r.rstrip("/") == rel for r in remains)


def ancestor_of_remaining(remains: list[str], rel: str) -> bool:
    return any(r.rstrip("/").startswith(rel + "/") for r in remains)


def selection(spec: dict, codes: dict, row: dict) -> tuple[str, str] | None:
    """R3: (origin rel, code) of the row's own first terminal failure, or None."""
    if natural(spec):
        sig = spec["signature"]
        for op, rel, _ in events(row, "fail"):
            if op == sig["op"]:
                return rel, codes[sig["code"]]
        return None
    terminal = {(q["op"], q["rel"]): q["code"] for q in spec["inject"] if q["outcome"] == "terminal"}
    for op, rel, code in events(row, "settle"):
        if (op, rel) in terminal:
            return rel, codes[terminal[(op, rel)]]
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


def trace_problems(spec: dict, row: dict, side: str) -> list[str]:
    """R2, by the matrix row's kind."""
    if natural(spec):
        sig = spec["signature"]
        if not any(op == sig["op"] for op, _, _ in events(row, "fail")):
            return [f"trace: {side} has no native {sig['op']} failure for the natural signature"]
        return []
    unfired = set(row.get("unfired", []))
    expected = Counter((q["op"], q["rel"], q["code"]) for q in spec["inject"]
                       if f"{q['op']} {q['rel']} #{q['nth']}" not in unfired)
    observed = Counter(events(row, "settle"))
    if observed != expected:
        return [f"trace: {side} settlements {sorted(observed.elements())} != fired injections {sorted(expected.elements())}"]
    return []


def declaration_problems(spec: dict, codes: dict, pi: dict) -> list[str]:
    """R1: the row's declarations against pinned Pi."""
    problems = []
    remains = pi["after_drain"]["remains"]
    if natural(spec):
        if pi["result"] != "ok":
            sig = spec["signature"]
            if not any(op == sig["op"] and rel == pi["path"] for op, rel, _ in events(pi, "fail")):
                problems.append(f"declaration: Pi's origin {pi['path']} is not a native {sig['op']} failure")
            if pi["result"] != codes[sig["code"]]:
                problems.append(f"declaration: Pi reports {pi['result']}, the signature's code is {codes[sig['code']]}")
        return problems
    terminal = [q for q in spec["inject"] if q["outcome"] == "terminal"]
    recovered = [q for q in spec["inject"] if q["outcome"] == "recovered"]
    if not terminal and pi["result"] != "ok":
        problems.append(f"declaration: every injection is recovered, but Pi reports {pi['result']}")
    if pi["result"] != "ok":
        chosen = [q for q in terminal if q["rel"] == pi["path"]]
        if not chosen:
            problems.append(f"declaration: Pi's selected failure {pi['path']} is not a declared-terminal injection")
        elif pi["result"] != codes[chosen[0]["code"]]:
            problems.append(f"declaration: Pi reports {pi['result']} for {pi['path']}, the table says {codes[chosen[0]['code']]}")
    for q in terminal:
        if not remains_has(remains, q["rel"]):
            problems.append(f"declaration: terminal {q['op']} {q['rel']} but the entry is removed in Pi")
    for q in recovered:
        if remains_has(remains, q["rel"]) and not ancestor_of_remaining(remains, q["rel"]):
            problems.append(f"declaration: recovered {q['op']} {q['rel']} but the entry remains in Pi")
    return problems


def check(spec: dict, codes: dict, pi: dict, b: dict) -> tuple[str, list[str]]:
    invalid = (readiness(pi, b) + trace_problems(spec, pi, "oracle") + trace_problems(spec, b, "binding")
               + declaration_problems(spec, codes, pi))
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
        own = selection(spec, codes, b)
        if own is None:
            problems.append("selection: the binding's trace has no terminal failure for its reported error")
        else:
            if b["path"] != own[0]:
                problems.append(f"selection: binding reports {b['path']}, its first terminal failure is {own[0]}")
            if b["result"] != own[1]:
                problems.append(f"selection: binding code {b['result']} for its first terminal failure {own[0]}, expected {own[1]}")
        if (pi["path"], pi["result"]) != (b["path"], b["result"]):
            verdict = "DIV-008"
    return ("FAIL" if problems else verdict), problems


def compare(matrix: dict, pi_rows: dict, b_rows: dict, quiet: bool = False) -> int:
    specs = {r["id"]: r for r in matrix["rows"]}
    failed = 0
    for key in pi_rows:
        if key not in b_rows:
            print(f"{'MISSING':8} {key[0]} run {key[1]}")
            failed += 1
            continue
        verdict, problems = check(specs[key[0]], matrix["codes"], pi_rows[key], b_rows[key])
        if not quiet:
            print(f"{verdict:8} {key[0]} run {key[1]}: Pi {pi_rows[key]['path']} / binding {b_rows[key]['path']}")
            for p in problems:
                print(f"           {p}")
        failed += verdict in ("FAIL", "INVALID")
    for key in sorted(set(b_rows) - set(pi_rows)):
        print(f"{'EXTRA':8} {key[0]} run {key[1]}")
        failed += 1
    return failed


# ---- controls -------------------------------------------------------------------------------------------------

def _drop(row: dict, kind: str) -> dict:
    return {**row, "seq": [s for s in row["seq"] if not s.startswith(kind + " ")]}


def _controls(matrix: dict, pi_rows: dict, b_rows: dict) -> list[tuple[str, dict, dict, dict, str, str]]:
    """(name, spec, pi, binding, expected verdict, expected reason) built from REAL rows."""
    specs = {r["id"]: r for r in matrix["rows"]}
    out = []
    x1 = next((k for k in b_rows if k[0].startswith("X1")), None)
    if x1:
        spec, pi, b = specs[x1[0]], pi_rows[x1], b_rows[x1]
        rec = next(q for q in spec["inject"] if q["outcome"] == "recovered")
        first_settle = next(s for s in b["seq"] if s.startswith("settle "))
        out += [
            ("recovered fault selected", spec, pi, {**b, "path": rec["rel"], "result": matrix["codes"][rec["code"]]},
             "FAIL", "selection: binding reports"),
            ("controlled trace omitted", spec, pi, _drop(b, "settle"), "INVALID", "trace:"),
            ("settlement duplicated", spec, pi, {**b, "seq": b["seq"] + [first_settle]}, "INVALID", "trace:"),
            ("settlement code forged", spec, pi,
             {**b, "seq": [s.rsplit(" ", 1)[0] + " EIO" if s == first_settle else s for s in b["seq"]]}, "INVALID", "trace:"),
            ("oracle trace omitted", spec, _drop(pi, "settle"), b, "INVALID", "trace:"),
            ("wrong code, right terminal origin", spec, pi, {**b, "result": "not_supported"}, "FAIL", "selection: binding code"),
            ("binding did not drain", spec, pi, {**b, "drained": False}, "INVALID", "binding:"),
            ("oracle settled by timeout", spec, {**pi, "settle_incomplete": True}, b, "INVALID", "oracle:"),
        ]
        flipped = copy.deepcopy(spec)
        for q in flipped["inject"]:
            q["outcome"] = "terminal"
        out.append(("declaration contradicts Pi (recovered declared terminal)", flipped, pi, b, "INVALID", "declaration:"))
    n1 = next((k for k in b_rows if k[0].startswith("N1")), None)
    if n1:
        spec, pi, b = specs[n1[0]], pi_rows[n1], b_rows[n1]
        out += [
            ("natural origin is an ancestor", spec, pi, {**b, "path": "tree"}, "FAIL", "selection: binding reports"),
            ("natural trace has no matching failure", spec, pi, _drop(b, "fail"), "INVALID", "trace:"),
        ]
    return out


def run_controls(controls, codes: dict) -> int:
    bad = 0
    for name, spec, pi, row, expect, reason in controls:
        verdict, problems = check(spec, codes, pi, row)
        ok = verdict == expect and any(x.startswith(reason) for x in problems)
        bad += not ok
        print(f"{'PASS' if ok else 'FAIL'} {name}: {verdict} (expected {expect}, {reason})")
    return bad


def real_controls(matrix: dict, pi_rows: dict, b_rows: dict) -> int:
    if compare(matrix, pi_rows, b_rows, quiet=True):
        print("CONTROLS INVALID: the unmodified baseline does not pass")
        return 2
    controls = _controls(matrix, pi_rows, b_rows)
    print(f"baseline passed; {len(controls)} controls on real rows"
          + ("" if any(c[0].startswith("natural") for c in controls) else " (natural rows not on this platform)"))
    bad = run_controls(controls, matrix["codes"])
    print("REAL-ROW CONTROLS " + ("PASSED" if not bad else f"FAILED ({bad})"))
    return 1 if bad else 0


def self_test() -> int:
    codes = {"EACCES": "permission_denied", "EBUSY": "unknown"}
    spec = {"id": "X", "inject": [{"op": "lstat", "rel": "tree/a", "nth": 1, "code": "EACCES", "outcome": "recovered"},
                                  {"op": "unlink", "rel": "tree/b", "nth": 1, "code": "EBUSY", "outcome": "terminal"}]}
    base = {"run": 1, "unfired": [], "late_calls": [], "drained": True, "settle_incomplete": False,
            "after_drain": {"remains": ["tree/", "tree/b"]}}
    trace = ["rmdir tree", "fail rmdir tree ENOTEMPTY", "lstat tree/a", "settle lstat tree/a EACCES", "unlink tree/a",
             "lstat tree/b", "unlink tree/b", "settle unlink tree/b EBUSY"]
    pi = {**base, "result": "unknown", "path": "tree/b", "seq": trace}
    good = {**base, "result": "unknown", "path": "tree/b", "seq": trace}
    nspec = {"id": "N", "signature": {"op": "unlink", "code": "EACCES"}}
    nbase = {**base, "after_drain": {"remains": ["tree/", "tree/a/", "tree/a/locked"]}}
    ntrace = ["rmdir tree", "fail rmdir tree ENOTEMPTY", "unlink tree/a/locked", "fail unlink tree/a/locked EACCES"]
    npi = {**nbase, "result": "permission_denied", "path": "tree/a/locked", "seq": ntrace}
    nb = {**nbase, "result": "permission_denied", "path": "tree/a/locked", "seq": ntrace}
    flipped = copy.deepcopy(spec)
    flipped["inject"][0]["outcome"] = "terminal"
    removed = copy.deepcopy(spec)
    cases = [
        ("positive: recovered then terminal", spec, pi, good, "MATCH", None),
        ("positive: natural first matching failure", nspec, npi, nb, "MATCH", None),
        ("recovered fault selected", spec, pi, {**good, "path": "tree/a", "result": "permission_denied"}, "FAIL", "selection: binding reports"),
        ("wrong code, right terminal origin", spec, pi, {**good, "result": "not_supported"}, "FAIL", "selection: binding code"),
        ("controlled trace omitted", spec, pi, _drop(good, "settle"), "INVALID", "trace:"),
        ("settlement duplicated", spec, pi, {**good, "seq": trace + ["settle unlink tree/b EBUSY"]}, "INVALID", "trace:"),
        ("settlement code forged", spec, pi, {**good, "seq": [s.replace("EBUSY", "EIO") for s in trace]}, "INVALID", "trace:"),
        ("natural origin is an ancestor", nspec, npi, {**nb, "path": "tree"}, "FAIL", "selection: binding reports"),
        ("natural trace has no matching failure", nspec, npi, _drop(nb, "fail"), "INVALID", "trace:"),
        ("declaration: recovered declared terminal (entry removed in Pi)", flipped, pi, good, "INVALID", "declaration:"),
        ("declaration: Pi selects a recovered injection", removed, {**pi, "path": "tree/a", "result": "permission_denied"},
         good, "INVALID", "declaration:"),
        ("extent differs", spec, pi, {**good, "after_drain": {"remains": ["tree/", "tree/a", "tree/b"]}}, "FAIL", "extent:"),
        # An honest skip (the unattempted injection reported unfired, the trace consistent with it) is a
        # completeness FAIL, not a trace INVALID.
        ("stop at first failure: sibling skipped", spec, pi, {**good, "unfired": ["unlink tree/b #1"],
                                                               "seq": trace[:4]}, "FAIL", "complete:"),
        ("late calls after return", spec, pi, {**good, "late_calls": ["unlink tree/m"]}, "FAIL", "complete:"),
        ("outcome differs", spec, pi, {**good, "result": "ok", "path": None}, "FAIL", "outcome:"),
        ("binding did not drain", spec, pi, {**good, "drained": False}, "INVALID", "binding:"),
        ("oracle did not drain", spec, {**pi, "drained": False}, good, "INVALID", "oracle:"),
        ("oracle settled by timeout", spec, {**pi, "settle_incomplete": True}, good, "INVALID", "oracle:"),
        ("oracle injection unfired", spec, {**pi, "unfired": ["unlink tree/b #1"]}, good, "INVALID", "oracle:"),
    ]
    bad = 0
    for name, s, p, row, expect, reason in cases:
        verdict, problems = check(s, codes, p, row)
        ok = verdict == expect and (reason is None or any(x.startswith(reason) for x in problems))
        bad += not ok
        print(f"{'PASS' if ok else 'FAIL'} {name}: {verdict} (expected {expect}{', ' + reason if reason else ''})")
    print("COMPARATOR SELFTEST " + ("PASSED" if not bad else f"FAILED ({bad})"))
    return 1 if bad else 0


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        raise SystemExit(self_test())
    args = [a for a in sys.argv[1:] if a != "--controls"]
    m = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    if "--controls" in sys.argv:
        raise SystemExit(real_controls(m, load(args[1]), load(args[2])))
    raise SystemExit(1 if compare(m, load(args[1]), load(args[2])) else 0)
