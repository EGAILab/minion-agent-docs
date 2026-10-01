# WP-13.2 Rust: resume after certified L0506-D003

## Exact scope and provenance

Implementation candidate: code `9138a013708e18f48d2b41f1fd05c1130a3c4d69`.
The preserved code candidate `e96bdb647491dcc58b64d2cc66ab001a972f87fa`
was integrated with accepted main
`4a9f1d1557bb5775f4b648b873b732da7c9d409a` in merge
`f30d33a06ff494da2a4629cc829931430255b977`.
The preserved docs candidate `8d4755f952c516174c4ff57a334635374bc49367`
was integrated with accepted master
`7e741bd6823dad378cf6e70c4eebbc9afaf026ea` in merge
`7156e2d0fc964df2f90b2b093450002acc1a5163`.

GitHub's read-only API independently confirmed those accepted defaults,
draft PR #98/#207 heads, and issue #49's Rust-owned resume instruction.
Shell fetch remained blocked on github.com:443. Exact signed remote commit
objects were recovered from GitHub git/commits payloads, recomputed to their
declared hashes, and checked against available trees and parents before
integration. This is content-addressed remote evidence, not reconstruction
from a handoff's prose. Both merges were conflict-free.

Authority is pinned Pi `b7bb00b936dbe21b8e160b3e89efdec361846699`, the
merged WP-13.2 contract, certified EXEC-009, prepared-runtime and prepared-string
seams, and certified L0506-D003's native result vocabulary. The earlier C001
and C002 records remain historical; their lower-layer defects are resolved
by the independently certified deltas, not by a Rust-only contract amendment.

## Implementation boundaries

* Edit registers the certified **raw** prepare seam, not the JSON compatibility
  adapter. Arguments and edits-JSON decoding retain UTF-16 strings and keys.
* Matching, occurrence selection, fuzzy normalization, line-ending handling,
  and diff/patch construction operate on code units. Replacing one half of a
  surrogate pair does not silently replace the other half in memory.
* The additive pinned-ICU code-unit NFKC entry point uses the same verified
  ICU build and Unicode-16 filter. Existing scalar normalization delegates to
  that implementation; lone surrogates remain unchanged, while scalar runs
  normalize ordinarily.
* Replacement happens only at the file UTF-8 encoding boundary. Write reports
  content length in UTF-16 units. Edit diff/patch remain lossless typed
  `ResultValue` / `ResultString` values through the after-hook, execution-end,
  tool-result message and typed Session append/derive.
* The mutation queue, provider operations, cancellation contract and certified
  lower-layer filesystem production code are unchanged.

The implementation diff changes Rust plus exactly five manifest `rust:`
evidence fields (TOOL-029 through TOOL-033). It changes no Python production,
canonical expectations, normative rules or dispositions.

## Canonical adapters and discrimination

The complete builtin-mutation case adapter consumes all 15 case documents:
**417 cases**, including the previously excluded surrogate cases. Its
fixture-only YAML decoder retains quoted UTF-16 values and keys while leaving
scenario semantics to the real tools. Eleven queue documents run through the
real queue. Existing scalar convenience tests remain additional regressions,
not the claimed full-domain evidence.

The prepared-runtime edit gate contains **8 cases**; the prepared-string edit
gate contains **21 cases**, including actual file bytes. The separate C002
`gate-wp132-edit-result.json` case runs the real edit tool through a scripted
provider, AgentLoop, lifecycle events and typed Session. Its expected diff and
patch are compared at the hook, execution-end, message and Session boundaries.
A permanent lossy-details mutant preserves file bytes but must disagree at
all four boundaries. The existing **142-case D003 gate** is also retained.

The K1 witness uses four genuinely distinct raw object enumerations, observes
them at execution-start, and compares TOOL-029..033-owned outputs for real
write/edit success and errors, nested/JSON-string edits, cancellation and the
same-target queue. Its deliberate order-leaking after-hook is rejected. This
does not certify general JavaScript object enumeration in prepared maps or
close the separately governed K1 delta.

Queue quiescence controls retain the 10 ms, 500 ms and 10 s abort-listener
timer witnesses. No runner sleep is substituted for production completion.

## Fresh gate record

Rust toolchain: 1.97.1 x86_64-pc-windows-msvc. Offline Cargo uses the supplied
locked vendor set; no new dependency was added. ICU linkage and identity use
the pinned shared ICU4C 78.3 build. Commands run from the candidate Rust root:

* `cargo fmt --all -- --check`: PASS.
* `cargo clippy --workspace --all-targets --all-features -- -D warnings`: PASS.
* `RUSTDOCFLAGS="-D warnings" cargo doc --workspace --no-deps`: PASS.
* `cargo run -p xtask -- conformance verify`: PASS.
* Shared schema and manifest tests: **385 passed**, explicitly without the
  global Python coverage gate because this is a schema-only run. Manifest
  validation was rerun after the evidence-only update: **8 passed**.
* `cargo test --workspace --all-features --no-fail-fast`: **485 passed / 6
  failed / 0 ignored**, exit 101; 491 tests in total (doc-test suites contain
  zero tests). All WP-13.2 gates and permanent negative controls pass.

The six failures are:

```text
execution_process::explicit_termination_is_success_with_the_os_reported_exit_code
execution_process::spawn_signal_controls_pre_and_post_spawn_cancellation
execution_read_write_access::windows::deny_write_and_deny_read_acls_both_fail_combined_access
execution_read_write_access::windows::directory_probe_requires_add_file_but_not_delete_child
execution_readability::windows_deny_list_directory_acl_is_permission_denied
execution_readability::windows_deny_read_acl_is_not_mistaken_for_existence
```

The process failures are Windows OS error 32 while deleting process-test
directories. The four ACL witnesses receive Ok instead of an enforced deny.
These exact six failures were independently reproduced on accepted baseline
`708d93c1` during D003's implementation pass (13 passed / 6 failed over the
three affected binaries). This pass verifies their production and test source
is unchanged against accepted main `4a9f1d15`. This is a baseline/environment
diagnosis, **not a waiver or a green full gate**. Claude must rerun the exact
candidate on the unrestricted host before approval. Append-completion and
operation-specific filesystem cancellation regressions pass in this run.

The first attempted full test link encountered Windows LNK1104 while a focused
corpus binary was still running. That process finished successfully; the full
gate was rerun serially. Its failed link is not counted as a semantic test
result. All focused edit gates, full 417-case corpus, queue documents and three
K1 tests passed before the final full run.

## Handoff status

Rust WP-13.2 is implemented as a review candidate, **not independently
certified**. Cross-language WP-13.2 is **not closed**. Shell push remains
blocked; exact commits and verified bundles are supplied for Claude to publish
without rewriting, followed by unrestricted-host gates and independent
CLOSURE_REVIEW. Remote completion is not claimed for local candidate commits.
No subsequent work package or layer is started by this pass.
