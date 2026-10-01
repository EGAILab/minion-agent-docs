"""L0506-D003 characterization cases: the tool-result runtime value domain (Owner decision WP132-RUST-C002-Q001).

Values are written in the probe's tagged observation form, so a case states the exact JavaScript value without
relying on any host JSON library:
    {"u": [code units]}     a JavaScript String (any UTF-16 code units)
    {"n": "token"}          a Number: "NaN", "+Infinity", "-Infinity", "-0", or Number::toString of a finite value
    {"a": [values]}         an array
    {"o": [[key units, value], ...]}   a plain object, keys in insertion order
    {"v": null|true|false}  null / a boolean
    {"undef": true}         undefined

Each case: a custom tool returns {content: [{type: "text", text}], details} (or throws), and an afterToolCall hook
runs in one of these modes:
    none        no afterToolCall configured
    observe     returns undefined (observes only)
    same        returns {content, details} = the very values it received
    replace     returns {content?, details?} = the case's replacement values
    null        returns {details: null} (Pi: `afterResult.details ?? result.details`)
    throws      throws an Error whose message is the case's text
"""

from __future__ import annotations

import json
import sys

HI, LO = 0xD800, 0xDC00
PAIR = [0xD83D, 0xDE00]  # U+1F600


def u(units):
    return {"u": list(units)}


def s(text):
    data = text.encode("utf-16-le", "surrogatepass")
    return u(int.from_bytes(data[i : i + 2], "little") for i in range(0, len(data), 2))


def n(token):
    return {"n": token}


def o(*entries):
    return {"o": [[list(k) if not isinstance(k, str) else s(k)["u"], v] for k, v in entries]}


def a(*values):
    return {"a": list(values)}


NULL, TRUE, FALSE, UNDEF = {"v": None}, {"v": True}, {"v": False}, {"undef": True}
OK = s("ok")

STRINGS = {
    "ascii": [0x61, 0x62],
    "bmp": [0xE9, 0x4E2D],
    "pair": PAIR,
    "lone-high-start": [HI, 0x41],
    "lone-high-middle": [0x41, HI, 0x42],
    "lone-high-end": [0x41, HI],
    "lone-high-only": [HI],
    "lone-low-start": [LO, 0x41],
    "lone-low-only": [LO],
    "adjacent-highs": [HI, HI],
    "low-then-high": [LO, HI],
    "pair-then-lone-high": PAIR + [HI],
    "lone-low-then-pair": [LO] + PAIR,
    "empty": [],
    "nul": [0],
    "replacement-char": [0xFFFD],
}
NUMBERS = ["0", "-0", "1.5", "+Infinity", "-Infinity", "NaN", "1.7976931348623157e+308", "5e-324", "9007199254740992"]


def case(cid, text=OK, details=None, hook="none", throws=None, replace=None):
    c = {"id": cid, "tool": {"text": text, "details": o() if details is None else details}, "hook": {"mode": hook}}
    if throws is not None:
        c["tool"] = {"throws": throws}
    if replace is not None:
        c["hook"].update(replace)
    return c


def build():
    cases = []
    for name, units in STRINGS.items():
        # the string as a details leaf, nested in an array, nested in an object, as an object key, and as the text
        cases.append(case(f"details-leaf/{name}", details=o(("diff", u(units)))))
        cases.append(case(f"details-array/{name}", details=o(("lines", a(s("x"), u(units))))))
        cases.append(case(f"details-nested/{name}", details=o(("outer", o(("inner", u(units)))))))
        cases.append(case(f"details-key/{name}", details=o((units, TRUE))))
        cases.append(case(f"text/{name}", text=u(units)))
        cases.append(case(f"details-top-string/{name}", details=u(units)))
    for token in NUMBERS:
        cases.append(case(f"details-number/{token}", details=o(("value", n(token)))))
        cases.append(case(f"details-array-number/{token}", details=o(("values", a(n(token))))))
        cases.append(case(f"details-top-number/{token}", details=n(token)))
    for name, value in {"null": NULL, "true": TRUE, "false": FALSE}.items():
        cases.append(case(f"details-scalar/{name}", details=o(("value", value))))
        cases.append(case(f"details-top-scalar/{name}", details=value))
    cases.append(case("details-top-undefined", details=UNDEF))
    cases.append(case("details-nested-undefined", details=o(("value", UNDEF), ("kept", TRUE))))
    cases.append(case("details-array-undefined", details=o(("values", a(UNDEF, TRUE)))))
    cases.append(case("details-empty-object", details=o()))
    cases.append(case("details-empty-array", details=a()))
    cases.append(case("details-key-order", details=o(("b", TRUE), ("2", TRUE), ("a", TRUE), ("1", TRUE))))
    mixed = o(("diff", u([0x41, HI])), ("n", n("-0")), (u([LO])["u"], a(n("NaN"), u([HI]))))
    # after-hook boundary
    for mode in ["observe", "same", "null"]:
        cases.append(case(f"hook-{mode}/mixed", text=u([0x41, HI]), details=mixed, hook=mode))
    cases.append(case("hook-replace/details", details=o(("diff", s("a"))), hook="replace",
                      replace={"details": mixed}))
    cases.append(case("hook-replace/text", hook="replace", replace={"text": u([LO, 0x41])}))
    cases.append(case("hook-replace/details-number", hook="replace", replace={"details": o(("v", n("+Infinity")))}))
    cases.append(case("hook-throws/lone-surrogate", hook="throws", replace={"message": u([0x41, HI])}))
    # failure conversion: the tool throws; Pi's createErrorToolResult text is the message
    for name in ["lone-high-middle", "lone-low-only", "pair"]:
        cases.append(case(f"tool-throws/{name}", throws=u(STRINGS[name])))
    ids = [c["id"] for c in cases]
    assert len(ids) == len(set(ids))
    return cases


if __name__ == "__main__":
    with open(sys.argv[1], "w", encoding="utf-8", newline="\n") as fh:
        json.dump(build(), fh, indent=1)
        fh.write("\n")
