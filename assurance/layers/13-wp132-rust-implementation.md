# WP-13.2 Rust implementation candidate

This is Rust-side implementation evidence for `minion-agent#49`, not independent
cross-language closure approval. No later work package is started by this record.

## Authority and starting state

- Accepted code baseline: `53290de4e66ab415fd2fe5537ac2a6e6d4c61cdd`.
- Accepted docs baseline: `fba5a6f3f9570015731564123b29b6730ce24c9e`.
- Pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`.
- Independently fetched issue #49 says `RUST_IMPLEMENTATION`, `NEXT_OWNER: Codex`.
  Its next action explicitly authorizes a local bundle handoff when pushes fail.
- Source read: pinned `core/tools/{write,edit,edit-diff,file-mutation-queue,path-utils}.ts`
  and `utils/text.ts`, then accepted `spec/tools.md` WP-13.2, manifest, schemas and
  canonical fixtures. Python production implementation was not the implementation oracle.
- The line-diff search and patch projection were derived from jsdiff 8.0.4's
  `src/diff/{base,line}.ts` and `src/patch/create.ts`, not another diff engine.
  Its BSD-3-Clause notice is retained in `minion-agent-rust/THIRD-PARTY-NOTICES.md`.

Production changes are confined to Rust. The only shared-file changes are five
`rust:` evidence pointers (TOOL-029..033); no rules, dispositions, expected
results, Python files, or process files are changed.

## Ownership and architecture

| Surface | Rust owner |
| --- | --- |
| Write | `tools/builtin/write.rs`, `create_write_tool` |
| Edit execution | `tools/builtin/edit.rs`, `create_edit_tool` |
| Preparation | `edit_prepare.rs`, certified ECMAScript JSON parser + `PreparedValue` |
| Matching and touched-line preservation | `edit_apply.rs` |
| Unicode-16 fuzzy view | `edit_text.rs` + isolated pinned-ICU crate |
| Exact jsdiff search/display/patch | `edit_diff.rs` |
| Registration and per-target queue | `mutation_queue.rs` |

The typed factories return real Layer-05 `ToolDefinition`s. Layer-06 owns
preparation, validation, hooks, and result/error settlement. Edit consumes the
certified EXEC-009 `check_read_write` operation; its disclosed third-party
fallback uses EXEC-008 and does not pretend to be equivalent to EXEC-009.

Registration links synchronously before the detached worker is spawned. A
process-wide completion chain serializes key derivation and tail linkage in
invocation order; independent provider/target chains serialize actual mutation.
Provider identity is the retained filesystem Arc's data address; retaining the
Arc prevents address reuse while an entry exists. Canonical keys use the
approved fallback set, not Layer-12 `resolve()`.

No map mutex spans a filesystem await. Completion notification uses a
level-triggered atomic latch with notification registration before the check.
RAII drops release registration and per-key entries. The detached worker owns
its entry until its in-flight filesystem operation settles. There is no abort
listener/race in the production write/edit path; filesystem calls receive no
signal. A caller dropping its future therefore cannot prematurely release the
mutation lock.

Fuzzy normalization verifies the existing pinned ICU4C 78.3 build and uses an
ICU `[:age=16.0:]` filtered NFKC normalizer. Unsafe FFI remains in the already
isolated pinned-ICU crate; core Rust remains unsafe-free. Strings for one edit
are normalized as a batch under one freshly verified artifact identity, with
no persistent verification cache. The fuzzy view is idempotent and may be
reused within that transaction. Quote/dash/space folding and ECMAScript
trimEnd are explicit, not Rust-native whitespace approximations.

The diff's display/patch base is the original LF-normalized file, including
original whitespace, not the fuzzy replacement-search base. The authority
corpus caught this distinction during development; the implementation was
corrected directly against pinned Pi.

## Canonical and language evidence

`tests/builtin_mutation_corpus.rs` constructs fresh local filesystem fixtures,
registers the real write/edit tools, and executes the eight generated corpus
documents through Layer 06. It compares error/success, text, details, and final
bytes. `tests/builtin_mutation_conformance.rs` does the same for the seven
hand-authored case documents and eleven queue documents, using a thin scripted
filesystem wrapper. The wrapper implements only provider answers, recording,
gates, and signal injection; it does not implement queue or edit semantics.

Discovery: **26 documents**, **417 cases**, **11 queue scenarios**. Rust's
already-certified outer string domain cannot receive the three explicitly
flagged lone-surrogate argument cases. They are rejected at the boundary,
separately disclosed, and **not counted as successful semantic executions**.
The reachable case inventory is 372 generated + 42 hand-authored = **414**.
Valid astral scalar strings are accepted and counted as UTF-16 units normally.

`tests/prepared_runtime_edit_conformance.rs` runs all **8** gate-WP-13.2 cases
through the real edit definition and pre-execute hook. It verifies Infinity,
negative Infinity, signed zero, large-integer rounding, provider result text,
actual edited bytes, and unchanged raw execution-start arguments.

Additional tests cover preparation, matching, exact diff/patch projection,
Unicode-16 and whitespace boundaries, direct write behavior, and completion
chain FIFO/release/provider independence. No canonical expected result is
modified to accommodate Rust.

### Scheduler protocol and negative controls

The queue adapter uses a paused Tokio current-thread runtime. Quiescence sleeps
through a **60-second virtual horizon**: Tokio drains runnable/blocking work
before automatically advancing to each next timer. This is not a fixed
wall-clock window or a fixed scheduler-turn count. All calls are polled into
their actual execution before the next call is started.

Permanent negative controls wrap real write execution with an intentionally
incorrect early abort-result race. All three poll intervals (**10 ms, 500 ms,
10 s**) violate the canonical `write answer before result A` ordering and are
rejected. Separate timer tests establish that each timer actually fires within
quiescence. Mutant behavior lives only in the test adapter; no production
configuration enables it.

## Gate results

Code candidate: `b059ea4c4e0fff64b804ed76ae41161201a33029`.
The final `cargo test --workspace --all-features --offline --no-fail-fast`
completed with **450 passed / 9 failed**, exit 101. Aggregate unit/integration
test counts are distinct from the case counts within the canonical adapters.
Doc tests discovered zero cases. The final run passed all new WP-13.2 test
targets, including the complete 26-document inventory and the 8-case edit gate.

| Gate | Fresh result |
| --- | --- |
| `cargo fmt --all -- --check` | PASS |
| `cargo clippy --workspace --all-targets --all-features --offline -- -D warnings` | PASS |
| workspace tests, all features, no-fail-fast | FAIL: 450 passed / 9 failed |
| `RUSTDOCFLAGS=-D warnings cargo doc --workspace --no-deps --offline` | PASS |
| `cargo run -p xtask --offline -- conformance verify` | PASS (layout verification; actual scenario execution is separately tested) |
| Python shared schema + manifest validation | PASS: 307 tests |

This is a **partial implementation, BLOCKED / NOT CERTIFIED**, not a closure
candidate. The newly discovered contract defect below independently blocks it,
regardless of disposition of the environment-sensitive regression failures.

### WP132-RUST-C001 — prepared UTF-16 string domain

Classification: **CONTRACT_ASSURANCE_DEFECT**; implementation-discovered
lower-layer representation gap. No shared semantic repair was attempted.

The accepted spec's String semantics and its three flagged surrogate cases
disclose a Layer-02/05 outer argument-decoding hazard. They do not settle this
distinct reachable preparation path:

```json
{"path":"f","edits":"[{\"oldText\":\"a\",\"newText\":\"\\ud800\"}]"}
```

Every character in the outer JSON and its decoded `edits` string is an ordinary
scalar. Rust's certified outer decoder accepts it. Pinned `prepareEditArguments`
then performs `JSON.parse` and creates a string containing UTF-16 code unit
0xD800. Pi accepts that string as `newText`; Node UTF-8 encoding writes U+FFFD.
The existing certified Rust `PreparedValue::String(String)` cannot hold it.
The partial candidate's conversion currently returns a capability error instead.
That error is **not** certified parity and cannot be disguised as an outer
argument rejection or counted as a conforming semantic execution.

Independent reproduction used the exact `isSingleEditInput` and
`prepareEditArguments` functions extracted from pinned `edit.ts`, with Node
22.15.1's type stripping removing only erased TypeScript annotations. Output:
`outerArgumentIsScalar=true`, `preparedCodeUnit=55296`, encoded bytes `efbfbd`.
A standalone Rust probe linked to the committed candidate confirmed outer
acceptance and the preparation capability error. Source probes are preserved
in `.tmp/wp132-rust/prepared-surrogate-{pi.mjs,rust.rs}` for replay. Pinned Pi
HEAD was independently verified as `b7bb00b936dbe21b8e160b3e89efdec361846699`.

Required next action: the shared owner must characterize and settle the prepared
string/key domain and required lower-layer delta, including nested JSON parsing,
before Rust implementation resumes. Preserve existing certified raw argument
semantics; do not silently replace surrogates, use a Rust-only escape convention,
or declare all such inputs unreachable. Include a permanent real-edit witness
and appropriate prepared-value/diagnostic coverage. A governance-approved
divergence, if selected instead of parity, must be explicit. No such choice is
made by this artifact.

### Independently reproduced baseline exceptions

The full workspace run reached `execution_process.rs` and failed two tests at
**temporary-directory cleanup**, after their subprocess assertions:

- `explicit_termination_is_success_with_the_os_reported_exit_code`, line 109;
- `spawn_signal_controls_pre_and_post_spawn_cancellation`, line 178.

Both `std::fs::remove_dir_all(root).unwrap()` calls received Windows OS error
32, "The process cannot access the file because it is being used by another
process." A serial candidate rerun reproduced both failures. A separately
checked-out accepted baseline at `53290de4e66ab415fd2fe5537ac2a6e6d4c61cdd`
also reproduced **the same two failures**, with 4 passed / 2 failed.
The test source and production subprocess source are unchanged by WP-13.2.

The completed no-fail-fast run additionally failed seven unchanged tests:

- `execution_read_write_access`: `windows::deny_write_and_deny_read_acls_both_fail_combined_access`,
  `windows::directory_probe_requires_add_file_but_not_delete_child`;
- `execution_readability`: `windows_deny_list_directory_acl_is_permission_denied`,
  `windows_deny_read_acl_is_not_mistaken_for_existence`;
- `execution_shell`: `shell_accumulates_streams_invokes_callbacks_and_preserves_nonzero_exit`,
  `runtime_timeout_and_signal_are_distinct`, `shell_cwd_uses_the_filesystem_lexical_normalization_rule`.

ACL probes unexpectedly returned `Ok(())`; shell output reported
`Bash/Service/CreateInstance/E_ACCESSDENIED`. These seven failures are recorded
as environment-sensitive, **not independently baseline-reproduced** in this
pass. Their test and execution-production files have an empty diff from the
accepted baseline. The full log preserves exact assertion sites and values;
unchanged source alone is not claimed as proof of a passing baseline gate.

These are disclosed regression-gate obstacles, not successful tests
and not silently waived. The Rust candidate is **not certified** until the
normal workflow resolves/accepts the gate disposition. No Layer-12 behavior
or unrelated test was changed to conceal them. Logs are preserved with the
handoff (`baseline-execution-process.log`, `cargo-test-complete.log`).

An intermediate baseline comparison shared a Cargo target directory and
invalidated the candidate's cached pinned-ICU dependency. The resulting
missing-symbol compile attempt is not treated as source evidence: the
pinned-ICU package's build artifacts were cleared and the candidate rebuilt
before the final run. Reproduction should use separate target directories
for distinct worktrees.

## Boundaries and handoff

- EXEC-001..009 and the certified L0506-D001 representation/validation/hooks
  are reused, not reimplemented or semantically changed.
- No WP-13.3, shell/subprocess mutation tool, Layer 14, or process-convergence
  implementation is included.
- Python/shared WP-13.2 approval is established by the merged baselines.
- Rust candidate requires the shared owner's independent exact-SHA closure
  review after publication. Cross-language WP-13.2 remains **NOT CLOSED**.
- Terminal GitHub fetch/push access was unavailable; the owner-approved
  verified-bundle publication path is used. A local commit is not represented
  as a remotely reachable PR or a completed coordination transition.

## Resume after L0506-D002 certification: output-domain blocker C002

The preceding partial-pass state and counts are historical, not new gates.
L0506-D002 is independently closure-reviewed and merged (code ac661221,
docs 2d2ba5fc); C001's prepared-string representation is resolved. On this
resume, Codex independently verified #49 RUST_IMPLEMENTATION / NEXT_OWNER
Codex and preserved draft #98 b059ea4c / #207 f1fa6b47. Accepted current
defaults are code `db1b5bdbc1652f8c77fb2535dad944807260da8c` and docs
`306109bea44e2a56f753f94c67291aa5ae9c3943`.

Terminal fetch remains blocked. The read-only GitHub git/commits API supplied
the exact signed commit payloads; their complete trees already existed locally
from the status-authoring commits. Tree hashes, parents and recomputed commit
hashes were verified exactly before importing those objects and merging them
into the existing WIP branches. No baseline was reconstructed from chat prose.
Both merges were clean. No new production implementation was applied before
the transitive audit exposed the boundary below.

### WP132-RUST-C002 — CONTRACT_ASSURANCE_DEFECT — blocking

**Rule:** TOOL-030/031 returns pinned Pi's exact `details.diff` and
`details.patch`. Replacing an unpaired surrogate at the file UTF-8 boundary
does not normalize the in-memory result strings. D002 certifies prepared
arguments, not a widened tool-result/details domain.

**Content-addressed source:** [edit.ts execute](https://github.com/earendil-works/pi/blob/b7bb00b936dbe21b8e160b3e89efdec361846699/packages/coding-agent/src/core/tools/edit.ts)
and [edit-diff.ts generateDiffString / generateUnifiedPatch](https://github.com/earendil-works/pi/blob/b7bb00b936dbe21b8e160b3e89efdec361846699/packages/coding-agent/src/core/tools/edit-diff.ts).
The probe uses their exact functions (only TypeScript erasure), Node 22.15.1
and diff 8.0.4 bytes independently verified against pinned Pi's committed
lockfile SHA-512. Complete actual Pi checkout cleanliness is checked.

**Minimal setup:** existing f.txt bytes `61 0a` (`a\n`), scalar outer arguments
with edits JSON string `[{"oldText":"a","newText":"\\ud800"}]`.

**Expected / independently executed Pi observation:** successful edit; prepared
newText units `[55296]`; file bytes `efbfbd0a`; result:

```json
{"diff":"-1 a\n+1 \ud800","firstChangedLine":1,"patch":"--- f.txt\n+++ f.txt\n@@ -1,1 +1,1 @@\n-a\n+\ud800\n"}
```

Neither result string contains U+FFFD. The escaping above is JSON display,
not six literal characters in Pi's runtime string.

**Certified Rust boundary:** `AgentToolResult.details: serde_json::Value`
(tools/definition.rs), with JSON String(String); result finalization passes
these details to ToolResultMessage without a UTF-16 result vocabulary. The
locked serde_json rejects the exact result (`unexpected end of hex escape`)
while U+FFFD and an escaped valid pair controls pass. PreparedString can now
hold the argument, but cannot be inserted losslessly into this result field.
The preserved edit engine also uses native String internally: an early lossy
conversion would merely hide the output defect, not resolve it.

**Discrimination:** the 21 prepared-string edit gate cases assert hook units,
success text and file bytes, not result diff/patch units. A tool replacing
newText early with U+FFFD could satisfy those output checks but violate exact
TOOL-030/031 result semantics. A runner must not manufacture an escaped result
string, drop details or bless that premature replacement.

**Fresh probes:** exact pinned-Pi probe passes; locked Rust representation
probe **2 passed / 0 failed** (one precise refusal witness plus scalar controls).
Sources are preserved in `data/wp132-result-domain-c002/`. No full Cargo gates
were run on this blocked resume; prior counts are not recycled as new evidence.

**Required next step:** shared/lower-layer owner independently characterizes
the result/details string and key domain and its reachable consumers/projections,
including BMP, valid pair, lone high/low, positional variants, returned diff and
patch, and any error-message path that can carry the same values. Scope and
authorize the minimal lower-layer delta or obtain explicit divergence governance;
do not silently broaden D002 or the raw/schema deltas. Existing prepared-domain
certification remains valid. No output mutation or new semantics implemented.

Rust WP-13.2 remains BLOCKED / NOT CERTIFIED; cross-language NOT CLOSED.
Return C002 for contract resolution, not CLOSURE_REVIEW certification. Subsequent
raw/schema implementation queue entries were not started during this pass.
