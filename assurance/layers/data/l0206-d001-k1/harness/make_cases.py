"""L0206-D001 (K1) canonical cases (minion-agent#100): tool-argument objects whose key enumeration order pinned Pi
fixes by ECMAScript's OrdinaryOwnPropertyKeys, observed at every argument boundary by k1_boundaries.mjs.

An object is written as an INSERTION SEQUENCE {"$o": [[key, value], ...]} (a key may repeat: JSON.parse keeps the
first position with the last value). `provider_text` is that sequence as JSON text; pinned Pi decodes it with
JSON.parse (CreateDataProperty, so "__proto__" is an ordinary own key). A case may also carry:
    schema    the tool's declared parameters (validation runs against it; default: open {type: object})
    prepare   "edit": pinned Pi's edit prepareArguments (nested `edits` re-parsed from a JSON string)
    mutate    insertions a pre-execute hook makes IN PLACE on the arguments object (Pi's beforeToolCall)
    program   (L0206-D001-R001/R002) a mutation program the pre-execute hook runs IN PLACE, op by op:
                {"op": "set",    "target": T, "key": k, "value": V, "as"?: h}   T[k] = V
                {"op": "push",   "target": T, "key": k, "value": V, "as"?: h}   T[k].push(V)
                {"op": "insert", "target": T, "key": k, "index": i, "value": V, "as"?: h}
                                                                            T[k].splice(i, 0, V)
                {"op": "get",    "target": T, "key": k, "as": h}               h = T[k]
              Instead of "value", an op may give "ref": h, placing the SAME object h again.
              T is "args" or a handle; "as" names the object V builds (or T[k] for get), so a later op
              mutates THAT object through the retained reference. `observe_second` additionally
              observes the arguments after the program (a later listener's view).
    raw_program (L0206-D001-R004) the same op grammar, run on the RAW arguments object after the call is
              constructed (it is shared and mutable), before the call is persisted or executed
    replace   an insertion sequence a Minion pre-execute listener returns as REPLACEMENT arguments
              (Minion mapping: Pi's beforeToolCall cannot replace; the expectation is ECMAScript's own order
              for that object)

Coercion (pinned Pi's Value.Convert turns "5" into 5 without moving the key) is characterized by k1_probe.mjs
(`declared-number/convert`) but is not a canonical case: Minion's validator does not coerce (the disclosed TOOL-003
mapping), so such a case would test validation, not order.

    python make_cases.py <cases.json>
"""

from __future__ import annotations

import json
import sys


def o(*pairs: tuple[str, object]) -> dict:
    return {"$o": [[k, v] for k, v in pairs]}


def text(value: object) -> str:
    if isinstance(value, dict):
        return "{" + ",".join(json.dumps(k) + ":" + text(v) for k, v in value["$o"]) + "}"
    if isinstance(value, list):
        return "[" + ",".join(text(v) for v in value) + "]"
    return json.dumps(value)


S = {"type": "string"}
OPEN = {"type": "object", "properties": {}}

CASES: list[dict] = [
    {"id": "insertion/non-index-only", "arguments": o(("b", 1), ("a", 2), ("c", 3))},
    {"id": "insertion/reverse-alphabetic", "arguments": o(("z", 1), ("y", 2), ("x", 3), ("a", 4))},
    {"id": "index/only-ascending", "arguments": o(("0", 1), ("1", 2), ("2", 3))},
    {"id": "index/only-reverse", "arguments": o(("2", 1), ("1", 2), ("0", 3))},
    {"id": "index/numeric-not-lexicographic", "arguments": o(("10", 1), ("9", 2), ("100", 3), ("2", 4))},
    {"id": "mixed/index-after-names", "arguments": o(("b", 1), ("2", 2), ("1", 3), ("a", 4))},
    {"id": "mixed/interleaved", "arguments": o(("x", 1), ("5", 2), ("y", 3), ("0", 4), ("z", 5), ("3", 6))},
    {"id": "boundary/largest-index", "arguments": o(("b", 1), ("4294967295", 2), ("4294967294", 3), ("0", 4))},
    {"id": "boundary/zero", "arguments": o(("a", 1), ("0", 2))},
    {"id": "non-canonical/leading-zeros",
     "arguments": o(("01", 1), ("1", 2), ("00", 3), ("0", 4), ("007", 5))},
    {"id": "non-canonical/signs-and-decimals",
     "arguments": o(("-1", 1), ("-0", 2), ("+1", 3), ("1.0", 4), ("1e3", 5), ("2", 6))},
    {"id": "non-canonical/whitespace-and-hex", "arguments": o((" 1", 1), ("1 ", 2), ("0x1", 3), ("3", 4))},
    {"id": "large/numeric-strings",
     "arguments": o(("18446744073709551616", 1), ("9007199254740993", 2), ("4294967296", 3), ("7", 4))},
    {"id": "duplicate/first-position-last-value", "arguments": o(("a", 1), ("1", 2), ("a", 3), ("b", 4))},
    {"id": "duplicate/index-key", "arguments": o(("2", 1), ("x", 2), ("2", 3))},
    {"id": "proto/own-key", "arguments": o(("b", 1), ("__proto__", 2), ("1", 3))},
    {"id": "nested/object", "arguments": o(("o", o(("z", 1), ("2", 2), ("a", 3), ("0", 4))), ("1", 5))},
    {"id": "nested/deep", "arguments": o(("p", o(("q", o(("b", 1), ("1", 2))), ("3", 4))))},
    {"id": "nested/objects-in-array",
     "arguments": o(("list", [o(("b", 1), ("0", 2)), o(("1", 3), ("a", 4))]))},
    {"id": "empty/object", "arguments": o()},
    {"id": "schema/declared-z-a-input-a-z", "schema": {"type": "object", "properties": {"z": S, "a": S}},
     "arguments": o(("a", "x"), ("z", "y"))},
    {"id": "schema/declared-with-extras", "schema": {"type": "object", "properties": {"z": S, "a": S}},
     "arguments": o(("extra", "e"), ("a", "x"), ("10", "t"), ("z", "y"), ("1", "o"))},
    {"id": "schema/declared-index-property", "schema": {"type": "object", "properties": {"b": S, "1": S}},
     "arguments": o(("b", "x"), ("1", "y"), ("c", "z"))},
    {"id": "schema/declared-nested", "schema": {"type": "object", "properties": {
        "o": {"type": "object", "properties": {"z": S, "a": S}}}},
     "arguments": o(("o", o(("a", "x"), ("z", "y"), ("2", "i"))))},
    {"id": "hook/mutation-adds-index-and-name", "arguments": o(("1", 1), ("2", 2), ("b", 3)),
     "mutate": [["c", 4], ["0", 5]]},
    {"id": "hook/mutation-overwrites-existing", "arguments": o(("b", 1), ("a", 2)),
     "mutate": [["b", 9], ["3", 3]]},
    {"id": "hook/replacement-object", "arguments": o(("a", 1)),
     "replace": o(("z", 1), ("2", 2), ("y", 3), ("1", 4))},
    {"id": "key/long-decimal-is-ordinary", "arguments": o(("b", 1), ("9" * 5000, 2), ("1", 3))},
    {"id": "key/eleven-digits-is-ordinary", "arguments": o(("b", 1), ("10000000000", 2), ("1", 3))},
    {"id": "mutation/push-object-into-array", "arguments": o(("a", [])),
     "program": [{"op": "push", "target": "args", "key": "a", "value": o(("b", 1), ("2", 2), ("1", 3))}]},
    {"id": "mutation/insert-object-into-array", "arguments": o(("a", [o(("x", 1))])),
     "program": [{"op": "insert", "target": "args", "key": "a", "index": 0, "value": o(("z", 1), ("0", 2))}]},
    {"id": "mutation/retained-child-set-later", "arguments": o(("a", 1)),
     "program": [{"op": "set", "target": "args", "key": "o", "value": o(("b", 1)), "as": "child"},
                 {"op": "set", "target": "child", "key": "2", "value": 2}]},
    {"id": "mutation/retained-array-element-set-later", "arguments": o(("a", [])),
     "program": [{"op": "push", "target": "args", "key": "a", "value": o(("b", 1)), "as": "el"},
                 {"op": "set", "target": "el", "key": "1", "value": 1},
                 {"op": "set", "target": "el", "key": "c", "value": 3}]},
    {"id": "mutation/nested-existing-gains-index", "arguments": o(("o", o(("z", 1), ("y", 2)))),
     "program": [{"op": "get", "target": "args", "key": "o", "as": "inner"},
                 {"op": "set", "target": "inner", "key": "0", "value": 0}]},
    {"id": "mutation/shared-child-two-places", "arguments": o(("a", 1)),
     "program": [{"op": "set", "target": "args", "key": "p", "value": o(("b", 1)), "as": "shared"},
                 {"op": "set", "target": "args", "key": "q", "ref": "shared"},
                 {"op": "set", "target": "shared", "key": "1", "value": 1}]},
    {"id": "mutation/second-listener-sees-ordered", "arguments": o(("a", [])), "observe_second": True,
     "program": [{"op": "push", "target": "args", "key": "a", "value": o(("b", 1), ("0", 2))},
                 {"op": "set", "target": "args", "key": "3", "value": 3}]},
    {"id": "raw/assign-index-keys-after-construction", "arguments": o(("b", 1)),
     "raw_program": [{"op": "set", "target": "args", "key": "2", "value": 2},
                     {"op": "set", "target": "args", "key": "1", "value": 3}]},
    {"id": "raw/push-object-into-raw-array", "arguments": o(("a", [])),
     "raw_program": [{"op": "push", "target": "args", "key": "a", "value": o(("z", 1), ("0", 2))}]},
    {"id": "raw/nested-raw-object-gains-index", "arguments": o(("o", o(("y", 1)))),
     "raw_program": [{"op": "get", "target": "args", "key": "o", "as": "inner"},
                     {"op": "set", "target": "inner", "key": "5", "value": 5}]},
    {"id": "prepare/edit-nested-edits",
     "prepare": "edit",
     "schema": "edit",
     "arguments": o(("path", "f.txt"), ("edits", text([o(("newText", "b"), ("1", "i"), ("oldText", "a"))])))},
]


def build() -> list[dict]:
    out = []
    for case in CASES:
        c = {"id": case["id"], "provider_text": text(case["arguments"]), "arguments": case["arguments"]}
        c["schema"] = case.get("schema", OPEN)
        for key in ("prepare", "mutate", "replace", "program", "observe_second", "raw_program"):
            if key in case:
                c[key] = case[key]
        if "replace" in c:
            c["replace_text"] = text(c["replace"])
        out.append(c)
    ids = [c["id"] for c in out]
    assert len(ids) == len(set(ids))
    return out


if __name__ == "__main__":
    with open(sys.argv[1], "w", encoding="utf-8", newline="\n") as fh:
        json.dump(build(), fh, indent=1)
        fh.write("\n")
