# WP-13.2 Python implementation — independent Rust review

Verdict: **CHANGES REQUIRED**. Review only; no implementation, semantic repair, or merge performed.

## Exact review target and authority

- Code PR #87: `d81872a07b1ff83914f973e945b1469badf9f8f4`.
- Docs PR #191: `940c815c1aa91d2c5bc40da33775b02ce5e6bee3`.
- Accepted code contract: `97d7c6bd98f2f07027e6ab1d057b3c7e6adab345`.
- Accepted docs contract: `59eba17bd71888d874d85c203c3b4dc646ce3ebc`.
- Pinned Pi: `b7bb00b936dbe21b8e160b3e89efdec361846699`.

Fetched both repositories and PR refs; candidates were remote-reachable, open, ready for review and unchanged at final verification. Issue #49 recorded IMPLEMENTATION_REVIEW / NEXT_OWNER Codex and this exact pair. Used isolated worktrees and a fresh review virtualenv; unrelated working trees preserved. Code descends from the accepted contract commit. Review follows `.agents/AGENTS.md`, `process/agent-workflow.md` and `process/coordination-state.md`.

Authority order: pinned Pi `write.ts`, `edit.ts`, `edit-diff.ts`, `file-mutation-queue.ts`, `utils/text.ts`; normative `spec/tools.md` WP-13.2 and accepted execution contracts; TOOL-026/029–033/039 manifest rules; builtin_mutation schema/scenarios and authority harness; certified Rust types/seams; implementation assurance; Python candidate. Prior R001–R005 contract closures and O1/O2 decisions are preserved. None of these findings requests a new semantic decision.

## Complete-surface audit

| Surface | Result |
|---|---|
| TOOL-029 write: queue placement, mkdir/write abort checkpoints, success text | Correct ordinary-path control flow; I003 blocks UTF-8 fidelity |
| TOOL-030 edit: prepare, validation, combined read/write access, sequential edits | Correct ordinary-path behavior; I002 blocks JSON.parse fidelity |
| TOOL-031 fuzzy/BOM/line endings/diff | Source audit and authority/canonical replay agree; no new finding |
| TOOL-032 queue: provider/key scoping, serialized registration, per-key release | Real production queue used; I001 blocks claimed deterministic runner evidence |
| TOOL-033 cooperative abort vs queue waiting | Production waits for the predecessor and checks at contractual boundaries; runner negative-control assurance insufficient (I001) |
| TOOL-026 path preprocessing | Existing preprocessing reused; write's absolute resolution stays inside queued work; accepted distinction preserved |
| TOOL-039 provider errors | Owner-approved deterministic mapping reused; stable Pi templates retained |
| Layer-06 preparation/execution and EXEC-009 | Real typed tool pipeline and combined access capability reused; no duplicate authority |
| Manifest and lower-layer scope | Evidence-only Python pointers; no disposition change or Rust implementation claim; existing contracts unchanged |

The runner dispatches real tools through Layer 06 with scripted filesystem operations, not a simulated edit/queue implementation. Its scheduling observation is nevertheless flawed: absence of recent progress is not proof that a timer cannot progress. Rust must not copy this fixed-time heuristic as the semantic meaning of quiescence.

## Fresh executable gates

Environment: Windows, CPython 3.13.5, fresh editable install of the exact code worktree. PyICU 2.16.2 uses the pinned ICU 78.3 build, with `MINION_AGENT_ICU_BIN` and `MINION_AGENT_ICU_IDENTITY` configured and integrity validation passing. Node authority: Docker `node:22.15.1-alpine`; pinned Pi source and lockfile-integrity-verified diff 8.0.4 via the candidate evidence harness.

Commands executed from the candidate `minion-agent-python` directory:

- `python -m pytest`: **2213 passed, 16 skipped, 19 xfailed, 0 failures**, **100% coverage** (6477 statements).
- `python -m pytest tests/conformance/test_builtin_mutation_conformance.py tests/tools/builtin/test_wp132_mutation_tools.py -q -o addopts=`: **48 passed**.
- `python -m ruff check .`: clean.
- `python -m mypy`: clean, **97 source files**.
- `python -m pytest tests/conformance/test_schema_validation.py tests/conformance/test_manifest_validation.py -q -o addopts=`: **292 passed**.
- `python -m ruff format --check .`: **9 pre-existing unchanged files** would be reformatted; **239 formatted**. All nine new Python files pass formatting. The nine flagged paths have no candidate diff.
- Pinned authority harness: **379 cases**, **13/13 mutants killed**, acquisition/source-integrity checks passed.

The independent Linux full suite was not rerun here. Issue #86's known Linux shell-test defect is separate; neither affected shell source nor test is changed by this candidate. No stale Linux counts are asserted as fresh review evidence. Green candidate tests do not settle the additional witnesses below.

## L13-WP132-I001 — fixed settle window is not queue quiescence

Severity: blocking. Taxonomy: **CONTRACT_ASSURANCE_DEFECT** (executable evidence/runner defect, not a request to reopen the agreed queue rule).

Affected: `tests/conformance/builtin_mutation_runner.py:223–250`, binding negative controls, assurance's “Runner note”. `_quiesce` waits scheduler turns and a 50 ms quiet window. A coroutine awaiting a longer timer remains runnable in the semantic sense despite no immediate progress and no gate release.

Independent reproduction (`data/13-wp132-python-review/runner_probe.py`): a 300 ms timer remains pending when `_quiesce` returns after approximately 52 ms; it subsequently progresses without releasing any provider gate. More importantly, the exact early-answer mutant that races queue waiting against abort is killed with the existing 10 ms polling interval, but **survives the actual candidate scenario assertions with a 500 ms interval**. The runner releases A's gate before the timer can demonstrate the forbidden early result B. The same invalid algorithm now receives PASS merely by delaying its timer. This is not permission to add timers to production: it is a discriminating negative control for a claimed queue assertion.

Required correction: make gate advancement rely on a reproducible timer-aware/controlled scheduling or equivalent explicit observation barrier; do not merely lengthen the quiet window. Preserve real production ownership. Add permanent evidence that the early-answer mutant is killed independently of this arbitrary window, including a timer longer than the old window. Correct the assurance's Rust-runner guidance. The existing source queue algorithm itself is not rejected by this witness.

## L13-WP132-I002 — edits JSON uses Python integer semantics

Severity: blocking. Taxonomy: **PI_PARITY_DEFECT**.

Affected: `src/minion_agent/tools/builtin/edit.py:87–90` (`_json_parse`). It rejects non-JSON constants correctly but leaves JSON integers as arbitrary-precision Python ints. Pi uses JSON.parse's IEEE-754 Number semantics.

Independent witness (`json_probe.py`, `prepare_probe.mjs`): edits supplied as a valid JSON string containing a single edit plus an allowed `extra` integer of 5000 digits. Pi's actual extracted preparation function parses it into an edit array, with the extra value Infinity; actual pinned edit-diff core produces `A\n`. Candidate preparation leaves the edits as a string because CPython's integer-digit guard raises; the real Layer-06 pipeline reports invalid arguments, makes zero filesystem calls and retains `alpha\n`. No JSON syntax error or schema restriction justifies this rejection. Separately, extra integer `9007199254740993` remains that value in Python but becomes `9007199254740992` in Pi; prepared extras are observable to hooks.

Required correction: reproduce JSON.parse numeric decoding, including overflow and binary64 rounding, without CPython's integer-digit rejection. Disabling the digit guard alone is insufficient. Add permanent real-pipeline and preparation/hook-visible witnesses for both cases. Existing constant-rejection behavior must remain intact.

## L13-WP132-I003 — write corrupts a valid surrogate pair

Severity: blocking. Taxonomy: **PI_PARITY_DEFECT**.

Affected: `src/minion_agent/tools/builtin/_utf16.py::encode_utf8` and `write.py:70`. The encoder replaces every surrogate-range Python character individually, assuming valid pairs were already combined. The write boundary does not enforce that assumption.

Independent witness (`surrogate_probe.py`, `surrogate_probe.mjs`): a normal YAML string `content: "\uD83D\uDE00"` decodes through the actual canonical loader into two adjacent surrogate code points. This is a **valid UTF-16 pair**, not the deferred unpaired-surrogate issue. The real candidate tool reports “Successfully wrote 2 bytes to f.txt” but writes hex `efbfbdefbfbd` / base64 `77+977+9` (two replacement characters). Node's string with those same two units has length 2 and encodes as hex `f09f9880` / base64 `8J+YgA==` (one astral character).

Required correction: combine valid high/low pairs before UTF-8 encoding and replace only genuinely unpaired units, preserving the UTF-16 success count and ordinary astral input. Add a permanent escaped-YAML/direct-boundary witness through real Layer 06, plus unpaired/wrong-order controls. Do not narrow the approved input domain or work around it only in the runner.

## Reproduction

Review-only probes are committed in `assurance/layers/data/13-wp132-python-review/`. Run Python probes in a fresh candidate environment with `PYTHONPATH=<exact-code-worktree>/minion-agent-python`, ensuring `minion_agent.__file__` resolves to that candidate, and the pinned ICU environment described above. Probes print expected/observed evidence; they are characterization scripts, not purported permanent production tests. They modify only in-memory imported test objects and temporary fixtures.

For the Node preparation probe, mount pinned Pi at `/pi`, candidate docs' `assurance/layers/data/13-wp132-evidence` at `/evid`, an output directory at `/out`, and `prepare_probe.mjs` at `/probe.mjs` in `node:22.15.1-alpine`. Run `sh /evid/harness/run_authority.sh >/out/prepare-runtime.log && node --experimental-strip-types --no-warnings /probe.mjs`. The probe removes TypeScript-only annotations from Pi's preparation function and invokes the harness's actual pinned core; it does not claim to execute the full Pi TUI. `surrogate_probe.mjs` needs only the same Node runtime.

## Workflow disposition

Trigger check: prior contract history already fired A/C and recorded a narrow-point-fix exception for R004. Those resolved findings remain closed. The three implementation findings above have not survived a remediation review; nevertheless the package-level rejection threshold remains met. Ordinary focused remediation is explicitly justified here: finite executable witnesses already establish the expected semantics, production corrections require no semantic redesign, and the runner defect has an independently reproduced timing counterexample. If characterization of deterministic timer observation requires a new contract decision, stop and enter convergence rather than inventing a runner rule.

Issue #49 returns to **REMEDIATION / NEXT_OWNER Claude**. Next review is targeted closure of I001–I003 and affected surfaces, followed by the required final complete exact-SHA review of the changed candidate. No merge is approved. Shared contract remains approved; Python implementation is not approved; Rust WP-13.2 remains unauthorized; cross-language closure remains incomplete. No WP-13.3 or Layer 14 work is authorized.
