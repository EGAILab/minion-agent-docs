# R002 differential corpus -- reproduction scripts

Committed per independent checkpoint review (`minion-agent-docs#120` @
`ca91006402ecf952f5e73691eca684d60ee3edaa`, non-blocking evidence-hardening note) so the
`12-python-r002-differential-corpus.md` table and the Node version-drift comparison can be
reproduced mechanically, rather than only by re-reading this artifact's own prose.

## Prerequisites

- Node.js `v22.19.0` (Pi's exact declared `engines.node` floor) and, for the drift check, the
  latest available Node `v22.x` -- both downloaded from `https://nodejs.org/dist/<version>/`
  and checksum-verified against that version's own published `SHASUMS256.txt` before use.
- A checkout of `minion-agent#44` (Python) at the exact frozen SHA
  `d44ea0e2b46e18997a425e514c7ab8f458642f7d`.
- Rust (`cargo`) -- the `rust_oracle_probe/` subdirectory here is a self-contained scratch
  Cargo project pinning `url = "=2.5.8"` (which pins `idna = "1.1.0"`) from
  `minion-agent-rust`'s own `Cargo.lock` at the certified commit `2b309ee8`, reproducing
  `filesystem.rs`'s `resolve_local_path`/`expand_path`/`lexical_normalize` VERBATIM (read-only
  source reading, not a modification to `minion-agent-rust/**`, which this scratch project does
  not touch or depend on at all).

## Steps

```sh
# 1. Node oracle (repeat once per Node version, e.g. v22.19.0 then v22.23.2)
<path-to-node-v22.19.0>/node node_probe.mjs > node_corpus_results_22.19.0.txt

# 2. Python candidate -- edit python_probe.py's sys.path.insert(...) to point at your checkout
#    of minion-agent#44 @ d44ea0e2b46e18997a425e514c7ab8f458642f7d, then:
<python-in-that-checkout's-venv> python_probe.py > python_corpus_results.txt

# 3. Rust candidate
cd rust_oracle_probe && cargo run --release > ../rust_corpus_results.txt 2>&1 && cd ..

# 4. Build the comparison matrix (writes matrix_full.tsv alongside this script)
python build_matrix.py
```

`build_matrix.py` prints the match counts and the exact mismatching rows for both Python and
Rust against the Node oracle, and writes the full `input / node / python / rust / py_match /
rust_match` table to `matrix_full.tsv` -- the same data rendered as markdown in
`../12-python-r002-differential-corpus.md`.

To confirm version-drift stability, diff two Node-version output files directly:

```sh
diff node_corpus_results_22.19.0.txt node_corpus_results_22.23.2.txt
```

An empty diff (as observed when this corpus was built) confirms the two Node versions produce
byte-for-byte identical output for every case.
