# Minion Agent Rust — Plan 2: LLM, Session, and Telemetry Implementation Plan

> **Status note (2026-08-21): written against the superseded 2026-08-18 design.** Per the frozen
> `2026-08-20-minion-agent-design.md`'s realignment guidance (§9), Rust must rewrite its Phase 2+
> executable plans against the frozen master, `minion-agent-docs/spec/`, and `pi-parity-manifest.yaml`
> before implementing semantic Phase 2+. Do not implement against this plan's LLM
> vocabulary/transformation/session content without cross-checking the current spec first.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the provider-neutral LLM and self-enforcing stream boundary, append-only session semantics with content-addressed request state, and observational telemetry on the green Plan 1 runtime.

**Architecture:** Immutable serde vocabulary is independent of sessions; `LlmService` wraps raw adapters so an already-returned stream exposes chunks only and exactly one terminal. `SessionService` owns atomic append logs, open string event identities, explicit surface projections, immutable ancestry, and a shared artifact store. Telemetry sanitizes before snapshotting sinks and cannot affect observed work.

**Tech Stack:** Plan 1 stack plus bytes, base64, and sha2 in the library; existing serde_yaml, jsonschema, proptest, and anyhow remain tooling/test-only.

**Spec:** `minion-agent-docs/plans/rust/2026-08-18-rust-phases-0-2-implementation-design.md`, implementing `minion-agent-docs/design/2026-08-18-minion-agent-design.md` §4, §5, §7 telemetry, and §8.

## Global Constraints

- Plan 1 is complete and its public APIs are the only runtime integration surface.
- The canonical source is a clean committed `minion-agent-python/conformance/`; Rust vendors exact files and hashes.
- Conformance remains exactly three families: `runtime`, `session`, and `agent`; no `llm` family is added.
- The Phase 2 `agent` runner is a partial adapter over the real `LlmService` and `AssistantStream`; it contains no stream settlement policy.
- Eager caller/configuration/model failures return `LlmStartError` before a stream exists.
- After return, `AssistantStream` exposes no `Result` items or iteration errors, preserves accumulated partial content on premature EOF, emits exactly one terminal, then fuses without hidden draining.
- Panics remain programming/invariant failures; expected adapter/provider faults are represented values.
- The event-kind namespace is open, string-value based, and loggable without prior registration; surface admission is separate and explicit.
- Sequence allocation, event validation, and append are one atomic session operation; sequence order equals commit order.
- Reset is a boundary; compaction is deterministic explicit replacement with retained provenance; fork ancestry is referenced, never copied.
- Artifact references in committed model-visible state remain resolvable; V1 has no artifact deletion.
- Telemetry sanitization precedes sinks; sink failures never change observed semantics.
- No executable agent loop, inbox, tool registry, tool pipeline, real provider, persistence backend, compaction trigger policy, or production telemetry sink is introduced.
- Core `llm/**`, `session/**`, and `telemetry/**` files join the per-file 100% line-coverage gate.
- Every public Phase 2 API is exercised by current conformance or Tier-2 tests.
- Use TDD, deterministic synchronization, conventional commits, and one commit per task.

---

## File Structure

```text
minion-agent-rust/crates/minion-agent/src/
  llm/
    mod.rs
    content.rs
    message.rs
    request.rs
    stream.rs
    service.rs
    mock.rs
  session/
    mod.rs
    event.rs
    log.rs
    codec.rs
    derive.rs
    operation.rs
    artifact.rs
    header.rs
    service.rs
  telemetry/
    mod.rs
    span.rs
    sanitize.rs
    service.rs

minion-agent-rust/crates/minion-agent/tests/
  llm_content.rs
  llm_stream.rs
  llm_service.rs
  agent_stream_conformance.rs
  session_event.rs
  session_log.rs
  session_derive.rs
  session_operation.rs
  session_artifact.rs
  session_conformance.rs
  session_properties.rs
  telemetry.rs
  phase2_public.rs
  support/agent_stream_scenario.rs
  support/session_scenario.rs

minion-agent-python/
  conformance/schema/agent-scenario.schema.json
  conformance/agent/*stream*.yaml
  tests/conformance/agent_stream_runner.py
  tests/conformance/test_agent_stream_conformance.py
```

Each file owns one concern. Message storage encoding lives in `session/codec.rs`,
not in `llm`; the LLM vocabulary does not know a log exists. The conformance
support files parse, arrange fixtures, and project results only.

---

### Task 1: Add canonical agent-family stream probes and keep Python green

**Files:**
- Modify: `minion-agent-python/conformance/schema/agent-scenario.schema.json`
- Create: `minion-agent-python/conformance/agent/premature-eof-synthesizes-error-terminal.yaml`
- Create: `minion-agent-python/conformance/agent/premature-eof-preserves-partial-message.yaml`
- Create: `minion-agent-python/conformance/agent/public-stream-fuses-after-first-terminal.yaml`
- Create: `minion-agent-python/conformance/agent/eager-invalid-model-fails-before-stream.yaml`
- Create: `minion-agent-python/conformance/agent/represented-provider-error-rides-stream.yaml`
- Create: `minion-agent-python/tests/conformance/agent_stream_runner.py`
- Create: `minion-agent-python/tests/conformance/test_agent_stream_conformance.py`
- Modify: `minion-agent-docs/plans/python/2026-08-18-plan-3-agent-loop.md`

**Interfaces:**
- Consumes: the already-landed Python `LlmService` settlement wrapper and open
  event/session alignment.
- Produces: five canonical `agent/` stream scenarios executable before the full
  agent loop, plus a partial Python runner that Plan 3 extends.

- [ ] **Step 1: Confirm the source repositories are clean**

Run `git status --short` in both `minion-agent-python` and
`minion-agent-docs`. Expected: no unrelated changes. Confirm the Python source
is commit `88aa220` or a clean descendant containing the two lifecycle cases
before adding the stream cases.

- [ ] **Step 2: Extend the agent schema for a stream probe without adding a family**

Keep existing full-agent fields. Retain `config` as an open object for future
full-agent settings, but add an `if`/`then` branch: when `config.probe` is
`stream`, require `config.model` with non-empty `provider` and `model` strings;
the `then` schema restates `probe` and `model` before setting
`additionalProperties: false`. Add `scriptedResponse.truncated: bool` and
`scriptedResponse.after_terminal` as an array of `contentBlock` values that the
fixture emits after its normal terminal. Keep `additionalProperties: false`
wherever the schema already closes objects.

The partial runner selects only documents whose config contains
`probe: stream`; ordinary agent scenarios remain for Plan 3.

- [ ] **Step 3: Write the five canonical YAML cases**

Use this complete shape for premature EOF:

```yaml
name: a truncated provider stream settles instead of raising
description: The returned stream synthesizes one error terminal.
config:
  probe: stream
  model: { provider: mock, model: mock-1 }
provider_script:
  - stop_reason: stop
    truncated: true
    content: [{ type: text, text: half a sentence }]
steps:
  - followup: hello
expect_events:
  - type: stream_start
  - { type: text_delta, text: half a sentence }
  - { type: stream_error, stop_reason: error, error_contains: without a terminal chunk }
expect_messages:
  - { role: assistant, text: half a sentence, stop_reason: error }
```

The preservation case additionally asserts usage/model/provider fields. The
fusion case scripts one normal terminal plus `after_terminal` output and expects
only the first terminal. The eager-invalid-model case names `mock/missing` and
expects `UnknownModelError` with no events. The represented-provider-error case
expects an in-band `StreamError`.

- [ ] **Step 4: Run schema validation and show the runner is missing**

Run:

```text
uv run pytest tests/conformance/test_schema_validation.py -v
uv run pytest tests/conformance/test_agent_stream_conformance.py -v
```

Expected: schema validation passes after Step 2; stream tests fail because the
partial runner is not implemented.

- [ ] **Step 5: Implement the thin Python stream runner**

The runner may convert scripted YAML to raw chunks, create a fixture adapter,
call the real `LlmService.stream`, iterate it, and normalize observed chunks and
the settled message. It must not synthesize EOF terminals, suppress
post-terminal output, or decide eager/in-band behavior; those remain in
`LlmService`.

Expose:

```python
async def run_agent_stream_scenario(document: dict[str, Any]) -> dict[str, Any]:
    """Return observed events, messages, or normalized eager error."""
```

- [ ] **Step 6: Remove duplicate future work from Python Plan 3**

Change its stream-case task to consume and extend the already-landed partial
runner. Preserve the five scenario names and state that Plan 3 adds agent-loop
operations to the same adapter rather than recreating the files.

- [ ] **Step 7: Restore Python green and commit each repository**

Run in Python:

```text
uv run pytest
uv run ruff check .
uv run mypy
```

Commit Python:

```text
git add conformance tests/conformance
git commit -m "test: add canonical agent stream boundary cases"
```

Commit the Python plan adjustment separately in docs:

```text
git add plans/python/2026-08-18-plan-3-agent-loop.md
git commit -m "docs: consume canonical stream probes in Python plan 3"
```

---

### Task 2: Sync the updated canonical snapshot into Rust

**Files:**
- Modify by sync: `minion-agent-rust/conformance/SOURCE.json`
- Modify by sync: `minion-agent-rust/conformance/schema/agent-scenario.schema.json`
- Create by sync: `minion-agent-rust/conformance/agent/*.yaml`

**Interfaces:**
- Consumes: clean Python commit from Task 1.
- Produces: exact Phase 2 canonical snapshot.

- [ ] **Step 1: Verify Python is clean and green**

Run `git status --short`, `uv run pytest`, `uv run ruff check .`, and
`uv run mypy` in `minion-agent-python`. Stop if any fail.

- [ ] **Step 2: Sync and verify**

Run in Rust:

```text
cargo run -p xtask -- conformance sync --source ..\minion-agent-python
cargo run -p xtask -- conformance verify
cargo test -p xtask --test conformance_snapshot
```

Expected: `SOURCE.json` records Task 1's Python commit and all five agent stream
files.

- [ ] **Step 3: Commit**

```text
git add conformance
git commit -m "test: sync Phase 2 canonical conformance"
```

---

### Task 3: Implement immutable LLM content and message vocabulary

**Files:**
- Create: `minion-agent-rust/crates/minion-agent/src/llm/mod.rs`
- Create: `minion-agent-rust/crates/minion-agent/src/llm/content.rs`
- Create: `minion-agent-rust/crates/minion-agent/src/llm/message.rs`
- Create: `minion-agent-rust/crates/minion-agent/src/llm/request.rs`
- Modify: `minion-agent-rust/crates/minion-agent/src/lib.rs`
- Create: `minion-agent-rust/crates/minion-agent/tests/llm_content.rs`

**Interfaces:**
- Consumes: bytes, serde, serde_json.
- Produces: `ContentBlock`, `ImageSource`, `ArtifactHash`, `ModelId`, `Request`,
  `StopReason`, `Usage`, `UserMessage`, `AssistantMessage`,
  `ToolResultMessage`, and `Message`.

- [ ] **Step 1: Write failing serde and invariant tests**

Round-trip every content/message variant through JSON. Assert image inline bytes
encode as base64 only in JSON, artifact references use `sha256:<64 hex>`, usage
total excludes reasoning, and settled assistant messages cannot use
`StopReason::Pending`.

- [ ] **Step 2: Run tests to verify failure**

Run: `cargo test -p minion-agent --test llm_content`

- [ ] **Step 3: Implement the tagged vocabulary**

```rust
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum ContentBlock {
    Text { text: String },
    Thinking { thinking: String },
    Image { mime_type: String, source: ImageSource },
    ToolCall { id: String, name: String, arguments: serde_json::Map<String, Value> },
}
```

Use a custom serde representation so image JSON has exactly one of `data` or
`reference`, matching conformance. Define message enums tagged by `role` and
timestamps as signed 64-bit integers matching the language-neutral data.
Define `ModelId { provider: String, model: String }` and `Request { model,
system, messages, max_output_tokens }` in `request.rs` so the stream and service
tasks use one vocabulary rather than redeclaring request identity.

- [ ] **Step 4: Run focused checks and commit**

Run: `cargo test -p minion-agent --test llm_content`

```text
git add crates/minion-agent Cargo.toml Cargo.lock
git commit -m "feat: add provider-neutral LLM vocabulary"
```

---

### Task 4: Implement stream chunks and the contract-enforcing AssistantStream

**Files:**
- Create: `minion-agent-rust/crates/minion-agent/src/llm/stream.rs`
- Modify: `minion-agent-rust/crates/minion-agent/src/llm/mod.rs`
- Create: `minion-agent-rust/crates/minion-agent/tests/llm_stream.rs`

**Interfaces:**
- Consumes: LLM messages from Task 3 and `futures::Stream`.
- Produces: `StreamChunk`, `RawAssistantStream`, `AssistantStream`,
  `AdapterStreamError`, and `collect`.

- [ ] **Step 1: Write the public stream contract tests**

Use `stream::iter` and `poll_fn` fixtures to cover normal completion,
represented provider error, empty EOF, partial EOF, raw `Err`, first-terminal
fusion, and no polling after terminal. For partial EOF assert text, usage,
provider, and model are preserved while stop reason becomes `Error`.

- [ ] **Step 2: Write the no-hidden-drain test**

Wrap a raw stream whose poll counter panics if polled after yielding its first
terminal. Drain the public wrapper and assert exactly one poll sequence and one
terminal.

- [ ] **Step 3: Run tests to verify failure**

Run: `cargo test -p minion-agent --test llm_stream`

- [ ] **Step 4: Implement raw and public stream types**

```rust
pub type RawAssistantStream = Pin<Box<dyn Stream<Item = Result<StreamChunk, AdapterStreamError>> + Send>>;

pub struct AssistantStream {
    source: RawAssistantStream,
    request_model: ModelId,
    partial: Option<AssistantMessage>,
    fused: bool,
}
```

Implement `Stream<Item = StreamChunk>`. Update `partial` from every observed
chunk. Convert a raw `Err` or premature EOF into one `StreamError`. For an empty
source create a deterministic empty partial with timestamp `0`. On the first
terminal set `fused = true`, drop the source, and return `None` on every later
poll without polling it.

- [ ] **Step 5: Implement collect over the public contract**

`collect(AssistantStream) -> AssistantMessage` drains until its guaranteed
terminal and returns that message. It has no operational error return; an EOF
without terminal is unreachable through the wrapper.

- [ ] **Step 6: Run focused checks and commit**

Run: `cargo test -p minion-agent --test llm_stream`

```text
git add crates/minion-agent
git commit -m "feat: enforce the assistant stream boundary"
```

---

### Task 5: Implement LlmService and the scripted mock adapter

**Files:**
- Create: `minion-agent-rust/crates/minion-agent/src/llm/service.rs`
- Create: `minion-agent-rust/crates/minion-agent/src/llm/mock.rs`
- Modify: `minion-agent-rust/crates/minion-agent/src/llm/mod.rs`
- Create: `minion-agent-rust/crates/minion-agent/tests/llm_service.rs`

**Interfaces:**
- Consumes: Plan 1 `Service`, Phase 2 vocabulary and stream wrapper.
- Produces: `Adapter`, `LlmStartError`, `LlmService`, `ScriptedResponse`, and
  `MockAdapter`; `ModelId` and `Request` are consumed from Task 3.

- [ ] **Step 1: Write failing eager/in-band tests**

Assert unknown model is `Err(LlmStartError::UnknownModel)` before a stream is
returned; registered models return wrapped streams; withdrawing one adapter
does not withdraw a replacement; exhausting the mock script returns an in-band
error message.

- [ ] **Step 2: Run tests to verify failure**

Run: `cargo test -p minion-agent --test llm_service`

- [ ] **Step 3: Define the adapter and service contracts**

```rust
pub trait Adapter: Send + Sync + 'static {
    fn provider(&self) -> &str;
    fn models(&self) -> BTreeSet<String>;
    fn stream(&self, request: Request) -> Result<RawAssistantStream, LlmStartError>;
}

impl Service for LlmService { const NAME: &'static str = "llm"; }
```

`LlmService::stream` resolves the adapter, invokes its eager method, and wraps
the raw stream before returning. Registration returns a lifecycle handle that
removes only mappings still owned by that adapter.

- [ ] **Step 4: Implement deterministic MockAdapter**

Store scripted responses in a mutex-protected queue and requests in source
order. Emit start/delta/end/terminal chunks with full partial messages. Script
exhaustion is a raw represented adapter error that the public wrapper settles
in-band.

- [ ] **Step 5: Mount it through the real runtime and commit**

Add a test plugin providing `LlmService` through `Context::provide`; require it
by type and perform one mock request.

Run: `cargo test -p minion-agent --test llm_service`

```text
git add crates/minion-agent
git commit -m "feat: add LLM service and scripted adapter"
```

---

### Task 6: Pass canonical agent stream probes through the real Rust service

**Files:**
- Create: `minion-agent-rust/crates/minion-agent/tests/support/agent_stream_scenario.rs`
- Create: `minion-agent-rust/crates/minion-agent/tests/agent_stream_conformance.rs`

**Interfaces:**
- Consumes: vendored agent scenarios and real `LlmService`/`AssistantStream`.
- Produces: exact observed event/message/error projections for stream probes.

- [ ] **Step 1: Parse only `config.probe: stream` scenarios**

Deserialize with `deny_unknown_fields` into fixture DTOs mirroring the vendored
schema. Assert all five expected scenario names load.

- [ ] **Step 2: Run conformance to verify failures**

Run: `cargo test -p minion-agent --test agent_stream_conformance -- --nocapture`

Expected: failures until the adapter fixture/projection is wired.

- [ ] **Step 3: Implement fixture conversion and observation**

Convert `provider_script` to a raw fixture adapter, including truncation and
post-terminal entries. Convert `followup` text to a real `Request`, call
`LlmService::stream`, and record chunks actually yielded. For eager errors,
record the returned `LlmStartError` without constructing a stream.

Do not synthesize terminal chunks or stop on a terminal inside the runner;
ordinary stream iteration delegates both decisions to `AssistantStream`.

- [ ] **Step 4: Run all five scenarios and commit**

Run: `cargo test -p minion-agent --test agent_stream_conformance`

```text
git add crates/minion-agent/tests
git commit -m "test: pass canonical stream boundary cases"
```

---

### Task 7: Implement open session event identities and lifecycle-owned extensions

**Files:**
- Create: `minion-agent-rust/crates/minion-agent/src/session/mod.rs`
- Create: `minion-agent-rust/crates/minion-agent/src/session/event.rs`
- Modify: `minion-agent-rust/crates/minion-agent/src/lib.rs`
- Create: `minion-agent-rust/crates/minion-agent/tests/session_event.rs`

**Interfaces:**
- Consumes: `EventName`, serde_json, Plan 1 effect ownership.
- Produces: `SessionEventKind`, core constants, `EventExtensions`, validation
  and optional `SurfaceProjection`, and removable registration handles.

- [ ] **Step 1: Write failing open-namespace tests**

Assert `plugin/note` is well formed and loggable without registration;
`Plugin/Note`, empty segments, and whitespace fail. Assert independent values
with the same spelling compare equal. Registration invokes additional
validation but does not make the event surface; adding an explicit projection
does. Disposal removes extension behavior without invalidating the string name.

- [ ] **Step 2: Run tests to verify failure**

Run: `cargo test -p minion-agent --test session_event`

- [ ] **Step 3: Implement string newtype and extension table**

Use the canonical lowercase-segment pattern. Core constants return the same
newtype as arbitrary names. Implement an internal name-keyed `EventExtensions`
table whose entries contain optional validation and projection callbacks and
are registered through runtime effect handles. `SessionLog` consumes the table
in Task 8, and `SessionService` owns it when that service is assembled in Task
11. Unknown well-formed names receive only JSON-object validation and remain
log-only.

- [ ] **Step 4: Run tests and commit**

Run: `cargo test -p minion-agent --test session_event`

```text
git add crates/minion-agent Cargo.toml Cargo.lock
git commit -m "feat: add extensible session event identities"
```

---

### Task 8: Implement atomic append-only session logs and message codec

**Files:**
- Create: `minion-agent-rust/crates/minion-agent/src/session/log.rs`
- Create: `minion-agent-rust/crates/minion-agent/src/session/codec.rs`
- Modify: `minion-agent-rust/crates/minion-agent/src/session/mod.rs`
- Create: `minion-agent-rust/crates/minion-agent/tests/session_log.rs`

**Interfaces:**
- Consumes: session events and LLM messages.
- Produces: `SessionId`, `SessionEvent { seq, kind, data }`, `SessionLog`,
  `encode_message`, and `decode_message`.

- [ ] **Step 1: Write failing append and codec tests**

Assert sequences start at one, validation failure creates no gap, event order is
commit order, raw and typed append share validation, every message round-trips,
and inline image bytes serialize as base64. Add a concurrent append test with a
barrier and assert returned sequence order equals the order events appear.

- [ ] **Step 2: Run tests to verify failure**

Run: `cargo test -p minion-agent --test session_log`

- [ ] **Step 3: Implement one atomic append critical section**

Store events behind a short-held mutex. `append(kind, Map<String, Value>)`
validates name, JSON object, registered validator, allocates `len + 1`, pushes,
and returns the committed clone under that one lock. No async work occurs in
the append boundary.

- [ ] **Step 4: Implement canonical message JSON codec**

Keep encoding out of `llm`. Match the Python/canonical `role`, `type`, usage,
stop-reason, image, and tool-call field spellings exactly. Reject unknown roles
and blocks with concrete `SessionCodecError`.

- [ ] **Step 5: Run tests and commit**

Run: `cargo test -p minion-agent --test session_log`

```text
git add crates/minion-agent
git commit -m "feat: add atomic append-only session log"
```

---

### Task 9: Implement surface derivation, reset, and compaction replacement

**Files:**
- Create: `minion-agent-rust/crates/minion-agent/src/session/derive.rs`
- Create: `minion-agent-rust/crates/minion-agent/src/session/operation.rs`
- Modify: `minion-agent-rust/crates/minion-agent/src/session/mod.rs`
- Create: `minion-agent-rust/crates/minion-agent/tests/session_derive.rs`
- Create: `minion-agent-rust/crates/minion-agent/tests/session_operation.rs`

**Interfaces:**
- Consumes: event snapshots and message codec.
- Produces: `derive_messages`, `reset`, `compact`, and explicit compaction
  replacement records.

- [ ] **Step 1: Write failing derivation tests**

Cover core surface filtering, plugin kind log-only by default, explicit plugin
projection, raw-name value equality for reset/compaction, reset floor, one
compaction, repeated/overlapping compaction, nested replacement, retained-tail
overlap, and messages appended after compaction.

- [ ] **Step 2: Run tests to verify failure**

Run:

```text
cargo test -p minion-agent --test session_derive
cargo test -p minion-agent --test session_operation
```

- [ ] **Step 3: Implement derivation as an ordered operation fold**

Snapshot the log, walk it in sequence order, and compare kinds by string value.
Reset clears the current effective surface. Compaction replaces its recorded
effective range with one summary node plus retained entries identified by
provenance. Track original event identity so retained content cannot appear
twice. Plugin projections run only for explicitly admitted names.

- [ ] **Step 4: Implement reset and compact append helpers**

`reset` appends `session/reset`. `compact(summary, keep)` computes the current
effective surface, records superseded range and retained event identities, and
appends `compaction`; it never edits or deletes entries.

- [ ] **Step 5: Run focused tests and commit**

Run both focused test commands above.

```text
git add crates/minion-agent
git commit -m "feat: derive reset and compacted session history"
```

---

### Task 10: Implement content-addressed artifacts and request headers

**Files:**
- Create: `minion-agent-rust/crates/minion-agent/src/session/artifact.rs`
- Create: `minion-agent-rust/crates/minion-agent/src/session/header.rs`
- Modify: `minion-agent-rust/crates/minion-agent/src/session/mod.rs`
- Create: `minion-agent-rust/crates/minion-agent/tests/session_artifact.rs`

**Interfaces:**
- Consumes: bytes, sha2, session append, and Task 3 `ArtifactHash`.
- Produces: `ArtifactStore`, `RequestComponents`,
  `assemble_system`, `record_header`, and `reconstruct_header`.

- [ ] **Step 1: Write failing artifact/header tests**

Assert identical bytes deduplicate, different bytes do not, hashes use lowercase
SHA-256, missing references return `MissingArtifact`, and a header/event cannot
commit an unresolved artifact hash. Assert no deletion API exists, stable
components store once across headers, sorted names define assembly, and
reconstruction equals dispatch assembly byte-for-byte.

- [ ] **Step 2: Run tests to verify failure**

Run: `cargo test -p minion-agent --test session_artifact`

- [ ] **Step 3: Implement immutable storage and canonical composition**

Store `Arc<[u8]>` by `ArtifactHash` behind a short-held lock. `put` is
idempotent. `RequestComponents` uses `BTreeMap<String, ArtifactHash>` so
assembly is deterministic. Validate every referenced hash before atomically
appending a header or model-visible event. Header append stores only component
hashes and model identity.

- [ ] **Step 4: Add image normalization**

Provide a session helper that writes `ImageSource::Inline` bytes to the store
and returns `ImageSource::Artifact`; model dispatch preparation uses this helper
before logging/request dispatch. Do not put artifact resolution into the LLM
vocabulary.

- [ ] **Step 5: Run tests and commit**

Run: `cargo test -p minion-agent --test session_artifact`

```text
git add crates/minion-agent Cargo.toml Cargo.lock
git commit -m "feat: add content-addressed request state"
```

---

### Task 11: Implement immutable fork ancestry and SessionService

**Files:**
- Create: `minion-agent-rust/crates/minion-agent/src/session/service.rs`
- Modify: `minion-agent-rust/crates/minion-agent/src/session/log.rs`
- Modify: `minion-agent-rust/crates/minion-agent/src/session/derive.rs`
- Modify: `minion-agent-rust/crates/minion-agent/src/session/mod.rs`
- Create: `minion-agent-rust/crates/minion-agent/tests/session_fork.rs`

**Interfaces:**
- Consumes: complete log, operations, and artifact store.
- Produces: `SessionService::create`, `get`, `fork`; registered runtime service
  name `sessions`.

- [ ] **Step 1: Write failing fork tests**

Assert a child derives ancestor surface only through its fixed boundary, later
writes stay branch-local, no surface event is copied into the child log,
compaction inside the fork leaves the ancestor unchanged, and a fork keeps the
source alive through `Arc` ancestry.

- [ ] **Step 2: Run tests to verify failure**

Run: `cargo test -p minion-agent --test session_fork`

- [ ] **Step 3: Implement service and ancestry**

`SessionService` stores logs by `SessionId` and one shared `ArtifactStore`.
`SessionLog` holds `Option<Arc<SessionLog>>` plus fixed boundary. `fork` appends
only `session/forked` to the child and rejects duplicate session IDs. Mount the
service through a real Plan 1 plugin.

- [ ] **Step 4: Run tests and commit**

Run: `cargo test -p minion-agent --test session_fork`

```text
git add crates/minion-agent
git commit -m "feat: add session service and fork ancestry"
```

---

### Task 12: Pass every canonical session scenario

**Files:**
- Create: `minion-agent-rust/crates/minion-agent/tests/support/session_scenario.rs`
- Create: `minion-agent-rust/crates/minion-agent/tests/session_conformance.rs`

**Interfaces:**
- Consumes: vendored session schema/scenarios and real session APIs.
- Produces: exact derived-message or normalized-error results.

- [ ] **Step 1: Parse all session scenarios with closed DTOs**

Mirror `surface_kinds`, append, fork, reset, compact, derive, expected messages,
and errors. Unknown fixture keys fail deserialization.

- [ ] **Step 2: Implement thin execution**

Create a real `SessionService`, apply each step via public APIs, and project
`derive_messages` into the canonical role/text form. The runner must not filter
surface events, apply compaction, or traverse ancestry itself.

- [ ] **Step 3: Run canonical session conformance**

Run: `cargo test -p minion-agent --test session_conformance -- --nocapture`

Expected: reset, repeated/overlapping compaction, fork-local compaction,
event-name identity, plugin-defined surface, and log-only default cases pass.

- [ ] **Step 4: Commit**

```text
git add crates/minion-agent/tests
git commit -m "test: pass canonical session conformance"
```

---

### Task 13: Implement typed telemetry, mandatory sanitization, and isolated sinks

**Files:**
- Create: `minion-agent-rust/crates/minion-agent/src/telemetry/mod.rs`
- Create: `minion-agent-rust/crates/minion-agent/src/telemetry/span.rs`
- Create: `minion-agent-rust/crates/minion-agent/src/telemetry/sanitize.rs`
- Create: `minion-agent-rust/crates/minion-agent/src/telemetry/service.rs`
- Modify: `minion-agent-rust/crates/minion-agent/src/lib.rs`
- Create: `minion-agent-rust/crates/minion-agent/tests/telemetry.rs`

**Interfaces:**
- Consumes: serde JSON values and Plan 1 service/effect APIs.
- Produces: `SpanKind`, `Span`, `Sanitizer`, `TelemetrySink`, `TelemetryService`,
  `RecordingSink`, and diagnostic sink-failure records.

- [ ] **Step 1: Write failing sanitization and sink tests**

Cover nested object/array string redaction, empty-secret rejection, secret
removal, fixed sink snapshot, failing first sink with healthy second sink, no
sinks, and proof that callers receive no semantic failure from emission.

- [ ] **Step 2: Run tests to verify failure**

Run: `cargo test -p minion-agent --test telemetry`

- [ ] **Step 3: Implement the mandatory boundary**

`TelemetryService::emit` first clones/sanitizes the entire span, then snapshots
sink `Arc`s, then calls each sink. `TelemetrySink::emit` returns
`Result<(), SinkError>`; collect failures into an observational diagnostic
buffer and continue. Never pass raw spans to a sink callback.

- [ ] **Step 4: Mount and withdraw sinks through effects**

Implement `Service for TelemetryService` with name `telemetry`. A recording
plugin provides the service and registers `RecordingSink`; disposal removes the
sink. Do not add file, debug, or OpenTelemetry sinks.

- [ ] **Step 5: Run tests and commit**

Run: `cargo test -p minion-agent --test telemetry`

```text
git add crates/minion-agent
git commit -m "feat: add sanitized observational telemetry"
```

---

### Task 14: Add Phase 2 properties and expand enforcement gates

**Files:**
- Create: `minion-agent-rust/crates/minion-agent/tests/session_properties.rs`
- Modify: `minion-agent-rust/xtask/src/coverage.rs`
- Modify: `minion-agent-rust/xtask/src/layering.rs`
- Modify as coverage requires: `minion-agent-rust/crates/minion-agent/src/{llm,session,telemetry}/*.rs`

**Interfaces:**
- Consumes: complete Phase 2 services and Plan 1 gates.
- Produces: stream/session properties and 100% scoped coverage for all Phase
  1–2 semantic modules.

- [ ] **Step 1: Add stream-shape properties**

Generate zero or more nonterminals followed by zero, one, or multiple raw
terminals. Assert the public result is always `nonterminal* → one terminal →
EOF`, preserves the latest partial on missing terminal, and never polls after
fusion.

- [ ] **Step 2: Add session properties**

Generate typed appends/resets/compactions and assert unique strictly increasing
committed sequences, reset exclusion, no duplicate retained messages, and JSON
round-trip stability. Generate arbitrary well-formed plugin event names and
assert logging does not imply surface admission.

- [ ] **Step 3: Expand layering rules**

Enforce `llm -> no session/agent/tools`, `session -> no agent/tools`, and
`telemetry -> no agent/tools`. Include fixtures for imports and qualified paths.

- [ ] **Step 4: Expand coverage scope**

Require per-file 100% lines under `src/llm`, `src/session`, and `src/telemetry`
in addition to `src/runtime`. Keep exclusions source-location-specific with a
reason.

- [ ] **Step 5: Run gates and commit**

Run:

```text
cargo test -p minion-agent --all-features
cargo run -p xtask -- layering verify
cargo run -p xtask -- coverage verify
```

```text
git add crates/minion-agent xtask
git commit -m "test: enforce Phase 2 properties and quality gates"
```

---

### Task 15: Freeze Phase 2 public APIs and verify both implementations

**Files:**
- Modify: `minion-agent-rust/crates/minion-agent/src/{llm,session,telemetry}/mod.rs`
- Modify: `minion-agent-rust/crates/minion-agent/src/lib.rs`
- Create: `minion-agent-rust/crates/minion-agent/tests/phase2_public.rs`
- Modify: `minion-agent-rust/README.md`

**Interfaces:**
- Consumes: all Plan 2 components.
- Produces: documented, tested Phase 0–2 public surface ready for Plan 3.

- [ ] **Step 1: Write a public-only composition test**

Using no private modules: mount LLM, session, and telemetry plugins; create a
session; append a user message; record/reconstruct a request header; run a mock
stream; append the settled assistant message; derive history; emit a sanitized
span. Assert every observable result.

- [ ] **Step 2: Remove speculative exports and unused dependencies**

Every exported item must be used by canonical conformance, a Tier-2 test, or
the public-only composition test. Remove unused `parking_lot`, `indexmap`,
`async-trait`, or any other budgeted crate if implementation did not require it.
Do not add forward-only agent/tool types.

- [ ] **Step 3: Verify Python at the snapshot revision**

In the clean current Python checkout run:

```text
uv run pytest
uv run ruff check .
uv run mypy
```

Expected: green, including runtime/session/agent stream conformance available
through Phase 2.

- [ ] **Step 4: Run every Rust gate**

Run:

```text
cargo fmt --check
cargo clippy --workspace --all-targets --all-features -- -D warnings
cargo test --workspace --all-features
cargo run -p xtask -- coverage verify
cargo run -p xtask -- layering verify
cargo run -p xtask -- conformance verify
$env:RUSTDOCFLAGS='-D warnings'; cargo doc --workspace --no-deps
```

Expected: all pass without the sibling Python checkout being consulted by any
Rust command.

- [ ] **Step 5: Commit**

```text
git add crates/minion-agent README.md Cargo.toml Cargo.lock
git commit -m "docs: freeze Rust Phase 2 public surface"
```

---

## Definition of Done

- [ ] The canonical suite still has exactly `runtime`, `session`, and `agent`
  families.
- [ ] Five canonical stream-boundary cases pass in Python and Rust.
- [ ] Rust's public stream has exactly one terminal, preserves partial EOF
  content, and performs no hidden post-terminal polling.
- [ ] Unknown models fail eagerly; represented provider faults ride the stream.
- [ ] Open event names are loggable without registration and remain log-only
  without explicit projection.
- [ ] Session append validation and sequence commit are atomic.
- [ ] Reset, repeated/overlapping/nested/fork-local compaction, and fork ancestry
  pass canonical and property tests without duplicate projection.
- [ ] Request reconstruction uses immutable artifacts and the same canonical
  composition function as dispatch.
- [ ] Telemetry sanitizes before sinks and sink failures remain observational.
- [ ] Every public Phase 0–2 API is exercised by current behavior.
- [ ] Python and Rust are green against the same recorded canonical revision.
- [ ] Formatting, Clippy, tests, per-file coverage, layering, snapshot, and
  rustdoc gates pass.
- [ ] No executable Phase 3 semantics or deferred Phase 2+ providers/sinks are
  present.

## Plan 3 Entry Contract

Plan 3 may extend the existing `agent/` conformance adapter and use the public
LLM, session, telemetry, and runtime services. It must not replace stream
settlement, session derivation, or lifecycle behavior with runner-local logic.
