# WP-13.2 Python implementation candidate (`write`, `edit`, mutation queue)

- **Coordination:** `minion-agent#49`.
- **Governance:** `standing_delegation: minion-agent#75`; `scope_extension:` the Owner decision "Finish Layer 13 Under Delegation" (`#75`).
- **State:** PYTHON_IMPLEMENTATION → IMPLEMENTATION_REVIEW. This record requests Codex's independent exact-SHA implementation review.

## Starting point

- The contract is AGREED FOR IMPLEMENTATION, per Codex's final complete review (`minion-agent-docs#190`), and merged:
  - `spec/tools.md` WP-13.2: docs #178 → master `59eba17b`;
  - manifest `TOOL-029`..`TOOL-033`, the `builtin_mutation` shape and the 26 canonical scenarios: code #81 → main `97d7c6bd`.
- `EXEC-009` is CERTIFIED_CLOSED (`minion-agent#79`). The final-`edit` dependency is satisfied.
- Candidate: code `d81872a07b1ff83914f973e945b1469badf9f8f4` (two commits: `c8f3e4ba`, the implementation, and `d81872a0`, the `L13-WP132-R005` direct-call guard), built on main `97d7c6bd`. Files:
  - `minion-agent-python/src/minion_agent/tools/builtin/`: `write.py`, `edit.py`, `edit_diff.py`, `_jsdiff.py`, `_utf16.py`, `mutation_queue.py`; plus additions to `plugin.py`, `__init__.py` and `collation.py`;
  - tests `tests/conformance/builtin_mutation_runner.py`, `test_builtin_mutation_conformance.py` and `tests/tools/builtin/test_wp132_mutation_tools.py`;
  - manifest `python:` fields.

## Design

**String semantics.**
- A JavaScript string is represented as a Python `str` whose characters are its UTF-16 code units (`_utf16.to_units`). An astral character becomes two surrogate characters.
- Every length, index, `indexOf`, `slice` and `split("")` in the matching and diff code is therefore Pi's own, not an approximation.
- Text converts at the boundaries only:
  - decoding uses `read`'s certified WHATWG decode;
  - tool arguments convert on entry;
  - NFKC works on scalar values, piecewise around unpaired surrogates, which are starters nothing composes with;
  - output is encoded as WHATWG UTF-8, with an unpaired surrogate written as `EF BF BD`.

**Fuzzy normalization.**
- NFKC is ICU's `FilteredNormalizer2` over `[:age=16.0:]`, on the SAME verified ICU 78.3 build `ls` already loads and gates (`collation.Collation.nfkc_unicode16`). No second ICU and no host normalizer is involved.
- The trim is the exact ECMAScript `trimEnd` set, not `str.rstrip()`.

**Diff.**
- `_jsdiff.py` ports `diff` 8.0.4's `diffLines` and `createTwoFilesPatch` line by line:
  - the Myers search with diagonal pruning and jsdiff's branch choice;
  - component merging;
  - `structuredPatch` hunk building;
  - the zero-line sentinel (`{value: '', lines: []}` keeps zero lines, because `[]` is truthy);
  - the no-newline marker;
  - `formatPatch`.
- `edit_diff.generate_diff_string` ports Pi's display diff.

**Queue** (`mutation_queue.py`).
- Pi's `registrationQueue` becomes a per-event-loop chain of futures. Each registration waits for the previous one to settle, and marks its own as settled in a `finally`, so a failed registration never blocks later ones.
- Keys use `canonical_path`, falling back to `absolute_path` on `not_found`, `not_directory` or `not_supported`. Entries are scoped by `(id(provider), key)`.
- Release happens on the way out. A waiter whose own wait is interrupted releases only after the entry ahead of it, which keeps FIFO order.
- Nothing listens for aborts. No `ctx.fs` call receives the signal.

**Tools.**
- `write`: `TOOL-026` steps 1-4, then registration, then inside the lock: checkpoint → `absolute_path` → `create_dir(dirname)` → checkpoint → `write_file` → checkpoint.
- `edit`:
  - `validateEditInput`, then preprocessing, then the EXEC-009 access stage, with the checkpoint before an access error.
  - On a provider without EXEC-009, `check_readable`; when that is unsupported too, no access stage.
  - Then read → checkpoint → match → checkpoint → write → checkpoint.
  - `prepare_arguments` is Pi's `prepareEditArguments`, with JSON parsing rejecting the `NaN`/`Infinity` literals JSON forbids.
- Errors use the `L13-WP132-O1` wrappers and the `R010-B` cause phrases.

## Evidence

| Evidence | Result |
|---|---|
| Canonical scenarios (`conformance/agent/builtin-mutation/`, real Layer 06 `execute_call`) | **26/26 documents pass**: 373 corpus cases, 43 hand-authored cases and 11 queue scenarios |
| `fuzzy_normalize` replay of pinned Pi's results | 5/5 |
| Scratch check of the pure core against every non-prepare authority result (370 edit/write + 5 fuzzy) | 0 mismatches |
| The 8 object-valued `prepareEditArguments` cases | pass through the real pipeline, in `builtin-edit-corpus-prepare` |
| The non-object input (`L13-WP132-R005`) | a unit test calls the callback directly and gets the value back unchanged |

**Binding-level negative controls** (spec item 4). Each is a single-point mutant of the real source, killed by its named canonical witness. `test_every_witness_passes_unmutated` proves every witness passes first.

| Mutant | Killed by |
|---|---|
| Unicode 15.1 NFKC (host `unicodedata`) | fuzzy replay |
| Unicode 17.0 NFKC (unfiltered ICU 78.3) | fuzzy replay (U+A7F1) |
| native whitespace trim (`str.rstrip()`) | `builtin-edit-corpus-curated` (NEL, U+001C) |
| registration not serialized | same-target call order; slow failing registration |
| failed registration never settles | slow failing registration (calls never settle) |
| queue without provider scoping | providers do not share queues |
| abort listener releasing the held lock | aborted call holds lock until its write settles |
| queue-wait abort listener (docs #188's control) | released after error and after abort |
| `absolute_path` awaited before registration (`R001` control) | same-target call order |
| two-probe access check | edit error sites |

**Runner note.** The queue runner's quiescence first treated "no event after N scheduler turns" as idle. A task reacting on a short timer, such as an abort poller, could then act after the next step, and the abort-listener control survived.

Quiescence now also requires the event log to stay unchanged across a wall-clock settle window, and both abort-listener controls are killed. This implements the schema's "no task can make progress without a gate". Another binding's runner needs an equivalent that is not scheduler-turn-only.

*Superseded by remediation 1 (`L13-WP132-I001`, below). A fixed real-time settle window is itself not quiescence.*

## Fresh gates

**Windows,** on the candidate, with the pinned ICU 78.3 environment:

| Gate | Result |
|---|---|
| `pytest` | **2213 passed**, 16 skipped, 19 xfailed; coverage **100%** (at `d81872a0`) |
| `ruff check` | clean |
| `mypy` (strict) | clean |
| schema + manifest validation | 292 passed |
| `ruff format --check` | the new files are formatted. It flags 9 files that are unchanged here and flagged identically on `main` (a pre-existing formatter-version drift, not part of this candidate) |

**Linux,** in a disposable `python:3.13-slim` container: the pinned ICU 78.3 was built with `scripts/pinned-icu/build.sh`, and PyICU 2.16.2 from its hash-checked sdist.

| Run | Result |
|---|---|
| WP-13.2 conformance and negative controls (root) | **47 passed** |
| WP-13.2 conformance as an unprivileged user | **28 passed** |
| full suite (root) | 2148 passed, 79 skipped, 19 xfailed, **1 failed**: `tests/execution/test_shell.py::test_exec_no_bash_found_on_this_platform`, pre-existing (below) |

The Linux run used the content of `c8f3e4ba`. `d81872a0` adds only the direct-call guard and its unit test, verified on Windows.

**The one Linux failure is pre-existing and outside WP-13.2.**
- The same test fails identically on `main` `8a2a3948` in the same image. `execution/shell.py` and `test_shell.py` are unchanged between `8a2a3948` and `97d7c6bd`.
- On POSIX, shell resolution falls back to `sh` and never answers `shell_unavailable`, which is Pi's POSIX behavior. The test simulates "no bash" but has no Windows-only skip.
- It is filed as the non-blocking Layer-12 test follow-up `minion-agent#86`, and is not part of this candidate.

## Disclosures

- **Lone-surrogate cases.** Python's JSON/YAML decoding carries unpaired surrogates, so both `unpaired_surrogate_arguments` cases pass as tool cases. None is recorded as a Layer 02/05 hazard for Python.
- **Lexical parent.** `dirname` is `os.path.dirname` of the provider's absolute path. That is the host's `path.dirname`, as in Pi. A non-local provider with foreign path syntax would need its own lexical parent; no such provider is certified.

## Remediation 1: `L13-WP132-I001`..`I003`

**Trigger.** Codex's independent implementation review of code #87 @ `d81872a0` and docs #191 @ `940c815c`, recorded in `minion-agent-docs#192`, requested changes on three findings. All three are accepted.

### `L13-WP132-I001`: timers are progress; they must be fired, not waited out (CONTRACT_ASSURANCE_DEFECT)

**The defect.** A queue-wait abort listener polling every 500 ms survived the 50 ms settle window.

**The fix.** Each queue scenario now runs on its own `VirtualClockLoop`, a `SelectorEventLoop` with a jumpable clock, in a worker thread. `_quiesce` repeatedly:
1. drains ready callbacks;
2. waits for real provider I/O, which is never skipped;
3. fast-forwards to the next timer due within a 60-second virtual horizon and fires it.

The runner advances to the next step only when nothing is ready, nothing is in flight, and no timer is due within the horizon.

**Evidence.**
- Both abort-listener controls are now parametrized over poll intervals of 10 ms, 500 ms and 10 s, and all six runs are killed.
- Correct implementations have no timers, so they are unaffected.
- The schema's QUIESCE comment now states the rule for every binding's runner: timers count as progress, and a fixed real-time window is not quiescence.

### `L13-WP132-I002`: `JSON.parse` numbers are doubles (PI_PARITY_DEFECT)

**The fix.** `prepareEditArguments` parses JSON integers through `float(str)`:
- the value is correctly rounded (`9007199254740993` → `9007199254740992`);
- an overflow is Infinity;
- there is no CPython integer-digit limit;
- an integral finite result stays a Python `int`, Layer 02's representation.

Fractions and exponents were already correctly rounded doubles. The rejection of the `NaN`/`Infinity` literals is unchanged.

**Evidence.**
- A new pinned-Pi authority case, `prepare-json-string-huge-integer-extra` (a 5000-digit `extra`), is in the corpus. Pinned Pi prepares an edits array and applies the edit. The authority now has 380 cases; the 13 source mutants are still all killed; the queue authority is unchanged. The evidence, the README and the spec's evidence-inventory counts are updated.
- It is generated into `builtin-edit-corpus-prepare` (now 374 corpus cases), so Rust carries the same canonical witness.
- Python unit witnesses cover the prepared values: Infinity, the rounded integer, and the unchanged fraction.

### `L13-WP132-I003`: a valid pair held as two characters (PI_PARITY_DEFECT)

**The fix.** `encode_utf8` first combines valid high+low pairs through the UTF-16 round trip, then replaces only unpaired units with U+FFFD. The success count is unchanged, because it is already UTF-16 units.

**Evidence.** Five witnesses go through the real Layer 06 pipeline from a YAML-escaped string:

| Input | Length | Bytes written |
|---|---|---|
| valid pair `😀` | 2 | `f09f9880` |
| unpaired high | 1 | `efbfbd` |
| unpaired low | 1 | `efbfbd` |
| wrong order | 2 | `efbfbdefbfbd` |
| ordinary astral | 2 | `f09f9880` |

### Fresh gates after remediation 1 (code `28a5938da93dd4b4c7205d3dffcdc8bc82227684`)

**Windows:**

| Gate | Result |
|---|---|
| `pytest` | **2224 passed**, 16 skipped, 19 xfailed; coverage **100%** |
| `ruff check`, `ruff format --check` (new/changed files), `mypy` | clean |
| canonical scenarios | 26/26 documents (374 corpus + 43 hand-authored cases + 11 queue scenarios) |
| fuzzy replay | 5/5 |

**Linux** (`5d5e2da5` content; `28a5938d` adds only a schema comment): WP-13.2 conformance and negative controls **59 passed** (root) and **28 passed** (unprivileged). Full suite: 2160 passed, 79 skipped, 19 xfailed, and the single pre-existing `#86` failure.

## Status

- `Python WP-13.2`: IMPLEMENTATION CANDIDATE (remediation 1), pending targeted re-review, then the final complete exact-SHA review.
- `Rust WP-13.2`: NOT_IMPLEMENTED.
- `WP-13.2 cross-language`: NOT CLOSED.
