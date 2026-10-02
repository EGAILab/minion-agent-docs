"""Generate the L0206-D001 (K1) canonical scenarios (minion-agent conformance/agent/key-order/) from the pinned-Pi
canonical-case authority (cases.json + k1-boundaries.json).

    python make_scenarios.py <cases.json> <k1-boundaries.json> <target dir>

Each case's `expect` is pinned Pi's own observation at each boundary. An observation is the recursive enumeration:
{"o": [[key, observation], ...]} for an object, {"a": [...]} for an array, the value itself otherwise. For a `replace`
case (a Minion replacement mapping: pinned Pi's beforeToolCall cannot replace arguments) `execute` is ECMAScript's own
order for the replacement object, which is what Minion's execute receives.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PI = "b7bb00b936dbe21b8e160b3e89efdec361846699"
AUTHORITY = ("pinned Pi b7bb00b9 agent-loop.ts prepareToolCall/executePreparedToolCall/finalizeExecutedToolCall + "
             "ai/src/utils/validation.ts validateToolArguments (typebox 1.3.7) + coding-agent edit.ts "
             "prepareEditArguments (sliced unmodified), raw = JSON.parse of the provider text, under Node 22.15.1 "
             "(L0206-D001 k1_boundaries.mjs)")


def main(cases_path: str, authority_path: str, target: str) -> None:
    cases = json.load(open(cases_path, encoding="utf-8"))
    observed = {r["id"]: r for r in json.load(open(authority_path, encoding="utf-8"))["results"]}
    assert [c["id"] for c in cases] == list(observed)
    out = []
    for c in cases:
        r = observed[c["id"]]
        expect = {"raw": r["raw"], "replay": r["replay"], "hook": r["hook"],
                  "execute": r["replacement"] if "replace" in c else r["execute"]}
        if "second" in r:
            expect["second"] = r["second"]
        if "prepare" not in c:  # a shim's in-place raw mutation is the certified nonmutation mapping's (Python copies)
            expect["start"] = r["start"]
            # `update` (the raw object, observed during execute) only where no hook mutated: whether a hook's NESTED
            # mutation reaches the raw object is value isolation (Pi validates a structuredClone), recorded separately
            # as L06-VALIDATION-SHALLOW-COPY (minion-agent#129), not key order.
            if not any(k in c for k in ("program", "mutate")):
                expect["update"] = r["update"]
        case = {"id": c["id"], "provider_text": c["provider_text"], "arguments": c["arguments"], "schema": c["schema"]}
        for key in ("prepare", "mutate", "replace", "program", "observe_second", "raw_program"):
            if key in c:
                case[key] = c[key]
        case["expect"] = expect
        out.append(case)
    Path(target).mkdir(parents=True, exist_ok=True)
    with open(Path(target) / "key-order.json", "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"name": "key-order", "family": "agent", "authority": AUTHORITY, "pi_revision": PI,
                   "requirements": ["AI-003", "TOOL-003"], "witnesses": ["ecmascript_object_key_order"],
                   "notes": ("Tool-argument object key enumeration order (L0206-D001, K1): ECMAScript "
                             "OrdinaryOwnPropertyKeys, recursively, at construction, session replay, the pre-execute "
                             "listener and execute (the tools/execution-start payload is the constructed object). "
                             "`arguments` is an insertion sequence the runner builds by plain assignment; ordering is "
                             "the pipeline's job. GENERATED from the pinned-Pi K1 boundary authority; regenerate with "
                             "harness/make_scenarios.py."),
                   "key_order": {"cases": out}}, fh, indent=1)
        fh.write("\n")
    print({"key-order": len(out)})


if __name__ == "__main__":
    main(*sys.argv[1:4])
