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
