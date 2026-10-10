This is the reproduction for finding minion-agent#193 (`L06-RUST-CYCLIC-VALIDATION`).
- Codex wrote it during the L0506-D005 contract review 1 (#190 issuecomment-6090443463).
- It is preserved here unchanged, except for the dependency path in `Cargo.toml`.

1. In `Cargo.toml`, replace `MINION_AGENT_CHECKOUT` with the path of a minion-agent checkout. The finding was observed at main `4efa52ff` and candidate `2bc2dd7c`.
2. Build with the repository's pinned ICU flags: `RUST_ICU_MAJOR_VERSION_NUMBER=78` and `RUSTFLAGS="-L native=<ICU lib dir>"`.
3. Run both variants:
   - `cargo run` (acyclic) prints `EXECUTE reached`;
   - `cargo run -- cycle` prints `structured_clone PASS; entering real execution/validation`, then overflows its stack.
