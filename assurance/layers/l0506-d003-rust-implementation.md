# L0506-D003 Rust implementation candidate

Status: **CANDIDATE — independent CLOSURE_REVIEW pending**. This is not cross-language certification. Publication and unrestricted-host full-suite verification remain prerequisites to closure.

## Authority and baseline

- Coordination: minion-agent#112, standing Rust delegation #75; NEXT_OWNER Codex independently checked.
- Accepted code: `708d93c12fc17065960fba66f48c642026abf293` (merged #116).
- Accepted docs: `7d73072cf334498bea135b101a0d28b93e2f4ff2` (merged #216).
- Pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`, clean source tree.
- Contract authority: spec/tools.md **Tool-result runtime value domain**, spec/session.md carrier rules, AI-006 / TOOL-005 / TOOL-017 / MINION-002, approved D003 contract and six-carrier feasibility matrix.
- Code candidate: `5a66d58d9adc192a6ac8ecb2cb327c3d4471669b`, tree `0c5e5561862622f4a97b0f57e00d46206fc732e6`. The paired docs SHA is recorded in the bundle handoff, not self-referentially in this file.

The implementation was derived from the approved Pi/spec/canonical boundaries. It does not reopen WP-13.2, ADJ-2, K1, the raw argument number domain, or schema validation.

## Typed architecture and carriers

`llm/result_value.rs` introduces `ResultString`, `ResultNumber`, `ResultValue` and `ResultTextBlock`. `ResultString` reuses the certified `JsString` code-unit primitive and retains a scalar cache only when conversion is lossless. `ResultNumber` admits binary64 NaN, infinities and signed zero; **RawNumber remains NaN-free**. Recursive object keys are `ResultString`, not Rust `String`. BTreeMap ordering is implementation determinism only, not a new ECMAScript enumeration guarantee.

Assistant/user text, ordinary identifiers and unrelated vocabulary are unchanged. Existing scalar tool-result callers use explicit `.into()` conversions. There is no live tagged-JSON escape hatch or lossy fallback. `try_to_json` and Serde are explicitly fallible scalar/finite boundaries; they are not a certified persisted byte format, JSON.stringify projection or session storage mechanism.

| Carrier | Actual production ownership |
| --- | --- |
| AgentToolResult | Typed result content and recursive details directly from execute |
| AfterToolCallResult / after-hook | Same typed values; replacement merge preserves prior values for nullish overrides |
| Failure conversion | ToolCapabilityError retains UTF-16; after-hook error uses additive ListenerFailedUtf16 rather than Display/string round-trip |
| ToolExecutionEnd | The actual finalized typed result is dispatched |
| ToolResultMessage | Typed result text/details carried into the live message |
| Session append + derive_messages | Existing SessionField::Message stores/clones typed messages; no new Session authority or JSON encode/decode |

Rust has no Session-log-to-Agent-event replay API. The two Python replay-specific controls are therefore N/A, per the approved binding-conditional contract. Session derive_messages is exercised, not waived. Top-level null/undefined details remain outside this delta (ADJ-2); `with_details(null)` retains Pi's nullish override fallback. Nested null, false and empty values remain distinct.

## Real composed-stack canonical evidence

`tests/tool_result_domain_conformance.rs` drives a registered tool through ScriptedAdapter, LlmService, AgentLoop.prompt, the real after-hook and lifecycle seam, and the actual Session. It observes the after-hook, execution-end event, live ToolResultMessage and Session-derived message independently. It does not append a synthetic message or use a copied Python finalizer.

All **142 gate-L0506-D003 cases** pass: 80 string, 17 key, 27 number, 7 scalar-details, 8 hook and 3 failure cases. The seventh document's one `gate-wp132-edit-result` case is intentionally excluded; it belongs to Rust WP-13.2's later implementation/review.

Fixture decoding is confined to the canonical boundary. Number tokens are preflight-checked as a named non-finite/signed-zero token or an exact finite binary64 ECMAScript spelling. Expected observations are never computed through the runtime fixture decoder. `$keys` observations are compared as unordered key sets (on both sides), consistent with K1's exclusion. Non-scalar code units and special numbers are observed directly, not via Serde.

`tests/tool_result_values.rs` separately proves typed Session append/derivation, strict JSON refusal for lone-surrogate text/keys and non-finite numbers, finite JSON compatibility, sign-preserving negative zero and unchanged RawNumber NaN refusal. A permanent canonical preflight test refuses noncanonical/overflowing number literals.

## Independent pinned-Pi replay

The accepted `harness/run.sh`, authority script, make_cases.py and make_scenarios.py were executed unchanged in offline host mode. Node was **v22.15.1**; the pinned Pi tree was clean and its recorded source hashes checked. TypeBox **1.3.7** and diff **8.0.4** archives were checked against the **pinned commit's package-lock.json**, not a mutable checkout lockfile.

- TypeBox SHA-512 SRI: `sha512-meKuifc33Pccx0O6PdIzYMq3Og8zvP4TIi/a+Bw3AEMZMxOD0+RHGQvpglEe6Zdy3wZ8nqn/j95h8LUZLk/6Hg==`.
- diff SHA-512 SRI: `sha512-DPi0FmjiSU5EvQV0++GFDOJ9ASQUVFh5kD+OzOnYdi7n3Wpm9hWWGfB/O2blfHcMVTL5WkQXSnRiK9makhrcnw==`.
- Fresh 146-result authority SHA-256: `97fa2ae9af4582533914c6a7b0007eab3edb85ac6f141a0c50dda537ba0212df`, byte-identical to the accepted artifact.
- All seven regenerated scenarios matched their **committed Git blobs byte-for-byte**. Working-tree CRLF conversion is not used as the comparison authority.

The 146 authority results include the three undefined-detail cases and top-level null, which are excluded from the adopted delta; 143 scenarios include the separately gated real-edit case. None are silently counted as this delta's 142 cases.

## Real-seam negative controls

The reversible source-patch generator is `data/l0506-d003-rust/mutants.py`. It emits apply_patch/restore patch pairs and never writes source itself. Supply the candidate's absolute `crates/minion-agent/src` path as argument 2. Apply one patch, run `cargo test -p minion-agent --all-features --test tool_result_domain_conformance`, then apply its restore before the next control. These are temporary faults at real production boundaries, not patched expected outputs or observers. The helper is never shipped in production.

| Mode | Fault | Fresh discrimination |
| --- | --- | --- |
| return | Lossy executed result before after-hook | 66 cases fail: hook 64, execution_end 2 |
| drop | Drop message details entirely | 142 cases fail at message |
| hook | Lossy after-hook input only | 64 cases fail at hook |
| end | Lossy execution-end payload only | 69 cases fail at execution_end |
| message | Lossy message strings/keys | 69 cases fail at message |
| text | Lossy message text only | 17 cases fail at message |
| nested | Lossy details string values | 45 cases fail at message |
| keys | Lossy details keys only | 14 cases fail at message |
| numbers | File-style number projection in message details | 17 cases fail at message |
| strict-log | Strict JSON encode at actual typed append | Canonical target fails on non-scalar JSON storage |
| log | Lossy typed Session append | 69 cases fail at session |
| log-numbers | File-style number projection at typed append | 17 cases fail at session |
| derive | Lossy derive_messages output | 69 cases fail at session |

All thirteen controls were run, killed, restored, and the unmutated canonical target passed again. The `nested` Rust control includes top-level details strings too; the `drop` control removes details rather than replacing them with `{}`. These deliberately broader faults explain differences from Python control counts; Python counts are not claimed as Rust results. An initial malformed hook patch failed compilation and was **not counted**; the corrected executable hook mutant produced the 64 failures above.

## Gates and regression safety

Fresh gates at the code candidate above:

| Gate | Result |
| --- | --- |
| cargo fmt --all -- --check | PASS |
| cargo clippy --workspace --all-targets --all-features -- -D warnings | PASS |
| cargo test --workspace --all-features --no-fail-fast -j 2 | 454 passed / 6 failed / 0 ignored; exit 101 (six baseline/environment failures below) |
| RUSTDOCFLAGS=-D warnings cargo doc --workspace --no-deps | PASS |
| cargo run -p xtask -- conformance verify | PASS |
| Shared schema + manifest validation | 385 passed; 116/116 unique rows |
| Pinned-Pi authority + regenerated canonical blobs | Byte-identical |
| Real-seam negative controls | 13/13 killed and restored |

Toolchain **Rust 1.97.1**, offline vendor set, pinned ICU4C **78.3** build and identity file; no new crates or Cargo.lock changes. Full Rust gates include the existing lower-layer canonicals and builtin image corpus. The four new Rust tests pass (one aggregate exercising 142 cases, one preflight test and two direct value tests). The Windows test linker emits existing `LNK4098` mixed-CRT warnings; these do not occur as Rust/clippy lint failures. Full-suite status is deliberately not reported as green.

Only four manifest `rust:` evidence fields change (AI-006, TOOL-005, TOOL-017, MINION-002). No rule, disposition, spec, scenario, schema, Python production file or expected outcome changes. Mechanical Rust caller conversions preserve the old scalar cases.

### Sandbox failures independently reproduced on accepted baseline

The full candidate run encounters six unchanged Windows execution failures. The exact accepted code baseline was freshly tested in a separate worktree with the same toolchain/runtime: **13 passed / 6 failed** across the three affected binaries, reproducing all six names and symptoms.

1. `execution_process::explicit_termination_is_success_with_the_os_reported_exit_code` — remove_dir_all sees Windows OS error 32 (sharing violation).
2. `execution_process::spawn_signal_controls_pre_and_post_spawn_cancellation` — same child-process cleanup sharing violation.
3. `execution_read_write_access::windows::deny_write_and_deny_read_acls_both_fail_combined_access` — ACL denial is not enforced; operation returns Ok.
4. `execution_read_write_access::windows::directory_probe_requires_add_file_but_not_delete_child` — same ACL enforcement symptom.
5. `execution_readability::windows_deny_list_directory_acl_is_permission_denied` — same ACL enforcement symptom.
6. `execution_readability::windows_deny_read_acl_is_not_mistaken_for_existence` — same ACL enforcement symptom.

These execution sources/tests are unchanged by D003. This is evidence of baseline/environment failure, **not a green full suite** and not a waiver. Claude must rerun the full suite on the unrestricted host at the exact published head and resolve any candidate-specific failure before certification.

## Handoff boundary

Code branch `layer/l0506-d003-rust`; docs branch `assurance/l0506-d003-rust`. Exact commits, parent ancestry, bundle heads/integrity hashes, remote-sync status, commands and fresh gate counts are in `.tmp/l0506-d003-rust/HANDOFF.md`. If publication is blocked, the candidate is LOCAL_ONLY until Claude verifies and pushes those exact bundles.

After remote publication: issue #112 -> CLOSURE_REVIEW, NEXT_OWNER Claude. Rust D003 is a review candidate, not CERTIFIED. No automatic Rust WP-13.2 resume, no Layer 14 work.
