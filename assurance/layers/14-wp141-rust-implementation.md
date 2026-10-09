# WP-14.1 — Rust implementation candidate

Status: implementation candidate; independent Rust closure review pending.
Coordination: minion-agent#158. This record does not certify the candidate.
Code candidate: `ba6c2a022e017b4d2520f5c537fedb2221c10ef9`.

## Authority and provenance

The approved shared/Python milestones are code `97ec5687b01b176f309475c5a1b4a23bdee57e38`
and docs `6ec91692343898d095fbc19b506d94d2a0f7142e`. The task branches start from
remote-reachable code `db63adcff1f3bc65edd7c8f03e5ae5b7ddb54eb9` and docs
`31847c606c78119d44d3dd7fd5133014293776ac`, which include those milestones.
The handoff is docs #263 at `3e92d61f4e0ebb534e592a1fb9c8b44e2757efb0`.

Behavioral authority is pinned Pi `b7bb00b936dbe21b8e160b3e89efdec361846699`,
`packages/agent/src/harness/skills.ts` and its record vocabulary; the approved
`spec/harness.md` WP-14.1 section governs the Minion mappings and departures.
Pinned dependency behavior is yaml@2.9.0 and ignore@7.0.5 / Node v22.15.1.
Python production code was not used as an implementation oracle.

## Rust mechanism

- `skills` exports writable typed records and discovery over the certified
  `FileSystem` trait. Names, paths and diagnostic interpolation retain UTF-16
  through the existing `FsPath` carrier. File text and subset-decoded scalar
  strings remain Rust `String`. Explicit JSON serialization remains fallible
  for non-scalar filesystem strings; discovery itself does not project them.
- Directory traversal uses explicit frames, drains the child before advancing
  its parent, and preserves ordered roots and addressed paths. No traversal
  depth limit, interpreter adjustment or recursive async walk is introduced.
- The private subset reader implements DIV-004 and the exact DIV-007 nesting
  bound: root mapping depth 1, each collection another level, maximum 64.
  There is no public YAML API or alternative full-YAML engine.
- The private ignore matcher ports the pinned regex transformations over UTF-16,
  including Annex B escape handling and non-Unicode Canonicalize. The upstream
  MIT notice accompanies the port. Parent evaluation is iterative; successful
  pattern additions invalidate the cache. DIV-006 rejects each invalid rule
  eagerly, preserving the remaining ordered rules. DIV-005 skips only the
  entry whose relative path is invalid and emits its diagnostic.
- The subordinate pinned-ICU binding supplies a fixed, internal raw comparison
  transaction. It is not re-exported as a public application comparator and has
  no caller-selected profile. ICU 78.3 identity is checked at transaction entry;
  raw en-001 tertiary comparison is stable with normalization ON, numeric OFF
  and case-first OFF. Existing ls lowercased comparison is unchanged. No ICU
  pointer or internal lock is held across a filesystem await.
- Sourced loaders retain opaque sources through `Arc`, pass owned writable
  skills to the mapper exactly once, and propagate application mapping errors.

## Evidence layout

`tests/skill_discovery.rs` materializes the shared fixtures, invokes the real
loader through `LocalFileSystem`, and compares observations without reproducing
discovery semantics. The corpus contains 96 documents, including 10 explicitly
POSIX-only rows. Cycle c01 uses only the approved code/path outcome shape.

Private unit tests consume the language-neutral frontmatter corpus (8,000
documents) and ignore corpus (6,000 pattern sets / 18,000 observations). These
JSON fixtures reside under the Python test-data directory by historical layout;
they are shared authority-derived data, not Python behavior.

Additional binding witnesses cover writable mapper records/source identity,
mapping-error propagation, filesystem-origin UTF-16 interpolation, stable raw
collation, deep acyclic directory traversal with a leaf ignore file and later
root, a 3,000-segment matcher parent chain, cache invalidation, collection-depth
boundaries and invalid relative-path diagnostics.

`scripts/wp141_negative_controls.py` mutates only an isolated scratch copy.
Each control requires a green baseline, an exact source-anchor match, a compiled
test failure and its named intended witness. Compile/infrastructure failures
and surviving mutants are INVALID, never kills. Selected canonical controls
also require the selected scenario's trace. The script rebuilds the package
for a new scratch root so a cached compile-time fixture path cannot mask evidence.

During control preparation, Kelvin sign alone did not discriminate removal of
the non-ASCII-to-ASCII Canonicalize guard: Kelvin uppercases to itself. The
permanent witness also uses long-s, whose uppercase is ASCII S; pinned Node
confirms `/s/i` rejects it while `/s/iu` accepts it. The initial surviving
control was not counted as a kill.

## Scope and stop condition

No Python or normative contract changes. Manifest changes are Rust evidence
pointers only. DIV-004..DIV-007 and PP-14-1/3/8 are consumed, not redefined.
Existing Layer-12 contracts, #69/#133 exclusions and WP-14.2 prompt assembly
are not reopened. L08-D001's separate owner decision is not a dependency.

Code PR #173 and assurance PR #267 are the paired candidates. Rust remains an
implementation candidate until Claude's
independent exact-SHA closure review. Cross-language WP-14.1 is not closed.

## Fresh validation and reproducibility

Windows control preparation reached 17/17 valid intended-witness kills. The
first full Windows build exhausted E: while writing PDBs (`LNK1318` / OS error
112); it did not run tests and is not semantic gate evidence. Regenerable
package build outputs were removed with `cargo clean -p minion-agent` (20.3 GiB).
The full sequential rerun uses two build jobs, no incremental metadata and
dev/test debug-symbol metadata disabled. Debug assertions and optimization
levels remain their normal test defaults. Linux will use the same resource
settings. No source, corpus, dependency artifact or contract was removed.

Windows unit/integration coverage is 606 passed, 0 failed, 0 ignored across 83
test binaries. The first complete test command reached doctests but two could
not link because its `RUSTDOCFLAGS` omitted the native ICU search path. With
that environment corrected, the complete doctest gate passed 4/4. Thus the
fresh unit/integration run and complete doctest retry cover the workspace; the
initial complete command is not reported as an uninterrupted exit-zero run.
Formatting, strict workspace/all-target/all-feature Clippy, warning-strict
rustdoc and `xtask conformance verify` passed. Canonical discovery covers 86
passing documents and 10 explicit POSIX-only exclusions on Windows. The final
Windows control batch has 17/17 valid intended-witness kills, zero invalid or
surviving controls; earlier infrastructure-invalid batches are not evidence.

Shared manifest/schema validation passed 846 tests, and docs process tests
passed 363 tests. These commands used E: scratch and temporary paths.

Linux initially used `rust:1.97.1-bookworm`, whose older libc/libstdc++ could not
link the existing pinned ICU artifact (`GLIBC_2.38` / `CXXABI_1.3.15` symbols).
That pre-test environment failure is preserved, not counted as a semantic
failure or a green gate. The retry uses `rust:1.97.1-trixie`, RepoDigest
`sha256:b1b3c9c0d921d7fa0a6d1f9ec7e4eab87f8c8ec97644c3d791450f131dec813f`,
with the same verified `icu783-linux` artifact and Node v22.15.1. Sources are
copied into the container filesystem; CR is stripped from shell scripts only
in that copy. Linux's complete workspace test command passed: 606 unit and
integration tests across 83 binaries, plus 4 doctests, zero failures/ignored
tests. The discovery adapter passed all 96 canonical documents, including the
POSIX-only rows and the 100/950/1050-depth plain/leaf-ignore binding witnesses.
Linux formatting, strict Clippy, warning-strict rustdoc and conformance verify
also passed. Its sequential control batch completed with 17/17 valid
intended-witness kills, zero invalid or surviving controls.

Both hosts use Rust 1.97.1, `CARGO_BUILD_JOBS=2`, `CARGO_INCREMENTAL=0`, and
`CARGO_PROFILE_DEV_DEBUG=0` / `CARGO_PROFILE_TEST_DEBUG=0`; these disable symbol
metadata, not debug assertions or alter test optimization. Set
`RUST_ICU_MAJOR_VERSION_NUMBER=78`, `MINION_AGENT_ICU_IDENTITY` to the verified
identity file and `MINION_SEARCH_ENGINE_ARTIFACTS` to the official archive
directory. Windows uses `RUSTFLAGS=-L native=<ICU>/lib64` and the same search
path in `RUSTDOCFLAGS=-D warnings -L native=<ICU>/lib64`; prepend ICU bin64 to
PATH. Linux uses `/icu/install/lib` for both flags and LD_LIBRARY_PATH,
`/icu/install/lib/pkgconfig` for PKG_CONFIG_PATH and Node on PATH. Cargo targets
and control scratch remain on E: (mapped as `/target` inside the container).

Run sequentially in `minion-agent-rust`:

```sh
cargo fmt --all -- --check
cargo clippy --locked --workspace --all-targets --all-features -- -D warnings
cargo test --locked --workspace --all-features
cargo doc --locked --workspace --no-deps
cargo run --locked -p xtask -- conformance verify
python scripts/wp141_negative_controls.py --source . --scratch <E-scratch>
```

The Windows doctest retry is `cargo test --workspace --all-features --doc`
with the corrected RUSTDOCFLAGS. Control names, source mutations and exact
intended witnesses are the committed `CONTROLS` table in the script; every
counted kill requires its own green baseline and compiled assertion failure.

The corpus integrity hashes (SHA-256) are:

- frontmatter: `4c4a58e269ea116be62920d4672fdfc5821c7f8a78232f0b8b05165f5cac9968`
- ignore: `baf69577830930d2026b9dfdc0a8b60a071c0e1709aceda95479135a3aed5802`

## Independent closure handoff

The Rust code is frozen at `ba6c2a022e017b4d2520f5c537fedb2221c10ef9` (#173).
The exact paired assurance head is recorded in issue #158 and the handoff,
after this evidence commit is pushed and its remote reachability verified.
Next owner: Claude. Review the approved shared contract and pinned Pi first,
then this candidate, shared scenarios/corpora and real binding witnesses.
No Python files, normative rules or canonical expectations are changed by
the implementation. The nine manifest edits change Rust evidence fields only.

Fresh logs are retained under workspace `.tmp`: Windows
`codex-scratch/wp141-win-compact-{test,fmt,clippy,doc,xtask}.log`,
`wp141-win-doctest-fixed.log`, `wp141-controls-windows-r3.log`, shared validation
`wp141-shared-validation-e.log`, docs `wp141-docs-process.log`; Linux
`wp141-rust-linux-target/wp141-{test,fmt,clippy,doc,xtask,controls}.log` and
per-control baseline/mutant logs in `wp141-controls-linux/`. Earlier invalid
control batches and environment failures remain historical evidence, not
successful results. The tests and control script are committed and independently
rerunnable; local logs do not substitute for the reviewer's fresh execution.

Rust WP-14.1: IMPLEMENTATION CANDIDATE, NOT CERTIFIED.
WP-14.1 cross-language: NOT CLOSED. No merge is performed by this handoff.
