# L05-D001 Rust implementation candidate

## Exact scope and provenance

Coordination: minion-agent#104. This implements the approved runtime-validation
**schema** string domain (TOOL-016 / TOOL-003), not provider wire encoding.
Code candidate: `83c0ce26d0656a5ef70b1c08642fe92027349b50`, branch
`layer/l05-d001-rust`.

Accepted code parent: `e83ba6aa81500cc3791fc1c02c3a6b64800b100c`.
Accepted docs parent: `e6bcd2ccbeb86340888049b7e6e0a522c27ad5a6`.
Approved contract: code #106 / docs #211, merged as `ef7fe40c` / `c624330b`.
Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`.
The accepted parent commits and trees were independently verified against
GitHub; local root worktrees and unrelated changes were not reset.

There is a genuine implementation/evidence dependency on **certified**
L0206-D002 (#110, merge `2ec46f4be68d8fcae3f51dfbed8b44149925c907`).
The canonical tool has no prepare callback: its raw arguments must preserve
lone-surrogate strings/keys before runtime validation. The candidate therefore
starts from merged main, not that delta's unmerged candidate. Separate semantic
ownership remains unchanged; no raw-domain production code is modified here.

## Architecture and compatibility

`RuntimeSchemaObject` owns the single authoritative schema in the certified
`PreparedValue` / `PreparedString` lossless UTF-16 vocabulary. Object-root and
finite-number restrictions remain; only the schema string/key domain widens.
The legacy scalar `ToolDefinition::new` converts losslessly into this authority;
`new_with_runtime_schema` exposes the new domain. Layer 06 reads it directly.

The existing extended validator is reused. Collision-free private tags preserve
identity for schema literals, property names and instance strings/keys.
Regex sources restore original code units; genuine unpaired units use Unicode
escapes, while valid pairs remain code points. Both pattern and patternProperties
execute Unicode-mode UTF-16 searches. Literal const/enum data is not treated as
schema syntax. Local references are rewritten to the corresponding private key
carriers; direct unit evidence covers valid, missing and literal-reference cases.
No carrier reaches preparation callbacks, hooks, execution or provider delivery.

Provider JSON remains the existing scalar-only vocabulary. `ToolDefinition::schema`
and registry `schemas` now return an explicit `Result`; a non-scalar runtime
schema cannot silently become replacement characters or be omitted. Scalar callers
remain lossless. Agent request construction propagates a typed projection error.
This is a disclosed public Rust signature adjustment, not a claim to certify
non-scalar provider wire transport. That transport remains outside this delta.

There are no Python, canonical expectation, shared schema, disposition, normative
spec or dependency changes. Manifest changes are only Rust evidence pointers in
TOOL-001 (execution seam) and TOOL-016. Historical contract snapshots saying
NOT_IMPLEMENTED are not rewritten; this candidate supersedes implementation
availability only, subject to closure review.

## Independent authority and discrimination

Read source first: Pi `packages/agent/src/validation.ts`, pinned TypeBox behavior,
then spec/tools.md's runtime-validation schema domain, manifest, scenario schema,
all ten scenario documents, and certified Rust validator/tool seams.

The accepted committed generators and authority script were executed unchanged
under host Node **v22.15.1**, with a clean pinned Pi tree and TypeBox **1.3.7**
archive verified against Pi's lockfile SHA-512 SRI. The 810-row authority output
reproduced byte-identically, SHA-256
`ad7976793de2e9f508e53b0e16e06d15be149fc9a8d895965761b84e1d0cf244`.
All ten regenerated canonical documents also matched byte-for-byte.

The thin Rust runner decodes the transport grammar, registers a real tool with
**no prepare callback**, executes through Layer 06, and checks rejection versus
one actual execution. It does not implement validation or derive expectations
from production output. **810/810 cases pass**.

Five real-source mutants are killed by that unchanged runner: reject legal
non-scalar schemas; UCS-2 pattern search (7 mismatches); UCS-2 pattern-property
search (7); schema replacement (92); instance-key replacement (56).
The compiler-flag-only attempt was non-discriminating and is explicitly not
counted. Exact mutation descriptions and all mismatching case IDs are preserved
in [the evidence directory](data/l05-d001-rust/README.md).
Every mutant was restored before final gates and commit; the final worktree is clean.

## Fresh gates, 2026-10-02

Toolchain **1.97.1**, offline vendored Cargo dependencies, selected shared ICU4C
78.3 build. No new crate dependency or lockfile change.

| Gate | Fresh result |
|---|---|
| cargo fmt --all -- --check | PASS |
| cargo clippy --workspace --all-targets --all-features -- -D warnings | PASS |
| cargo test --workspace --all-features --no-fail-fast | **448 passed, 6 failed** |
| RUSTDOCFLAGS=-D warnings cargo doc --workspace --no-deps | PASS |
| cargo run -p xtask -- conformance verify | PASS |
| shared schema + manifest pytest validation | **365 passed** |
| targeted schema-domain / public API tests | **3 passed**, including 810 cases |
| local-reference compatibility unit | **1 passed** |

The six full-suite failures are the known restricted-host process/Windows ACL
tests, not hidden or skipped:

- execution_process::explicit_termination_is_success_with_the_os_reported_exit_code
- execution_process::spawn_signal_controls_pre_and_post_spawn_cancellation
- execution_read_write_access::windows::deny_write_and_deny_read_acls_both_fail_combined_access
- execution_read_write_access::windows::directory_probe_requires_add_file_but_not_delete_child
- execution_readability::windows_deny_list_directory_acl_is_permission_denied
- execution_readability::windows_deny_read_acl_is_not_mistaken_for_existence

Logs are in `.tmp/l05-d001-rust/` (test-final, clippy-final, doc-final,
verify-final, shared-final, focused-final, refs2 and individual mutant logs).
An unrestricted-host fresh full gate is required before certification; previous
host results do not count as this candidate's gate. Pre-existing linker LIBCMT
warnings do not make the successful strict clippy/rustdoc gates failures.

## Handoff and status

GitHub transport is blocked in this session. Exact commits and verified bundles
are supplied through the owner-approved fallback in `.tmp/l05-d001-rust/HANDOFF.md`.
Until Claude publishes these exact objects and independently verifies remote
reachability, they are **LOCAL_ONLY / REMOTE_SYNC_BLOCKED**; this document does
not assert a completed GitHub handoff or mutate coordination state by implication.

After publication: NEXT_OWNER Claude, CLOSURE_REVIEW of exact code/docs heads,
with unrestricted-host gates and independent source/authority/mutant verification.
Rust L05-D001: IMPLEMENTED CANDIDATE, NOT YET CERTIFIED.
Cross-language L05-D001: NOT CLOSED. WP-13.2 remains BLOCKED_FOR_OWNER and untouched.

Retrospective observation for closure: representation feasibility must include
the schema *and* unprepared raw instance path. A preparation callback in a runner
would have concealed the actual cross-delta representation dependency.
