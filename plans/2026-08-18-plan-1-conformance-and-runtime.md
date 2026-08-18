# Minion Agent — Plan 1: Conformance Harness and Plugin Runtime

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the language-neutral conformance scenario formats and the Cordis-semantic plugin runtime they validate, so every later subsystem mounts as a plugin against a runtime whose semantics are pinned by executable cases.

**Architecture:** A `Context` is a repository of services. A `Fiber` is one loaded plugin instance owning validated config, lifecycle state, and a reverse-ordered disposable list. Services register exclusively by name; dependents load when their injected services appear and unload when any disappears, unwinding effects in reverse. Events dispatch in four declared modes. Conformance scenarios are YAML data describing plugins declaratively and asserting an ordered lifecycle/effect trace.

**Tech Stack:** Python 3.12+, `pydantic` v2 (plugin config + JSON Schema export), `pytest` + `pytest-asyncio`, `hypothesis` (property tests), `PyYAML` (scenario files), `jsonschema` (scenario validation), `ruff` (lint/format), `mypy` (types), `pytest-cov` (coverage gate).

**Spec:** `minion-agent-docs/design/2026-08-18-minion-agent-design.md` — read §3 (plugin runtime), §8 (validation), §9 (build order) before starting. The plan argues from the spec; where they disagree, the spec wins and the plan is the bug.

## Global Constraints

- **Python floor:** 3.12. Use `type` statements, `StrEnum`, and PEP 695 generics freely.
- **Interpreter, on this machine:** bare `python` on PATH is the Windows Store stub — it exits with code 49 and does nothing, which fails *silently* inside shell pipelines. Real interpreters are `py -3.12` (`E:\AI\Python\Python312`) and `py -3.13`. `uv` is installed at `~/.local/bin/uv`. Create the environment once with `uv venv --python 3.12 && uv pip install -e ".[dev]"`, then run tools from `.venv/Scripts/` (Windows) so no command depends on PATH resolution. Never invoke bare `python` in a script or CI step.
- **Async:** `asyncio` throughout. Every lifecycle operation that can await, awaits.
- **Naming:** the package is `minion_agent.runtime`. Cordis is credited in prose and docstrings as design lineage ("Cordis-semantic", "Cordis-inspired") and **never** appears in a module path, class name, or public identifier.
- **Coverage:** `src/minion_agent/runtime/**` targets 100% per-file. Exceptions require a `# pragma: no cover` with a written reason on the same line.
- **Conformance rule:** every externally meaningful runtime behavior change must be represented in `conformance/`. Extending or parameterizing an existing scenario counts.
- **Normativity:** for behavior a scenario covers, the executable result is the oracle. Prose defines the general rule elsewhere.
- **Deferred, do not implement:** isolation realms, service shadowing (they are one mechanism), the declarative YAML loader, hot module replacement. A child context **cannot** shadow a parent service in this phase.
- **Commit style:** conventional commits (`feat:`, `test:`, `chore:`, `docs:`). Commit at the end of every task.

---

## File Structure

```
minion-agent/
  pyproject.toml                          # deps, pytest/ruff/mypy/coverage config
  src/minion_agent/
    __init__.py
    runtime/
      __init__.py                         # public surface re-exports
      errors.py                           # exception hierarchy
      disposable.py                       # Disposer type, DisposableList
      events.py                           # EventBus, DispatchMode, declarations
      service.py                          # ServiceRegistry, Impl, resolution
      fiber.py                            # Fiber, FiberState, effects, lifecycle
      context.py                          # Context, service access, plugin mounting
      plugin.py                           # @plugin decorator, PluginSpec
  conformance/
    schema/
      runtime-scenario.schema.json        # runtime/ family format
      agent-scenario.schema.json          # agent/ family format
      README.md                           # runner contract
    runtime/
      *.yaml                              # executable kernel cases
    agent/
      .gitkeep                            # populated in Plan 2
  tests/
    conformance/
      runner.py                           # scenario loader + trace-recording harness
      test_schema_validation.py           # every scenario validates against its schema
      test_runtime_conformance.py         # executes conformance/runtime/*.yaml
    runtime/
      test_*.py                           # Python-specific (tier 2) tests
```

Responsibilities are split so each file holds one concern and stays small enough to reason about whole: `service.py` knows nothing about lifecycle, `fiber.py` owns lifecycle and effects, `context.py` is the user-facing façade, and `events.py` is independent of both.

---

# Phase 0 — Conformance scenario formats

## Task 1: Project scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `src/minion_agent/__init__.py`
- Create: `src/minion_agent/runtime/__init__.py`
- Test: `tests/test_scaffold.py`

**Interfaces:**
- Consumes: nothing.
- Produces: an installed `minion_agent` package exposing `__version__: str`; a working `pytest` invocation; `ruff` and `mypy` configured.

- [ ] **Step 1: Write the failing test**

Create `tests/test_scaffold.py`:

```python
"""The package imports and reports a version."""

import minion_agent


def test_package_exposes_version() -> None:
    assert isinstance(minion_agent.__version__, str)
    assert minion_agent.__version__
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_scaffold.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'minion_agent'`

- [ ] **Step 3: Write minimal implementation**

Create `pyproject.toml`:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "minion-agent"
version = "0.1.0"
description = "Agent runtime with a Cordis-inspired plugin architecture"
requires-python = ">=3.12"
dependencies = [
    "pydantic>=2.7",
    "pyyaml>=6.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "pytest-cov>=5.0",
    "hypothesis>=6.100",
    "jsonschema>=4.22",
    "ruff>=0.5",
    "mypy>=1.10",
]

[tool.hatch.build.targets.wheel]
packages = ["src/minion_agent"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
addopts = "-q"

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM", "RUF"]

[tool.mypy]
python_version = "3.12"
strict = true
files = ["src/minion_agent"]

[tool.coverage.run]
source = ["src/minion_agent/runtime"]

[tool.coverage.report]
fail_under = 100
show_missing = true
exclude_lines = ["pragma: no cover"]
```

Create `src/minion_agent/__init__.py`:

```python
"""Minion Agent — an agent runtime with a Cordis-inspired plugin architecture."""

__version__ = "0.1.0"
```

Create `src/minion_agent/runtime/__init__.py`:

```python
"""The plugin runtime: contexts, fibers, services, events, and reversible effects.

Cordis-semantic, not a Cordis port. See the design spec, section 3.
"""
```

- [ ] **Step 4: Create the environment and run the test**

Run, from the repository root:

```bash
uv venv --python 3.12
uv pip install -e ".[dev]"
.venv/Scripts/pytest tests/test_scaffold.py -v
```

Expected: PASS

Every later `pytest`, `ruff`, and `mypy` invocation in this plan means the one
in `.venv/Scripts/`. Bare `python` is the Store stub and must never be used
(see Global Constraints).

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/minion_agent tests/test_scaffold.py
git commit -m "chore: scaffold package, test, lint, and type configuration"
```

---

## Task 2: Runtime scenario format

The `runtime/` family asserts a generic lifecycle and effect trace. Unlike agent scenarios — where the "program" is already data (a provider script and tool stubs) — here the plugin *behavior* is what's under test, so the format needs a declarative vocabulary for it.

**Files:**
- Create: `conformance/schema/runtime-scenario.schema.json`
- Create: `conformance/runtime/effect-reversal.yaml`
- Create: `conformance/runtime/reactive-dependency.yaml`
- Test: `tests/conformance/test_schema_validation.py`

**Interfaces:**
- Consumes: nothing.
- Produces: the runtime scenario format. Task 15's runner reads exactly these keys: top-level `name`, `description`, `plugins`, `steps`, `expect_trace`, optional `expect_result`, optional `expect_error`. A plugin entry has `id`, optional `inject` (list of service names), optional `provides` (service name), optional `config` (object), optional `effects` (list of `{label}`), optional `listeners` (list of `{event, action, tag, returns?}`), optional `fails` (bool). A step is exactly one of `{mount: id}`, `{unmount: id}`, or `{dispatch: {event, mode, args?}}`. Trace entries are `{event, ...fields}` where `event` is one of `fiber_state`, `effect_created`, `effect_disposed`, `listener_entered`, `service_provided`, `service_revoked`.

- [ ] **Step 1: Write the failing test**

Create `tests/conformance/test_schema_validation.py`:

```python
"""Every conformance scenario validates against its family's JSON Schema."""

import json
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

CONFORMANCE = Path(__file__).resolve().parents[2] / "conformance"

FAMILIES = {
    "runtime": CONFORMANCE / "schema" / "runtime-scenario.schema.json",
}


def _scenarios(family: str) -> list[Path]:
    return sorted((CONFORMANCE / family).glob("*.yaml"))


@pytest.mark.parametrize("family", sorted(FAMILIES))
def test_family_has_scenarios(family: str) -> None:
    assert _scenarios(family), f"conformance/{family}/ has no scenarios"


@pytest.mark.parametrize(
    ("family", "scenario"),
    [(f, s) for f in sorted(FAMILIES) for s in _scenarios(f)],
    ids=lambda value: value.stem if isinstance(value, Path) else value,
)
def test_scenario_validates(family: str, scenario: Path) -> None:
    schema = json.loads(FAMILIES[family].read_text(encoding="utf-8"))
    document = yaml.safe_load(scenario.read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(schema).iter_errors(document),
        key=lambda error: list(error.path),
    )
    assert not errors, "\n".join(
        f"{'/'.join(str(part) for part in error.path)}: {error.message}" for error in errors
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/conformance/test_schema_validation.py -v`
Expected: FAIL — the schema file does not exist (`FileNotFoundError`), and `test_family_has_scenarios` fails on the empty directory.

- [ ] **Step 3: Write the schema**

Create `conformance/schema/runtime-scenario.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://minion-agent.dev/conformance/runtime-scenario.schema.json",
  "title": "Minion Agent runtime conformance scenario",
  "type": "object",
  "required": ["name", "plugins", "steps", "expect_trace"],
  "additionalProperties": false,
  "properties": {
    "name": { "type": "string", "minLength": 1 },
    "description": { "type": "string" },
    "plugins": {
      "type": "array",
      "minItems": 1,
      "items": { "$ref": "#/$defs/plugin" }
    },
    "steps": {
      "type": "array",
      "minItems": 1,
      "items": { "$ref": "#/$defs/step" }
    },
    "expect_trace": {
      "type": "array",
      "items": { "$ref": "#/$defs/traceEntry" }
    },
    "expect_result": {},
    "expect_error": {
      "type": "object",
      "required": ["type"],
      "additionalProperties": false,
      "properties": {
        "type": {
          "enum": [
            "ServiceConflictError",
            "InactiveFiberError",
            "ServiceNotFoundError",
            "EventModeError"
          ]
        },
        "message_contains": { "type": "string" }
      }
    }
  },
  "$defs": {
    "serviceName": { "type": "string", "pattern": "^[a-z][a-z0-9_]*$" },
    "plugin": {
      "type": "object",
      "required": ["id"],
      "additionalProperties": false,
      "properties": {
        "id": { "type": "string", "minLength": 1 },
        "inject": { "type": "array", "items": { "$ref": "#/$defs/serviceName" } },
        "provides": { "$ref": "#/$defs/serviceName" },
        "config": { "type": "object" },
        "fails": { "type": "boolean", "default": false },
        "effects": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["label"],
            "additionalProperties": false,
            "properties": { "label": { "type": "string", "minLength": 1 } }
          }
        },
        "listeners": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["event", "action", "tag"],
            "additionalProperties": false,
            "properties": {
              "event": { "type": "string", "minLength": 1 },
              "action": { "enum": ["delegate", "short_circuit", "observe", "raise"] },
              "tag": { "type": "string", "minLength": 1 },
              "returns": {}
            }
          }
        }
      }
    },
    "step": {
      "type": "object",
      "additionalProperties": false,
      "minProperties": 1,
      "maxProperties": 1,
      "properties": {
        "mount": { "type": "string" },
        "unmount": { "type": "string" },
        "dispatch": {
          "type": "object",
          "required": ["event", "mode"],
          "additionalProperties": false,
          "properties": {
            "event": { "type": "string", "minLength": 1 },
            "mode": { "enum": ["emit", "parallel", "serial", "waterfall"] },
            "args": { "type": "array" }
          }
        }
      }
    },
    "traceEntry": {
      "type": "object",
      "required": ["event"],
      "additionalProperties": false,
      "properties": {
        "event": {
          "enum": [
            "fiber_state",
            "effect_created",
            "effect_disposed",
            "listener_entered",
            "service_provided",
            "service_revoked"
          ]
        },
        "plugin": { "type": "string" },
        "state": {
          "enum": ["pending", "loading", "active", "failed", "unloading", "disposed"]
        },
        "label": { "type": "string" },
        "tag": { "type": "string" },
        "service": { "$ref": "#/$defs/serviceName" }
      }
    }
  }
}
```

- [ ] **Step 4: Write the two example scenarios**

Create `conformance/runtime/effect-reversal.yaml`:

```yaml
name: effects dispose in reverse creation order when a fiber unloads
description: >
  A fiber creating three labelled effects must dispose them last-created-first
  on unload. Reverse order is normative, not incidental.
plugins:
  - id: subject
    effects:
      - label: first
      - label: second
      - label: third
steps:
  - mount: subject
  - unmount: subject
expect_trace:
  - { event: fiber_state, plugin: subject, state: loading }
  - { event: effect_created, plugin: subject, label: first }
  - { event: effect_created, plugin: subject, label: second }
  - { event: effect_created, plugin: subject, label: third }
  - { event: fiber_state, plugin: subject, state: active }
  - { event: fiber_state, plugin: subject, state: unloading }
  - { event: effect_disposed, plugin: subject, label: third }
  - { event: effect_disposed, plugin: subject, label: second }
  - { event: effect_disposed, plugin: subject, label: first }
  - { event: fiber_state, plugin: subject, state: disposed }
```

Create `conformance/runtime/reactive-dependency.yaml`:

```yaml
name: a dependent fiber loads when its service appears and unloads when it disappears
description: >
  The consumer declares inject:[tools] and is mounted before any provider
  exists, so it must stay pending. Mounting the provider activates it;
  unmounting the provider unloads it again, unwinding its effects in reverse.
  Services appearing and vanishing at runtime is a normal condition.
plugins:
  - id: consumer
    inject: [tools]
    effects:
      - label: subscription
      - label: resource
  - id: provider
    provides: tools
steps:
  - mount: consumer
  - mount: provider
  - unmount: provider
expect_trace:
  - { event: fiber_state, plugin: provider, state: loading }
  - { event: service_provided, plugin: provider, service: tools }
  - { event: fiber_state, plugin: provider, state: active }
  - { event: fiber_state, plugin: consumer, state: loading }
  - { event: effect_created, plugin: consumer, label: subscription }
  - { event: effect_created, plugin: consumer, label: resource }
  - { event: fiber_state, plugin: consumer, state: active }
  - { event: fiber_state, plugin: provider, state: unloading }
  - { event: service_revoked, plugin: provider, service: tools }
  - { event: fiber_state, plugin: consumer, state: unloading }
  - { event: effect_disposed, plugin: consumer, label: resource }
  - { event: effect_disposed, plugin: consumer, label: subscription }
  - { event: fiber_state, plugin: consumer, state: pending }
  - { event: fiber_state, plugin: provider, state: disposed }
```

Note the asymmetry, which is deliberate and normative: the consumer returns to `pending` (its plugin is still mounted, merely unsatisfied) while the explicitly unmounted provider reaches `disposed`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/conformance/test_schema_validation.py -v`
Expected: PASS — three tests (one `test_family_has_scenarios`, two `test_scenario_validates`).

- [ ] **Step 6: Commit**

```bash
git add conformance/schema/runtime-scenario.schema.json conformance/runtime tests/conformance
git commit -m "feat: add runtime conformance scenario format with lifecycle and effect cases"
```

---

## Task 3: Agent scenario format and runner contract

The `agent/` family is populated in Plan 2, but its format is fixed now so Plan 2 writes scenarios rather than designing a vocabulary mid-flight.

**Files:**
- Create: `conformance/schema/agent-scenario.schema.json`
- Create: `conformance/agent/.gitkeep`
- Create: `conformance/schema/README.md`
- Modify: `tests/conformance/test_schema_validation.py`

**Interfaces:**
- Consumes: the test module from Task 2.
- Produces: the agent scenario format — top-level `name`, `description`, `provider_script`, `tools`, `config`, `steps`, `expect_events`. Plan 2's runner reads these keys.

- [ ] **Step 1: Write the failing test**

Modify `tests/conformance/test_schema_validation.py` — replace the `FAMILIES` mapping and add an allowance for the not-yet-populated family:

```python
FAMILIES = {
    "runtime": CONFORMANCE / "schema" / "runtime-scenario.schema.json",
    "agent": CONFORMANCE / "schema" / "agent-scenario.schema.json",
}

# Families whose scenarios arrive in a later plan. Their schema must still exist
# and must still be a valid JSON Schema.
UNPOPULATED = {"agent"}
```

Replace `test_family_has_scenarios` and add a schema-wellformedness test:

```python
@pytest.mark.parametrize("family", sorted(FAMILIES))
def test_family_has_scenarios(family: str) -> None:
    if family in UNPOPULATED:
        pytest.skip(f"conformance/{family}/ is populated in a later plan")
    assert _scenarios(family), f"conformance/{family}/ has no scenarios"


@pytest.mark.parametrize("family", sorted(FAMILIES))
def test_family_schema_is_wellformed(family: str) -> None:
    schema = json.loads(FAMILIES[family].read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/conformance/test_schema_validation.py -v`
Expected: FAIL — `test_family_schema_is_wellformed[agent]` raises `FileNotFoundError`.

- [ ] **Step 3: Write the agent schema**

Create `conformance/schema/agent-scenario.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://minion-agent.dev/conformance/agent-scenario.schema.json",
  "title": "Minion Agent agent conformance scenario",
  "type": "object",
  "required": ["name", "provider_script", "steps", "expect_events"],
  "additionalProperties": false,
  "properties": {
    "name": { "type": "string", "minLength": 1 },
    "description": { "type": "string" },
    "config": { "type": "object" },
    "provider_script": {
      "type": "array",
      "minItems": 1,
      "items": { "$ref": "#/$defs/scriptedResponse" }
    },
    "tools": {
      "type": "object",
      "additionalProperties": { "$ref": "#/$defs/toolStub" }
    },
    "steps": {
      "type": "array",
      "minItems": 1,
      "items": { "$ref": "#/$defs/step" }
    },
    "expect_events": { "type": "array" },
    "expect_messages": { "type": "array" }
  },
  "$defs": {
    "scriptedResponse": {
      "type": "object",
      "required": ["stop_reason"],
      "additionalProperties": false,
      "properties": {
        "content": { "type": "array", "items": { "$ref": "#/$defs/contentBlock" } },
        "stop_reason": {
          "enum": ["stop", "length", "tool_use", "error", "aborted"]
        },
        "error_message": { "type": "string" },
        "usage": { "type": "object" }
      }
    },
    "contentBlock": {
      "type": "object",
      "required": ["type"],
      "properties": {
        "type": { "enum": ["text", "thinking", "tool_call"] },
        "text": { "type": "string" },
        "thinking": { "type": "string" },
        "id": { "type": "string" },
        "name": { "type": "string" },
        "arguments": { "type": "object" }
      }
    },
    "toolStub": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "result": { "type": "object" },
        "raises": { "type": "string" },
        "execution_mode": { "enum": ["parallel", "sequential"] },
        "delay_ticks": { "type": "integer", "minimum": 0 }
      }
    },
    "step": {
      "type": "object",
      "additionalProperties": false,
      "minProperties": 1,
      "maxProperties": 1,
      "properties": {
        "followup": { "type": "string" },
        "steer": { "type": "string" },
        "inject": { "type": "string" },
        "abort": { "type": "boolean" },
        "await_idle": { "type": "boolean" }
      }
    }
  }
}
```

`delay_ticks` is a logical clock, not wall time — tool completion order must be deterministic without sleeping.

- [ ] **Step 4: Write the runner contract**

Create `conformance/schema/README.md`:

```markdown
# Conformance runner contract

These scenarios are the executable half of the Minion Agent specification.
They are language-neutral data: any implementation ships a thin runner that
feeds them to its own code and diffs the observed trace.

## Families

| Family | Asserts |
|---|---|
| `runtime/` | A generic lifecycle and effect trace — mount and unmount operations in, ordered fiber-state transitions and effect disposals out. |
| `agent/` | The session-log projection and the derived Pi event stream. |

## Rules for every runner

1. **Assert on observable output only.** The trace and the log projection are
   the surface. A runner that inspects implementation internals is not
   conformant, and its scenarios will not port.
2. **Order is significant** unless a scenario marks an entry otherwise.
   Reverse-order effect disposal and source-order tool results are behavior,
   not implementation detail.
3. **No wall-clock time.** Scenarios settle on state transitions and logical
   ticks. A runner that sleeps is wrong even when it passes.
4. **Unknown keys are errors.** Both schemas set `additionalProperties: false`
   so a scenario using a feature a runner has not implemented fails loudly
   rather than silently skipping.
5. **Trace comparison is exact.** Extra observed entries fail the case, as do
   missing ones. A scenario that needs to permit variation says so explicitly.

## Normativity

For behavior a scenario covers, the executable result is the compatibility
oracle. The prose spec (`minion-agent-docs/spec/`) defines the general
semantic rule and the behavior that cannot be exhaustively enumerated.
Behavior is not "unspecified" merely because no scenario encodes it yet.
```

- [ ] **Step 5: Create the placeholder directory and run tests**

```bash
touch conformance/agent/.gitkeep
```

Run: `pytest tests/conformance/test_schema_validation.py -v`
Expected: PASS — the `agent` family skips its scenario test and passes wellformedness.

- [ ] **Step 6: Commit**

```bash
git add conformance/schema conformance/agent tests/conformance
git commit -m "feat: add agent conformance scenario format and runner contract"
```

---

# Phase 1 — Plugin runtime

## Task 4: Errors and the disposable list

**Files:**
- Create: `src/minion_agent/runtime/errors.py`
- Create: `src/minion_agent/runtime/disposable.py`
- Test: `tests/runtime/test_disposable.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `RuntimeError_` base, plus `ServiceConflictError`, `InactiveFiberError`, `ServiceNotFoundError`, `EventModeError`.
  - `type Disposer = Callable[[], Awaitable[None] | None]`
  - `DisposableList` with `push(disposer: Disposer) -> Callable[[], None]`, `async dispose_all() -> None` (reverse order, idempotent), and `__len__`.

- [ ] **Step 1: Write the failing test**

Create `tests/runtime/test_disposable.py`:

```python
"""DisposableList unwinds in reverse and is idempotent."""

from minion_agent.runtime.disposable import DisposableList


async def test_disposes_in_reverse_order() -> None:
    order: list[str] = []
    disposables = DisposableList()
    for label in ("first", "second", "third"):
        disposables.push(lambda label=label: order.append(label))

    await disposables.dispose_all()

    assert order == ["third", "second", "first"]


async def test_dispose_all_is_idempotent() -> None:
    order: list[str] = []
    disposables = DisposableList()
    disposables.push(lambda: order.append("once"))

    await disposables.dispose_all()
    await disposables.dispose_all()

    assert order == ["once"]


async def test_awaits_async_disposers() -> None:
    order: list[str] = []
    disposables = DisposableList()

    async def async_disposer() -> None:
        order.append("async")

    disposables.push(async_disposer)
    disposables.push(lambda: order.append("sync"))

    await disposables.dispose_all()

    assert order == ["sync", "async"]


async def test_remove_handle_prevents_later_disposal() -> None:
    order: list[str] = []
    disposables = DisposableList()
    disposables.push(lambda: order.append("kept"))
    remove = disposables.push(lambda: order.append("removed"))

    remove()
    await disposables.dispose_all()

    assert order == ["kept"]


async def test_all_disposers_run_even_when_one_raises() -> None:
    order: list[str] = []
    disposables = DisposableList()
    disposables.push(lambda: order.append("first"))
    disposables.push(lambda: (_ for _ in ()).throw(ValueError("boom")))
    disposables.push(lambda: order.append("third"))

    with pytest.raises(ExceptionGroup) as excinfo:
        await disposables.dispose_all()

    assert order == ["third", "first"]
    assert len(excinfo.value.exceptions) == 1
```

Add `import pytest` at the top of the file.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/runtime/test_disposable.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'minion_agent.runtime.disposable'`

- [ ] **Step 3: Write the implementation**

Create `src/minion_agent/runtime/errors.py`:

```python
"""Exception hierarchy for the plugin runtime.

These are programming and composition errors. Operational failures at the
capability seams are values, not exceptions — see the design spec, section 7.
"""


class RuntimeError_(Exception):
    """Base for every runtime error.

    Named with a trailing underscore to avoid shadowing the builtin while
    keeping the public alias `errors.RuntimeError_` unambiguous at call sites.
    """


class ServiceConflictError(RuntimeError_):
    """A second plugin tried to provide a service that is already provided."""


class InactiveFiberError(RuntimeError_):
    """An effect was created on a fiber that is no longer active."""


class ServiceNotFoundError(RuntimeError_):
    """A service was accessed that no active provider supplies."""


class EventModeError(RuntimeError_):
    """An event was dispatched in a mode other than the one it declared."""
```

Create `src/minion_agent/runtime/disposable.py`:

```python
"""Reverse-ordered disposal, the primitive behind reversible effects."""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from typing import Any

type Disposer = Callable[[], Awaitable[None] | None]


class DisposableList:
    """An ordered collection of disposers, unwound last-in-first-out.

    Reverse order is normative: a later effect may depend on an earlier one,
    so tearing down in creation order could observe a half-disposed world.
    """

    __slots__ = ("_disposers", "_disposed")

    def __init__(self) -> None:
        self._disposers: list[Disposer | None] = []
        self._disposed = False

    def __len__(self) -> int:
        return sum(1 for disposer in self._disposers if disposer is not None)

    def push(self, disposer: Disposer) -> Callable[[], None]:
        """Register `disposer`; returns a handle that removes it without running it."""
        index = len(self._disposers)
        self._disposers.append(disposer)

        def remove() -> None:
            self._disposers[index] = None

        return remove

    async def dispose_all(self) -> None:
        """Run every disposer in reverse order, exactly once.

        Every disposer runs even if one raises; failures are collected and
        re-raised together, because a disposer that fails must not strand the
        ones queued behind it.
        """
        if self._disposed:
            return
        self._disposed = True

        failures: list[Exception] = []
        for disposer in reversed(self._disposers):
            if disposer is None:
                continue
            try:
                result: Any = disposer()
                if inspect.isawaitable(result):
                    await result
            except Exception as error:  # noqa: BLE001 - collected and re-raised below
                failures.append(error)

        self._disposers.clear()
        if failures:
            raise ExceptionGroup("errors while disposing", failures)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/runtime/test_disposable.py -v`
Expected: PASS — five tests.

- [ ] **Step 5: Commit**

```bash
git add src/minion_agent/runtime/errors.py src/minion_agent/runtime/disposable.py tests/runtime/test_disposable.py
git commit -m "feat: add runtime error hierarchy and reverse-ordered disposable list"
```

---

## Task 5: Event bus — declarations, `on`, and `emit`

**Files:**
- Create: `src/minion_agent/runtime/events.py`
- Test: `tests/runtime/test_events_emit.py`

**Interfaces:**
- Consumes: `errors.EventModeError`, `disposable.Disposer`.
- Produces:
  - `class DispatchMode(StrEnum)` with `EMIT`, `PARALLEL`, `SERIAL`, `WATERFALL`.
  - `class EventBus` with `declare(name: str, mode: DispatchMode) -> None`, `mode_of(name: str) -> DispatchMode`, `on(name: str, listener: Callable[..., Any], *, prepend: bool = False) -> Callable[[], None]`, `emit(name: str, *args: Any) -> None`.
  - Later tasks add `parallel`, `serial`, `waterfall` to the same class.

- [ ] **Step 1: Write the failing test**

Create `tests/runtime/test_events_emit.py`:

```python
"""Event declarations bind a dispatch mode; emit is synchronous and unawaited."""

import pytest

from minion_agent.runtime.errors import EventModeError
from minion_agent.runtime.events import DispatchMode, EventBus


def test_emit_calls_listeners_in_registration_order() -> None:
    bus = EventBus()
    bus.declare("test/emit", DispatchMode.EMIT)
    seen: list[str] = []
    bus.on("test/emit", lambda: seen.append("first"))
    bus.on("test/emit", lambda: seen.append("second"))

    bus.emit("test/emit")

    assert seen == ["first", "second"]


def test_prepend_puts_listener_first() -> None:
    bus = EventBus()
    bus.declare("test/emit", DispatchMode.EMIT)
    seen: list[str] = []
    bus.on("test/emit", lambda: seen.append("ordinary"))
    bus.on("test/emit", lambda: seen.append("prepended"), prepend=True)

    bus.emit("test/emit")

    assert seen == ["prepended", "ordinary"]


def test_disposer_removes_listener() -> None:
    bus = EventBus()
    bus.declare("test/emit", DispatchMode.EMIT)
    seen: list[str] = []
    dispose = bus.on("test/emit", lambda: seen.append("gone"))

    dispose()
    bus.emit("test/emit")

    assert seen == []


def test_emit_passes_arguments() -> None:
    bus = EventBus()
    bus.declare("test/emit", DispatchMode.EMIT)
    seen: list[tuple[int, str]] = []
    bus.on("test/emit", lambda number, label: seen.append((number, label)))

    bus.emit("test/emit", 7, "seven")

    assert seen == [(7, "seven")]


def test_dispatching_in_the_wrong_mode_raises() -> None:
    bus = EventBus()
    bus.declare("test/serial", DispatchMode.SERIAL)

    with pytest.raises(EventModeError, match="declared 'serial'"):
        bus.emit("test/serial")


def test_undeclared_event_raises() -> None:
    bus = EventBus()

    with pytest.raises(EventModeError, match="not declared"):
        bus.emit("test/unknown")


def test_redeclaring_with_a_different_mode_raises() -> None:
    bus = EventBus()
    bus.declare("test/emit", DispatchMode.EMIT)

    with pytest.raises(EventModeError, match="already declared"):
        bus.declare("test/emit", DispatchMode.SERIAL)


def test_redeclaring_with_the_same_mode_is_allowed() -> None:
    bus = EventBus()
    bus.declare("test/emit", DispatchMode.EMIT)
    bus.declare("test/emit", DispatchMode.EMIT)

    assert bus.mode_of("test/emit") is DispatchMode.EMIT
```

Redeclaring with the same mode is allowed because two plugins may legitimately declare a shared event; only a *conflicting* declaration is an error.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/runtime/test_events_emit.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'minion_agent.runtime.events'`

- [ ] **Step 3: Write the implementation**

Create `src/minion_agent/runtime/events.py`:

```python
"""Typed events with four declared dispatch modes.

Dispatch mode is part of an event's public contract: it is declared where the
event is declared, and a mismatch between declaration and dispatch site is an
error rather than a silent behavior change.
"""

from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum
from typing import Any

from .errors import EventModeError


class DispatchMode(StrEnum):
    """How an event's listeners are invoked and combined."""

    EMIT = "emit"
    """Fire and forget. Synchronous, registration order, no return value."""

    PARALLEL = "parallel"
    """Awaited, concurrent, no return value. Listener errors are aggregated."""

    SERIAL = "serial"
    """Awaited, registration order, returns a value."""

    WATERFALL = "waterfall"
    """Awaited around-middleware. A listener delegates via `next` or short-circuits."""


class _Listener:
    __slots__ = ("callback",)

    def __init__(self, callback: Callable[..., Any]) -> None:
        self.callback = callback


class EventBus:
    """Holds event declarations and their listeners."""

    __slots__ = ("_declarations", "_listeners")

    def __init__(self) -> None:
        self._declarations: dict[str, DispatchMode] = {}
        self._listeners: dict[str, list[_Listener]] = {}

    def declare(self, name: str, mode: DispatchMode) -> None:
        """Bind `name` to `mode`. Re-declaring the same mode is a no-op."""
        existing = self._declarations.get(name)
        if existing is None:
            self._declarations[name] = mode
            return
        if existing is not mode:
            raise EventModeError(
                f"event {name!r} is already declared {existing.value!r}; "
                f"cannot redeclare as {mode.value!r}"
            )

    def mode_of(self, name: str) -> DispatchMode:
        """Return the declared mode for `name`, raising when it is undeclared."""
        mode = self._declarations.get(name)
        if mode is None:
            raise EventModeError(f"event {name!r} is not declared")
        return mode

    def _require_mode(self, name: str, expected: DispatchMode) -> None:
        actual = self.mode_of(name)
        if actual is not expected:
            raise EventModeError(
                f"event {name!r} is declared {actual.value!r}; "
                f"it cannot be dispatched with {expected.value!r}"
            )

    def on(
        self,
        name: str,
        listener: Callable[..., Any],
        *,
        prepend: bool = False,
    ) -> Callable[[], None]:
        """Register `listener` for `name`; returns a disposer that removes it."""
        self.mode_of(name)
        entry = _Listener(listener)
        listeners = self._listeners.setdefault(name, [])
        if prepend:
            listeners.insert(0, entry)
        else:
            listeners.append(entry)

        def dispose() -> None:
            current = self._listeners.get(name)
            if current is not None and entry in current:
                current.remove(entry)

        return dispose

    def _chain(self, name: str) -> list[Callable[..., Any]]:
        return [entry.callback for entry in self._listeners.get(name, ())]

    def emit(self, name: str, *args: Any) -> None:
        """Invoke every listener synchronously in registration order."""
        self._require_mode(name, DispatchMode.EMIT)
        for callback in self._chain(name):
            callback(*args)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/runtime/test_events_emit.py -v`
Expected: PASS — eight tests.

- [ ] **Step 5: Commit**

```bash
git add src/minion_agent/runtime/events.py tests/runtime/test_events_emit.py
git commit -m "feat: add event bus with mode declarations and emit dispatch"
```

---

## Task 6: Event bus — `parallel` and `serial`

**Files:**
- Modify: `src/minion_agent/runtime/events.py`
- Test: `tests/runtime/test_events_async.py`

**Interfaces:**
- Consumes: `EventBus` from Task 5.
- Produces: `async parallel(name: str, *args: Any) -> None` and `async serial(name: str, *args: Any) -> Any` on `EventBus`.

- [ ] **Step 1: Write the failing test**

Create `tests/runtime/test_events_async.py`:

```python
"""Parallel fans out and aggregates errors; serial runs in order and returns."""

import asyncio

import pytest

from minion_agent.runtime.errors import EventModeError
from minion_agent.runtime.events import DispatchMode, EventBus


async def test_parallel_runs_listeners_concurrently() -> None:
    bus = EventBus()
    bus.declare("test/parallel", DispatchMode.PARALLEL)
    started = asyncio.Event()
    finished: list[str] = []

    async def slow() -> None:
        await started.wait()
        finished.append("slow")

    async def fast() -> None:
        started.set()
        finished.append("fast")

    bus.on("test/parallel", slow)
    bus.on("test/parallel", fast)

    await bus.parallel("test/parallel")

    assert finished == ["fast", "slow"]


async def test_parallel_aggregates_listener_errors() -> None:
    bus = EventBus()
    bus.declare("test/parallel", DispatchMode.PARALLEL)

    async def boom_one() -> None:
        raise ValueError("one")

    async def boom_two() -> None:
        raise ValueError("two")

    bus.on("test/parallel", boom_one)
    bus.on("test/parallel", boom_two)

    with pytest.raises(ExceptionGroup) as excinfo:
        await bus.parallel("test/parallel")

    assert len(excinfo.value.exceptions) == 2


async def test_serial_runs_in_registration_order_and_returns_last_value() -> None:
    bus = EventBus()
    bus.declare("test/serial", DispatchMode.SERIAL)
    seen: list[str] = []

    async def first() -> str:
        seen.append("first")
        return "first-result"

    async def second() -> str:
        seen.append("second")
        return "second-result"

    bus.on("test/serial", first)
    bus.on("test/serial", second)

    result = await bus.serial("test/serial")

    assert seen == ["first", "second"]
    assert result == "second-result"


async def test_serial_returns_none_without_listeners() -> None:
    bus = EventBus()
    bus.declare("test/serial", DispatchMode.SERIAL)

    assert await bus.serial("test/serial") is None


async def test_serial_accepts_sync_listeners() -> None:
    bus = EventBus()
    bus.declare("test/serial", DispatchMode.SERIAL)
    bus.on("test/serial", lambda: "sync-result")

    assert await bus.serial("test/serial") == "sync-result"


async def test_parallel_rejects_wrong_mode() -> None:
    bus = EventBus()
    bus.declare("test/serial", DispatchMode.SERIAL)

    with pytest.raises(EventModeError):
        await bus.parallel("test/serial")
```

`serial` returning the *last* listener's value is the design choice this test pins: listeners run in order and the final one owns the result.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/runtime/test_events_async.py -v`
Expected: FAIL — `AttributeError: 'EventBus' object has no attribute 'parallel'`

- [ ] **Step 3: Write the implementation**

Add to `src/minion_agent/runtime/events.py` — first extend the imports at the top of the file:

```python
import asyncio
import inspect
```

Then append these methods to `EventBus`:

```python
    @staticmethod
    async def _call(callback: Callable[..., Any], *args: Any) -> Any:
        result = callback(*args)
        if inspect.isawaitable(result):
            return await result
        return result

    async def parallel(self, name: str, *args: Any) -> None:
        """Invoke every listener concurrently, aggregating any failures."""
        self._require_mode(name, DispatchMode.PARALLEL)
        callbacks = self._chain(name)
        if not callbacks:
            return
        outcomes = await asyncio.gather(
            *(self._call(callback, *args) for callback in callbacks),
            return_exceptions=True,
        )
        failures = [outcome for outcome in outcomes if isinstance(outcome, Exception)]
        if failures:
            raise ExceptionGroup(f"errors in {name!r} listeners", failures)

    async def serial(self, name: str, *args: Any) -> Any:
        """Invoke listeners in registration order; the last value wins."""
        self._require_mode(name, DispatchMode.SERIAL)
        result: Any = None
        for callback in self._chain(name):
            result = await self._call(callback, *args)
        return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/runtime/test_events_async.py -v`
Expected: PASS — six tests.

- [ ] **Step 5: Commit**

```bash
git add src/minion_agent/runtime/events.py tests/runtime/test_events_async.py
git commit -m "feat: add parallel and serial event dispatch"
```

---

## Task 7: Event bus — `waterfall`

Around-middleware. A listener receives `next` as its final positional argument and either delegates or short-circuits by returning without calling it.

**Files:**
- Modify: `src/minion_agent/runtime/events.py`
- Test: `tests/runtime/test_events_waterfall.py`

**Interfaces:**
- Consumes: `EventBus` from Tasks 5–6.
- Produces: `async waterfall(name: str, *args: Any) -> Any` on `EventBus`. Listeners are invoked as `listener(*args, next)` where `next` is a zero-argument awaitable returning the downstream result.

- [ ] **Step 1: Write the failing test**

Create `tests/runtime/test_events_waterfall.py`:

```python
"""Waterfall is around-middleware: delegate via next, or short-circuit."""

from collections.abc import Awaitable, Callable
from typing import Any

from minion_agent.runtime.events import DispatchMode, EventBus


async def test_listeners_delegate_through_next() -> None:
    bus = EventBus()
    bus.declare("test/waterfall", DispatchMode.WATERFALL)
    seen: list[str] = []

    async def outer(next_: Callable[[], Awaitable[Any]]) -> Any:
        seen.append("outer-before")
        result = await next_()
        seen.append("outer-after")
        return result

    async def inner(next_: Callable[[], Awaitable[Any]]) -> Any:
        seen.append("inner")
        return "inner-result"

    bus.on("test/waterfall", outer)
    bus.on("test/waterfall", inner)

    result = await bus.waterfall("test/waterfall")

    assert seen == ["outer-before", "inner", "outer-after"]
    assert result == "inner-result"


async def test_short_circuit_skips_downstream_listeners() -> None:
    bus = EventBus()
    bus.declare("test/waterfall", DispatchMode.WATERFALL)
    seen: list[str] = []

    async def decider(next_: Callable[[], Awaitable[Any]]) -> Any:
        seen.append("decider")
        return "decided"

    async def never(next_: Callable[[], Awaitable[Any]]) -> Any:
        seen.append("never")
        return "never-result"

    bus.on("test/waterfall", decider)
    bus.on("test/waterfall", never)

    result = await bus.waterfall("test/waterfall")

    assert seen == ["decider"]
    assert result == "decided"


async def test_a_listener_may_replace_the_downstream_result() -> None:
    bus = EventBus()
    bus.declare("test/waterfall", DispatchMode.WATERFALL)

    async def replacer(next_: Callable[[], Awaitable[Any]]) -> Any:
        await next_()
        return "replaced"

    async def original(next_: Callable[[], Awaitable[Any]]) -> Any:
        return "original"

    bus.on("test/waterfall", replacer)
    bus.on("test/waterfall", original)

    assert await bus.waterfall("test/waterfall") == "replaced"


async def test_arguments_reach_every_listener() -> None:
    bus = EventBus()
    bus.declare("test/waterfall", DispatchMode.WATERFALL)
    seen: list[int] = []

    async def first(number: int, next_: Callable[[], Awaitable[Any]]) -> Any:
        seen.append(number)
        return await next_()

    async def second(number: int, next_: Callable[[], Awaitable[Any]]) -> Any:
        seen.append(number * 2)
        return number

    bus.on("test/waterfall", first)
    bus.on("test/waterfall", second)

    assert await bus.waterfall("test/waterfall", 21) == 21
    assert seen == [21, 42]


async def test_waterfall_without_listeners_returns_none() -> None:
    bus = EventBus()
    bus.declare("test/waterfall", DispatchMode.WATERFALL)

    assert await bus.waterfall("test/waterfall") is None


async def test_next_called_twice_returns_the_same_result() -> None:
    bus = EventBus()
    bus.declare("test/waterfall", DispatchMode.WATERFALL)
    calls: list[str] = []

    async def caller(next_: Callable[[], Awaitable[Any]]) -> Any:
        first = await next_()
        second = await next_()
        return (first, second)

    async def terminal(next_: Callable[[], Awaitable[Any]]) -> Any:
        calls.append("terminal")
        return "value"

    bus.on("test/waterfall", caller)
    bus.on("test/waterfall", terminal)

    assert await bus.waterfall("test/waterfall") == ("value", "value")
    assert calls == ["terminal"]
```

The last test pins a decision worth stating: `next` is memoized, so a listener that delegates twice does not re-run the downstream chain.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/runtime/test_events_waterfall.py -v`
Expected: FAIL — `AttributeError: 'EventBus' object has no attribute 'waterfall'`

- [ ] **Step 3: Write the implementation**

Append to `EventBus` in `src/minion_agent/runtime/events.py`:

```python
    async def waterfall(self, name: str, *args: Any) -> Any:
        """Invoke listeners as around-middleware.

        Each listener receives `next` as its final positional argument. Calling
        it delegates to the rest of the chain and yields their result; returning
        without calling it short-circuits. `next` is memoized, so delegating
        twice does not re-run the downstream chain.
        """
        self._require_mode(name, DispatchMode.WATERFALL)
        callbacks = self._chain(name)

        async def step(index: int) -> Any:
            if index >= len(callbacks):
                return None

            settled = False
            value: Any = None

            async def next_() -> Any:
                nonlocal settled, value
                if not settled:
                    value = await step(index + 1)
                    settled = True
                return value

            return await self._call(callbacks[index], *args, next_)

        return await step(0)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/runtime/test_events_waterfall.py -v`
Expected: PASS — six tests.

- [ ] **Step 5: Commit**

```bash
git add src/minion_agent/runtime/events.py tests/runtime/test_events_waterfall.py
git commit -m "feat: add waterfall event dispatch with memoized delegation"
```

---

## Task 8: Service registry

Exclusive registration by name, `ACTIVE`-gated visibility, no fallback stack. These rules are normative — see spec §3 "Service resolution".

**Files:**
- Create: `src/minion_agent/runtime/service.py`
- Test: `tests/runtime/test_service.py`

**Interfaces:**
- Consumes: `errors.ServiceConflictError`.
- Produces:
  - `@dataclass class Impl` with fields `name: str`, `value: Any`, `owner: Any` (the providing fiber), `check: Callable[[], bool] | None`.
  - `class ServiceRegistry` with `provide(name, value, owner, check=None) -> Callable[[], None]`, `resolve(name, *, strict=True) -> Any | None`, `impl_of(name) -> Impl | None`, `has(name) -> bool`, `names() -> frozenset[str]`.
  - `resolve` returns `None` when no provider exists, when the owner is not active, or when `check()` is falsey. `strict=False` bypasses only the active-state gate.
- Note: `owner` is typed `Any` here to avoid a circular import with `fiber.py`. Task 11 supplies real `Fiber` instances. The registry's only requirement is that `owner` has a `state` attribute comparable to `FiberState.ACTIVE`.

- [ ] **Step 1: Write the failing test**

Create `tests/runtime/test_service.py`:

```python
"""Service registration is exclusive; visibility is narrower than registration."""

from dataclasses import dataclass

import pytest

from minion_agent.runtime.errors import ServiceConflictError
from minion_agent.runtime.fiber import FiberState
from minion_agent.runtime.service import ServiceRegistry


@dataclass
class FakeOwner:
    """Stands in for a Fiber; the registry only reads `state` and `name`."""

    name: str = "owner"
    state: FiberState = FiberState.ACTIVE


def test_provide_then_resolve() -> None:
    registry = ServiceRegistry()
    owner = FakeOwner()

    registry.provide("tools", "tool-service", owner)

    assert registry.resolve("tools") == "tool-service"
    assert registry.has("tools")


def test_second_provider_raises_naming_the_holder() -> None:
    registry = ServiceRegistry()
    registry.provide("tools", "first", FakeOwner(name="holder"))

    with pytest.raises(ServiceConflictError, match="holder"):
        registry.provide("tools", "second", FakeOwner(name="latecomer"))


def test_revoking_frees_the_name_for_a_new_provider() -> None:
    registry = ServiceRegistry()
    revoke = registry.provide("tools", "first", FakeOwner())

    revoke()
    registry.provide("tools", "second", FakeOwner())

    assert registry.resolve("tools") == "second"


def test_no_fallback_to_an_earlier_provider() -> None:
    registry = ServiceRegistry()
    first_revoke = registry.provide("tools", "first", FakeOwner())
    first_revoke()
    second_revoke = registry.provide("tools", "second", FakeOwner())

    second_revoke()

    assert registry.resolve("tools") is None
    assert not registry.has("tools")


def test_inactive_owner_hides_the_service() -> None:
    registry = ServiceRegistry()
    owner = FakeOwner(state=FiberState.LOADING)
    registry.provide("tools", "value", owner)

    assert registry.resolve("tools") is None
    assert registry.resolve("tools", strict=False) == "value"


def test_check_predicate_narrows_visibility() -> None:
    registry = ServiceRegistry()
    visible = False
    registry.provide("tools", "value", FakeOwner(), check=lambda: visible)

    assert registry.resolve("tools") is None

    visible = True
    assert registry.resolve("tools") == "value"


def test_revoking_twice_is_a_no_op() -> None:
    registry = ServiceRegistry()
    revoke = registry.provide("tools", "value", FakeOwner())

    revoke()
    revoke()

    assert registry.resolve("tools") is None


def test_names_lists_registered_services() -> None:
    registry = ServiceRegistry()
    registry.provide("tools", "a", FakeOwner())
    registry.provide("llm", "b", FakeOwner())

    assert registry.names() == frozenset({"tools", "llm"})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/runtime/test_service.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'minion_agent.runtime.service'`

- [ ] **Step 3: Write the implementation**

First create the `FiberState` enum that both this task and Task 11 need. Create `src/minion_agent/runtime/fiber.py` with only the enum for now:

```python
"""Fibers: one loaded plugin instance, its lifecycle, config, and effects."""

from __future__ import annotations

from enum import StrEnum


class FiberState(StrEnum):
    """Lifecycle state of one plugin instance."""

    PENDING = "pending"
    """Mounted but not satisfied: at least one injected service is missing."""

    LOADING = "loading"
    """Dependencies satisfied; the plugin body is running."""

    ACTIVE = "active"
    """Loaded. Its services are visible and its effects are live."""

    FAILED = "failed"
    """The plugin body raised. Effects created before the failure are unwound."""

    UNLOADING = "unloading"
    """Effects are being disposed."""

    DISPOSED = "disposed"
    """Terminal. The fiber cannot be reused."""
```

Create `src/minion_agent/runtime/service.py`:

```python
"""The service registry: exclusive registration, active-gated visibility.

Resolution rules are normative (design spec, section 3):

* Identity is the service name. There is exactly one slot per name.
* Registration is exclusive; a second provider raises rather than winning.
* There is no fallback stack. Revoking frees the name; it does not reveal
  an earlier provider, because none was retained.
* Visibility is narrower than registration: a service resolves only while its
  owning fiber is ACTIVE and its optional `check` predicate holds.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .errors import ServiceConflictError
from .fiber import FiberState


@dataclass(slots=True)
class Impl:
    """One service registration."""

    name: str
    value: Any
    owner: Any
    check: Callable[[], bool] | None = None

    def is_visible(self) -> bool:
        """Whether this registration currently resolves."""
        if getattr(self.owner, "state", None) is not FiberState.ACTIVE:
            return False
        return self.check is None or bool(self.check())


class ServiceRegistry:
    """Maps service names to their single registration."""

    __slots__ = ("_impls",)

    def __init__(self) -> None:
        self._impls: dict[str, Impl] = {}

    def provide(
        self,
        name: str,
        value: Any,
        owner: Any,
        check: Callable[[], bool] | None = None,
    ) -> Callable[[], None]:
        """Register `name`; returns a disposer that revokes it.

        Raises `ServiceConflictError` when the name is already held, naming the
        fiber that holds it.
        """
        existing = self._impls.get(name)
        if existing is not None:
            holder = getattr(existing.owner, "name", "<unknown>")
            raise ServiceConflictError(
                f"service {name!r} has been registered at <{holder}>"
            )

        impl = Impl(name=name, value=value, owner=owner, check=check)
        self._impls[name] = impl

        def revoke() -> None:
            if self._impls.get(name) is impl:
                del self._impls[name]

        return revoke

    def impl_of(self, name: str) -> Impl | None:
        """Return the registration for `name` regardless of visibility."""
        return self._impls.get(name)

    def resolve(self, name: str, *, strict: bool = True) -> Any | None:
        """Return the service value, or None when it does not currently resolve.

        `strict=False` bypasses the ACTIVE-state gate but still honors `check`.
        """
        impl = self._impls.get(name)
        if impl is None:
            return None
        if strict and not impl.is_visible():
            return None
        if not strict and impl.check is not None and not impl.check():
            return None
        return impl.value

    def has(self, name: str) -> bool:
        """Whether `name` currently resolves."""
        return self.resolve(name) is not None

    def names(self) -> frozenset[str]:
        """Every registered service name, visible or not."""
        return frozenset(self._impls)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/runtime/test_service.py -v`
Expected: PASS — eight tests.

- [ ] **Step 5: Commit**

```bash
git add src/minion_agent/runtime/service.py src/minion_agent/runtime/fiber.py tests/runtime/test_service.py
git commit -m "feat: add service registry with exclusive registration and gated visibility"
```

---

## Task 9: Plugin declaration

**Files:**
- Create: `src/minion_agent/runtime/plugin.py`
- Test: `tests/runtime/test_plugin.py`

**Interfaces:**
- Consumes: nothing from earlier runtime modules.
- Produces:
  - `@dataclass(frozen=True) class PluginSpec` with `name: str`, `apply: Callable[[Context, Any], Awaitable[None] | None]`, `inject: tuple[str, ...]`, `config_model: type[BaseModel] | None`, `provides: str | None`.
  - `def plugin(*, name, inject=(), config=None, provides=None) -> Callable[[F], F]` — decorator attaching `__plugin_spec__: PluginSpec` to the function.
  - `def spec_of(candidate: Any) -> PluginSpec` — resolves a decorated function, a bare async function, or an object with `apply`.

- [ ] **Step 1: Write the failing test**

Create `tests/runtime/test_plugin.py`:

```python
"""Plugin declaration: the decorator, config models, and spec resolution."""

import pytest
from pydantic import BaseModel

from minion_agent.runtime.plugin import PluginSpec, plugin, spec_of


class SampleConfig(BaseModel):
    timeout_ms: int = 120_000


def test_decorator_attaches_a_spec() -> None:
    @plugin(name="sample", inject=["tools"], config=SampleConfig, provides="sample")
    async def sample(ctx, config):  # noqa: ANN001, ARG001
        return None

    spec = spec_of(sample)

    assert spec.name == "sample"
    assert spec.inject == ("tools",)
    assert spec.config_model is SampleConfig
    assert spec.provides == "sample"


def test_bare_async_function_resolves_to_a_spec() -> None:
    async def bare(ctx, config):  # noqa: ANN001, ARG001
        return None

    spec = spec_of(bare)

    assert spec.name == "bare"
    assert spec.inject == ()
    assert spec.config_model is None


def test_object_with_apply_resolves_to_a_spec() -> None:
    class Mounted:
        name = "mounted"

        async def apply(self, ctx, config):  # noqa: ANN001, ARG001
            return None

    spec = spec_of(Mounted())

    assert spec.name == "mounted"


def test_non_plugin_raises() -> None:
    with pytest.raises(TypeError, match="not a plugin"):
        spec_of(42)


def test_config_model_validates_and_applies_defaults() -> None:
    @plugin(name="sample", config=SampleConfig)
    async def sample(ctx, config):  # noqa: ANN001, ARG001
        return None

    spec = spec_of(sample)
    assert spec.config_model is not None

    validated = spec.config_model.model_validate({})
    assert validated.timeout_ms == 120_000


def test_spec_is_frozen() -> None:
    spec = PluginSpec(
        name="frozen",
        apply=lambda ctx, config: None,
        inject=(),
        config_model=None,
        provides=None,
    )

    with pytest.raises(Exception):
        spec.name = "changed"  # type: ignore[misc]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/runtime/test_plugin.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'minion_agent.runtime.plugin'`

- [ ] **Step 3: Write the implementation**

Create `src/minion_agent/runtime/plugin.py`:

```python
"""Plugin declaration: a body, its injected services, and its config model."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, TypeVar

from pydantic import BaseModel

if TYPE_CHECKING:
    from .context import Context

F = TypeVar("F", bound=Callable[..., Any])

SPEC_ATTRIBUTE = "__plugin_spec__"


@dataclass(frozen=True, slots=True)
class PluginSpec:
    """Everything the runtime needs to mount one plugin."""

    name: str
    apply: Callable[["Context", Any], Awaitable[None] | None]
    inject: tuple[str, ...]
    config_model: type[BaseModel] | None
    provides: str | None


def plugin(
    *,
    name: str,
    inject: Iterable[str] = (),
    config: type[BaseModel] | None = None,
    provides: str | None = None,
) -> Callable[[F], F]:
    """Declare a function as a plugin.

    The decorated function is returned unchanged with a `PluginSpec` attached,
    so it stays directly callable and testable.
    """

    def decorate(body: F) -> F:
        spec = PluginSpec(
            name=name,
            apply=body,
            inject=tuple(inject),
            config_model=config,
            provides=provides,
        )
        setattr(body, SPEC_ATTRIBUTE, spec)
        return body

    return decorate


def spec_of(candidate: Any) -> PluginSpec:
    """Resolve `candidate` to a PluginSpec.

    Accepts a decorated function, a bare callable taking `(ctx, config)`, or an
    object exposing `apply`.
    """
    existing = getattr(candidate, SPEC_ATTRIBUTE, None)
    if isinstance(existing, PluginSpec):
        return existing

    if callable(candidate) and not isinstance(candidate, type):
        return PluginSpec(
            name=getattr(candidate, "__name__", "<anonymous>"),
            apply=candidate,
            inject=(),
            config_model=None,
            provides=None,
        )

    apply = getattr(candidate, "apply", None)
    if callable(apply):
        return PluginSpec(
            name=getattr(candidate, "name", type(candidate).__name__),
            apply=apply,
            inject=tuple(getattr(candidate, "inject", ())),
            config_model=getattr(candidate, "config_model", None),
            provides=getattr(candidate, "provides", None),
        )

    raise TypeError(
        f"{candidate!r} is not a plugin: expected a callable taking (ctx, config) "
        "or an object with an 'apply' method"
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/runtime/test_plugin.py -v`
Expected: PASS — six tests.

- [ ] **Step 5: Commit**

```bash
git add src/minion_agent/runtime/plugin.py tests/runtime/test_plugin.py
git commit -m "feat: add plugin declaration decorator and spec resolution"
```

---

## Task 10: Context — service access and extension

**Files:**
- Create: `src/minion_agent/runtime/context.py`
- Test: `tests/runtime/test_context_access.py`

**Interfaces:**
- Consumes: `ServiceRegistry`, `EventBus`, `ServiceNotFoundError`.
- Produces: `class Context` with:
  - `__init__(self) -> None` — constructs a root context owning a `ServiceRegistry` and an `EventBus`
  - `__getattr__(self, name: str) -> Any` — resolves a service, raising `ServiceNotFoundError`
  - `require[T](self, protocol: type[T]) -> T` — typed lookup by the protocol's `__service_name__`
  - `extend(self, **meta: Any) -> Context` — a child sharing the registry and bus
  - properties `registry: ServiceRegistry`, `events: EventBus`, `root: Context`, `fiber: Fiber | None`
- Note: Task 12 adds `plugin()`, `on()`, and `effect()` to this class.

- [ ] **Step 1: Write the failing test**

Create `tests/runtime/test_context_access.py`:

```python
"""Attribute access and require() are two views over one resolution mechanism."""

from typing import Protocol

import pytest

from minion_agent.runtime.context import Context
from minion_agent.runtime.errors import ServiceNotFoundError
from minion_agent.runtime.fiber import FiberState


class ToolService(Protocol):
    __service_name__ = "tools"

    def register(self, tool: str) -> None: ...


class FakeOwner:
    name = "owner"
    state = FiberState.ACTIVE


class FakeTools:
    def __init__(self) -> None:
        self.registered: list[str] = []

    def register(self, tool: str) -> None:
        self.registered.append(tool)


def test_attribute_access_resolves_a_service() -> None:
    ctx = Context()
    tools = FakeTools()
    ctx.registry.provide("tools", tools, FakeOwner())

    ctx.tools.register("bash")

    assert tools.registered == ["bash"]


def test_require_resolves_the_same_instance() -> None:
    ctx = Context()
    tools = FakeTools()
    ctx.registry.provide("tools", tools, FakeOwner())

    assert ctx.require(ToolService) is ctx.tools


def test_missing_service_raises_by_attribute() -> None:
    ctx = Context()

    with pytest.raises(ServiceNotFoundError, match="tools"):
        _ = ctx.tools


def test_missing_service_raises_by_require() -> None:
    ctx = Context()

    with pytest.raises(ServiceNotFoundError, match="tools"):
        ctx.require(ToolService)


def test_require_rejects_a_protocol_without_a_service_name() -> None:
    class Unnamed(Protocol): ...

    ctx = Context()

    with pytest.raises(TypeError, match="__service_name__"):
        ctx.require(Unnamed)


def test_extend_shares_the_registry_and_bus() -> None:
    root = Context()
    child = root.extend(label="child")

    assert child.registry is root.registry
    assert child.events is root.events
    assert child.root is root
    assert child.label == "child"


def test_child_sees_services_provided_after_extension() -> None:
    root = Context()
    child = root.extend()
    tools = FakeTools()

    root.registry.provide("tools", tools, FakeOwner())

    assert child.tools is tools


def test_child_cannot_shadow_a_parent_service() -> None:
    """Shadowing is isolation realms, which are deferred. See spec section 3."""
    from minion_agent.runtime.errors import ServiceConflictError

    root = Context()
    child = root.extend()
    root.registry.provide("tools", FakeTools(), FakeOwner())

    with pytest.raises(ServiceConflictError):
        child.registry.provide("tools", FakeTools(), FakeOwner())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/runtime/test_context_access.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'minion_agent.runtime.context'`

- [ ] **Step 3: Write the implementation**

Create `src/minion_agent/runtime/context.py`:

```python
"""The context: a repository of services and the surface plugins are handed.

Attribute access (`ctx.tools`) is the ergonomic door; `ctx.require(ToolService)`
is the statically-checked one. Both resolve through one mechanism keyed by
service name — the protocol is a typed view, never a second key space.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar

from .errors import ServiceNotFoundError
from .events import EventBus
from .service import ServiceRegistry

if TYPE_CHECKING:
    from .fiber import Fiber

T = TypeVar("T")

_RESERVED = frozenset({"registry", "events", "root", "fiber"})


class Context:
    """A view onto the shared service registry and event bus."""

    def __init__(self) -> None:
        self._registry = ServiceRegistry()
        self._events = EventBus()
        self._root: Context = self
        self._fiber: Fiber | None = None
        self._meta: dict[str, Any] = {}

    @property
    def registry(self) -> ServiceRegistry:
        return self._registry

    @property
    def events(self) -> EventBus:
        return self._events

    @property
    def root(self) -> Context:
        return self._root

    @property
    def fiber(self) -> Fiber | None:
        return self._fiber

    def extend(self, **meta: Any) -> Context:
        """Create a child context sharing this one's registry and bus."""
        child = object.__new__(Context)
        child._registry = self._registry
        child._events = self._events
        child._root = self._root
        child._fiber = meta.pop("fiber", self._fiber)
        child._meta = {**self._meta, **meta}
        return child

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_") or name in _RESERVED:
            raise AttributeError(name)

        meta = self.__dict__.get("_meta", {})
        if name in meta:
            return meta[name]

        registry: ServiceRegistry | None = self.__dict__.get("_registry")
        if registry is not None:
            value = registry.resolve(name)
            if value is not None:
                return value
            raise ServiceNotFoundError(
                f"no active provider for service {name!r}"
            )
        raise AttributeError(name)

    def require(self, protocol: type[T]) -> T:
        """Resolve the service `protocol` declares, by name."""
        name = getattr(protocol, "__service_name__", None)
        if not isinstance(name, str):
            raise TypeError(
                f"{protocol!r} does not declare __service_name__; "
                "a service protocol must name the service it describes"
            )
        value = self._registry.resolve(name)
        if value is None:
            raise ServiceNotFoundError(f"no active provider for service {name!r}")
        return value  # type: ignore[no-any-return]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/runtime/test_context_access.py -v`
Expected: PASS — eight tests.

- [ ] **Step 5: Commit**

```bash
git add src/minion_agent/runtime/context.py tests/runtime/test_context_access.py
git commit -m "feat: add context with attribute and protocol service access"
```

---

## Task 11: Fiber lifecycle and effects

**Files:**
- Modify: `src/minion_agent/runtime/fiber.py`
- Test: `tests/runtime/test_fiber.py`

**Interfaces:**
- Consumes: `FiberState`, `DisposableList`, `InactiveFiberError`.
- Produces: `class Fiber` with:
  - `__init__(self, *, name: str, parent: Context, plugin: PluginSpec, config: Any) -> None`
  - attributes `name: str`, `state: FiberState`, `config: Any`, `ctx: Context`, `inject: tuple[str, ...]`
  - `effect(self, execute: Callable[[], Disposer | None], label: str | None = None) -> Callable[[], Awaitable[None]]`
  - `async load(self) -> None`, `async unload(self) -> None`, `async dispose(self) -> None`
  - `on_state_change: Callable[[Fiber, FiberState], None] | None` — the hook the conformance runner uses to record `fiber_state` trace entries
  - `on_effect: Callable[[Fiber, str, str], None] | None` — called with `(fiber, "created" | "disposed", label)`
- Note: `Context` (Task 10) and `PluginSpec` (Task 9) already exist. Import them under `if TYPE_CHECKING:` to avoid a runtime import cycle.

- [ ] **Step 1: Write the failing test**

Create `tests/runtime/test_fiber.py`:

```python
"""Fibers own lifecycle state and reverse-unwound effects."""

import pytest

from minion_agent.runtime.errors import InactiveFiberError
from minion_agent.runtime.fiber import Fiber, FiberState
from minion_agent.runtime.plugin import PluginSpec


def _spec(body=None, *, inject=(), name="test-plugin"):
    async def noop(ctx, config):  # noqa: ANN001, ARG001
        return None

    return PluginSpec(
        name=name,
        apply=body or noop,
        inject=tuple(inject),
        config_model=None,
        provides=None,
    )


async def test_effects_unwind_in_reverse_on_unload() -> None:
    order: list[str] = []

    async def body(ctx, config):  # noqa: ANN001, ARG001
        ctx.effect(lambda: lambda: order.append("first"), "first")
        ctx.effect(lambda: lambda: order.append("second"), "second")

    from minion_agent.runtime.context import Context

    root = Context()
    fiber = Fiber(name="subject", parent=root, plugin=_spec(body), config=None)
    await fiber.load()
    assert fiber.state is FiberState.ACTIVE

    await fiber.unload()

    assert order == ["second", "first"]
    assert fiber.state is FiberState.PENDING


async def test_effect_disposer_can_be_called_early_and_is_idempotent() -> None:
    order: list[str] = []
    captured: dict[str, object] = {}

    async def body(ctx, config):  # noqa: ANN001, ARG001
        captured["dispose"] = ctx.effect(lambda: lambda: order.append("once"), "once")

    from minion_agent.runtime.context import Context

    root = Context()
    fiber = Fiber(name="subject", parent=root, plugin=_spec(body), config=None)
    await fiber.load()

    dispose = captured["dispose"]
    await dispose()  # type: ignore[operator]
    await dispose()  # type: ignore[operator]
    await fiber.unload()

    assert order == ["once"]


async def test_effect_on_a_disposed_fiber_raises() -> None:
    from minion_agent.runtime.context import Context

    root = Context()
    fiber = Fiber(name="subject", parent=root, plugin=_spec(), config=None)
    await fiber.load()
    await fiber.dispose()

    with pytest.raises(InactiveFiberError):
        fiber.effect(lambda: None, "too-late")


async def test_a_failing_body_marks_the_fiber_failed_and_unwinds() -> None:
    order: list[str] = []

    async def body(ctx, config):  # noqa: ANN001, ARG001
        ctx.effect(lambda: lambda: order.append("created-before-failure"), "early")
        raise ValueError("boom")

    from minion_agent.runtime.context import Context

    root = Context()
    fiber = Fiber(name="subject", parent=root, plugin=_spec(body), config=None)

    await fiber.load()

    assert fiber.state is FiberState.FAILED
    assert order == ["created-before-failure"]


async def test_state_changes_are_reported_in_order() -> None:
    from minion_agent.runtime.context import Context

    root = Context()
    fiber = Fiber(name="subject", parent=root, plugin=_spec(), config=None)
    seen: list[FiberState] = []
    fiber.on_state_change = lambda _fiber, state: seen.append(state)

    await fiber.load()
    await fiber.dispose()

    assert seen == [
        FiberState.LOADING,
        FiberState.ACTIVE,
        FiberState.UNLOADING,
        FiberState.DISPOSED,
    ]


async def test_generator_effects_are_supported() -> None:
    from contextlib import contextmanager

    order: list[str] = []

    @contextmanager
    def managed():
        order.append("enter")
        yield
        order.append("exit")

    async def body(ctx, config):  # noqa: ANN001, ARG001
        ctx.effect(managed, "managed")

    from minion_agent.runtime.context import Context

    root = Context()
    fiber = Fiber(name="subject", parent=root, plugin=_spec(body), config=None)
    await fiber.load()
    await fiber.unload()

    assert order == ["enter", "exit"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/runtime/test_fiber.py -v`
Expected: FAIL — `ImportError: cannot import name 'Fiber'`

- [ ] **Step 3: Write the implementation**

Append to `src/minion_agent/runtime/fiber.py` (keep the existing `FiberState`):

```python
import inspect
from collections.abc import Awaitable, Callable
from contextlib import AbstractContextManager
from typing import TYPE_CHECKING, Any

from .disposable import DisposableList, Disposer
from .errors import InactiveFiberError

if TYPE_CHECKING:
    from .context import Context
    from .plugin import PluginSpec

_LIVE_STATES = frozenset({FiberState.LOADING, FiberState.ACTIVE})


class Fiber:
    """One loaded plugin instance: its state, config, and reversible effects."""

    def __init__(
        self,
        *,
        name: str,
        parent: "Context",
        plugin: "PluginSpec",
        config: Any,
    ) -> None:
        self.name = name
        self.plugin = plugin
        self.config = config
        self.inject: tuple[str, ...] = plugin.inject
        self._state = FiberState.PENDING
        self._disposables = DisposableList()
        self.on_state_change: Callable[[Fiber, FiberState], None] | None = None
        self.on_effect: Callable[[Fiber, str, str], None] | None = None
        self.ctx = parent.extend(fiber=self)

    @property
    def state(self) -> FiberState:
        return self._state

    def _transition(self, state: FiberState) -> None:
        self._state = state
        if self.on_state_change is not None:
            self.on_state_change(self, state)

    def effect(
        self,
        execute: Callable[[], Disposer | AbstractContextManager[Any] | None],
        label: str | None = None,
    ) -> Callable[[], Awaitable[None]]:
        """Run `execute` now and collect its disposer.

        `execute` may return a disposer, a context manager, or None. The
        returned disposer tears this effect down; calling it twice is a no-op,
        and the fiber's own unload runs it if it has not already.
        """
        if self._state not in _LIVE_STATES:
            raise InactiveFiberError(
                f"cannot create effect on fiber <{self.name}> in state {self._state.value!r}"
            )

        outcome = execute()
        disposer: Disposer | None
        if outcome is None:
            disposer = None
        elif isinstance(outcome, AbstractContextManager):
            outcome.__enter__()
            disposer = lambda: outcome.__exit__(None, None, None)  # noqa: E731
        else:
            disposer = outcome

        effect_label = label or "<unlabelled>"
        if self.on_effect is not None:
            self.on_effect(self, "created", effect_label)

        settled = False

        async def run_disposer() -> None:
            nonlocal settled
            if settled:
                return
            settled = True
            if disposer is not None:
                result = disposer()
                if inspect.isawaitable(result):
                    await result
            if self.on_effect is not None:
                self.on_effect(self, "disposed", effect_label)

        remove = self._disposables.push(run_disposer)

        async def dispose() -> None:
            remove()
            await run_disposer()

        return dispose

    async def load(self) -> None:
        """Run the plugin body, transitioning PENDING -> LOADING -> ACTIVE."""
        if self._state is not FiberState.PENDING:
            return
        self._transition(FiberState.LOADING)
        try:
            result = self.plugin.apply(self.ctx, self.config)
            if inspect.isawaitable(result):
                await result
        except Exception:
            await self._disposables.dispose_all()
            self._disposables = DisposableList()
            self._transition(FiberState.FAILED)
            return
        self._transition(FiberState.ACTIVE)

    async def unload(self) -> None:
        """Unwind effects and return to PENDING, ready to load again."""
        if self._state not in _LIVE_STATES and self._state is not FiberState.FAILED:
            return
        self._transition(FiberState.UNLOADING)
        await self._disposables.dispose_all()
        self._disposables = DisposableList()
        self._transition(FiberState.PENDING)

    async def dispose(self) -> None:
        """Unwind effects and enter the terminal DISPOSED state."""
        if self._state is FiberState.DISPOSED:
            return
        if self._state in _LIVE_STATES or self._state is FiberState.FAILED:
            self._transition(FiberState.UNLOADING)
            await self._disposables.dispose_all()
            self._disposables = DisposableList()
        self._transition(FiberState.DISPOSED)
```

Note the deliberate asymmetry pinned by `reactive-dependency.yaml`: `unload` returns to `PENDING` (the plugin is still mounted, merely unsatisfied) while `dispose` is terminal.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/runtime/test_fiber.py -v`
Expected: PASS — six tests.

- [ ] **Step 5: Commit**

```bash
git add src/minion_agent/runtime/fiber.py tests/runtime/test_fiber.py
git commit -m "feat: add fiber lifecycle with reversible effects"
```

---

## Task 12: Mounting plugins and reactive dependency

The heart of the runtime. A fiber loads when every injected service is visible and unloads when any disappears.

**Files:**
- Modify: `src/minion_agent/runtime/context.py`
- Modify: `src/minion_agent/runtime/fiber.py`
- Create: `src/minion_agent/runtime/registry.py`
- Test: `tests/runtime/test_reactive.py`

**Interfaces:**
- Consumes: `Context`, `Fiber`, `PluginSpec`, `spec_of`, `ServiceRegistry`.
- Produces:
  - `class PluginRegistry` with `mount(spec, config, parent) -> Fiber`, `async unmount(fiber) -> None`, `async reconcile() -> None`, `fibers: tuple[Fiber, ...]`.
  - `Context.plugin(self, candidate: Any, config: Any = None) -> Fiber` — validates config against the spec's model, mounts, and reconciles.
  - `Context.on(self, name: str, listener, *, prepend: bool = False)` — registers through the owning fiber's effect list so it is auto-disposed.
  - `Context.effect(self, execute, label=None)` — delegates to `self.fiber.effect`.
  - `Context.provide(self, name: str, value: Any, check=None)` — registers a service as an effect of the owning fiber.

- [ ] **Step 1: Write the failing test**

Create `tests/runtime/test_reactive.py`:

```python
"""Fibers load when their injected services appear and unload when they vanish."""

from minion_agent.runtime.context import Context
from minion_agent.runtime.fiber import FiberState
from minion_agent.runtime.plugin import plugin


async def test_dependent_stays_pending_until_its_service_appears() -> None:
    loaded: list[str] = []

    @plugin(name="consumer", inject=["tools"])
    async def consumer(ctx, config):  # noqa: ANN001, ARG001
        loaded.append("consumer")

    @plugin(name="provider", provides="tools")
    async def provider(ctx, config):  # noqa: ANN001, ARG001
        ctx.provide("tools", object())

    root = Context()
    consumer_fiber = await root.plugin(consumer)

    assert consumer_fiber.state is FiberState.PENDING
    assert loaded == []

    await root.plugin(provider)

    assert consumer_fiber.state is FiberState.ACTIVE
    assert loaded == ["consumer"]


async def test_dependent_unloads_when_its_service_disappears() -> None:
    disposed: list[str] = []

    @plugin(name="consumer", inject=["tools"])
    async def consumer(ctx, config):  # noqa: ANN001, ARG001
        ctx.effect(lambda: lambda: disposed.append("consumer-effect"), "consumer-effect")

    @plugin(name="provider", provides="tools")
    async def provider(ctx, config):  # noqa: ANN001, ARG001
        ctx.provide("tools", object())

    root = Context()
    provider_fiber = await root.plugin(provider)
    consumer_fiber = await root.plugin(consumer)
    assert consumer_fiber.state is FiberState.ACTIVE

    await root.registry_of_plugins.unmount(provider_fiber)

    assert consumer_fiber.state is FiberState.PENDING
    assert disposed == ["consumer-effect"]


async def test_dependent_reloads_when_the_service_returns() -> None:
    loads: list[int] = []

    @plugin(name="consumer", inject=["tools"])
    async def consumer(ctx, config):  # noqa: ANN001, ARG001
        loads.append(len(loads) + 1)

    @plugin(name="provider", provides="tools")
    async def provider(ctx, config):  # noqa: ANN001, ARG001
        ctx.provide("tools", object())

    root = Context()
    first_provider = await root.plugin(provider)
    await root.plugin(consumer)
    await root.registry_of_plugins.unmount(first_provider)

    await root.plugin(provider)

    assert loads == [1, 2]


async def test_listeners_registered_via_ctx_on_are_auto_disposed() -> None:
    from minion_agent.runtime.events import DispatchMode

    seen: list[str] = []

    @plugin(name="listener-plugin")
    async def listener_plugin(ctx, config):  # noqa: ANN001, ARG001
        ctx.on("test/emit", lambda: seen.append("heard"))

    root = Context()
    root.events.declare("test/emit", DispatchMode.EMIT)
    fiber = await root.plugin(listener_plugin)

    root.events.emit("test/emit")
    assert seen == ["heard"]

    await root.registry_of_plugins.unmount(fiber)
    root.events.emit("test/emit")

    assert seen == ["heard"]


async def test_config_is_validated_against_the_declared_model() -> None:
    from pydantic import BaseModel

    class Config(BaseModel):
        timeout_ms: int = 120_000

    captured: dict[str, object] = {}

    @plugin(name="configured", config=Config)
    async def configured(ctx, config):  # noqa: ANN001
        captured["config"] = config

    root = Context()
    await root.plugin(configured, {"timeout_ms": 500})

    assert isinstance(captured["config"], Config)
    assert captured["config"].timeout_ms == 500  # type: ignore[union-attr]


async def test_invalid_config_raises_before_the_body_runs() -> None:
    from pydantic import BaseModel, ValidationError

    class Config(BaseModel):
        timeout_ms: int

    ran: list[str] = []

    @plugin(name="configured", config=Config)
    async def configured(ctx, config):  # noqa: ANN001, ARG001
        ran.append("body")

    root = Context()

    import pytest

    with pytest.raises(ValidationError):
        await root.plugin(configured, {"timeout_ms": "not-an-int"})

    assert ran == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/runtime/test_reactive.py -v`
Expected: FAIL — `AttributeError: 'Context' object has no attribute 'plugin'`

- [ ] **Step 3: Write the plugin registry**

Create `src/minion_agent/runtime/registry.py`:

```python
"""The plugin registry: mounting, unmounting, and dependency reconciliation.

Reconciliation is the reactive mechanism. After any change to the set of
visible services, every mounted fiber is re-evaluated: satisfied fibers load,
unsatisfied ones unload. Repeating until the world stops changing lets one
service's arrival cascade through a chain of dependents.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .fiber import Fiber, FiberState

if TYPE_CHECKING:
    from .context import Context
    from .plugin import PluginSpec

_MAX_PASSES = 100


class PluginRegistry:
    """Owns every mounted fiber and keeps their load state consistent."""

    __slots__ = ("_fibers", "_root")

    def __init__(self, root: "Context") -> None:
        self._root = root
        self._fibers: list[Fiber] = []

    @property
    def fibers(self) -> tuple[Fiber, ...]:
        return tuple(self._fibers)

    def mount(self, spec: "PluginSpec", config: Any, parent: "Context") -> Fiber:
        """Create a fiber for `spec`. It loads during the next reconcile."""
        fiber = Fiber(name=spec.name, parent=parent, plugin=spec, config=config)
        self._fibers.append(fiber)
        return fiber

    async def unmount(self, fiber: Fiber) -> None:
        """Dispose `fiber` and reconcile the fibers that depended on it."""
        if fiber in self._fibers:
            self._fibers.remove(fiber)
        await fiber.dispose()
        await self.reconcile()

    def _is_satisfied(self, fiber: Fiber) -> bool:
        registry = self._root.registry
        return all(registry.has(name) for name in fiber.inject)

    async def reconcile(self) -> None:
        """Load satisfied fibers and unload unsatisfied ones until stable."""
        for _ in range(_MAX_PASSES):
            changed = False

            for fiber in list(self._fibers):
                if fiber.state is FiberState.ACTIVE and not self._is_satisfied(fiber):
                    await fiber.unload()
                    changed = True

            for fiber in list(self._fibers):
                if fiber.state is FiberState.PENDING and self._is_satisfied(fiber):
                    await fiber.load()
                    changed = True

            if not changed:
                return

        raise RuntimeError(  # pragma: no cover - a cycle in plugin dependencies
            "plugin reconciliation did not stabilize; check for a dependency cycle"
        )
```

- [ ] **Step 4: Extend Context**

Add to `src/minion_agent/runtime/context.py` — extend the imports:

```python
from collections.abc import Callable
from contextlib import AbstractContextManager

from .disposable import Disposer
from .plugin import spec_of
from .registry import PluginRegistry
```

Add `_plugins` to `__init__` and `extend`, then append the methods. In `__init__`, after `self._meta = {}`:

```python
        self._plugins = PluginRegistry(self)
```

In `extend`, after `child._meta = ...`:

```python
        child._plugins = self._plugins
```

Add `"registry_of_plugins"` to `_RESERVED`, then append these methods to `Context`:

```python
    @property
    def registry_of_plugins(self) -> PluginRegistry:
        """The plugin registry shared by this context tree."""
        return self._plugins

    async def plugin(self, candidate: Any, config: Any = None) -> Fiber:
        """Mount `candidate` as a plugin and reconcile dependencies.

        Config is validated against the plugin's declared model before the
        fiber is created, so an invalid config never runs a plugin body.
        """
        spec = spec_of(candidate)
        resolved = config
        if spec.config_model is not None:
            resolved = spec.config_model.model_validate(config or {})
        fiber = self._plugins.mount(spec, resolved, self)
        await self._plugins.reconcile()
        return fiber

    def effect(
        self,
        execute: Callable[[], Disposer | AbstractContextManager[Any] | None],
        label: str | None = None,
    ) -> Callable[[], Any]:
        """Register a reversible effect on the owning fiber."""
        if self._fiber is None:
            raise RuntimeError("ctx.effect() requires a fiber; call it inside a plugin")
        return self._fiber.effect(execute, label)

    def on(
        self,
        name: str,
        listener: Callable[..., Any],
        *,
        prepend: bool = False,
    ) -> Callable[[], Any]:
        """Register an event listener, auto-disposed with the owning fiber."""
        if self._fiber is None:
            dispose = self._events.on(name, listener, prepend=prepend)
            return dispose
        return self.effect(
            lambda: self._events.on(name, listener, prepend=prepend),
            f"on({name})",
        )

    def provide(
        self,
        name: str,
        value: Any,
        check: Callable[[], bool] | None = None,
    ) -> Callable[[], Any]:
        """Provide a service, withdrawn when the owning fiber unloads."""
        if self._fiber is None:
            raise RuntimeError("ctx.provide() requires a fiber; call it inside a plugin")
        fiber = self._fiber
        return self.effect(
            lambda: self._registry.provide(name, value, fiber, check),
            f"provide({name})",
        )
```

Also add the `Fiber` import under `TYPE_CHECKING` and a runtime import at the bottom of the module to avoid the cycle:

```python
from .fiber import Fiber  # noqa: E402  - imported late to break the context/fiber cycle
```

- [ ] **Step 5: Make service changes trigger reconciliation**

The registry must reconcile after a service is provided or revoked. In `src/minion_agent/runtime/registry.py`, add to `PluginRegistry`:

```python
    async def reconcile_after_service_change(self) -> None:
        """Alias kept explicit at call sites that react to service changes."""
        await self.reconcile()
```

In `Context.provide`, wrap the registration so revocation reconciles. Replace the `provide` method body's `return self.effect(...)` with:

```python
        plugins = self._plugins

        def register() -> Disposer:
            revoke = self._registry.provide(name, value, fiber, check)

            async def undo() -> None:
                revoke()
                await plugins.reconcile()

            return undo

        return self.effect(register, f"provide({name})")
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/runtime/test_reactive.py tests/runtime/test_fiber.py -v`
Expected: PASS — six reactive tests and six fiber tests.

- [ ] **Step 7: Run the whole suite**

Run: `pytest -v`
Expected: PASS — every test from Tasks 1–12.

- [ ] **Step 8: Commit**

```bash
git add src/minion_agent/runtime/registry.py src/minion_agent/runtime/context.py tests/runtime/test_reactive.py
git commit -m "feat: add plugin mounting and reactive dependency reconciliation"
```

---

## Task 13: Public surface

**Files:**
- Modify: `src/minion_agent/runtime/__init__.py`
- Test: `tests/runtime/test_public_surface.py`

**Interfaces:**
- Consumes: everything from Tasks 4–12.
- Produces: `minion_agent.runtime` re-exporting `Context`, `Fiber`, `FiberState`, `PluginSpec`, `plugin`, `spec_of`, `DispatchMode`, `EventBus`, `ServiceRegistry`, `Impl`, `DisposableList`, `Disposer`, and the five error types, with `__all__` set.

- [ ] **Step 1: Write the failing test**

Create `tests/runtime/test_public_surface.py`:

```python
"""The runtime package exposes a curated public surface."""

import minion_agent.runtime as runtime

EXPECTED = {
    "Context",
    "DisposableList",
    "Disposer",
    "DispatchMode",
    "EventBus",
    "EventModeError",
    "Fiber",
    "FiberState",
    "Impl",
    "InactiveFiberError",
    "PluginSpec",
    "RuntimeError_",
    "ServiceConflictError",
    "ServiceNotFoundError",
    "ServiceRegistry",
    "plugin",
    "spec_of",
}


def test_all_matches_expected_surface() -> None:
    assert set(runtime.__all__) == EXPECTED


def test_every_exported_name_resolves() -> None:
    for name in runtime.__all__:
        assert getattr(runtime, name) is not None


def test_no_cordis_in_public_identifiers() -> None:
    """Cordis is design lineage, not API vocabulary. See spec section 3."""
    for name in runtime.__all__:
        assert "cordis" not in name.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/runtime/test_public_surface.py -v`
Expected: FAIL — `AttributeError: module 'minion_agent.runtime' has no attribute '__all__'`

- [ ] **Step 3: Write the implementation**

Replace `src/minion_agent/runtime/__init__.py`:

```python
"""The plugin runtime: contexts, fibers, services, events, and reversible effects.

Cordis-semantic, not a Cordis port: faithful to Cordis's semantics, not its
mechanics. See the design spec, section 3.
"""

from .context import Context
from .disposable import DisposableList, Disposer
from .errors import (
    EventModeError,
    InactiveFiberError,
    RuntimeError_,
    ServiceConflictError,
    ServiceNotFoundError,
)
from .events import DispatchMode, EventBus
from .fiber import Fiber, FiberState
from .plugin import PluginSpec, plugin, spec_of
from .service import Impl, ServiceRegistry

__all__ = [
    "Context",
    "DisposableList",
    "DispatchMode",
    "Disposer",
    "EventBus",
    "EventModeError",
    "Fiber",
    "FiberState",
    "Impl",
    "InactiveFiberError",
    "PluginSpec",
    "RuntimeError_",
    "ServiceConflictError",
    "ServiceNotFoundError",
    "ServiceRegistry",
    "plugin",
    "spec_of",
]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/runtime/test_public_surface.py -v`
Expected: PASS — three tests.

- [ ] **Step 5: Commit**

```bash
git add src/minion_agent/runtime/__init__.py tests/runtime/test_public_surface.py
git commit -m "feat: export the runtime public surface"
```

---

## Task 14: Conformance runner

Makes the Phase 0 scenarios executable.

**Files:**
- Create: `tests/conformance/runner.py`
- Create: `tests/conformance/test_runtime_conformance.py`

**Interfaces:**
- Consumes: the runtime public surface; the scenario format from Task 2.
- Produces:
  - `class TraceRecorder` with `entries: list[dict[str, Any]]` and `record(entry: dict[str, Any]) -> None`.
  - `async def run_runtime_scenario(document: dict[str, Any]) -> RunOutcome` where `RunOutcome` is a dataclass with `trace: list[dict[str, Any]]`, `result: Any`, `error: Exception | None`.
  - `def build_plugin(entry: dict[str, Any], recorder: TraceRecorder) -> PluginSpec` — turns a declarative plugin entry into a real plugin.

- [ ] **Step 1: Write the failing test**

Create `tests/conformance/test_runtime_conformance.py`:

```python
"""Execute every conformance/runtime/*.yaml scenario against the runtime."""

from pathlib import Path

import pytest
import yaml

from .runner import run_runtime_scenario

SCENARIOS = sorted(
    (Path(__file__).resolve().parents[2] / "conformance" / "runtime").glob("*.yaml")
)


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda path: path.stem)
async def test_runtime_scenario(scenario: Path) -> None:
    document = yaml.safe_load(scenario.read_text(encoding="utf-8"))
    outcome = await run_runtime_scenario(document)

    assert outcome.error is None, f"scenario raised: {outcome.error!r}"
    assert outcome.trace == document["expect_trace"]

    if "expect_result" in document:
        assert outcome.result == document["expect_result"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/conformance/test_runtime_conformance.py -v`
Expected: FAIL — `ImportError: cannot import name 'run_runtime_scenario'`

- [ ] **Step 3: Write the runner**

Create `tests/conformance/runner.py`:

```python
"""Executes declarative conformance scenarios against the runtime.

The scenario vocabulary describes plugins by what they do — the services they
provide, the labelled effects they create, the listeners they register — so
the cases stay language-neutral. This module is the Python half of the runner
contract in conformance/schema/README.md.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from minion_agent.runtime import Context, DispatchMode, PluginSpec
from minion_agent.runtime.errors import RuntimeError_


@dataclass
class TraceRecorder:
    """Collects ordered trace entries as the scenario runs."""

    entries: list[dict[str, Any]] = field(default_factory=list)

    def record(self, entry: dict[str, Any]) -> None:
        self.entries.append(entry)


@dataclass
class RunOutcome:
    """What a scenario produced."""

    trace: list[dict[str, Any]]
    result: Any = None
    error: Exception | None = None


def _make_listener(
    spec: dict[str, Any],
    plugin_id: str,
    recorder: TraceRecorder,
) -> Callable[..., Awaitable[Any]]:
    action = spec["action"]
    tag = spec["tag"]
    returns = spec.get("returns")

    async def listener(*args: Any) -> Any:
        recorder.record({"event": "listener_entered", "plugin": plugin_id, "tag": tag})
        next_ = args[-1] if args and callable(args[-1]) else None

        if action == "raise":
            raise ValueError(f"{tag} raised")
        if action == "short_circuit":
            return returns
        if action == "observe":
            return returns
        if next_ is not None:
            return await next_()
        return returns

    return listener


def build_plugin(entry: dict[str, Any], recorder: TraceRecorder) -> PluginSpec:
    """Turn one declarative plugin entry into a mountable PluginSpec."""
    plugin_id = entry["id"]
    provides = entry.get("provides")
    effects = entry.get("effects", [])
    listeners = entry.get("listeners", [])
    fails = entry.get("fails", False)

    async def apply(ctx: Context, config: Any) -> None:  # noqa: ARG001
        if provides is not None:
            ctx.provide(provides, {"service": provides})
            recorder.record(
                {"event": "service_provided", "plugin": plugin_id, "service": provides}
            )

        for effect in effects:
            label = effect["label"]
            ctx.effect(lambda: None, label)

        for listener in listeners:
            ctx.on(listener["event"], _make_listener(listener, plugin_id, recorder))

        if fails:
            raise ValueError(f"{plugin_id} failed on purpose")

    return PluginSpec(
        name=plugin_id,
        apply=apply,
        inject=tuple(entry.get("inject", ())),
        config_model=None,
        provides=provides,
    )


def _attach_recording(fiber: Any, plugin_id: str, recorder: TraceRecorder) -> None:
    fiber.on_state_change = lambda _fiber, state: recorder.record(
        {"event": "fiber_state", "plugin": plugin_id, "state": state.value}
    )

    def on_effect(_fiber: Any, phase: str, label: str) -> None:
        if label.startswith("provide(") or label.startswith("on("):
            if phase == "disposed" and label.startswith("provide("):
                service = label[len("provide(") : -1]
                recorder.record(
                    {"event": "service_revoked", "plugin": plugin_id, "service": service}
                )
            return
        recorder.record(
            {"event": f"effect_{phase}", "plugin": plugin_id, "label": label}
        )

    fiber.on_effect = on_effect


async def run_runtime_scenario(document: dict[str, Any]) -> RunOutcome:
    """Mount the scenario's plugins, run its steps, and return the trace."""
    recorder = TraceRecorder()
    root = Context()
    specs = {entry["id"]: build_plugin(entry, recorder) for entry in document["plugins"]}
    configs = {entry["id"]: entry.get("config") for entry in document["plugins"]}
    fibers: dict[str, Any] = {}
    result: Any = None

    for step in document["steps"]:
        try:
            if "mount" in step:
                plugin_id = step["mount"]
                spec = specs[plugin_id]
                fiber = root.registry_of_plugins.mount(spec, configs[plugin_id], root)
                _attach_recording(fiber, plugin_id, recorder)
                fibers[plugin_id] = fiber
                await root.registry_of_plugins.reconcile()

            elif "unmount" in step:
                plugin_id = step["unmount"]
                await root.registry_of_plugins.unmount(fibers[plugin_id])

            elif "dispatch" in step:
                dispatch = step["dispatch"]
                name = dispatch["event"]
                mode = DispatchMode(dispatch["mode"])
                args = dispatch.get("args", [])
                root.events.declare(name, mode)
                if mode is DispatchMode.EMIT:
                    root.events.emit(name, *args)
                elif mode is DispatchMode.PARALLEL:
                    await root.events.parallel(name, *args)
                elif mode is DispatchMode.SERIAL:
                    result = await root.events.serial(name, *args)
                else:
                    result = await root.events.waterfall(name, *args)

        except RuntimeError_ as error:
            return RunOutcome(trace=recorder.entries, result=result, error=error)

    return RunOutcome(trace=recorder.entries, result=result)
```

Listener registration must happen before the event is dispatched, so scenarios declare listeners on plugins mounted in earlier steps. `root.events.declare` is called at dispatch time and is idempotent for a matching mode, which is why re-declaring the same mode is allowed (Task 5).

- [ ] **Step 4: Reconcile the runner against the scenarios**

Run: `pytest tests/conformance/test_runtime_conformance.py -v`
Expected: FAIL on trace mismatches. Compare the observed trace against `expect_trace` and fix **the runner or the scenario**, not the runtime, unless the runtime genuinely violates the spec. Common corrections:
- `ctx.on(...)` and `ctx.provide(...)` create effects; the runner filters them out of `effect_created` so scenarios only assert their own labelled effects.
- `service_provided` is recorded by the plugin body; `service_revoked` is derived from the `provide(...)` effect's disposal.

Iterate until both scenarios pass.

- [ ] **Step 5: Run the whole suite**

Run: `pytest -v`
Expected: PASS — all tests including both conformance scenarios.

- [ ] **Step 6: Commit**

```bash
git add tests/conformance/runner.py tests/conformance/test_runtime_conformance.py
git commit -m "feat: add runtime conformance runner and execute the kernel scenarios"
```

---

## Task 15: Remaining kernel scenarios

Fill out the `runtime/` family named in the spec: `waterfall-short-circuit`, `service-exclusivity`, `service-visibility`, `double-dispose`.

**Files:**
- Create: `conformance/runtime/waterfall-short-circuit.yaml`
- Create: `conformance/runtime/service-exclusivity.yaml`
- Test: existing `tests/conformance/test_runtime_conformance.py` picks them up automatically.

**Interfaces:**
- Consumes: the runner from Task 14.
- Produces: two additional executable cases. `double-dispose` and `service-visibility` are covered by tier-2 tests (Tasks 4 and 8) because they assert idempotence and predicate evaluation rather than an ordered trace; this is recorded here so the coverage gap is a decision, not an oversight.

- [ ] **Step 1: Write the scenarios**

Create `conformance/runtime/waterfall-short-circuit.yaml`:

```yaml
name: a waterfall listener that short-circuits skips every downstream listener
description: >
  Waterfall is around-middleware. A listener that returns without delegating
  owns the decision, and listeners registered after it never run. Short-circuit
  is the design for policy events, not an edge case.
plugins:
  - id: observer
    listeners:
      - event: test/policy
        action: delegate
        tag: observer
  - id: decider
    listeners:
      - event: test/policy
        action: short_circuit
        tag: decider
        returns: blocked
  - id: unreachable
    listeners:
      - event: test/policy
        action: delegate
        tag: unreachable
steps:
  - mount: observer
  - mount: decider
  - mount: unreachable
  - dispatch: { event: test/policy, mode: waterfall }
expect_trace:
  - { event: fiber_state, plugin: observer, state: loading }
  - { event: fiber_state, plugin: observer, state: active }
  - { event: fiber_state, plugin: decider, state: loading }
  - { event: fiber_state, plugin: decider, state: active }
  - { event: fiber_state, plugin: unreachable, state: loading }
  - { event: fiber_state, plugin: unreachable, state: active }
  - { event: listener_entered, plugin: observer, tag: observer }
  - { event: listener_entered, plugin: decider, tag: decider }
expect_result: blocked
```

Create `conformance/runtime/service-exclusivity.yaml`:

```yaml
name: a second provider of the same service is rejected
description: >
  Registration is exclusive. The second provider raises rather than winning;
  there is no last-wins rule and no priority, because there is never more than
  one provider to choose between.
plugins:
  - id: holder
    provides: tools
  - id: latecomer
    provides: tools
steps:
  - mount: holder
  - mount: latecomer
expect_trace:
  - { event: fiber_state, plugin: holder, state: loading }
  - { event: service_provided, plugin: holder, service: tools }
  - { event: fiber_state, plugin: holder, state: active }
  - { event: fiber_state, plugin: latecomer, state: loading }
  - { event: fiber_state, plugin: latecomer, state: failed }
expect_error:
  type: ServiceConflictError
  message_contains: holder
```

Note the interaction with `Fiber.load`: a body that raises is caught and the fiber transitions to `FAILED` rather than propagating. So this scenario asserts the trace, and `expect_error` documents intent.

- [ ] **Step 2: Teach the test to check `expect_error`**

Add to `tests/conformance/test_runtime_conformance.py`:

```python
    if "expect_error" in document:
        expected = document["expect_error"]
        failed = [
            entry
            for entry in outcome.trace
            if entry["event"] == "fiber_state" and entry["state"] == "failed"
        ]
        assert failed, f"expected a failed fiber for {expected['type']}"
```

Change the existing unconditional assertion so a scenario declaring `expect_error` is not required to be error-free:

```python
    if "expect_error" not in document:
        assert outcome.error is None, f"scenario raised: {outcome.error!r}"
```

- [ ] **Step 3: Run the conformance suite**

Run: `pytest tests/conformance -v`
Expected: PASS — four scenarios plus schema validation.

- [ ] **Step 4: Commit**

```bash
git add conformance/runtime tests/conformance/test_runtime_conformance.py
git commit -m "feat: add waterfall short-circuit and service exclusivity scenarios"
```

---

## Task 16: Property tests and the coverage gate

**Files:**
- Create: `tests/runtime/test_properties.py`
- Modify: `pyproject.toml`

**Interfaces:**
- Consumes: `DisposableList`, `Context`, `plugin`.
- Produces: property coverage for disposal ordering and mount/unmount sequences; a coverage gate at 100% for `src/minion_agent/runtime/**`.

- [ ] **Step 1: Write the property tests**

Create `tests/runtime/test_properties.py`:

```python
"""Properties that must hold for any effect and mount sequence."""

from hypothesis import given
from hypothesis import strategies as st

from minion_agent.runtime import Context, DisposableList, FiberState, plugin

labels = st.lists(st.text(min_size=1, max_size=8), min_size=0, max_size=25, unique=True)


@given(labels)
async def test_disposal_is_always_exact_reverse_of_creation(order: list[str]) -> None:
    seen: list[str] = []
    disposables = DisposableList()
    for label in order:
        disposables.push(lambda label=label: seen.append(label))

    await disposables.dispose_all()

    assert seen == list(reversed(order))


@given(labels)
async def test_every_effect_disposes_exactly_once(order: list[str]) -> None:
    counts: dict[str, int] = {label: 0 for label in order}
    disposables = DisposableList()
    for label in order:
        disposables.push(lambda label=label: counts.__setitem__(label, counts[label] + 1))

    await disposables.dispose_all()
    await disposables.dispose_all()

    assert all(count == 1 for count in counts.values())


@given(st.integers(min_value=1, max_value=12))
async def test_mount_unmount_cycles_leave_no_residue(cycles: int) -> None:
    """Repeated provider churn always returns the dependent to a clean state."""
    live: list[str] = []

    @plugin(name="provider", provides="tools")
    async def provider(ctx, config):  # noqa: ANN001, ARG001
        ctx.provide("tools", object())

    @plugin(name="consumer", inject=["tools"])
    async def consumer(ctx, config):  # noqa: ANN001, ARG001
        ctx.effect(lambda: (live.append("on"), lambda: live.remove("on"))[1], "live")

    root = Context()
    consumer_fiber = await root.plugin(consumer)

    for _ in range(cycles):
        provider_fiber = await root.plugin(provider)
        assert consumer_fiber.state is FiberState.ACTIVE
        assert live == ["on"]

        await root.registry_of_plugins.unmount(provider_fiber)
        assert consumer_fiber.state is FiberState.PENDING
        assert live == []
```

- [ ] **Step 2: Run the property tests**

Run: `pytest tests/runtime/test_properties.py -v`
Expected: PASS — three property tests.

- [ ] **Step 3: Enable the coverage gate**

Add to `pyproject.toml` under `[tool.pytest.ini_options]`, replacing `addopts`:

```toml
addopts = "-q --cov --cov-report=term-missing"
```

- [ ] **Step 4: Run the full suite with coverage**

Run: `pytest`
Expected: PASS with 100% coverage of `src/minion_agent/runtime/**`.

If a line is genuinely unreachable, add `# pragma: no cover` **with a written reason on the same line**. If a line is reachable but untested, write the test rather than exempting it.

- [ ] **Step 5: Run lint and types**

Run: `ruff check . && ruff format --check . && mypy`
Expected: clean. Fix any findings.

- [ ] **Step 6: Commit and push**

```bash
git add tests/runtime/test_properties.py pyproject.toml
git commit -m "test: add disposal and lifecycle property tests; enable coverage gate"
git push -u origin main
```

---

## Definition of done

- [ ] `pytest` passes with 100% coverage of `src/minion_agent/runtime/**`
- [ ] `ruff check`, `ruff format --check`, and `mypy` are clean
- [ ] Four scenarios in `conformance/runtime/` execute and pass
- [ ] Both JSON Schemas validate, and every scenario validates against its schema
- [ ] No identifier in `minion_agent.runtime.__all__` contains "cordis"
- [ ] `conformance/schema/README.md` documents the runner contract
- [ ] Work is pushed to `origin/main`

## What Plan 2 picks up

LLM message vocabulary and the never-raises stream contract, the scripted mock adapter, the session log with `derive_messages()`, and the agent loop through a complete tool round-trip. It writes `conformance/agent/*.yaml` against the format fixed in Task 3, mounting every subsystem as a plugin on the runtime this plan delivers.
