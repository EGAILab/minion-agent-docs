# L0506-D002 — Rust implementation candidate

Independent Rust owner: Codex. Date: 2026-10-01. Coordination: minion-agent#99.

## Status and exact scope

Implementation candidate, **not certification or cross-language closure**. Code head:
`c1aff9b655aaf311c075b1fc3a3503ff55d7f276`, branch `layer/l0506-d002-rust`.
Its two task commits are the previously disclosed WIP
`a2a3eea41efdb787a863e05d3a17b5e50f2d1ba2` followed by this completion commit.
No WIP evidence is retrospectively represented as passing.

Accepted starting code: `c9b6e910d310ad0982ec0bf0ace6b5671554ae24`.
Accepted starting docs: `2ef3828b0b1706a60016f68913634e08ea35ad1b`.
Both contain the merged approved L0506-D002 contract. The current defaults were
independently rechecked through GitHub's read API: code
`ef7fe40c4bcca3f0c0ce441181a7a217aa96c21d`, docs
`c624330b05422d0c60fa8ff313df851c6e6ae825`. The later L05-D001 contract merge
does not widen this delta. These later commit objects were unavailable locally;
this candidate does **not** claim to contain them. Integration onto newer defaults
needs the ordinary ancestry/conflict check, preserving both additive contracts.

Issue #99 was re-fetched: OPEN, RUST_IMPLEMENTATION, NEXT_OWNER Codex. Git fetch
fails connecting to github.com:443; reads through the GitHub connector work.
Local commits/bundles are an explicitly authorized publishing alternative,
not proof of remote reachability. Until the exact commits are published and
the issue transition verifies, remote state remains unchanged.

Scope: prepared **instance** strings AND keys, scalar-schema validation,
preparation/pre-hook/Proceed replacement/execution. Raw ToolCall.arguments is
L0206-D002; non-scalar schema literals are L05-D001; ECMAScript object enumeration
is K1/L0206-D001. The 21 real-edit cases belong to WP-13.2 and are not counted as
D002 certification. No WP-13.2 implementation resumed here.

## Authority and architecture

Pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`.
Read the adopted tool preparation/validation/execution boundaries and the
merged spec/tools.md prepared-runtime string section, TOOL-041, scenario schema
and eight documents before implementing. The independent prior offline Node
v22.15.1 / pinned TypeBox 1.3.7 authority replay produced the recorded 198-case
output and canonical documents byte-identically. This is prior reviewer-executed
evidence, not a claim of a new authority replay in this implementation pass.

`PreparedString` owns exact UTF-16 units with an optional **lossless** scalar
view. Equality and key comparison use units; high/low surrogates and U+FFFD
remain distinct. A valid pair equals its corresponding scalar representation.
Scalar indexing converts the lookup key rather than claiming an invalid
Borrow<str> ordering relationship. `PreparedValue` retains its existing authority
and now carries this type for values and object keys. Existing typed preparation,
hook, Proceed replacement and execute paths consume that same value.

`try_to_json` refuses any non-scalar string/key or non-finite number, with an
explicit error; it never replaces or discards a live value. `to_utf8_lossy` is an
explicit later-boundary helper, not automatic runtime normalization. The current
TOOL-003 diagnostic mapping remains unchanged and does not serialize the
non-scalar instance through serde_json.

The certified jsonschema engine continues to own schema traversal, composition
and references. Its existing private numeric carrier is extended with
collision-free string tags; schema and ordinary runtime literals/keys are excluded
from the tag namespace. Tags exist only inside validation. Length keywords count
decoded code points (each unpaired unit counts one). Pattern and patternProperties
use pinned regress 0.11.1's Unicode-mode UTF-16 matcher over the original units.
Key matching and additionalProperties dispatch retain real schema validation;
there is no runner-owned validation algorithm. Scalar-only JSON instances retain
the existing fast path. Numeric keyword applicability from certified L0506-D001
is retained, including oneOf/not verdicts.

Additional units cover surrogate Unicode classes, key patterns, propertyNames,
root and nested-ID references, collision exclusion, integer-valued float length
constraints and invalid-schema classification. These are implementation tests,
not new shared contract rules.

## Dependency provenance

Rust/Cargo: 1.97.1. The supplied offline vendor directory contains 325 packages.
Independently checked the 324 accepted Cargo.lock package/checksum pins, the
resolved union and every listed extracted-file hash. No prior package pin changes.
The new regress 0.11.1 pin was independently confirmed against the official
crates.io index (`re/gr/regress`):

`158a764437582235e3501f683b93a0a6f8d825d04a789dbe5ed30b8799b8908a`.

Cargo's resolved lock adds regress and enables already-pinned hashbrown's
allocator dependencies. Source declarations pin `=0.11.1`, feature `utf16`.
The extracted source directory is supplier-provided. Matching the package field
and extracted hashes establishes lock/metadata/internal consistency; it does
**not**, by itself, independently authenticate archive bytes when the checksum
manifest and files arrive together. No such stronger verification is claimed.
Independent closure can reacquire the crate against this registry/lock pin.

All Cargo runs use `--offline --config <review-dir>/vendor-config.toml`.
ICU uses the existing verified ICU4C 78.3 build/identity and native library paths;
no system ICU substitution. Existing Windows linker LNK4098 LIBCMT warnings
remain disclosed, not suppressed by changes to the code.

## Real-seam evidence and controls

`tests/prepared_string_conformance.rs` validates the shared schema, performs the
language-neutral pointer preflight, discovers all documents and selects the
L0506-D002 gate dynamically. It constructs fixture values, registers a real tool
and pre-hook in the real Runtime, and invokes execute_tool_calls. Hook and execute
observations are independent; expected observations come from scenario data.
Original raw arguments remain unchanged. No tool/validation semantics are
implemented in the runner. The WP-13.2 document is schema-checked but not executed.

Fresh result: **181/181 delta cases**, two Rust test functions pass. Eight permanent
fixture controls are killed: rejection, early replacement/lossy conversion,
strict UTF-8 rejection, valid-pair corruption, lone-low-only corruption, key-only
replacement, hook-only replacement, execute-only replacement. The replacement
control covers both normalization and lossy-conversion outcomes.

Two additional single-field **production-source** mutations were independently
executed and restored: forcing JSON-only conversion at the pre-hook handoff,
and forcing it at the execute handoff. Each made the real canonical gate fail at
`string/lone-high-start` (0 passed / 1 failed); restored source passed 181/181.
execution.rs has zero final diff. No mutation is retained in production.

## Fresh gates and unresolved broad-gate limitations

- cargo fmt --all -- --check: PASS.
- cargo clippy --workspace --all-targets --all-features -- -D warnings: PASS.
- RUSTDOCFLAGS=-D warnings cargo doc --workspace --no-deps: PASS.
- cargo run -p xtask -- conformance verify: PASS.
- Focused `--lib prepared`: **15 passed**, zero failed.
- Final prepared-string runner, including all eight controls: **2 passed**, zero failed.
- Shared schema/manifest pytest, explicit candidate PYTHONPATH: **349 passed**, zero failed.
- Complete workspace/all-features/no-fail-fast suite with Git Bash first on PATH:
  **438 passed / 6 failed**, exit 101. This is **NOT** a green full gate.

The six failures are in unchanged existing execution surfaces:

1. execution_process::explicit_termination_is_success_with_the_os_reported_exit_code,
   line 109, and spawn_signal_controls_pre_and_post_spawn_cancellation, line 178:
   fixture remove_dir_all fails with OS code 32 after behavior assertions.
2. execution_read_write_access::windows::deny_write_and_deny_read_acls_both_fail_combined_access,
   line 242, and directory_probe_requires_add_file_but_not_delete_child, line 269:
   expected permission-denied result is Ok instead.
3. execution_readability::windows_deny_read_acl_is_not_mistaken_for_existence,
   line 208, and windows_deny_list_directory_acl_is_permission_denied, line 227:
   expected permission-denied result is Ok instead.

The earlier run with System32 WSL bash first reported 435 passed / 9 failed;
selecting Git Bash cleared all three shell failures, with its focused suite
8/8 green and full-suite shell target also 8/8 green. No test was skipped/modified.
The execution production sources and these six test sources have empty diffs
against accepted code c9b6e910. The two subprocess cleanup failures were also
independently reproduced on the earlier accepted baseline during WP-13.2 work;
that historical record remains separate. A new baseline compilation attempt here
was interrupted before tests and supplies **no** fresh baseline verdict. Empty
diffs are not represented as execution of that baseline or as a waiver of failures.

These full-gate limitations must be resolved or explicitly adjudicated before
certification. No 100% Rust coverage claim, automatic waiver, merge authorization,
WP132-RUST-C001 closure, or cross-language closure is asserted.

## Next action

Publish exact commits/bundles and verify remote heads/ancestry. Then the independent
Python/shared owner reviews this Rust candidate and re-runs full gates on its
review host, explicitly settling the broad-gate failures before certification.
Use CLOSURE_REVIEW only after the remote candidate and complete coordination state
are verified. Keep WP-13.2 paused pending D002 cross-language certification.
