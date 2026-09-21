# Layer 12 Python convergence targeted closure review 5

Mode: targeted convergence closure review (`agent-workflow.md` §11.8.7)

Verdict: **REJECTED — CONVERGENCE REMAINS ACTIVE**

## Exact target

- convergence episode: `CE-L12-PY-01-01`
- Python candidate: `EGAILab/minion-agent` PR #44 at
  `d44ea0e2b46e18997a425e514c7ab8f458642f7d`
- predecessor: `cf38945495bdd102842d2bf2900d3ca7b960a248`
- prior targeted evidence:
  `assurance/layers/12-execution-seams-python-convergence-targeted-review-4.md` at
  `a404c612063ae719a0436872affe06f71f9d49d9`
- revised checkpoint/implementation record: issue #39 comment `5748375359`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`

The exact PR head was fetched from GitHub into a clean detached worktree and reviewed against
pinned Pi and the approved Layer-12 contract. Scope was R002/R004, dependencies touched by those
fixes, the newly explicit `idna` dependency, and regression of the five provisionally closed
findings. This was not a complete final review. No candidate, shared, Rust, or Layer-13 file was
modified.

## Closure ledger

| Finding | Result | Status |
|---|---|---|
| `L12-PY-R002` | The third-party library closes the two supplied invalid-A-label cases, but whole-domain strict IDNA validation rejects ordinary ASCII labels that Node accepts whenever a neighboring label is punycoded; other whole-host WHATWG behavior also still differs. | **STILL_OPEN** |
| `L12-PY-R004` | `_KillIssue.issued` distinguishes helper-spawn failure, but successful helper spawn/syscall issuance is still treated as actual kill causation even when it has no effect and the child exits naturally. | **STILL_OPEN** |
| `L12-PY-R001/R003/R005/R006/R007` | Scoped regression evidence remains green; no touched dependency invalidated their provisional closures. | **PROVISIONALLY_CLOSED (retained)** |

## L12-PY-R002 — strict whole-domain IDNA is not WHATWG URL host parsing

**Taxonomy:** `PI_PARITY_DEFECT`  
**Status:** `STILL_OPEN`

Using the third-party `idna` package correctly closes the bidi-invalid and leading-combining-mark
A-label examples. The candidate calls `idna.decode(host)` on the entire dotted host whenever any
label starts with `xn--`. That applies strict IDNA validation to neighboring ordinary ASCII labels,
while Node's WHATWG URL host parser permits several such labels and decodes the A-label normally.

Direct Node 22 versus exact-candidate witnesses:

```text
input: file://xn--bcher-kva._foo/share
Node:      \\bücher._foo\share
candidate: rejects / lexical fallback

input: file://xn--bcher-kva.-foo/share
Node:      \\bücher.-foo\share
candidate: rejects / lexical fallback

input: file://xn--bcher-kva..foo/share
Node:      \\bücher..foo\share
candidate: rejects / lexical fallback
```

The candidate also accepts `file://xn--bcher-kva.123/share` as a UNC hostname, while Node rejects
it (`ERR_INVALID_URL`) through whole-host numeric/IPv4 processing. These examples show that
neither bare Punycode nor strict whole-domain IDNA is the adopted WHATWG URL algorithm.

The new skip gate for hosts with no `xn--` label is a local workaround for this mismatch: it
prevents the library from over-validating `file://./share/file`, but once one punycode label is
present the same over-validation returns for every neighboring label. This is precisely the
successive-approximation failure the convergence process was meant to stop.

Minimal correction: stop treating a general IDNA decoder as the URL parser. Use a standards-
faithful WHATWG URL implementation for the complete host parse/canonicalization stage (including
domain-to-Unicode presentation required by `fileURLToPath`), or present a complete behavior matrix
and implementation rather than another local gate around one newly discovered mismatch.

## L12-PY-R004 — successful issuance is still not actual kill causation

**Taxonomy:** `CONTRACT_ASSURANCE_DEFECT`  
**Status:** `STILL_OPEN`

`_KillIssue(issued=False)` correctly closes the Windows `Popen`-raises witness. The approved
contract, however, says whichever operation caused the actual kill first determines
classification. Successfully spawning `taskkill`, or successfully issuing `killpg`, proves a
request was delivered; it does not prove that request killed the target before its natural exit or
another termination path.

Minimal executable witness against the exact candidate:

```text
setup
    _issue_kill returns _KillIssue(issued=True) but performs no kill
    child exits naturally with code 0
    spawn signal fires while child is running

candidate
    Err(aborted)

approved causal rule
    Ok(ExitStatus{exit_code: 0})
```

Observed candidate output was `Err aborted None`. This directly models a Windows helper that was
successfully spawned but reports "process not found"/otherwise has no effect; `_confirm_kill`
already observes that helper result but the candidate deliberately excludes it from
classification. Thus the new result type moves the boundary from "intent" to "request issued"
but still does not represent the contract's "actual kill" boundary.

Minimal correction: revise the convergence contract rather than add another boolean. The state
machine must preserve prompt exit-only `wait()` settlement and determine the winning actual exit/
termination cause without letting a late helper block settlement. If the selected platform
primitive cannot provide that classification, the approved Minion-extension rule itself needs an
explicit architecture/governance resolution; it cannot be silently weakened from actual causation
to successful request issuance.

Permanent evidence must include: helper spawn failure, helper successfully spawned but no target
killed, genuine signal kill, natural exit while confirmation is pending, and explicit-terminate/
signal race.

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
    PASS: 222 tests, 4 platform skips, zero promoted warnings

uv run ruff check .
    PASS

uv run mypy
    PASS: 79 source files

schema + manifest validation
    PASS: 213 tests
```

Green tests do not override the direct Node URL counterexamples or the no-effect-issued-kill
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

Return R002/R004 to the Python owner within the same convergence episode. The next checkpoint must
address the root abstractions rather than add another adjacent witness-specific patch. Do not
transition to final complete review or begin Layer 13.
