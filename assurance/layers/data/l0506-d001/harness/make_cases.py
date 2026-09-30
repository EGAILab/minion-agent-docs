"""L0506-D001 authority cases: the prepared runtime numeric domain at the Layer-05/06 boundary.

    python make_cases.py <out.json>

Each case is one tool call through preparation -> validation -> the pre-execute hook (-> execute).
`edit` cases use the real pinned-Pi preparation path (`prepareEditArguments`' JSON.parse of a string
`edits`); `custom` cases use a tool whose `prepare_arguments` sets a value (Pi's public
`AgentTool.prepareArguments` shim) against a declared-number, declared-integer or open schema.
Numbers are written as tokens: "+Infinity", "-Infinity", "-0", "NaN", or a decimal literal.
"""
import json
import sys

cases = []


def edit(cid, extra_token):
    edits = '{"oldText":"a","newText":"b","extra":' + extra_token + "}"
    cases.append({"id": cid, "tool": "edit", "arguments": {"path": "f.txt", "edits": edits},
                  "observe": ["/edits/0/extra"]})


def custom(cid, schema_kind, field, token):
    cases.append({"id": cid, "tool": "custom", "schema": schema_kind, "prepare_set": {field: token},
                  "arguments": {}, "observe": ["/" + field]})


# ---- the real Pi preparation path: JSON.parse inside prepareEditArguments
edit("edit-overflow-positive-exponent", "1e999")
edit("edit-overflow-negative-exponent", "-1e999")
edit("edit-overflow-positive-400-digits", "9" * 400)
edit("edit-overflow-negative-400-digits", "-" + "9" * 400)
edit("edit-negative-zero", "-0")
edit("edit-positive-zero", "0")
edit("edit-largest-finite", "1.7976931348623157e308")
edit("edit-rounded-integer", "9007199254740993")

# ---- a tool's own prepare_arguments, against each schema kind
for token in ["+Infinity", "-Infinity", "NaN", "-0", "1e308", "0"]:
    slug = {"+Infinity": "pos-inf", "-Infinity": "neg-inf", "NaN": "nan", "-0": "neg-zero",
            "1e308": "large-finite", "0": "zero"}[token]
    custom(f"declared-number-{slug}", "number", "limit", token)
    custom(f"declared-integer-{slug}", "integer", "limit", token)
    custom(f"undeclared-{slug}", "open", "extra", token)

# L0506-D001-R001: several runtime numbers in one rejected call, for Pi's diagnostic serialization
cases.append({"id": "declared-number-diagnostic-projection", "tool": "custom", "schema": "number",
              "prepare_set": {"limit": "+Infinity", "extra": "NaN", "negativeZero": "-0"},
              "arguments": {}, "observe": ["/limit", "/extra", "/negativeZero"]})

with open(sys.argv[1], "w", encoding="utf-8", newline="\n") as handle:
    json.dump(cases, handle, indent=1)
    handle.write("\n")
print(f"{len(cases)} cases")
