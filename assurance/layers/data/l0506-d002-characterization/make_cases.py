"""L0506-D002 characterization cases: the Owner decision's string neighborhood (#49 comment 5924605017 sec. 2)
x the schema keywords that observe strings, plus the edit JSON.parse path and the object-key domain.
Strings are arrays of UTF-16 code units, so lone surrogates survive the JSON case file.

    python make_cases.py <out.json>
"""
import json
import sys

HI, LO, PAIR = 0xD800, 0xDC00, [0xD83D, 0xDE00]  # U+1F600 as a surrogate pair
A, B = 0x41, 0x42
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
SCHEMAS = ["open", "string", "min-length-2", "max-length-1", "pattern-one-char", "pattern-two-chars",
           "const-pair", "enum-lone"]

cases = []
for name, units in NEIGHBORHOOD.items():
    for schema in SCHEMAS:
        cases.append({"id": f"{schema}/{name}", "kind": "string", "schema": schema, "units": units})


def esc(units):
    return "".join("\\u%04x" % u for u in units)


# the real edit path: the inner JSON.parse of a string `edits` (escapes as the model would send them)
for name, units in NEIGHBORHOOD.items():
    text = '[{"oldText":"a","newText":"' + esc(units) + '"}]'
    cases.append({"id": f"edit/{name}", "kind": "edit", "edits_json": text})

# object keys reached through JSON.parse in the edit path
KEYS = {
    "integer-like-order": '[{"oldText":"a","newText":"b","b":1,"2":2,"1":3,"a":4}]',
    "lone-surrogate-key": '[{"oldText":"a","newText":"b","' + esc([HI]) + '":1}]',
    "pair-key": '[{"oldText":"a","newText":"b","' + esc(PAIR) + '":1}]',
    "proto-key": '[{"oldText":"a","newText":"b","__proto__":{"x":1}}]',
    "duplicate-key": '[{"oldText":"a","newText":"b","k":1,"k":2}]',
    "empty-key": '[{"oldText":"a","newText":"b","":1}]',
}
for name, text in KEYS.items():
    cases.append({"id": f"keys/{name}", "kind": "keys", "json_text": text})

with open(sys.argv[1], "w", encoding="utf-8", newline="\n") as handle:
    json.dump(cases, handle, indent=1)
print(len(cases), "cases")
