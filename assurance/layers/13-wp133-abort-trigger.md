# WP133-D001: `builtin-bash-abort-during` aborts on the output event (TEST-BASH-ABORT-TIMING)

Coordination: `minion-agent#217`. Provenance: `#197`. Requirement: `TOOL-034` (WP-13.3, bash). Pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`, Node v22.15.1.

Status: **CLOSED (both runners)**, `minion-agent#217`. Shared candidate approved (Codex review 3, issuecomment-6130548185) and merged: code #218 → `ae8bce46`, docs #295 → `2611105d`. Rust runner approved (Claude closure reviews 1–2, issuecomment-6137242627 and -6137344859) and merged: code #220 → `0653dbf7`, docs #299 → `06ab808c` (record `13-wp133-abort-trigger-rust.md`). Provenance #197 is resolved: the scenario's abort is event-triggered in both runners. *(Earlier status: candidate, for independent review; the Rust runner pending.)*

## 1. Defect

The canonical scenario `conformance/agent/builtin-bash/builtin-bash-abort-during.yaml` runs `printf 'before\n'; sleep 5`. It aborts the call's signal a **fixed 400 ms** after the start, and expects:
- `is_error: true`;
- text `before\n\n\nCommand aborted`.

Under full-suite load on Windows, Git Bash start-up can exceed 400 ms. The abort then lands before `printf` runs, and the observation is `Command aborted` alone.

It was seen four times, always in a full Windows Python suite, and passed in isolation each time:
- three times on 2026-10-10 (`#197`);
- once on 2026-10-12, in the L12-D008 gate run (`12-l12-d008-div008.md` §6.2), where it also left `tools/builtin/bash.py:269` uncovered.

This is a test-robustness defect in shared canonical evidence, not a product defect.

## 2. Change

- **Schema** (`conformance/schema/builtin-bash-scenario.schema.json`): a new fixture field, `abort_on_output` (a non-empty string).
  - The runner aborts the call's signal once **the command's output delivered to the tool** contains it. That is stdout and stderr, through the `ctx.subprocess` seam, in the order the tool reads them.
  - The abort happens **after** the tool has taken in the chunk that completed the marker.
  - `abort_after_ms` remains valid; no scenario uses it any more.
- **Scenario:** `abort_after_ms: 400` becomes `abort_on_output: before`. The command and the expectations are **unchanged**.
- **Runners:**
  - The Python runner (`tests/conformance/builtin_bash_runner.py`) wraps the tool's `ctx.subprocess` provider. It proxies the spawned process's output streams and watches the bytes as the tool reads them. When the marker appears, it schedules `abort()` on the next loop turn.
  - The Rust runner implements the same field (Codex).

The trigger is still "abort **during** the command": the command has printed `before` and is in `sleep 5`.

**Why not `tools/update`.** The first draft listened on `tools/update`. But Minion's `bash` is certified to emit **zero** partial updates (spec `tools.md`, "No partial updates (Owner Q2)"), so that event never fires, and the first draft never aborted. The delivered output is the observable both bindings share. In pinned Pi the same moment is observable through the tool's `onUpdate`, which fires on received data; that is what the re-measurement probe (§3) uses.

## 3. Pinned-Pi re-measurement

`data/13-wp133-abort-trigger/abort_trigger_probe.mjs` is derived mechanically from the WP-13.3 probe (`data/13-wp133/harness/bash_probe.mjs`). It keeps the same pinned-Pi source slices (`bash.ts` execute body, `shell.ts`, `child-process.ts`, `truncate.ts`, `output-accumulator.ts`). Every change is asserted to apply exactly once:
- **only the abort cases,** run `repeat` times each;
- **an `abortOnOutput` trigger in `onUpdate`,** beside the original 400 ms timer;
- **sandboxes from the reviewed fs-guard** inside the project root, instead of `mkdtemp(tmpdir())`, which may fall back to C:.

The derivation script is recorded beside it.

| Case | Windows (5 runs) | Linux |
|---|---|---|
| timer 400 ms (original) | `before\n\n\nCommand aborted`, is_error, 5/5 | `before\n\n\nCommand aborted`, is_error, 5/5 (uid 1000, `/bin/bash`) |
| on output `before` (new) | `before\n\n\nCommand aborted`, is_error, 5/5 | `before\n\n\nCommand aborted`, is_error, 5/5 |

Outputs: `data/13-wp133-abort-trigger/pi-{win32,linux}.json`. The Linux run is `run-linux-abort.sh`: read-only mounts proven inside the project root by the reviewed guard, uid 1000, private tmpfs.

The expected text is unchanged under the new trigger.

## 4. Evidence and gates

**The flake's mechanism, reproduced deterministically** (`tests/conformance/test_builtin_bash_abort_trigger.py`). A 600 ms delay before the spawn stands in for Git Bash start-up under load:
- **the original 400 ms timer** loses `before`, which is exactly the flake: the observation is not the expectation, and `before` is absent;
- **the `abort_on_output` trigger** keeps the scenario's expectation.

Windows result: 3/3 runs, both directions.

**Focused Windows run:** the 37 bash scenarios passed 5/5 consecutive runs.

**Full gates at code `48c4dba8196a6566b1720521a594c63624ec1a1f`:**
- **Windows** (pinned ICU 78.3; preflight clean; no concurrent batch):
  - ruff: clean;
  - format (the 2 changed Python files): clean;
  - mypy: clean (117 source files);
  - pytest: **6294 passed, 43 skipped, 19 xfailed**;
  - coverage: **100.00%** (9601 statements).

  This full-load run includes `builtin-bash-abort-during`, the scenario that flaked under exactly this load before; it passed.
- **Linux** (`python:3.13`, uid 1000): pytest **5902 passed, 422 skipped, 19 xfailed**. The container mypy shows the same 15 pre-existing platform/stub errors as every Linux run, none in the changed files.

**Status at that point:** candidate, for independent review. Review 1 follows in §5.

## 5. Review 1 (Codex) and remediation 1

Review 1 (#217 issuecomment-6123874116) gave **CHANGES REQUESTED** at code `48c4dba8` / docs `2b552bd4`, class delta / governing (CP-6, and CP-1 for the oracle's writes). The remedy's design was found sound, the slow-start witness discriminating, and the Rust tap feasible. The Rust runner is deferred to the approved candidate.

### `WP133D001-R001` (medium): the tap watched every spawn, including the shell lookup

`_AbortOnOutput` wrapped every successful spawn. The certified shell selection (`bash_shell.lookup`, `where`/`which`) spawns through the same capability, so a lookup path containing the marker aborted the call **before any command process existed**. The reviewer's in-memory witness showed `signal_aborted=True` with only the lookup spawned.

**Fix:** the tap watches a spawn only when its options carry **the call's own signal**. That is the certified distinction: the command spawn passes `signal=` (`bash.py`), and the lookup passes none (`bash_shell.py`). The lookup is passed through untouched.

**Witnesses** (scripted in-memory subprocess; no native process):
- the lookup negative, through the **real** `bash_shell.lookup`: a lookup path containing `before` does not abort, and ordinary collection is kept;
- the command positive: a marker split across chunks fires only after delivery, on the next loop turn;
- the **control** restoring the all-spawns tap is caught by the lookup witness, for its intended reason (the abort fires).

43 bash conformance and trigger tests pass at code `2266c4b6`.

### `WP133D001-R002` (high): the authority probe's output write was unguarded

`abort_trigger_probe.mjs` wrote its result with `writeFileSync(outPath, …)`. `outPath` came from the command line with **no containment proof**, against the Owner's containment rule and kit 9.8. The reviewer demonstrated the attempted outside write with the writer intercepted, so nothing was written. *The author's recorded runs wrote their outputs inside the project; the defect is that nothing enforced it.*

**Fix:**
- The derivation script (`derive_abort_trigger_probe.py`) now makes the probe import fs-guard `assertOutput` and write only through `writeFileSync(assertOutput(outPath), …)`. The proof runs immediately before the write: inside the project root, or `FS_GUARD_OUTPUT`, failing closed through links.
- The derivation's own write goes through `fs_guard.assert_output`.
- The Linux recipe sets `FS_GUARD_OUTPUT=/tmp/w`, the container's private output directory.
- The probe is regenerated from the derivation, not hand-edited.

**Controls** (`abort_trigger_output_controls.mjs`). The probe's **actual writer statement** is extracted from its source and executed with `writeFileSync` **intercepted**, using the real `assertOutput`, under a guard boundary narrowed to a fixture directory **inside** the project:
- legitimate output: 1 attempt;
- output outside the boundary: refused, **0 attempts**;
- foreign absolute path: refused, **0 attempts**;
- output under a **junction parent** leading outside: refused, **0 attempts**;
- **control** with the proof removed: the outside case makes a write attempt, so the control is caught.

Result: PASS 5/5. Every fixture path derives from one literal base and is containment-checked before each mutation; cleanup removes the junction itself, never its target.

### Remediation-1 evidence

All of this ran in an isolated window, after the reviewer released the host (the L12-D008 Rust batch was done), sequentially: Windows replay, Linux replay, Windows gates, Linux gates. The preflight before the replays showed 27.54 GB free and no active builds.

**Authority replays from the repaired, guarded probe** (`pi-{win32,linux}.json`, regenerated):
- Windows: both triggers give `before\n\n\nCommand aborted`, is_error, **5/5 each**.
- Linux (uid 1000; the output went through the explicit `FS_GUARD_OUTPUT=/tmp/w`): **5/5 each**, identical.

**Gates at code `2266c4b6b53991dbeded96bf7e5f33d9b76e4371`:**
- **Windows:**
  - ruff: clean;
  - format (changed files): clean;
  - mypy: clean (117 files);
  - pytest: **6297 passed, 43 skipped, 19 xfailed**;
  - coverage: **100.00%** (9601 statements).
- **Linux** uid 1000: **5905 passed, 422 skipped, 19 xfailed**. The container mypy shows the same 15 pre-existing errors as every run.

**Output controls:** 5/5 (above).

*Status at that point:* remediation 1, for targeted re-review. Review 2 follows in §6.

## 6. Review 2 (Codex) and remediation 2

Review 2 (#217 issuecomment-6126544438):
- **`WP133D001-R001`** is **provisionally closed**. The rejected runner aborted on lookup output, and the candidate does not.
- **`WP133D001-R002`** is **not closed**. My new control script's **own fixture writes** used an ad-hoc **lexical-only** check (`path.resolve` + prefix + a `..` substring) before `mkdirSync` ×2, `symlinkSync`, and the cleanup `unlink`/`rmdir`. There was no real-path or link-hop proof, so a pre-existing outward ancestor would have redirected them. That is the very containment rule this finding enforces.
  - The reviewer showed it with every mutation intercepted: 3 attempts, 0 inspections, 0 native mutations.
  - The derivation also imported the guard from another worktree, so it was not reproducible from the candidate alone.

**Trigger A** fired for R002, which survived two reviews; B and C did not. RT-6: the Owner was notified in the Claude session. The route taken is the **narrow targeted-fix exception**: the remaining surface is finite, the reviewed fs-guard operations replace the ad-hoc check, and the guard comes from the candidate's own tree. If the next review does not close R002, the route is `CONTRACT_CONVERGENCE` with no further point fix. This is recorded in #217 `history.routes`.

**Remediation 2:**
- **Fixtures through the reviewed guard only** (CE-L12D007-01 operation classes, each proven immediately before its operation):
  - `makeSandbox` proves the REFERENT ancestry before its `mkdir`;
  - `assertInside` for each directory and for the junction's target;
  - `assertEntry` for the junction itself;
  - `cleanupSandbox` (TRAVERSAL) removes the junction as an entry, never following it.

  The ad-hoc check survives only as the regression control. The guard is imported relative to the script, from the candidate's own copy. The narrowed-boundary `assertOutput` comes from a second guard instance, loaded under a distinct module URL.
- **Part B witnesses**, over the setup's **actual** mutation calls, with every `mkdir`/`symlink` intercepted and the guard's inspections steered in memory (no outward link is ever created):
  - an outward-link ancestor: refused, **0 attempts**;
  - an inspection-failure (EACCES) ancestor: refused, **0 attempts**;
  - the **lexical-only control** under the outward-link ancestor makes **3 attempts**, so it is caught by the zero-attempt assertion.
- **Part A** (unchanged): legitimate 1 attempt; outside, foreign and junction-parent refused with 0; proof-removed control caught.
- The fixture is removed by `cleanupSandbox`. **9/9 PASS.**
- **The derivation** imports the guard (`../l12-d007/fs-guard`) and reads the WP-13.3 probe (`../13-wp133/harness/bash_probe.mjs`) relative to **its own checkout**.
  - Run in an **independent detached checkout** of docs `2b469948`, it regenerated `abort_trigger_probe.mjs` **byte-identically**: SHA-256 `0adee1d6…` equals the committed blob, with an empty `git diff`.
  - Git flagged the file only because `core.autocrlf=true` had materialized it with CRLF.
  - The check worktree was removed afterwards.

No product, expectation or other code change. Code is unchanged at `2266c4b6`.

**Status:** remediation 2, **for targeted re-review** of R002 and the review of the changed candidate. The Rust runner follows, on the approved candidate.
