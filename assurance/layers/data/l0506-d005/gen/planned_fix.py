"""L0506-D005 planned Python correction, applied to a DISPOSABLE copy of minion-agent-python for the
contract-stage controls (the contract candidate itself carries no production change).

    python planned_fix.py <copy of minion-agent-python>
"""

import pathlib
import sys

root = pathlib.Path(sys.argv[1])


def patch(relative: str, old: str, new: str) -> None:
    path = root / relative
    text = path.read_text(encoding="utf-8")
    assert text.count(old) == 1, (relative, old[:60])
    path.write_text(text.replace(old, new), encoding="utf-8")


patch(
    "src/minion_agent/llm/js_object.py",
    "def order_raw(arguments: Any) -> Any:",
    '''def structured_clone(value: Any) -> Any:
    """`L0506-D005` (`TOOL-003`): pinned Pi's `structuredClone` of the prepared arguments. Every
    object and array reachable from `value` is copied exactly once -- a container reached twice
    becomes ONE copy, so aliases and cycles inside the graph survive -- as a `JsObject` / `JsArray`
    enumerating as its source does. Every other value is carried as is. The copy shares no
    container with `value`. Iterative, so nesting depth is not bounded by the interpreter stack."""

    def fresh(item: Any) -> Any:
        return JsObject() if isinstance(item, dict) else JsArray()

    if not isinstance(value, (dict, list)):
        return value
    memo: dict[int, Any] = {id(value): fresh(value)}
    pending = [value]
    while pending:
        source = pending.pop()
        target = memo[id(source)]
        children = dict.items(source) if isinstance(source, dict) else enumerate(list.__iter__(source))
        for key, child in children:
            if isinstance(child, (dict, list)):
                if id(child) not in memo:
                    memo[id(child)] = fresh(child)
                    pending.append(child)
                child = memo[id(child)]
            if isinstance(target, dict):
                dict.__setitem__(target, key, child)
            else:
                list.append(target, child)
    return order_in_place(memo[id(value)])


def order_raw(arguments: Any) -> Any:''',
)
patch(
    "src/minion_agent/tools/execute.py",
    "from ..llm.js_object import JsArray, JsObject, adopt, order_in_place, order_raw",
    "from ..llm.js_object import JsArray, JsObject, adopt, order_in_place, order_raw, structured_clone",
)
patch(
    "src/minion_agent/tools/execute.py",
    '''    if isinstance(definition.parameters, dict):
        try:
            PreparedArgumentsValidator(definition.parameters).validate(arguments)
        except JsonSchemaValidationError as error:
            raise ArgumentValidationError(error.message) from error
        # `L0206-D001` (K1): validation never reorders -- the validated object enumerates as its
        # input did (pinned Pi's `structuredClone` + `Value.Convert`); no schema order is imposed.
        validated: dict[str, Any] = order_in_place(JsObject(arguments))
        return validated''',
    '''    if isinstance(definition.parameters, dict):
        # `L0506-D005`: validation works on pinned Pi's `structuredClone` of the prepared arguments,
        # so a hook's or `execute`'s mutation never reaches the raw object through a nested alias.
        # `L0206-D001` (K1): the clone enumerates as its input did; no schema order is imposed.
        validated: dict[str, Any] = structured_clone(arguments)
        try:
            PreparedArgumentsValidator(definition.parameters).validate(validated)
        except JsonSchemaValidationError as error:
            raise ArgumentValidationError(error.message) from error
        return validated''',
)
print("planned fix applied")
