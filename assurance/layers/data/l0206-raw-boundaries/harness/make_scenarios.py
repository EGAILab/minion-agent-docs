"""L0206-D002 canonical scenarios (minion-agent conformance/agent/raw-arguments/,
conformance/schema/raw-arguments-scenario.schema.json), generated from the pinned-Pi raw-boundary probe.

    python make_scenarios.py <cases.json> <out/raw.json> <out dir>

Each case is the raw `ToolCall.arguments` value pinned Pi's `JSON.parse` produced from a provider's argument text
(the probe's `decode` observation), written in the value grammar: {"utf16": units} for a string, {"number": token}
for a number, {"$keys": [[units, v], ...]} for an object whose keys need code units, plain objects/arrays.
Pinned Pi carries that exact value to tool_execution_start, beforeToolCall and execute for a tool WITHOUT
prepareArguments; the expectation is therefore the value itself at every Minion boundary (construction, session
append + replay, tools/execution-start, the pre-execute hook, execute). Key ENUMERATION order is L0206-D001's (K1)
and is not asserted here: objects compare as key sets.
"""
import json
import sys
from pathlib import Path

PI = "b7bb00b936dbe21b8e160b3e89efdec361846699"
AUTH = (f"pinned Pi {PI[:8]} ai/src/utils/json-parse.ts parseJsonWithRepair (sliced) + agent-loop.ts prepareToolCall/"
        "executePreparedToolCall/finalizeExecutedToolCall (sliced; a tool without prepareArguments) + "
        "validation.ts validateToolArguments (typebox 1.3.7), under Node 22.15.1 (L0206-D002 raw-boundary probe)")


def value(o):
    """The probe's observation -> the scenario value grammar."""
    if "u" in o:
        return {"utf16": o["u"]}
    if "n" in o:
        return {"number": o["n"]}
    if "a" in o:
        return [value(x) for x in o["a"]]
    if "o" in o:
        plain = all(all(0x20 <= c < 0x7F for c in k) for k, _ in o["o"])
        if plain:
            return {"".join(map(chr, k)): value(v) for k, v in o["o"]}
        return {"$keys": [[k, value(v)] for k, v in o["o"]]}  # keys that need code units
    raise ValueError(o)


GROUPS = [
    ("string/", "raw-arguments-string-domain",
     "Raw string leaves: pinned Pi's JSON.parse keeps every member of the Owner decision's neighborhood (L0506-D002-Q001 "
     "section 6) as exact UTF-16 code units -- unpaired highs and lows at every position, adjacent/reversed/mixed, a "
     "valid pair (escaped or literal), empty, NUL, nested-object and array strings -- and carries them to "
     "tool_execution_start, beforeToolCall and execute with no prepareArguments."),
    ("number/", "raw-arguments-number-domain",
     "Raw number leaves (decision section 6): pinned Pi's JSON.parse yields runtime numbers -- -0 (also from -1e-400), "
     "+/-Infinity from overflow, binary64 rounding (9007199254740993 -> 9007199254740992), the smallest subnormal and "
     "the largest finite -- and carries them live to tool_execution_start, beforeToolCall and execute. (Pi's persisted "
     "session line projects -0 -> 0 and +/-Infinity -> null; Minion's certified Layer 03 has no persisted byte form, so "
     "the log keeps and replays the live value.)"),
    ("keys/surrogate-keys", "raw-arguments-key-domain",
     "Raw object keys share the string domain: keys holding an unpaired low, an unpaired high and a valid pair keep "
     "their exact code units. Enumeration ORDER is L0206-D001's (K1) and is not asserted here."),
]


def main():
    cases = {c["id"]: c for c in json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))}
    results = {r["id"]: r for r in json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))["results"]}
    out = Path(sys.argv[3])
    out.mkdir(parents=True, exist_ok=True)
    for prefix, name, notes in GROUPS:
        docs_cases = []
        for cid, r in results.items():
            if not cid.startswith(prefix):
                continue
            p = r["pipeline"]
            assert p["outcome"] == "prepared" and p["hook"] == r["decode"] == p["execute"], cid
            docs_cases.append({"id": cid, "provider_text": cases[cid]["text"], "arguments": value(r["decode"])})
        doc = {"name": name, "family": "agent", "authority": AUTH, "pi_revision": PI, "requirements": ["AI-003"],
               "witnesses": ["raw_tool_call_argument_value_domain"],
               "notes": notes + " GENERATED from the pinned-Pi raw-boundary probe; regenerate with harness/make_scenarios.py.",
               "raw_arguments": {"cases": docs_cases}}
        (out / f"{name}.json").write_text(json.dumps(doc, indent=1, ensure_ascii=True) + "\n", encoding="ascii",
                                          newline="\n")
        print(name, len(docs_cases))


if __name__ == "__main__":
    main()
