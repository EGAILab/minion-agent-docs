WP-13.1 Python implementation pass -- evidence tooling (see ../../13-wp131-python-implementation.md).

gen_scenarios.py  Generates minion-agent conformance/agent/builtin-*.yaml. Every expected value comes
                  from a pinned-Pi authority: read text from piauth/ (Pi read.ts + truncate.ts under
                  Node), images from the R005-A authority.json, ls byte truncation from Pi's
                  truncateHead, collation from the pinned PyICU 2.16.2 / ICU 78.3 engine and the
                  R006-C v2 recorded comparison matrix, fixed texts from pinned source / spec.
                  Run: <python with PyYAML + pinned PyICU> gen_scenarios.py <code> <docs> <piauth>
synth.py          Synthetic JPEG/WebP/PNG/GIF/BMP byte inputs for every EXIF/MIME parser branch;
                  expected values from Pi via piauth/probe_bytes.mjs (tests/tools/builtin/
                  test_byte_parsers.py).
mutants.py        Negative controls: 23 single-point wrong implementations injected into the real
                  modules; the builtin_tool canonical suite must fail for each (mutants.log: 23/23).
pi_sources.sha256 The pinned Pi files audited for this pass.
