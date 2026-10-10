"""CE-L12D007-01 permanent rejecting controls for fs_guard.py (python ce01_controls.py).
Runs ce01_suite.py against the REAL guard and each MUTANT (copies under a make_sandbox root; the
driver's own writes are REFERENT-guarded). Real must pass all; each mutant must be KILLED."""

import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fs_guard import PROJECT_ROOT, assert_inside, make_sandbox  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = open(os.path.join(HERE, "fs_guard.py"), encoding="utf-8").read()
SUITE = os.path.join(HERE, "ce01_suite.py")
work = make_sandbox(os.path.join(PROJECT_ROOT, ".tmp", "ce01-controls-py", f"run-{int(time.time() * 1000)}"))
MUTANTS = [
    ("1 budget-accept", '    raise RuntimeError(f"fs_guard: {what}: {BUDGET}-hop budget exhausted without a repeated state; refused")', "    return pending", ["budget_plus_one_contained_refused"]),
    ("2 catch-all-missing", "        raise RuntimeError(f\"fs_guard: cannot inspect {p} ({exc}); refused\") from exc", "        return None", ["ancestor_EACCES_refused"]),
    ("3 unchecked-last-hop", "        if not inside(redirected):\n            raise RuntimeError(f\"fs_guard: {what} reaches {redirected} through a link, outside {boundary}\")\n        pending = redirected\n    raise RuntimeError(f\"fs_guard: {what}: {BUDGET}-hop budget exhausted without a repeated state; refused\")",
     "        pending = redirected\n    return pending", ["last_hop_outward_refused"]),
    ("5 restore-without-proof", "    try:\n        target = assert_inside(sandbox, rel)\n        st = _inspect(target)", "    try:\n        restore(rel)\n        return True\n        target = assert_inside(sandbox, rel)\n        st = _inspect(target)", ["f_restore_missing_skipped"]),
    ("6 tool-traversal-cleanup", "        clean(root)\n        os.rmdir(root)", "        subprocess.run([\"icacls\", root, \"/reset\", \"/T\", \"/C\", \"/Q\"])\n        os.rmdir(root)", ["c_cleanup_removes_link_as_entry_only"]),
    ("8 parent-only-everywhere", "    lexical = _lexical(sandbox, target, cwd)\n    _prove(lexical, sandbox, repr(target))\n    return lexical", "    return assert_entry(sandbox, target, cwd)", ["a_referent_through_outward_link_refused"]),
    ("9 follow-final-in-cleanup", "                if _is_link(st):\n                    _remove_link_entry(child)\n                    continue", "                if _is_link(st):\n                    clean(child)\n                    _remove_link_entry(child)\n                    continue", ["c_cleanup_removes_link_as_entry_only"]),
    ("11 logical-not-native", "    pending = os.path.abspath(project(target))", "    pending = os.path.abspath(target)", ["e_projection_alias_refused"]),
    ("12 restore-on-absence", '        if st is None:\n            log(f"fs_guard: restore skipped, {rel!r} is missing")\n            return False', "        if st is None:\n            restore(target)\n            return True", ["f_restore_missing_skipped"]),
    ("13 windows-keeps-surrogate", "    return text.encode(\"utf-16-le\", \"surrogatepass\").decode(\"utf-16-le\", \"replace\")",
     "    if sys.platform == \"win32\":\n        return text\n    return text.encode(\"utf-16-le\", \"surrogatepass\").decode(\"utf-16-le\", \"replace\")",
     ["e_projection_alias_refused"] if sys.platform == "win32" else []),
]


def variant(name, old, new):
    d = assert_inside(work, "".join(c if c.isalnum() else "-" for c in name))
    os.mkdir(d)
    text = SRC
    if old:
        if text.count(old) != 1:
            raise SystemExit(f"mutant anchor: {name}")
        text = text.replace(old, new)
    with open(assert_inside(work, os.path.relpath(os.path.join(d, "fs_guard.py"), work)), "w", encoding="utf-8") as f:
        f.write(text)
    return d


def run(d):
    p = subprocess.run([sys.executable, SUITE, d, os.path.join(d, "virtual")], capture_output=True, text=True)
    lines = p.stdout.strip().splitlines()
    if p.returncode != 0 or not lines or not lines[-1].startswith("{"):
        return {"__crash": f"{p.returncode} {p.stderr[-400:]}"}
    return json.loads(lines[-1])


bad = 0
real = run(variant("real", None, None))
failing = [k for k, v in real.items() if v is not True]
print(f"FAIL real guard: {failing}" if failing else f"PASS real guard: all {len(real)} controls hold")
bad += bool(failing)
for name, old, new, expect in MUTANTS:
    if not expect:
        print(f"SKIP {name} (platform-specific)")
        continue
    res = run(variant(name, old, new))
    killed = "__crash" not in res and all(res.get(k) is False for k in expect)
    bad += not killed
    print(f"{'KILLED' if killed else 'NOT KILLED'} {name} by {', '.join(expect)}" + (f" ({res['__crash']})" if "__crash" in res else ""))
print(f"{bad} FAILED" if bad else "ALL PASS")
sys.exit(1 if bad else 0)
