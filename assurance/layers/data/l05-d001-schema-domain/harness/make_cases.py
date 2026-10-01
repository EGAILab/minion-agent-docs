"""L05-D001 schema-domain cases: role x schema member x instance member (Owner decision #99 comment 5926416181 s.4).

    python make_cases.py <out.json>
"""
import json
import sys

HI, LO, PAIR, FFFD = 0xD800, 0xDC00, [0xD83D, 0xDE00], 0xFFFD
MEMBERS = {
    "ascii": [0x61, 0x62],
    "bmp": [0xE9, 0x4E2D],
    "pair": PAIR,
    "lone-high": [HI],
    "lone-low": [LO],
    "pair-then-lone-high": [*PAIR, HI],
    "fffd": [FFFD],
    # the halves of the valid pair, alone: Unicode-mode pattern matching must not find them inside the pair
    "pair-high-half": [0xD83D],
    "pair-low-half": [0xDE00],
}
ROLES = ["properties-required", "additional-properties-false", "const", "enum", "pattern", "pattern-unanchored", "pattern-properties",
         "pattern-properties-unanchored",  # L05-D001-R001
         "property-names-const", "dependent-required"]
cases = [{"id": f"{role}/{s}/{i}", "role": role, "schema_units": su, "instance_units": iu}
         for role in ROLES for s, su in MEMBERS.items() for i, iu in MEMBERS.items()]
with open(sys.argv[1], "w", encoding="utf-8", newline="\n") as handle:
    json.dump(cases, handle, indent=1)
    handle.write("\n")
print(f"{len(cases)} cases")
