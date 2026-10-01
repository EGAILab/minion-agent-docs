"""L0506-D002 canonical scenarios (minion-agent conformance/agent/prepared-runtime-string/,
conformance/schema/prepared-string-scenario.schema.json), generated from the pinned-Pi authority run.

    python make_scenarios.py <cases.json> <authority.json> <out dir>

Every Pi-derived expectation is pinned Pi's: the outcome (prepared, or an argument-validation failure) and the UTF-16
code units of each observed prepared value and key. The runner additionally requires the pre-execute hook and (custom
tools) execute to observe the same units, and the raw ToolCall arguments to be unchanged. The hook-replacement
document is the one exception: it witnesses Minion's own `Proceed(arguments=...)` extension, which pinned Pi has no
equivalent for, and its expectations are the contract's, not Pi's.
"""
import json
import sys
from pathlib import Path

PI = "b7bb00b936dbe21b8e160b3e89efdec361846699"
AUTH = (f"pinned Pi {PI[:8]} agent-loop.ts prepareToolCall/executePreparedToolCall/finalizeExecutedToolCall (sliced "
        "from source) + ai/src/utils/validation.ts validateToolArguments (typebox 1.3.7) + edit.ts "
        "prepareEditArguments, under Node 22.15.1 (L0506-D002 authority)")
GATE_NOTE_EDIT = (" Gate WP-13.2: an integration witness through the real built-in edit tool; not part of the delta's "
                  "certification gate -- WP-13.2's Rust implementation review runs it once L0506-D002 is certified. "
                  "The final file bytes are the UTF-8 projection of the prepared newText followed by the fixture's "
                  "\\n (fs.writeFile(path, text, \"utf-8\"): each unpaired surrogate code unit becomes EF BF BD).")
GROUPS = [
    ("open", ["open"], "prepared-string-undeclared-field",
     "A tool's own prepare_arguments sets a key the schema does not declare to each member of the Owner decision's "
     "string neighborhood. Pinned Pi keeps the exact UTF-16 code units -- lone high and low surrogates at every "
     "position, adjacent and reversed surrogates, valid pairs, the empty string and NUL -- and the pre-execute hook "
     "and execute observe them."),
    ("string", ["string"], "prepared-string-declared-type",
     "A declared {type: string} field. Every member of the neighborhood is a JavaScript string and validates as one; "
     "the prepared code units are unchanged."),
    ("length", ["min-length-2", "max-length-1"], "prepared-string-length-keywords",
     "minLength/maxLength count CODE POINTS (pinned Pi, typebox 1.3.7): a valid surrogate pair counts 1, and each "
     "unpaired surrogate code unit counts 1 -- so the pair passes maxLength 1, adjacent highs fail it."),
    ("pattern", ["pattern-one-char", "pattern-two-chars"], "prepared-string-pattern-keywords",
     "pattern is matched in Unicode mode: `.` matches a valid pair as one character and an unpaired surrogate as "
     "one character; NUL is a character."),
    ("equality", ["const-pair", "enum-lone"], "prepared-string-equality-keywords",
     "const/enum compare exact code-unit sequences: the pair constant matches only the pair, and the lone-high enum "
     "member matches only the lone high (not the replacement character, not the lone low)."),
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
            raise ValueError(f"non-ASCII text in a scenario: {s!r}")
    out.append('"')
    return "".join(out)


def flow(v):
    """A JSON-shaped value on one line (YAML flow style, ASCII only)."""
    if isinstance(v, dict):
        return "{" + ", ".join(f"{q(k)}: {flow(x)}" for k, x in v.items()) + "}"
    if isinstance(v, list):
        return "[" + ", ".join(flow(x) for x in v) + "]"
    if v is True or v is False:
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    return q(v)


def emit(v, ind=0):
    pad = "  " * ind
    if isinstance(v, dict):
        if not v:
            return "{}"
        lines = []
        for k, x in v.items():
            key = q(k) if k.startswith("/") or k.startswith("$") else k
            if isinstance(x, (dict, list)) and x and not _leaf(x):
                lines.append(f"{pad}{key}:\n{emit(x, ind + 1)}")
            else:
                lines.append(f"{pad}{key}: {flow(x) if isinstance(x, (dict, list)) else emit(x)}")
        return "\n".join(lines)
    if isinstance(v, list):
        lines = []
        for x in v:
            if isinstance(x, dict) and x:
                body = emit(x, ind + 1).split("\n")
                lines.append(f"{pad}- {body[0].lstrip()}")
                lines.extend(body[1:])
            else:
                lines.append(f"{pad}- {flow(x)}")
        return "\n".join(lines)
    return flow(v)


def _leaf(x):
    """Flow-style leaves: code-unit arrays, lists of them, and value objects ({utf16}/{$key})."""
    if isinstance(x, list):
        return all(isinstance(i, int) for i in x) or all(isinstance(i, list) for i in x)
    return "utf16" in x or "$key" in x


def custom_case(c, r):
    case = {"id": c["id"], "tool": "custom", "schema": c["schema"], "prepare_set": c["prepare_set"],
            "arguments": c["arguments"], "observe": c["observe"]}
    if c.get("observe_keys"):
        case["observe_keys"] = c["observe_keys"]
    case["expect"] = expect(c, r)
    return case


def expect(c, r):
    if r["outcome"] != "prepared":
        return {"outcome": "argument_validation_failure"}
    hook = r["hook"]
    assert hook == r["execute"] == r["after"] and r["same_object"], c["id"]
    out = {"outcome": "prepared", "observed": hook["values"]}
    if c.get("observe_keys"):
        out["observed_keys"] = hook["keys"]
    if c["tool"] == "edit":
        out["result_text"] = "Successfully replaced 1 block(s) in f.txt."
        out["file_utf8_hex"] = r["projections"]["/edits/0/newText"]["utf8_hex"] + "0a"
    return out


# Minion's own Proceed(arguments=...) extension (spec/tools.md Layer 06): the replacement carries the same string
# domain into execute. Not a Pi behavior -- these expectations are the contract's.
HI, LO, PAIR = 0xD800, 0xDC00, [0xD83D, 0xDE00]
REPLACEMENTS = [
    ("replace/lone-high-into-execute", {"/extra": {"utf16": [0x41]}}, {"/extra": {"utf16": [0x41, HI]}}),
    ("replace/lone-low-into-execute", {"/extra": {"utf16": [0x41]}}, {"/extra": {"utf16": [LO]}}),
    ("replace/pair-into-execute", {"/extra": {"utf16": [HI]}}, {"/extra": {"utf16": PAIR}}),
    ("replace/lone-key-into-execute", {"/extra": {"utf16": [0x41]}},
     {"/extra": {"utf16": [0x41]}, "/bag": {"$key": [LO, HI], "value": 1}}),
]


def replacement_cases():
    cases = []
    for cid, prepare_set, replace_set in REPLACEMENTS:
        units = lambda v: v["utf16"]  # noqa: E731
        hook = {p: units(v) for p, v in prepare_set.items()}
        execute = {p: units(v) for p, v in replace_set.items() if "utf16" in v}
        case = {"id": cid, "tool": "custom", "schema": "open", "prepare_set": prepare_set,
                "hook_replace_set": replace_set, "arguments": {"seed": "raw"}, "observe": sorted(hook)}
        exp = {"outcome": "prepared", "observed": hook, "execute_observed": execute}
        keys = {p: [v["$key"]] for p, v in replace_set.items() if "$key" in v}
        if keys:
            case["execute_observe_keys"] = sorted(keys)
            exp["execute_observed_keys"] = keys
        case["execute_observe"] = sorted(execute)
        case["expect"] = exp
        cases.append(case)
    return cases


def document(name, notes, gate, cases, authority=AUTH, witnesses=("prepared_runtime_string_domain",)):
    return {"name": name, "family": "agent", "authority": authority, "pi_revision": PI, "requirements": ["TOOL-041"],
            "witnesses": list(witnesses), "notes": notes, "gate": gate, "prepared_string": {"cases": cases}}


def main():
    cases = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    results = {r["id"]: r for r in json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))["results"]}
    out = Path(sys.argv[3])
    out.mkdir(parents=True, exist_ok=True)
    generated = " GENERATED from the pinned-Pi authority run; regenerate with harness/make_scenarios.py."
    docs = []
    for _key, kinds, name, notes in GROUPS:
        members = [custom_case(c, results[c["id"]]) for c in cases
                   if c["tool"] == "custom" and c["schema"] in kinds and "/" in c["id"]
                   and c["id"].split("/")[0] in kinds]
        docs.append(document(name, notes + generated, "L0506-D002", members))
    other = [custom_case(c, results[c["id"]]) for c in cases
             if c["tool"] == "custom" and c["id"].split("/")[0] in ("position", "key", "diagnostic")]
    docs.append(document(
        "prepared-string-positions-and-keys",
        "Positions other than a top-level property -- a nested object value, an array element, a lone high and a "
        "lone low in one call -- and the KEY domain: an object key holding a lone high, a lone low, a pair, a "
        "reversed pair or the empty string keeps its exact code units. diagnostic/lone-surrogates is rejected (Pi "
        "then serializes the prepared value only in its failure text, escaping each unpaired surrogate as \\udXXX); "
        "no hook or execute runs." + generated, "L0506-D002", other))
    docs.append(document(
        "prepared-string-hook-replacement",
        "Minion's own tools/pre-execute Proceed(arguments=...) replacement (spec/tools.md Layer 06; an intentional "
        "Minion extension pinned Pi's BeforeToolCallResult has no equivalent for) carries the same string domain: "
        "the hook observes the prepared value, and execute observes the replacement's exact code units, including "
        "unpaired surrogates in values and keys. CONTRACT expectations, not Pi's.",
        "L0506-D002", replacement_cases(),
        authority="Minion contract: spec/tools.md Layer 06 TOOL-041 (L0506-D002), Proceed(arguments=...) extension",
        witnesses=("prepared_runtime_string_domain", "pre_execute_replacement_string_domain")))
    edits = [{"id": c["id"], "tool": "edit", "arguments": c["arguments"], "observe": c["observe"],
              "expect": expect(c, results[c["id"]])} for c in cases if c["tool"] == "edit"]
    docs.append(document(
        "prepared-string-edit-json-string",
        "The real pinned-Pi preparation path: edit's prepareEditArguments JSON-parses a string `edits` whose newText "
        "is written with \\uXXXX escapes, producing every member of the neighborhood (JSON.parse combines a valid "
        "escaped pair, and keeps an unpaired escaped surrogate as a lone code unit). The pre-execute hook observes "
        "the exact code units; the edit applies." + GATE_NOTE_EDIT + generated, "WP-13.2", edits))
    for doc in docs:
        (out / f"{doc['name']}.yaml").write_bytes((emit(doc) + "\n").encode("ascii"))
        print(doc["name"], doc["gate"], len(doc["prepared_string"]["cases"]))


if __name__ == "__main__":
    main()
