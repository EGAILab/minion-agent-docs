"""L05-D001 canonical scenarios (minion-agent conformance/agent/schema-domain/, shape schema-domain-scenario.schema.json),
generated from the pinned-Pi schema-domain probe.

    python make_scenarios.py <cases.json> <out/schema.json> <out dir>

Each case carries its literal `schema` (a tool's ToolDefinition.parameters) and `arguments` (the raw arguments of a
tool without prepare_arguments) in the value grammar -- {"utf16": units} for every string, {"$keys": [[units, v]...]}
for an object, plain JSON for numbers/booleans/arrays -- so a runner needs no knowledge of the role that built them.
The expectation is pinned Pi's verdict: `accept` (validation passes; execute runs) or `reject` (the certified
immediate argument-validation error, TOOL-003).
"""
import json
import sys
from pathlib import Path

PI = "b7bb00b936dbe21b8e160b3e89efdec361846699"
AUTH = (f"pinned Pi {PI[:8]} ai/src/utils/validation.ts validateToolArguments (typebox 1.3.7, unmodified), under "
        "Node 22.15.1 (L05-D001 schema-domain probe)")
ROLE_NOTES = {
    "properties-required": "property names and `required` entries match instance keys by exact UTF-16 identity",
    "additional-properties-false": "a declared property name admits exactly the identical instance key",
    "const": "`const` compares exact code-unit sequences",
    "enum": "`enum` compares exact code-unit sequences",
    "pattern": "an anchored `pattern` (^S$) built from the member is a Unicode-mode RegExp: identity",
    "pattern-unanchored": ("an unanchored `pattern` is a Unicode-mode RegExp SEARCH: a valid pair is one code point, "
                           "so neither of its halves matches inside it, while a genuinely unpaired surrogate does "
                           "match where it occurs"),
    "pattern-properties": "a `patternProperties` key is an anchored Unicode-mode RegExp over instance keys",
    "property-names-const": "`propertyNames: {const: S}` compares keys by exact code units",
    "dependent-required": "a `dependentRequired` key triggers on the exact instance key",
}


def build(role, s, i):
    """The role's schema and instance (identical to harness/schema_probe.mjs ROLES)."""
    return {
        "properties-required": ({"type": "object", "properties": {s: {"type": "string"}}, "required": [s]}, {i: "x"}),
        "additional-properties-false": ({"type": "object", "properties": {s: {"type": "string"}},
                                         "additionalProperties": False}, {i: "x"}),
        "const": ({"type": "object", "properties": {"t": {"const": s}}}, {"t": i}),
        "enum": ({"type": "object", "properties": {"t": {"enum": [s]}}}, {"t": i}),
        "pattern": ({"type": "object", "properties": {"t": {"type": "string", "pattern": "^" + s + "$"}}}, {"t": i}),
        "pattern-unanchored": ({"type": "object", "properties": {"t": {"type": "string", "pattern": s}}}, {"t": i}),
        "pattern-properties": ({"type": "object", "patternProperties": {"^" + s + "$": {"type": "number"}}}, {i: "x"}),
        "property-names-const": ({"type": "object", "propertyNames": {"const": s}}, {i: 1}),
        "dependent-required": ({"type": "object", "dependentRequired": {s: ["a"]}}, {i: 1}),
    }[role]


def units_of(s):
    data = s.encode("utf-16-le", "surrogatepass")
    return [int.from_bytes(data[k:k + 2], "little") for k in range(0, len(data), 2)]


def encode(v):
    if isinstance(v, str):
        return {"utf16": units_of(v)}
    if isinstance(v, dict):
        return {"$keys": [[units_of(k), encode(x)] for k, x in v.items()]}
    if isinstance(v, list):
        return [encode(x) for x in v]
    return v


def string(units):
    return b"".join(u.to_bytes(2, "little") for u in units).decode("utf-16-le", "surrogatepass")


def main():
    cases = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    verdicts = {r["id"]: r["verdict"] for r in json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))["results"]}
    assert set(verdicts.values()) <= {"accept", "reject"}
    out = Path(sys.argv[3])
    out.mkdir(parents=True, exist_ok=True)
    for role, note in ROLE_NOTES.items():
        docs_cases = []
        for c in cases:
            if c["role"] != role:
                continue
            schema, arguments = build(role, string(c["schema_units"]), string(c["instance_units"]))
            docs_cases.append({"id": c["id"], "schema": encode(schema), "arguments": encode(arguments),
                               "expect": verdicts[c["id"]]})
        doc = {"name": f"schema-domain-{role}", "family": "agent", "authority": AUTH, "pi_revision": PI,
               "requirements": ["TOOL-016", "TOOL-003"], "witnesses": ["runtime_validation_schema_string_domain"],
               "notes": (f"L05-D001 role `{role}`: {note}. 9 schema members x 9 instance members (ASCII, BMP, valid "
                         "pair, lone high, lone low, pair+lone high, U+FFFD, and each half of the pair alone). "
                         "GENERATED from the pinned-Pi probe; regenerate with harness/make_scenarios.py."),
               "schema_domain": {"cases": docs_cases}}
        (out / f"schema-domain-{role}.json").write_text(json.dumps(doc, indent=1, ensure_ascii=True) + "\n",
                                                         encoding="ascii", newline="\n")
        print(role, len(docs_cases))


if __name__ == "__main__":
    main()
