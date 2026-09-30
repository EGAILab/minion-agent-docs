"""CE-L0506-D001-I001-01 characterization matrix: pydantic-model tools vs pinned Pi on the model's JSON schema.

    python matrix.py cases <out.json>          -- emit cases (JSON schema + prepared arguments as tokens)
    python matrix.py rule  <out.json>          -- the proposed finite-variant rule's verdict per case

The Pi verdict comes from authority.mjs (pinned validateToolArguments over each case's JSON schema).
"""
import json
import math
import sys
from dataclasses import dataclass
from typing import Annotated, Any, TypedDict

from pydantic import AllowInfNan, BaseModel, ConfigDict, ValidationError, create_model

F = Annotated[float, AllowInfNan(False)]


class Inner(BaseModel):
    y: float


class InnerF(BaseModel):
    y: F


class Box(TypedDict):
    w: float


class BoxF(TypedDict):
    w: F


@dataclass
class Pt:
    x: float


@dataclass
class PtF:
    x: F


# (id, annotation, finite-variant annotation, value-token builder)
ROWS = [
    ("scalar", float, F),
    ("nullable-numeric-first", float | None, F | None),
    ("nullable-none-first", None | float, None | F),
    ("numeric-or-string", float | str, F | str),
    ("string-or-numeric", str | float, str | F),
    ("numeric-or-any", float | Any, F | Any),
    ("any-or-numeric", Any | float, Any | F),
    ("numeric-or-object", float | object, F | object),
    ("list-numeric", list[float], list[F]),
    ("list-numeric-or-list-any", list[float] | list[Any], list[F] | list[Any]),
    ("list-any-or-list-numeric", list[Any] | list[float], list[Any] | list[F]),
    ("dict-numeric", dict[str, float], dict[str, F]),
    ("dict-numeric-or-dict-any", dict[str, float] | dict[str, Any], dict[str, F] | dict[str, Any]),
    ("dict-any-or-dict-numeric", dict[str, Any] | dict[str, float], dict[str, Any] | dict[str, F]),
    ("model", Inner, InnerF),
    ("model-or-dict-any", Inner | dict[str, Any], InnerF | dict[str, Any]),
    ("dict-any-or-model", dict[str, Any] | Inner, dict[str, Any] | InnerF),
    ("typeddict", Box, BoxF),
    ("dataclass", Pt, PtF),
    ("any", Any, Any),
]
SHAPES = {  # how the non-finite value is placed for each row
    "list": lambda v: [1.0, v], "dict": lambda v: {"k": v}, "model": lambda v: {"y": v},
    "typeddict": lambda v: {"w": v}, "dataclass": lambda v: {"x": v},
}


def shape(row_id):
    """The value's shape for a row: exact-name rows first (typeddict/dataclass/model), then containers."""
    for key in ("typeddict", "dataclass"):
        if row_id == key:
            return SHAPES[key]
    if row_id in ("model", "model-or-dict-any", "dict-any-or-model"):
        return SHAPES["model"]
    for key in ("list", "dict"):
        if row_id.startswith(key):
            return SHAPES[key]
    return lambda v: v


VALUES = {"+Infinity": math.inf, "-Infinity": -math.inf, "NaN": math.nan, "-0": -0.0, "1e308": 1e308}


def tokenize(v):
    if isinstance(v, float):
        if math.isnan(v):
            return {"$num": "NaN"}
        if math.isinf(v):
            return {"$num": "+Infinity" if v > 0 else "-Infinity"}
        if v == 0 and math.copysign(1, v) < 0:
            return {"$num": "-0"}
        return v
    if isinstance(v, dict):
        return {k: tokenize(x) for k, x in v.items()}
    if isinstance(v, list):
        return [tokenize(x) for x in v]
    return v


def cases():
    out = []
    for row_id, ann, _ in ROWS:
        model = create_model("M", __config__=ConfigDict(arbitrary_types_allowed=True), field=(ann, ...))
        schema = model.model_json_schema()
        for tok, v in VALUES.items():
            out.append({"id": f"{row_id}/{tok}", "schema": schema, "arguments": tokenize({"field": shape(row_id)(v)})})
    return out


def rule():
    out = {}
    for row_id, ann, fin in ROWS:
        original = create_model("M", field=(ann, ...))
        finite = create_model("MF", field=(fin, ...))
        for tok, v in VALUES.items():
            args = {"field": shape(row_id)(v)}
            try:
                original.model_validate(args)
            except ValidationError:
                out[f"{row_id}/{tok}"] = "pydantic-rejects"
                continue
            try:
                finite.model_validate(args)
                out[f"{row_id}/{tok}"] = "accept"
            except ValidationError:
                out[f"{row_id}/{tok}"] = "reject"
    return out


if __name__ == "__main__":
    data = cases() if sys.argv[1] == "cases" else rule()
    with open(sys.argv[2], "w", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, indent=1)
    print(len(data))
