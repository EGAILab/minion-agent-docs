# L12-D012: convergence episode `CE-L12D012-01`

Coordination: `minion-agent#229`. Work package record: `12-l12-d012-path-colon.md` (§§11–12). Template: kit `templates/convergence-record.md`; procedure: kit `WORKFLOW.md` §11.8.

```text
EPISODE             CE-L12D012-01
TRIGGER             C: four rejected complete reviews of L12-D012 (scoping 1, scoping 2, implementation
                    review 1, final complete review 1); `minion-process convergence counters 229`, 7 events,
                    nothing excluded. A is historical (C001, closed at scoping review 3); B not fired.
                    Default route TAKEN (RT-6; Owner notified): two targeted-fix exceptions were already
                    taken in this work package, so no further one.
OPEN FINDINGS       L12D012-PY-I002 (AUTHORITY_PARITY_DEFECT, blocking; final complete review 1,
                    #229 issuecomment-6177822640)
PROVISIONALLY CLOSED L12D012-PY-I001 (targeted closure, issuecomment-6177521281) -- retained
ROOT-CAUSE SURFACE  literal-port fidelity of the win32 drive-relative selection branch: the value Node
                    selects, and the positions it reads in it, are JavaScript-string UTF-16 code units
                    of Node's own process.env view -- not Python characters of the raw native entry.
```

The shared contract (`spec/execution.md` §3.2, §15; `path-resolution.json`) is **unchanged**. Neither dimension below needs a new rule: both are existing normative text that the Python port did not apply.

## 1. Characterization (native)

**Probe:** `data/l12-d012/ce01/unit_partition.py`, output `unit-partition-win32.json`; Windows, Node v22.15.1, pinned Pi `b7bb00b9`, candidate `8119d0ab`. It ran in a host window granted by Codex.
- **The children.** For each crafted `=A:` value, a **Python parent** launches a **Node child** (pinned Pi `resolvePath`, sliced unmodified: the oracle) and a **Python child** (the real `LocalFileSystem.absolute_path`) with **identical environment blocks**: ordinary variables plus exactly `=A:`.
- **The checks.** Each child reports, as UTF-16 units, the entry it actually received. The binding child must receive exactly the crafted one; the Node child's view is recorded.
- **The setting.** Provider cwd `C:\x`, input `a:leaf`. Pure computation.
- **Why a Python parent.** It is used because Node's own spawn cannot place a lone surrogate in a child's block.

| Crafted `=A:` | Node's view of it | Pinned Pi (Node) | Candidate binding | |
|---|---|---|---|---|
| absent | absent | `a:\leaf` | `a:\leaf` | MATCH |
| empty | empty | `a:\leaf` | `a:\leaf` | MATCH |
| `A:\deep` | same | `a:\deep\leaf` | same | MATCH |
| `é\deep` | same | `a:é\deep\leaf` | same | MATCH |
| `😀\deep` | same | `a:\leaf` | `a:😀\deep\leaf` | **DIFF** (unit 2 is `\`; character 2 is `d`) |
| `😀/deep` | same | `a:😀\deep\leaf` | same | MATCH |
| `x😀\deep` | same | `a:x😀\deep\leaf` | `a:\leaf` | **DIFF** (unit 2 is the low surrogate; character 2 is `\`) |
| `😀x\deep` | same | `a:😀x\deep\leaf` | `a:\leaf` | **DIFF** (unit 2 is `x`) |
| `😀` | same | `a:😀\leaf` | same | MATCH |
| `x😀` | same | `a:x😀\leaf` | same | MATCH |
| `A:😀\deep` | same | `a:😀\deep\leaf` | same | MATCH |
| `\uD83D\deep` (lone high) | **U+FFFD ×3** `\deep` | `a:<FFFD×3>\deep\leaf` | `a:\uD83D\deep\leaf` | **DIFF** (projection) |
| `x\uD83D\deep` | `x` **U+FFFD ×3** `\deep` | `a:x<FFFD×3>\deep\leaf` | `a:\leaf` | **DIFF** (projection, then units) |
| `\uDE00x\deep` (lone low) | **U+FFFD ×3** `x\deep` | `a:<FFFD×3>x\deep\leaf` | `a:\leaf` | **DIFF** (projection) |
| `éé\deep` | same | `a:\leaf` | same | MATCH |

**6 of 15 rows differ.** The three astral DIFF rows are exactly the reviewer's unit-indexing witness. Three lone-surrogate rows expose a **second dimension**.

**Dimension 1: the positions are UTF-16 units.** The branch is quoted verbatim in record §3.1: `StringPrototypeSlice(path, 0, 2)` and `StringPrototypeCharCodeAt(path, 2)`. Python `path[:2]` / `path[2:3]` index code points.

**Dimension 2: the selected value is Node's `process.env` view.** Node reads the entry through UTF-8. That is the **existing normative §15 rule** ("Node's view of the native environment": the generalized UTF-8 of the Windows UTF-16 units, then a WHATWG decode with replacement, one U+FFFD per maximal invalid subpart; the executed authority row "Windows value `a\uD800b` → `a`, three U+FFFD, `b`"). §15 states that it is normative **for every consumer that reproduces Pi's `process.env`**, and `win32.resolve`'s `process.env['=D:']` is such a read. The Python port passed the raw native value. It is already implemented, and certified, for WP-13.3 as `tools/builtin/environment.py::node_environment_view`.

## 2. Challenge and offset audit (the reviewer's requirement: audit every ported offset/length operation)

| Ported operation | Node reads | Python read before | Verdict |
|---|---|---|---|
| `_select_drive_base`: first two positions | `slice(0, 2)` (units), lower-cased | `path[:2]` (code points) | **WRONG** for astral (dimension 1) |
| `_select_drive_base`: third position | `charCodeAt(2) === \` (unit) | `path[2:3]` | **WRONG** for astral (dimension 1) |
| `_select_drive_base`: the selected value | `process.env['=D:']` (Node's view) `\|\| process.cwd()` | the raw native entry | **WRONG** for lone surrogates (dimension 2) |
| `_win32_root`: `path[0]` device-root letter, `path[1]` colon, separators | `charCodeAt(0/1)`, units | code points | **equivalent**. Every test compares against an ASCII character: a device needs an ASCII letter at position 0 and `:` at position 1, and positions 0 and 1 are the same characters in both views whenever position 0 is ASCII. An astral (or lone-surrogate) start is never a device in either view. Slices produce the same substrings |
| `_win32_root`: UNC component scan | index loops over separators | the same loops | **equivalent**: only ASCII separators are compared; the slices are identical strings |
| `_node_normalize_string`: `last_segment_length`, `len(res) < 2`, the `..` test | unit lengths | code-point lengths | **equivalent**. A length only decides together with "the last two units are `.`", which forces an ASCII `..` segment whose unit and code-point lengths agree. Other segments are not `..` in either view |
| `process_cwd()` (`os.getcwd()`) | `process.cwd()` through UTF-8 (libuv) | raw | **DEFERRED_WITH_REASON**: a lone surrogate in the process cwd needs a real directory with such a name as the process cwd. That is a filesystem fixture outside this lexical work package; the trigger is any such host |

A **refinement of PY-I002, not a new finding**: dimension 2 is the same root-cause surface (the selected value Node reads), found by the characterization this episode requires (§11.8.1).

## 3. Proposed fix (no contract change)

1. **`_select_drive_base` indexes UTF-16 units.** The first two units are compared, lower-cased, with the device, and unit 2 must be `\` (0x5C), computed on the value's UTF-16 encoding. `""` is still falsy.
2. **The inherited entry is Node's §15 view.** `inherited_drive_cwd` returns the decoded view: the generalized UTF-8 of the entry's UTF-16 units, WHATWG-decoded with replacement. That is the same projection as the certified `node_environment_view` value decode, applied locally because the execution layer cannot import tools (`test_layering`). An absent entry is still `None`, and an empty one is still `""`.
3. **Nothing else changes:** the hook, `_win32_root`, the loop and `normalizeString` (§2 audit).

## 4. Witnesses and controls (to be permanent)

- **W1 (real binding, win32):**
  - The 15 rows above are frozen as a Node-derived fixture (`tests/execution/data/node_inherited_entry_units.json`, regenerated by `unit_partition.py`).
  - A test launches a Python child with exactly each crafted entry (the real `LocalFileSystem`, the real `GetEnvironmentVariableW` read) and asserts Node's result.
  - All 15 rows must pass, including the 6 that fail at `8119d0ab`.
- **W2 (port, all platforms):** `node_win32_resolve` with injected `inherited` returning **Node's view** of each row's entry gives Node's result.
- **W3 (projection):** the decoded view against §15's executed table, covering lone high, lone low, a valid pair, a pair split across positions, and a BOM.
- **Controls** (known-bad → FAIL on the named rows; candidate → PASS):
  - **K1, code-point indexing** (`path[:2]` / `path[2:3]` restored) → `astral-backslash`, `x-astral-backslash`, `astral-x-backslash`;
  - **K2, the raw entry** (no projection) → `lone-high-backslash`, `x-lone-high-backslash`, `lone-low-x-backslash`;
  - **K3, per-surrogate replacement** (one U+FFFD instead of the WHATWG maximal-subpart decode) → the same three rows;
  - **K4:** the existing ASCII host-class controls (fall-through, mismatch-always-root, empty-is-a-value) and the PY-I001 entry-point refusal and omission controls stay green.
- **The 55 win32 and 25 linux canonical cases** stay green, and the canonical expectations are unchanged.

## 5. Cross-language feasibility delta (record §10)

The value-domain row "inherited `=D:` entry" now reads:
- **Pi:** Node's §15 view of the native entry (lone surrogates become U+FFFD per maximal subpart), indexed by UTF-16 units.
- **Python:** the §15 decode of the `GetEnvironmentVariableW` value, plus unit indexing.
- **Rust:** must also take its `var_os` value through the §15 view and index it by units.

The **Rust F001** implementation inherits both requirements; that is the note for the Rust handoff. The canonical corpus's host cases are ASCII. W1's fixture holds the non-ASCII rows as binding-level witnesses; it adds no canonical cases, and the contract text is unchanged.

## 6. Checkpoint (step 1, proposed)

```text
CONVERGENCE CHECKPOINT      PROPOSED FOR IMPLEMENTATION   (CE-L12D012-01)
OPEN FINDINGS               L12D012-PY-I002 (dimensions: UTF-16 unit indexing; Node's section 15 view
                            of the inherited entry)
ACCEPTANCE WITNESSES        section 1 partition (15 native rows) frozen as a Node-derived fixture;
                            W1 real-binding children; W2 port with Node-view inputs; W3 projection
                            against section 15's executed table; controls K1-K4; the 80 canonical
                            cases and PY-I001 controls unchanged and green
NORMATIVE DELTAS            none (spec section 3.2 and section 15 apply as written; canonical cases and
                            expectations unchanged); record section 10 feasibility row updated
NEXT_OWNER                  Codex (independent checkpoint review of exactly this proposal)
```

## 7. Checkpoint review 1 (REJECTED) and revision 1

**Checkpoint review 1** (Codex, `#229` issuecomment-6178272131, round 8) **REJECTED** the §6 proposal at docs `214dced4`.
- **Accepted:** the inherited-entry projection and the UTF-16 indexing model (§§1–3), the offset audit, W1–W3 and K1–K3.
- **The missing dimension:** the **other selected-value operand**, `process.cwd()`, used when the entry is absent or empty. Node obtains it through libuv `uv_cwd` (GetCurrentDirectoryW, then `uv__copy_utf16_to_utf8`) and `String::NewFromUtf8`, while the port passed raw `os.getcwd()`. §2's DEFERRED disposition was not a scope exclusion: §3.2's parity rule is not restricted to ASCII host state.

§§1–6 are kept as written; this section supersedes §2's process-cwd row and §§3–6 where it says so.

**The fixture plan** (`data/l12-d012/ce01/cwd_partition.py`) was safety-checked before running (issuecomment-6178360188), revised, and its intercepted `--self-test` (16/16, `cwd-partition-self-test.txt`) independently rechecked. It then ran **at docs `efeafd8f`** in a host window granted by Codex.
- **Authority and ancestry.** The authority is the fixed project root, and its ancestry was proven no-follow to `E:\`.
- **Preconditions** came before any mkdir: Node v22.15.1, and the pinned Pi `nodejs.ts` blob equal to `b7bb00b9`'s.
- **The fixture.** A new guarded sandbox `.tmp/claude-scratch/i229/cwd-fixture-1` holds five empty directories, kept, with no cleanup. That is 6 mkdirs, each proven before and after.
- **The children.** Each row ran a pinned-Pi Node child and a real-binding Python child with identical blocks and the same cwd. The binding's native entry read and its cwd equalled the crafted ones on every row. Output: `cwd-partition-win32.json`.

| Child cwd (in the sandbox) | entry absent | entry empty | entry `E:\deep` | control `a:leaf` |
|---|---|---|---|---|
| `plain` | MATCH | MATCH | MATCH | MATCH |
| `pair-😀` | MATCH | MATCH | MATCH | MATCH |
| `lone-\uD83D` | **DIFF**: Node `…\lone-<FFFD×3>\leaf`, binding `…\lone-\uD83D\leaf` | **DIFF** (same) | MATCH (cwd not selected) | MATCH (root) |
| `lone-\uDE00` | **DIFF** (`<FFFD×3>`) | **DIFF** | MATCH | MATCH |
| `x\uD83Dy` | **DIFF** (`x<FFFD×3>y`) | **DIFF** | MATCH | MATCH |

**6 of 20 rows differ**, exactly where the process cwd is the selected value and holds a lone surrogate. `cwd-view-check.txt` shows that Node's `process.cwd()` view of every crafted name **equals the §15 decode**: the generalized UTF-8 of its UTF-16 units, then WHATWG UTF-8 decoding with replacement. So a lone surrogate becomes three U+FFFD, and ASCII and valid-pair names are unchanged.

**Revised model (supersedes §3):** the selected value is **`view(process.env['=D:']) || view(process.cwd())`**, where `view` is the §15 decode, indexed by **UTF-16 units**. It is projected **only** at this native-read boundary:
- the caller's logical provider cwd and the path argument are never projected (§14.1's logical domain is unchanged);
- the decode is §15's, not §14.1's one-U+FFFD-per-surrogate fs projection.

**Revised fix:**
1. `_select_drive_base` indexes UTF-16 units: the first two units case-insensitively against the device, and unit 2 must be `\`.
2. The real host dependencies passed by the hook are **both** Node views: `inherited = view ∘ _libuv_win32.inherited_drive_cwd` (absent stays `None`, empty stays `""`) and `process_cwd = view ∘ os.getcwd`.
3. Nothing else changes; the §2 audit stands. **The DEFERRED row is withdrawn.**

**Witnesses and controls (supersede §4; additions):**
- **W1–W3 as §4.**
- **W4 (real binding, win32): a lone-surrogate process cwd.**
  - A permanent test creates directories with the crafted names inside pytest's contained `tmp_path` on E:. They are only used as a child's cwd and are never written.
  - It runs the real `LocalFileSystem` in a child there, with the entry absent and empty.
  - It asserts `<child cwd prefix> + <Node's view of the name, frozen from cwd-partition-win32.json> + \leaf`. The expected name view is Node's recorded output, not computed by the binding.
  - Positive neighbors: the ASCII and pair names, the matching-drive entry and the other-drive control.
- **K5, the raw process cwd** (no view): killed by W4's lone-surrogate rows.
- **K6, the projection moved to the logical side** (the provider cwd or the path argument viewed instead): killed by the existing L12-D001 `fs-path-names` `absolute_path` cases, whose logical lone-surrogate result stays raw, and by W4's matching-drive row.
- **K1–K4 as §4.**

**Feasibility (§5, revised):** Rust F001 inherits the complete boundary: both operands as §15 views (`var_os`, and `current_dir` as native UTF-16 put through the same decode) and UTF-16 unit indexing.

**Checkpoint (step 1, revision 1, proposed):**

```text
CONVERGENCE CHECKPOINT      PROPOSED FOR IMPLEMENTATION   (CE-L12D012-01, revision 1)
OPEN FINDINGS               L12D012-PY-I002 (UTF-16 unit indexing; Node's section 15 view of BOTH
                            selected-value operands: the inherited entry and the process cwd)
ACCEPTANCE WITNESSES        section 1 (15 entry rows) and section 7 (20 cwd rows) native partitions frozen as
                            Node-derived fixtures; W1 entry children, W4 cwd children (contained tmp_path
                            directories, child cwd only); W2 port with Node-view inputs; W3 projection vs
                            section 15; controls K1 code-point indexing, K2 raw entry, K3 per-surrogate
                            replacement, K5 raw process cwd, K6 projection on the logical side; K4 ASCII and
                            PY-I001 controls green; the 80 canonical cases unchanged
NORMATIVE DELTAS            none (sections 3.2 and 15 as written; expectations unchanged); record section 10
                            feasibility row updated; Rust F001 inherits the complete boundary
NEXT_OWNER                  Codex (independent checkpoint review of exactly this revision)
```

## 8. Checkpoint review 2 (REJECTED) and revision 2

**Checkpoint review 2** (Codex, `#229` issuecomment-6178582084, round 9) **REJECTED** revision 1 for one witness/control dimension.
- **Accepted:** the both-native-source model, view(entry) `||` view(process cwd) indexed by UTF-16 units, with **lazy** lookups so that a non-empty entry never reads the process cwd. Also accepted: the 15 + 20 measured rows, W1–W4, K1–K5 and the offset audit.
- **Missing:** §7's K6 claimed that existing cases would kill a projection moved to the logical side. They do not reach the touched branch. The L12-D001 `fs-path-names` `absolute_path` steps are relative names that bypass `_is_other_drive_relative`, and every logical input in the 35 new rows is ASCII. The **branch-local** mutant would survive: correct native views, plus the view applied to the logical `normalized` inside the hook. **The §7 claim that W4's matching-drive row catches logical-side projection is withdrawn.** W4 remains a selection and projection-bypass positive, not K6's kill witness.

**Revision 2: logical input through the other-drive branch.** The generator is `data/l12-d012/ce01/logical_partition.py`.
- **Children.** A Python parent launches pinned-Pi Node and real-binding Python children with identical blocks (plus exactly `=E:`).
- **Lossless logical transport.** The **logical input** travels as JSON UTF-16 units and is rebuilt **inside** each child (`String.fromCharCode` / `surrogatepass`), so no OS argv conversion turns it into another native-read test.
- **Checks.** The binding's native read of `=E:` must equal the crafted entry. Provider cwd `C:\x`.

**Rows and the source-predicted Pi value** (§3.1: a matching non-empty entry is selected; the caller's tail stays a raw logical component; the native entry takes the §15 view):

| Row | Native `=E:` | Logical input | Predicted Pi result (UTF-16) |
|---|---|---|---|
| scalar-positive | `E:\deep` | `e:leaf` | `e:\deep\leaf` |
| logical-lone-high | `E:\deep` | `e:leaf\uD800` | `e:\deep\leaf\uD800` (raw) |
| logical-lone-low | `E:\deep` | `e:leaf\uDE00` | `e:\deep\leaf\uDE00` (raw) |
| logical-pair | `E:\deep` | `e:leaf😀` | `e:\deep\leaf😀` |
| native-and-logical-nonscalar | `E:\de\uD83Dp` | `e:leaf\uD800` | `e:\de<FFFD×3>p\leaf\uD800`: native part decoded, logical tail raw |

The generator runs as the **first step of the implementation pass**, in a granted window. **If any Node observation differs from the prediction, implementation stops** and the checkpoint returns to characterization. The observed rows are frozen as a Node-derived fixture.

**New witnesses and controls:**
- **W5 (the logical tail through the touched branch).** The five rows are checked:
  - through the **real hook**: `resolve_local_path` / `LocalFileSystem.absolute_path`, with `_libuv_win32.inherited_drive_cwd` returning the row's raw native entry and the hook applying the view;
  - through the **pure port**, with Node-view inputs;
  - on win32, through **real-binding children** carrying exactly the crafted `=E:`.

  Each asserts Node's frozen result, including the raw logical `\uD800` / `\uDE00` units.
- **K6 (revised, branch-local).** The correct native views and unit indexing are **kept**, and the view is **additionally** applied to `normalized` only inside the other-drive hook. Against a green baseline, it must fail W5's raw-logical-tail assertions on `logical-lone-high`, `logical-lone-low` and `native-and-logical-nonscalar`, where it gives three U+FFFD at the caller's surrogate. It must pass `scalar-positive` and `logical-pair`, which delimit the domain.
- **K6b (global early projection).** The §14.1 one-U+FFFD fs projection applied to the logical argument before resolution is killed both by the existing L12-D001 cases and by W5. This keeps the one-replacement fs projection distinct from the three-replacement native view.
- **Retained:** W1–W4 and K1–K5 as §7; K4 (ASCII and PY-I001 controls) green; the 80 canonical cases unchanged.

**Checkpoint (step 1, revision 2, proposed):**

```text
CONVERGENCE CHECKPOINT      PROPOSED FOR IMPLEMENTATION   (CE-L12D012-01, revision 2)
OPEN FINDINGS               L12D012-PY-I002 (UTF-16 unit indexing; Node's section 15 view of both native
                            selected-value operands, read lazily; logical caller input preserved raw through
                            the touched branch)
ACCEPTANCE WITNESSES        sections 1 and 7 native partitions (15 + 20 rows) and section 8 logical rows (5;
                            Node-observed at implementation step 1, stopping on any disagreement with the
                            stated predictions) frozen as Node-derived fixtures; W1 entry children, W4 cwd
                            children, W5 logical tail through the real hook, the pure port and real-binding
                            children; W2 port; W3 projection; controls K1 code-point indexing, K2 raw entry,
                            K3 per-surrogate replacement, K5 raw process cwd, K6 branch-local logical
                            projection, K6b global fs projection of the logical argument; K4 ASCII and
                            PY-I001 controls green; the 80 canonical cases unchanged
NORMATIVE DELTAS            none (sections 3.2, 14.1 and 15 as written; expectations unchanged); record
                            section 10 feasibility row updated; Rust F001 inherits the complete boundary
NEXT_OWNER                  Codex (independent checkpoint review of exactly this revision)
```

## 9. Checkpoint agreement and the implementation pass

**Agreement.** Checkpoint review 3 (Codex, `#229` issuecomment-6178665172, round 10) gave **APPROVED / AGREED FOR IMPLEMENTATION** of exactly §8 (revision 2) at docs `32bf3b4a` and code `8119d0ab`. It is not the closure of PY-I002.

**Step 1: oracle confirmation** (Codex's grant, scheduled window). The generator `data/l12-d012/ce01/logical_partition.py` (sha256 of output `23d5607c…`) produced `logical-partition-win32.json`:
- Node `v22.15.1`, and `nodejs.ts` equal to the pinned blob at Pi `b7bb00b9` (`git rev-parse` vs `hash-object`).
- **All five predictions confirmed** (`all_predictions_confirmed: true`): each Node result equals the §8 prediction unit for unit. That includes `logical-lone-high` → `…leaf` + `0xD800` and `logical-lone-low` → `…leaf` + `0xDE00` (both raw), and `native-and-logical-nonscalar` → `e:\de` + `0xFFFD ×3` + `p\leaf` + `0xD800` (native part decoded, logical tail raw).
- The binding child's own read of `=E:` equaled the crafted entry on every row.
- **Disclosure:** the `binding` column was produced from the code worktree with the fix already edited in but not yet committed. That differs from `b7d046fe`'s `filesystem.py` only by the later `ruff format` line wrapping. It is therefore **not** `8119d0ab` evidence. The oracle confirmation is the **Node** column against the predictions, which does not depend on the binding.
- **No disagreement, so no stop.**

**The fixture.** `data/l12-d012/ce01/build_fixture.mjs` freezes the three Node-observed partitions as the binding fixture `tests/execution/data/node_selected_value.json`: 15 entry rows, 5 cwd names (name and Node view) and 5 logical rows. Rebuilding it from the committed outputs is byte-identical (sha256 `634ceeb8…`). It reads only committed JSON; it runs no process and does no resolution.

**The fix** (code PR #232 @ `b7d046fe406eb2db3b05a6112ed05bcbd289870e`, `filesystem.py`):
- `_select_drive_base` compares the first **two UTF-16 code units** and tests the **third code unit** for `\`.
- `node_native_string_view` is §15's view: the generalized UTF-8 of the UTF-16 units, then a decode with replacement.
- The other-drive hook passes `_native_inherited_view` (view of `_libuv_win32.inherited_drive_cwd`) and `_native_process_cwd_view` (view of `os.getcwd`) as the two lazy operands. `cwd` and `normalized` are passed raw.
- No contract or expectation change.

**Witnesses** (`tests/execution/test_path_resolution_selected_value.py`, 70 tests on Windows; every expectation comes from the Node fixture):

| ID | What it checks | Where |
|---|---|---|
| W1 | 15 entry rows, real-binding children with exactly the crafted `=A:` | win32 |
| W2 | the pure port with Node's entry view (15 rows) and the logical rows (5) | all platforms |
| W3 | the view against §15's authority, and against WP-13.3's certified `node_environment_view` | all platforms |
| W4 | the 5 cwd names × entry absent/empty, in contained `tmp_path` children (refuses A:/C:), plus the matching-entry and other-drive neighbors | win32 |
| W5 | the 5 logical rows through the real hook (in-process, scripted raw entry) and through real-binding children (logical input as UTF-16 units rebuilt in the child) | win32 |

**Negative controls (§11.8.7.1).** Each control first asserts a green baseline and then the **exact** set of failing rows. The kill is the observed set of failing row labels, never a rendering, and a setup error would surface as an exception, not as a row set.

| Control | Method (substitution at the seam) | Expected / observed failing rows | Candidate (`b7d046fe`) |
|---|---|---|---|
| K1 | `_select_drive_base` counting Python characters (the `8119d0ab` indexing) | the 3 astral rows / the same 3 | pass |
| K2 | `node_native_string_view` → identity (raw entry; the `8119d0ab` entry handling) | the 3 lone-surrogate entry rows / the same 3 | pass |
| K3 | `node_native_string_view` → `scalar_value_string` (one U+FFFD per surrogate) | the 3 lone-surrogate entry rows / the same 3 | pass |
| K5 | `_native_process_cwd_view` → raw `os.getcwd` (the `8119d0ab` cwd handling) | `lone-high`, `lone-low`, `lone-high-then-ascii` / the same 3 | pass |
| K6 | the correct views, **plus** `node_native_string_view(normalized)` inside the hook only | the 3 raw-tail rows; `scalar-positive` and `logical-pair` stay green / the same 3 | pass |
| K6b | §14.1's `native_path` applied to the logical argument before `absolute_path` | the `logical-lone-high` tail and L12-D001's raw `a\uD800` name / both changed | pass |

K1 + K2 + K5 together reconstruct the `8119d0ab` behavior component by component. K4, the ASCII rows and the PY-I001 entry-point refusal controls, stays green, and the 80 canonical cases are unchanged.

**Fresh gates** at `b7d046fe` (window granted by Codex; evidence in `data/l12-d012/python-implementation/remediation-2/`):

| Gate | Windows (pinned ICU 78.3) | Linux `python:3.13` (uid 1000, private tmpfs `/tmp`, E: binds inside the root) |
|---|---|---|
| focused (6 files) | 1081 passed, 4 skipped | — |
| pytest | 6779 passed, 43 skipped, 19 xfailed (+70 vs `8119d0ab`) | 6531 passed, 249 skipped, 19 xfailed (+29, the platform-neutral tests); exit 1 from coverage only |
| coverage | **100.00%** | 96.72%. Missed lines vs the base reference: `_libuv_win32` +15 and `filesystem.py` +6, all Windows-only (the base delta plus the win32 bodies of the two native-view helpers) |
| ruff check | 0 | 0 |
| ruff format (changed files) | 0 (whole tree: the 7 pre-existing files, unchanged) | — |
| mypy | 0 (118 files) | the base's 15 errors, an identical set |

Preflight was clear before each platform: 36.39 GB free (Codex), then 35.85 GB, with no active builds.

```text
CONVERGENCE IMPLEMENTATION  CE-L12D012-01 revision 2 implemented
CANDIDATE                   code #232 b7d046fe406eb2db3b05a6112ed05bcbd289870e; docs #306 (this commit)
FINDING                     L12D012-PY-I002 -- requested: PROVISIONALLY CLOSED @ b7d046fe (WORKFLOW 11.8.7)
REGRESSIONS                 PY-I001 controls, the C001 select-then-check closure, the 80 canonical cases
NEXT_OWNER                  Codex (targeted convergence closure; then the one final complete review)
```

## 10. Episode outcome

- **Targeted closure** (Codex, `#229` issuecomment-6179169609, round 11): **L12D012-PY-I002 PROVISIONALLY CLOSED** at code `b7d046fe` / docs `482d0c32`.
  - A fresh run of 250 tests passed.
  - Old code-point indexing plus the raw native view, substituted in memory, failed exactly 4 intended assertions (21 passed, no errors).
  - The original native 8-row probe gave 8/8 MATCH, against 3 mismatches at `8119d0ab`.
- **The final complete review 2** (issuecomment-6179335846, round 12) was **APPROVED** at the same frozen pair. PY-I002 is CLOSED. Merged code #232 → `8bb165e5`, docs #306 → `b2e8148c`.

**Episode CE-L12D012-01 is settled.** The shared contract is unchanged. Rust L12D012-F001 inherits the complete boundary of §§7–8: view(entry) `||` view(process cwd), read lazily, indexed by UTF-16 code units, with the logical caller input kept raw.

**Kit retrospective candidates** (WORKFLOW §14, to be filed against `EGAILab/minion-process`):
- **Every operand.** A characterization of a selected value covers every operand of the selection, the fallback as well as the primary; checkpoint review 1 rejected the omission of `process.cwd()`.
- **Origin through the touched branch.** A control claimed to protect logical-versus-native origin must be shown to reach the touched branch; checkpoint review 2 rejected kill witnesses that bypassed it.
- **Confirm before editing.** Run an oracle-confirmation step before the fix is edited into the measured worktree, so that its binding column is pre-fix evidence (§9 disclosure).
