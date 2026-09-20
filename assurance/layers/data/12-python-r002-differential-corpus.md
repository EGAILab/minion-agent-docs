# Layer 12 R002 differential corpus -- Node/Pi vs Python vs Rust

## Normative oracle

```text
pinned Pi (b7bb00b936dbe21b8e160b3e89efdec361846699)
    -> Pi resolvePath (nodejs.ts:51-65)
    -> Node url.fileURLToPath (nodejs.ts:20)
    -> Node path.isAbsolute / path.resolve
```

Node's OWN executable `fileURLToPath`/path-resolution behavior, at the Node runtime version pinned Pi actually declares support for, IS the normative oracle for this surface -- not a proxy for it, and not this corpus. Pi's own `engines.node` field pins `>=22.19.0`.

**Primary oracle version: Node v22.19.0** (the exact declared floor). Every value in the table below was generated against this exact version.

**Drift check: Node v22.23.2** (latest available 22.x as of this artifact). The full 68-case probe script was re-run verbatim against this version; the output was BYTE-FOR-BYTE IDENTICAL to v22.19.0 for every case, with no differences at all (`diff node_corpus_results_22.19.0.txt node_corpus_results_22.23.2.txt` -- empty). Also cross-checked against locally-available v22.15.1 (below Pi's declared floor) -- also byte-for-byte identical to both v22.19.0 and v22.23.2. **This is now an empirically confirmed non-issue across the entire 22.15.1-22.23.2 range, not an assumption.** Both downloads (`node-v22.19.0-win-x64.zip`, `node-v22.23.2-win-x64.zip`) were checksum-verified against Node's own published `SHASUMS256.txt` before use.

## Corpus role

This 65-case (68 generated, 3 platform-dependent excluded) corpus is **discriminating regression evidence and a representative acceptance suite** -- it is NOT an exhaustive definition of Node's own WHATWG URL/`fileURLToPath` algorithm. Additional differential/property probes against the SAME oracle (Node's own executable behavior at the pinned version) remain legitimate at any time without requiring a new semantic decision; they extend this corpus, they do not replace or redefine it.

Python candidate: frozen diagnostic candidate `d44ea0e2b46e18997a425e514c7ab8f458642f7d` (`minion-agent#44`), via `resolve_local_path` in `filesystem.py`.

Rust candidate: certified `2b309ee8` (`minion-agent-rust/crates/minion-agent/src/execution/filesystem.rs:534-589`), `resolve_local_path`/`expand_path`/`lexical_normalize`, reproduced VERBATIM (read-only, no modification to `minion-agent-rust/**`) in an isolated scratch Cargo project pinning the SAME `url = "=2.5.8"` (which pins `idna = "1.1.0"`) from `Cargo.lock`, to obtain a real differential result without touching the protected directory.

cwd for every case: `C:\cwd`. Three cases are excluded as platform-dependent/not meaningful for cross-implementation comparison: `/already/absolute.txt` (depends on the actual OS process cwd's drive letter), `~`, `~/x.txt` (depend on the actual `USERPROFILE`).

**Result: Python matches Node/Pi on 61/65 cases (93.8%). Rust matches Node/Pi on 48/65 cases (73.8%).**

Reproducible: `12-python-r002-scripts/` (same directory as this file) contains the exact probe
scripts (`node_probe.mjs`, `python_probe.py`, `rust_oracle_probe/`, `build_matrix.py`) and their
raw output, so this table and the version-drift comparison above can be regenerated
mechanically -- see `12-python-r002-scripts/README.md`.

| # | input | node/pi (oracle) | python (frozen) | rust (certified) | py match | rust match |
|---|---|---|---|---|---|---|
| 1 | `file:///C:/%ZZ` | `C:\cwd\file:\C:\%ZZ` | `C:\cwd\file:\C:\%ZZ` | `C:\%ZZ` | match | **MISMATCH** |
| 2 | `file:///C:/a%2Fb` | `C:\cwd\file:\C:\a%2Fb` | `C:\cwd\file:\C:\a%2Fb` | `C:\a\b` | match | **MISMATCH** |
| 3 | `file://%41/share` | `\\a\share\` | `\\a\share\` | `\\a\share\` | match | match |
| 4 | `file:///%ZZ` | `C:\cwd\file:\%ZZ` | `C:\cwd\file:\%ZZ` | `C:\cwd\file:\%ZZ` | match | match |
| 5 | `file://%zz-not-a-valid-escape` | `C:\cwd\file:\%zz-not-a-valid-escape` | `C:\cwd\file:\%zz-not-a-valid-escape` | `C:\cwd\file:\%zz-not-a-valid-escape` | match | match |
| 6 | `file:///C:/Users/test/file.txt` | `C:\Users\test\file.txt` | `C:\Users\test\file.txt` | `C:\Users\test\file.txt` | match | match |
| 7 | `file://localhost/C:/Users/test/file.txt` | `C:\Users\test\file.txt` | `C:\Users\test\file.txt` | `C:\Users\test\file.txt` | match | match |
| 8 | `file:///c:/foo/bar` | `c:\foo\bar` | `c:\foo\bar` | `c:\foo\bar` | match | match |
| 9 | `file://192.168.1.5/share/file.txt` | `\\192.168.1.5\share\file.txt` | `\\192.168.1.5\share\file.txt` | `\\192.168.1.5\share\file.txt` | match | match |
| 10 | `file:///C:/a%20b` | `C:\a b` | `C:\a b` | `C:\a b` | match | match |
| 11 | `file:///C:/a%252Fb` | `C:\a%2Fb` | `C:\a%2Fb` | `C:\a%2Fb` | match | match |
| 12 | `file://%2541/share` | `C:\cwd\file:\%2541\share` | `C:\cwd\file:\%2541\share` | `C:\cwd\file:\%2541\share` | match | match |
| 13 | `file:///C:/%25ZZ` | `C:\%ZZ` | `C:\%ZZ` | `C:\%ZZ` | match | match |
| 14 | `file:///` | `C:\cwd\file:` | `C:\cwd\file:` | `C:\cwd\file:` | match | match |
| 15 | `file://` | `C:\cwd\file:` | `C:\cwd\file:` | `C:\cwd\file:` | match | match |
| 16 | `file:///C:/a%5Cb` | `C:\cwd\file:\C:\a%5Cb` | `C:\cwd\file:\C:\a%5Cb` | `C:\a\b` | match | **MISMATCH** |
| 17 | `file:///C:/a%5cb` | `C:\cwd\file:\C:\a%5cb` | `C:\cwd\file:\C:\a%5cb` | `C:\a\b` | match | **MISMATCH** |
| 18 | `file:///C:/a%2fb` | `C:\cwd\file:\C:\a%2fb` | `C:\cwd\file:\C:\a%2fb` | `C:\a\b` | match | **MISMATCH** |
| 19 | `file://[::1]/C:/foo` | `\\[::1]\C:\foo` | `\\[::1]\C:\foo` | `C:\foo` | match | **MISMATCH** |
| 20 | `file://./share/file` | `\\.\share\file` | `\\.\share\file` | `\\.\share\file` | match | match |
| 21 | `file:////host/share/file` | `C:\cwd\file:\host\share\file` | `C:\cwd\file:\host\share\file` | `C:\cwd\file:\host\share\file` | match | match |
| 22 | `file:///C:/%` | `C:\cwd\file:\C:\%` | `C:\cwd\file:\C:\%` | `C:\%` | match | **MISMATCH** |
| 23 | `file:///C:/%2` | `C:\cwd\file:\C:\%2` | `C:\cwd\file:\C:\%2` | `C:\%2` | match | **MISMATCH** |
| 24 | `file:///C%3A/foo` | `C:\foo` | `C:\foo` | `C:\foo` | match | match |
| 25 | `file:///C:foo` | `C:\cwd\foo` | `C:\cwd\foo` | `C:foo` | match | **MISMATCH** |
| 26 | `file:///foo` | `C:\cwd\file:\foo` | `C:\cwd\file:\foo` | `C:\cwd\file:\foo` | match | match |
| 27 | `file:///C:/caf%C3%A9` | `C:\café` | `C:\café` | `C:\café` | match | match |
| 28 | `file:///C:/na%C3%AFve file.txt` | `C:\naïve file.txt` | `C:\naïve file.txt` | `C:\naïve file.txt` | match | match |
| 29 | `file://%25/share` | `C:\cwd\file:\%25\share` | `C:\cwd\file:\%25\share` | `C:\cwd\file:\%25\share` | match | match |
| 30 | `file://a%25b/share` | `C:\cwd\file:\a%25b\share` | `C:\cwd\file:\a%25b\share` | `C:\cwd\file:\a%25b\share` | match | match |
| 31 | `file://a.b.c/share` | `\\a.b.c\share\` | `\\a.b.c\share\` | `\\a.b.c\share\` | match | match |
| 32 | `file://EXAMPLE.COM/share` | `\\example.com\share\` | `\\example.com\share\` | `\\example.com\share\` | match | match |
| 33 | `file://a%23b/share` | `C:\cwd\file:\a%23b\share` | `C:\cwd\file:\a%23b\share` | `C:\cwd\file:\a%23b\share` | match | match |
| 34 | `file://a%40b/share` | `C:\cwd\file:\a%40b\share` | `C:\cwd\file:\a%40b\share` | `C:\cwd\file:\a%40b\share` | match | match |
| 35 | `file:///C:/%e2%98` | `C:\cwd\file:\C:\%e2%98` | `C:\cwd\file:\C:\%e2%98` | `C:%e2%98` | match | **MISMATCH** |
| 36 | `file:///C:/%ff%fe` | `C:\cwd\file:\C:\%ff%fe` | `C:\cwd\file:\C:\%ff%fe` | `C:%ff%fe` | match | **MISMATCH** |
| 37 | `file://xn--bcher-kva/share` | `\\bücher\share\` | `\\bücher\share\` | `\\xn--bcher-kva\share\` | match | **MISMATCH** |
| 38 | `file://xn--/share` | `C:\cwd\file:\xn--\share` | `C:\cwd\file:\xn--\share` | `C:\cwd\file:\xn--\share` | match | match |
| 39 | `file://xn--zzzz/share` | `C:\cwd\file:\xn--zzzz\share` | `C:\cwd\file:\xn--zzzz\share` | `C:\cwd\file:\xn--zzzz\share` | match | match |
| 40 | `file://xn--a/share` | `C:\cwd\file:\xn--a\share` | `C:\cwd\file:\xn--a\share` | `C:\cwd\file:\xn--a\share` | match | match |
| 41 | `file://XN--BCHER-KVA/share` | `\\bücher\share\` | `\\bücher\share\` | `\\xn--bcher-kva\share\` | match | **MISMATCH** |
| 42 | `file://host\share\file` | `\\host\share\file` | `\\host\share\file` | `\\host\share\file` | match | match |
| 43 | `file://HOST\Share\File` | `\\host\Share\File` | `\\host\Share\File` | `\\host\Share\File` | match | match |
| 44 | `file:///C:\Users\test` | `C:\Users\test` | `C:\Users\test` | `C:\Users\test` | match | match |
| 45 | `file://xn--fa-hia.de/share` | `\\faß.de\share\` | `\\faß.de\share\` | `\\xn--fa-hia.de\share\` | match | **MISMATCH** |
| 46 | `file://xn--strae-oqa.de/share` | `\\straße.de\share\` | `\\straße.de\share\` | `\\xn--strae-oqa.de\share\` | match | **MISMATCH** |
| 47 | `file://xn--zca/share` | `\\ß\share\` | `\\ß\share\` | `\\xn--zca\share\` | match | **MISMATCH** |
| 48 | `file://xn--abc-ppe/share` | `C:\cwd\file:\xn--abc-ppe\share` | `C:\cwd\file:\xn--abc-ppe\share` | `C:\cwd\file:\xn--abc-ppe\share` | match | match |
| 49 | `file://xn--abc-jdc/share` | `C:\cwd\file:\xn--abc-jdc\share` | `C:\cwd\file:\xn--abc-jdc\share` | `C:\cwd\file:\xn--abc-jdc\share` | match | match |
| 50 | `relative/path.txt` | `C:\cwd\relative\path.txt` | `C:\cwd\relative\path.txt` | `C:\cwd\relative\path.txt` | match | match |
| 51 | `file:///C:/` | `C:\` | `C:\` | `C:\` | match | match |
| 52 | `file:///C:` | `C:\cwd` | `C:\cwd` | `C:` | match | **MISMATCH** |
| 53 | `file://user_name.example/share` | `\\user_name.example\share\` | `\\user_name.example\share\` | `\\user_name.example\share\` | match | match |
| 54 | `file://-leadinghyphen.example/share` | `\\-leadinghyphen.example\share\` | `\\-leadinghyphen.example\share\` | `\\-leadinghyphen.example\share\` | match | match |
| 55 | `file://trailinghyphen-.example/share` | `\\trailinghyphen-.example\share\` | `\\trailinghyphen-.example\share\` | `\\trailinghyphen-.example\share\` | match | match |
| 56 | `file://a..b/share` | `\\a..b\share\` | `\\a..b\share\` | `\\a..b\share\` | match | match |
| 57 | `file://a.b.c.d.e.f/share` | `\\a.b.c.d.e.f\share\` | `\\a.b.c.d.e.f\share\` | `\\a.b.c.d.e.f\share\` | match | match |
| 58 | `file://0.0.0.0/share` | `\\0.0.0.0\share\` | `\\0.0.0.0\share\` | `\\0.0.0.0\share\` | match | match |
| 59 | `file://256.256.256.256/share` | `C:\cwd\file:\256.256.256.256\share` | `\\256.256.256.256\share\` | `C:\cwd\file:\256.256.256.256\share` | **MISMATCH** | match |
| 60 | `file://1.2.3.4.5/share` | `C:\cwd\file:\1.2.3.4.5\share` | `\\1.2.3.4.5\share\` | `C:\cwd\file:\1.2.3.4.5\share` | **MISMATCH** | match |
| 61 | `file://[::ffff:192.168.1.1]/share` | `\\[::ffff:c0a8:101]\share\` | `\\[::ffff:192.168.1.1]\share\` | `\\[::ffff:c0a8:101]\share\` | **MISMATCH** | match |
| 62 | `file://%E2%80%8B/share` | `C:\cwd\file:\%E2%80%8B\share` | `\\​\share\` | `C:\cwd\file:\%E2%80%8B\share` | **MISMATCH** | match |
| 63 | `not-a-file-url-at-all` | `C:\cwd\not-a-file-url-at-all` | `C:\cwd\not-a-file-url-at-all` | `C:\cwd\not-a-file-url-at-all` | match | match |
| 64 | `file:not-even-slashes` | `C:\cwd\file:not-even-slashes` | `C:\cwd\file:not-even-slashes` | `C:\cwd\file:not-even-slashes` | match | match |
| 65 | `file:/one/slash` | `C:\cwd\file:\one\slash` | `C:\cwd\file:\one\slash` | `C:\cwd\file:\one\slash` | match | match |
