# L12-D011: convergence episode `CE-L12D011-01`

Coordination: `minion-agent#224`. Work package record: `12-l12-d011-spawn-nul.md` (§9). Template: kit `templates/convergence-record.md`; procedure: kit `WORKFLOW.md` §11.8.

```text
EPISODE             CE-L12D011-01
TRIGGER             A: L12D011-I002 survived implementation review 1 (issuecomment-6146503957, round 4)
                    and implementation review 2 (issuecomment-6162425940, round 5) on the same
                    control-credit surface.
                    C (already recorded at round 4): four rejected complete reviews (rounds 1, 2, 4, 5).
                    B: not fired (one blocking finding on the surface).
                    `minion-process convergence counters 224` (pinned kit v0.3.0), 5 distinct review
                    events: "Trigger A HAS FIRED: L12D011-C001, L12D011-I002 ... Trigger C HAS FIRED: 4
                    rejected complete reviews"; nothing excluded. (C001 is the contract-phase finding,
                    closed at review 3; it is history, not open.)
                    The RT-6 targeted-fix exception taken at round 4 said a survivor enters convergence;
                    it is exhausted. Default route CONTRACT_CONVERGENCE taken; Owner notified (RT-6).
OPEN FINDINGS       L12D011-I002 (CONTRACT_ASSURANCE_DEFECT, blocking)
PROVISIONALLY CLOSED L12D011-I001 @ 705d57af (review 2); L12D011-N001 closed (documentary)
ROOT-CAUSE SURFACE  validity of negative-control credit: an intended witness's failure is credited by a
                    substring of the pytest reason, not by its FORM, so an unrelated setup/import/name
                    exception that carries the marker text is credited as a kill.
```

The contract (`spec/execution.md` §21, `EXEC-013`) is approved and unchanged. This episode concerns evidence validity only, not NUL-spawn semantics. The implementation and runtime code (`src/**`) and every unrelated writer stay frozen.

## 1. Challenge of the reviewer's characterization (§11.8.4)

Codex's round-5 characterization (issuecomment-6162425940, "Compact characterization"; probe `.tmp/codex-scratch/l12d011-impl-r2-probes.py`) is accepted, with the additions below.

| Question | Answer |
|---|---|
| Is the authority mapping correct? | Yes. The authority is kit `WORKFLOW.md` §9.7 (a control is credited only when the intended witness fails for its discriminating reason), not Pi/Node. Runtime semantics are untouched. |
| Is the matrix complete enough to separate realistic wrong drivers? | Not quite. Four dimensions are added: (a) the **two pytest renderings** of a rewritten assertion (§2); (b) a **mixed** run where one intended witness has a genuine form and another a forbidden one; (c) an **exception-class name that merely contains** an allowed class (`…<locals>.Sub: …`, an `AssertionError` subclass, which renders its qualified name); (d) the **marker position**, a marker that appears later in an assertion message. |
| Are any rows mechanics rather than observable rules? | The observable here is the driver's verdict for a given pytest result. Rendering forms are pinned by an executable fixture run with the gate's own pytest on each platform (§4, W3), not assumed from one version. |
| Does a fix reopen a certified lower layer? | No. The driver script and its tests change; `src/**`, the spec, the manifest and the canonical cases do not. |
| Can every implementation language implement it idiomatically? | It is Python-evidence mechanics. Rust's negative controls are its own harness, under the same §9.7 rule. **No shared delta, and no Rust action** (`lessons/L09-REENTRANT-OBSERVER.md`, applied to evidence). A general lesson is proposed to the kit at episode close (§6). |
| Is every previous finding represented by an acceptance criterion? | I002 (rounds 4 and 5): rows M1–M14. I001: its control stays in the 15-control run, and its witness form is declared (assertion, `LONG NAME CONVERTED`). N001: closed and documentary; the gate keeps recording exits. |

## 2. Characterization probe: how this pytest renders failures

The probe is `data/l12-d011/ce01/test_forms.py`, run with the driver's flags: `-q -rA -p no:cacheprovider --no-header`, `COLUMNS=4000`. The environment was pytest 9.1.1 and Python 3.13.5 on Windows. The output is `data/l12-d011/ce01/forms-output.txt`. The probe file's committed blob has sha256 `5587b0e4…829c`. The output's committed blob, LF-normalized by git, has sha256 `7f84a5a6…9786`; the CRLF original was `00793168…cafe8`.

| Raised in the test body | `-rA` reason (first line) |
|---|---|
| `assert 'a' == 'b'` (short) | `AssertionError: assert 'a' == 'b'` |
| `assert got == want` (long strings, elided) | `assert "The property...ived 'd\\x00'" == "The property...'x\\\\d\\x00'"` (**no class prefix**) |
| `assert x, "PREFIX LOST: The fake"` | `AssertionError: PREFIX LOST: The fake` |
| `assert x, ""` | `AssertionError: ` |
| `raise AssertionError("PREFIX LOST: …")` | `AssertionError: PREFIX LOST: hand-raised` |
| `AssertionError` subclass | `test_forms.test_assertion_subclass.<locals>.Sub: PREFIX LOST: subclass` |
| `NameError("PREFIX LOST: …")` | `NameError: PREFIX LOST: counterfeit setup failure` |
| a real undefined helper | `NameError: name 'PREFIX_LOST_helper' is not defined` |
| `UnboundLocalError` | `UnboundLocalError: cannot access local variable …` |
| `import_module("PREFIX LOST")` | `ModuleNotFoundError: No module named 'PREFIX LOST'` |
| a native NUL (`os.stat("a\0b")`) | `ValueError: stat: embedded null character in path` |
| a qualified custom exception | `test_forms.test_custom_qualified.<locals>.Boom: PREFIX LOST` |
| a multi-line assertion message | `AssertionError: LONG NAME CONVERTED: line one` (first line only) |
| `pytest.fail("PREFIX LOST: …")` | `Failed: PREFIX LOST: via pytest.fail` |
| `ExceptionGroup` | `NameError('x') [single exception in ExceptionGroup]` |
| an exception in a fixture | `ERROR … - NameError: PREFIX LOST: in fixture` (an ERROR entry, not FAILED) |

**Observable rule.**
- A pytest-rewritten assertion renders as `assert …`, or `AssertionError: …` with the exact class name.
- Every other exception renders as `<qualified class name>: <message>`, or with a non-colon shape (an exception group). It can never start with `assert ` (a keyword cannot be a class name), and it never has the exact prefix `AssertionError: ` unless it is that exact class.

The form is therefore decidable from the reason's prefix alone.

## 3. Behavior matrix (acceptance rows)

Declared forms per witness:
- **ASSERT_MSG(marker)**: the reason starts `AssertionError: <marker>`. The marker is anchored at the start of the message.
- **ASSERT_EXPR(regex)**: the reason starts `assert ` or `AssertionError: assert `, and the regex matches the remainder.
- **NATIVE_NUL**: the reason is exactly `ValueError: embedded null character` or `ValueError: embedded null byte` (CPython's message at `create_subprocess_exec`), full match.

Every row assumes a green, selected baseline unless it says otherwise. "intended" means a witness node of the control under test.

| # | Observation | Verdict |
|---|---|---|
| M1 | intended node FAILED in its declared form with its reason; exit 1; no ERROR | KILLED |
| M2 | intended node FAILED `NameError` with no marker | INVALID |
| M3 | intended node FAILED `NameError` / `UnboundLocalError` / `ImportError` / `ModuleNotFoundError` **containing the marker**, synthetic and real (Codex's `import_module('PREFIX LOST')` text) | INVALID |
| M4 | intended node FAILED `Failed: <marker>` (`pytest.fail`), a qualified custom class with the marker, an `AssertionError` subclass with the marker, or an exception group | INVALID |
| M5 | intended node FAILED in its declared form, but with a different reason (`AssertionError: ` empty; another assertion) | NOT KILLED |
| M6 | ASSERT_MSG witness whose marker appears later in the message, not at its start (`AssertionError: wrapper: PREFIX LOST`) | NOT KILLED |
| M7 | NATIVE_NUL witness FAILED with the genuine `ValueError: embedded null character` | KILLED (never blanket-rejected) |
| M8 | NATIVE_NUL witness FAILED with another `ValueError` (`ValueError: stat: embedded null character in path`, `ValueError: x`), or `NameError: embedded null character` | INVALID for a non-`ValueError` class; NOT KILLED for a `ValueError` whose text differs |
| M9 | mixed: one intended witness in its genuine form, another intended witness in a forbidden form (M3/M4) | INVALID (a setup-class failure on any intended node voids the run) |
| M10 | no intended node failed; only an unrelated node failed | NOT KILLED |
| M11 | an ERROR entry (any node), a timeout, or exit 2/3/4/5 even with a matching FAILED line | INVALID |
| M12 | an intended node absent, skipped or xfail-hidden in the baseline; baseline exit ≠ 0; or any baseline FAILED/ERROR | INVALID before any mutant credit |
| M13 | exit 0 | NOT KILLED |
| M14 | the declared form/reason table: every witness of all 15 controls has exactly one declared form; every ASSERT_MSG marker occurs in exactly one assertion statement or raise in the witness's test source, checked mechanically by reading the test file | self-test FAILS if violated |

Every non-allowed form is forbidden. A FAILED reason on an intended node that matches none of the three form shapes is **INVALID**. It is not NOT KILLED, because a setup failure means the witness never ran.

**Declared form for each of the 15 controls** (current witness nodes, unchanged):

| Control | Witness → form |
|---|---|
| check-after-native-spawn | `test_no_native_spawn_after_rejection[argv0-options0]` → ASSERT_MSG `native spawn reached`; `canon(name/file)` → NATIVE_NUL |
| baseline-first-posix-order | `test_env_check_order_both_platforms` → ASSERT_EXPR `\['A', 'Z'` |
| sort-all-posix-order | the same node → ASSERT_EXPR `\['01', '10'` |
| naive-integer-index | the same node → ASSERT_EXPR `\['01', '2'` |
| unbounded-index-conversion | both I001 witnesses → ASSERT_MSG `LONG NAME CONVERTED` |
| superseded-baseline-value | `canon(env/superseded-baseline-value-control)` → ASSERT_MSG `a control must reach the OS` |
| raw-cwd-not-resolved | `canon(cwd/file-url-percent-00)` → NATIVE_NUL; `canon(cwd/literal-relative)` → ASSERT_EXPR `ived 'd\\\\x00'` |
| double-url-decode | `canon(cwd/file-url-percent-2500-control)` → ASSERT_MSG `a control must reach the OS` |
| default-cwd-unchecked | `canon(cwd/provider-default-nul)` → NATIVE_NUL |
| cwd-before-args | `canon(precedence/args-before-cwd)` → ASSERT_EXPR `"The property` |
| cut-at-or-above-128 | `canon(len/inspected-128)` → ASSERT_EXPR `x00'\.\.\." ==` |
| quote-selection | `canon(fmt/single-quote)` → ASSERT_EXPR `'it\\\\'s` |
| tool-string-matching | `test_engine_keeps_its_prefix_for_a_non_nul_failure` → ASSERT_MSG `PREFIX LOST` |
| tool-checks-projected-argv | `test_engine_diagnostic_shows_the_unprojected_value` → ASSERT_MSG `PROJECTED DIAGNOSTIC` |
| bash-checks-stdin-command | `test_bash_stdin_transport_command_is_not_argv` → ASSERT_EXPR `"The argument.*== 'Failed to st` |

**NATIVE_NUL residual (disclosed).** A setup-phase `ValueError` whose whole message is exactly CPython's native `embedded null character` would be accepted. That text is the native boundary's own signature, and the M14 table pins it to canonical nodes that pass a NUL to the spawn. `default-cwd-unchecked` is the only control credited solely by NATIVE_NUL. The rest also have an assertion witness: `check-after-native-spawn` has the spy, and `raw-cwd-not-resolved` has `literal-relative`. This is accepted as a residual rather than adding a new runtime test, because the reviewer required that the deliberately observed native `ValueError` not be blanket-rejected.

## 4. Minimal executable witnesses and negative controls (to be permanent)

All of these run without native spawns or filesystem writes. W3 runs pytest on a committed fixture with `-p no:cacheprovider` and `PYTHONDONTWRITEBYTECODE=1`, so it writes nothing.

- **W1 (`--self-test`, credit matrix).** Rows M1–M13 on synthetic results, including Codex's four exact counterfeit reasons and the **real** `ModuleNotFoundError` text produced at runtime by `importlib.import_module('PREFIX LOST')` (M3).
- **W2 (`--self-test`, declaration table).** M14 over all 15 controls: each witness has one declared form; each ASSERT_MSG marker occurs exactly once in its test file.
- **W3 (end-to-end rendering).** A committed fixture module, outside `testpaths` and therefore not collected by the suite, is run with the driver's own pytest command on each gate platform. Its nodes produce each §2 form, and the driver's real `parse` + form classifier must classify each one as expected. This pins the rendering assumption per platform and per pytest version instead of trusting the Windows probe.
- **W4 (pytest test).** `tests/scripts/test_l12_d011_control_driver.py` imports the driver by path and runs W1 and W2. The credit rules are thus part of the normal full suite on both platforms. The test-file location must be confirmed against the coverage configuration: `src/**` stays at 100%, and the script is not added to coverage.
- **Driver meta-controls (§11.8.7.1, known-bad → FAIL)**, each an in-memory mutation of the driver source run against W1/W2. Each must fail on the row named:
  - **D1** removes form validation (substring match only) → M3, the marker-bearing `NameError`, not merely M2;
  - **D2** blanket-rejects every `ValueError` → M7;
  - **D3** drops the marker anchor (`re.search` anywhere) → M6;
  - **D4** accepts a qualified/subclass name ending in `AssertionError` or containing it → M4;
  - **D5** lets a genuine witness mask a forbidden one (any-match instead of void-on-forbidden) → M9;
  - **D6** ignores the exit code → M11;
  - **D7** skips the baseline selection → M12.
  - On the candidate, each row passes.
- **The 15 real controls**, rerun on both platforms after the pass: baseline GREEN, 15/15 KILLED, each with its declared form recorded in the report (`observed_form`), every mutant exit 1, 0 errors.

## 5. Current candidate failures, deltas, constraints

- **Current candidate failures** (`705d57af`, by reading `credit()`):
  - M3, M4 (`Failed:`, qualified class names), M6 and M9 are credited KILLED;
  - M2 and M8's non-`ValueError` half are NOT KILLED today, where INVALID is required;
  - M14 does not exist;
  - M1, M5, M7 and M10–M13 already behave as required.
- **Spec / manifest / conformance deltas: none.** The record (§9 → a §10 implementation entry) and the evidence change.
- **Implementation constraints.**
  - Only `scripts/l12_d011_negative_controls.py`, the new W3 fixture, the W4 test, and the record change.
  - Keep the baseline, selection, exit, compile, unique-anchor and containment protections.
  - No new runtime test is added and no witness node changes, so the 15 controls keep their nodes.
  - The `-rA` command and `COLUMNS=4000` are unchanged.
- **Out of scope.** NUL-spawn semantics; the Rust harness; cross-repo changes; any other WP's control drivers. A kit lesson is proposed at close (§6).

## 6. Checkpoint (step 1, proposed)

```text
CONVERGENCE CHECKPOINT      PROPOSED FOR IMPLEMENTATION   (CE-L12D011-01)
OPEN FINDINGS               L12D011-I002
ACCEPTANCE WITNESSES        matrix rows M1-M14 (section 3) with the per-control declared-form table;
                            W1 credit matrix (incl. Codex round-5 counterfeits and the real
                            ModuleNotFoundError text); W2 declaration table; W3 end-to-end rendering
                            fixture on both gate platforms; W4 pytest test in the full suite;
                            driver meta-controls D1-D7 (known-bad -> FAIL on the named row, candidate
                            -> PASS); the 15 real controls rerun on both platforms with observed_form
NORMATIVE DELTAS            none (spec/execution.md section 21, EXEC-013 and the canonical cases are
                            unchanged); evidence/record only
NEXT_OWNER                  Codex (independent checkpoint review of exactly this proposal)
```

After implementation, the episode proceeds as follows:
1. targeted closure of I002 (§11.8.7), with the I001 control rerun as the previously closed dependency;
2. one final complete exact-SHA review (§11.8.8).

At close, a general lesson ("credit a negative control by the failure's form, not a marker substring") is proposed to the kit as a `lessons/` record.

Probe provenance: `.tmp/claude-scratch/i195/ce01-probe/`, copied to `data/l12-d011/ce01/`.

## 7. Checkpoint review 1 (REJECTED) and revision 1

**Checkpoint review 1** (Codex, #224 issuecomment-6162669604, round 6) **REJECTED** the §6 proposal at docs `fc148e5e`, code `705d57af`. §§1–6 above are kept as written; this section supersedes their rules where it says so.
- **CE-L12D011-01-C001** (HIGH): `NATIVE_NUL` accepted a same-text setup `ValueError`. For example, a helper that raises `ValueError('embedded null character')` with zero native calls renders identically to a genuine boundary rejection. The "accepted residual" in §3 had no governance basis. **Missing dimension: the observed failure origin, i.e. whether the intended boundary fired.**
- **CE-L12D011-01-C002** (MEDIUM): a rendered prefix is not exception identity. `type('AssertionError', (Exception,), {'__module__': 'builtins'})` renders `AssertionError: PREFIX LOST: The fake`, byte-identical to the real assertion. `type("assert ['A', 'Z']", …)` renders `assert ['A', 'Z']: setup helper failed`. §2's two universal claims, that no other exception has the exact `AssertionError: ` prefix and that nothing else can start with `assert `, are **false** and are withdrawn. **Missing dimension: the actual exception kind versus the rendered name.**

Both are accepted without dispute. The root cause is the same in each: §§2–3 inferred identity and origin from the human-facing rendering. Revision 1 stops inferring and **observes** them.

### 7.1 Characterization (revision 1)

**The mechanism probe** (`data/l12-d011/ce01/evidence_probe_plugin.py`, `test_origin.py`, output `origin-output.txt`; Windows, pytest 9.1.1, CPython 3.13.5). It is a pytest plugin, loaded with `-p`, whose `pytest_runtest_makereport` hookwrapper records, for each failed report:
- `when`;
- the exception **kind by identity**: `type(exc) is builtins.AssertionError`, `type(exc) is builtins.ValueError`, or otherwise OTHER. The identities are captured at plugin import;
- the first line of `str(exc)`;
- the **innermost raising frame** (file, function, line), taken from `exc.__traceback__`, with the stdlib `subprocess` module recognized by comparing resolved `subprocess.__file__`;
- whether the seam frame `minion_agent/execution/subprocess.py:spawn` is on the traceback stack.

It writes one `L12D011-EVIDENCE <json>` line per record, through the terminal reporter after capture ends, and makes no file writes. Observed:

| Test body | Rendered `-rA` reason | Recorded kind / innermost frame / seam frame |
|---|---|---|
| `assert …, "PREFIX LOST: The fake"` | `AssertionError: PREFIX LOST: The fake` | **ASSERTION** / `test_genuine_assertion` / no |
| C002 fake class `type('AssertionError', …)` | `AssertionError: PREFIX LOST: The fake` (identical) | **OTHER** / `test_fake_assertion_class` / no |
| C002 `type("assert ['A', 'Z']", …)` | `assert ['A', 'Z']: setup helper failed` | **OTHER** |
| C001 helper `raise ValueError('embedded null character')` | `ValueError: embedded null character` | VALUE_ERROR / **`_helper`** / no |
| genuine native fire through the seam (check bypassed, as in the mutants) | `ValueError: embedded null character` (identical) | VALUE_ERROR / **`stdlib:subprocess` `_execute_child`** / **yes** |
| a native fire that bypasses the seam (`asyncio.create_subprocess_exec` directly) | `ValueError: embedded null character` (identical) | VALUE_ERROR / `stdlib:subprocess` `_execute_child` / **no** |
| a rewritten elided assertion | `assert "The property...ived …"` | ASSERTION / the test function; the first line of `str(exc)` equals the rendered elided text |
| an `AssertionError` subclass / `pytest.fail` / a fixture `NameError` | qualified name / `Failed: …` / ERROR | OTHER / OTHER / OTHER with `when: setup` |

Every pair that renders identically is distinguished by kind, origin or seam frame.

The origin probe `origin_probe.py` (output `origin-probe-output.txt`) drives the real `LocalSubprocess.spawn` with the check removed in memory. NULs in argv, cwd, an env value and an env name all raise exact `ValueError` (`embedded null character`), innermost at stdlib `subprocess._execute_child`, with the seam frame present, on Windows.

**Linux (from source; to be confirmed executably).** In CPython 3.13 `Lib/subprocess.py`'s POSIX `_execute_child`:
- `os.fsencode` does not reject a NUL;
- the NUL is rejected in C, by `_fork_exec` (called from `_execute_child`) or by `os.posix_spawn` (called from `_posix_spawn`).

So the innermost Python frame is stdlib `subprocess`'s `_execute_child` or `_posix_spawn`, and the message is CPython's `embedded null byte`/`character`. W3 (§7.4) confirms this on the Linux gate before any control is credited there. If it disagrees, implementation stops and the checkpoint returns to characterization. If you want this confirmed **before** approval instead, a sub-minute `python:3.13` container probe in a host window does it.

### 7.2 Revised rule (replaces §3's form rules)

The credit uses only the **evidence records**. The `-rA` rendering is kept for human reading and for baseline PASSED selection, and is never used to decide a kill.

Each intended witness declares one **kind** and one **origin**:
- **ASSERTION(origin = file, function, statement anchor; reason)**:
  - kind ASSERTION by identity, `when == "call"`;
  - the innermost frame is in the declared file and function, at a line inside the declared assertion statement. The anchor source text is resolved to its line span by reading the test file, and must be unique within that function;
  - the reason regex is anchored (`re.match`) on the first line of `str(exc)`.
- **NATIVE_NUL(reason)**:
  - kind VALUE_ERROR by identity, `when == "call"`;
  - the innermost frame is in stdlib `subprocess` (`_execute_child` or `_posix_spawn`);
  - the seam frame `LocalSubprocess.spawn` is on the stack;
  - the first line fully matches `embedded null (character|byte)`.

How a run is judged:
- **Plugin presence.** Each pytest run (baseline and mutants) carries a fresh random token in the environment, and the plugin echoes it in every record. A run whose output lacks the plugin's start line, or holds a record with the wrong token, is INVALID.
- **Every intended node must be accounted for.** If an intended node is FAILED in `-rA` but has no matching evidence record, the run is INVALID.

| # | Observation (green, selected baseline) | Verdict |
|---|---|---|
| R1 | intended ASSERTION: identity, declared origin and anchored reason all hold; exit 1; no ERROR | KILLED |
| R2 | intended NATIVE_NUL: identity, stdlib origin, seam on stack, full-match text | KILLED (genuine native observations are never blanket-rejected) |
| R3 | C001: an exact `ValueError` with the NUL text whose innermost frame is not stdlib `subprocess` (a helper) | INVALID |
| R4 | a native fire without the seam frame on the stack | INVALID |
| R5 | C002: the fake `type('AssertionError', …)`, the `type("assert ['A', 'Z']", …)` class, an `AssertionError` subclass, `pytest.fail`, `NameError`/`UnboundLocalError`/`ImportError`/`ModuleNotFoundError` with or without the marker, an exception group | INVALID (kind is not the declared identity) |
| R6 | genuine ASSERTION raised in a different statement or function than declared (a helper's assert, another assert in the same test) | INVALID (the intended assertion did not fire) |
| R7 | right kind and origin, reason not matching, or the marker not at the start | NOT KILLED |
| R8 | mixed: one intended witness valid (R1/R2), another intended witness R3–R6 | INVALID |
| R9 | an intended node FAILED in `-rA` without an evidence record; a missing or foreign token; a duplicate record for a node | INVALID |
| R10 | `when != "call"` on an intended node; any ERROR entry; a timeout; exit 2/3/4/5 | INVALID |
| R11 | no intended node failed (only unrelated nodes) | NOT KILLED |
| R12 | an intended node not PASSED in the baseline; a red baseline | INVALID before any mutant credit |
| R13 | exit 0 | NOT KILLED |
| R14 | declaration table: each of the 15 controls' witnesses has one kind; every ASSERTION anchor is unique within its declared function in the current test source | self-test FAILS if violated |

**There is no residual.** The §3 `NATIVE_NUL` residual is withdrawn: R3 rejects a same-text pre-boundary `ValueError`.

**Trust boundary (stated, not a residual).** This is an assurance distinction between cooperating test components, as the reviewer framed it, and does not defend against hostile processes. A test that deliberately rebinds `builtins.AssertionError`, forges a traceback or prints a token-bearing record is out of scope. An accidental echo is excluded, because tests run under capture and records carry the per-run token.

### 7.3 Declared kind and origin for the 15 controls (witness nodes unchanged)

Abbreviations: U = `tests/execution/test_spawn_nul.py`, C = `tests/conformance/test_spawn_nul_conformance.py::test_spawn_case`.

| Control | Witness → declaration |
|---|---|
| check-after-native-spawn | U `test_no_native_spawn_after_rejection[argv0-options0]` → ASSERTION in `spy`, `raise AssertionError("native spawn reached")`, `native spawn reached`; C `[name/file]` → NATIVE_NUL |
| baseline-first-posix-order / sort-all-posix-order / naive-integer-index | U `test_env_check_order_both_platforms` → ASSERTION, `assert env_check_order(baseline, overlay, Platform.POSIX) == [`, with reasons `assert \['A', 'Z'` / `assert \['01', '10'` / `assert \['01', '2'` respectively |
| unbounded-index-conversion | U `test_index_domain_neighborhood_and_long_names` and U `test_long_numeric_env_name_is_an_ordinary_name_at_the_provider` → ASSERTION, each `raise AssertionError(f"LONG NAME CONVERTED: {error}") from error` in its own function, `LONG NAME CONVERTED` |
| superseded-baseline-value / double-url-decode | C `[env/superseded-baseline-value-control]` / C `[cwd/file-url-percent-2500-control]` → ASSERTION, `assert not observed["nul_input"], "a control must reach the OS, not the NUL check"`, `a control must reach the OS` |
| raw-cwd-not-resolved | C `[cwd/file-url-percent-00]` → NATIVE_NUL; C `[cwd/literal-relative]` → ASSERTION, `assert observed["message"] == text(expected["message"])`, `assert .*ived 'd\\\\x00'` |
| default-cwd-unchecked | C `[cwd/provider-default-nul]` → NATIVE_NUL (now origin-proved; C001's specific concern) |
| cwd-before-args / cut-at-or-above-128 / quote-selection | C `[precedence/args-before-cwd]` / `[len/inspected-128]` / `[fmt/single-quote]` → ASSERTION, the same `observed["message"]` statement, with reasons `assert "The property` / `assert .*x00'\.\.\." ==` / `assert .*'it\\\\'s` |
| tool-string-matching | U `test_engine_keeps_its_prefix_for_a_non_nul_failure` → ASSERTION, `assert str(caught.value) == "Failed to run fd: The fake"`, `PREFIX LOST` |
| tool-checks-projected-argv | U `test_engine_diagnostic_shows_the_unprojected_value` → ASSERTION, `assert str(caught.value).endswith(`, `PROJECTED DIAGNOSTIC` |
| bash-checks-stdin-command | U `test_bash_stdin_transport_command_is_not_argv` → ASSERTION, `assert await _run_bash(fake, tmp_path, "echo a" + N) == "Failed to start the shell wsl-bash"`, `assert .*'Failed to st` |

The reason regexes are carried over from the committed driver, rewritten as `re.match` on the first line of `str(exc)`. This first line equals the rendered elided text for a rewritten assertion (§7.1). The exact regex strings are finalized in the implementation and checked by R14 and by the baseline/mutant runs.

### 7.4 Witnesses and controls (replace §4)

- **W1 (`--self-test`).** Rows R1–R13 on synthetic evidence records, including each C001/C002 counterexample and Codex's round-5 counterfeits.
- **W2 (`--self-test`).** R14 over the 15 declarations against the current test source.
- **W3 (end-to-end, both gate platforms).** A committed fixture module, outside `testpaths` and in the shape of `data/l12-d011/ce01/test_origin.py` plus `test_forms.py`'s forms, is run with the driver's own pytest command and evidence plugin. Its nodes are: a genuine assertion; the fake `AssertionError` class; the `assert …`-named class; a subclass; `pytest.fail`; a marker-bearing `NameError`/`ImportError`; a helper `ValueError` with the NUL text; a genuine native fire through the real `LocalSubprocess.spawn` with `spawn_rejection` monkeypatched to `None` inside that test only; a native fire without the seam; and a wrong-statement assertion. The driver's real parser and credit must give each its R-row verdict. **On Linux this is also the executable confirmation of §7.1's origin.**
- **W4.** A pytest test in the full suite, `tests/scripts/test_l12_d011_control_driver.py`, runs W1 and W2.
- **Driver meta-controls (known-bad → FAIL on the named row; candidate → PASS)**, each an in-memory mutation of the driver or plugin:
  - **D1** kind by class **name** instead of identity → R5, the fake `AssertionError`;
  - **D2** blanket rejection of `ValueError` → R2;
  - **D3** an unanchored reason (`re.search`) → R7, the marker not at the start;
  - **D4** the innermost-origin check dropped → R3 (C001) and R6;
  - **D5** the seam-frame check dropped → R4;
  - **D6** any-match masking (no void on a forbidden witness) → R8;
  - **D7** a fallback to the rendered `-rA` reason when a record is missing → R9;
  - **D8** the token check dropped → R9, the foreign token;
  - **D9** the exit code ignored → R10;
  - **D10** baseline selection skipped → R12.
- **The 15 real controls,** rerun on both platforms: baseline GREEN; 15/15 KILLED; each credited witness reported with its recorded kind, origin, seam flag and first line; every mutant exit 1 with 0 errors.

**Constraints (revised).**
- The evidence reporter is a test-support plugin. It may be loaded only by the control driver and the W3/W4 runs, and is not loaded by the normal suite.
- No runtime (`src/**`) change. No witness node is renamed. Witness test bodies are unchanged, unless R14 shows that an anchor is not unique; any such evidence-only witness edit is disclosed.
- The protections for baseline, selection, exit, timeout, compile, unique anchor and containment stay as they are.

### 7.5 Checkpoint (step 1, revision 1, proposed)

```text
CONVERGENCE CHECKPOINT      PROPOSED FOR IMPLEMENTATION   (CE-L12D011-01, revision 1)
OPEN FINDINGS               L12D011-I002 (checkpoint dimensions CE-L12D011-01-C001 origin,
                            CE-L12D011-01-C002 identity)
ACCEPTANCE WITNESSES        evidence reporter (identity, innermost origin, seam frame, token);
                            rows R1-R14 + the section 7.3 declaration table; W1-W4 (W3 on both
                            gate platforms, including the C001/C002 pairs and the Linux origin
                            confirmation); driver meta-controls D1-D10; the 15 real controls rerun
                            on both platforms with recorded kind/origin
NORMATIVE DELTAS            none (spec section 21, EXEC-013, canonical cases unchanged)
NEXT_OWNER                  Codex (independent checkpoint review of exactly this revision)
```

## 8. Checkpoint review 2 (APPROVED) and the implementation pass

**Checkpoint review 2** (Codex, #224 issuecomment-6163015575, round 7) **APPROVED** exactly revision 1 (§7, checkpoint §7.5) at docs `3766d23f` / code `705d57af`. C001 and C002 are closed at proposal level. Recorded by the reviewer: **CONVERGENCE CONTRACT AGREED FOR IMPLEMENTATION**. The approval carried four cautions:
- resolve full source identities, not basenames;
- bind node, phase, kind, origin, token and reason together, with no fallback to the rendered summary;
- keep statement spans, not function-name-only matching;
- the Linux origin must be confirmed by W3 before any Linux credit.

**Implementation:** code #226 `f27b915e`, one commit on `705d57af`. It is evidence tooling only; the `src/**` diff is **0 lines**, so the runtime contract, I001's fix and EXEC-013 are untouched.
- **`scripts/l12_d011_evidence.py`, the reporter.** Its `observe(exc)` records type identity against the builtin `AssertionError`/`ValueError` captured at import, the first line of `str(exc)`, and every traceback frame as a **fully resolved** file with its code `co_qualname` and line. A `pytest_runtest_makereport` hookwrapper records every failed report, writing `error` when an observation is impossible. `pytest_terminal_summary` emits `START`/`RECORD`/`END` lines carrying the per-run token.
- **`scripts/l12_d011_negative_controls.py`, the driver.**
  - The witness declarations are `Assertion(file, qualname, anchor, reason)` and `NativeNul()`.
  - `statement_span` resolves an anchor with `ast`, scoped to the declared function by qualname, nested definitions excluded, unique.
  - `classify` returns GENUINE / MISMATCH / FORBIDDEN using full-path `normcase(resolve())` identity. Native origins are stdlib `subprocess` `Popen._execute_child`/`Popen._posix_spawn`, with the run's own `…/minion_agent/execution/subprocess.py` `LocalSubprocess.spawn` on the stack.
  - `credit` voids on any FORBIDDEN intended witness; accounts for every node (a FAILED node without a record is INVALID, as is a record without a FAILED line); and never reads the rendered reason.
  - W3 runs before the baseline; a W3 failure credits nothing.
  - The run report records each intended witness's classification, detail and observed type.
- **`scripts/l12_d011_evidence_fixture.py` (W3):** 12 nodes. They pair a genuine assertion, the marker not at the start, a wrong statement, the fake `AssertionError` class, the `assert`-named class, a subclass, `pytest.fail`, a marker-bearing `NameError`, an elided rewritten assertion, a helper `ValueError`, a genuine native fire through the seam, and a native fire without the seam.
- **`tests/scripts/test_l12_d011_control_driver.py` (W4):** 84 suite tests. They cover W1 (R1–R13, 41 rows, on real in-process observations, including an R3 variant with the same-text `ValueError` raised **inside the seam before the native call**), W2 (R14, 31 checks: 18 control witnesses, 12 fixture declarations and the 15-control count) and the 11 meta-control rows.
- **The witness test bodies and nodes are unchanged.** Every anchor resolved uniquely, so no evidence-only witness edit was needed.

**I002 negative-control evidence (§11.8.7.1).** Method: deterministic in-memory mutation of the driver or reporter source, so the known-bad state FAILS its named row while the candidate PASSES it. In addition, the old credit of `705d57af` is the known-bad prior state for the C001/C002 pairs: Codex's round-5/6 probes show it crediting them as KILLED.

| Meta-control | Known-bad mutation | Expected / observed failure | Candidate `f27b915e` |
|---|---|---|---|
| D1 | the reporter decides kind by class **name** | R5 "C002 fake AssertionError class" fails / failed | PASS |
| D2 | every `ValueError` rejected | R2 genuine native fails / failed | PASS |
| D3 | `re.search` instead of `re.match` | R7 marker not at start fails / failed | PASS |
| D4 | native origin check dropped | R3 C001 (inside-seam variant) fails / failed | PASS |
| D4 | statement-span check dropped | R6 another statement fails / failed | PASS |
| D5 | seam check dropped | R4 native without seam fails / failed | PASS |
| D6 | a genuine witness masks a forbidden one | R8 fails / failed | PASS |
| D7 | fallback to the rendered `-rA` reason | R9 FAILED without record fails / failed | PASS |
| D8 | token check dropped | R9 foreign token fails / failed | PASS |
| D9 | exit code ignored | R10 exit 2 fails / failed | PASS |
| D10 | baseline selection skipped | R12 missing from baseline fails / failed | PASS |

**Gates at `f27b915e`.** The host window was granted by Codex, Windows then Linux. Evidence is in `data/l12-d011/python-implementation/ce01/{windows,linux}`, each with `gates-summary.txt` and the Linux `*.exit` files.

| Gate | Windows | Linux (`python:3.13`, pytest 9.1.1, uid 1000, pinned ICU 78.3) |
|---|---|---|
| pytest | **6514 passed** (6430 + 84 W4), 43 skipped, 19 xfailed, 0 failed; exit 0 | **6340 passed** (6256 + 84 W4), 204 skipped, 19 xfailed, 0 failed; exit 1 (coverage only) |
| coverage | **100%** (9748 statements) | 96.89%, 303 missed: **identical per file and per line** to the remediation-1 candidate (`src` unchanged), i.e. the established base-equal platform limitation (§9 of the work package record) |
| mypy | clean (118 files); exit 0 | the same 15 errors, byte-identical to the remediation-1 run; exit 1 |
| ruff | clean; the 14 changed files formatted (whole-tree drift of 7 untouched files, informational) | clean; exit 0 |
| driver self-test | PASSED: 83 in-process checks (W1, W2, D1–D10), W3 12/12 | PASSED: 83 checks, W3 12/12; exit 0 |
| **W3 native origin** | genuine: `embedded null character` at `Popen._execute_child`, seam on stack | **genuine: `embedded null byte` at `Popen._execute_child`, seam on stack**, the executable Linux confirmation of §7.1 |
| negative controls | W3 PASS first; baseline GREEN (exit 0, 85 passed, evidence present); **15/15 KILLED**, every mutant exit 1 with 0 errors; **18/18 intended-witness observations GENUINE** (3 native, 15 assertion) | identical: W3 PASS, baseline GREEN, **15/15 KILLED**, 18/18 GENUINE; exit 0 |

**Development runs (disclosed, not credited):** a Windows self-test and a contained development run of the 15 controls at the same tooling (`controls-dev-ce01`), made before the window to check the declarations. Both were green.

**Open:** L12D011-I002 awaits the **targeted convergence closure review** (§11.8.7), with I001's control as the previously closed dependency. After that comes the one final complete exact-SHA review (§11.8.8).
