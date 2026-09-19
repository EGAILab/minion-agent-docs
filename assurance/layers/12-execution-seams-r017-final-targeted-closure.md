# Layer 12 — `L12-R017` final targeted convergence closure

**Mode:** independent Rust-side contract review only  
**Workflow step:** `agent-workflow.md` §11.8.7  
**Pinned Pi:** `b7bb00b936dbe21b8e160b3e89efdec361846699`  
**Code candidate:** `997d22ba52b2040cf190fa3e9515c6db738aad1b` (`minion-agent#40`)  
**Docs candidate:** `d0ab7b53cf16d3da17360ea5faa633a235ee8e7a` (`minion-agent-docs#110`)  
**Prior targeted review:** `cb3cb3ea9adf70003a1d1ba3c110a450905cb549` (`minion-agent-docs#114`)  

The candidate heads and issue control state were fetched and independently verified. Issue #39
named Codex as `NEXT_OWNER` and requested a targeted review of only the refined `L12-R017`, its
semantic dependencies, and regression safety for already-settled findings. No implementation or
Layer 13 work was authorized or performed.

## Pinned-Pi recheck

Pinned Pi's `NodeExecutionEnv`:

- tracks each `exec()` child in `activeChildPids`;
- has `cleanup()` kill every tracked process tree and clear that set;
- settles a cleanup-killed command through ordinary exit handling when no callback error, timeout,
  or abort signal has higher precedence; and
- constructs the success value using `exitCode: code ?? 0`.

The last rule is conditional: a numeric child completion code is preserved, and zero is substituted
only when the code is absent/null.

## `L12-R017` result

```text
L12-R017
    PROVISIONALLY CLOSED

candidate
    code 997d22ba52b2040cf190fa3e9515c6db738aad1b
    docs d0ab7b53cf16d3da17360ea5faa633a235ee8e7a
```

`spec/execution.md` §5.7 and `EXEC-004` now state both observable cases:

1. reported numeric code `K` -> successful result preserving `K` exactly;
2. absent/null code -> successful result with zero.

Both remain ordinary successful settlements rather than `aborted` or `timeout`. The witness matrix
contains both cases and rejects an implementation that always overwrites the reported code with
zero.

### Negative control

**Known-bad SHA:** code `0b573c653e641fdd8242656e0fbbcee133b99f20`, docs
`134d246f0b710099aee6b96c8de9d5ac68fae6c0`.

**Method:** documentary/source-rule comparison. The known-bad spec and manifest mandated
unconditional `exit_code: 0`; they therefore fail the numeric-`K` case while pinned Pi's
`code ?? 0` preserves `K`. The reviewed candidate explicitly preserves `K` and passes both cases.
This is a contract-only work package, so no production execution implementation exists yet to
mutate; the documentary discriminator is the applicable §11.8.7.1 evidence.

## Regression scope

The remediation changed only:

- `pi-parity-manifest.yaml` — `EXEC-004` settlement text;
- `spec/execution.md` — §5.7, remediation history, and the R017 witness.

It did not modify `EXEC-001`/`EXEC-002`/`EXEC-003`, the `FsTarget` design, provider classification,
Python, Rust, schemas, or canonical scenarios. `L12-R015` and `L12-R016` remain provisionally
closed, as do `L12-R001`–`L12-R014`.

## Fresh gates

```text
uv run pytest --no-cov -ra
    1504 passed, 19 xfailed

uv run ruff check .
    PASS

uv run mypy
    PASS — 71 source files

uv run pytest --no-cov \
    tests/conformance/test_manifest_validation.py \
    tests/conformance/test_schema_validation.py -q
    PASS — 213 tests

manifest inventory
    101 rows / 101 unique IDs

git diff --check (code and docs remediation deltas)
    PASS
```

## Workflow result

All findings in `CE-L12-01-03` are now provisionally closed. Across the three Layer-12 convergence
episodes, `L12-R001` through `L12-R017` are provisionally closed at their recorded exact candidates.

This is not final contract approval. Per §11.8.8, the next action is one complete independent final
review of the frozen code/docs candidate above. The issue may transition to
`FINAL_CONTRACT_REVIEW`, with `NEXT_OWNER = Codex`. That final review must occur in a later pass.

```text
shared Layer-12 contract
    NOT YET APPROVED FOR RUST IMPLEMENTATION

Rust Layer 12
    BLOCKED / NOT IMPLEMENTED

Layer 12 cross-language
    NOT CLOSED

Layer 13
    NOT STARTED
```
