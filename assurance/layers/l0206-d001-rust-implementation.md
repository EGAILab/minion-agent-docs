# L0206-D001 / K1 — Rust implementation candidate

## Authority and status

Issue `minion-agent#100`, handoff comment `5968225019`, and the Owner's 2026-10-03 go-ahead authorize this Rust pass. Starting code/main: `d81edb0ae38f925f26b4413f2d21585f6b79b6c9`; starting docs/master: `8521106de8ebf4f562487aa0c4fd33452741066e`. Pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`, Node 22.15.1, TypeBox 1.3.7. Authority is spec/llm.md's tool-argument key-order contract, including every-observer access, the A–F model and container provenance, plus the spec/tools.md scope note. Rust has no Python Q1/Q2 native-alias exception.

Code candidate: `b350f2078db6db8ca0ba7c3f13318d6fc4a28b08`, `minion-agent#134`, branch `layer/l0206-d001-rust`. This is implementation evidence, not independent certification. Python's accepted certification is unchanged; Rust remains a candidate; cross-language closure awaits the independent reviewer.

## Representation and real seams

`ArgumentObject<K,V>` preserves ordinary-key insertion history and keeps canonical ASCII array-index keys 0 through 4294967294 first, ascending. Recognition checks length before conversion and rejects noncanonical, Unicode, leading-zero and out-of-range spellings. Replacement retains position; delete/reinsert changes ordinary position. No mutable underlying-map escape exists.

`ArgumentObjectRef` and `ArgumentArray` are shared `Arc<RwLock<...>>` containers. Reads return scalar clones/shared child handles; writes normalize within typed storage. Cloning a value retains container identity, including attachment through arrays and replacement values. Locks are released before callbacks or awaits. Borrowed indexing was replaced by safe get/set/handle APIs, without unsafe code or leaked allocations.

Raw and prepared argument values use these containers. Raw-to-prepared conversion memoizes both arrays and objects. Prepared structured cloning isolates the cloned graph while preserving its internal aliases and both cross-frontier traversal orders. Preparation/validation uses that clone boundary; hook mutations and Proceed replacement continue through the shared handles. Start/update event listeners, live delivery, execute and typed session persistence use the same representation, not observer-time sorting.

The pre-existing runtime-schema boundary remains owned and finite: construction, cloning and public inspection take isolated structured snapshots. A permanent witness verifies that external constructor aliases and inspection mutations cannot introduce non-finite schema values. This is regression protection, not an expansion of L05 schema semantics.

serde_json's `preserve_order` feature prevents re-sorting explicit ordered projections and raw serialization. Cargo.lock adds an edge to already-pinned indexmap; no package version/checksum changes. Tool-result storage is unchanged.

## Canonical and binding evidence

`tests/key_order_conformance.rs` runs all 49 shared cases through the real registry, preparation, validation, hooks, execute, event bus/live callbacks and typed session append/derive. It interprets mutation programs using retained shared handles, not duplicate-path simulation. It observes native iteration and serialized JSON without compensating sorting. The edit preparation discriminator uses the real edit schema and preparation shim, with the scenario's probe executor; this is not a filesystem behavior claim.

`tests/argument_graph_identity.rs` covers retained child attachment, array mutation APIs, alias-preserving isolated clone, raw-to-prepared aliases, real shim/two-hook/execute composition, and array-root lifecycle event/live delivery. `tests/argument_object_order.rs` covers storage/serialization; primitive units cover recognition/order.

The pre-existing WP-13.2 independence witness now has two distinct ordinary-key orders, not four: canonicalizing index keys collapses the four variants into two. Owned-output assertions and the leaky negative control remain; the change is documented in that test.

## Permanent source mutants

`scripts/k1-negative-controls.ps1` creates a detached scratch worktree, applies each source mutant separately, requires executable assertion failures (compilation failures do not count), logs the exact candidate and restores source in finally. It clears the tested crate's Cargo artifacts before each mutant and after restoration.

Final replay at `ac0a71d6f65d4e36479f87f913cac6c796ed3d53`: all ten mutants compile and are killed. Logs and machine-readable results are retained in `.tmp/k1-rust/negative-controls-final/`; the committed script reproduces them.

The subsequent `b350f207` correction moves the prepared evidence note from the preceding manifest row to TOOL-003. The complete Rust tree is identical to the mutant-tested tree; only evidence metadata changed.

| Source mutant | Failed assertions/tests |
| --- | ---: |
| insertion without index-first | 11 |
| sorted map | 6 |
| leading-zero index recognition | 3 |
| 4294967295 index recognition | 3 |
| long-decimal conversion | 3 |
| construction-only ordering | 9 |
| sorted prepared value | 2 |
| sorted hook replacement | 1 |
| detached/sorted event argument projection | 2 |
| sorted session serialization | 2 |

A first full regression attempt exposed cross-worktree Cargo cache contamination: a restored source reused the last mutant's serialization binary. That interrupted run is NOT passing evidence. The harness was corrected to force tested-crate rebuilds; the final controls and full gates rebuild the candidate. Original candidate sources were not patched by the mutant script.

## Fresh gates

Final rebuilt run: **517 passed / 0 failed**, summed from the 78 workspace test-result lines (including zero-test/doc-test targets). All 49 K1 cases pass within the canonical integration test; the retained lower-layer canonical suites and WP-13.2 independence control pass.

| Gate | Fresh result |
| --- | --- |
| `cargo fmt --all -- --check` | PASS |
| `cargo clippy --workspace --all-targets --all-features --offline -- -D warnings` | PASS |
| `cargo test --workspace --all-features --offline --no-fail-fast --quiet` | 517 passed, 0 failed |
| `RUSTDOCFLAGS=-D warnings cargo doc --workspace --no-deps --offline` | PASS |
| `cargo run -p xtask --offline -- conformance verify` | PASS |
| shared schema and manifest tests | 404 passed |
| permanent source mutants | 10/10 killed |

Runs use Rust/cargo 1.97.1 and the verified shared ICU4C 78.3 build/identity, with `RUST_ICU_MAJOR_VERSION_NUMBER=78`, the pinned native library/DLL paths and `MINION_AGENT_ICU_IDENTITY`. Existing MSVC LIBCMT linker warnings are disclosed separately from clean strict clippy/rustdoc results. The complete rebuilt test log is `.tmp/k1-rust/final-full-tests-rebuilt.log`.

The full run started at `ac0a71d6`; its complete Rust tree is byte-identical to final candidate `b350f207`. The 404 shared checks were rerun after the manifest correction. A semantic manifest comparison confirms that only the `rust` fields of AI-003 and TOOL-003 differ from the accepted baseline. No gate result is inferred from the earlier interrupted runs.

## Scope and handoff boundary

No Python, normative contract, canonical corpus, schema or expected output changes. Manifest changes are restricted to AI-003 and TOOL-003 Rust evidence pointers, explicitly identified as candidate evidence. Exclusions remain #129 shallow-copy value isolation, prepare nonmutation mapping, K1-F2 diagnostics, tool-result details order and provider projection.

Next step after publication: independent closure review by Claude. No merge or certification is performed by this implementation pass.
