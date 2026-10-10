"""Self-test for fs_guard.py: python fs_guard_check.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import fs_guard as g  # noqa: E402

sb = g.make_sandbox(os.path.join(g.PROJECT_ROOT, ".tmp", "claude-scratch", "guard-check-py"))
cases = [
    ("a" + "\\.." * 17, False), ("f:stream:bad", False), ("./f:stream:bad", True), ("E:", False), ("E:\\", False),
    ("C:/Users", False), ("\\\\server\\share", False), ("..", False), (".", False), ("sub/x", True),
    ("n" * 300, True), ("x<y", True), ("sub/../../x", False), ("d/f:s", True),
]
bad = 0
for t, want in cases:
    try:
        g.assert_inside(sb, t)
        ok = True
    except RuntimeError:
        ok = False
    bad += ok != want
    print("PASS" if ok == want else "FAIL", "allowed" if ok else "refused", repr(t[:40]))
for s in ["E:/", "C:/temp/x", g.PROJECT_ROOT]:
    try:
        g.make_sandbox(s)
        bad += 1
        print("FAIL sandbox allowed", s)
    except RuntimeError:
        print("PASS sandbox refused", s)
print(f"{bad} FAILED" if bad else "ALL PASS")
sys.exit(1 if bad else 0)
