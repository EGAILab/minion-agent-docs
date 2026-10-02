"""L12-D001 tool-level inheritance document (conformance/agent/fs-path-domain/fs-path-tools.json): the REAL built-in
tools over a surrogate-bearing directory, so a binding that refuses the path, substitutes ".", or rewrites
tool-authored text fails (Owner decision FSP-Q001 sections 5, 9 and 19).

Expectation sources, stated per field:
    tool-authored text   pinned Pi's own templates, interpolating the `path` argument AS GIVEN:
                         write.ts:229 `Successfully wrote ${content.length} bytes to ${path}`,
                         edit.ts:380 `Successfully replaced ${edits.length} block(s) in ${path}.`
    read content / ls    the ctx.fs facts of the L12-D001 authority (fs-path-names / fs-path-alias): every spelling
                         reaches the one native file; listings report the PROJECTED name; ls appends '/' to a
                         directory (pinned Pi ls.ts) and lists the ADDRESSED directory.

    python make_tool_scenarios.py <target dir>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HI, LO, RC = 0xD800, 0xDC00, 0xFFFD
PAIR = [0xD83D, 0xDE00]
NAMES = {
    "pair": PAIR,
    "explicit-fffd": [0x61, RC],
    "lone-high-middle": [0x61, HI, 0x62],
    "lone-low-end": [0x61, LO],
    "mixed-pair-then-lone": PAIR + [HI],
}


def u(text: str) -> list[int]:
    return [ord(c) for c in text]


def projected(units: list[int]) -> list[int]:
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


def text(units: list[int]) -> dict:
    return {"utf16": units}


def build() -> list[dict]:
    cases = []
    for name, units in NAMES.items():
        directory = u("d") + units
        target = directory + u("/f.txt")
        alt = projected(directory) + u("/f.txt")
        cases.append({"id": f"tools/{name}", "steps": [
            {"tool": "write", "arguments": {"path": text(target), "content": text(u("content"))},
             "expect": {"is_error": False, "text": text(u("Successfully wrote 7 bytes to ") + target)}},
            {"tool": "read", "arguments": {"path": text(target)},
             "expect": {"is_error": False, "text": text(u("content"))}},
            {"tool": "read", "arguments": {"path": text(alt)},
             "expect": {"is_error": False, "text": text(u("content"))}},
            {"tool": "ls", "arguments": {"path": text(directory)},
             "expect": {"is_error": False, "text": text(u("f.txt"))}},
            {"tool": "edit", "arguments": {"path": text(target), "edits": [
                {"oldText": text(u("content")), "newText": text(u("changed"))}]},
             "expect": {"is_error": False, "text": text(u("Successfully replaced 1 block(s) in ") + target + u("."))}},
            {"tool": "read", "arguments": {"path": text(alt)},
             "expect": {"is_error": False, "text": text(u("changed"))}},
            {"tool": "ls", "arguments": {"path": text(u("."))},
             "expect": {"is_error": False, "text": text(projected(directory) + u("/"))}},
        ]})
    return cases


if __name__ == "__main__":
    out = Path(sys.argv[1])
    with open(out / "fs-path-tools.json", "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"name": "fs-path-tools", "family": "agent",
                   "authority": ("pinned Pi b7bb00b9 coding-agent tool templates (write.ts:229, edit.ts:380, ls.ts '/' "
                                 "suffix; path interpolated as given) + the L12-D001 ctx.fs authority facts"),
                   "pi_revision": "b7bb00b936dbe21b8e160b3e89efdec361846699",
                   "requirements": ["EXEC-002", "TOOL-025", "TOOL-028", "TOOL-029", "TOOL-030"],
                   "witnesses": ["fs_path_javascript_string_domain"], "platforms": ["linux", "win32"],
                   "notes": ("Layer-13 tools INHERIT the Layer-12 rule: a surrogate-bearing path reaches ctx.fs (no "
                             "refusal, no '.' substitution); tool-authored text keeps the path as given; reads via "
                             "the U+FFFD spelling reach the same file; listings show projected names. GENERATED; "
                             "regenerate with harness/make_tool_scenarios.py."),
                   "fs_path_tools": {"cases": build()}}, fh, indent=1)
        fh.write("\n")
    print(len(build()), "tool cases")
