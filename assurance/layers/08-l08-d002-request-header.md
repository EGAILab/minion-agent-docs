# L08-D002 — Request header per provider request (Layer 08 delta)

**Status:** contract delta, for independent contract review. Python: conforms (pre-existing).
Rust: NOT_IMPLEMENTED.

**Coordination:** `minion-agent#171`.

**Governance:** Owner decision on `L08D001-RUST-C001`, Option 1, recorded verbatim at
`minion-agent#166` issuecomment-6068630928. It authorizes a targeted correction to certified
Layer 08 in both bindings, including the observable change to the session event log.

**Normative text:** `spec/agent.md`, Layer 08, "Request header per provider request". Manifest row
`AG-025`.

## 1. Origin

- **The finding.** Codex's Rust `L08-D001` checkpoint found `L08D001-RUST-C001`: the certified Rust
  driver never calls `Session::record_header`. A real run sends a provider request and records no
  `request/header` event.
- **The executed witness:** `l08d001_baseline_header_gap_characterization`, on draft code `#169` @
  `d8c1658b`, record `assurance/layers/08-l08-d001-rust-blocker.md` on draft docs `#264`.
- **Why it matters:** `L08-D001`'s contract had assumed header recording was existing behaviour in
  both bindings.
- **The cause:** no certified spec required the driver to record a header. Python's driver did; the
  Rust driver did not.

## 2. Characterization

### Python

- **How it was run:** `data/08-l08-d002/probe_python.py`, through the real `AgentLoop`, Session log,
  artifact store and mock provider, at code main `db63adcf`. Output: `data/08-l08-d002/python.json`.
- **Order inside a request build:** TURN_START (or the run's first turn) → the entering messages are
  admitted → system text (override, else `L08-D001` assembler, else the stored prompt) → tool
  schemas → **`record_header`** → `transformContext` → `llm.stream`.

| Scenario | Requests sent | Headers | Observation |
|---|---|---|---|
| single request | 1 | 1 | `user, header, assistant` |
| tool call (two requests) | 2 | 2 | a header per request, after its entering messages |
| provider error stop | 1 | 1 | header kept |
| `transformContext` raises (first request) | 0 | **1** | header published, then the failure; the run settles failed |
| `transformContext` raises (second request) | 1 | 2 | the first request and header intact; the second header without a request |
| assembler raises (`L08-D001`) | 0 | 0 | the failure happens before publication |
| pre-step `Reject` | 0 | 0 | no request is built |
| per-step override | 1 | 1 | the header records the override literally |
| unknown model | 0 | **1** | header published; the eager `UnknownModelError` propagates (certified behaviour) |
| abort during a tool | 2 | 2 | one header per request built |

**Not every failure before the provider send means zero headers.** The `transformContext` and
unknown-model failures happen after publication and keep the header. The Owner asked for exactly
this to be characterized (item 5). The contract codifies Python's existing timing rather than
changing it, so no Python behaviour changes.

### Rust

Inspected read-only at code main `db63adcf` (`minion-agent-rust/crates/minion-agent/src/agent_loop/driver.rs`,
`run_provider_turn_with_decision`):
- **Order:** `transform_context` runs first, then the request is built with fallible schema
  computation, then `llm.stream(request)?`.
- **Headers:** there is no `record_header` call anywhere outside Session tests.
- **What already exists:** `Session::record_header(components, model, tools)` has the Layer 03
  shape. Rust can therefore conform using only existing APIs, by placing the call after schema
  computation and before `transform_context`.

## 3. Contract decisions

All of these follow from the characterization. Each is within the Owner's scope.

| Item | Rule | Why |
|---|---|---|
| Header content | `{system_base: system text}`, `ModelId.model`, the request's schemas | Python's existing content; the Layer 03 format, unchanged |
| Publication point | after entering messages and the final system, model and schemas; before `transformContext` and the provider | Python's existing timing (item 4: preserve Python) |
| Failure before the point | no header (assembler, schema computation, `Reject`) | matches Python and `L08-D001` |
| Failure after the point | header kept (`transformContext`, unknown model, provider error or abort) | matches Python; one header per build |
| Duplicates | exactly one per request build | no retry path inside a build |
| Log-only | `request/header` is never surface data | Layer 03 classification, unchanged |
| History | historical logs are untouched | Owner item 6 |
| `L08-D001` | its no-assembler guarantee is relative to the corrected baseline; AG-024 unchanged | Owner "L08-D001 relationship" |

## 4. Evidence

**Canonical cases** (`conformance/agent/request-header-*.yaml`, 7 documents). Two keys are added to
`agent-scenario.schema.json`:
- `expect_request_log`: surface messages interleaved with headers;
- `expect_headers`: the reconstructed system text, component names, model and tool names.

Two additive listener kinds are added to the vocabulary: `agent/pre-step` with `system_override`,
and `agent/transform-context` with `raise` plus `on_request`. The cases are:

| Case | Covers |
|---|---|
| `single-request` | the basic header |
| `one-per-request-in-order` | multi-request order and tool snapshot |
| `provider-error-keeps-the-header` | a provider failure after publication |
| `unknown-model-recorded-before-eager-failure` | eager failure after publication; `expect_error` |
| `records-the-literal-override` | the per-step override |
| `transform-failure-first-request` | first-turn failure after publication |
| `transform-failure-later-request` | later-turn failure; earlier records intact |

**Python runner:** `tests/conformance/agent_runner.py` observes the log and headers through the real
Session; it adds no behaviour. All 7 pass with the **unchanged** Python driver.

**Kill controls** (`data/08-l08-d002/controls.py`, disposable copy of the Python driver). All 5 are
valid kills, exit 0:

| Mutant | Killed by |
|---|---|
| Header after `transformContext` | exactly the two transform-failure cases (this pins the timing) |
| No header | all 7 |
| Duplicate header | all 7 |
| Stored prompt instead of the override | the override case |
| Provider-qualified model | all 7 |

**Gates (code PR head):**

| Platform | Result |
|---|---|
| Windows, pinned ICU | **5,332 passed, 48 skipped, 21 xfailed**; coverage **100%**; ruff and mypy clean |
| Linux | **5,285 passed, 0 failed, 97 skipped, 19 xfailed** |

## 5. Implementation scope after approval

- **Python:** none beyond the runner support already here. Its witnesses are these canonical
  cases.
- **Rust:**
  - the driver calls `Session::record_header` at the defined point;
  - the Rust agent-loop conformance runner gains `expect_request_log`, `expect_headers` and the two
    listener kinds;
  - the regressions the Owner requires: projection, fork, compaction and the certified Layer 08
    suites.
- **Serialization:** the Rust `L08-D001` branch (`#169`) must not change the same driver code
  concurrently. Integrate `L08-D002` first, then rebase `L08-D001` (Owner).

## 6. Requested review

An independent contract-delta review covering:
1. the publication point and its failure split, against the Python characterization;
2. whether the canonical observable (surface messages interleaved with headers, plus reconstructed
   headers) is language-neutral and sufficient;
3. Rust feasibility with the existing `Session::record_header`, including the fallible schema
   computation coming before publication;
4. the `L08-D001` dependency clarification.
