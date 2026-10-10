"""L12-D007 canonical case builder: the characterized condition x operation matrix (record section 2),
for the 16 Pi-derived operations only (the EXEC-007/008/009 primitives are preserved extensions, not
parity). Writes gen/cases.json in the fs_path_domain step grammar; pi_oracle.mjs computes expectations.

    python make_cases.py
"""

import json
import os

u = lambda s: {"utf16": [ord(c) for c in s]}  # noqa: E731  (BMP-only literals here)
w = lambda p, content="x": {"op": "write_file", "path": u(p), "content": [ord(c) for c in content]}  # noqa: E731
d = lambda p: {"op": "create_dir", "path": u(p), "recursive": True}  # noqa: E731

# condition -> (fixture steps, target, platforms)
BOTH, WIN = ["linux", "win32"], ["win32"]
CONDITIONS = {
    "missing": ([], "missing", BOTH),
    "file": ([w("f")], "f", BOTH),
    "directory-empty": ([d("d")], "d", BOTH),
    "directory-nonempty": ([d("d"), w("d/c")], "d", BOTH),
    "non-directory-component": ([w("f")], "f/x", BOTH),
    "symlink-loop": ([{"op": "make_symlink", "path": u("a"), "to": u("b")},
                      {"op": "make_symlink", "path": u("b"), "to": u("a")}], "a", BOTH),
    "name-too-long": ([], "n" * 300, BOTH),
    "invalid-name": ([], "x<y", WIN),
    "ntfs-stream-syntax": ([w("f")], "./f:stream:bad", WIN),
    "sharing-violation": ([w("f", "0123456789" * 10), {"op": "hold_exclusive", "path": u("f")}], "f", WIN),
    "lock-violation": ([w("f", "0123456789" * 10), {"op": "lock_range", "path": u("f")}], "f", WIN),
}


def operations(t):
    return {
        "read_text_file": [{"op": "read_text_file", "path": u(t)}],
        "read_text_lines": [{"op": "read_text_lines", "path": u(t)}],
        "read_binary_file": [{"op": "read_binary_file", "path": u(t)}],
        "write_file": [{"op": "write_file", "path": u(t), "content": [119]}],
        "append_file": [{"op": "append_file", "path": u(t), "content": [119]}],
        "rename_file-source": [{"op": "rename_file", "path": u(t), "to": u("renamed")}],
        "rename_file-onto": [w("src", "s"), {"op": "rename_file", "path": u("src"), "to": u(t)}],
        "file_info": [{"op": "file_info", "path": u(t)}],
        "exists": [{"op": "exists", "path": u(t)}],
        "list_dir": [{"op": "list_dir", "path": u(t)}],
        "canonical_path": [{"op": "canonical_path", "path": u(t)}],
        "create_dir-recursive": [{"op": "create_dir", "path": u(t), "recursive": True}],
        "create_dir-nonrecursive": [{"op": "create_dir", "path": u(t), "recursive": False}],
        "remove": [{"op": "remove", "path": u(t)}],
        "remove-recursive": [{"op": "remove", "path": u(t), "recursive": True}],
        "remove-force": [{"op": "remove", "path": u(t), "force": True}],
    }


cases = []
for condition, (fixture, target, platforms) in CONDITIONS.items():
    for op, steps in operations(target).items():
        cases.append({"id": f"errors/{condition}/{op}", "platforms": platforms, "steps": [*fixture, *steps]})

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cases.json")
with open(out, "w", encoding="utf-8", newline="\n") as f:
    json.dump({"cases": cases}, f, indent=1)
    f.write("\n")
print(f"{len(cases)} cases -> {out}")
