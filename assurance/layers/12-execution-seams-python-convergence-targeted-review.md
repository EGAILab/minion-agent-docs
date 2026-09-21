# Layer 12 Python convergence targeted closure review

Mode: targeted convergence closure review (`agent-workflow.md` §11.8.7)

Verdict: **REJECTED — CONVERGENCE REMAINS ACTIVE**

## Exact target

- convergence episode: `CE-L12-PY-01-01`
- Python candidate: `EGAILab/minion-agent` PR #44 at
  `6ef45734dbeccabdfe1f9fd07ca9f367ed9929e7`
- predecessor: `cff76057a9b131f8e979c77755f15422290b8903`
- prior targeted review evidence:
  `assurance/layers/12-execution-seams-python-implementation-rereview.md` at
  `5f9ebefc0248a5c979edeb084fd7f68225766bf3`
- convergence checkpoint/implementation record:
  `EGAILab/minion-agent#39` comment `5745460384`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`

The candidate was fetched from GitHub's PR ref and reviewed in a clean detached worktree. Issue
#39 named `NEXT_OWNER = Codex` and requested this targeted review. The review scope was the four
open convergence findings, dependencies touched by their fixes, and regression of previously
closed R001/R005/R006. It was not substituted with a complete final review.

No Python, shared contract, Rust, or Layer-13 file was modified.

## Closure ledger

| Finding | Independent result | Status |
|---|---|---|
| `L12-PY-R001` | Empty-directory and prompt caller-settlement witnesses remain green. | **PROVISIONALLY_CLOSED (retained)** |
| `L12-PY-R002` | The two prior malformed inputs are fixed, but the ad-hoc file-URL parser still differs from Node for encoded hosts and encoded separators/invalid escapes in otherwise drive-shaped paths. | **STILL_OPEN** |
| `L12-PY-R003` | `shell_plugin` now requires, resolves, and dispatches through the mounted `ctx.subprocess`; the fake-provider witness discriminates the old bypass. | **PROVISIONALLY_CLOSED** |
| `L12-PY-R004` | Immediate no-effect kill is fixed, but the eager cause flag survives when natural exit cancels a still-pending no-effect kill check. | **STILL_OPEN** |
| `L12-PY-R005` | Incremental decoded-text callback evidence remains green. | **PROVISIONALLY_CLOSED (retained)** |
| `L12-PY-R006` | The shell pre-spawn abort classification evidence remains green. | **PROVISIONALLY_CLOSED (retained)** |
| `L12-PY-R007` | Exact buffered payload remains readable after `wait()`, EOF closes its stream transport, and warnings-as-errors is clean. | **PROVISIONALLY_CLOSED** |

## Open convergence findings

### L12-PY-R002 — the replacement file-URL parser remains incomplete

**Taxonomy:** `PI_PARITY_DEFECT`  
**Status:** `STILL_OPEN`

The candidate now correctly falls through to normal lexical resolution when its helper rejects a
file URL, and it fixes the two exact prior inputs. However, `_file_url_to_path` is a small set of
regular-expression/host checks layered over Python's permissive `urlparse`/`url2pathname`, not an
equivalent implementation of Node's WHATWG URL plus `fileURLToPath` validation.

Live Node/candidate comparisons on Windows produced:

```text
input: file:///C:/%ZZ
Node:      fileURLToPath throws; resolvePath falls back to <cwd>\file:\C:\%ZZ
candidate: C:\%ZZ

input: file:///C:/a%2Fb
Node:      ERR_INVALID_FILE_URL_PATH; fallback to <cwd>\file:\C:\a%2Fb
candidate: C:\a\b

input: file://%41/share
Node:      valid host after WHATWG host decoding; \\a\share
candidate: rejected solely because the raw host contains "%", then cwd-relative fallback
```

Thus the convergence checkpoint's claim that the helper has “equivalent fidelity” is not closed.
The new witnesses cover only the originally named malformed shapes and allow these adjacent
counterexamples.

Minimal correction: use a standards-faithful WHATWG/file-URL parser or fully characterize the
relevant Node validation and decoding surface before implementing it. Add the three witnesses
above (plus their valid controls) so accepted percent-encoded hosts and rejected encoded path
separators/invalid escapes cannot regress independently.

### L12-PY-R004 — eager signal cause still survives a pending no-effect kill

**Taxonomy:** `CONTRACT_ASSURANCE_DEFECT`  
**Status:** `STILL_OPEN`

The candidate's new witness makes `_kill_process_tree` return `False` immediately, giving
`_watch_signal` time to clear its eager `"signal"` flag before natural exit. It does not exercise
the scheduling race described in the implementation's own rationale: natural exit may reach
`wait()` while `_watch_signal` is still awaiting kill confirmation. `wait()` then cancels that
watcher, so a later `False` result can never clear the eager flag.

A deterministic witness used a kill function that entered, remained pending, and would return
`False`; it then released a natural exit code `0` through `wait()`:

```text
kill attempt entered                    YES
natural process result                  0
wait() cancels pending watcher           YES
candidate wait result                    Err(aborted)
required result                          Ok(ExitStatus(exit_code=0))
```

Minimal correction: coordinate `wait()` and the signal-kill attempt so classification cannot be
read while a causality decision is still pending, and so neither a genuine signal kill nor a
no-effect attempt is lost through watcher cancellation. Add both delayed-`False` and delayed-`True`
witnesses; an immediate mock result is not a sufficient negative control for this race.

## Provisionally closed convergence findings

### L12-PY-R003

`shell_plugin` declares `inject=["subprocess"]`, resolves `ctx.subprocess`, and passes that exact
instance to `LocalShell`. The fake mounted provider's `spawn()` is invoked. The old private
`LocalSubprocess` fallback is no longer used through this plugin path.

### L12-PY-R007

`wait()` no longer closes stdout/stderr transports. The real-process witness waits first, then
reads and asserts the exact `b"buffered-payload"` before EOF. `ReadableStream` closes its own
transport at natural EOF. The warnings-promoted execution suite passes without resource or
unraisable warnings. No new contrary witness was found within the touched ownership surface.

These closures remain provisional until the mandatory final complete exact-SHA review after every
convergence finding is closed.

## Regression scope

- `L12-PY-R001`: list pre-check and delayed read/binary/write caller-settlement tests pass.
- `L12-PY-R005`: decoded callbacks and split-multibyte tests pass.
- `L12-PY-R006`: deterministic abort-between-shell-check-and-spawn test passes.

No regression was found in those previously closed findings.

## Fresh targeted gates

```text
uv run pytest tests/execution --no-cov -q \
  -W error::pytest.PytestUnraisableExceptionWarning \
  -W error::ResourceWarning
    PASS: 186 passed, 4 platform skips, zero promoted warnings

focused convergence + R001/R005/R006 regression selection
    PASS (platform-specific FIFO cases skipped as configured)

uv run ruff check .
    PASS

uv run ruff format --check .
    FAIL: the same 7 pre-existing files outside this candidate would be reformatted

uv run mypy
    PASS: 79 source files

schema + manifest validation
    PASS: 213 tests
```

The green candidate tests do not include the two discriminating counterexample families above.

## Verdict and next state

```text
CE-L12-PY-01-01
    ACTIVE

open findings
    L12-PY-R002
    L12-PY-R004

newly provisionally closed
    L12-PY-R003
    L12-PY-R007

previous provisional closures retained
    L12-PY-R001
    L12-PY-R005
    L12-PY-R006

Python Layer 12
    NOT CERTIFIED

Rust Layer 12
    CERTIFIED / unchanged

Layer 12 cross-language
    NOT CLOSED

Layer 13
    NOT STARTED
```

Return only R002 and R004 to the Python owner within the existing convergence episode. Do not
transition to `FINAL_CONTRACT_REVIEW` until both are independently provisionally closed. Any new
candidate requires another targeted closure review of the remaining findings and touched
dependencies.
