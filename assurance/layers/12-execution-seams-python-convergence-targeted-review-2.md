# Layer 12 Python convergence targeted closure review 2

Mode: targeted convergence closure review (`agent-workflow.md` §11.8.7)

Verdict: **REJECTED — CONVERGENCE REMAINS ACTIVE**

## Exact target

- convergence episode: `CE-L12-PY-01-01`
- Python candidate: `EGAILab/minion-agent` PR #44 at
  `81a7e10412c1fe718286324f59f8c60224505a59`
- predecessor: `6ef45734dbeccabdfe1f9fd07ca9f367ed9929e7`
- prior targeted evidence:
  `assurance/layers/12-execution-seams-python-convergence-targeted-review.md` at
  `761bef5ee4a33e00b8d231af3cce42419c6c61b2`
- revised checkpoint/implementation record: issue #39 comment `5745837535`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`

The exact PR head was fetched from GitHub and reviewed in a clean detached worktree. The scope was
R002/R004, dependencies touched by those fixes, and regression of the five provisionally closed
findings. This was not a complete final review. No candidate, shared, Rust, or Layer-13 file was
modified.

## Closure ledger

| Finding | Result | Status |
|---|---|---|
| `L12-PY-R002` | The new table closes the previously named percent cases, but the implementation explicitly omits observable WHATWG URL behavior and differs from live Node. | **STILL_OPEN** |
| `L12-PY-R004` | Delayed true/false classification works only by blocking `wait()` on the kill helper, contradicting exit-only settlement and hanging when confirmation does not return promptly. | **STILL_OPEN** |
| `L12-PY-R001/R003/R005/R006/R007` | Scoped regression evidence remains green; no touched dependency invalidated their provisional closures. | **PROVISIONALLY_CLOSED (retained)** |

## L12-PY-R002 — known WHATWG behavior remains omitted

**Taxonomy:** `PI_PARITY_DEFECT`  
**Status:** `STILL_OPEN`

The revised helper is substantially broader, but its own docstring discloses two intentional
omissions: Node's domain-to-Unicode host processing and WHATWG raw-backslash normalization. These
are observable inputs to pinned Pi's direct `fileURLToPath` call. No governance source approves a
narrower parity surface, and a checkpoint cannot declare known Pi behavior out of scope merely
because it was absent from the previous witness list.

Live Windows comparisons:

```text
input: file://xn--bcher-kva/share
Node fileURLToPath: \\bücher\share
candidate:          \\xn--bcher-kva\share\

input: file://host\share\file
Node fileURLToPath: \\host\share\file
candidate:          <cwd>\file:\host\share\file
```

The candidate also frames its hand-written helper as a characterized port while relying on a
finite table rather than the actual WHATWG parser already required by the contract. This repeats
the root problem that produced the preceding rounds: each table expansion leaves adjacent parser
behavior unowned.

Minimal correction: use a standards-faithful WHATWG URL implementation and then perform the
platform-specific file-URL conversion, or characterize and implement the complete adopted parsing
surface without exclusions. Add the two witnesses above and negative controls. If the owner wants
to narrow direct Pi parity instead, that is an intentional divergence requiring explicit
governance—not an implementation checkpoint decision.

## L12-PY-R004 — `wait()` no longer settles on process exit alone

**Taxonomy:** `CONTRACT_ASSURANCE_DEFECT`  
**Status:** `STILL_OPEN`

The approved subprocess contract explicitly states that `wait()` settles on the process's own exit
alone. The new implementation instead awaits `_watch_signal` after the process has exited. If that
watcher is awaiting a slow or stuck kill-confirmation helper, an already-exited process's `wait()`
does not settle.

A deterministic witness made the kill attempt enter and remain pending, then released natural
exit code `0`:

```text
process exit observed                         YES
kill confirmation pending                    YES
candidate wait() after process exit          TIMEOUT
contract requirement                         settle from process exit alone
```

The new delayed-false test explicitly asserts that `wait()` must remain pending until the helper is
released. It therefore codifies the opposite of the normative exit-only rule. On Windows the real
taskkill helper itself has bounded waits, so this can add seconds of unrelated latency even without
a synthetic permanently-stuck helper.

Minimal correction: model process exit and signal termination as one coordinated race so the
winner determines classification without either (a) reading an unresolved eager cause or (b)
blocking an already-observed natural exit on auxiliary kill confirmation. Permanent evidence must
cover delayed true, delayed false, and confirmation that never returns promptly, while preserving
exit-only settlement.

## Retained provisional closures

Scoped regression checks found no change to:

- R001 filesystem cancellation witnesses;
- R003 mounted subprocess dispatch;
- R005 decoded callback behavior;
- R006 pre-spawn abort mapping;
- R007 post-wait exact payload draining and warning-clean resource ownership.

Their provisional closures remain recorded at the earlier exact SHAs.

## Fresh targeted gates

```text
warnings-promoted execution suite
    PASS: 213 tests, 4 platform skips, zero promoted warnings

uv run ruff check .
    PASS

uv run ruff format --check .
    FAIL: the same 7 pre-existing files outside this candidate would be reformatted

uv run mypy
    PASS: 79 source files

schema + manifest validation
    PASS: 213 tests
```

Green candidate tests do not override the two direct counterexamples, and one candidate test now
asserts behavior contrary to the normative contract.

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

Return R002/R004 to the Python owner within the same convergence episode. The convergence
checkpoint must be revised again before implementation. Do not transition to final complete review
or begin Layer 13.
