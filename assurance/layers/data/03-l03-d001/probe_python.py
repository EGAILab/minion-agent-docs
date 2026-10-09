"""L03-D001 characterization: request-header tool reconstruction over every constrained-sampling state.

Drives only real seams: `ToolSchema.as_json`, `record_header` into a real `ArtifactStore`/`SessionLog`,
the stored tools artifact as bytes, and `reconstruct_tools`. For each certified state it reports the
model-facing JSON of the recorded schema, of the stored artifact entry and of the reconstructed schema,
and whether the reconstruction equals the recorded schema.

Run from `minion-agent-python/` with `PYTHONPATH=src`:  python probe_python.py OUT.json
"""

from __future__ import annotations

import json
import sys

from minion_agent.llm.tools import GrammarConstrainedSampling, JsonSchemaConstrainedSampling, ToolSchema
from minion_agent.session import ArtifactStore, SessionLog, record_header, reconstruct_tools

PARAMETERS = {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}
STATES = {
    "absent": None,
    "false": False,
    "json_schema_prefer": JsonSchemaConstrainedSampling(strict="prefer"),
    "json_schema_require": JsonSchemaConstrainedSampling(strict="require"),
    "grammar_lark": GrammarConstrainedSampling(openai_lark="start: WORD"),
    "grammar_regex": GrammarConstrainedSampling(openai_regex="[a-z]+"),
    "grammar_both": GrammarConstrainedSampling(openai_lark="start: WORD", openai_regex="[a-z]+"),
    "grammar_neither": GrammarConstrainedSampling(),
}


def main(out: str) -> None:
    rows = []
    for label, sampling in STATES.items():
        schema = ToolSchema(name="echo", description="Echo.", parameters=PARAMETERS, constrained_sampling=sampling)
        store, log = ArtifactStore(), SessionLog("probe")
        event = record_header(log, store, {"system_base": "base"}, "mock-1", tools=(schema,))
        stored = json.loads(store.get(event.data["tools"]).decode("utf-8"))[0]
        rebuilt = reconstruct_tools(event, store)[0]
        rows.append(
            {
                "state": label,
                "recorded": schema.as_json(),
                "stored": stored,
                "reconstructed": rebuilt.as_json(),
                "stored_equals_recorded": stored == schema.as_json(),
                "reconstructed_equals_recorded": rebuilt == schema,
            }
        )
    with open(out, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(rows, handle, indent=2, sort_keys=True)
        handle.write("\n")


if __name__ == "__main__":
    main(sys.argv[1])
