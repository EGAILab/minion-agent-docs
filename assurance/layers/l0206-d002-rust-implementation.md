# L0206-D002 — Rust raw tool-call argument domain candidate

Coordination: minion-agent#103. Date: 2026-10-02 (Australia/Sydney).
Status: implementation candidate; **NOT CERTIFIED**, independent CLOSURE_REVIEW pending.

## Exact state and authority

- Code baseline: remote main `db1b5bdbc1652f8c77fb2535dad944807260da8c`.
- Docs baseline: remote master `306109bea44e2a56f753f94c67291aa5ae9c3943`.
- Code candidate: `c2ea8777dc7594dd34e79c9dc4858f0c191733e2`, branch `layer/l0206-d002-rust`.
- Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`, clean checkout.
- Approved contract: spec/llm.md “Raw tool-call argument value domain”, AI-003 / MINION-002,
  conformance/agent/raw-arguments, CE-L0206-D002-01 revision 2.
- Issue #103 independently re-fetched: OPEN, RUST_IMPLEMENTATION, NEXT_OWNER Codex,
  existing owner governance and approved merged contract present. Both exact default refs
  independently re-verified through GitHub's read-only API when terminal fetch failed.

Pi was inspected before implementation: ai/src/types.ts ToolCall; ai/src/utils/json-parse.ts
parseJsonWithRepair/parseStreamingJson; agent/src/agent-loop.ts prepareToolCallArguments,
prepareToolCall, executePreparedToolCall and start/update argument payloads.
JSON.parse produces binary64 numbers and arbitrary UTF-16 strings; the loop carries these
values, not a serialization projection. The approved contract's live-session rule is a
Minion mapping; Pi's separately disclosed persisted JSON-line projection is not applied here.

## Architecture and boundary mapping

| Boundary | Rust mechanism / fresh evidence |
|---|---|
| Raw decoding | RawValue::decode reuses the certified JavaScript parser; decode_utf16 also accepts literal non-scalar UTF-16 JSON string text |
| ToolCall / AssistantMessage construction | ToolCall::new_raw owns RawValue without validation or normalization; existing JSON-object convenience constructor retained |
| Strings and keys | RawString retains UTF-16 units; RawValue::Object uses unique RawString keys in IndexMap; no K1 enumeration claim |
| Numbers | Private RawNumber binary64 leaf; signed-zero bit identity, infinities; NaN rejected as outside this raw domain |
| Session append | SessionField::Message stores the typed Message directly in the existing event log, no serde_json conversion |
| Session replay | Typed payload returned from the same log; generic JSON event metadata and JSON-compatible message intake remain supported |
| Fork / compaction / reset | Existing session derivation, sequence and locking authorities reused; focused raw-value regression witnesses |
| Start / update arguments | ToolExecutionStart/ToolExecutionUpdate carry RawValue, including the actual update event and async callback delivery |
| No-prepare hook / execute | Lossless RawValue -> certified PreparedValue conversion; no U+FFFD, null or zero replacement |
| Preparation input | with_prepare_raw_arguments accepts the whole unchanged raw domain and returns certified PreparedValue |
| Existing JSON callback convenience APIs | Explicit fallible compatibility adapters; incapable JSON input is not silently repaired. Whole-domain callbacks use the raw API |

The existing auth JavaScript decoder/renderer was moved intact into a neutral javascript module.
The old auth API re-exports it; only UTF-16 access/construction and standard string conversion/hash
support were added. There is no second JSON parser and no lower layer dependency on auth.
Auth regression tests remain in the complete workspace suite.

The live log is NOT a byte form. RawValue::try_to_json / serde serialization are explicit,
fallible interoperability projections: lone surrogates and infinities cannot silently become
replacement text/null. SessionField::Message is a public typed payload, not a hidden sidecar or
escaped-key carrier. JSON event metadata is a distinct variant. Append sequence allocation is
shared by both typed messages and existing metadata; no parallel Session authority was introduced.
Future persisted-byte semantics remain outside this delta.

## Thin canonical adapter

tests/raw_arguments_conformance.rs consumes and schema-validates every current raw-arguments
document: **38 cases** (22 strings, 15 numbers, one key case). It:

1. preflights named or exact ECMAScript finite number tokens;
2. constructs the typed fixture and independently decodes provider_text;
3. constructs a real ToolCall/AssistantMessage, appends it to the real Session and replays it;
4. registers a real no-prepare tool and real hook/event listeners, then executes the real batch;
5. observes hook, execute, start, update event and async update delivery, each exactly once;
6. compares with an expectation read directly from scenario text, never through the fixture decoder.

Observation represents strings/keys as code units and numbers by ECMAScript spelling, including
signed zero and infinities. Binary64 is structural in Rust: there is no arbitrary-precision runtime
integer leaf that an observer could silently round. N3's Python int/digit-limit exception hazards
are therefore unrepresentable in this type, rather than recreated in the Rust runner.
Key lists are sorted only for membership/value comparison; K1's production enumeration remains
separately owned. No runner implements session behavior, execution, updates or validation.

## Discrimination

Nine actual single-point **production-source** mutants were independently installed, executed
against the canonical test, and restored. Every mutant compiled and made the test semantically
RED, not merely fail compilation. The restored candidate's canonical test is GREEN.

| Mutant | Detected boundary |
|---|---|
| Decoder replaces non-scalar string with U+FFFD | independent provider-text decode comparison |
| Decoder replaces non-scalar key with U+FFFD | key case decode comparison |
| Strict JSON conversion at session append | real append cannot admit raw key/value domain |
| Replay loses arguments | replayed ToolCall differs |
| Start arguments alone lost | start observation differs |
| Update event alone lost | event observation differs; callback left correct |
| Async update delivery alone lost | callback observation differs; event left correct |
| Execute input alone lost | execute observation differs |
| Hook input lost | hook observation differs |

Exact source replacements and actual failure output are preserved in
data/l0206-d002-rust/mutation-results-final.json and mutation-key.json.
mutation-results.json preserves the first run before the equivalent typed-map/append-helper
refinement; it is not substituted for the later rerun. No mutant remains in the candidate.

Five focused language tests additionally cover decoder invalid tokens/NaN rejection, binary64
rounding, literal UTF-16 input text, unique keys, typed log/fork/compaction/reset, explicit
non-JSON projection failure, signed-zero identity, JSON-compatible shape and raw preparation input.
Supplementary literal-text.cjs runs on verified Node v22.15.1 and yields
`[55296,55357,56832,56320]`, `rejected`, `rejected`, matching the Rust witness.

## Fresh gates

Rust 1.97.1, offline locked vendor source; same verified pinned ICU4C 78.3 environment as the
accepted baseline. Cargo.lock and dependency versions unchanged. No new dependency bytes needed.

| Command | Result |
|---|---|
| cargo fmt --all -- --check | PASS |
| cargo clippy --workspace --all-targets --all-features -- -D warnings | PASS |
| cargo test --workspace --all-features --no-fail-fast | **444 passed / 6 failed**, 450 total; failures below |
| focused raw_arguments + raw_arguments_conformance | **6 passed / 0 failed**, including all 38 canonical cases |
| RUSTDOCFLAGS=-D warnings cargo doc --workspace --no-deps | PASS |
| cargo run -p xtask -- conformance verify | PASS (layout verification, not a substitute for running canonical tests) |
| shared schema + manifest pytest, focused --no-cov | **365 passed / 0 failed** |
| git diff --check | PASS |

All Cargo commands use --offline and the supplied verified vendor-config.toml.
The initial focused Python run also passed its tests but exited nonzero on the unrelated
whole-package 100% coverage threshold; the explicit focused --no-cov rerun above is the shared
schema/manifest gate, not a claim of a fresh full Python coverage run. No Python code changed.
MSVC reports the same LNK4098 static/dynamic runtime warning seen in the accepted baseline.

The complete Rust run's six failures are unchanged execution/process/Windows ACL tests:

- execution_process::explicit_termination_is_success_with_the_os_reported_exit_code
- execution_process::spawn_signal_controls_pre_and_post_spawn_cancellation
- execution_read_write_access::windows::deny_write_and_deny_read_acls_both_fail_combined_access
- execution_read_write_access::windows::directory_probe_requires_add_file_but_not_delete_child
- execution_readability::windows_deny_list_directory_acl_is_permission_denied
- execution_readability::windows_deny_read_acl_is_not_mistaken_for_existence

No execution implementation or test was modified. These sandbox failures match the six failures
previously independently cleared by the unrestricted-host D002 closure run. They are NOT waived
here: receiving review MUST rerun the complete gates on the unrestricted host at this exact new
candidate before certification. This record does not describe the complete suite as green.

## Scope and next state

No Python implementation, normative spec, canonical scenario, expectation, schema, manifest
disposition, dependency lock or governance decision changed. Manifest edits are Rust evidence
pointers and Rust candidate status only. Prepared/schema/result domains remain separately owned.

WP-13.2 (#49) remains BLOCKED_FOR_OWNER on WP132-RUST-C002-Q001; its result details types were not
changed or certified here. L05-D001 and K1 are not implemented by this pass. Layer 14 not started.

**Verdict:** Rust L0206-D002 IMPLEMENTED CANDIDATE / NOT CERTIFIED. L0506-D002-Q001's raw-domain
obligation is supplied for independent closure, not self-declared CLOSED. Cross-language NOT CLOSED.

Terminal fetch/push are blocked by github.com:443. Exact commits and verified bundles are supplied
through the owner-authorized publication fallback. Local commits are not remote completion.
After the receiver publishes and verifies both exact commits, the next action is independent
CLOSURE_REVIEW by Claude, including an unrestricted-host complete gate run. Stop here.
