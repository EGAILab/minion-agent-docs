"""Self-test for fs_guard.py: python fs_guard_check.py

Builds links INSIDE its own sandbox (some pointing outside) and only asks the guard about them; it
never writes, renames or deletes through any link, and deliberately does no cleanup."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fs_guard as g  # noqa: E402

sb = g.make_sandbox(os.path.join(g.PROJECT_ROOT, ".tmp", "fs-guard-check-py", f"run-{int(time.time() * 1000)}"))
outside = "C:\\fs-guard-check-never-created" if os.name == "nt" else "/fs-guard-check-never-created"
os.mkdir(os.path.join(sb, "d"))
os.symlink(outside, os.path.join(sb, "out-dangling"))
os.symlink("nothing-here", os.path.join(sb, "in-dangling"))
os.symlink("loop-b", os.path.join(sb, "loop-a"))
os.symlink("loop-a", os.path.join(sb, "loop-b"))
os.symlink("in-to-out", os.path.join(sb, "hop-out"))
os.symlink(outside, os.path.join(sb, "in-to-out"))
if os.name == "nt":
    import _winapi

    _winapi.CreateJunction("C:\\", os.path.join(sb, "j-out"))
else:
    os.symlink("/", os.path.join(sb, "j-out"), target_is_directory=True)

cases = [
    ("a" + "\\.." * 17, False), ("f:stream:bad", False), ("./f:stream:bad", True), ("E:", False), ("E:\\", False),
    ("C:/Users", False), ("\\\\server\\share", False), ("..", False), (".", False), ("sub/x", True),
    ("n" * 300, True), ("x<y", True), ("sub/../../x", False), ("d/f:s", True), ("d/new", True),
    ("out-dangling", False), ("in-dangling", True), ("loop-a", True), ("hop-out", False), ("j-out/x", False),
    ("d/../out-dangling", False),
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
for s in ["E:/", "C:/temp/x" if os.name == "nt" else "/tmp/x", g.PROJECT_ROOT, os.path.join(sb, "j-out", "x")]:
    try:
        g.make_sandbox(s)
        bad += 1
        print("FAIL sandbox allowed", s)
    except RuntimeError:
        print("PASS sandbox refused", s)
for o, want in [(os.path.join(sb, "result.json"), True), (os.path.join(sb, "out-dangling"), False),
                (outside, False), (os.path.join(sb, "j-out", "o.json"), False)]:
    try:
        g.assert_output(o)
        ok = True
    except RuntimeError:
        ok = False
    bad += ok != want
    print("PASS" if ok == want else "FAIL", "output", "allowed" if ok else "refused", o)
# L12D007-C001: through an outward junction, make_sandbox must refuse BEFORE any mkdir is reached.
from pathlib import Path  # noqa: E402

calls = []
real_mkdir = Path.mkdir
Path.mkdir = lambda self, *a, **k: calls.append(str(self)) or (_ for _ in ()).throw(OSError("intercepted mkdir"))
try:
    g.make_sandbox(os.path.join(sb, "j-out", "sandbox"))
    refused = False
except RuntimeError:
    refused = True
finally:
    Path.mkdir = real_mkdir
ok = refused and not calls
bad += not ok
print("PASS" if ok else "FAIL", f"make_sandbox through an outward junction refuses before mkdir (mkdir calls: {len(calls)})")
print(f"{bad} FAILED" if bad else "ALL PASS")
sys.exit(1 if bad else 0)
