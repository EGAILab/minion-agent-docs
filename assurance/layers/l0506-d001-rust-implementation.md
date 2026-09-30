# L0506-D001 — Rust implementation assurance

**Current status: IMPLEMENTED / CLOSURE CANDIDATE, pending independent review.**
Cross-language closure is not claimed. The final candidate section below supersedes
the historical foundation checkpoint; both stages are preserved for audit.

## Historical foundation checkpoint

The following checkpoint was pushed in code `f3f406e3d2387f1f0c03efc52374a0eb5099153d`
and docs `92358ca02b7f7db47c2da61efba31229d2f718a3`. Its incomplete-state statements
describe that earlier stage only, not the current candidate.

## Accepted starting state

- Code `main`: `a993f5d84adaddd3c8e4a75ab4e146f9deab58d4`.
- Docs `master`: `6076ad357a0a90fe6e889828cf20322032eb01ef`.
- Pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`.
- Coordination: `minion-agent#88`, `RUST_IMPLEMENTATION`, `NEXT_OWNER: Codex`.
- Approved shared/Python merge handoff:
  https://github.com/EGAILab/minion-agent/issues/88#issuecomment-5919432901.

Both defaults were fetched and verified at those SHAs. Fresh task worktrees were
created directly from them; unrelated local work was preserved. Implementation
branches are `rust/l0506-d001` (code) and `assurance/l0506-d001-rust` (docs).
The issue and draft PRs record their exact pushed heads.

## Authority and seam inspection

Re-read pinned `agent-loop.ts::prepareToolCallArguments/prepareToolCall` and
`validation.ts::validateToolArguments`, the approved TOOL-041 section in
`spec/tools.md`, and the existing Rust definition/execution APIs. Preparation
precedes validation, validated runtime arguments reach the before hook and
execute, while the original raw call remains the lifecycle/history source.
The Python-only Pydantic callback mechanism is not a Rust implementation mandate.

The existing Rust seams still use `serde_json::Value` for prepared results,
pre-execute arguments/replacements, and `ToolExecutionRequest.params`. The
existing JSON Schema engine also accepts only that JSON domain. Those seams are
**not changed by this checkpoint**, and non-finite values therefore do not yet
flow through production tool execution.

## Implemented foundation

`tools/prepared.rs` adds a typed `PreparedValue` and `PreparedNumber` vocabulary.
Finite values retain the existing JSON-number representation; the runtime float
constructor preserves binary64 signed zero and explicitly represents positive
infinity, negative infinity, and NaN. Recursive arrays/objects are typed, with
ordinary strings remaining strings. Raw JSON conversion is explicit and lossless.

The type intentionally does not implement `Serialize`. `try_to_json()` rejects
non-finite values with their JSON pointer rather than null-mapping, stringifying,
or clamping them. It is a fallible domain check, not a success-path projection.
No authoritative duplicate argument store, validation workaround, schema change,
manifest status claim, or later built-in edit implementation was introduced.

Four new representation tests cover numeric categories, signed zero, exact raw
JSON round-tripping, missing/null/false/empty distinctions, nested non-finite
conversion errors, and non-coercion of numeric-looking strings. These are
foundation tests only, **not** evidence for the production pipeline or the seven
required delta negative controls.

## Fresh checkpoint gates

- `cargo fmt --all -- --check`: PASS.
- `cargo test -p minion-agent --test prepared_runtime_value --all-features`:
  PASS, **4 passed / 0 failed**.
- `cargo clippy -p minion-agent --test prepared_runtime_value --all-features -- -D warnings`:
  PASS (library plus the new integration-test target only).
- Full workspace tests, strict workspace clippy, rustdoc, xtask conformance,
  shared schema/manifest gates, and lower-layer certification regressions:
  **PENDING**. No old test counts are reused.

The test command used toolchain 1.97.1 and the workspace's pinned ICU4C 78.3
environment: `RUST_ICU_MAJOR_VERSION_NUMBER=78`, the pinned identity file,
`bin64` first on `PATH`, and
`RUSTFLAGS='-L native=E:/AI/Projects/OpenMinds/Minions/Minion-Agent/.toolchain/icu-78.3-src/icu/lib64'`.
Initial attempts without the required version/native search failed inside the
third-party ICU setup (missing version, then missing import library, then system
library selection). The corrected command passed. The pre-existing Windows
`LNK4098` CRT default-library warning remains; it is not a test failure.

## Required continuation

1. Wire the prepared domain into Layer-05 preparation and Layer-06 validation,
   before-hook/replacement and execute parameters. Keep raw calls/lifecycle
   payloads unchanged and preserve existing certified behavior.
2. Implement and verify finite-only declared-number/integer validation while
   retaining unconstrained non-finites and composed-schema acceptance. Do not
   pass a null/string/clamped surrogate as the runtime value or invent a runner
   validator. The validation integration is unfinished, not a discovered shared
   contract defect.
3. Add real-pipeline language tests and a thin canonical runner selecting only
   gate `L0506-D001`: three custom documents / 19 cases. Prove all seven specified
   negative controls. The eight real-edit cases belong to later `WP-13.2` and
   count as neither executed nor passed here.
4. Run all configured Rust/shared gates and lower-layer regressions freshly.
5. Finish Rust evidence-only manifest updates and assurance, push/verify exact
   heads, and then transfer to Claude for independent closure review.

At this checkpoint Python/shared approval remains accepted; Rust is **INCOMPLETE
/ NOT CERTIFIED**, cross-language is **NOT CLOSED**, and `NEXT_OWNER` remains
**Codex**. No later work is started and no merge is requested.

## Final Rust candidate — 2026-10-01

Paired PRs: [code #94](https://github.com/EGAILab/minion-agent/pull/94) and
[docs #203](https://github.com/EGAILab/minion-agent-docs/pull/203). Exact pushed
heads are recorded in their descriptions and issue #88's canonical workflow
object, avoiding a self-referential assurance commit SHA.

### Production ownership and domain boundaries

- `PreparedValue` / `PreparedNumber` carry recursive finite JSON and explicit
  binary64 `NaN`, positive/negative infinity, and signed zero in memory.
- `PrepareArguments` returns this domain. Existing JSON-only
  `with_prepare_arguments` callers retain a lossless conversion wrapper;
  `with_prepare_runtime_arguments` admits the wider result directly.
- Layer-06 `BeforeToolCallContext.arguments`, `Proceed` replacements, and
  `ToolExecutionRequest.params` use the same typed domain. Hooks and execute
  receive actual prepared values, not JSON surrogates. Replacement arguments
  follow the existing no-second-validation rule.
- Original `ToolCall.arguments`, execution-start/update arguments, durable
  message history, and tool-result details remain their certified JSON domain.
  Preparation does not rewrite the raw call. No serializer for the wider domain
  was introduced; explicit `try_to_json()` fails on non-finite values.
- Existing read/ls consumers changed only to read the typed parameter accessors.
  The finite `ls` cap detail remains JSON via a fallible conversion at that
  existing result boundary. No write/edit built-in or WP-13.2 behavior is added.

### JSON Schema integration

`prepared_validation.rs` reuses the existing `jsonschema` engine for traversal,
references, composition, and all nonnumeric structural constraints. Fully JSON
values run the original validator directly, retaining its error behavior.

For non-finite instances the backend uses a **private validation carrier**:
three collision-free finite tags encode the three additional numeric categories.
Tags are chosen after scanning the instance and schema, and never reach public
hooks, execute, history, or diagnostics. Custom keyword factories interpret
numeric identity/constraints (`type`, `const`, `enum`, `uniqueItems`, bounds,
`multipleOf`) while the existing engine still owns schema traversal and branch
acceptance. This is internal validation metadata, not null/string/clamp mapping
of the authoritative runtime value. The actual prepared object is passed onward
unchanged. Binding-local failure text is owned by TOOL-003, not by Pi's diagnostic
JSON.stringify projection.

Seven backend tests cover declared numeric/nullable rejection, complete-value
unconstrained alternatives in both branch orders, nested refs/arrays, null/string/
const/enum distinctions, tag collisions, unique-items identity, numeric bounds,
and older Draft-4 bound modifiers/keyword applicability. The dependency's
`Validator::draft()` accessor does not reflect auto-detected dialect; preserving
`$schema` in keyword-local validators avoids imposing the default dialect on
older-draft schemas. No runner-side schema validator was introduced.

### Canonical and discriminating evidence

`tests/prepared_runtime_conformance.rs` discovers and schema-validates documents,
checks language-neutral token/reference preflight, builds a custom tool, and
invokes the real registry / preparation / validation / hook / execute pipeline.
Numeric tokens are fixture input construction and observation normalization only.

- Gate `L0506-D001`: **3 discovered documents / 19 executed cases / 19 passed**.
- Later gate `WP-13.2`: **1 document / 8 edit cases excluded**, neither executed
  nor counted as delta successes. Acyclic staging remains intact.
- Six permanent fixture controls are killed by the same expected observations:
  reject non-finites, map to null, clamp to a finite maximum, stringify,
  lose signed zero, and lose non-finites in hook replacement.
- Seventh control was RED-confirmed by temporarily changing the production
  non-finite `type` rejection to acceptance. The real canonical test failed at
  `declared-integer-pos-inf` with a hook/execute infinity and no validation error.
  The mutation was restored before all final gates. No weakened validator remains.
- A real pre-execute replacement witness observes preparation's zero at the
  hook and infinity at execute, with the raw start/update arguments unchanged.
- Four representation tests and two preflight refusal controls complement the
  production/canonical evidence. Pydantic-specific callback mechanisms are not
  copied into Rust.

### Fresh final gates

Run against the final source on Windows with Rust **1.97.1**, pinned ICU4C **78.3**
identity/native library search, `bin64` first on `PATH`, and two build jobs:

| Gate | Fresh result |
| --- | --- |
| `cargo fmt --all -- --check` | PASS |
| `cargo clippy --workspace --all-targets --all-features -- -D warnings` | PASS |
| `cargo test --workspace --all-features --quiet` | **435 passed / 0 failed**, including 10 doc tests; dynamically summed across 55 result groups |
| `RUSTDOCFLAGS="-D warnings" cargo doc --workspace --no-deps` | PASS |
| `cargo run -p xtask -- conformance verify` | PASS |
| Shared schema + manifest validation | **306 passed / 0 failed** |
| `git diff --check` | PASS |

All configured lower-layer regressions ran in the full workspace suite, including
the existing read/ls, tool execution, agent, auth, execution-capability, runtime,
session and conformance targets. No old counts are reused.

Earlier continuation attempts revealed an older-dialect bug in the new backend
test (fixed before the final run) and an omitted ICU identity environment value
(corrected command). Neither is left as a hidden failed gate. The pre-existing
Windows `LNK4098` CRT warning remains an environmental linker warning, not a test
failure; strict clippy and rustdoc passed.

### Shared scope, findings, and handoff

The only shared-file delta is TOOL-041's `rust:` evidence pointer. No semantic
rule, disposition, Python source, schema, canonical expectation, or normative
spec changed. The delta is the already-approved Layer-05/06 domain extension;
existing raw-wire/lifecycle behavior and finite JSON behavior are retained.

No active `PI_PARITY_DEFECT`, `CONTRACT_ASSURANCE_DEFECT`, or
`PI_BEHAVIOR_UNCERTAIN` is known in this implementation pass. This is a candidate
assessment, not independent certification. No new divergence is selected.

Shared/Python approval remains accepted. Rust is **IMPLEMENTED / READY FOR
INDEPENDENT CLOSURE REVIEW**; cross-language remains **NOT CLOSED** until the
required review and accepted-branch integration. Transfer issue #88 to
`CLOSURE_REVIEW`, `NEXT_OWNER: Claude` for exact-SHA verification of both PRs.
No merge or later WP-13.2 implementation is performed in this pass.
