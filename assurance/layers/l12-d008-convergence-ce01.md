# CE-L12D008-01: how acceptance identifies the first terminal failure

Convergence episode for `L12D008-C002` on `minion-agent#215` (L12-D008 / DIV-008). Trigger A fired: C002 survived review 1 (issuecomment-6119284467) and the remediation-1 review (issuecomment-6119651732). Default route under RT-6; the Owner was notified and the route is recorded in #215 `history.routes`.

**Revision 1: AGREED FOR IMPLEMENTATION.** Codex's checkpoint review 1 (#215 issuecomment-6122626197) approved it at docs `101febec`. Its one non-blocking wording note (F2) is applied below. *(This line originally read "PROPOSED checkpoint, for independent review".)* Implementation: §7.

**Unchanged and out of scope:**
- the production walk, which the reviews found correct;
- the Owner's DIV-008 and "Continue siblings" decisions;
- the corrected extent composition (C001, closed);
- spec §19.5 rules 0–3, 5 and 6.

## 1. The surface

DIV-008's acceptance must decide **which failure a binding reports**: the first failure it encountered, with that failure's code. Review 2 showed that the surface has three dimensions the remediation-1 comparator conflated:
1. **Recovered fault versus terminal entry outcome.** A child's classification `lstat` fault is recovered by §19.5 rule 1: the child is unlinked as itself and removed. It is an injected OS fault, but not a failed child removal. Selecting the first *injected fault* rather than the first *terminal outcome* rejects correct behaviour. That is the reviewer's mixed witness: `lstat(a)=EACCES`, then `unlink(b)=EBUSY`; Pi and Python both report `unknown` at `b`.
2. **Missing controlled trace.** A controlled row without its fault events fell through to the natural branch, so absence relaxed the rule.
3. **Natural origin.** A natural row's reported path was accepted if it merely remained (for example `tree`, an ancestor), not proven to be a failing call's origin.

## 2. Characterization (revision 1)

The probes now record three kinds of trace events, in order:
- a call: `op rel`;
- an injected fault: `settle op rel CODE`;
- a **native** failure: `fail op rel CODE`, recorded at the real call and re-raised unchanged.

The matrix adds X1–X5, mixed recovered and terminal faults in both orders and nested:

| Row | Faults (in matrix order) | Pi (W / L) | Python (W / L) | What remains (all four) |
|---|---|---|---|---|
| X1 | `lstat a` EACCES (recovered), `unlink b` EBUSY | `unknown` @ b / same | same / same | `tree/`, `tree/b` |
| X2 | `unlink a` EBUSY, `lstat b` EACCES (recovered) | `unknown` @ a / same | same / same | `tree/`, `tree/a` |
| X3 | `lstat a/x` EACCES (recovered, nested), `unlink b` EBUSY | `unknown` @ b / same | same / same | `tree/`, `tree/b` |
| X4 | `lstat a` EACCES on a **directory** (recovered), `unlink b` EBUSY | `unknown` @ b / same | same / same | `tree/`, `tree/b` |
| X5 | `unlink a` EACCES, `lstat m` (recovered), `unlink z` EBUSY | `permission_denied` @ a / same | same / `unknown` @ z (**DIV-008**: tmpfs visits `z` first) | `tree/`, `tree/a`, `tree/z` |

Data: `data/l12-d008/ce01/ce01-{pi,py-1339078d}-{win32,linux}.jsonl`.

**Findings:**
- **F1.** A recovered fault is never the reported failure, in Pi or Python, on either platform. The terminal faults in these rows (`unlink` EACCES/EBUSY; and in B1/B3–B7, `readdir` and `rmdir`) are reported, and **their entries remain**.
- **F2.** Native failures are **mostly routine**. Where the target's rmdir-first step runs on a non-empty target, the trace has `fail rmdir tree ENOTEMPTY` (§19.5 rule 3). That is most rows, but not B5/B6, which inject at the target boundary first; *corrected wording, checkpoint review 1*. Recovering a directory child adds `fail unlink tree/a EPERM` (Windows) or `EISDIR` (Linux), then `fail rmdir tree/a ENOTEMPTY`. The **first native failure is therefore not the terminal failure.** Natural rows (Linux, a `chmod 0555` directory) carry their real origin as `fail unlink tree/<d>/locked EACCES`.
- **F3.** Raw native **codes are per-layer labels**, not observables. For the same directory unlink on Windows, libuv reports `EPERM` and Python's errno name is `EACCES`. Both are Win32 access-denied, which the binding routes as libuv `EPERM` by its Win32 code. Raw codes are recorded for provenance and never compared.

## 3. Proposed model (checkpoint)

**R1 — declared outcomes, verified against pinned Pi.** Every injection in the matrix declares `"outcome": "terminal"` or `"recovered"`. Every natural row declares the **signature** of its terminal native failure, for example `{"op": "unlink", "code": "EACCES"}`. The declarations are data. The comparator **verifies each one against pinned Pi on every row**, and refuses the matrix (INVALID) otherwise:
- **(a)** Pi's reported failure is a declared-terminal injection, or a native failure matching the row's signature.
- **(b)** A row whose injections are all `recovered` is `ok` in Pi.
- **(c)** A terminal injection's entry **remains** in Pi's drained state. A recovered injection's entry does **not**, unless it is an ancestor of a remaining failed entry.
- **(d)** In a natural row, Pi's reported path is the `rel` of a `fail` event in Pi's trace that matches the signature.

**R2 — complete traces, by row kind.** The acceptance branch is chosen by the **matrix row**, never by what the trace happens to contain.
- **Controlled row:** in both the oracle and binding traces, each fired injection appears **exactly once** as `settle op rel CODE`, with its matrix code. The fired set equals the injections minus `unfired`. Otherwise the row is **INVALID** (incomplete or forged trace).
- **Natural row:** the binding trace must contain at least one `fail` event matching the signature. Otherwise **INVALID**.

**R3 — selection.** The binding's selected failure is:
- **controlled row:** the **first `settle` event of a declared-terminal injection** in its own trace;
- **natural row:** the **first `fail` event matching the signature** in its own trace.

The binding must report that event's `rel`, with code `codes[injected code]` (controlled) or Pi's reported code (natural, the same host failure). Recovered faults and routine native failures are never selected. DIV-008 allows the selected **entry** to differ from Pi's, never the code or the origin of the binding's own selection.

**R4 — unchanged.** These checks are unchanged:
- readiness (INVALID for an undrained, timeout-settled or unfired oracle, or an undrained binding);
- extent against Pi's drained state;
- completeness (no binding-only unfired injection, no late calls);
- outcome agreement;
- the `codes` table verified against Pi.

**R5 — one model in both acceptance helpers.** The Python witness (`_violations`) reads the **same** declarations (copied into its oracle `div008_pi.json` by the generator) and applies R3. The shared comparator applies R1–R4. Neither runner re-implements §19.5 routing: terminality comes from the verified declarations, not from replaying rules.

## 4. Required controls (each credited only for its intended reason)

**Positives:**
- X1, X2, X3, X4 (recovered and terminal, in both orders, nested, directory);
- X5 (DIV-008 selection with a recovered fault between two terminal ones);
- B2 (recovered only, `ok`).

**Negatives:**

| Control | Expected | Reason |
|---|---|---|
| A recovered fault selected as the failure (the review-2 false negative, reversed into a check) | FAIL | selection |
| Trace omission: a controlled row with its `settle` events removed | INVALID | trace incomplete |
| A forged settlement: a `settle` with the wrong code, or a duplicated one | INVALID | trace |
| A natural row reporting an ancestor (`tree`) | FAIL | selection origin |
| A natural row with no matching `fail` event | INVALID | trace |
| A declaration that contradicts Pi: a terminal injection whose entry is removed, or a recovered one Pi selects | INVALID | declaration |
| Wrong code on the correct selection; undrained or timeout-settled rows (kept from remediation 1) | FAIL / INVALID | (as before) |

All controls run on **real** rows after a green baseline (`--controls`) and in the synthetic `--self-test`.

## 5. Feasibility

- **Python:** probe and test changes only. The production walk is unchanged.
- **Rust:** the Rust witness records the same trace grammar at its rimraf `Operations` seam (the injected `settle` and native `fail` events) and reads the same declarations. No new lower-layer API is needed (consistent with review 2's Rust note).
- **The matrix's declarations are checked against Pi on every run**, so they cannot silently drift.

## 6. Stop condition

The checkpoint is agreed when the reviewer accepts R1–R5 and the control list. Then the implementation pass:
- comparator v3;
- the matrix declarations;
- Python oracle and witness consistency;
- fresh Windows and Linux runs and gates.

After that comes the targeted closure of C002 and the final review of the changed pair.

## 7. Implementation of the agreed checkpoint

**R1 — declarations** (`div008-matrix.json`).
- Every injection has `outcome`. A child's classification `lstat` is `recovered` (B2 and X1–X5); every other injection is `terminal`.
- The natural rows N1/N2 have `signature: {op: unlink, code: EACCES}`.
- A `declarations` note records that they are verified against Pi on every row.

**R1–R4 — comparator v3** (`div008_compare.py`). It is rewritten to the agreed model:
- parses the trace grammar;
- verifies the declarations against Pi (a)–(d);
- requires complete traces by row kind;
- selects the first terminal failure;
- keeps readiness, extent, completeness and outcome.

The verdicts: MATCH, DIV-008 (selection only), FAIL, INVALID.

**Controls**, each credited only for its intended verdict **and** reason:
- **`--self-test`, 19 synthetic cases:**
  - positives: recovered then terminal; natural first matching failure;
  - recovered fault selected → FAIL;
  - wrong code with the right origin → FAIL;
  - controlled trace omitted, settlement duplicated, settlement code forged → INVALID;
  - natural ancestor origin → FAIL;
  - natural row with no matching failure → INVALID;
  - two declaration contradictions → INVALID;
  - the kept checks: extent, honest skip (completeness FAIL), late calls, outcome, binding or oracle undrained, timeout-settled, unfired oracle.
- **`--controls` on real rows, after a green baseline:**
  - X1-based, on both platforms: recovered selected, binding trace omitted, duplicated, forged, oracle trace omitted, wrong code, binding undrained, oracle timeout-settled, declaration flipped;
  - N1-based, Linux only (natural rows run only there): ancestor origin, no matching failure.

  Result: **9/9 on Windows, 11/11 on Linux.**

*One expectation corrected during implementation:* the self-test case "stop at first failure" had expected INVALID on the trace. An honest skip has a **consistent** trace (the skipped injection is reported unfired), so its correct verdict is FAIL on completeness. That is what v3 returns, and the expectation was corrected.

**R5 — one model** (`tests/execution/test_filesystem_remove_multi_failure.py`).
- `_Run` records `(op, rel, code)` per injected fault.
- `_violations` selects the first fault whose injection is declared `terminal`, from the same declarations, copied into the oracle `div008_pi.json` (25 rows) by the generator.
- New witness `test_recovered_fault_is_never_the_selection`: the real X1 run is accepted, and the same observation reporting the recovered `tree/a` is rejected on selection.
- 30 witnesses.

**F2 wording:** corrected in §2.

### Evidence (code `c479e6f49db724979befdbadd49fc78a4afb4ab9`; production unchanged since `521577b5`)

- **Pinned Pi over the 27-row matrix:** `div008-pi-{win32,linux}.jsonl`, which equal the CE-01 runs `ce01/ce01-pi-*`. All rows are drained, with no timeout settlement and no unfired injection.
- **Comparator v3, candidate `c479e6f4`, Windows:** exit 0. 20 MATCH, 5 DIV-008, 0 FAIL, 0 INVALID.
- **Comparator v3 on the CE-01 Python runs at `1339078d`:** Windows 20 + 5; Linux 19 + 26. This matches the checkpoint reviewer's independent replay.
- **Windows gates at `c479e6f4`:**
  - ruff, format (changed files) and mypy: clean;
  - pytest: **6321 passed, 43 skipped, 19 xfailed**;
  - coverage: **100.00%**.
- **Disclosure:** the Windows candidate probe ran while the Linux container gates were running. It is deterministic fault injection, so the concurrency does not affect its rows.
### 7.1 Linux (uid 1000, `python:3.13`, pinned ICU 78.3)

- **Gates at `c479e6f4`:** pytest **5929 passed, 422 skipped, 19 xfailed**. Container mypy shows the same 15 pre-existing platform/stub errors as every earlier Linux run.
- **Pinned-Pi replay:** a fresh run is identical to the committed `div008-pi-linux.jsonl` on **45/45** row-runs (result, path, drained extent).
- **Comparator v3, candidate `c479e6f4`:** exit 0. **19 MATCH, 26 DIV-008, 0 FAIL, 0 INVALID**. The X5 and natural-row DIV-008 selections are each the binding's own first terminal failure with its correct code.
- **Real-row controls:** **11/11** (`controls-candidate-c479e6f4-linux.txt`).

**Status:** the CE-L12D008-01 implementation is complete. `L12D008-C002` is ready for **targeted closure** by the reviewer, followed by the mandatory complete exact-SHA review. Rust: NOT_IMPLEMENTED. Cross-language: NOT CLOSED.
