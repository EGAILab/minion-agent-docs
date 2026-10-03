# WP-12.E4: convergence episode `CE-WP12E4-01`

**Trigger (§11.8 C):** four rejected reviews of WP-12.E4:
- audit 1 (docs #230 comment `5965735488`);
- audit 2 (`5966930540`);
- contract review 1 (`5969781012`);
- final complete review 1 (`5970101803`).

The episode covers the final review's three implementation findings. The earlier contract-side approvals (`CON-R001`/`R002`) are not reopened.

## 1. Findings (final complete review 1, code #138 @ `cedf9bec` / docs #230 @ `12489f65`)

| ID | Classification | Defect |
|---|---|---|
| `WP12E4-I001` | PI_PARITY_DEFECT | The native block was walked, and `CompareStringOrdinal` lengths were counted, in Python code points. After an astral entry the walk stopped one unit early and dropped every later entry. The test's child reader shared the bug |
| `WP12E4-I002` | PI_PARITY_DEFECT | An explicit high/low pair held as two surrogate code points was encoded as two 3-byte sequences, giving six U+FFFD and dropping a name, where Node gives the astral character |
| `WP12E4-I003` | CONTRACT_ASSURANCE_DEFECT | A declared `WINDOWS` world on a non-Windows host fell back to ASCII-only folding, weaker than the specified native comparison (`Qé` against `QÉ`) |

## 2. Characterization

- **The Windows name comparison.**
  - `ntdll!RtlUpcaseUnicodeChar` over all 65,536 UTF-16 units (Windows 11 build 26200) maps **973** units, none of them surrogates.
  - It maps `é` (U+00E9) to `É`. It leaves `ß` (U+00DF) and `ı` (U+0131) unchanged.
  - It agrees with `CompareStringOrdinal(ignoreCase)` on every mapped unit.
  - `GetEnvironmentVariableW("WPE4_QÉ")` finds a native `WpE4_Qé`.
  - So the OS's environment-name equality is: the same UTF-16 units after each passes through this table. That is consistent with `Qß`/`Qss` and `Qı`/`QI` staying distinct (characterization §9).
- **The pair encoding.** CPython's `encode("utf-8", "surrogatepass")` of two separate surrogate code points gives `ED A0 BD ED B8 80`, which decodes to six U+FFFD. Node's generalized UTF-8 of the same UTF-16 units gives `F0 9F 98 80`.

## 3. Checkpoint (proposed)

```text
CONVERGENCE CHECKPOINT (CE-WP12E4-01)
    PROPOSED

I001  the native block is walked in UTF-16 UNITS (each entry to its NUL; the block to the empty
      entry); every Windows length and comparison counts UTF-16 units
I002  WINDOWS native bytes: re-read the UTF-16 units (an explicit valid pair combines), then
      generalized UTF-8; only a genuinely unpaired unit is a 3-byte sequence
I003  WINDOWS lookup: equal UTF-16 units after the OS uppercase table, per unit -- on a Windows
      host the live table (any build); elsewhere the table captured from build 26200
      (windows_upcase.json, committed), so a declared WINDOWS world never depends on the host
      (spec/execution.md section 15.3)

WITNESSES (code minion-agent#138)
    I001  an entry after an astral entry survives: snapshot and inherit_env=True child (the
          child reader itself fixed to walk UTF-16 units)
    I002  explicit pair == astral character, in names and values; lone high/low -> three U+FFFD
    I003  Qé finds QÉ, astral differences stay distinct, Qss does not find Qß -- under a Windows
          host AND a simulated non-Windows host; the pinned table == the live table for all 65,536
          units; the OS's own GetEnvironmentVariableW agrees on a non-ASCII name
CONTROLS
    an ASCII-only fallback (I003); encoding without combining pairs (I002)
    the Owner's full C002 section 13 list, each now an explicit test:
      os.environ baseline; upper-casing every key; omitting native-only variables; base_env from
      another source; inherit baseline from another source; a construction-time cache;
      changing inherit_env=false; case-insensitive deletion of every MINION_* spelling
KNOWN-BAD (section 11.8.7.1)
    against the rejected source cedf9bec: the I001, I002 and I003 witnesses FAIL (5 failed);
    the lone-unit witnesses pass, as the old code already handled them
GATES
    pytest 4237 passed, 29 skipped, 19 xfailed; coverage 100.00%; ruff and mypy (100 files) clean
NEXT_OWNER
    Codex (checkpoint review)
```
