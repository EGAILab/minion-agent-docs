# WP133-D001: `builtin-bash-abort-during` aborts on the output event (TEST-BASH-ABORT-TIMING)

Coordination: `minion-agent#217`. Provenance: `#197`. Requirement: `TOOL-034` (WP-13.3, bash). Pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`, Node v22.15.1.

Status: **candidate, for independent review.** The Rust runner is pending (Codex).

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

**Status:** candidate, for independent review. The Rust runner follows: Codex implements `abort_on_output` at its `ctx.subprocess` seam. Not merged until both runners consume the field, because the Rust runner would otherwise run this scenario without an abort.
