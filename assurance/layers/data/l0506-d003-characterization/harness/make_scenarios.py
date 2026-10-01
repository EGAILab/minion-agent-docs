"""Generate the L0506-D003 canonical scenarios (minion-agent conformance/agent/tool-result-domain/) from this
characterization's pinned-Pi authority (out/result.json) and its cases (cases.json).

    python make_scenarios.py <cases.json> <out/result.json> <target dir>

Every expectation is Pi's own observation at that boundary, translated from the probe's tagged form into the shared
value grammar ({"utf16": units}, {"number": token}, {"$keys": [[units, value], ...]}, arrays, true/false/null).
`session` expects the in-memory ToolResultMessage value: Minion's certified Layer-03 log keeps and replays the live
value (MINION-002 / spec/session.md; the L0206-D002 mapping). Pi's own session-FILE projection is recorded per case as
`pi_session_file` -- evidence for a future persisted form, asserted by no current runner.

Excluded, with reasons recorded in the documents' notes:
    details-*-undefined         ADJ-2 (Python and Rust have no undefined; certified IR-L06-004 host mapping)
    details-top-scalar/null     ADJ-2 (top-level null vs absent details is the same unresolved host mapping;
                                nested null stays in the domain) -- L0506-D003-R001 re-scope
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PI = "b7bb00b936dbe21b8e160b3e89efdec361846699"
AUTHORITY = ("pinned Pi b7bb00b9 agent-loop.ts executeToolCalls/executeToolCallsSequential .. emitToolResultMessage "
             "(sliced, toolExecution sequential; a custom tool + afterToolCall) + coding-agent session-manager.ts "
             "`${JSON.stringify(entry)}\\n` / parseSessionEntries, under Node 22.15.1 (L0506-D003 result-domain probe)")


class Excluded(Exception):
    pass


def grammar(t):
    if "u" in t:
        return {"utf16": t["u"]}
    if "n" in t:
        return {"number": t["n"]}
    if "a" in t:
        return [grammar(x) for x in t["a"]]
    if "o" in t:
        return {"$keys": [[k, grammar(v)] for k, v in t["o"]]}
    if "undef" in t:
        raise Excluded
    return t["v"]


def boundary(b):
    return {"content": [grammar(x) for x in b["content"]], "details": grammar(b["details"]),
            "is_error": b["isError"]}


def case_doc(case, result):
    tool = case["tool"]
    if "throws" in tool:
        tool_out = {"throws": grammar(tool["throws"])}
    else:
        tool_out = {"returns": {"content": [grammar(tool["text"])], "details": grammar(tool["details"])}}
    hook = {"mode": case["hook"]["mode"]}
    if "text" in case["hook"]:
        hook["content"] = [grammar(case["hook"]["text"])]
    if "details" in case["hook"]:
        hook["details"] = grammar(case["hook"]["details"])
    if "message" in case["hook"]:
        hook["message"] = grammar(case["hook"]["message"])
    message = boundary(result["message"])
    return {
        "id": case["id"],
        "tool": tool_out,
        "hook": hook,
        "expect": {
            "hook": boundary(result["hook"]) if result["hook"] else None,
            "execution_end": boundary(result["end"]),
            "message": message,
            "session": {"content": message["content"], "details": message["details"]},
        },
        "pi_session_file": {
            "line_utf8_hex": result["persisted_utf8_hex"],
            "reload": {"content": [grammar(x) for x in result["reload"]["content"]],
                       "details": grammar(result["reload"]["details"])},
        },
    }


DOCUMENTS = [
    ("tool-result-string-domain",
     lambda i: i.startswith(("details-leaf/", "details-array/", "details-nested/", "details-top-string/", "text/")),
     "Result text and details strings are JavaScript Strings: 16 code-unit sequences (incl. lone high/low surrogates "
     "at any position, a valid pair, U+FFFD as a control) as a details leaf, an array element, a nested value, the "
     "whole top-level details, and the result text."),
    ("tool-result-key-domain", lambda i: i.startswith("details-key"),
     "Details object KEYS share the string domain (folded under the Owner decision's section 6). Enumeration ORDER is "
     "L0206-D001's (K1) and is not asserted: objects compare as key sets."),
    ("tool-result-number-domain", lambda i: i.startswith(("details-number/", "details-array-number/", "details-top-number/")),
     "Details numbers are binary64 incl. -0, +/-Infinity and NaN (NaN/+/-Infinity folded under the Owner decision's "
     "section 6; -0 a required witness). Pi's session FILE writes -0 as 0 and non-finite as null (pi_session_file)."),
    ("tool-result-scalar-shape", lambda i: i.startswith(("details-scalar/", "details-top-scalar/", "details-empty-")),
     "null/true/false as leaves; true/false as the whole top-level details; empty object and array. Absent/undefined "
     "details and a top-level null are excluded (ADJ-2: certified IR-L06-004 host mapping, not folded)."),
    ("tool-result-after-hook", lambda i: i.startswith(("hook-", "edit-witness/")),
     "The afterToolCall boundary: the hook observes the tool's own result; observe-only, same-values, {details: null} "
     "(Pi's `??` keeps the tool's details), replacement of details/text with domain values, and a throwing hook "
     "(createErrorToolResult text keeps its code units). edit-witness: the WP-13.2 edit result value (details "
     "diff/patch hold code unit D800) carried by a generic tool; its real-edit-tool gate is gate-wp132."),
    ("tool-result-failure", lambda i: i.startswith("tool-throws/"),
     "Failure conversion: a tool's thrown message becomes the result text (createErrorToolResult), code units kept, "
     "details {}."),
]


def main(cases_path, result_path, target):
    cases = {c["id"]: c for c in json.load(open(cases_path, encoding="utf-8"))}
    results = json.load(open(result_path, encoding="utf-8"))["results"]
    target = Path(target)
    target.mkdir(parents=True, exist_ok=True)
    placed, excluded, witness = set(), [], None
    docs = {name: [] for name, _, _ in DOCUMENTS}
    for result in results:
        rid = result["id"]
        if rid == "edit-witness/lone-high":
            witness = result
            case = {"id": rid, "tool": {"text": {"u": result["end"]["content"][0]["u"]},
                                        "details": result["end"]["details"]},
                    "hook": {"mode": "observe"}}
        else:
            case = cases[rid]
        try:
            if rid == "details-top-scalar/null":
                raise Excluded
            doc = case_doc(case, result)
        except Excluded:
            excluded.append(rid)
            continue
        for name, match, _ in DOCUMENTS:
            if match(rid):
                docs[name].append(doc)
                placed.add(rid)
                break
    assert placed | set(excluded) == {r["id"] for r in results}, "every result is placed or excluded"
    assert sorted(excluded) == ["details-array-undefined", "details-nested-undefined", "details-top-scalar/null",
                                "details-top-undefined"]
    for name, _, notes in DOCUMENTS:
        write(target / f"{name}.json", {
            "name": name, "family": "agent", "authority": AUTHORITY, "pi_revision": PI,
            "requirements": ["AI-006", "TOOL-005", "TOOL-017", "MINION-002"],
            "witnesses": ["tool_result_runtime_value_domain"],
            "notes": notes + " GENERATED from the pinned-Pi L0506-D003 probe; regenerate with harness/make_scenarios.py.",
            "tool_result_domain": {"cases": docs[name]},
        })
    w = witness
    write(target / "gate-wp132-edit-result.json", {
        "name": "gate-wp132-edit-result", "family": "agent",
        "authority": AUTHORITY.replace("(L0506-D003", "+ edit.ts prepareEditArguments / edit-diff.ts (sliced), diff "
                                       "8.0.4 (L0506-D003"),
        "pi_revision": PI, "requirements": ["TOOL-030", "AI-006"], "witnesses": ["tool_result_runtime_value_domain"],
        "gate": "WP-13.2",
        "notes": "The Owner decision's mandatory WP-13.2 witness (section 3) through the REAL edit tool: f.txt = \"a\\n\", "
                 "edits string [{\"oldText\":\"a\",\"newText\":\"\\ud800\"}]. The file holds EF BF BD 0A (UTF-8 "
                 "projection), while the result text, details.diff and details.patch keep code unit D800 at every "
                 "boundary. Runtime result value != filesystem encoding. GENERATED; regenerate with "
                 "harness/make_scenarios.py.",
        "tool_result_domain": {"cases": [{
            "id": "edit/lone-high-new-text",
            "edit": {"file_utf8_hex": "610a",
                     "arguments": {"path": "f.txt", "edits": {"utf16": [ord(c) for c in
                                   '[{"oldText":"a","newText":"\\ud800"}]']}}},
            "hook": {"mode": "observe"},
            "expect": {
                "hook": boundary(w["hook"]), "execution_end": boundary(w["end"]), "message": boundary(w["message"]),
                "session": {"content": boundary(w["message"])["content"], "details": boundary(w["message"])["details"]},
                "file_utf8_hex": w["file_utf8_hex"],
            },
            "pi_session_file": {"line_utf8_hex": w["persisted_utf8_hex"],
                                "reload": {"content": [grammar(x) for x in w["reload"]["content"]],
                                           "details": grammar(w["reload"]["details"])}},
        }]},
    })
    print({name: len(docs[name]) for name, _, _ in DOCUMENTS}, "+ gate 1; excluded", excluded)


def write(path, document):
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(document, fh, indent=1)
        fh.write("\n")


if __name__ == "__main__":
    main(*sys.argv[1:4])
