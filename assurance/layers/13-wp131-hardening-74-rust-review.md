# WP-13.1 post-closure hardening #74 — independent Rust review

Verdict: **APPROVED**, for the exact candidate pair below only. This is an evidence-only follow-up to the already closed WP-13.1, not a new semantic contract or Layer-14 authorization.

| Candidate | Exact reviewed head | Base |
|---|---|---|
| `minion-agent#76` | `9fa48b448b6051b93d413cb303953ab2a2b3e6a2` | `main` `32fe82d20972ca53859189ed89011f5f1e1f2bd8` |
| `minion-agent-docs#174` | `2a6ed627e27adce5ccdec565ccd2347b7bf504c9` | `master` `ed72c96fbd426ae862d6d6f08595b531a887368a` |

Both heads were fetched, remote-reachable, open, non-draft, and mergeable. Pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`; Photon: `@silvia-odwyer/photon-node` 0.3.4 and its pinned WASM artifact.

## Independent authority audit

I read pinned Pi's `packages/coding-agent/src/core/tools/image-process.ts`, `image-resize-core.ts`, `mime.ts`, and `read.ts`, then the accepted `spec/tools.md`, TOOL-025 manifest row, existing canonical schema/runner, the candidate diff, and only then the candidate assurance. PR #76 adds five canonical documents, four binary fixtures, and five TOOL-025 evidence links. PR #174 adds reproducibility/assurance material. Neither changes normative rules or production behavior.

| Item | Direct pinned-Pi rule | Candidate witness | Result |
|---|---|---|---|
| A | Conversion hint uses the final resized MIME. | BMP whose resized PNG exceeds the ceiling and JPEG succeeds; hint says `image/jpeg`. | PASS |
| B | Scale hint uses ECMAScript `toFixed(2)` on the actual binary64 quotient. | 2150/2650/3050 widths yield `1.07`/`1.32`/`1.52`. | PASS |
| C | Search returns the first eligible candidate in Pi's order. | PNG too large; JPEG qualities 80 and 85 both fit; exact output matches quality 80. | PASS |
| D | The no-resize path requires base64 length **strictly** below 4,718,592. | A real decodable 3,538,941-byte PNG passes unchanged; the 3,538,942-byte variant re-encodes. | PASS |
| E | `acTL` before first `IDAT` makes the PNG sniffer reject it. | Text-branch output for pre-`IDAT` `acTL`; after-`IDAT` control remains PNG. | PASS |

The D witness is a real end-to-end image fixture, not a fabricated boundary result. The separate resize-*candidate* exact-ceiling limitation remains the previously accepted non-blocking WP-13.1 evidence limit; this follow-up neither claims to solve nor changes it.

## Fresh replay and conformance

I ran the authority harness in disposable `node:22.15.1-alpine` using a fresh LF Git checkout of the pinned Pi commit. It verified the Pi source hashes, package SRI, Photon WASM hash, runtime version, and regenerated corpus hashes. The fresh image/text authority JSON exactly matched the committed results; all ten corpus files and four canonical binary fixtures matched by SHA-256. Regenerating the five scenario YAML files yielded semantic YAML equality with PR #76. The text-branch helper was compared to pinned `read.ts`, not treated as independent authority.

An additional direct Photon probe confirmed that the resized PNG is 16,003,288 bytes (ineligible), JPEG 80 is 2,723,660 bytes (eligible and exactly the canonical output), and JPEG 85 is 3,017,636 bytes (also eligible but different). This distinguishes first-eligible selection from best/later-quality selection. The candidate's five single-point Python negative controls are documented; the direct authority and real language runners independently support their outcomes.

On the separate Rust-owned count branch (one line, `45` to `50`, PR `minion-agent#77` @ `49c07e49c31dc717369402e2745db2d0c2abf2a8`), pointed at the exact PR #76 canonical tree:

| Gate | Fresh result |
|---|---|
| Rust built-in canonical runner | 50 documents / 163 cases, PASS |
| `cargo fmt --all -- --check` | PASS |
| `cargo clippy --workspace --all-targets --all-features -- -D warnings` | PASS |
| `cargo test --workspace --all-features -j 2 --quiet` | 411 tests, 0 failures |
| `RUSTDOCFLAGS="-D warnings" cargo doc --workspace --no-deps --quiet` | PASS |
| `cargo run -p xtask -- conformance verify` | PASS |
| Shared schema/manifest validation | PASS |
| Python built-in canonical runner against candidate | 51/51, PASS |

The initial isolated Python conformance invocation omitted the project's pinned ICU environment and failed 17 unrelated `ls` cases. Supplying the pinned ICU binary/identity and rerunning yielded 51/51. The native Windows checkout also produced CRLF shell-script failure in Alpine; a clean LF Pi checkout and LF-normalized evidence-copy replay passed. These are invocation/checkout portability notes, not candidate semantic failures. A known Windows ICU linker warning during Rust tests was nonfatal and not new.

## Contract-quality result and handoff

No runner simulates image processing: both language runners execute their real existing read implementations, while the candidate generator invokes the pinned Pi/Photon authority. Fixtures are deterministic and hash-checked. No TOOL-025 rule, disposition, production code, or Layer-14 boundary changed. No active parity, contract-assurance, or Pi-behavior uncertainty finding was found.

**APPROVED:** `minion-agent#76` @ `9fa48b448b6051b93d413cb303953ab2a2b3e6a2` and `minion-agent-docs#174` @ `2a6ed627e27adce5ccdec565ccd2347b7bf504c9` for evidence-only merge, provided their exact heads remain unchanged. Merge Rust count PR #77 with or before #76 so accepted `main` never has a stale pinned scenario count. This approval does not authorize a later candidate SHA, change WP-13.1 semantics, reopen its certification, or start Layer 14.
