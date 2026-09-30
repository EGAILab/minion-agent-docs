"""CE-L0506-D001-I001-01 rev 2: the 100 matrix cells plus the supplemental opaque-sibling row, through
the REAL Layer 06 `_validate` of a candidate source tree -- verdict and delivered value (tokenized).

    python real.py cases <out.json>                 -- cases.json (matrix rows + opaque-sibling)
    python real.py minion <src> <pi.json> <out.json> -- Minion's verdict/value, compared to Pi's
"""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # the rev-1 matrix rows
import matrix  # noqa: E402
from pydantic import ConfigDict, create_model  # noqa: E402


class Opaque:
    """Validated by isinstance only (arbitrary_types_allowed); pydantic cannot give it a JSON schema."""


OPAQUE_SCHEMA = {  # the model's JSON projection with the opaque field unconstrained
    "type": "object",
    "properties": {"field": {"type": "number"}, "thing": {}},
    "required": ["field"],
}


def models():
    for row_id, ann, _ in matrix.ROWS:
        model = create_model("M", __config__=ConfigDict(arbitrary_types_allowed=True), field=(ann, ...))
        yield row_id, model, model.model_json_schema(), matrix.shape(row_id)
    opaque = create_model(
        "M", __config__=ConfigDict(arbitrary_types_allowed=True), field=(float, ...), thing=(Opaque | None, None)
    )
    yield "opaque-sibling", opaque, OPAQUE_SCHEMA, lambda v: v


def cases():
    return [
        {"id": f"{row_id}/{tok}", "schema": schema, "arguments": matrix.tokenize({"field": shape(v)})}
        for row_id, _, schema, shape in models()
        for tok, v in matrix.VALUES.items()
    ]


def minion(pi):
    from minion_agent.tools.definition import ToolDefinition
    from minion_agent.tools.execute import ArgumentValidationError, _validate

    out, agree, differ = {}, 0, []
    for row_id, model, _, shape in models():
        tool = ToolDefinition(name="t", label="t", description="d", parameters=model, execute=lambda *a: None)
        for tok, v in matrix.VALUES.items():
            key = f"{row_id}/{tok}"
            try:
                got = {"verdict": "accept", "value": matrix.tokenize(_validate(tool, {"field": shape(v)}))}
            except ArgumentValidationError:
                got = {"verdict": "reject"}
            out[key] = got
            if got == pi[key]:
                agree += 1
            else:
                differ.append(key)
    return out, agree, differ


if __name__ == "__main__":
    if sys.argv[1] == "cases":
        data = cases()
        with open(sys.argv[2], "w", encoding="utf-8", newline="\n") as handle:
            json.dump(data, handle, indent=1)
        print(len(data))
    else:
        sys.path.insert(0, sys.argv[2])
        pi = json.load(open(sys.argv[3], encoding="utf-8"))
        out, agree, differ = minion(pi)
        with open(sys.argv[4], "w", encoding="utf-8", newline="\n") as handle:
            json.dump({"cells": out, "agree": agree, "differ": differ}, handle, indent=1)
        print("agree", agree, "differ", len(differ))
        for key in differ:
            print("DIFFER", key, "pi", pi[key], "minion", out[key])
