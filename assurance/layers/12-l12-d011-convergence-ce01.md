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
