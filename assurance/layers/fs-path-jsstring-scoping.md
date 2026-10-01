# Filesystem path JavaScript-string domain — scoping and options packet

**Issue:** `minion-agent#123` (SCOPING, provisional name, no layer or delta identifier yet).
**Authorized by:** Owner decision `minion-agent#49` comment `5942146215`, §2–§11.
**Author:** Claude. Characterization only: no production change.
**Pinned Pi:** `b7bb00b936dbe21b8e160b3e89efdec361846699`. **Node:** v22.15.1 (ICU 76.1).
**Evidence:** `assurance/layers/data/fs-path-jsstring/`.

| Artifact | What |
|---|---|
| `harness/path_probe.mjs` | Pi's own `normalizePath`/`resolvePath`, sliced unmodified from `utils/paths.ts`, then the exact Node fs operations Pi's tools perform: `mkdir(dirname)`+`writeFile`, `readFile`, `readdir`, `realpath` as the queue key. 10 names × {final component, directory component}, plus a collision case |
| `harness/url_probe.mjs` | `fileURLToPath` on raw and percent-encoded surrogates |
| `harness/py_path_probe.py` | certified Python main `c2cb4607` through the REAL tools (`write`/`read`/`edit`/`ls` via `execute_call`) and `ctx.fs` directly |
| `out/node-win32.json` | `85c41490…`, Windows 11 host |
| `out/node-linux.json` | `57f97aea…`, `node:22.15.1-alpine` |
| `out/python-win32.json` | `0596bf79…` |
| `out/python-linux.json` | `5b69a57d…`, `python:3.13`, no pinned ICU; see §3 |

## 1. Observed pinned Pi / Node behavior

| Step | Observation (Linux and Windows identical) |
|---|---|
| Pi's path helpers (`resolveToCwd` → `normalizePath` → `path.resolve`) | **unchanged code units** in all 20 cases. They only replace Unicode spaces, strip `@`, expand `~`, map MSYS drive paths and resolve; no surrogate is touched |
| Node fs operation (write, read, readdir, realpath) | **succeeds**. The projection happens when Node converts the JS String to a native path: each unpaired surrogate becomes **U+FFFD**, and a valid pair is kept as its astral character |
| actual filesystem name (`readdir`) | e.g. `fa\uD800b.txt` → `fa�b.txt`; `\uDC00\uD800` → `��`; a directory component is projected the same way |
| read after write | the same string reads the file back, **and so does its U+FFFD variant**: it is one file |
| collision | `a\uD800` and `a\uDC00` both name the file `a�`. The second write overwrites the first (read gives `B`). `realpath(a) === realpath(b)`, while `resolve(a) !== resolve(b)` |
| queue key (`realpath(resolve(p))`, falling back to `resolve(p)`) | once the file exists, the key is the **projected** name (≠ `resolve(p)`). For a missing file it is the **raw** `resolve(p)`. So two raw spellings of one missing file get different keys |
| Node error (`readFile` of a missing file) | `ENOENT`. `err.path` and the message carry the **projected** (U+FFFD) path, not the input |
| Pi tool text using `path` as given (e.g. "Successfully wrote … to ${path}") | JS interpolation of the input, so the **raw** code units are kept (per Pi source; not separately executed) |
| `file://` URL | a raw lone surrogate inside the URL string is replaced by U+FFFD **at WHATWG URL parsing** (pure JS, before any fs call). Percent-encoded `%ED%A0%80` makes `fileURLToPath` **throw**. A percent-encoded valid pair decodes to the astral character |

**The semantic projection boundary is the JS String → native path conversion inside Node's fs binding.** It happens neither in Pi's path code nor in a Node `path` helper, and it is the same on POSIX (UTF-8 path bytes) and Windows (wide API). That shows the replacement occurs before the platform-specific step. The only earlier projection is WHATWG URL parsing, and only for `file://` inputs.

**macOS:** not characterized (no macOS host available) → DEFERRED_WITH_REASON. Linux and Windows agree, which shows the projection occurs in Node's platform-independent string-to-path conversion. macOS (APFS, UTF-8 paths) is expected to agree, but that is not observed. Trigger: a macOS run of `path_probe.mjs` before any contract freezes macOS-specific claims.

## 2. Platform matrix

| Platform | Pi / Node | Python (certified main) | Rust (certified main) |
|---|---|---|---|
| Linux | U+FFFD filename; success | `ctx.fs` **raises `UnicodeEncodeError`** (escapes the `Result`; nothing written). Tools report Python's codec message as an error | refused before `ctx.fs` (see below) |
| Windows | U+FFFD filename; success | writes a filename holding the **raw unpaired code unit** (NTFS allows it). `ls`/`canonical_path` return it. No collision between `a\uD800` and `a\uDC00` | refused before `ctx.fs` |
| macOS | (expected U+FFFD; DEFERRED) | not run | not run |

## 3. Python current behavior (both platforms)

The real `write`, `read`, `edit` and `ls` tools pass the string unchanged to `LocalFileSystem`. That provider hands it to the OS API:
- **Linux:** Python's `os.fsencode` (`surrogateescape`) cannot encode D800–DBFF (or DC00–DC7F) → `UnicodeEncodeError`. That is not an `OSError`, so it escapes the provider's `Result` contract.
- **Windows:** CPython's wide-character conversion passes the surrogate through → the raw code unit is in the filename.

Scalar names (BMP, valid pair) behave like Pi on both platforms. On Linux, `edit`/`ls` additionally reported `PyICU … not loadable`, because the container lacks the pinned ICU build. That is environment-only and not part of these findings.

## 4. Rust current behavior

- `read`, `write` and `edit` take `path` with `PreparedValue::as_str()`. A non-scalar string yields `None` → error **"path is required"** before any filesystem access.
- `ls` uses the same call with `.unwrap_or(".")` → it **silently lists the working directory instead**.
- The Layer-12 `FileSystem` trait takes `path: &str` (`canonical_path`, `read_text_file`, `write_file`, …), so it cannot receive such a path at all.

## 5. Exact divergences

| ID | Binding | Divergence from pinned Pi |
|---|---|---|
| FSP-D1 | Python, Linux | `ctx.fs` raises `UnicodeEncodeError` (a `Result`-contract breach) instead of operating on the U+FFFD name |
| FSP-D2 | Python, Windows | filename holds the raw unpaired code unit instead of U+FFFD. Consequences: read/write identity, collision and `canonical_path` all differ |
| FSP-D3 | Rust, all | `read`/`write`/`edit` refuse with "path is required" |
| FSP-D4 | Rust, all | `ls` silently substitutes `"."`, a wrong target, not just a wrong error |
| FSP-D5 | both | queue `target_key` for such paths is not established. Pi: projected name if it exists, else raw `resolve(p)` |
| FSP-D6 | both (to verify) | `file://` paths: Pi projects a raw lone surrogate at URL parsing and throws on percent-encoded invalid UTF-8. Minion's certified file-URL handling (`L12-PY-R002`, ada) has not been probed with these |

## 6. Owning layer and semantic seam

- **The defect is at Layer 12's `ctx.fs` path seam, not in a tool.** In Pi, every tool passes the JS string through untouched, and the only projection is the host filesystem conversion.
- Both Minion bindings break exactly there:
  - Python's `LocalFileSystem` uses the OS's own conversion instead of Node's;
  - Rust's trait cannot carry the string, and the tools refuse it early.
- **Layer 13 has a secondary, mechanical part:** Rust's tools must stop refusing (and `ls` must stop substituting `"."`) once the seam can carry the value. Pi's tool text keeps interpolating the path as given.
- **The shared string primitive already exists.** The path value is the raw/prepared JS string (`L0206-D002`, `L0506-D002`), so no new representational primitive is needed.

**Is a lower-layer delta required?** **Yes: an additive Layer-12 extension.**
- `ctx.fs` path parameters accept the JavaScript-string domain.
- The host provider performs Node's projection (unpaired surrogate → U+FFFD) at the OS boundary, and nowhere earlier.
- `canonical_path` and `list_dir` report projected names.
- `target_key` follows Pi's realpath-or-raw rule.

The Layer-12 path-resolution rules (`resolve_local_path`, `file://` handling) need the FSP-D6 probe. Scalar behavior is unchanged.

**Can current certifications remain preserved?** **Yes.**
- Layer 12 (EXEC-001…009) was certified for scalar paths.
- WP-13.1 and WP-13.2 explicitly exclude lone-surrogate argument decoding (WP-13.2 does so verbatim).
- A scoped additive extension, like `L0506-D001/2/3`, leaves every certified scalar claim intact and adds the new domain.

## 7. Proposed options

**Option 1 — RECOMMENDED: an additive Layer-12 path-domain delta** (provisional ID `L12-D001`; the final ID is assigned by the decision).
- **Contract.** `ctx.fs` paths are JS strings. The local provider projects unpaired surrogates to U+FFFD only at the OS call, which reproduces Node: collisions, read-via-either-spelling and the projected `realpath`.
- **Keys and text.** `target_key` = projected canonical name when it exists, else the raw resolved string. Tool and result text interpolate the path as given. Errors that Pi takes from Node carry the projected path. `file://` follows Pi's URL-level projection and throws on percent-encoded invalid UTF-8.
- **Fixes:**
  - Python: one provider-level projection, fixing FSP-D1 and FSP-D2 together.
  - Rust: the trait accepts the JS-string type, and the tools stop refusing (FSP-D3/D4).
- **Evidence.**
  - Canonical cases generated from `path_probe.mjs` on Linux and Windows.
  - Negative controls: early projection in the tool, raw passthrough (the Windows-Python defect), refusal, `ls` substitution, and a wrong queue key.
- **Benefit.** It fixes `read`, `ls`, `write` and `edit` at once, and every future filesystem tool (WP-13.4 `find`/`grep` path arguments) inherits it.

**Option 2 — tool-level projection (Layer 13 only):** tools replace unpaired surrogates with U+FFFD before calling `ctx.fs`.
- It is cheaper. But it projects **earlier** than Pi, so result and error text would show U+FFFD where Pi shows the raw path, and the missing-file queue key would differ (decision §5).
- It must be repeated in every tool. Not recommended.

**Option 3 — intentional divergence:** both bindings uniformly refuse a path holding an unpaired surrogate, with one defined error.
- It is the smallest change and removes FSP-D1/D2/D4's wrong-target and contract-breach behavior. But it is observable divergence from Pi, where the operation succeeds.
- Acceptable only as an interim, explicitly labeled divergence if the Owner wants this deferred.

**Recommendation: Option 1.**
- Sequencing: it does not block anything in flight. It should be agreed before the WP-13.4 contract freezes `find`/`grep` path handling (or WP-13.4 records the same exclusion WP-13.2 did).
- A natural interim regardless of the option: Rust `ls` must not list a different directory (FSP-D4). That is wrong-target behavior, and it can be fixed under whichever option is chosen.

## 8. Dependency impact

| Work package | Impact |
|---|---|
| `L0206-D001` (#100, K1 key order) | none: independent value-order question |
| WP-13.3 (#50, `bash`) | minimal: `bash` takes a command string, not a `ctx.fs` path. A `cwd` override, if Pi exposes one, would inherit the Layer-12 rule. No blocking |
| WP-13.4 (#51, `find`/`grep`) | **direct**: path arguments and fd/rg output paths cross this seam. Agree Option 1 before WP-13.4's contract freezes, or WP-13.4 excludes it explicitly |
| future filesystem tools | inherit the Layer-12 rule (Option 1); under Option 2 each must re-implement it |
