"""L0506-D001 canonical scenarios (conformance/agent/prepared-runtime/, prepared-runtime-scenario.schema.json),
generated from the pinned-Pi authority run.

    python make_scenarios.py <cases.json> <authority.json> <out dir>

Every expectation is pinned Pi's: the outcome (prepared, or an argument-validation failure) and the token of each
observed prepared value. The runner additionally requires the pre-execute hook and (custom tools) execute to observe
the same token, and the raw ToolCall arguments to be unchanged.
"""
import json
import sys
from pathlib import Path

PI = "b7bb00b936dbe21b8e160b3e89efdec361846699"
AUTH = (f"pinned Pi {PI[:8]} agent-loop.ts prepareToolCall + ai/src/utils/validation.ts validateToolArguments "
        "(typebox 1.3.7) + edit.ts prepareEditArguments, under Node 22.15.1 (L0506-D001 authority)")
GROUPS = [
    ("edit", "prepared-runtime-edit-json-string-numbers",
     "The real pinned-Pi preparation path: edit's prepareEditArguments JSON-parses a string `edits`. An overflowing "
     "number becomes +/-Infinity, -0 keeps its sign, and a large integer is rounded to binary64. The value survives "
     "validation (an undeclared key of an edit item) and reaches the pre-execute hook; the edit itself applies."),
    ("number", "prepared-runtime-declared-number-field",
     "A tool's own prepare_arguments sets a declared {type: number} field. Pinned Pi's validator rejects +/-Infinity "
     "and NaN there (finite-only), and accepts -0 (sign kept) and large finite values."),
    ("integer", "prepared-runtime-declared-integer-field",
     "A tool's own prepare_arguments sets a declared {type: integer} field. Pinned Pi's validator rejects "
     "+/-Infinity and NaN, and accepts -0 (sign kept) and large finite integral values."),
    ("open", "prepared-runtime-undeclared-field",
     "A tool's own prepare_arguments sets a key the schema does not declare. Pinned Pi keeps every runtime number "
     "there -- +Infinity, -Infinity, NaN, -0 -- and the pre-execute hook and execute observe it."),
]


def q(s):
    out = ['"']
    for ch in s:
        o = ord(ch)
        if ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        elif 0x20 <= o < 0x7F:
            out.append(ch)
        elif o == 0x0A:
            out.append("\\n")
        else:
            out.append("\\u%04X" % o if o <= 0xFFFF else "\\U%08X" % o)
    out.append('"')
    return "".join(out)


def emit(v, ind=0):
    pad = "  " * ind
    if isinstance(v, dict):
        if not v:
            return "{}"
        return "\n".join(f"{pad}{k}:\n{emit(x, ind + 1)}" if isinstance(x, (dict, list)) and x
                         else f"{pad}{k}: {emit(x, ind + 1)}" for k, x in v.items())
    if isinstance(v, list):
        if not v:
            return "[]"
        lines = []
        for x in v:
            if isinstance(x, dict) and x:
                body = emit(x, ind + 1).split("\n")
                lines.append(f"{pad}- {body[0].lstrip()}")
                lines.extend(body[1:])
            else:
                lines.append(f"{pad}- {emit(x, ind + 1)}")
        return "\n".join(lines)
    if v is True:
        return "true"
    if v is False:
        return "false"
    if isinstance(v, int):
        return str(v)
    return q(v)


def main():
    cases = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    results = {r["id"]: r for r in json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))["results"]}
    out = Path(sys.argv[3])
    out.mkdir(parents=True, exist_ok=True)
    for key, name, notes in GROUPS:
        members = [c for c in cases if (c["tool"] == "edit") == (key == "edit") and c.get("schema", "edit") in (key, "edit")]
        docs_cases = []
        for c in members:
            r = results[c["id"]]
            case = {"id": c["id"], "tool": c["tool"]}
            if c["tool"] == "custom":
                case["schema"] = c["schema"]
                case["prepare_set"] = c["prepare_set"]
            case["arguments"] = c["arguments"]
            case["observe"] = c["observe"]
            if r["outcome"] == "prepared":
                expect = {"outcome": "prepared", "observed": r["observed"]}
                if c["tool"] == "edit":
                    expect["result_text"] = "Successfully replaced 1 block(s) in f.txt."
            else:
                expect = {"outcome": "argument_validation_failure"}
            case["expect"] = expect
            docs_cases.append(case)
        doc = {"name": name, "family": "agent", "authority": AUTH, "pi_revision": PI,
               "requirements": ["TOOL-041"], "witnesses": ["prepared_runtime_numeric_domain"],
               "notes": notes + " GENERATED from the pinned-Pi authority run; regenerate with harness/make_scenarios.py.",
               "prepared_runtime": {"cases": docs_cases}}
        (out / f"{name}.yaml").write_bytes((emit(doc) + "\n").encode("ascii"))
        print(name, len(docs_cases))


if __name__ == "__main__":
    main()
