# Layer 12 Python implementation targeted re-review

Mode: targeted independent implementation re-review (`agent-workflow.md` §11.4)

Verdict: **REJECTED**

## Exact target

- remediated Python candidate: `EGAILab/minion-agent` PR #44 at
  `cff76057a9b131f8e979c77755f15422290b8903`
- rejected predecessor: `849d4ea5aba12090ad663f5e16ece4bf1a369990`
- original independent review: `assurance/layers/12-execution-seams-python-implementation-review.md`
  at `71d8382c61c729f6b815a5f8d73b2fa6377679de`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`
- shared/docs baseline: `3da25015383c4ff6bda956b34d91e05b25f49660`

The PR head was fetched through GitHub's pull-request ref and checked out in a clean detached
worktree. PR #44 was open, ready for review, and mergeable at the exact target SHA. The issue #39
control block named `NEXT_OWNER = Codex` and requested an ordinary implementation re-review.

Per the workflow, this pass reviewed the seven prior findings and the semantic dependencies
touched by their fixes. It did not repeat an unrestricted whole-layer audit. No candidate,
shared-contract, Rust, or Layer-13 files were modified.

## Finding-closure ledger

| Finding | Remediation result | Status |
|---|---|---|
| `L12-PY-R001` | The empty-directory `list_dir` pre-check and caller-observable mid-read/write cancellation race are implemented and discriminated. | **RESOLVED** |
| `L12-PY-R002` | Empty/rooted joins and replacement decoding are fixed, but malformed `file:` URL fallback remains observably wrong and its test remains non-discriminating. | **PARTIALLY_RESOLVED_BLOCKING** |
| `L12-PY-R003` | Protocols, names, identities, and plugins now exist, but the shell plugin bypasses the mounted `ctx.subprocess` capability. | **PARTIALLY_RESOLVED_BLOCKING** |
| `L12-PY-R004` | Late abort after known natural/explicit exit is fixed, but an unsuccessful/no-effect signal kill is still recorded as the causal exit reason. | **PARTIALLY_RESOLVED_BLOCKING** |
| `L12-PY-R005` | Shell callbacks now receive incrementally decoded UTF-8 text, including split multibyte sequences. | **RESOLVED** |
| `L12-PY-R006` | A subprocess pre-spawn abort now retains the shell `aborted` classification. | **RESOLVED** |
| `L12-PY-R007` | The original taskkill/resource-warning leak is fixed, but the fix closes output transports during `wait()` and breaks the contracted post-wait drain. | **PARTIALLY_RESOLVED_BLOCKING** |

No finding is closed from prose or aggregate green tests alone.

## Still-open findings

### L12-PY-R002 — malformed `file:` URL fallback still diverges

**Taxonomy:** `PI_PARITY_DEFECT`  
**Status:** `PARTIALLY_RESOLVED_BLOCKING`

Pinned Pi attempts `fileURLToPath`; if parsing fails, it retains the original string as the path
input and then continues the ordinary lexical absolute/relative resolution pipeline. The candidate
uses permissive `urlparse`/`url2pathname` parsing and, on its manually detected error path, returns
the raw string immediately instead of continuing lexical resolution.

Exact Windows observations:

```text
input: file:///%ZZ
candidate: E:\%ZZ
pinned Node: <cwd>\file:\%ZZ

input: file://%zz-not-a-valid-escape
candidate: <cwd>
pinned Node: <cwd>\file:\%zz-not-a-valid-escape
```

The existing `test_malformed_file_url_is_kept_as_literal_string` still asserts only
`isinstance(resolved, str)`, so every wrong value above passes. The POSIX non-local-host witnesses
also require the raw string itself rather than testing Pi's subsequent relative-path resolution.

Minimal correction: use WHATWG/Node-compatible file-URL validation or an equivalent exact parser;
on parse failure, retain the original string as the input to the normal lexical resolution steps,
not as an early return. Permanently assert exact results for invalid percent escapes and invalid
URLs on the supported host platforms.

### L12-PY-R003 — the shell plugin does not consume `ctx.subprocess`

**Taxonomy:** `CONTRACT_ASSURANCE_DEFECT`  
**Status:** `PARTIALLY_RESOLVED_BLOCKING`

The remediation correctly added `FileSystem`, `Shell`, and `Subprocess` protocols, service names,
execution-world identities, and Runtime plugins. `LocalShell` now accepts an abstract
`Subprocess`. However, `shell_plugin` constructs `LocalShell()` without resolving the mounted
`subprocess` service, so that constructor silently creates a second private `LocalSubprocess`.

A discriminating probe mounted a fake conforming `ctx.subprocess`, then mounted `shell_plugin`:

```text
ctx.shell._subprocess is mounted_fake_subprocess -> False
```

This defeats the approved architecture that the local shell provider is built on the independently
swappable `ctx.subprocess` capability. The plugin tests only assert concrete types and common
world-value equality, so they do not detect the bypass.

Minimal correction: make the shell plugin depend on and inject the Runtime's mounted subprocess
capability into `LocalShell`. Add a non-local/fake provider witness proving a shell operation is
actually dispatched through that mounted seam. Do not create another registry or private service
authority.

### L12-PY-R004 — attempted signal kill is still mistaken for causal signal termination

**Taxonomy:** `CONTRACT_ASSURANCE_DEFECT`  
**Status:** `PARTIALLY_RESOLVED_BLOCKING`

The remediation no longer checks only the signal's state at `wait()` time, so the original
late-abort witnesses now pass. But `_watch_signal` sets `_kill_cause = "signal"` before it knows
whether `_kill_process_tree` affected the process. `_kill_process_tree` is best-effort and
suppresses the relevant failures. Therefore the common exit/kill race can still report
`Err(aborted)` when the process exited naturally and the signal-triggered kill attempt had no
effect.

A controlled witness held a process's natural `0` result, fired the signal, made the kill attempt
a no-op (the process-already-gone case), then released the natural result:

```text
kill attempts: [pid]
process result: 0
candidate wait(): Err(aborted)
required wait(): Ok(ExitStatus(exit_code=0))
```

Minimal correction: record signal causality only when signal-triggered termination actually wins
the process-exit race. Add a permanent process-already-exited/kill-no-effect witness in addition to
the already-added late-abort tests.

### L12-PY-R007 — warning cleanup closes streams before the caller drains them

**Taxonomy:** `CONTRACT_ASSURANCE_DEFECT`  
**Status:** `PARTIALLY_RESOLVED_BLOCKING`

The taskkill helper is now settled and the warnings-as-errors execution gate is clean. However,
`Process.wait()` calls `_close_transport(self._proc)`, and `_close_transport` explicitly closes the
stdout/stderr stream transports. The normative subprocess contract says `wait()` settles on exit
alone and the caller may continue calling `read_chunk()` until EOF afterward.

A discriminating stream double with unread payload produced:

```text
wait()                    -> Ok(ExitStatus(exit_code=0))
stdout transport closed  -> True
read_chunk() after wait   -> Err(pipe_error: transport closed before drain)
```

The candidate's post-wait test only checks that `read_chunk()` returns `Ok`; `Ok(None)` after
premature closure satisfies it, so it does not prove that buffered output remains readable.

Minimal correction: settle owned process/helper resources without closing readable stream
transports before their EOF has been consumed. Add a post-wait witness that asserts exact unread
payload followed by EOF, while retaining the warnings-as-errors gate.

## Resolved-finding verification

- `L12-PY-R001`: direct tests cover a pre-aborted empty directory and portable delayed
  text/binary/write calls; the caller settles `Err(aborted)` promptly.
- `L12-PY-R005`: the public callback types are `str`, and incremental decoders preserve a UTF-8
  character split across byte chunks.
- `L12-PY-R006`: `LocalShell.exec` preserves `SubprocessErrorCode.ABORTED` as
  `ShellErrorCode.ABORTED`; the deterministic flip-between-check-and-spawn witness passes.

These closures are provisional until the later mandatory final complete review, as required by
the ordinary-remediation route.

## Fresh gates

Run against the exact remediated candidate:

```text
uv run pytest tests/execution --no-cov -q \
  -W error::pytest.PytestUnraisableExceptionWarning \
  -W error::ResourceWarning
    PASS: 177 tests, 4 platform skips, zero promoted warnings

uv run pytest --no-cov -q
    PASS: full suite, zero failures

uv run ruff check .
    PASS

uv run ruff format --check .
    FAIL: the same 7 pre-existing files outside this remediation would be reformatted

uv run mypy
    PASS: 79 source files

uv run pytest tests/conformance/test_schema_validation.py \
              tests/conformance/test_manifest_validation.py --no-cov -q
    PASS: 213 tests
```

Aggregate green tests do not override the four discriminating failures above.

## Verdict and workflow transition

```text
shared Layer-12 contract
    APPROVED / unchanged

Rust Layer 12
    CERTIFIED

Python Layer 12
    NOT CERTIFIED

Layer 12 cross-language
    NOT CLOSED

Layer 13
    NOT STARTED
```

PR #44 at `cff76057a9b131f8e979c77755f15422290b8903` is rejected. Return only the
four refined findings above for targeted remediation. Re-check the workflow's convergence triggers
against the now-larger finding history before another remediation pass. Do not begin a final
complete review, merge the candidate, or start Layer 13.
