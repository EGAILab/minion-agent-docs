# L08-D002 Rust request-header implementation

Status: IMPLEMENTATION CANDIDATE; independent Rust closure review pending.
Rust NOT CERTIFIED; cross-language L08-D002 NOT CLOSED.

## Authority and baseline

Coordination: minion-agent#171, handoff issuecomment-6073247180. Owner decisions:
#166 issuecomment-6068630928 and #171 issuecomment-6071887505. Approved shared
contract: `spec/agent.md`, Layer 08, "Request header per provider request";
AG-025 and the eight `conformance/agent/request-header-*.yaml` documents.
Starting merged code: `3de4b75d0119b6c413dae651a3cba039873756c7`;
docs: `52945167d56732ff592ff745951642d42a5100fd`.
Implementation commit: `689e2e1ba39a642c18f748bff532df674281a647`.

Pinned Pi `b7bb00b936dbe21b8e160b3e89efdec361846699`,
`packages/agent/src/agent-loop.ts::streamAssistantResponse`, supplies the
provider-context transformation/conversion path. Header publication is the
Owner-authorized MINION-003 architectural mapping, not a Pi artifact parity
claim. Session header/artifact APIs and historical logs are unchanged.

## Implementation and ownership

`agent_loop/driver.rs::run_provider_turn_with_decision` resolves the request's
system text and derives one ordered owned schema vector before transformation.
It publishes through the existing `Session::record_header` with exactly one
`system_base` component and the model identifier (not a provider-qualified
name). The header receives a clone of the captured values; the request consumes
the original vector. Schema failure publishes nothing. Transformation, eager
unknown-model failure, provider failure and abort keep the published header.

`ToolSchema` owns its strings, nested `JsonSchemaObject` and sampling metadata.
`ToolDefinition::schema()` uses the certified fallible provider-JSON projection;
these values have no application-shared mutable aliases. Consequently Rust
already provides the independent value snapshot: there is no Python-style
application parameter alias to manufacture or freeze. The Layer-05 tool API,
run-start shallow definition snapshot and later-context replacement are unchanged.

The L08-D001 #169 worktree/branch was not edited. Its assembler integration must
be rebased after this delta's independent approval, merge and certification.
No Python source, normative contract, shared expectation or Session format is
changed. AG-025 changes only its Rust evidence pointer.

## Canonical adapter and binding witnesses

`tests/agent_loop_conformance.rs` drives all eight documents, also as individually
named tests. It accepts the certified override/transform listener vocabulary,
descriptions and sampling metadata. It observes actual Session event order,
reconstructs real headers, and serializes the schemas captured by the actual
scripted provider adapter. No expectation is used to generate an observation.
Existing full agent-loop scenarios continue through the same adapter.

Additional real-driver witnesses:

- fallible non-scalar schema projection happens before header publication and
  before the transform listener; failure follows the existing run-failure path;
- pre-step rejection constructs no provider request or header;
- a transform listener sees the published header before aborting; it remains
  exactly once, with monotonically incremented Session sequence numbers, while
  surface derivation still contains only messages.

The complete Session suites cover artifact/header round-trip, log-only
classification, fork, reset and compaction, including 22 canonical Session cases.

## Discriminating controls

Committed recipe: `minion-agent-rust/scripts/request-header-negative-controls.py`.
Run in a disposable candidate worktree, from `minion-agent-rust`, using the
pinned Rust/ICU environment:

```sh
python scripts/request-header-negative-controls.py --tree . --logs <scratch>
```

Each mutant gets its own unmutated green baseline, with its exact intended test
selected and passing. A kill requires the named test to fail with its assertion
signature; compiler/infrastructure failures and unrelated failures are INVALID.
Anchors must match once and the original source is restored in `finally`.
Rust has no pending pytest xfail marker or planned-fix overlay.

| Mutation | Intended witness |
| --- | --- |
| no header | single request |
| duplicate header | single request |
| publish after transform | first-request transform failure |
| publish first request only | multi-request order |
| wrong model | single request |
| wrong component | single request |
| ignore literal override | literal override |
| omit header schemas | full-schema identity |
| reverse header schemas | full-schema identity |
| omit provider schemas | full-schema identity |
| ignore schema projection failure | schema-failure binding witness |

## Fresh gates

Fresh G3 at the implementation commit above:

| Gate | Windows | Linux |
| --- | --- | --- |
| formatting | PASS | PASS |
| strict Clippy, workspace/all targets/all features | PASS | PASS |
| workspace/all-feature unit and integration tests | 617 passed, 0 failed | 617 passed, 0 failed, 1 ignored |
| doctests | 4 passed | 4 passed |
| strict rustdoc | PASS | PASS |
| xtask conformance verify | PASS | PASS |
| request-header controls | 11/11 intended-witness kills | 11/11 intended-witness kills |

Linux's pre-existing ignored recursive-remove permission witness was then run
separately as UID/GID 65534: **1 passed**, without changing the candidate.
All eight request-header documents passed through the real adapter on both hosts.
The complete suite includes the Owner-required Session and lower-layer regressions.
Shared manifest/schema validation: **856 passed**; docs process suite: **363 passed**.
Windows' existing MSVC LNK4098 dependency-link warnings are not new failures;
all gate commands returned zero. No gate or mutant infrastructure failure is
reported as a successful control.

Candidate remains NOT CERTIFIED. Exact paired remote heads are recorded in #171;
the next step is Claude's independent Rust closure review, not a merge.

### Reproduction environment

Rust is the repository-pinned 1.97.1 toolchain; Node is v22.15.1. Both platforms
use the verified shared ICU4C 78.3 build, its `pinned-icu-identity.txt`, and the
official search-engine artifacts through `MINION_SEARCH_ENGINE_ARTIFACTS`.
`CARGO_BUILD_JOBS=2`, `CARGO_INCREMENTAL=0`, `CARGO_PROFILE_DEV_DEBUG=0` and
`CARGO_PROFILE_TEST_DEBUG=0` limit disk use, without disabling debug assertions.
There is one reused target per platform, not a target per control or worktree.

Windows adds the pinned ICU `icu/lib64` to `RUSTFLAGS=-L native=<lib64>` and
`RUSTDOCFLAGS=-D warnings -L native=<lib64>`, and its `icu/bin64` to PATH.
Linux uses `rust:1.97.1-trixie` at
`sha256:b1b3c9c0d921d7fa0a6d1f9ec7e4eab87f8c8ec97644c3d791450f131dec813f`,
copies the source into the container filesystem, and strips CR from copied shell
scripts. It mounts the existing `icu783-linux` volume, adds `/icu/install/lib`
to both native link flags and `LD_LIBRARY_PATH`, and puts Node on PATH.
Dependencies come from the existing offline vendor set with an isolated
`CARGO_HOME`, source replacement and `CARGO_NET_OFFLINE=true`; Cargo validates
the committed lockfile checksums. No dependency or lockfile changes are needed.

Run, sequentially, from `minion-agent-rust`:

```sh
cargo fmt --all -- --check
cargo clippy --locked --workspace --all-targets --all-features -- -D warnings
cargo test --locked --workspace --all-features
cargo doc --locked --workspace --no-deps
cargo run --locked -p xtask -- conformance verify
python scripts/request-header-negative-controls.py --tree . --logs <scratch>
```

The negative controls restore the original driver even on failure. None of the
mutant sources is part of the candidate commit. Full regressions include the
certified Session projection/fork/compaction suites and all Layer-08 scenarios.
