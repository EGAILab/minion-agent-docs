# Contract-review probes

Review-only, no production implementation.

`check.py <code candidate> <docs candidate> <replayed out> <regenerated scenarios>` uses the existing review Python environment (PyYAML/jsonschema). It verifies the authority hash/bytes, four scenario Git blobs, and the four R002 malformed-schema probes. Current candidate reports all four malformed cases ACCEPTED. Required corrected result: each REJECTED while all original scenarios validate.

`probe.mjs` runs the actual pinned validator after the candidate authority setup. Mount Pi at `/pi`, candidate `assurance/layers/data/l0506-d001` at `/evid`, writable output at `/out`, and this directory at `/review`, in `node:22.15.1-alpine`. Execute `sh /evid/harness/run_authority.sh` then `node --experimental-strip-types /review/probe.mjs` in the same container. It asserts that the validation diagnostic projects Infinity/NaN to null and -0 to 0, while the original runtime values are unchanged. The authority setup verifies pinned Pi hashes and typebox SRI before this probe.

These are independent reviewer characterizations, not substitutes for future real-binding production/negative-control tests.
