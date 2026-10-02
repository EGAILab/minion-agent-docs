"""L12-D001 cases (minion-agent#123; Owner decision FSP-Q001): step programs over a fresh, realpath'd working
directory, executed by the pinned-Pi authority (l12_probe.mjs) and by each binding's canonical runner.

A path is {"utf16": [code units]} relative to the working directory, '/'-separated (both Node and Minion accept '/'
on Windows), or {"file_url_tail": [code units]} -- a file:// URL formed from the working directory's own file URL
plus that tail (fixture construction only). Operations are the Layer-12 ctx.fs seam (Pi harness NodeExecutionEnv)
plus target_key (Pi coding-agent getMutationQueueKey == Minion's FsTarget derivation):

    write_file(path, content)   read_text_file(path)   list_dir(path)   canonical_path(path)
    absolute_path(path)         target_key(path)       exists(path)     file_info(path)

and, for the error-origin cases (L12-D001-R001: WHICH path an OS-originated failure names):

    append_file(path, content)  read_text_lines(path)  read_binary_file(path)
    create_dir(path, recursive) remove(path)           rename_file(path, to)

An error-origin case may carry `platforms` when a recorded Layer-12 finding makes a binding's answer on the other
platform differ from pinned Pi for a reason outside this delta (`platform_note` names it).

    python make_cases.py <cases.json>
"""

from __future__ import annotations

import json
import sys

HI, LO, RC = 0xD800, 0xDC00, 0xFFFD
PAIR = [0xD83D, 0xDE00]
NAMES = {
    "bmp": [0xE9],
    "pair": PAIR,
    "explicit-fffd": [0x61, RC],
    "lone-high-start": [HI, 0x61],
    "lone-high-middle": [0x61, HI, 0x62],
    "lone-high-end": [0x61, HI],
    "lone-low-start": [LO, 0x61],
    "lone-low-middle": [0x61, LO, 0x62],
    "lone-low-end": [0x61, LO],
    "mixed-pair-then-lone": PAIR + [HI],
    "low-then-high": [LO, HI],
}


def u(text: str) -> list[int]:
    return [ord(c) for c in text]


def p(*parts: list[int]) -> dict:
    out: list[int] = []
    for i, part in enumerate(parts):
        if i:
            out.append(0x2F)
        out += part
    return {"utf16": out}


def fffd(units: list[int]) -> list[int]:
    """The explicit U+FFFD spelling of a name: each unpaired surrogate replaced (a fixture, not an expectation)."""
    out, i = [], 0
    while i < len(units):
        c = units[i]
        if 0xD800 <= c <= 0xDBFF and i + 1 < len(units) and 0xDC00 <= units[i + 1] <= 0xDFFF:
            out += units[i:i + 2]
            i += 2
            continue
        out.append(RC if 0xD800 <= c <= 0xDFFF else c)
        i += 1
    return out


def step(op: str, path: dict, **extra) -> dict:
    return {"op": op, "path": path, **extra}


def build() -> list[dict]:
    cases = []
    for name, units in NAMES.items():
        for position in ("file", "dir"):
            if position == "file":
                target, alt, listed = p(u("f") + units + u(".txt")), p(u("f") + fffd(units) + u(".txt")), p(u("."))
            else:
                target = p(u("d") + units, u("f.txt"))
                alt = p(u("d") + fffd(units), u("f.txt"))
                listed = p(u("d") + units)
            cases.append({"id": f"{position}/{name}", "steps": [
                step("target_key", target),
                step("write_file", target, content=u("content")),
                step("read_text_file", target),
                step("read_text_file", alt),
                step("list_dir", p(u("."))),
                *([step("list_dir", listed)] if position == "dir" else []),
                step("canonical_path", target),
                step("target_key", target),
                step("absolute_path", target),
                step("exists", target),
                step("file_info", target),
            ]})
            missing = p(u("missing") + units + u(".txt")) if position == "file" else p(u("m") + units, u("f.txt"))
            cases.append({"id": f"missing/{position}/{name}", "steps": [
                step("read_text_file", missing),
                step("canonical_path", missing),
                step("target_key", missing),
                step("absolute_path", missing),
                step("exists", missing),
                step("list_dir", missing),
            ]})
    for position in ("file", "dir"):
        spell = (lambda c: p(u("a") + [c])) if position == "file" else (lambda c: p(u("d") + [c], u("f.txt")))
        a, b, c = spell(HI), spell(LO), spell(RC)
        cases.append({"id": f"alias/{position}", "steps": [
            step("target_key", a), step("target_key", b), step("target_key", c),
            step("write_file", a, content=u("first")),
            step("read_text_file", a), step("read_text_file", b), step("read_text_file", c),
            step("target_key", a), step("target_key", b), step("target_key", c),
            step("write_file", b, content=u("second")),
            step("read_text_file", a), step("read_text_file", b), step("read_text_file", c),
            step("list_dir", p(u("."))),
            step("canonical_path", a), step("canonical_path", b), step("canonical_path", c),
        ]})
    for name, tail in {
        "raw-lone-high": u("a") + [HI], "raw-lone-low": u("a") + [LO], "raw-pair": u("a") + PAIR,
        "raw-mixed": u("a") + PAIR + [LO], "pct-fffd": u("a%EF%BF%BD"), "pct-astral": u("a%F0%9F%98%80"),
    }.items():
        url = {"file_url_tail": tail}
        cases.append({"id": f"file-url/{name}", "steps": [
            step("absolute_path", url), step("write_file", url, content=u("url")), step("list_dir", p(u("."))),
            step("canonical_path", url), step("target_key", url),
        ]})
    for name, tail in {"pct-lone-high": u("a%ED%A0%80"), "pct-lone-low": u("a%ED%B0%80"),
                       "pct-truncated": u("a%F0%9F"), "pct-overlong": u("a%C0%AF")}.items():
        # Malformed: the harness keeps the literal URL string as an ordinary path (certified L12 rule); only the
        # last component is platform-neutral, so that is all the case observes.
        cases.append({"id": f"file-url/{name}", "steps": [step("absolute_path", {"file_url_tail": tail},
                                                                observe="last_component")]})
    cases += error_origin_cases()
    ids = [c["id"] for c in cases]
    assert len(ids) == len(set(ids))
    return cases


WIN_DIRECTORY_OPEN = ("win32 excluded: opening a directory as a file is refused on Windows before Node's own EISDIR, "
                      "the recorded Layer-12 finding minion-agent#67 (code and, where Node's error has no path, path)")


def error_origin_cases() -> list[dict]:
    """L12-D001-R001: for each OS-originated failure, the path pinned Pi's toFileError reports -- Node's err.path,
    i.e. the path of the native call that failed (a parent or an ancestor, a rename's source), else the logical
    fallback -- for an ordinary name and for a name with an unpaired surrogate. `remove` of a directory is not
    here: its code is the separately recorded L12 finding (Pi `unknown`, both bindings `is_directory`)."""
    cases = []
    for variant, n in {"scalar": u("b"), "lone": u("a") + [HI]}.items():
        x, y, child = u("x"), u("y"), u("child")
        blocker = step("write_file", p(n), content=u("c"))
        directory = step("create_dir", p(n), recursive=True)
        src = step("write_file", p(u("src")), content=u("s"))
        programs = {
            "parent-file/write": [blocker, step("write_file", p(n, child), content=u("c"))],
            "parent-file/append": [blocker, step("append_file", p(n, child), content=u("c"))],
            "grandparent-file/write": [blocker, step("write_file", p(n, x, child), content=u("c"))],
            "grandparent-file/append": [blocker, step("append_file", p(n, x, child), content=u("c"))],
            "parent-file/create-dir": [blocker, step("create_dir", p(n, x), recursive=True)],
            "grandparent-file/create-dir": [blocker, step("create_dir", p(n, x, y), recursive=True)],
            "self-file/create-dir": [blocker, step("create_dir", p(n), recursive=True)],
            "parent-file/create-dir-nonrecursive": [blocker, step("create_dir", p(n, x), recursive=False)],
            "missing-parent/create-dir-nonrecursive": [step("create_dir", p(n, x), recursive=False)],
            "parent-file/read": [blocker, step("read_text_file", p(n, child))],
            "parent-file/read-lines": [blocker, step("read_text_lines", p(n, child))],
            "parent-file/read-binary": [blocker, step("read_binary_file", p(n, child))],
            "parent-file/file-info": [blocker, step("file_info", p(n, child))],
            "parent-file/exists": [blocker, step("exists", p(n, child))],
            "parent-file/canonical": [blocker, step("canonical_path", p(n, child))],
            "parent-file/remove": [blocker, step("remove", p(n, child))],
            "self-file/list-dir": [blocker, step("list_dir", p(n))],
            "missing/read-lines": [step("read_text_lines", p(n))],
            "missing/read-binary": [step("read_binary_file", p(n))],
            "missing/file-info": [step("file_info", p(n))],
            "missing/remove": [step("remove", p(n))],
            "missing-parent/canonical": [step("canonical_path", p(n, x))],
            "rename/missing-source": [step("rename_file", p(n), to=p(u("dst")))],
            "rename/missing-source-named-dest": [step("rename_file", p(u("src")), to=p(n))],
            "rename/dest-parent-file": [src, blocker, step("rename_file", p(u("src")), to=p(n, child))],
            "rename/dest-parent-missing": [src, step("rename_file", p(u("src")), to=p(n, child))],
            "rename/source-parent-file": [blocker, step("rename_file", p(n, child), to=p(u("dst")))],
            "rename/dest-nonempty-dir": [src, step("write_file", p(n, u("f")), content=u("c")),
                                        step("rename_file", p(u("src")), to=p(n))],
        }
        linux_only = {
            "self-dir/write": [directory, step("write_file", p(n), content=u("c"))],
            "self-dir/append": [directory, step("append_file", p(n), content=u("c"))],
            "self-dir/read": [directory, step("read_text_file", p(n))],
            "self-dir/read-lines": [directory, step("read_text_lines", p(n))],
            "self-dir/read-binary": [directory, step("read_binary_file", p(n))],
        }
        for name, steps in programs.items():
            cases.append({"id": f"error/{variant}/{name}", "steps": steps})
        for name, steps in linux_only.items():
            cases.append({"id": f"error/{variant}/{name}", "platforms": ["linux"], "platform_note": WIN_DIRECTORY_OPEN,
                          "steps": steps})
    return cases


if __name__ == "__main__":
    with open(sys.argv[1], "w", encoding="utf-8", newline="\n") as fh:
        json.dump(build(), fh, indent=1)
        fh.write("\n")
