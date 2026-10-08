# WP-14.1 — Rust implementation candidate

Status: implementation in progress; independent Rust closure review pending.
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

Fresh final gate results and exact remote candidate heads will be recorded
before handoff. Rust remains an implementation candidate until Claude's
independent exact-SHA closure review. Cross-language WP-14.1 is not closed.

## Validation progress (not a completed handoff)

Windows control preparation reached 17/17 valid intended-witness kills. The
first full Windows build exhausted E: while writing PDBs (`LNK1318` / OS error
112); it did not run tests and is not semantic gate evidence. Regenerable
package build outputs were removed with `cargo clean -p minion-agent` (20.3 GiB).
The full sequential rerun uses two build jobs, no incremental metadata and
dev/test debug-symbol metadata disabled. Debug assertions and optimization
levels remain their normal test defaults. Linux will use the same resource
settings. No source, corpus, dependency artifact or contract was removed.

The corpus integrity hashes (SHA-256) are:

- frontmatter: `4c4a58e269ea116be62920d4672fdfc5821c7f8a78232f0b8b05165f5cac9968`
- ignore: `baf69577830930d2026b9dfdc0a8b60a071c0e1709aceda95479135a3aed5802`
