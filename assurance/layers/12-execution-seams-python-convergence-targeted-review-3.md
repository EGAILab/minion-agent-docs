# Layer 12 Python convergence targeted closure review 3

Mode: targeted convergence closure review (`agent-workflow.md` §11.8.7)

Verdict: **REJECTED — CONVERGENCE REMAINS ACTIVE**

## Exact target

- convergence episode: `CE-L12-PY-01-01`
- Python candidate: `EGAILab/minion-agent` PR #44 at
  `65023b5fe39d06745695a0678bb25fb876263254`
- predecessor: `81a7e10412c1fe718286324f59f8c60224505a59`
- prior targeted evidence:
  `assurance/layers/12-execution-seams-python-convergence-targeted-review-2.md` at
  `a4d8284ea50d905b3bf1130b6dbd35efba609fec`
- revised checkpoint/implementation record: issue #39 comment `5747455247`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`

The exact PR head was fetched from GitHub and reviewed against pinned Pi and the approved
Layer-12 contract. Scope was R002/R004, dependencies touched by those fixes, and regression of the
five provisionally closed findings. This was not a complete final review. No candidate, shared,
Rust, or Layer-13 file was modified.

## Closure ledger

| Finding | Result | Status |
|---|---|---|
| `L12-PY-R002` | The two previously named omissions were attempted, but Python's built-in IDNA codec is not Node/WHATWG domain-to-Unicode behavior and rejects valid hosts accepted by pinned Pi's primitive. | **STILL_OPEN** |
| `L12-PY-R004` | `wait()` is exit-only again, but the replacement eager/unconfirmed cause flag reports `aborted` even when the dispatched kill never executes and the child exits naturally, contradicting the approved first-actual-kill classification. | **STILL_OPEN** |
| `L12-PY-R001/R003/R005/R006/R007` | Scoped regression evidence remains green; no touched dependency invalidated their provisional closures. | **PROVISIONALLY_CLOSED (retained)** |

## L12-PY-R002 — the IDNA replacement is not WHATWG-compatible

**Taxonomy:** `PI_PARITY_DEFECT`  
**Status:** `STILL_OPEN`

Pinned Pi delegates `file://` conversion to Node's `fileURLToPath`, whose URL host processing uses
the WHATWG/ICU domain-to-Unicode behavior. The candidate substitutes Python's built-in `idna`
codec and states that RFC 3492 Punycode makes it equivalent. That is not sufficient: Punycode is
only the encoding algorithm; the surrounding IDNA processing and validation profiles differ.

Minimal executable witness, run against Node 22 and the exact candidate:

```text
input
    file://xn--fa-hia.de/share

Node fileURLToPath(..., {windows: true})
    \\faß.de\share

candidate _file_url_to_path with Windows mode
    ValueError: file:// URL host is not a valid hostname: 'xn--fa-hia.de'
```

Additional valid Node cases rejected by the candidate were
`file://xn--strae-oqa.de/share` -> `\\straße.de\share` and
`file://xn--zca/share` -> `\\ß\share`. The existing `bücher` witness exercises only an A-label
accepted by both profiles and therefore cannot establish WHATWG compatibility.

This is discriminating: a standards-faithful implementation accepts and decodes the valid A-label;
the candidate falls through to ordinary lexical-path handling at the public `resolve_local_path`
boundary. A finite table that omits valid labels cannot close the adopted direct-Pi surface.

Minimal correction: use a WHATWG-compatible host parser/domain-to-Unicode implementation, or
implement the complete adopted host algorithm with permanent positive and negative witnesses that
distinguish it from Python's legacy built-in IDNA profile. Preserve the raw-backslash witnesses,
which now pass.

## L12-PY-R004 — eager intent is not actual kill causation

**Taxonomy:** `CONTRACT_ASSURANCE_DEFECT`  
**Status:** `STILL_OPEN`

The candidate correctly restores the contract's exit-only settlement property: `wait()` no longer
awaits the watcher or kill helper. It then replaces confirmed causation with an eager
`_kill_cause = "signal"` write before the fire-and-forget kill runs. That contradicts the approved
Minion `ctx.subprocess` contract in `spec/execution.md` §6.4:

```text
If terminate and the spawn signal race, whichever caused the actual kill first determines
classification; an operation that did not cause the kill cannot overwrite that classification.
```

The candidate's own new test is the minimal witness:

```text
setup
    child exits naturally with code 0
    spawn signal fires first
    mocked _kill_process_tree waits forever and therefore never kills anything

actual process outcome
    natural exit; signal kill never executed

candidate observation
    Err(aborted)

contract observation
    Ok(ExitStatus{exit_code: 0})
```

The test currently asserts the candidate's `Err(aborted)` result, so it permanently codifies the
opposite of the contract's actual-cause rule. Pinned Pi's `Shell.exec()` reactive
`abortSignal.aborted` check cannot silently replace this rule: `ctx.subprocess` is a separately
approved Minion extension, and its causal classification was explicitly specified to support both
signal-triggered cancellation and explicit `terminate()` on the same lower-level process seam.

Minimal correction: preserve exit-only `wait()` settlement while atomically determining whether
the signal path actually won process termination. Do not await auxiliary confirmation after exit,
and do not treat intent to kill as proof that a kill occurred. Permanent evidence must retain the
never-returning-helper prompt-settlement witness but expect the natural exit, plus cover a genuine
signal kill and an explicit-terminate/signal race.

If the project instead intends to replace the approved causal rule with Pi Shell's simpler
reactive classification, that is a shared-contract change to a Minion extension and must go back
through contract/governance review; it cannot be introduced as an implementation-only correction.

## Retained provisional closures

Scoped inspection and the warning-promoted execution suite found no regression to:

- R001 filesystem cancellation witnesses;
- R003 mounted subprocess dispatch;
- R005 decoded callback behavior;
- R006 pre-spawn abort mapping;
- R007 post-wait exact payload draining and warning-clean resource ownership.

Their earlier provisional closures remain valid.

## Fresh targeted gates

```text
warning-promoted execution suite
    PASS: 217 tests, 4 platform skips, zero promoted warnings

uv run ruff check .
    PASS

uv run mypy
    PASS: 79 source files

schema + manifest validation
    PASS: 213 tests
```

Green tests do not override the direct Node counterexample or the test that asserts behavior
opposite to the approved subprocess contract.

## Verdict

```text
CE-L12-PY-01-01
    ACTIVE

open findings
    L12-PY-R002
    L12-PY-R004

provisionally closed
    L12-PY-R001
    L12-PY-R003
    L12-PY-R005
    L12-PY-R006
    L12-PY-R007

Python Layer 12
    NOT CERTIFIED

Rust Layer 12
    CERTIFIED / unchanged

Layer 12 cross-language
    NOT CLOSED

Layer 13
    NOT STARTED
```

Return R002/R004 to the Python owner within the same convergence episode. Revise the convergence
checkpoint before another implementation pass. Do not transition to final complete review or
begin Layer 13.
