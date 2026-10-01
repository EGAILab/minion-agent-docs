# EXEC-002-R1 Rust append completion remediation

Coordination: minion-agent#115, Rust finding EXEC-002-R1-RUST-APPEND.
Scope: implementation defect against the existing adopted Layer-12 EXEC-002
contract; no contract redesign, new operation or fsync guarantee.

## Baselines and authority

Code parent: `f150ca68fd1c9780093314543d290ae6877c87fb`.
Docs parent: `5722c31db8ec72b84cf4acf25bba25193610a388`.
Both current default-branch heads were independently confirmed through GitHub's
read API before isolated task worktrees were created. Shell fetch/push transport
is blocked; the authorized exact-object bundle fallback is used for publication.

Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`,
`packages/agent/src/harness/env/nodejs.ts:574–581`: await node:fs/promises appendFile
before returning success. Shared spec/execution.md §3.4 adopts create-or-append
and non-inspection of append's optional signal. Tokio 1.44.2's File::poll_write
schedules a blocking write before returning accepted byte count; poll_flush
joins that write and returns its I/O outcome. The implementation previously
awaited write_all but never joined the pending write.

Origin diagnosis: minion-agent#115 comment 5938178398, published verbatim from
Codex's independently reproduced O1 report. This defect is not attributed to
L05-D001, whose diff never touched the filesystem code.

## Narrow correction

Only LocalFileSystem::append_file changes in production:

```rust
file.write_all(content).await.map_err(map_fs_error)?;
file.flush().await.map_err(map_fs_error)
```

The existing FsError mapper handles both write and completion errors. No error
is suppressed, no signal is inspected, and parent creation/path handling/open
options are unchanged. Flush joins Tokio's pending operation; it does not request
sync_all or storage durability. Rust still accepts bytes, not Python text.
The parallel Python str-content remediation is outside this branch.

No manifest, normative spec, canonical data, shared schema, Python code, dependency
or Cargo.lock changes. No WP-13.2/D003 work.

## Permanent discrimination

`tests/execution_append_completion.rs` uses the real filesystem provider and a
supported current-thread Tokio runtime with one blocking worker. It holds that
worker using channels at each mkdir/open setup stage, then at the write stage.
This prevents fast setup tasks from collapsing polling stages. The real append
must remain pending while the actual write cannot run, then succeed with exact
bytes after worker release. Two tests cover no signal and a pre-aborted signal.
There is no mock writer, sleep/retry assertion, shadow operation or overridden
production result. Ten-second channel timeouts only guard setup/deadlock failures.
The held worker is released before the completion assertion even for a mutant,
so a failure cannot leave the runtime blocked during shutdown.

The real-source mutant replaces only the final flush expression with `Ok(())`.
Both unchanged witnesses must fail specifically at the early-completion assertion.
The candidate restores the join before all final gates and commit. The exact
candidate, mutation result and fresh gate counts are recorded below at handoff.

Code candidate: `ffa7eaca798be5a236a2d435f39271b961d7bb80`, branch
`remediate/exec002-r1-rust-append`, one commit directly above the accepted parent.
Only two code-repository files change: the provider implementation and the new
Rust integration test. No mutant remains.

Final-witness negative control: replacing only
`file.flush().await.map_err(map_fs_error)` with `Ok(())` yields **0 passed / 2
failed**, exit 101. Both failures are at the assertion
`append returned success before its blocking write could execute`.
The setup assertions, released worker and subsequent exact-byte read succeed;
this is not a deadlock, timeout or setup-error rejection. The final witness holds
the worker during setup as well as the write, avoiding a fast-open scheduling
assumption. The earlier exploratory version also killed the same mutant but is
not substituted for this final-version result.

Mutation command: `cargo +1.97.1 test -p minion-agent --all-features --test
execution_append_completion --offline --config <vendor-config.toml>`.
Logs retained in `.tmp/exec002-r1/mutant-final.log`; the fixed candidate's
unchanged tests run as part of `.tmp/exec002-r1/test-final.log`.

## Status

Fresh final gates at the exact code candidate (Rust **1.97.1**, selected shared
ICU4C **78.3** build; offline pinned Cargo vendor set, no new dependency):

| Gate | Result |
|---|---|
| cargo fmt --all -- --check | PASS |
| cargo clippy --workspace --all-targets --all-features -- -D warnings | PASS |
| cargo test --workspace --all-features --no-fail-fast | **450 passed / 6 failed** |
| RUSTDOCFLAGS=-D warnings cargo doc --workspace --no-deps | PASS |
| cargo run -p xtask -- conformance verify | PASS |
| shared schema + manifest pytest validation | **365 passed** |
| new controlled completion witnesses (included in full test gate) | **2 passed** |
| original cancellation_matches_the_operation_specific_contract | PASS |

The six failures are the same previously disclosed restricted-host tests:

```text
execution_process::explicit_termination_is_success_with_the_os_reported_exit_code
execution_process::spawn_signal_controls_pre_and_post_spawn_cancellation
execution_read_write_access::windows::deny_write_and_deny_read_acls_both_fail_combined_access
execution_read_write_access::windows::directory_probe_requires_add_file_but_not_delete_child
execution_readability::windows_deny_list_directory_acl_is_permission_denied
execution_readability::windows_deny_read_acl_is_not_mistaken_for_existence
```

No failures are hidden/skipped and no earlier unrestricted-host result is used
as this candidate's certification gate. Independently rerun the exact candidate
on the unrestricted host before closure. Existing LIBCMT linker warnings are
not new candidate warnings. Final logs: `.tmp/exec002-r1/test-final.log`,
`clippy.log`, `doc.log`, `verify.log`, `shared.log`. The earlier `test.log` build
overlapped a test-only witness hardening edit and is superseded by `test-final.log`;
it is not the final gate record.

The task worktrees are isolated and clean after commits. GitHub pushes remain
blocked at github.com:443, so verified bundles and the complete SHA-bound handoff
are provided in `.tmp/exec002-r1/HANDOFF.md`. They are LOCAL_ONLY until Claude
publishes and verifies the exact remote heads. No automatic issue transition
is claimed while transport remains blocked.

IMPLEMENTED CANDIDATE, independent closure review pending. No certification
claim is made until unrestricted-host full gates and review pass. Source and
test commits must be published and exact remote heads verified before #115's
Rust handoff is considered committed workflow state.
