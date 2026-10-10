# Convergence episode `CE-L12D007-01`: containment of the L12-D007 evidence path

Coordination: minion-agent#199.
- **Trigger A** (§11.8): `L12D007-C001` survived independent review 1 and targeted re-review 2. Codex review 2: #199 comments 6101167674 / 6101177995, `.tmp/codex-scratch/l12d007-contract-review-2.md`.
- **Scope:** the evidence and fixture containment surface only. No Pi filesystem semantics, error-code expectation, native call sequence or certified product behavior changes here.
- `L12D007-C002` and `L12D007-C003` stay provisionally closed at code `80fd74c0` / docs `105bc1f9`.

**Checkpoint: PROPOSED** (shared owner, Claude). Awaiting independent checkpoint review. No guard implementation or native evidence run happens before **AGREED FOR IMPLEMENTATION** (§11.8.5).

## OPEN FINDINGS

`L12D007-C001` (HIGH): containment is not enforced over the complete evidence path. Two failures remain open after remediation 1:
- **(a) Hop-budget exhaustion is accepted as success.** A 42-hop acyclic chain that ends outside is accepted. The walk can also return the last redirected path unchecked.
- **(b) Inspection failures are treated as absence.** Node's `lstatOrNull` returns null on any error, and Python's `lexists` is false on `EACCES`. So an unreadable component, which might redirect, is trusted.

## ROOT-CAUSE SURFACE

Both failures are the same defect: **the guard has no positive proof of containment at the point it permits a mutation.** It infers containment from the *absence* of contrary evidence (a budget ran out; a component could not be read). Codex's review points at the guards themselves. The challenge below extends the surface to every place that mutates or trusts a path in this evidence workflow.

## Challenge: the complete resolution and operation inventory

Codex's characterization table is accepted in full. These are added:

| # | Surface | Mutation / trust | Status at `80fd74c0`/`105bc1f9` | Needed |
|---|---|---|---|---|
| S1 | `assertInside` / `assert_inside`, `_fixture_target` | target resolution | defects (a) and (b) | rules R2, R3 |
| S2 | `makeSandbox` / `make_sandbox` | mkdir of the sandbox and its ancestry | uses the same walk, so inherits (a) and (b) | R2, R3 |
| S3 | `assertOutput` / `assert_output` | output files | inherits (a) and (b) | R2, R3 |
| S4 | oracle / probe **provider-operation targets** (the steps under test) | the provider writes, renames and deletes | the oracle asserts them; **the Python runner does not** (only fixture steps are checked) | R5 |
| S5 | fixture setup: writes, `make_symlink` (link path **and** text), `deny_access`, holders | mutation, ACL change, open handles | guarded, but inherits (a) and (b) | R2-R4 |
| S6 | **case-end restore** (`deny_access` undo) | an ACL / mode change at the ORIGINAL path, after the operation under test may have **renamed or replaced** it | not re-proven at restore time | R6 |
| S7 | **final cleanup reset** | Windows `icacls <root> /reset /T`; POSIX recursive chmod | **`icacls /T` traverses by itself and, without `/L`, may act on a link's target**; the POSIX walk skips links but inherits (a) and (b) | R7 |
| S8 | final cleanup `rmSync` / `shutil.rmtree` of the sandbox | recursive delete | Node `rm` and Python 3.12+ `rmtree` remove links and junctions as themselves (no follow); the root is guarded | R2, R3 on the root; the no-follow property is a stated precondition |
| S9 | the **controls driver** (`containment-controls.mjs`) | its own scratch writes, the mutant file in `gen/`, the junction it creates, the mutant's removal | **unguarded per operation** | R4 |
| S10 | the **intercept preload** (`intercept.mjs`) | the backstop decision | **lexical-only** | R8 |
| S11 | generators' outputs (`gen_canonical`, `make_cases`, `widen_d001`), probe outputs | output files | `assertOutput` (inherits (a) and (b)) | R2, R3 |
| S12 | the container scripts | writes inside the container's tmpfs, plus one `/out` bind | `/out` is checked with `FS_GUARD_OUTPUT` (inherits (a) and (b)) | R2, R3 |

Out of scope, recorded:
- The product's own operations (Python/Rust providers). Their behavior *is* the evidence; they are confined by the case directory the guarded runner/oracle hands them (S4).
- Gate test suites using pytest `tmp_path` / Rust fixtures. Their bases are already required to be inside the root (`--basetemp`, `.tmp/process-temp`, `MINION_FIXTURE_ROOT`); that is not changed here.

## OBSERVABLE RULES (proposed)

- **R1, raw forms.** Fixture and guard targets are refused **before normalization** if they are:
  - empty;
  - a drive form (`X:`, `X:foo`, `X:\`);
  - absolute, UNC or device;
  - or contain a `..` segment.

  (Unchanged from remediation 1.)
- **R2, positive resolution proof.** Resolution walks the target component by component. Every link met (existing, dangling or looping) has its text resolved, and that hop is **checked at once** against the boundary (as written or as its real path), including the last iteration.
  - A hop outside: **refuse**.
  - The walk ends **only** with one of two proofs: (i) a component is proven missing (R3), so nothing below it exists to redirect; or (ii) the full pending path repeats a state already checked, a **proven contained cycle**.
  - **Budget exhaustion without a repeated state: refuse** (budget 64). A contained cycle longer than the budget is therefore refused (fail closed); the corpus's cycles have 2 hops.
- **R3, inspection outcomes.** Only these end a walk as "missing":
  - POSIX `ENOENT`, and `ENOTDIR` (a prefix is a non-directory, so the rest cannot exist);
  - Windows Win32 2 / 3 (not found), 267 (a prefix is not a directory) and **123 / 161 (an invalid or over-long name, or stream syntax): the name cannot exist, so nothing can redirect through it**. In Node errno terms: `ENOENT` / `ENOTDIR`.

  Every other inspection failure (`EACCES`, `EPERM`, `EBUSY`, `ELOOP` from the OS, …) **refuses**. Readlink failure on a known link refuses.
- **R4, every entry point, before every operation.** Each mutation in the inventory calls the guard on its exact target immediately before the native operation:
  - fixture writes and mkdirs;
  - the link path, and the link text from the link's own directory;
  - `deny_access`;
  - per-case directories;
  - outputs;
  - the controls driver's own scratch, mutant and junction writes and removals.
- **R5, provider-operation targets.** The runner, like the oracle, resolves each step's path argument as pinned Pi does (a `file://` URL is decoded; a relative path is joined to the case directory), and requires the result to be proven inside the case directory under R2/R3 before calling the provider.
  - The raw-form ban (R1) is **not** applied to provider inputs: they are the behavior under test, and the corpus deliberately includes forms such as `file://` URLs.
  - Their **resolution** must still stay inside, or the case is refused (fail closed) rather than run.
- **R6, restore re-proves.** A case-end restore re-runs R2/R3 on its target at restore time. If the proof fails, or the target is now a link, the restore is **skipped**, the sandbox is left in place, and this is logged. It is never forced.
- **R7, cleanup traversal is the guard's own.** No tool-driven recursive traversal (`icacls /T`, `chmod -R`). The cleanup walks the sandbox itself, never follows a link or junction, re-proves each entry, resets each entry singly (`icacls <entry> /reset /L`; `chmod` on non-links only), and then removes the root with a no-follow recursive remove. Any failure leaves the sandbox in place.
- **R8, the intercept backstop uses the same proof.** `intercept.mjs` admits a mutation only when the R2/R3 proof places its target inside the project root. Lexical-only admission is removed.
- **R9, no native evidence run** (oracle, probes, runner corpus) until R1-R8 and their controls pass.

## BEHAVIOR MATRIX (proposed guard outcomes)

| Input | Outcome |
|---|---|
| prohibited raw form (R1) | refuse, before normalization or mutation |
| contained, existing target with no link | allow |
| contained, missing target (ENOENT / 2 / 3) | allow |
| contained invalid name (`x<y`, 300-char name, `./f:stream:bad`): Windows 123 | allow (the name cannot exist) |
| outward link, existing or dangling, 1 hop or many | refuse |
| acyclic chain whose hop 42 (or any hop) is outward | refuse at that hop |
| acyclic contained chain longer than the budget | refuse (budget exhausted, no repeat) |
| contained cycle (2 hops; 10 hops) | allow (a repeated, fully checked state) |
| inspection failure `EACCES` / `EPERM` / `EBUSY` on any component | refuse |
| readlink failure on a link | refuse |
| restore whose target was renamed away, or replaced by a link | skip, log, leave the sandbox |
| cleanup over a sandbox containing a junction to the drive root | the junction is removed as itself; its target is never visited or reset |
| controls-driver scratch / mutant / junction operations | each guarded |
| intercept: a lexically-inside path that redirects outside through a link | refused by the backstop |

## MINIMAL EXECUTABLE WITNESSES

- Codex's intercepted scripts: `.tmp/codex-scratch/l12d007-remediation1-memory.{py,mjs}` (42-hop acyclic outward chain; `lstat` `EACCES`). After implementation, both must report **REFUSED**.
- **New permanent synthetic-metadata controls**, for both guards and the runner. These use no native links: they substitute `lstat` / `readlink` and the error answers, and intercept every mutation. They cover:
  - long acyclic outward chains (hop 42, and hop budget+1);
  - budget-boundary off-by-one;
  - contained cycles of 2 and 10 hops;
  - `EACCES` / `EPERM` / `EBUSY` / readlink failure at an ancestor and at the leaf;
  - Win32 123 / 161 as missing;
  - restore after a rename or a link replacement;
  - cleanup over an outward junction (the target must not be visited);
  - an intercept backstop facing a lexically-inside link to outside.
- The existing native self-tests (`fs-guard-check.mjs`, `fs_guard_check.py`, runner `test_fs_path_runner_containment.py`) stay, extended with a native 2-hop contained cycle and an outward dangling chain. These create links only inside their own sandboxes and never write through them.

## NEGATIVE CONTROLS (each must be killed by its intended witness)

1. **budget-accept:** return success on budget exhaustion. Killed by the 42-hop and budget+1 synthetic controls.
2. **catch-all-missing:** treat every `lstat` error as absent. Killed by the `EACCES` / `EPERM` / `EBUSY` controls.
3. **unchecked-last-hop:** skip the check on the final redirected hop. Killed by the budget-boundary control.
4. **lexical-intercept:** the backstop's admission check reverts to lexical-only. Killed by the redirecting-inside-link backstop control.
5. **restore-without-proof:** the restore skips its re-proof. Killed by the renamed/replaced restore control.
6. **tool-traversal-cleanup:** restore `icacls /T` (or recursive chmod) in place of the guarded walk. Killed by the outward-junction cleanup control, which observes, intercepted, an attempted operation on the junction target.
7. **runner-skips-provider-target:** the runner stops proving provider-operation targets. Killed by a corpus-shaped case whose provider path resolves outside through a link (intercepted, never executed).

## CURRENT CANDIDATE FAILURES

At code `80fd74c0` / docs `105bc1f9`:
- defects (a) and (b) in every guard and the runner;
- S4 (the runner does not prove provider targets);
- S6 (no re-proof at restore);
- S7 (`icacls /T`);
- S9 (unguarded controls driver);
- S10 (lexical intercept).

## SPEC / MANIFEST / CONFORMANCE DELTAS

- **None to `spec/execution.md` §19 or the corpus expectations.** The guard rules are evidence-path rules, recorded here and in the record's method section.
- The record (`12-l12-d007-error-codes.md`) gets a remediation-2 section and a corrected method statement.
- The code repo's runner and its containment tests change. `pi-parity-manifest.yaml` only updates its evidence-file list if a file is added.

## IMPLEMENTATION CONSTRAINTS

- No product path, projection, error-code expectation or native call sequence may change to accommodate a guard. If a corpus case cannot be proven contained, the case is refused (fail closed) and the finding is reported; the case is never adjusted to pass.
- No new native evidence run until R9's controls pass. Native self-tests may create links only inside their own sandboxes and must never write through them.

## OUT-OF-SCOPE / DEFERRED BEHAVIOR

- Product provider behavior (Python/Rust): the evidence itself.
- Pytest and Rust test-suite temp bases: already required inside the root.
- The guard does not defend against an adversarial process racing the filesystem between proof and operation; the sandboxes are private to the run. This is stated, not solved: the risk is concurrent modification, which no single-process proof can exclude.
