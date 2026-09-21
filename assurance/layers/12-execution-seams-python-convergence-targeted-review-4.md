# Layer 12 Python convergence targeted closure review 4

Mode: targeted convergence closure review (`agent-workflow.md` §11.8.7)

Verdict: **REJECTED — CONVERGENCE REMAINS ACTIVE**

## Exact target

- convergence episode: `CE-L12-PY-01-01`
- Python candidate: `EGAILab/minion-agent` PR #44 at
  `cf38945495bdd102842d2bf2900d3ca7b960a248`
- predecessor: `65023b5fe39d06745695a0678bb25fb876263254`
- prior targeted evidence:
  `assurance/layers/12-execution-seams-python-convergence-targeted-review-3.md` at
  `353196266b808c7a57858c948005596341ba1492`
- revised checkpoint/implementation record: issue #39 comment `5748239360`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`

The exact PR head was fetched from GitHub into a clean detached worktree and reviewed against
pinned Pi and the approved Layer-12 contract. Scope was R002/R004, dependencies touched by those
fixes, and regression of the five provisionally closed findings. This was not a complete final
review. No candidate, shared, Rust, or Layer-13 file was modified.

## Closure ledger

| Finding | Result | Status |
|---|---|---|
| `L12-PY-R002` | Bare Punycode closes the three supplied `ß` examples but omits WHATWG/UTS46 validity rules, accepting A-labels Node rejects. | **STILL_OPEN** |
| `L12-PY-R004` | Issue/confirm separation restores prompt settlement, but `_issue_kill` cannot report whether issuance occurred; `_watch_signal` records signal causation even when Windows helper spawn failed and no kill reached the OS. | **STILL_OPEN** |
| `L12-PY-R001/R003/R005/R006/R007` | Scoped regression evidence remains green; no touched dependency invalidated their provisional closures. | **PROVISIONALLY_CLOSED (retained)** |

## L12-PY-R002 — bare Punycode is not WHATWG host validation

**Taxonomy:** `PI_PARITY_DEFECT`  
**Status:** `STILL_OPEN`

The candidate correctly demonstrates why Python's IDNA2003 codec cannot implement modern Node
host decoding. It then replaces that codec with bare RFC 3492 decoding plus only an
`isprintable()` check. Punycode defines encoding/decoding; it does not implement the bidi,
combining-mark, contextual, and other validity rules applied by Node's WHATWG/ICU host parser.

Minimal live witnesses:

```text
input A
    file://xn--abc-ppe/share
decoded label
    אabc
Node fileURLToPath(..., {windows: true})
    ERR_INVALID_URL
candidate
    ACCEPT -> \\אabc\share

input B
    file://xn--abc-jdc/share
decoded label
    <leading combining acute accent>abc
Node fileURLToPath(..., {windows: true})
    ERR_INVALID_URL
candidate
    ACCEPT -> UNC path containing that label
```

The first distinguishes bidi validation; the second distinguishes the leading-combining-mark
rule. Both decoded strings are printable, so the candidate's only post-decode validity check
cannot reject them. The three added `ß` witnesses prove Punycode decoding but not WHATWG host
validity.

Minimal correction: use a WHATWG/UTS46-compatible host-processing implementation rather than
successively approximating its rules with a hand-written decoder. If implementing the whole
adopted algorithm locally remains the choice, the convergence matrix must characterize its
validation dimensions rather than adding only these two examples to another finite list.

## L12-PY-R004 — issuance failure is still classified as signal causation

**Taxonomy:** `CONTRACT_ASSURANCE_DEFECT`  
**Status:** `STILL_OPEN`

Separating `_issue_kill` from `_confirm_kill` is directionally correct: confirmation no longer
blocks exit-only `wait()` settlement. The API cannot, however, distinguish a successful POSIX
issuance from a failed Windows issuance: both return `None`. `_watch_signal` records
`_kill_cause = "signal"` unconditionally after `_issue_kill` returns.

The candidate's own Windows failure branch therefore contradicts its new causal claim:

```text
_subprocess.Popen([taskkill, ...]) raises OSError
    -> _issue_kill returns None
    -> no OS kill command was issued
    -> _watch_signal records _kill_cause = "signal" anyway
    -> child exits naturally with code 0
    -> wait() returns Err(aborted)
```

An executable platform-independent probe substituted an immediate `_issue_kill` returning
`None`, allowed the child to exit naturally, and observed exactly:

```text
Err aborted None
```

This is discriminating because the signal path provably performed no kill, while the approved
contract requires actual-kill causation. The existing unit test for the Windows `Popen` failure
checks only that `_issue_kill` returns `None`; it does not compose that outcome through
`_watch_signal` and `wait()`, so it misses the misclassification.

Even a successfully spawned `taskkill` helper is issuance, not proof that it killed the target;
the process can exit naturally before the helper acts. The convergence design must state how the
Minion extension determines the actual winner without either blocking `wait()` on auxiliary
confirmation or treating a failed/no-effect request as causation. If exact actual-cause
classification cannot be provided by the chosen OS primitive, that is a contract/architecture
question to resolve explicitly—not a condition that `None` can silently represent both ways.

Minimal correction: revise the convergence checkpoint around a result type/state machine that
does not collapse issuance failure with successful issuance and preserves exit-only settlement.
Permanent evidence must compose the Windows spawn-failure/no-issue branch through public
`wait()`, retain natural-exit-versus-hung-confirmation, genuine signal-kill, and explicit-
terminate/signal race witnesses.

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
    PASS: 219 tests, 4 platform skips, zero promoted warnings

uv run ruff check .
    PASS

uv run mypy
    PASS: 79 source files

schema + manifest validation
    PASS: 213 tests
```

Green tests do not override the direct Node counterexamples or the composed issuance-failure
counterexample.

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
