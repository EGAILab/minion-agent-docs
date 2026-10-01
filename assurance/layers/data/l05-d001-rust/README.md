# L05-D001 Rust discrimination evidence

The unchanged canonical runner is
`minion-agent-rust/crates/minion-agent/tests/schema_domain_conformance.rs`.
Run from the Rust workspace:

```text
cargo +1.97.1 test -p minion-agent --all-features --test schema_domain_conformance
```

Every mutation below was applied to **production Rust source**, one at a time.
The runner/scenarios/expectations were not changed between mutant and control.
After each run the source was restored; the final control passes 810/810.
No mutant code is included in the candidate.

| Mutation | Exact seam | Observed result |
|---|---|---|
| Reject non-scalar schemas | Add `|| value.try_to_json().is_err()` to the `RuntimeSchemaObject::try_from` object-domain guard | Registration refuses a legal schema (`InvalidDomain`); canonical test fails |
| UCS-2 pattern search | In `RuntimeKeyword::valid`, replace only `find_from_utf16` with `find_from_ucs2` | 7 verdict mismatches, including both pair halves in the pair |
| UCS-2 pattern-property search | In `RuntimeObjectKeyword::valid`, replace only `find_from_utf16` with `find_from_ucs2` | 7 verdict mismatches in pattern-property documents; ordinary pattern documents remain correct |
| Schema replacement | At `validate_runtime_schema` entry, recursively replace schema strings and keys with `to_utf8_lossy()`; keep instances unchanged | 92 verdict mismatches |
| Instance-key replacement | At the same entry, recursively replace only instance object keys with `to_utf8_lossy()`; keep string values and schema unchanged | 56 verdict mismatches |

The recursive replacement mutation is precisely:

```rust
fn wrong_normalize(value: &PreparedValue) -> PreparedValue {
    match value {
        PreparedValue::String(s) => PreparedValue::String(s.to_utf8_lossy().into()),
        PreparedValue::Array(a) => PreparedValue::Array(a.iter().map(wrong_normalize).collect()),
        PreparedValue::Object(o) => PreparedValue::Object(o.iter().map(|(k, v)|
            (k.to_utf8_lossy().into(), wrong_normalize(v))).collect()),
        _ => value.clone(),
    }
}
let wrong_schema = wrong_normalize(schema);
let schema = &wrong_schema;
```

For the instance-key mutation, change the String arm to
`PreparedValue::String(_) => value.clone()`, and instead bind
`let wrong_value = wrong_normalize(value); let value = &wrong_value;`.

`mutation-results.json` preserves every mismatching canonical case ID.
Each material mutant exits 101 with one failing Rust test.

**Non-discriminating attempt, disclosed:** merely changing the pattern
compiler flag from `"u"` to `""` passed all 810 cases. It is not counted as
negative-control proof. The actual UCS-2 input search mutations above are
discriminating and do cover the required pair-half cells.

## Independent authority replay

The exact accepted harness was re-executed under host Node v22.15.1 after:

- verifying Pi HEAD `b7bb00b936dbe21b8e160b3e89efdec361846699` and a clean Pi tree;
- checking supplied typebox 1.3.7 bytes against the pinned Pi lockfile SHA-512 SRI;
- verifying `validation.ts` SHA-256
  `460786b57dead200e411b9afec916a5049c96ebcff4da082096456ac06d44fb7`;
- running the committed case generator, authority script and scenario generator unchanged.

All 810 authority observations reproduced byte-identically:
`ad7976793de2e9f508e53b0e16e06d15be149fc9a8d895965761b84e1d0cf244`.
All 10 regenerated scenario documents are byte-identical to accepted canonical data.
This is an offline hermetic replay, not a Python-oracle substitution.
