"""Raw ToolCall.arguments boundary cases for L0206-D002 (Q001: raw string domain, plus the decision's section 6
numeric leaves) and L0206-D001 (K1: key enumeration order). Each case is the final tool-call argument TEXT a provider
delivers; the probe decodes it as pinned Pi does and follows the value through persistence, replay and the pipeline.

    python make_cases.py <out.json>
"""
import json
import sys

HI, LO, PAIR = 0xD800, 0xDC00, [0xD83D, 0xDE00]
A, B = 0x41, 0x42
# Q001 decision section 6 (and the D002 neighborhood, for one shared vocabulary)
STRINGS = {
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
    "low-then-high": [LO, HI],
    "pair-then-lone-high": [*PAIR, HI],
    "lone-low-then-pair": [LO, *PAIR],
    "empty": [],
    "nul": [0x00],
    "nul-middle": [A, 0x00, B],
}
# decision section 6: other already-known JavaScript-domain mismatches at the same JSON.parse boundary
NUMBERS = {
    "large-finite": "1.7976931348623157e308",
    "integer-2p53-plus-1": "9007199254740993",
    "negative-zero": "-0",
    "zero": "0",
    "overflow-positive": "1e999",
    "overflow-negative": "-1e999",
    "overflow-400-digits": "9" * 400,
    "underflow-to-zero": "1e-400",
    "negative-underflow": "-1e-400",
    "smallest-subnormal": "5e-324",
    # CE-L0206-D002-01 (R002): integer-looking spellings whose exact binary64 value differs, and their controls
    "exact-1e18": "1000000000000000000",
    "non-exact-integer-spelling": "1000000000000000100",
    "non-exact-integer-spelling-negative": "-1000000000000000100",
    "integral-exponent-1e21": "1e21",
    "fraction-0.1": "0.1",
}
# K1 (L0206-D001) decision sections 2/3: key neighborhood; nested objects
KEYS = {
    "mixed-index-first": '{"b":1,"2":2,"1":3,"a":4}',
    "index-boundaries": '{"x":0,"4294967295":1,"4294967294":2,"0":3}',
    "non-canonical-numerals": '{"x":0,"01":1,"00":2,"-0":3,"-1":4,"1.0":5,"+1":6,"1":7}',
    "nested": '{"b":{"z":1,"9":2,"a":3},"1":[{"y":1,"0":2}],"a":0}',
    "duplicate-key": '{"k":1,"a":2,"k":3}',
    "proto-key": '{"__proto__":{"x":1},"a":1}',
    "surrogate-keys": '{"\\udc00":1,"\\ud800":2,"\\ud83d\\ude00":3,"a":4}',
}


def esc(units):
    return "".join("\\u%04x" % u for u in units)


cases = []
for name, units in STRINGS.items():
    s = '"' + esc(units) + '"'
    cases.append({"id": f"string/{name}", "text": '{"s":' + s + "}"})
cases.append({"id": "string/nested-object", "text": '{"o":{"s":"A' + esc([HI]) + '"}}'})
cases.append({"id": "string/array", "text": '{"a":["x","' + esc([LO]) + 'B"]}'})
cases.append({"id": "string/literal-pair", "text": '{"s":"\U0001F600"}'})  # an unescaped astral character
for name, literal in NUMBERS.items():
    cases.append({"id": f"number/{name}", "text": '{"n":' + literal + "}"})
for name, text in KEYS.items():
    cases.append({"id": f"keys/{name}", "text": text})

with open(sys.argv[1], "w", encoding="utf-8", newline="\n") as handle:
    json.dump(cases, handle, indent=1)
    handle.write("\n")
print(f"{len(cases)} cases")
