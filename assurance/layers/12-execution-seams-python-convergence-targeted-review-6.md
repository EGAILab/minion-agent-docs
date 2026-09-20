# Layer 12 Python convergence targeted closure review 6

Mode: targeted finding-closure review (`agent-workflow.md` section 11.8.7)

Verdict: **REJECTED — L12-PY-R002 REMAINS OPEN**

## Exact target

- Python implementation PR: `EGAILab/minion-agent#44`
- reviewed Python SHA: `a7dcd65192176d6405dd4464e85075c5741379ac`
- companion docs PR: `EGAILab/minion-agent-docs#121`
- reviewed docs SHA: `36a88f14f5e96c587ed9723c6d9fb09c2be52c1b`
- agreed checkpoint SHA: `2db656c01126bfb775d1fe453241e191ed78b2f0`
- checkpoint approval evidence: `EGAILab/minion-agent-docs#120` at
  `80bbf9d8dd0a117826d39aff706e863558cd76fb`
- certified Rust baseline, read-only: `2b309ee8cecbc333a7965781087677bd6cbba46b`
- pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`

The coordination issue was open and valid, assigned `NEXT_OWNER = Codex`, and recorded the same
remote-reachable PR heads. Both candidate PRs were open, ready for review, and unmerged. No Python,
shared-contract, or Rust implementation was modified by this review. Layer 13 was not started.

## Targeted result

```text
L12-PY-R002
    STILL OPEN — PI_PARITY_DEFECT

L12-PY-R004-A
    PROVISIONALLY CLOSED

previous provisional closures R001/R003/R005/R006/R007
    RETAINED

R004-B and Rust EXEC-002/EXEC-003, R004-A, R004-B surfaces
    REVALIDATE_REQUIRED — unchanged, out of this review's implementation scope

ready for final complete review
    NO
```

## R004-A — provisionally closed

The production path implements the agreed deterministic first-claim model through the real
`Process` seam:

- `_watch_signal` records `signal` synchronously after observing an aborted signal while its
  latest liveness check still says running, before scheduling `_issue_kill`;
- `terminate()` records `explicit` synchronously before awaiting `_issue_kill`;
- both write only when the cause is still `None`, so the first event-loop turn to claim wins;
- kill issuance and confirmation cannot revise the stored cause;
- `wait()` classifies solely from the stored claim and remains independent of confirmation.

The updated language tests exercise failed and indefinitely delayed kill issuance through the
real `wait()` API and now assert the agreed `Err(aborted)` result. The complete focused filesystem
and subprocess test set passed on the reviewed candidate (`154 passed, 4 platform-gated skips` on
this Windows review host). `spec/execution.md` now states the first-claim model without changing
the retained process-exit-only settlement rule.

The prior contrary issuance-success tests were correctly replaced because they encoded the
superseded, stricter-than-agreed model rather than valid regression behavior.

## L12-PY-R002 — still open

**Classification:** `PI_PARITY_DEFECT`  
**Severity:** blocking

The agreed checkpoint retained Model A: the supported Node `fileURLToPath` behavior delegated to
by pinned Pi is the general oracle; the 65-case corpus is representative and explicitly
non-exhaustive. Passing those 65 rows therefore cannot close a known mismatch elsewhere in the
same accepted input domain.

The candidate itself discloses a not-yet-differentially-verified class: hosts that become
non-ASCII through percent decoding. Independent probes of that class expose observable mismatches,
not merely an unobservable intermediate Punycode round trip.

### Discriminating witness W-R002-RESET-1

```text
finding
    L12-PY-R002

Pi/source basis
    pinned Pi resolvePath delegates file:// conversion to Node url.fileURLToPath;
    supported floor Node v22.19.0 is the agreed executable oracle

minimal inputs
    file://%E2%98%83.com/share       # percent-encoded U+2603 SNOWMAN host
    file://%F0%9F%92%A9.com/share   # percent-encoded U+1F4A9 host

Node v22.19.0 expected/observed
    \\☃.com\share
    \\💩.com\share

Node v22.23.2 drift check
    identical outputs

candidate a7dcd651 observed
    both inputs raise ValueError from _file_url_to_path

why discriminating
    a conforming delegated-WHATWG implementation accepts both and returns a UNC path;
    the candidate's ada_url plus strict idna.decode composition rejects both before a path
    can be returned
```

The existing invalid-A-label controls remain important and must not regress:
`xn--abc-ppe` and `xn--abc-jdc` remain rejected. The defect is not solved by removing all host
validation.

The manifest currently embeds this acknowledged, unfixed class inside adopted row `EXEC-002` and
calls it only an unverified intermediate round trip. The witness above disproves that description:
the current difference is observable and is not authorized as an intentional divergence.

## Required narrow remediation

1. Extend the permanent differential corpus/evidence with both exact witnesses above, using Node
   v22.19.0 as primary oracle and v22.23.2 as the drift check.
2. Correct the URL/IDNA composition so both witnesses produce Node's exact UNC outputs while the
   existing malformed-host, Bidi, leading-combining-mark, IPv4, IPv6, encoded-separator, and
   fallback witnesses remain unchanged.
3. Add direct Python regression tests for the two accepted percent-decoded Unicode hosts and
   negative controls retaining the invalid-A-label rejections.
4. Remove the manifest/docstring claim that this is merely a characterized, unfixed but
   observably identical divergence. `EXEC-002` may remain `adopted` only when the observable
   mismatch is closed.
5. Demonstrate the exact new witnesses fail against reviewed SHA `a7dcd651...` and pass on the new
   candidate, then return only R002 for another targeted closure review.

No checkpoint reset is required yet: this is the first targeted closure review against the newly
approved reset checkpoint, and that checkpoint already selected full Node/Pi compatibility and
explicitly permitted additional oracle probes beyond the finite corpus. This is an implementation
and evidence failure against the agreed model, not a new semantic choice.

## Gates run

```text
focused Python tests
    tests/execution/test_filesystem.py + test_subprocess.py
    154 passed, 4 skipped, 0 failed

committed comparison matrix
    65 comparable rows
    Python 65/65
    Rust 48/65

additional Node/Python witness
    Node v22.19.0: accepts both Unicode-host cases
    Node v22.23.2: identical
    Python candidate: rejects both
```

The extra witness, rather than a failure in the finite table, is the blocker.

## Stop state

```text
Python Layer 12
    NOT CERTIFIED

L12-PY-R004-A
    PROVISIONALLY CLOSED

L12-PY-R002
    OPEN

Rust affected surfaces
    REVALIDATE_REQUIRED

Layer 12 cross-language
    NOT CLOSED

Layer 13
    NOT STARTED
```

Return the narrow R002 remediation to Claude. Do not modify Rust and do not begin final complete
review until R002 is provisionally closed on an exact candidate.
