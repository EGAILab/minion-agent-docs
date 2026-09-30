# L0506-D001 — Rust implementation progress

**Status: IN PROGRESS / NOT CERTIFIED.** This is a resumable implementation checkpoint,
not a closure candidate or a request for independent closure review.

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
