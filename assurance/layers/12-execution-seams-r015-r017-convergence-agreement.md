# Layer 12, WP-12.1 — `L12-R015`–`L12-R017` convergence characterization challenge and agreement

**Episode:** `CE-L12-01-03`
**Trigger:** `agent-workflow.md` §11.8.8 Case B — the second mandatory final complete review
(`minion-agent-docs#114` @ `2b5f333`, `assurance/layers/12-execution-seams-final-contract-review-2.md`)
found three new blockers coupled to, and in places invalidating, the settled `CE-L12-01-01`/
`CE-L12-01-02` matrices.
**This document performs:** the §11.8.4 challenge pass against that review's own characterization,
and records the §11.8.5 `AGREED FOR IMPLEMENTATION` checkpoint for `CE-L12-01-03`.
**Candidate this episode is about:** code `88cf0b4564262cddf2aa5fe1a2de66cbe5dfa99e` (PR #40), docs
`a4eb07c764ea8006c867f574475779c9fcfa78ae` (PR #110) — REJECTED at the final-review stage; neither
is changed by this document. The coherent fix pass (§11.8.6) is a separate, later step. `L12-R001`
through `L12-R014` remain historically/provisionally closed for the exact issues they addressed;
this episode concerns only the three new findings.

---

## 1. Independent re-verification of the characterization

Every claim in the review was independently re-checked against pinned Pi source
(`b7bb00b936dbe21b8e160b3e89efdec361846699`) and the actual candidate text before being accepted.
All are confirmed correct.

- **`L12-R015` `EXEC-001` result/exception contradiction**: independently re-read the manifest's
  own `EXEC-001` row. Confirmed it still states "every ctx.fs/ctx.shell operation returns
  Result[T, E], never raises/rejects, including for unexpected backend failures," immediately
  followed by an Exceptions list that includes "an unnormalized backend exception escaping a seam
  (itself a provider bug)" — the same universal-vs-scoped contradiction `L12-R004` found and fixed
  in `design/2026-08-20-minion-agent-design.md` §7. That earlier fix touched ONLY the design
  document; `EXEC-001`'s own independent copy of the identical claim was never checked or
  corrected. Confirmed a genuine gap in my own prior remediation, not a re-opening of `L12-R004`'s
  own settled substance (`spec/execution.md` §2 itself was, and remains, correctly scoped).
- **`L12-R016` `FsTarget` contradiction and incompleteness**: independently re-read
  `design/2026-08-20-minion-agent-design.md` §7's bridge bullets directly: "`resolve(path) ->
  FsTarget` returns an opaque `target_key`. The same file reached by different paths yields the
  same key" and "`process_path(target)` returns the canonical path." Confirmed both contradict the
  settled location-key model: a rename changes the key for the SAME underlying file (violates "the
  same file... yields the same key"); two hard links to the same underlying file have different
  canonical paths and therefore different keys (also violates it); a missing-path key is the
  lexical `absolute_path`, not a canonical path (violates "returns the canonical path"). This
  design-doc text was NEVER touched during the `L12-R005`/`CE-L12-01-01` remediation, which
  corrected only `spec/execution.md` §4 and `EXEC-003`. Independently re-read
  `file-mutation-queue.ts:20-26` (`getMutationQueueKey`) again: confirmed the fallback from
  `canonicalPath` to `absolutePath` fires ONLY for error codes `not_found` or `not_supported`; any
  other `canonicalPath` error (e.g. `permission_denied`) is re-thrown, not silently absorbed. The
  candidate's own "canonical path if it exists, else absolute path" / "when canonicalization
  fails" wording does not commit to this exact condition set, confirmed a genuine specification
  gap (three mutually different Rust implementations could all satisfy the current prose).
  Confirmed `resolve(path, signal?)`'s own cancellation behavior is never stated, even though its
  two constituent operations (`absolute_path`, `canonical_path`) are both in the
  accepts-but-does-not-inspect group (§3.1) — a caller has no stated answer for a pre-aborted
  `resolve()` call.
- **`L12-R017` local-provider parity/cleanup incoherence**: independently re-read
  `spec/execution.md` §8: "**DIRECT_PI_PARITY** for observable behavior (§3-§6 above...)" —
  confirmed this blankets §6 (`ctx.subprocess`) despite §6's own text and `EXEC-005` explicitly
  stating `ctx.subprocess` is `MINION_EXTENSION` with NO direct Pi seam at all. A genuine, direct
  contradiction within the same document. Independently re-read `nodejs.ts:691-694`
  (`NodeExecutionEnv.cleanup()`): confirmed it kills every PID in `activeChildPids` and clears the
  set; independently re-read `nodejs.ts:429` confirming `exec()`'s own spawned child IS added to
  that SAME tracking set (`this.activeChildPids.add(child.pid)`) — so in Pi's own COMBINED
  environment, `cleanup()` observably terminates in-flight shell commands too. Confirmed the
  candidate's current cleanup ownership does not reproduce this: `ctx.shell`'s own `cleanup()` is
  specified only as "best-effort, must not raise," with no requirement to kill active commands;
  `ctx.subprocess` has no provider-level `cleanup()` at all (only per-`Process`
  `wait()`/`terminate()`, a deliberately different, already-settled concern from `CE-L12-01-01`);
  `ctx.fs`'s own §3.8 describes killing active child PIDs, misattributing Pi's combined behavior to
  the WRONG split provider. Independently re-read `nodejs.ts:495` confirming the exact
  `exitCode: code ?? 0` normalization: a process killed by `cleanup()` (no abort signal, no
  timeout involved) settles its own in-flight `exec()` call as SUCCESS with `exit_code` normalized
  from a null/signal-killed exit code to `0` -- not an error of any kind, since cleanup-triggered
  termination does not pass through the `aborted`/`timeout` classification machinery at all.

No part of the characterization is rejected. All three findings are confirmed as characterized.

## 2. Challenge pass (`agent-workflow.md` §11.8.4)

**Is the Pi source mapping correct?** Yes, independently confirmed above for `L12-R016`/`L12-R017`
(Pi-sourced). `L12-R015` is a candidate-internal consistency defect (the design-doc half was
already fixed; the manifest half was missed) rather than a fresh Pi-source question.

**Is the behavior matrix complete enough to distinguish realistic wrong implementations?** Yes —
each finding's own minimal-correction/witness proposal names a concrete discriminator (an
unnormalized-invariant-failure documentary contrast for `L12-R015`; hard-link/rename witnesses and
an exact fallback-condition stub-provider matrix for `L12-R016`; a cleanup-kills-active-command
witness with the exact `exitCode ?? 0` settlement for `L12-R017`).

**Are any cases implementation mechanics rather than observable semantics?** No — every finding
concerns an OBSERVABLE outcome (which classification a caller sees, which `target_key` two
resolves produce, whether an in-flight command dies on cleanup), not a language-specific mechanism.

**Does any proposed fix silently reopen a lower certified layer?** No. Confirmed by scope: every
fix is confined to `EXEC-001`/`EXEC-003`/`EXEC-005`/`EXEC-008`(local providers, folded into the
relevant rows), `spec/execution.md` §§2/4/8, and `design/2026-08-20-minion-agent-design.md` §7's
bridge bullets. No certified Runtime/LLM/Session/Tool/Agent/Auth surface is touched.

**Can both Python and Rust implement the rule idiomatically?** Yes for all three — a scoped
error/exception boundary, an exact fallback-condition set, and a provider-level `cleanup()` method
that iterates and kills tracked child processes are all ordinary typed-code patterns in both
languages.

**Does the defect's root cause depend on an extensibility point one language's certified lower
layer exposes and the other does not?** No — same footing in both languages.

**Are all previous review findings represented by an executable or documentary acceptance
criterion?** Yes — §5 below states one for each of `L12-R015`–`L12-R017`.

## 3. Design decisions

### 3.1 `L12-R015` — sync `EXEC-001` with the already-settled error/exception boundary

**Decision:** apply the SAME scoping correction already made to
`design/2026-08-20-minion-agent-design.md` §7 (`L12-R004`) to `EXEC-001`'s own independent copy of
the claim, which was never checked during that earlier fix. `EXEC-001` now states: an execution
seam normalizes every EXPECTED operational/environmental failure into a typed `Result` error
(matching `spec/execution.md` §2, unchanged and already correct); an unexpected OPERATIONAL backend
failure that has no narrower mapping still normalizes, to `unknown` (this is what pinned Pi's own
`toFileError` does for any unrecognized errno — normalization, not exception); a broken provider
invariant, an impossible state transition, an assertion failure, or a programming error remains an
exception/panic, INCLUDING when it originates from within a seam provider's own implementation. The
distinction is OPERATIONAL (however unexpected) vs. INVARIANT/PROGRAMMING, not "expected" vs.
"unexpected" alone -- an unexpected operational failure is still operational.

### 3.2 `L12-R016` — align the frozen design's bridge description; exact fallback condition; `resolve()` cancellation

**Decision (design-doc alignment, narrow citation-accuracy correction, matching the established
`L12-R003`/`L12-R004` precedent -- no fresh owner escalation, per `agent-workflow.md` §11.10 and
Layer 11 Pass 2 Slice C's `L11-SC-R026`):** correct
`design/2026-08-20-minion-agent-design.md` §7's bridge bullets to match the settled location-key
model, preserving the owner-approved bridge MECHANISM (an opaque `target_key` plus
`process_path`) unchanged -- only the characterization of what `target_key` identifies changes:

```text
"The same file reached by different paths yields the same key"
    -> "The same RESOLVED LOCATION yields the same key -- two syntactically different paths that
       resolve to the same location (a relative path and its absolute form; a symlink and its
       target) share a key, but a rename or a hard link is a DIFFERENT location even when a POSIX
       filesystem considers the underlying file the same resource."

"process_path(target) returns the canonical path a subprocess... can open"
    -> "process_path(target) returns the path a subprocess in this provider's execution world can
       open to reach the target's own resolved location -- canonical once the resource exists,
       lexical-absolute for a not-yet-existing target's own future location."
```

**Decision (exact fallback condition, `spec/execution.md` §4 / `EXEC-003`):** `target_key`'s
derivation states the EXACT pinned-Pi-matching condition set, not an approximation:
`canonical_path(path)` is used when it succeeds; `absolute_path(path)` is used ONLY when
`canonical_path` fails with `not_found` or `not_supported`; any OTHER `canonical_path` failure
(`permission_denied`, `invalid`, `not_directory`, `is_directory`, `unknown`) PROPAGATES as
`resolve()`'s own `FsError` -- `resolve()` does NOT silently fall back to `absolute_path` for those
cases, matching pinned Pi's own `getMutationQueueKey` exactly (which re-throws for any other
error).

**Decision (`resolve()` cancellation):** `resolve(path, signal?)` is in the accepts-but-does-not-
inspect group (§3.1) -- consistent with, and a direct consequence of, both operations it composes
(`absolute_path`, `canonical_path`) already being in that same group. No new cancellation behavior
is introduced by composing them.

### 3.3 `L12-R017` — local-provider parity classification and cleanup ownership

**Decision (parity classification, `spec/execution.md` §8):** replace the blanket "DIRECT_PI_PARITY
for observable behavior (§3-§6 above)" with a per-seam-accurate statement: DIRECT_PI_PARITY for the
`ctx.fs` (§3) and `ctx.shell` (§5) local providers' observable behavior, each genuinely sourced
from pinned Pi's reference implementation; MINION_EXTENSION for the `ctx.subprocess` (§6) local
provider, matching its own already-correct `EXEC-005` disposition (`intentional divergence`) --
the local subprocess provider does not acquire direct-Pi status merely because its primitive set
was informed by Pi's combined shell implementation's own process-management internals.

**Decision (cleanup ownership):** reassign active-process-tracking/killing to `ctx.shell`'s own
`cleanup()`, matching pinned Pi's real combined behavior (its `exec()`-spawned children share the
SAME `activeChildPids` tracking `cleanup()` iterates). `ctx.shell.cleanup()` MUST kill the process
tree of every command this provider instance currently has in flight (tracked internally by this
provider, independent of `ctx.subprocess`'s own per-`Process` disposal, which remains the
already-settled, unrelated caller-owned mechanism from `CE-L12-01-01`) and clear its own tracking;
like all `cleanup()` methods in this contract, it is best-effort and MUST NOT raise. A killed
in-flight `exec()` call does NOT go through the `aborted`/`timeout` classification machinery (§5.4)
at all -- no signal fired, no timeout elapsed -- so it settles through the SAME exit-handling path
an ordinary process exit would, with a killed (signal-terminated, null-exit-code) process's own
`exit_code` normalized to `0`: the caller observes `Ok({stdout, stderr, exit_code: 0})`, not an
error. `ctx.fs.cleanup()` is corrected to make NO child-process-killing claim at all (removing the
misattributed behavior from §3.8) -- it remains best-effort/must-not-raise for whatever the
filesystem provider itself tracks, which is currently nothing beyond the never-throw contract
itself. `ctx.subprocess` gains no new provider-level `cleanup()` method -- its own disposal model
(explicit `wait()`/`terminate()` per `Process`, no implicit provider-wide sweep) was deliberately
settled in `CE-L12-01-01` and is unaffected by this decision.

## 4. Observable behavior matrix (new dimensions this episode settles)

```text
Error/exception boundary consistency across EXEC-001, the frozen design, and spec/execution.md --
    all three documents must state the SAME operational-vs-invariant distinction, not merely two
    of the three
FsTarget resolved-location framing, consistent between the frozen design and the settled
    spec/manifest location-key model
target_key fallback EXACT condition set (not_found/not_supported only) vs. propagation for any
    other canonicalization failure
resolve()'s own cancellation classification, explicitly stated rather than left to inference
Local-provider parity classification per seam (fs/shell direct-parity, subprocess Minion
    extension), not one blanket statement across all three
Cleanup ownership and settlement: which provider's cleanup() kills which tracked processes, and
    the exact non-error settlement (exit_code: 0) a cleanup-killed in-flight shell command produces
```

## 5. Acceptance witnesses (one per finding, discriminating)

```text
L12-R015  setup: a seam provider's own internal invariant is violated (a genuine provider bug),
          and it throws/panics before producing an operational FsError/ShellError/SubprocessError
          reader A: follows EXEC-001's own (now-corrected) universal sentence literally
          reader B: follows EXEC-001's own adjacent exceptions list
          expect: both readers now reach the SAME conclusion (exception, not Result) -- EXEC-001,
          the frozen design, and spec/execution.md section 2 all state the identical boundary
          negative control: a candidate whose EXEC-001 text still reads as a universal "every
          failure becomes Result" claim fails this witness even if section 2 is correct

L12-R016  setup: file.txt and hardlink.txt, two hard links to the SAME underlying inode; resolve
          both
          expect: DIFFERENT target_key values (different canonical paths) -- confirming the
          design doc's own corrected text ("different LOCATIONS... even when... the same
          resource") and NOT the pre-correction "same file... same key" claim
          second setup: canonical_path(missing/path) failing with permission_denied (not
          not_found/not_supported)
          expect: resolve() returns Err(FsError(permission_denied)) -- it does NOT silently fall
          back to absolute_path for this error code
          third setup: resolve(path, signal) with a pre-aborted signal, on an EXISTING path
          expect: Ok(FsTarget{...}) -- resolve() accepts signal but does not inspect it, matching
          its own constituent operations
          negative control: a candidate falling back to absolute_path on ANY canonicalization
          error (not just not_found/not_supported) fails the second case; a candidate returning
          Err(aborted) on the third case fails that one

L12-R017  setup: shell.exec() in flight (no timeout, no external abort signal fired); caller calls
          shell.cleanup() while it is still running
          expect: the in-flight process tree is killed; the exec() call itself settles
          Ok({stdout, stderr, exit_code: 0}) -- NOT Err(aborted), NOT Err(timeout) -- because
          cleanup-triggered termination never sets the abort signal or fires the timeout
          second setup: read section 8's own parity claim for ctx.subprocess (section 6) side by
          side with EXEC-005's own disposition
          expect: both now say MINION_EXTENSION/intentional divergence -- no remaining blanket
          DIRECT_PI_PARITY claim covering ctx.subprocess
          negative control: an implementation whose shell.cleanup() is a true no-op leaves the
          command running, failing the first case; a candidate still claiming DIRECT_PI_PARITY for
          section 6 in section 8's own text fails the second case
```

## 6. Normative deltas required (coherent fix pass, next step -- not performed by this document)

```text
design/2026-08-20-minion-agent-design.md section 7
    -- narrow factual correction only, preserving the owner-approved FsTarget bridge mechanism:
       replace the "same file... same key" and "returns the canonical path" bridge bullets with
       the resolved-location framing in section 3.2 above. No fresh owner escalation required,
       matching established precedent (L11-SC-R026, and this same episode's own L12-R003/L12-R004
       precedent within Layer 12 itself).

spec/execution.md
    -- section 2 / new subsection: no change needed (already correctly scoped); cross-reference
       EXEC-001's own correction so both documents are explicitly kept in sync;
    -- section 4: state the exact not_found/not_supported-only fallback condition and the
       resolve() cancellation classification from section 3.2 above;
    -- section 3.8: remove the child-process-killing claim from ctx.fs's own cleanup(); state it
       makes no such claim;
    -- section 5 / new subsection: add ctx.shell's own cleanup()-kills-active-commands MUST rule
       and its exact non-error settlement, from section 3.3 above;
    -- section 8: replace the blanket DIRECT_PI_PARITY statement with the per-seam-accurate one
       from section 3.3 above;
    -- section 9: add a round-4/CE-L12-01-03 remediation record entry;
    -- section 10: extend the witness matrix with section 5 above's entries.

pi-parity-manifest.yaml
    -- EXEC-001: rule text corrected to the scoped operational-vs-invariant boundary (section 3.1
       above);
    -- EXEC-002: section 3.8's cleanup correction reflected in EXEC-002's own cleanup description;
    -- EXEC-003: rule text updated with the exact fallback condition and resolve() cancellation
       (section 3.2 above);
    -- EXEC-004: rule text updated with ctx.shell's own cleanup()-kills-active-commands rule
       (section 3.3 above);
    -- local-provider row(s) (wherever section 8's disposition is mirrored, if at all): corrected
       to the per-seam-accurate parity classification.
```

## 7. Convergence contract

```text
CONVERGENCE CONTRACT
    AGREED FOR IMPLEMENTATION

EPISODE
    CE-L12-01-03

OPEN FINDINGS
    L12-R015 L12-R016 L12-R017

ACCEPTANCE WITNESSES
    section 5 above (one per finding)

NORMATIVE DELTAS
    design/2026-08-20-minion-agent-design.md section 7 (factual correction only)
    spec/execution.md sections 3.8, 4, 5, 8, 9, 10
    pi-parity-manifest.yaml EXEC-001, EXEC-002, EXEC-003, EXEC-004

NEXT_OWNER
    Claude (coherent fix pass, agent-workflow.md section 11.8.6)
```

This checkpoint means the remaining observable surface is sufficiently characterized for one
coherent implementation-of-the-contract pass -- it is NOT final contract approval. A targeted
closure review (`agent-workflow.md` §11.8.7) of the resulting exact candidate, with the negative-
control evidence required by §11.8.7.1, remains mandatory before another `FINAL_CONTRACT_REVIEW`.
No Python or Rust Layer 12 implementation, and no Layer 13 work, is authorized by this document.
