# I004 review probes

Review-only evidence, not production implementation or canonical adapters.

`python_hook.py`: run with the exact code #87 candidate's Python environment, from `minion-agent-python`, with that directory on PYTHONPATH (the probe imports its existing test context helper). It uses the actual ToolRegistry, edit tool, local filesystem, execute_call and TOOLS_PRE_EXECUTE hook. Expected: `real Layer-06 hook extra inf isinf True`, `is_error False file b`.

`rust-probe`: `cargo run --manifest-path rust-probe/Cargo.toml` (offline works with the existing cache). Pins the same serde_json 1.0.140 as the certified Rust Cargo.lock. Expected: parsing the same valid edits JSON reports `number out of range at line 1 column 5037`; constructing Infinity returns None; negative zero returns Some(Number(-0.0)).

`pi_prepare.mjs`: uses the same pinned Node 22.15.1-alpine container/setup as the authority harness in `../13-wp132-evidence`. Mount pinned Pi at `/pi`, that evidence directory at `/evid`, writable output at `/out`, and this probe directory at `/probe`. In the same container run `sh /evid/harness/run_authority.sh` first to materialize `/tmp/s/a/pi/core/tools/edit-diff.ts`, then `node --experimental-strip-types /probe/pi_prepare.mjs`. It extracts the actual pinned edit.ts preparation body, erasing only TS annotations, and invokes the staged actual edit-diff implementation. Expected: `extra_is_infinity:true`, successful replacement; finite integer witness rounds to 9007199254740992. Source extraction fails loudly if the pinned function layout changes; it is not a substitute for pinned-file integrity checks performed by the authority harness.

The final review records those integrity checks, candidate SHA pair, successful replay hashes, real hook result and locked Rust-domain result. None of these probes changes candidate code.
