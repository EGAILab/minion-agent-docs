"""L12-D006 (minion-agent#65 + #133-F1): the NUL-path cases, as `fs_path_domain` steps WITHOUT expectations
(pi_oracle.mjs fills them). Every case starts with the fixture steps (file `f` = "x", directory `d`), then
ONE operation on a NUL-containing path, then -- where pinned Pi has an observable side effect or leaves
state that must be unchanged -- a follow-up observation.

    python make_cases.py <out cases.json>
"""

import json
import sys


def u(text: str) -> list[int]:
    data = text.encode("utf-16-le", "surrogatepass")
    return [int.from_bytes(data[i : i + 2], "little") for i in range(0, len(data), 2)]


def p(text: str) -> dict:
    return {"utf16": u(text)}


NUL = "\x00"
PATHS = {
    "begin": f"{NUL}f",
    "middle": f"f{NUL}x",
    "end": f"f{NUL}",
    "under-new-parent": f"new/a{NUL}b",
    "in-parent-component": f"p{NUL}q/child",
    "lone-surrogate-and-nul": f"\ud800{NUL}z",
}
FIXTURE = [
    {"op": "write_file", "path": p("f"), "content": u("x")},
    {"op": "create_dir", "path": p("d"), "recursive": True},
]
CONTENT = u("w")


def case(case_id: str, *steps: dict) -> dict:
    return {"id": case_id, "steps": [*FIXTURE, *steps]}


cases = []
for where, text in PATHS.items():
    path = p(text)
    after_write = [{"op": "exists", "path": p("new")}] if where == "under-new-parent" else []
    cases += [
        case(f"nul/{where}/absolute_path", {"op": "absolute_path", "path": path}),
        case(f"nul/{where}/read_text_file", {"op": "read_text_file", "path": path}),
        case(f"nul/{where}/read_text_lines", {"op": "read_text_lines", "path": path}),
        case(f"nul/{where}/read_text_lines-max0", {"op": "read_text_lines", "path": path, "max_lines": 0}),
        case(f"nul/{where}/read_binary_file", {"op": "read_binary_file", "path": path}),
        case(f"nul/{where}/write_file", {"op": "write_file", "path": path, "content": CONTENT}, *after_write),
        case(f"nul/{where}/append_file", {"op": "append_file", "path": path, "content": CONTENT}, *after_write),
        case(f"nul/{where}/rename_file-source", {"op": "rename_file", "path": path, "to": p("g")}),
        case(f"nul/{where}/rename_file-destination", {"op": "rename_file", "path": p("f"), "to": path},
             {"op": "read_text_file", "path": p("f")}),
        case(f"nul/{where}/rename_file-both", {"op": "rename_file", "path": path, "to": path}),
        case(f"nul/{where}/file_info", {"op": "file_info", "path": path}),
        case(f"nul/{where}/exists", {"op": "exists", "path": path}),
        case(f"nul/{where}/list_dir", {"op": "list_dir", "path": path}),
        case(f"nul/{where}/canonical_path", {"op": "canonical_path", "path": path}),
        case(f"nul/{where}/target_key", {"op": "target_key", "path": path}),
        case(f"nul/{where}/create_dir", {"op": "create_dir", "path": path, "recursive": True}),
        case(f"nul/{where}/create_dir-nonrecursive", {"op": "create_dir", "path": path, "recursive": False}),
        case(f"nul/{where}/remove", {"op": "remove", "path": path}),
        case(f"nul/{where}/remove-recursive", {"op": "remove", "path": path, "recursive": True}),
        case(f"nul/{where}/remove-force", {"op": "remove", "path": path, "force": True}),
        case(f"nul/{where}/remove-recursive-force", {"op": "remove", "path": path, "recursive": True, "force": True}),
        # Minion operations (EXEC-007 / EXEC-008 / EXEC-009): pinned Node's own primitive
        # (readdir / lstat / access) rejects the argument; the oracle checks that rejection.
        case(f"nul/{where}/list_dir_raw", {"op": "list_dir_raw", "path": path}),
        case(f"nul/{where}/probe_dir_entry", {"op": "probe_dir_entry", "path": path}),
        case(f"nul/{where}/check_readable", {"op": "check_readable", "path": path}),
        case(f"nul/{where}/check_read_write", {"op": "check_read_write", "path": path}),
    ]
middle = p(PATHS["middle"])
cases += [
    # Abort precedence: a pre-aborted signal wins before any filesystem access (Pi's signal-taking operations).
    case("nul/aborted/read_text_file", {"op": "read_text_file", "path": middle, "aborted": True}),
    case("nul/aborted/read_text_lines", {"op": "read_text_lines", "path": middle, "aborted": True}),
    case("nul/aborted/read_text_lines-max0", {"op": "read_text_lines", "path": middle, "max_lines": 0, "aborted": True}),
    case("nul/aborted/read_binary_file", {"op": "read_binary_file", "path": middle, "aborted": True}),
    case("nul/aborted/write_file", {"op": "write_file", "path": p(PATHS["under-new-parent"]), "content": CONTENT,
                                    "aborted": True}, {"op": "exists", "path": p("new")}),
    case("nul/aborted/rename_file-source", {"op": "rename_file", "path": middle, "to": p("g"), "aborted": True}),
    case("nul/aborted/rename_file-destination", {"op": "rename_file", "path": p("f"), "to": middle, "aborted": True}),
    case("nul/aborted/list_dir", {"op": "list_dir", "path": middle, "aborted": True}),
]
with open(sys.argv[1], "w", encoding="utf-8") as handle:
    json.dump({"cases": cases}, handle, indent=1)
    handle.write("\n")
print(f"{len(cases)} cases")
