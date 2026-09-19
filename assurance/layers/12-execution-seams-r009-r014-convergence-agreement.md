# Layer 12, WP-12.1 — `L12-R009`–`L12-R014` convergence characterization challenge and agreement

**Episode:** `CE-L12-01-02`
**Trigger:** `agent-workflow.md` §11.8.8 Case B — the mandatory final complete review
(`minion-agent-docs#114` @ `c36a2ee22c990b1f829933f6b785ba7813e33210`) found six new blockers
coupled to, and in places invalidating, the settled `CE-L12-01-01` behavior matrices.
**This document performs:** the §11.8.4 challenge pass against that review's own characterization,
and records the §11.8.5 `AGREED FOR IMPLEMENTATION` checkpoint for `CE-L12-01-02`.
**Candidate this episode is about:** code `71a341802349e0c6f706d599648f8566153318eb` (PR #40), docs
`1279c0287d03a3ba42fa32d3ee6b25fc42b04e8a` (PR #110) — REJECTED at the final-review stage; neither
is changed by this document. The coherent fix pass (§11.8.6) is a separate, later step. `L12-R001`
through `L12-R008` remain historically/provisionally closed for the exact issues they addressed;
this episode concerns only the six new findings.

---

## 1. Independent re-verification of the characterization

Every claim in the final review was independently re-checked against pinned Pi source
(`b7bb00b936dbe21b8e160b3e89efdec361846699`) before being accepted, not taken on the review's own
prose. All are confirmed correct.

- **`L12-R009` filesystem cancellation checkpoints**: independently re-read `nodejs.ts:502-609`
  method by method. `readTextFile`/`readBinaryFile`: pre-check, then `signal` threaded into the
  single underlying `readFile()` call — no separate checkpoint. `writeFile` (`nodejs.ts:555-572`):
  pre-check; `await mkdir(...)` (itself NOT abort-checked); an EXPLICIT `afterMkdirAbort` check
  immediately after `mkdir` resolves and before `writeFile()` is called; `signal` also threaded
  into the `writeFile()` call itself — three distinct checkpoints, not the single "mid-operation"
  bucket the candidate described it under. `readTextLines` (`nodejs.ts:513-542`): pre-check before
  opening the stream; `signal` passed to `createReadStream`; a `loopAbort` check at EACH loop
  iteration; and an EXPLICIT `afterReadAbort` check AFTER the loop completes, before `ok(lines)` is
  returned — confirmed a genuine fourth checkpoint the candidate's "pre + each loop" description
  omitted. `listDir` (`nodejs.ts:611-633`): pre-check, per-entry loop check, and confirmed NO
  post-loop check (returns `ok(infos)` immediately after the loop) — genuinely DIFFERENT from
  `readTextLines` despite the candidate grouping them as identical. `renameFile`
  (`nodejs.ts:585-600`): confirmed `rename()` accepts no `signal` option at all — pre-check only,
  no exception. All confirmed.
- **`L12-R010` shell pre-spawn order**: independently re-read `nodejs.ts:367-390` in exact
  execution order: `options?.abortSignal?.aborted` check; `resolveTimeoutMs`; `cwd =
  options?.cwd ? resolvePath(...) : this.cwd` (lexical only, no filesystem touch);
  `getShellConfig(this.shellPath)` (shell discovery, AWAITED, can fail `shell_unavailable`); THEN
  `access(cwd, constants.F_OK)` (the cwd EXISTENCE check). Confirmed: shell discovery completes
  strictly before the cwd existence check, so a configured-nonexistent shell together with a
  nonexistent cwd observably returns `shell_unavailable`, never `spawn_error` — the candidate's
  single combined "cwd/shell resolution" step did not commit to this order.
- **`L12-R011` timeout ceiling**: independently re-read `nodejs.ts:34-48`. `MAX_TIMEOUT_MS =
  2_147_483_647` exactly (`2^31 - 1`, not `2^31`); rejected when `timeout * 1000 > MAX_TIMEOUT_MS`.
  The largest ACCEPTED value is therefore `2147483.647` seconds exactly (`2147483.647 * 1000 =
  2147483647.0`, not `>`). The candidate's "roughly `2^31/1000`" (`= 2147483.648`) is off by
  `0.001` seconds at the exact boundary pinned Pi actually enforces — confirmed a real, if small,
  imprecision unacceptable at a typed accept/reject boundary.
- **`L12-R012` `SpawnOptions` cwd/environment gap**: independently re-read `spec/execution.md` §6's
  `SpawnOptions` shape. Confirmed the candidate declares `cwd?`, `env?`, `inherit_env=true` with no
  stated default cwd, no stated relative-cwd resolution base, and no stated environment-merge rule
  — `ctx.subprocess` has no Pi seam to source these from (`MINION_EXTENSION`, confirmed
  unchanged), so this is a genuine shared-contract completeness gap, not a Pi-parity question.
- **`L12-R013` execution-world compatibility primitive undefined**: independently re-read
  `spec/execution.md` §7. Confirmed it states the GOVERNING RULE (opaque identity; a consumer
  needing multiple capabilities to address the same resource validates compatibility) but defines
  no type shape for the identity value, no comparison/validation operation signature, no
  compatibility relation (identity equality vs. a broader relation), and no typed failure result —
  confirmed a real specification gap, not an implementation-mechanics question the frozen design
  left open.
- **`L12-R014` `process_path` foreign-provider contradiction**: independently re-read
  `spec/execution.md` §4's `process_path` bullet. Confirmed it simultaneously (a) scopes
  `target_key` comparison to ONE producing provider instance (§4's own provider/world-scoping
  bullet, `EXEC-003`), and (b) permits `process_path(target)` to be called on "the SAME provider
  instance... or one the caller has independently validated as execution-world-compatible via §7."
  These two rules conflict: execution-world compatibility (§7) is a statement about whether a
  RESULTING PATH STRING is meaningful across providers, not a grant of authority to decode another
  provider's own opaque `target_key`. A second provider has no way to interpret a foreign key
  correctly merely because it happens to belong to a compatible world. Confirmed a genuine
  contradiction, not a wording nitpick.

No part of the characterization is rejected. All six findings are confirmed as characterized.

## 2. Challenge pass (`agent-workflow.md` §11.8.4)

**Is the Pi source mapping correct?** Yes for `L12-R009`/`L12-R010`/`L12-R011` (Pi-sourced,
independently confirmed above). `L12-R012`/`L12-R013`/`L12-R014` have no Pi source to map — they
are shared-contract completeness/consistency defects on Minion-owned surfaces, correctly
classified `CONTRACT_ASSURANCE_DEFECT` rather than `PI_PARITY_DEFECT`.

**Is the behavior matrix complete enough to distinguish realistic wrong implementations?** Yes —
each finding's own minimal-correction/witness proposal names a concrete, executable discriminator
(e.g. abort `read_text_lines` after the last yielded line but before the post-loop check; a
combined nonexistent-shell-and-cwd witness; the exact `2147483.647`/`2147483.648` boundary pair).

**Are any cases implementation mechanics rather than observable semantics?** No — every finding
concerns an OBSERVABLE outcome (which `Result`/error a caller sees, which checkpoint fires first,
what path/environment a spawned child actually observes), not a language-specific mechanism.

**Does any proposed fix silently reopen a lower certified layer?** No. The review's own
"Rust implementability and lower-layer impact" section confirms no certified Runtime/LLM/Session/
Tool/Agent/Auth reopen is required; independently confirmed by scope — every fix is confined to
`spec/execution.md` §§3.1, 5.4, 6, 7, 4 and the corresponding `EXEC-###` manifest rows.

**Can both Python and Rust implement the rule idiomatically?** Yes for all six — checkpoint
ordering, precedence ordering, an exact numeric boundary, cwd/env defaulting, an
identity-comparison primitive, and a same-provider-only scoping rule are all ordinary typed-code
patterns in both languages; none depends on a language-specific mechanism.

**Does the defect's root cause depend on an extensibility point one language's certified lower
layer exposes and the other does not?** No — same footing in both languages, as for `CE-L12-01-01`.

**Are all previous review findings represented by an executable or documentary acceptance
criterion?** Yes — §5 below states one for each of `L12-R009`–`L12-R014`.

## 3. Design decisions

### 3.1 `L12-R009` — complete per-operation cancellation checkpoint table

Replaces `spec/execution.md` §3.1's binding table with the full, checkpoint-accurate version:

```text
read_text_file, read_binary_file:
    checks pre-aborted; signal threaded into the single underlying read call (no separate
    checkpoint -- a single-phase operation)

write_file:
    checks pre-aborted; awaits recursive parent mkdir (itself not abort-checked); checks AGAIN
    immediately after mkdir completes, before the write begins; signal also threaded into the
    underlying write call -- THREE checkpoints, not one

read_text_lines:
    checks pre-aborted (before opening the read stream); signal passed to the underlying stream;
    re-checks at EACH loop iteration (once per yielded line); checks ONCE MORE after the loop
    completes, before returning success -- FOUR checkpoints

list_dir:
    checks pre-aborted; re-checks at each loop iteration (once per directory entry); NO check
    after the loop completes -- genuinely fewer checkpoints than read_text_lines despite the
    superficial similarity of "loops over entries"

rename_file:
    checks pre-aborted only; the underlying rename() call accepts no signal option at all -- no
    mid-operation checkpoint of any kind

accepts signal (uniform typed API, section 3.1's public-API-shape rule) but does NOT inspect it:
    absolute_path, join_path, append_file, file_info, canonical_path, exists, create_dir,
    remove, create_temp_dir, create_temp_file
```

### 3.2 `L12-R010` — exact shell pre-spawn precedence, six steps not five

Replaces §5.4's step 3 with the exact source order:

```text
1. Pre-aborted signal
2. Invalid timeout
3. Lexical cwd resolution (no filesystem touch -- options.cwd resolved against provider cwd, or
   provider cwd used as-is; purely a string operation)
4. Shell discovery (getShellConfig) -- MAY fail shell_unavailable
5. cwd existence check (access(cwd)) -- MAY fail spawn_error -- AFTER shell discovery, not before
6. [process spawns]
7. On completion/interruption: callback_error > timeout > aborted > success (unchanged from the
   existing §5.4 step 5)
```

Discriminating consequence: a configured-nonexistent shell together with a nonexistent cwd
observably returns `shell_unavailable` (step 4 fails first), never `spawn_error`.

### 3.3 `L12-R011` — exact timeout ceiling

Replaces "roughly `2^31/1000` seconds" with the exact rule: `timeout` is rejected (`timeout` error
code, before any process is spawned) when `timeout * 1000 > 2_147_483_647`; the largest ACCEPTED
value is `2147483.647` seconds exactly.

### 3.4 `L12-R012` — `ctx.subprocess` cwd/environment defaults, mirroring `ctx.shell`

**Decision:** since the frozen design states `ctx.shell`'s own local provider spawns THROUGH
`ctx.subprocess` (design §7, confirmed structurally in `spec/execution.md` §6's own architecture
paragraph), `ctx.subprocess`'s own cwd/environment rule MUST already be well-defined enough for
that composition to work, and the simplest coherent choice is to mirror `ctx.shell`'s own already-
specified rule exactly rather than inventing a second, independent one — this is a
**MINION_EXTENSION** design decision (no Pi source; `ctx.subprocess` itself has none), not a
Pi-parity claim.

```text
SpawnOptions.cwd, when omitted, defaults to the provider's own current working directory (the
    same concept ctx.fs's own cwd and ctx.shell's own default cwd already use); when supplied and
    relative, it resolves against that same provider cwd, using the identical lexical resolution
    rule ctx.fs's own absolute_path/§3.2 uses -- not a separately re-implemented mechanism.

inherit_env=true (default): effective environment is the provider's own base/inherited
    environment overlaid by any per-call env -- identical to ctx.shell's own EXEC-004/§5.3 rule.

inherit_env=false: effective environment is EXACTLY the per-call env and nothing else -- no
    inherited variables leak through, identical to ctx.shell's own rule.
```

### 3.5 `L12-R013` — execution-world compatibility: defined primitive

**Decision:** a minimal, concrete language-neutral shape, **MINION_EXTENSION** (no Pi source):

```text
ExecutionWorldIdentity: opaque, provider-declared value; supports equality comparison

compatible(a: ExecutionWorldIdentity, b: ExecutionWorldIdentity) -> bool
    -- the compatibility relation. Identity EQUALITY is always sufficient: two providers with
       equal execution-world identity values are always compatible. A provider MAY additionally
       declare itself compatible with specific OTHER identity values (e.g. a documented family of
       interoperable remote backends) -- compatibility is not required to be equality alone, but
       equality is always the minimum baseline every provider must honor.

validate(providers: list[(name: str, identity: ExecutionWorldIdentity)]) ->
    Result[None, ExecutionWorldError]
    -- called by a CONSUMER (never the runtime) at its own activation, over the specific set of
       providers it needs to address the SAME resource through. Returns Err(ExecutionWorldError)
       naming (by the caller-supplied name/diagnostic label) every pairwise-incompatible provider
       if any pair among the given providers fails compatible(); returns Ok(None) otherwise.
       Providers not passed to a given validate() call are never implicated -- mounting
       incompatible capabilities that no consumer ever asks to be validated together remains legal
       (the existing "mixed worlds are a legitimate deployment" rule, unchanged).
```

### 3.6 `L12-R014` — `process_path` scoped to the producing provider only

**Decision:** adopt the review's own minimal-correction option 1 (require the producing provider
only) rather than inventing a new transferable-target protocol, per this project's narrow-fix
discipline. `process_path(target)` MUST be called on the SAME provider instance that produced
`target` -- full stop, no "or a compatible provider" exception. The cross-seam workflow this bridge
exists for is: `resolve()` and `process_path()` both happen on the ORIGINATING `ctx.fs` provider;
the resulting PATH STRING (not the `FsTarget`, not the `target_key`) is what gets handed to a
`ctx.shell`/`ctx.subprocess` provider independently validated as execution-world-compatible (§7,
now `EXEC-006`'s own `validate()` primitive) with that `ctx.fs` provider. World compatibility
justifies TRUSTING that the resulting path string is meaningful to the shell/subprocess provider;
it never grants a SECOND filesystem provider authority to decode the first provider's own opaque
`target_key`. This removes the contradiction: `target_key` scoping (§4's existing rule) and
`process_path` scoping are now the SAME rule, not two different ones.

## 4. Observable behavior matrix (new dimensions this episode settles)

```text
Filesystem cancellation checkpoint COUNT and ORDER per operation -- not merely "pre-aborted vs.
    mid-operation" as a binary, but the exact number and position of checkpoints per operation
Shell pre-spawn precedence -- the full six-step order, including the shell-discovery-before-cwd-
    check ordering and its combined-invalidity observable consequence
Shell timeout boundary -- the exact accept/reject numeric boundary, not an approximation
Subprocess spawn cwd/environment -- default cwd, relative-cwd resolution base, environment merge
    rule for both inherit_env values, all directly observable in the spawned child
Execution-world compatibility -- a concrete identity/comparison/validation shape and failure
    result, not merely a governing-rule statement
FsTarget/process_path provider scoping -- process_path callable ONLY on the producing provider;
    world-compatibility governs path-string trust across seams, not target_key decodability
```

## 5. Acceptance witnesses (one per finding, discriminating)

```text
L12-R009  setup: a file being read line-by-line via read_text_lines, with a signal that aborts
          AFTER the last line has been yielded to the loop but BEFORE the operation returns
          expect: Err(aborted) -- the post-loop checkpoint catches this window
          negative control: an implementation checking only pre-aborted-and-each-loop-iteration
          (no post-loop check) returns Ok(lines) here, failing this witness

          second setup: write_file whose signal aborts AFTER parent-directory mkdir completes but
          BEFORE the write call begins
          expect: Err(aborted); no content write may have started
          negative control: an implementation checking only pre-aborted (no after-mkdir check)
          proceeds to write, failing this witness

L12-R010  setup: shell.exec() called with a configured, nonexistent custom shell path AND a
          nonexistent cwd
          expect: Err(ShellError(shell_unavailable)) -- shell discovery fails first
          negative control: an implementation checking cwd existence before shell discovery
          returns Err(ShellError(spawn_error)) instead, failing this witness

L12-R011  setup: timeout = 2147483.647 seconds; separately, timeout = 2147483.648 seconds
          expect: 2147483.647 is Ok (accepted, spawns normally); 2147483.648 is
          Err(ShellError(timeout)) before any process is spawned
          negative control: an implementation using "roughly 2^31/1000" (2147483.648) as its own
          accept boundary accepts the second case, failing this witness

L12-R012  setup: spawn() with cwd omitted, in a provider whose own cwd is /work
          expect: the child process's own observable cwd is /work
          second setup: spawn() with inherit_env=true and env={"X":"1"}, in a provider whose base
          environment includes Y=2
          expect: the child observes both X=1 and Y=2
          third setup: spawn() with inherit_env=false and env={"X":"1"}
          expect: the child observes ONLY X=1 -- no inherited variable leaks through
          negative control: an implementation defaulting cwd to the OS process cwd rather than the
          provider's own cwd, or dropping the base environment under inherit_env=true, fails these
          witnesses

L12-R013  setup: two synthetic providers, A and B, declaring EQUAL execution-world identities; a
          synthetic consumer calling validate([("a", A.identity), ("b", B.identity)])
          expect: Ok(None) -- equal identities are always compatible
          second setup: A and B declaring UNEQUAL, non-family identities; same validate() call
          expect: Err(ExecutionWorldError) naming both "a" and "b"
          negative control: an implementation with no concrete validate()/ExecutionWorldError
          shape cannot even express this witness, which is itself the finding

L12-R014  setup: FsTarget resolved on provider A; process_path(target) called on provider B, a
          DIFFERENT provider instance independently validated as execution-world-compatible with A
          expect: this call is OUTSIDE the contract entirely (undefined) -- the correct workflow
          calls process_path on provider A itself, then hands the resulting STRING to a
          shell/subprocess provider compatible with A
          negative control: a candidate asserting this call MUST succeed, or MUST return a
          specific FsError, is WRONG under this agreement -- the contract no longer permits calling
          process_path on any provider other than the one that produced the target at all
```

## 6. Normative deltas required (coherent fix pass, next step -- not performed by this document)

```text
spec/execution.md
    -- section 3.1: replace the per-operation cancellation table with section 3.1 above (four
       distinct checkpoint profiles instead of three, read_text_lines/list_dir no longer grouped
       identically);
    -- section 5.4: replace step 3 with the six-step exact order in section 3.2 above;
    -- section 5.4 (or new subsection): replace "roughly 2^31/1000 seconds" with the exact
       2147483.647/2147483.648 boundary in section 3.3 above;
    -- section 6: add the SpawnOptions cwd/environment rule from section 3.4 above;
    -- section 7: add the concrete ExecutionWorldIdentity/compatible()/validate() shape from
       section 3.5 above;
    -- section 4: narrow process_path to the producing-provider-only rule from section 3.6 above,
       removing the "or a compatible provider" allowance;
    -- section 9: add a round-3/CE-L12-01-02 remediation record entry;
    -- section 10: extend the witness matrix with section 5 above's entries.

pi-parity-manifest.yaml
    -- EXEC-002: rule text updated to the complete checkpoint table (section 3.1 above);
    -- EXEC-004: rule text updated to the six-step precedence order and the exact timeout
       boundary (sections 3.2/3.3 above);
    -- EXEC-005: rule text updated with the cwd/environment default rule (section 3.4 above);
    -- EXEC-006: rule text updated with the concrete identity/comparison/validation shape
       (section 3.5 above);
    -- EXEC-003: rule text updated to scope process_path to the producing provider only
       (section 3.6 above).
```

## 7. Convergence contract

```text
CONVERGENCE CONTRACT
    AGREED FOR IMPLEMENTATION

EPISODE
    CE-L12-01-02

OPEN FINDINGS
    L12-R009 L12-R010 L12-R011 L12-R012 L12-R013 L12-R014

ACCEPTANCE WITNESSES
    section 5 above (one per finding)

NORMATIVE DELTAS
    spec/execution.md sections 3.1, 4, 5.4, 6, 7, 9, 10
    pi-parity-manifest.yaml EXEC-002, EXEC-003, EXEC-004, EXEC-005, EXEC-006

NEXT_OWNER
    Claude (coherent fix pass, agent-workflow.md section 11.8.6)
```

This checkpoint means the remaining observable surface is sufficiently characterized for one
coherent implementation-of-the-contract pass -- it is NOT final contract approval. A targeted
closure review (`agent-workflow.md` §11.8.7) of the resulting exact candidate, with the negative-
control evidence required by §11.8.7.1, remains mandatory before another `FINAL_CONTRACT_REVIEW`.
No Python or Rust Layer 12 implementation, and no Layer 13 work, is authorized by this document.
