"""Shared fixture for the WP141-I002 canonical_path characterization: builds the tree and lists the
probe paths (relative to the base). Run: python fixture.py <base>  -> prints the case list as JSON."""

import json
import os
import sys


def build(base: str) -> list[dict]:
    j = lambda *p: os.path.join(base, *p)  # noqa: E731
    os.makedirs(j("dir", "sub"), exist_ok=True)
    open(j("file"), "w").write("x")
    open(j("dir", "inner"), "w").write("x")
    os.symlink("file", j("link-file"))
    os.symlink("dir", j("link-dir"))
    os.symlink(j("file"), j("link-abs"))
    os.symlink("missing", j("dangling"))
    os.symlink("self", j("self"))
    os.symlink("cyc-b", j("cyc-a"))
    os.symlink("cyc-a", j("cyc-b"))
    os.symlink("..", j("dir", "up"))
    os.symlink("sub", j("dir", "down"))
    # chains: chain-N/0 -> 1 -> ... -> N -> file (N links before the file)
    for n in (39, 40, 41):
        d = j(f"chain-{n}")
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, "end"), "w").write("x")
        for k in range(n):
            os.symlink(str(k + 1) if k + 1 < n else "end", os.path.join(d, str(k)))
    # c01-style loop: loop/a/back -> .. ; probe a deep path through it
    os.makedirs(j("loop", "a"), exist_ok=True)
    os.symlink("..", j("loop", "a", "back"))
    os.makedirs(j("noperm", "inside"), exist_ok=True)
    open(j("noperm", "inside", "f"), "w").write("x")
    cases = [
        "file", "dir", "dir/", "dir/inner", "dir/sub/..", "dir/sub/../inner", "missing", "missing/x",
        "file/", "file/.", "file/..", "file/x", "dir//inner", "./file", "dir/../file",
        "link-file", "link-dir", "link-dir/inner", "link-dir/", "link-abs", "dangling", "dangling/x",
        "self", "self/x", "cyc-a", "cyc-b/x", "dir/up", "dir/up/file", "dir/up/dir/up/dir/inner",
        "dir/down/..", "link-dir/down/../inner", "link-file/",
        "chain-39/0", "chain-40/0", "chain-41/0",
        "loop/a/back/a/back/a/back/a/back/a/back/a/back/a/back/a/back/a/back/a/back/a",
        "/".join(["loop", "a"] + ["back", "a"] * 39), "/".join(["loop", "a"] + ["back", "a"] * 40),
        "/".join(["loop", "a"] + ["back", "a"] * 41),
        "x" * 300, "dir/" + "y" * 256, "/".join(["dir"] * 1100),
        "noperm/inside/f", "noperm/inside",
    ]
    return [{"rel": c} for c in cases]


if __name__ == "__main__":
    print(json.dumps(build(sys.argv[1])))
