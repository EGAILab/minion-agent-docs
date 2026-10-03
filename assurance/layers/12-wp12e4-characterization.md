# WP-12.E4: execution-world environment and platform — characterization

**Work package:** `minion-agent#130` (CONTRACT_DRAFT), requirement `EXEC-010` (proposed).
**Authorization:** Owner decision `WP133-F1` = A and `WP133-F2` = A (`minion-agent#50` comment `5951046523`).
**Consumer:** WP-13.3 `bash` (`minion-agent#50`; `13-wp133-feasibility-matrix.md`).
**Author:** Claude. This is characterization, not a contract.
**Pinned Pi:** `b7bb00b936dbe21b8e160b3e89efdec361846699`, Node v22.15.1.

## 1. What the consumer needs, and the Pi behavior it must reproduce

Pinned Pi's `bash` touches the environment in three places:

| Site | Pi source | Operation |
|---|---|---|
| Git Bash discovery | `utils/shell.ts:79-86` | `process.env.ProgramFiles`, `process.env["ProgramFiles(x86)"]` |
| spawn-context build | `core/tools/bash.ts:169-182` | `env = {...getShellEnv()}`; `delete env.PI_*` (five keys); then set the live values |
| spawn | `bash.ts:104-110` | `spawn(shell, args, {env})` |

`getShellEnv` (`shell.ts:122-134`) is `{...process.env, [pathKey]: updatedPath}`. Minion adds no `PATH` entry today (Q1 §8), so Minion's equivalent of `getShellEnv()` is the world's base environment unchanged.

The decision's composition (§6): `env = copy(base_env())`, remove the five `MINION_*` keys, inject the live values, then spawn with `inherit_env = false`. The question for this delta is what `base_env()` must hold, and what that composition must do on each platform, so that the child observes what pinned Pi's child observes.

## 2. Windows: executable observations

**Harness:** `data/12-wp12e4/harness/`. **Outputs:** `data/12-wp12e4/out/`.
**Host:** Windows 11 (`10.0.26200`), Node v22.15.1, CPython 3.13.5, Git Bash 5.3.15 (`out/versions.txt`).

### 2.1 Node (the authority)

| # | Observation | Evidence |
|---|---|---|
| N1 | `process.env` keeps each name's **original case** and looks it up **case-insensitively**: a parent whose block holds `ProgramFiles` lists `ProgramFiles`, and `process.env.PROGRAMFILES` finds it | `node-dedup.json` `parentView` |
| N2 | A spread copy `{...process.env}` is a plain object: **case-sensitive**. `copy.PROGRAMFILES` is `undefined` when the name is `ProgramFiles` | `parentView.copyUpper = null` |
| N3 | When `spawn` receives an `env` object with names equal up to case, the child gets **exactly one** of them. It is the name that sorts **first by UTF-16 code units**, whatever the insertion order: `XK` beats `xk`; `xK` beats `xk`; `Xk` beats `xK` | `node-dedup.json`, `node-dedup2.json` |
| N4 | Names keep their case into the child. Git Bash then upper-cases **some** well-known names (`ProgramFiles` → `PROGRAMFILES`, `Path` → `PATH`) but leaves `ProgramFiles(x86)` and `Minion_Session_Id` unchanged, so name case is observable to commands | `node-msys.json` |

**Consequences for Pi `bash` on Windows:**
- **Discovery** reads `ProgramFiles` and `ProgramFiles(x86)` case-insensitively (N1).
- **The strip** deletes the five **exact-case** names from a case-sensitive copy (N2). An inherited case variant (`Pi_Session_Id`) survives the `delete`.
- **When the live value is injected** under the exact upper-case name, N3 makes the upper-case name win at spawn: an all-upper-case name sorts before every case variant of itself. So **with a live value**, the child sees only the live value.
- **When no live value is injected** (exposure disabled, no context, or that field absent), an inherited case variant **reaches the child** unchanged.

### 2.2 CPython 3.13 (the Python binding's local provider today)

| # | Observation | Evidence |
|---|---|---|
| P1 | `os.environ` **upper-cases every name** on Windows: `PROGRAMFILES(X86)`, `COMMONPROGRAMFILES(X86)` | `python-cpython313-win.json` `pyEnvironKeys` |
| P2 | `subprocess` with an `env` mapping whose names are equal up to case passes them through, and the child gets the **last-inserted** one: `{XK, xk}` → `xk`; `{xk, XK}` → `XK` | `upperFirst`, `lowerFirst`, `lowerThenxK` |
| P3 | A name's case reaches the child unchanged when there is no duplicate | `pfExact` |

**P1 ≠ N1 and P2 ≠ N3.** The existing Python `LocalSubprocess` builds its inherited environment as `dict(os.environ)` (`execution/subprocess.py::_effective_env`). Its children therefore see upper-cased names where a Node-spawned child sees the original case, for example `PROGRAMFILES(X86)` against `ProgramFiles(x86)` (observable through Git Bash, N4).

## 3. POSIX

POSIX environment names are case-sensitive byte strings. Node and CPython keep names as they are, and a mapping cannot hold two equal names, so N1–N3 and P1–P2 have no POSIX counterpart.
- **Discovery** never reads the environment on POSIX (`shell.ts:109-119`).
- **The strip** is exact-name deletion.

**DEFERRED_WITH_REASON (runtime confirmation):** a `node:22.15.1-bookworm-slim` probe of the same harness. The WP-13.3 Linux run already confirms POSIX `bash` end to end (`13-wp133-bash-characterization.md` §11). Trigger: the contract corpus run.

## 4. What this means for `base_env()`

**R1: identity of the snapshot.** `base_env()` returns the environment a spawn with `inherit_env = true` inherits in that world, before any overlay (decision §1). It is a snapshot taken when called (§4).
- Its names carry the **case the provider's spawn would give the child**.
- Lookup semantics follow the platform.

**R2: Windows name semantics are platform semantics, not a binding choice (decision §5).** On `WINDOWS` the snapshot is a mapping with:
- original-case names;
- at most one entry per case-insensitive name;
- case-insensitive lookup (N1).

On `POSIX` it is an exact-name mapping.

**R3: the duplicate rule belongs to spawn composition.** When a caller-built environment holds names equal up to case on `WINDOWS`, the child must receive the one that sorts first by UTF-16 code units (N3). This is Pi's observable behavior.
- Python's `subprocess` does the opposite (P2), so the rule cannot be left to the binding's spawn library.
- Decision §12 says E4 does not alter spawn or overlay semantics. The rule is therefore stated where Pi applies it: as part of the **consumer's** composition (WP-13.3 normalizes the environment it builds before `spawn`), with a shared helper. The certified `spawn` contract is untouched.

**R4: Python binding representation (finding, see §5).** A Python `base_env()` derived from `os.environ` would carry upper-cased names (P1). Pi's child sees original case. To match, the Python local provider's base environment on Windows must come from the process environment block with original case:
- `GetEnvironmentStringsW`, or an equivalent read;
- that is the same source a `CreateProcess` call with a null environment would hand the child.

Rust's `std::env::vars_os` already preserves case.

**R5: platform.** It is provider-declared, from the closed set `WINDOWS | POSIX` (decision §8). A local provider declares its host's family. A remote or fake provider declares its world's family (decision §9). It is not part of `ExecutionWorldIdentity` (decision §10).

## 5. Findings for the contract

```text
WP12E4-C001  CONTRACT_ASSURANCE (characterization)  Windows env name semantics
    Node: original case, case-insensitive lookup, spawn keeps the first name by
    UTF-16 order among case-equal duplicates. CPython: os.environ upper-cases
    names, and subprocess keeps the last-inserted duplicate. The contract states
    R2 (snapshot) and R3 (consumer composition); bindings MUST NOT rely on the
    spawn library's duplicate handling.

WP12E4-C002  PYTHON_BINDING (local provider)  base environment name case on Windows
    The Python LocalSubprocess's inherit_env=true environment is dict(os.environ),
    with upper-cased names. E4's base_env() is DEFINED as that environment
    (decision section 1), so a faithful base_env() keeps the upper-casing unless
    the local provider reads the original-case block. Proposed resolution: the
    Python local provider sources its base environment, for both base_env() and
    the inherit_env=true spawn, from the original-case block. This changes no
    certified contract text: section 6 says only "the provider's own
    base/inherited environment", and the name case was never specified or
    witnessed. Flagged for the reviewer: if the reviewer judges it a
    certified-behavior change, it goes to the Owner (#75 item 4).

WP12E4-C003  WP-13.3 consequence (Pi parity, recorded)  case-variant inherited MINION_* names on Windows
    With a live value injected, the child sees only the live value (N3). With no
    live value, an inherited case variant (Minion_Session_Id) reaches the child,
    exactly as Pi's PI_* case variants do (exact-case delete, N2). This is Pi's
    behavior mapped (Q1 section 7: "map Pi's actual behavior carefully"). It is
    not a new choice. The WP-13.3 contract states it, and witnesses it.
```

No finding here needs a new Owner decision.
- **C001** and **C003** follow Pi.
- **C002** is a binding-level representation fix. The decision delegated API spelling and representation (§§1, 5).

## 6. Independent audit 1 and Owner decision C002

**Codex audit 1** (docs #230 @ `740c9a03`; comment `5965735488`, verbatim):
- C001 and C003 are **confirmed**. All four probes reproduced.
- **`WP12E4-AUD-R001`:** C002 changes certified Layer 12 behavior, so it went to the Owner.

**Owner decision C002 = Option B** (`minion-agent#130` comment `5966459749`, verbatim). The baseline of the Python **Windows** local provider becomes the **live native process environment**, for `base_env()` and for `inherit_env = true` alike. This is a scoped amendment, not a divergence and not a Layer 12 reopen. POSIX is unchanged.
- Original spelling is kept.
- Native-only variables (`os.putenv`) are included.
- Removals are honored.
- The snapshot is taken per request.
- §9's witnesses A–D and §13's negative controls bind the contract.

R4 and C002 in §4 and §5 above are superseded by this decision. The text is kept as reviewed.

## 7. Non-Unicode values and snapshot timing (audit 1, Rust note; decision C002 §12)

**Node** is the authority here (`data/12-wp12e4/harness/nonutf8.sh`, `out/node-nonutf8-linux.json`, `node:22.15.1-bookworm-slim`).
- A POSIX environment value with invalid UTF-8 (`61 FF 62`) is decoded **lossily** into `process.env`: `a�b`.
- A child receives the re-encoded scalar form, `61 EF BF BD 62`. This holds for an explicit `env` object, which is what Pi's `bash` always passes, and for the default inherited environment.
- Node also re-reads `process.env` live at each spawn.

**CPython 3.12, POSIX** (`nonutf8py.sh`, `out/python-nonutf8-linux.json`):
- `os.environ` keeps the byte through surrogateescape (`'a\udcffb'`).
- `subprocess` hands the child the **raw** byte (`61 FF 62`).

**Rust**, accepted `main` `4c735ed6` (read-only; audit 1):
- `LocalSubprocess` captures `std::env::vars()` **once, at construction**, into `BTreeMap<String, String>`. `inherit_env = true` spawns `env_clear()` plus that map plus the overlay.
- `vars()` **panics** if any host name or value is not Unicode.
- `with_base_env` lets a test or fake world supply the map.

**Disposition:**

1. **The bash path needs no provider change.** WP-13.3 always spawns with `inherit_env = false` and the environment it built (decision §6). The WP-13.3 contract projects that environment's names and values to their **scalar form** (each unpaired surrogate or surrogateescape byte → U+FFFD) at the spawn boundary, as it does for `command` (`WP133-AUD-R001`).
   - This reproduces Node's child-observed bytes on every platform.
   - It changes no certified provider behavior.
2. **`base_env()` reports the provider's baseline as it stands when called.** That baseline is:
   - the live native environment for Python on Windows (C002);
   - the current `os.environ` for Python on POSIX (unchanged);
   - the configured map for Rust's `LocalSubprocess` (captured at construction, or supplied by `with_base_env`).

   In every case `base_env()` equals what `inherit_env = true` would inherit at that moment, which is the decision §1/§2 invariant.
3. **Recorded separately, per decision §6 and §12; not resolved here:**
   - **`E4-OBS-1` (Python, POSIX):** direct `inherit_env = true` children receive raw non-UTF-8 bytes, where Node children receive U+FFFD. Not reached by `bash` (disposition 1).
   - **`E4-OBS-2` (Rust):** the construction-time capture does not see host environment changes made later, while Node reads live. Rust Minion code is not known to mutate the host environment.
   - **`E4-OBS-3` (Rust):** a non-Unicode host environment panics provider construction.

   Each changes certified behavior only if acted on. Under decision §12 they are not acted on in E4 without a separate decision. The Rust owner sees them through the handoff.

## 8. Audit 2 and `WP12E4-AUD-R002`: how Node presents a non-Unicode environment

**Codex audit re-review 2** (docs #230 @ `4cee5d58`; comment `5966930540`, verbatim):
- `WP12E4-AUD-R001` is **CLOSED** (C002 integration).
- **New, `WP12E4-AUD-R002`** (CONTRACT_ASSURANCE_DEFECT): §7's "each surrogateescape byte → U+FFFD" is wrong.
  - CPython's surrogateescape keeps one surrogate per byte.
  - Node's UTF-8 replacement groups a valid incomplete prefix: `E1 80` gives one U+FFFD where per-byte replacement gives two.
  - An environment BOM is kept.

**Characterization (executed):**

- **POSIX** (`harness/envbytes_linux.sh`, `out/node-envbytes-linux.json`; `node:22.15.1-bookworm-slim`, uid 1000). Each value's raw bytes reach Node unchanged. `process.env` gives:

  | Raw value bytes | `process.env` value | Child receives (explicit `env`, as Pi's `bash` passes) |
  |---|---|---|
  | `61 FF 62` | `a�b` | `61 EF BF BD 62` |
  | `61 E1 80` | `a�` (**one**) | `61 EF BF BD` |
  | `61 E1 80 62` | `a�b` | |
  | `61 F0 90 80` | `a�` (**one**) | |
  | `61 ED A0 80 62` | `a` + **three** U+FFFD + `b` | |
  | `61 C0 AF 62` | `a` + **two** U+FFFD + `b` | |
  | `E2 82 AC E1 80 E2 82 AC` | `€�€` | |
  | `EF BB BF 61` | `﻿a` (**BOM kept**) | `EF BB BF 61` |

  This is exactly WHATWG UTF-8 decoding with replacement (one U+FFFD per maximal invalid subpart), and no BOM stripping. An entry whose **name** is not valid UTF-8 (`N_\xFF`) is **absent** from `process.env`, so a child spawned with an explicit `env` does not receive it. A valid non-ASCII name (`N_é`) is kept.

- **Windows** (`harness/envunits_win.py`, `out/node-envunits-win32.json`; Node v22.15.1, the native UTF-16 environment set through `_wputenv`):
  - `a\uD800b` → `process.env` `a` + three U+FFFD + `b`. That is the generalized-UTF-8 bytes of the lone surrogate (`ED A0 80`) decoded with replacement, the same rule as POSIX.
  - A valid pair is kept.
  - An entry whose name holds a lone surrogate is **absent**.
  - The grandchild receives exactly Node's view.

**Rule (proposed for the E4 contract, replacing §7 disposition 1).** The environment Pi's `bash` passes to its child is Node's view of the native environment, which is:

```text
native entry (name, value)            POSIX: bytes;  WINDOWS: UTF-16 code units
  -> bytes  (WINDOWS: generalized UTF-8 of the code units, lone surrogates as 3-byte sequences)
  -> name:  not valid UTF-8  => the entry is dropped
     value: WHATWG UTF-8 decode with replacement (maximal subpart), BOM kept
```

**Provenance boundaries (Codex's correction).** Two conversions must not be conflated:
- **OS bytes or units → JS string:** the rule above. It groups, and can drop an entry.
- **JS string → OS:** WP-13.3 `WP133-AUD-R001`, where each unpaired surrogate becomes U+FFFD. Applied after the first conversion, it is the identity: the decoded string is already scalar.

**What `base_env()` must therefore carry.** The rule needs the native form, so the snapshot must be **lossless** with respect to the provider's baseline. The consumer applies the rule; the provider does not.

| Binding / provider | Baseline | Lossless? |
|---|---|---|
| Python, POSIX | `os.environ` at call time (`str`, surrogateescape) | **yes**: `os.fsencode` recovers the bytes |
| Python, Windows (C002) | the live native block (`str` with any lone surrogate) | **yes** |
| Rust `LocalSubprocess` | the configured `BTreeMap<String, String>` | **yes, for every baseline it can hold**: a non-Unicode host panics at construction (`E4-OBS-3`), so no non-Unicode entry exists |

So **no provider behavior changes**. WP-13.3's composition applies the rule to the `base_env()` snapshot before stripping, injecting and spawning with `inherit_env = false`. §7 disposition 1 ("each … surrogateescape byte → U+FFFD") is **superseded**; the text is kept as reviewed.

**Witnesses for the contract:**
- every row above, on both platforms;
- the dropped invalid name;
- the kept BOM;
- negative controls: per-surrogate replacement (killed by `E1 80`), BOM stripping (killed by `EF BB BF 61`), and keeping an invalid-name entry.


**Audit 3 notes (nonblocking, docs #230 comment `5967993103`), resolved:**
- `envunits_win.py`'s header comment now says what the harness does: it passes an explicit UTF-16 block to the Node child, not `_wputenv`.
- In `out/node-envbytes-linux.json`, the valid name `N_é` has empty `childLineBytes`. The harness's `sh -c env | grep` intermediate does not keep that name. That field is therefore **not** evidence that Node dropped it. The evidence of retention is the Node-view `nameUnits`.


## 9. Contract review 1 and remediation

**Codex contract checkpoint review 1** (docs #230 @ `166e32a4`; it will be published verbatim): **CHANGES REQUIRED**.

- **`WP12E4-CON-R001`:** `EnvSnapshot` was never made read-only or isolated, as Owner F1 §§1, 2 and 12 require.
- **`WP12E4-CON-R002`:** native Windows name lookup and Node's spawn deduplication are two **different** equivalence rules. "Equal up to case" left the second undefined.

**Remediation:** `spec/execution.md` §§15.1, 15.3, 15.5 and 15.6.

- **R001 fix.** The snapshot exposes no mutator and is isolated from the provider in both directions. A consumer edits its own mutable copy. There are witnesses and a writable or aliased snapshot control.
- **R002 fix.** The native snapshot keeps exactly the native entries and uses the OS's own name comparison for lookup. The consumer-stage arbitration uses ECMAScript `toUpperCase` as the duplicate key, at the pinned runtime's Unicode version, and keeps the UTF-16-first name. There are wrong-equivalence controls.

**Executed authority** (Windows 11, Node v22.15.1):

- **Explicit `env` arbitration** (`harness/unicode_names.mjs`, `out/node-unicode-names-win32.json`), both insertion orders:
  - `Qß`/`Qss`: the child receives only `Qss=ss`. Both names uppercase to `QSS`.
  - `Qı`/`QI`: the child receives only `QI=ascii`. Both uppercase to `QI`.
- **Native block** (`harness/native_names.py`, `out/node-native-names-win32.json`; CPython supplies the block to the Node child, so Node does no explicit-env arbitration):
  - all **four** names enumerate as distinct entries;
  - `process.env.QSS` reads `ss` and `process.env.qi` reads `ascii`, an ASCII lookup answered natively;
  - `process.env['Qß']` reads `sharp` and `process.env['Qı']` reads `dotless`.

These reproduce Codex's review probes independently.

## 10. Contract re-review and Python implementation

**Codex targeted re-review** (docs #230 @ `6d8572d2`; comment `5969835483`, verbatim): **APPROVED**. `WP12E4-CON-R001` and `R002` are closed contract-side, and the non-ASCII probes were replayed byte-identical.

**Python implementation** (code `minion-agent#138` @ `cedf9bec`):

- **Provider.**
  - `Platform` and the read-only `EnvSnapshot`.
  - `LocalSubprocess.base_env()` and `_effective_env` both read `local_baseline()`, which keeps the C002 invariant.
  - On Windows that source is `GetEnvironmentStringsW`.
  - The `=`-prefixed per-drive records (`=C:=C:\`) are **excluded**. They are not variables. Observed under `cmd.exe`, `os.environ` and Node's `process.env` both omit them (scratch probe 2026-10-04). Disclosed here for the reviewer.
- **Windows lookup.** It uses the OS's `CompareStringOrdinal(ignoreCase)`. A fake Windows world on a POSIX host has no OS to ask, so it falls back to ASCII-only folding. That agrees with the native comparison on every ASCII name, and the specified consumers look up only ASCII names.
- **Consumer composition** (`tools/builtin/environment.py`):
  - Node's view, through UTF-8 with `surrogateescape` on POSIX and `surrogatepass` on Windows, then strict name decoding and `replace` value decoding.
  - Removal by exact spelling, then injection.
  - On Windows, arbitration keyed by `upper_unicode16`: ICU root full uppercase filtered to `[:age=16.0:]`, the same pattern as WP-13.2's NFKC. The UTF-16-first name wins.
- **Evidence.**
  - Pinned-Node rows: all POSIX values, invalid and valid names, Windows lone surrogates, and the non-ASCII and ASCII duplicate pairs in both orders.
  - C002 witnesses A–D: a snapshot, an `inherit_env=True` child and a `base_env()+inherit_env=False` child, compared by reading the child's **native** block. The rebuilt child equals the inheriting child exactly.
  - Isolation and per-drive records.
  - The Owner's negative controls: the `os.environ` baseline, a mismatched inherit source, a construction-time cache, per-surrogate replacement, BOM stripping, keeping an invalid name, lowercase / casefold / ASCII-only equivalence, last-inserted arbitration, and reading the host environment.
- **Gates.** `pytest` 4224 passed, 29 skipped, 19 xfailed; coverage 100.00%; `ruff` and `mypy` (100 files) clean.
