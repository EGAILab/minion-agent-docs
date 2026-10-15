# L12-D013: win32 rooted drive-less input (scoping 1)

Status: **SCOPING, PROPOSED for independent scoping review.** Python is not corrected yet and no shared case has changed. Coordination: `minion-agent#235`. Delta of `EXEC-002`/`EXEC-005`. Class: governing, CP-6 (WORKFLOW 11.8.11(c)).

## 1. Source

- **Origin:** the `#229` Rust closure review 1 (issuecomment-6183035989).
- **Python:** merged Python resolves `\leaf` against the *provider* cwd's drive.
- **Pinned Pi:** resolves it against the *process* cwd's device.
- **Gap:** spec §3.2 says "an absolute result is used as-is (syntactically normalized)" without naming where the device comes from. The 80-case corpus has no win32 rooted drive-less row, which is why both certifications missed this.

## 2. Authority (pinned Pi, Node v22.15.1)

`resolvePath` (`nodejs.ts:51-65`, Pi `b7bb00b9`) is `isAbsolute(p) ? resolve(p) : resolve(cwd, p)`. `path.win32.isAbsolute` is true for every input whose first unit is `\` or `/`. Such an input therefore reaches `path.win32.resolve(p)` **without the provider cwd**.

`win32.resolve` (`lib/path.js` at v22.15.1) parses the input's root as follows:

- **One leading separator** (or the input is a single separator): `rootEnd = 1`, `isAbsolute = true`, device `''`.
- **Two leading separators:**
  - It is a UNC root only when `server`, one or more separators, and `share` follow, with both parts non-empty. Then the device is `\\server\share` and the input is used with that device.
  - Otherwise there is **no device and `rootEnd = 0`**, so the whole input, separators included, becomes the tail. Examples: `\\leaf`, `\\srv\`, `\\\leaf`.
- **An absolute tail with an empty device:** the loop reaches `i = -1` with `resolvedDevice` empty and takes `path = process.cwd()`. **No `=X:` entry is consulted.**
  - The cwd's own root parse supplies the device: `E:`, `\\localhost\E$`, or `\\?\E:` (parsed as server `?`, share `E:`).
  - The loop then ends. The cwd's tail is unused, because the input was already absolute.
- **Result:** `device + '\' + normalizeString(tail)`.
  - Both separators are accepted, and `\` is emitted.
  - Empty and `.` segments are dropped, and `..` is clamped at the root.

The `process.cwd()` operand is the one settled in CE-L12D012-02 R1 (libuv's `uv_cwd` single final-separator trim, then the native string view). Its read failure keeps the existing L12-D012 typed error, with no guessing.

POSIX is not affected: `/leaf` is absolute there and is used as-is.

## 3. Characterization (read-only, Codex-granted windows)

All children run with an existing directory as their cwd. Nothing is created, written, renamed or deleted, and results go to stdout only. Pinned Pi's `resolvePath` is sliced unmodified from the verified pinned blob.
- The Python source is `minion-agent-python/src` at `b7d046fe`, identical to main `83a78655`.
- The Rust observer is the ignored `native_observer` test built from `666e7365` (the code merged as `83a78655`), on the reviewer-only target.

| Run | Probe | Output | Dimensions |
|---|---|---|---|
| 1 | `rooted_probe.py` `b19a9160…` | `rooted-probe-1.json` `9dd52873…` | cwd {plain `E:\…`, root `E:\`, extended `\\?\E:\…`} × provider {`C:\x`, `E:\y`, `\\srv\share\x`, `\\?\C:\x`} × `=C:`/`=E:` {absent, present elsewhere} × 19 inputs; Node + Python |
| 2 | `rooted_probe2.py` `9235516f…` | `rooted-probe-2.json` `8fae1de1…` | run 1's partition, plus a UNC cwd `\\localhost\E$\…` and 6 more inputs (incomplete-UNC `\\srv\`; complete-UNC controls `\\srv\share`, `\\srv\share\leaf`, `//srv/share/leaf`, `\\srv\\share`, `\\.\leaf`); Node + Python + Rust |

Evidence, ledger and summarizers: `data/l12-d013/scoping/` (`SHA256SUMS`).

### 3.1 Results

- **Pinned Node.**
  - A result depends only on the cwd form and the input. The provider cwd and the inherited entries never changed it: 456/456 observations in run 1 and 800/800 in run 2.
  - Every drive-less rooted input took the process cwd's device: `E:\leaf`, `\\?\E:\leaf`, `\\localhost\E$\leaf`.
  - The incomplete UNC forms were treated as a whole tail: `\\leaf` → `E:\leaf`, `\\srv\` → `E:\srv`, `\\\leaf` → `E:\leaf`.
  - The complete UNC inputs kept their own device: `\\srv\share` → `\\srv\share\`, and `\\srv\\share` → `\\srv\share\`.
- **Rust** (`83a78655` code): **800/800 equal to Node** in run 2, across every cwd form including the UNC and the extended cwd.
- **Merged Python:** not equal to Node in every combination.

  | Python mismatch class | Example (Node → Python) | Cause |
  |---|---|---|
  | M1: the device comes from the provider | `\leaf`: `E:\leaf` → `C:\leaf`; extended cwd `\\?\E:\leaf` → `C:\leaf`; UNC cwd `\\localhost\E$\leaf` → `C:\leaf` | `os.path.isabs('\\leaf')` is false on Python 3.13, so the input goes through `os.path.join(provider_cwd, p)` |
  | M2: an incomplete UNC is kept as UNC | `\\leaf` → `\\leaf\`; `\\srv\` → `\\srv\\`; `//leaf`, `\/leaf`, `/\leaf`, `\\\leaf` similarly | ntpath's UNC split differs from Node's root parse |
  | M3: repeated separators inside a complete UNC root | `\\srv\\share`: `\\srv\share\` → `\\srv\\share` | ntpath does not collapse the separator run between server and share |

  Equal rows: only the complete-UNC controls `\\srv\share`, `\\srv\share\leaf`, `//srv/share/leaf` and `\\.\leaf` (4 of 25), plus the M1 inputs when the provider and process drives agree (18/25 for the `E:\y` provider with a plain or root cwd).

## 4. Proposed shared statement (spec §3.2, win32; DIRECT_PI_PARITY)

> On win32, an input absolute under Node's `path.win32.isAbsolute` is resolved as Node's `path.win32.resolve(input)`. In particular:
>
> - A **complete UNC root** is exactly two leading separators, a non-empty server, one or more separators, then a non-empty share; either separator may be used. It is the result's device. The rest is normalized. The root is emitted with single `\` separators and a trailing `\` when the tail is empty.
> - An input whose root has **no device** is resolved against the **process cwd's device**: a leading `\` or `/` that does not complete such a root, or a double-separator form that is not a complete UNC root.
>   - The device comes from the same root parse of the process-cwd native operand (CE-L12D012-02 R1): `X:`, `\\server\share`, or a namespace root such as `\\?\E:`.
>   - The provider cwd and inherited `=X:` entries play no part.
>   - The tail is the input after its one-unit root. For a double-separator form that is not a complete UNC root, the whole input is the tail.
> - The result is `device\` plus the normalized tail: `.` and empty segments dropped, `..` clamped at the root, `\` emitted.
> - A process-cwd read failure is the existing typed error.

This uses no Python or Rust mechanics. The drive-letter, drive-relative (L12-D012) and relative-input rules are unchanged.

## 5. Proposed canonical additions

The new rows are host cases using the existing crafted-child mechanism, with verified preconditions: the process-cwd drive is not the provider's, and the cwd form is as stated. They refuse fail-closed. Expectations are generated from pinned Node only.

| Group | Inputs | Purpose |
|---|---|---|
| R1 process device | `\leaf`, `/leaf`, `\`, `\..\leaf`, `\a\b\..\c` with provider `C:\x` and a process cwd on another drive | M1 |
| R2 incomplete UNC | `\\leaf`, `//leaf`, `\\srv\`, `\\\leaf` | M2 |
| R3 complete-UNC control | `\\srv\share\leaf`, `\\srv\share`, `\\srv\\share` | used as-is; M3 |
| R4 extended cwd | `\leaf` with cwd `\\?\E:\…` | the namespace device |

A UNC process cwd is characterized here (`\\localhost\E$`), but it is **not proposed as a canonical host case**, because it depends on the admin share. It is recorded as a characterization witness only.

## 6. Plan and stop condition

1. Independent scoping review (Codex) of §§2–5 and the evidence.
2. Shared cases plus the Python correction (M1–M3) on paired candidates, then independent Python review.
3. Rust revalidation against the new cases. Rust already matches 800/800, so a new Rust code change is not expected.
4. Closure. `#236` (the home source) stays separate.
