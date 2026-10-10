# Convergence episode `CE-L12D007-01`: containment of the L12-D007 evidence path

Coordination: minion-agent#199.
- **Trigger A** (§11.8): `L12D007-C001` survived independent review 1 and targeted re-review 2. Codex review 2: #199 comments 6101167674 / 6101177995, `.tmp/codex-scratch/l12d007-contract-review-2.md`.
- **Scope:** the evidence and fixture containment surface only. No Pi filesystem semantics, error-code expectation, native call sequence or certified product behavior changes here.
- `L12D007-C002` and `L12D007-C003` stay provisionally closed at code `80fd74c0` / docs `105bc1f9`.

**Checkpoint: AGREED FOR IMPLEMENTATION** at revision 3 (independent checkpoint review 3 APPROVED: #199 comment 6101296900, `.tmp/codex-scratch/l12d007-ce01-checkpoint-review-3.md`, at code `80fd74c0` / docs `2e3056f4`). History: revision 1 REJECTED (checkpoint review 1); revision 2 REJECTED narrowly on R5 (checkpoint review 2). `L12D007-C001` still needs targeted closure after implementation. No guard implementation or native evidence run happens before **AGREED FOR IMPLEMENTATION** (§11.8.5).

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

## Checkpoint revision 2 (after independent checkpoint review 1: REJECTED)

Checkpoint review 1 (#199 comment 6101235663; `.tmp/codex-scratch/l12d007-ce01-checkpoint-review-1.md`) found **`CE-L12D007-01-C001`**: the rules give **one dereferencing proof for every operation**, while the matrix promises operations on an outward link **as an entry**. Examples: cleanup removing `j-out -> C:\` as itself, and controls creating outward-link fixtures.

Under revision 1's R2 the entry `j-out` fails its own proof. So either the promise is impossible, or it is met by silently bypassing the proof, which recreates the missing-guard defect.

Accepted. Revision 2 **supersedes R2, R4, R5, R6, R7 and R8** below; R1, R3 and R9 stand. The S1-S12 inventory stands.

**Checkpoint: PROPOSED (revision 2).**

### Operation classes (new)

Every mutation in the inventory belongs to exactly one class. Its proof is determined by the class, never chosen per call site.

| Class | Operations | What is proven | Final component |
|---|---|---|---|
| **REFERENT** | anything that follows the final link: open, read, write, append, truncate, chmod/ACL change on a target, mkdir *through* a path, every provider operation under test | the **entire effective native path**, through the final component (R2) | an outward final link is **refused** |
| **ENTRY** (only with a verified no-follow primitive) | creating a link (its *path*), unlinking a symlink or junction, an own-entry metadata reset that is verifiably no-follow (`icacls <entry> /reset /L`; POSIX `lchown`-class or none) | the **containing directory** by the full R2 proof, plus the entry name as a single component (no separator, R1-clean). **The final component is not dereferenced** | an outward link may be inspected (`lstat`/`readlink`) and removed **as itself**; it never authorizes traversal or a referent mutation |
| **TRAVERSAL** | recursive cleanup, the POSIX permission restore walk | each child is first classified as an ENTRY. A link or junction child is handled **only** by an ENTRY operation (removed as itself) and **never descended into**. An ordinary directory child is re-proven by R2 before it is visited | an outward junction's target is never enumerated, reset or deleted |

- **No-follow is a verified property, not a declaration.** An ENTRY operation may be used only where the platform primitive's no-follow behavior is part of the cited contract:
  - Node `fs.unlinkSync` / `rmSync` (no recursion) on a link; Python `os.unlink` on a link; Windows `RemoveDirectoryW` on a junction;
  - `icacls ... /L` ("performs the operation on a symbolic link itself versus its target");
  - link creation (`symlink(2)`, `CreateSymbolicLinkW`, `CreateJunction`), which writes only the new entry.

  If no such primitive exists for an operation (for example a recursive chmod tool), the operation is **refused or skipped and the sandbox is left in place**. It never falls back to a following call.
- **Link text is data.** Creating a link writes only its entry. The text may point anywhere *only* for a link whose creation is an ENTRY operation in a **negative fixture** (below). For every ordinary fixture, the text must resolve inside under R2 from the link's own directory (revision-1 R4).

### R2 (revised): positive resolution proof, with explicit terminals

The REFERENT proof walks the effective native path component by component. Every link met has its text resolved, and that hop is checked at once, including on the last iteration. The proof **succeeds only** at one of three terminals:
- **(i) completed traversal:** every component was inspected, the last exists and is not a link (or is a link whose chain ends at (i) or (ii)), and every hop stayed inside;
- **(ii) proven missing:** a component is missing under R3, so nothing below it exists to redirect;
- **(iii) proven contained cycle:** the full pending path repeats a state already checked.

**Budget exhaustion (64) without a repeat, an outward hop, an unknown inspection outcome (R3) or a readlink failure all refuse.** No mutation may depend on exhaustion or on an unknown inspection state.

### R4 (revised): every entry point, by class

Each inventory mutation calls the guard for **its class** immediately before the native call:

| Entry point | Class |
|---|---|
| fixture writes and mkdirs, per-case directories, outputs, `deny_access` (an ACL change on a file or directory, never on a link) | REFERENT |
| `make_symlink` | ENTRY for the link path. For ordinary fixtures, the text is also REFERENT-proven from the link's directory |
| the controls driver's scratch, mutant-file and log writes | REFERENT |
| the controls driver's junction creation | ENTRY, as a negative fixture |
| removals of anything | TRAVERSAL / ENTRY |

### Negative-fixture rule (new; narrow)

A **negative fixture** is an outward-pointing link created *only* to prove the guard refuses it.
- It may be created **only** by an ENTRY operation inside a sandbox that was itself created under R2 for that control.
- Its text must be a fixed constant listed in the control: `C:\`, `/`, or `C:\l12d007-…-never-created`.
- It must never be the target of a REFERENT operation by the control.
- It is never removed by anything other than an ENTRY unlink.
- The control's own assertions are that the guard **refuses** REFERENT use of it and that no operation on its referent is attempted. They are observed under the intercept (R8).

This is the only route that admits an outward link text. It is not an exemption for controls in general: every other control operation is REFERENT or TRAVERSAL as above.

### R5 (revised): provider-operation targets, as the native spelling actually touched

The runner and the oracle pass the step's **original argument unchanged** to the provider. Separately, they compute the **effective native path** the provider will touch:
1. Pi's logical resolution: a `file://` URL is decoded through the certified §14 rules, and a relative path is joined to the case directory;
2. then the certified L12-D001 OS **projection** (§14): on POSIX a lone surrogate becomes U+FFFD in the native spelling; on Windows the UTF-16 spelling is kept.

That native spelling is REFERENT-proven under R2. A lone-surrogate argument and its U+FFFD projection can address the same entry, so a link at the projected spelling cannot evade the proof. This applies the certified §14 rule; it does not modify it. The raw-form ban (R1) still does not apply to provider inputs.

### R6 (revised): restore requires an existing, non-link entry

A case-end restore (undoing `deny_access`) re-proves its target at restore time and **additionally requires an existing, non-link entry of the kind it changed** (file or directory).
- A **proven-missing** target (renamed away) means the restore is **skipped**: absence never authorizes a restore attempt.
- A target that is now a **link** is also skipped; a restore never follows a link.
- On any skip or failure: log it, leave the sandbox in place, and never force.

### R7 (revised): cleanup is a TRAVERSAL

The cleanup walks the sandbox itself, by the TRAVERSAL class:
- links and junctions are removed as entries (ENTRY unlink), never descended into, never reset;
- ordinary children are re-proven before they are visited;
- each ordinary entry is reset singly (`icacls <entry> /reset /L`; POSIX `chmod` on ordinary entries only);
- the ordinary entries are removed bottom-up.

No tool traversal (`/T`, `-R`). Any refusal or failure leaves the sandbox in place.

### R8 (revised): the intercept admits the proven operation only

The intercept preload classifies each intercepted call by its **operation**, then applies that class's proof:
- write, append, truncate, open-for-write, chmod and mkdir: REFERENT;
- unlink, rmdir, symlink creation: ENTRY.

A proof for unlink therefore **never** authorizes a write or chmod through the same outward link. The intercept's **log destination** is itself REFERENT-proven before every append. A refused call is logged and thrown; it never reaches the OS.

### Behavior matrix (revision 2 additions; revision 1's rows stand unless superseded)

| Input | Operation | Outcome |
|---|---|---|
| entry `j-out -> C:\` inside the sandbox | REFERENT write, chmod, open, mkdir `j-out/x` | **refuse** |
| the same entry | ENTRY unlink / `rmdir` of the junction itself | allow; only the entry is removed; **no operation on `C:\`** |
| the same entry | TRAVERSAL cleanup | the junction is unlinked as an entry; `C:\` is never enumerated, reset or deleted |
| the same entry | ENTRY `icacls /reset /L` | allow (acts on the link itself); without `/L`, refused as a REFERENT ACL change |
| an entry whose **parent** resolves outside (`j-out/x`) | ENTRY unlink, link creation | **refuse**: the parent's REFERENT proof fails |
| a contained, existing, non-link target | REFERENT | allow, terminal (i) |
| a lone-surrogate argument whose U+FFFD projection is an outward link (POSIX) | provider operation | **refuse**; the projected spelling is proven |
| a restore target renamed away | restore | skip (proven missing does not authorize), log, leave the sandbox |
| a restore target replaced by a link | restore | skip, log |

### Witnesses and negative controls (revision 2)

All synthetic-metadata controls substitute `lstat` / `readlink` and error answers and intercept every mutation. The native self-tests create links only inside their own sandboxes, under the negative-fixture rule.

New **paired** controls, all on the **same** outward final link:
- **(a)** REFERENT write and chmod are refused;
- **(b)** ENTRY unlink is allowed, and its native effect is confined to the entry: under the intercept, the only attempted mutation is the unlink of the entry path;
- **(c)** no operation on the referent is attempted, in either (a) or (b);
- **(d)** an outward **ancestor**: ENTRY unlink and link creation of `j-out/x` are both refused;
- **(e)** the projection alias pair: a synthetic lone-surrogate argument whose projected U+FFFD spelling is an outward link is refused;
- **(f)** restore after a rename, and after a replacement by a link: both are skipped and no restore call is attempted.

Kept from revision 1: long acyclic chains (hop 42, budget+1), the last hop, inspection errors at an ancestor and at the leaf (`EACCES`/`EPERM`/`EBUSY`/readlink failure), Win32 123/161 as missing, contained cycles (2 and 10), and the intercept facing a lexically-inside link to outside.

Negative controls, each killed by its intended witness. Revision 1's seven stand, plus:
8. **parent-only-everywhere:** prove only the parent for every mutation. Killed by (a): a REFERENT write through the outward final link is admitted.
9. **follow-final-in-cleanup:** the cleanup descends into, or resets through, a link or junction. Killed by the TRAVERSAL control: an attempted operation on the referent is intercepted.
10. **entry-proof-authorizes-write:** the intercept admits a write after an ENTRY proof of the same path. Killed by (a) under the intercept.
11. **logical-not-native:** prove the logical spelling instead of the native projection. Killed by (e).
12. **restore-on-absence:** a restore attempted on a proven-missing target. Killed by (f).

## Checkpoint revision 3 (after independent checkpoint review 2: REJECTED narrowly)

Checkpoint review 2 (#199 comment 6101270123; `.tmp/codex-scratch/l12d007-ce01-checkpoint-review-2.md`) provisionally closed the entry-versus-referent finding (`CE-L12D007-01-C001`). It rejected only R5's projection clause.

Revision 2 said "on POSIX a lone surrogate becomes U+FFFD; on Windows the UTF-16 spelling is kept". **That is wrong.** Certified §14.1 states the native projection "is the same on Linux and Windows: it happens before the platform-specific call". It also says a provider must not leave it to the host ("Python on Windows passes the raw surrogate to NTFS").

The earlier Windows observation of a kept lone surrogate (`error/lone/self-dir/append`) is the **logical** fallback path of a path-less error (§14.1's logical value). It is not the native spelling.

Revision 3 **supersedes only R5** below. Everything else in revision 2 stands.

**Checkpoint: PROPOSED (revision 3).**

### R5 (revision 3): provider-operation targets, as the native spelling actually touched

The runner and the oracle pass the step's **original argument unchanged** to the provider. Separately, they compute the **effective native path** the provider will touch:
1. Pi's logical resolution: a `file://` URL is decoded through the certified §14 rules, and a relative path is joined to the case directory;
2. then the certified §14.1 native projection, **identical on Linux and Windows**:
   - an unpaired high or low surrogate becomes U+FFFD;
   - a valid surrogate pair, including one held as two separate surrogate characters, becomes its astral character;
   - everything else is unchanged.

That native spelling is REFERENT-proven under R2 on both platforms. So `a<U+D800>`, `a<U+DC00>` and `a<U+FFFD>` (§14.1's aliasing) are proven as the one native entry `a<U+FFFD>`, and a link at that spelling cannot evade the proof on either host. This applies the certified §14.1 rule; it does not modify it. The raw-form ban (R1) still does not apply to provider inputs.

**Witness (e), revised:** the projection alias pair runs on **both** platforms. A synthetic lone-surrogate argument (high, and low) whose projected U+FFFD spelling is an outward link is **refused**. Its unprojected spelling, which is missing, must not be what the guard proves. Negative control 11 (**logical-not-native**) is killed by (e) on both platforms. A further mutant, **windows-keeps-surrogate** (project only on POSIX), is killed by (e)'s Windows run.

## Checkpoint amendment (revision 4): R3a, a proven over-long single component (POSIX)

**Context.**
- Under the agreed revision 3, the native Linux replay (uid 1000) **refused**, failing closed, at `errors/name-too-long`: the guard's `lstat` of the 300-character fixture component fails with `ENAMETOOLONG`, which is outside R3's POSIX missing set.
- The first amendment request (add every `ENAMETOOLONG` to the missing set) was **REJECTED** (#199 comment 6101513676; `.tmp/codex-scratch/l12d007-ce01-amendment-review-1.md`). POSIX uses `ENAMETOOLONG` for an over-long **component**, an over-long **complete pathname**, and an over-long intermediate pathname after **link substitution** (POSIX `lstat` errors; pathname resolution, Base Definitions 4.16). Only the first proves that the inspected component cannot exist.
- Accepted. The blanket rule is withdrawn. Revision 4 adds only R3a below. Revision 3 is otherwise unchanged, and R3a changes no Pi error-code expectation or product behavior.

**Checkpoint: amendment PROPOSED (revision 4).**

### R3a: proven over-long single native component (POSIX only)

During the R2 walk, an `lstat` of component *C* that fails with `ENAMETOOLONG` proves *C* missing (terminal ii) **only if all of the following are established**, each independently:
1. **The containing directory is fully proven.** Every earlier component of the current pending path was inspected, exists and is not a link (the R2 walk substitutes links as it meets them, so the prefix holds no link). There is therefore no link substitution between the proven directory and *C*.
2. **The limit is established for that directory**, never assumed:
   - `NAME_MAX` is queried for the **containing directory itself** (Python `os.pathconf(dir, "PC_NAME_MAX")`; Node `getconf NAME_MAX <dir>`, a read-only query);
   - the answer must be a positive integer;
   - an error, an unavailable or indeterminate limit (`-1`, `undefined`, non-numeric output) **refuses**. There is no default, and no assumption of 255.
3. **The comparison is in native bytes.** *C*'s length is measured in the bytes of its §14.1 native spelling, encoded as the filesystem receives it (UTF-8 on POSIX). It must **exceed** `NAME_MAX`. A component at or under the limit that reports `ENAMETOOLONG` **refuses**: that error came from elsewhere, for example the whole pathname. A character count is never used.
4. **The whole path is excluded as the cause.** `PATH_MAX` is queried the same way for the containing directory (a positive integer, or refuse). The byte length of the full absolute path inspected (directory + separator + *C*) must not exceed it. If it does, the source is ambiguous and the call **refuses**.

If any condition fails, or the error is anything other than `ENAMETOOLONG`, R3 applies unchanged (refuse). Windows is unchanged: the same over-long component already fails with 123, in R3's agreed set.

### Witnesses (synthetic; `lstat`, `pathconf`/`getconf` answers substituted; every mutation recorded, none reaches the OS)

| # | Situation | Expected |
|---|---|---|
| W1 | proven directory, `NAME_MAX` 255, a 300-byte ASCII component reports `ENAMETOOLONG` (the corpus case) | **admit** (proven missing); no mutation outside the sandbox |
| W2 | proven directory, a 100-byte component reports `ENAMETOOLONG` because the full path exceeds `PATH_MAX` | **refuse** |
| W3 | an `ENAMETOOLONG` attributed to link expansion: a component at or under the limit whose `lstat` reports it | **refuse** |
| W4 | byte versus character: 128 × `é` (128 characters, **256** UTF-8 bytes) against `NAME_MAX` 255 | **admit** |
| W5 | byte versus character: 200 ASCII characters (200 bytes) against `NAME_MAX` 255, reporting `ENAMETOOLONG` | **refuse** (not over the byte limit) |
| W6 | the limit query errors, or returns `-1` / undefined / non-numeric | **refuse** |
| W7 | the `PATH_MAX` query is unavailable | **refuse** |
| W8 | the containing directory is not proven (an earlier component's inspection is refused) | **refuse**, before any limit query |

### Negative controls

- **blanket-ENAMETOOLONG-is-missing:** admit every `ENAMETOOLONG`. Killed by W2, W3 and W5.
- **refuse-every-overlong:** never admit. Killed by W1 and W4 (the positive fixtures).
- **assume-255:** use 255 when the limit is unavailable. Killed by W6.
- **character-count:** compare character length, not bytes. Killed by W4 and W5.
- **skip-path-max:** omit condition 4. Killed by W2.

The native Linux replay resumes only after this amendment is independently approved and its controls pass.
