"""L0506-D002 authority cases: the prepared runtime JavaScript STRING domain at the Layer-05/06 boundary.

    python make_cases.py <out.json>

Each case is one tool call through pinned Pi's own agent-loop preparation -> validation -> beforeToolCall -> execute
(-> afterToolCall). Strings are written as arrays of UTF-16 code units, so lone surrogates survive the JSON case file.

  custom  a tool whose own prepare_arguments (Pi's public AgentTool.prepareArguments shim) sets strings at JSON
          pointers, against a schema kind; gate L0506-D002.
  edit    the real pinned-Pi preparation path: edit's prepareEditArguments JSON-parses a string `edits` whose
          newText is written with \\uXXXX escapes; gate WP-13.2.
"""
import json
import sys

HI, LO, PAIR = 0xD800, 0xDC00, [0xD83D, 0xDE00]  # U+1F600 as a surrogate pair
A, B = 0x41, 0x42
# Owner decision (#49 comment 5924605017) section 2, every member
NEIGHBORHOOD = {
    "ascii": [A, B],
    "bmp": [0xE9, 0x4E2D],
    "pair": PAIR,
    "lone-high-start": [HI, A],
    "lone-high-middle": [A, HI, B],
    "lone-high-end": [A, HI],
    "lone-high-only": [HI],
    "lone-low-start": [LO, A],
    "lone-low-middle": [A, LO, B],
    "lone-low-end": [A, LO],
    "lone-low-only": [LO],
    "adjacent-highs": [HI, HI],
    "adjacent-lows": [LO, LO],
    "high-then-non-low": [HI, A],
    "low-then-high": [LO, HI],
    "pair-then-lone-high": [*PAIR, HI],
    "lone-low-then-pair": [LO, *PAIR],
    "empty": [],
    "nul": [0x00],
    "nul-middle": [A, 0x00, B],
}
# schema kinds that observe a string: none (undeclared), its type, its length in both directions, a Unicode-mode
# pattern counting one and two characters, and exact equality (const of a pair, enum of a lone high)
SCHEMA_KINDS = ["open", "string", "min-length-2", "max-length-1", "pattern-one-char", "pattern-two-chars",
                "const-pair", "enum-lone"]

cases = []


def custom(cid, schema, prepare_set, observe, observe_keys=()):
    case = {"id": cid, "tool": "custom", "schema": schema, "prepare_set": prepare_set, "arguments": {"seed": "raw"},
            "observe": list(observe)}
    if observe_keys:
        case["observe_keys"] = list(observe_keys)
    cases.append(case)


for name, units in NEIGHBORHOOD.items():
    for schema in SCHEMA_KINDS:
        field = "extra" if schema == "open" else "text"
        custom(f"{schema}/{name}", schema, {"/" + field: {"utf16": units}}, ["/" + field])

# positions other than a top-level property: a nested object value, an array element, two strings at once (a lone
# high and a lone low: one must not be mishandled differently from the other), and an object KEY
custom("position/nested-object-value", "open", {"/outer": {"inner": {"utf16": [A, HI]}}}, ["/outer/inner"])
custom("position/array-element", "open", {"/list": ["x", {"utf16": [LO, B]}]}, ["/list/0", "/list/1"])
custom("position/two-strings", "open", {"/high": {"utf16": [HI]}, "/low": {"utf16": [LO]}}, ["/high", "/low"])
for name in ("lone-high-only", "lone-low-only", "pair", "low-then-high", "empty"):
    custom(f"key/{name}", "open", {"/bag": {"$key": NEIGHBORHOOD[name], "value": 1}}, [], ["/bag"])

# Pi's failure diagnostic (the one place pinned Pi serializes the prepared value): a rejected call carrying lone
# surrogates, a pair and NUL in several positions
custom("diagnostic/lone-surrogates", "max-length-1",
       {"/text": {"utf16": [HI, HI]}, "/extra": {"utf16": [A, LO]}, "/pair": {"utf16": PAIR},
        "/nul": {"utf16": [0x00]}},
       ["/text", "/extra", "/pair", "/nul"])


def esc(units):
    return "".join("\\u%04x" % u for u in units)


for name, units in NEIGHBORHOOD.items():
    cases.append({"id": f"edit/{name}", "tool": "edit",
                  "arguments": {"path": "f.txt", "edits": '[{"oldText":"a","newText":"' + esc(units) + '"}]'},
                  "observe": ["/edits/0/newText"]})

with open(sys.argv[1], "w", encoding="utf-8", newline="\n") as handle:
    json.dump(cases, handle, indent=1)
    handle.write("\n")
print(f"{len(cases)} cases")
