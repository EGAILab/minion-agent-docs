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

During final handoff, defaults advanced to code `290ac1fdf3e19b6f8e14c2d491acfdf5a5959c66`
and docs `b15c98659c897b35c99d936d549005a06cd56b98` via shared/Python status-sync
PRs #93/#202. The code default was merged into the implementation branch,
preserving its current approval wording and resolving only the adjoining `rust:`
evidence line. `git diff --exit-code f2042d48e8da57550c7c69513bdc544187627a5c HEAD
-- minion-agent-rust` verified the tested Rust tree remained byte-identical.
Shared schema/manifest gates were rerun after that resolution. The docs status
sync changes only `spec/tools.md`; this assurance branch does not edit that file.

No active `PI_PARITY_DEFECT`, `CONTRACT_ASSURANCE_DEFECT`, or
`PI_BEHAVIOR_UNCERTAIN` is known in this implementation pass. This is a candidate
assessment, not independent certification. No new divergence is selected.

Shared/Python approval remains accepted. Rust is **IMPLEMENTED / READY FOR
INDEPENDENT CLOSURE REVIEW**; cross-language remains **NOT CLOSED** until the
required review and accepted-branch integration. Transfer issue #88 to
`CLOSURE_REVIEW`, `NEXT_OWNER: Claude` for exact-SHA verification of both PRs.
No merge or later WP-13.2 implementation is performed in this pass.

## RC001 remediation after independent closure review

The preceding candidate assessment is historical. Independent review of code
`2ed140396a956955588de4d9d70d8be45861d70d` / docs
`5ae09b32d42ac9511299e6d38084375389c2cad9` found
`L0506-D001-RC001` (`PI_PARITY_DEFECT`): the Rust validator applied numeric
keywords to non-finite runtime values. That assessment did not certify Rust.
Review: https://github.com/EGAILab/minion-agent-docs/pull/203#issuecomment-5922416518.

### Accepted baseline and scope

RC002's shared correction was independently approved and merged before this
remediation started. Accepted defaults:

- Code: `537304b23a53e592e690d33237b9b160a6bfe92d` (#96).
- Docs: `b216eb6a2979e3273ef9105cefb71855250aef80` (#205).
- Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`.

Both default commits were verified remotely using GitHub's connector and merged
into the existing local implementation/assurance branches without rewriting
their history. Issue #88 explicitly authorizes Codex's RC001 remediation against
these merged defaults. RC002 remains closed; I001/I002's settled shared/Python
convergence rules are unchanged.

This is RC001's first remediation attempt after the Rust closure finding, not
another attempt at the settled Python convergence mechanism. Its observable
rule and finite controls are fixed by the accepted RC002 contract. No new
semantic decision, architectural mapping or lower-layer reopen is introduced.

### Production and runner changes

`RuntimeKeyword` now treats `minimum`, `maximum`, `exclusiveMinimum`,
`exclusiveMaximum` and `multipleOf` as inapplicable to non-finite instances.
The existing JSON Schema engine still owns composition, references and traversal:
two successful bound branches make `oneOf` reject, and `not` reverses a successful
bound. Explicit declared-type rejection remains unchanged. Finite instances use
the existing keyword validator, including finite siblings in objects containing
non-finites and older-draft exclusive-bound modifiers. No prepared value is
clamped, projected, stringified or replaced.

The thin canonical runner adds only the eight approved schema fixtures. It
executes the actual preparation/validation/hook/execute seam; it does not
implement applicability or branch verdicts. Aggregate failure reporting now
evaluates every discovered case instead of stopping at the first mismatch.
TOOL-041's Rust evidence pointer is updated to the 50-case corpus; shared rules,
dispositions, Python production, schemas and expected outcomes are unchanged.

### Discriminating evidence

Before changing production, the new fixture dispatch and regression tests were
run against the rejected Rust implementation's unchanged validator:

- Canonical RED: four delta documents / 50 executed cases / 12 failed.
  Failures were maximum (+Infinity, NaN), minimum (-Infinity, NaN),
  exclusive maximum (+Infinity), exclusive minimum (-Infinity), multipleOf
  (+Infinity, NaN), oneOf bounds (+Infinity, -Infinity), and not bounds
  (+Infinity, NaN). This is the count for the new canonical corpus, not the
  independent review's separate 49-cell matrix / 13-cell finding count.
- Both focused validator tests were RED: non-finite -Infinity under minimum
  was incorrectly rejected, and the oneOf bound witness incorrectly accepted.
- Restored/fixed production GREEN: all 50 cases passed; both focused tests
  passed. The full canonical target's four tests passed, including all six
  permanent preparation/hook-loss negative controls.
- Permanent validator evidence covers all three non-finites under all five
  numeric keywords, finite rejection on both the JSON-only and extended paths,
  `oneOf`, `not`, `anyOf`, `allOf`, declared-number rejection, references and
  nested arrays. Prior declared-type/nullable, equality, tag-collision and
  older-dialect tests remain in place.

The known-bad production source is the validator from code PR #94 at
`2ed140396a956955588de4d9d70d8be45861d70d`, unchanged by merging RC002.
The earlier seventh declared-type mutation is historical evidence, not a
newly-executed mutation claimed by this pass. The six permanent fixture controls
and the new RC001 production RED/GREEN controls are freshly executed here.

### Gate results and publication

Final full gate results and exact candidate/publication state are recorded in
the completion addendum below. Rust remains a remediation candidate pending
Claude's independent targeted closure; RC001 is not self-declared closed.
No Rust/Python WP-13.2 implementation or later-layer work is authorized here.

### RC001 completion addendum

Fresh gates on the remediated tree:

- `cargo fmt --all -- --check`: PASS.
- `cargo clippy --workspace --all-targets --all-features -- -D warnings`: PASS.
- `RUSTDOCFLAGS="-D warnings" cargo doc --workspace --no-deps`: PASS.
- `cargo run -p xtask -- conformance verify`: PASS.
- Shared schema/manifest validation: 307 passed.
- Delta canonical target: 4 tests passed, 4 documents / 50 cases passed;
  six permanent negative controls killed.
- `cargo test --workspace --all-features --no-fail-fast --quiet`:
  **427 passed / 9 failed**, exit 1. The full regression gate is NOT green.

The failures are in unchanged execution tests: `execution_process` (2 Windows
sharing-violation errors at temporary-directory cleanup),
`execution_read_write_access` (2 ACL assertions returning success),
`execution_readability` (2 ACL assertions returning success), and
`execution_shell` (3 failures with WSL `E_ACCESSDENIED` output). The process
target also reproduced both failures in an independent targeted retry. Git
comparison against accepted main proves these tests and execution production
sources are unchanged; this is not a claim that the accepted baseline was
independently executed here. No unrelated execution patch or skipped test was
used to manufacture a passing gate. This environment cannot establish full
certification; the complete suite must be reproduced in a capable environment.

GitHub read access verified the accepted defaults and open candidate heads.
GitHub mutations are unavailable under this session's approval policy, and
terminal fetch fails connecting to `github.com:443`. Completion/push status and
exact local commit identities are therefore recorded separately in
`.tmp/rc001-remediation/HANDOFF.md`. Local-only commits are not remote-reachable
review candidates. RC001 awaits independent targeted closure; no certification,
issue-state transition, merge, or later work is claimed.
