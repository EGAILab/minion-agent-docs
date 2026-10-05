# WP-13.4 (`find`, `grep`): pinned-Pi characterization and engine pins

- **Coordination:** `minion-agent#51`, status CONTRACT_DRAFT.
- **Requirements:** `TOOL-036` (`find`), `TOOL-037` (`grep`), `TOOL-038` (engine pinning).
- **Binding Owner decision:** `TOOL-038` = `EXACT_MINION_PINNED_ENGINES`, recorded in #51's state block. It is applied under the practical-parity cut-over (2026-10-04).
- **Pinned Pi:** `b7bb00b936dbe21b8e160b3e89efdec361846699` (commit date 2026-08-19). Node `v22.15.1`.
- **Sources audited in full:**
  - `core/tools/find.ts` (380 lines);
  - `core/tools/grep.ts` (390 lines);
  - `utils/tools-manager.ts` (374 lines);
  - `core/tools/path-utils.ts` and `utils/paths.ts` (`resolveToCwd`, `pathExists`);
  - `core/tools/truncate.ts` (`truncateHead`, `truncateLine`, `GREP_MAX_LINE_LENGTH = 500`).

## 1. Engine pins (`TOOL-038`)

**Rule for choosing the versions.** Use the release that pinned Pi's own stage-3 acquisition (`getLatestVersion`, the GitHub "latest" release) would have downloaded on the pinned commit's date, 2026-08-19.
- **fd:** that was `v10.4.2` (released 2026-03-10). `v10.5.0` came out on 2026-08-26, after the pin.
- **ripgrep:** that was `15.2.0` (released 2026-07-15).
- The behaviour certified is therefore the behaviour pinned Pi had on a clean machine on the date of its revision, with no PATH or cache history involved.

**Assets.** The asset names are Pi's own `getAssetName` choices: fd `x86_64-unknown-linux-gnu` and ripgrep `x86_64-unknown-linux-musl` on Linux, and `x86_64-pc-windows-msvc` for both on Windows.

| Engine | Platform | Official artifact | Artifact SHA-256 | Extracted binary | Binary SHA-256 | `--version` |
|---|---|---|---|---|---|---|
| fd | win32-x64 | `https://github.com/sharkdp/fd/releases/download/v10.4.2/fd-v10.4.2-x86_64-pc-windows-msvc.zip` | `b2816e506390a89941c63c9187d58a3cc10e9a55f2ef0685f9ea0eccaf7c98c8` | `fd-v10.4.2-x86_64-pc-windows-msvc/fd.exe` | `4c9d082ee20f0d9e44881ac4e92adf765efc314d82103c53d7f576bd78dc5761` | `fd 10.4.2` |
| fd | linux-x64 | `https://github.com/sharkdp/fd/releases/download/v10.4.2/fd-v10.4.2-x86_64-unknown-linux-gnu.tar.gz` | `def59805cd14b5651b68990855f426ad087f3b96881296d963910431ba3143c8` | `fd-v10.4.2-x86_64-unknown-linux-gnu/fd` | `0dff4a420feb3e57fd1d4402d3e29f46115aa38d962467d2f3b72e7439d3ada8` | `fd 10.4.2` |
| ripgrep | win32-x64 | `https://github.com/BurntSushi/ripgrep/releases/download/15.2.0/ripgrep-15.2.0-x86_64-pc-windows-msvc.zip` | `71b2fef860abe467217a538ff31de02f5258807c0129f771846f87bd029aafc5` | `ripgrep-15.2.0-x86_64-pc-windows-msvc/rg.exe` | `14231169855ec5205cf5a1b6f1db358ff4aed4247c86b69ce8aae647c77f6680` | `ripgrep 15.2.0 (rev e89fff89ac)` |
| ripgrep | linux-x64 | `https://github.com/BurntSushi/ripgrep/releases/download/15.2.0/ripgrep-15.2.0-x86_64-unknown-linux-musl.tar.gz` | `33e15bcf1624b25cdd2a55813a47a2f95dbe126268203e76aa6a585d1e7b149c` | `ripgrep-15.2.0-x86_64-unknown-linux-musl/rg` | `e62198eb19b136b88c330af83647b5a962cb99b6b1f066758568f12de1974849` | `ripgrep 15.2.0 (rev e89fff89ac)` |

**How the hashes were verified.**
- Each artifact SHA-256 was computed locally after download, and equals GitHub's own recorded release-asset `digest` for that asset.
- For ripgrep, it also equals the upstream `<artifact>.sha256` file published with the release.
- The binary hashes were computed after extracting with the archive member paths above.
- Linux `--version` was observed in `debian:bookworm-slim` and `node:22.15.1-bookworm-slim`; Windows `--version` was observed on Windows 11.

The machine-readable record is `data/13-wp134/engines.json`. Other Pi-supported platforms (darwin x64/arm64, linux arm64, windows arm64) are **not certified**, because they are not observed. Pi's darwin/x64 `fd 10.3.0` exception is not adopted (TOOL-038).

## 2. Harness

`data/13-wp134/harness/search_probe.mjs` runs pinned Pi's own code under Node v22.15.1:
- `truncate.ts` is imported whole;
- `pathExists`, `resolveToCwd`, `normalizePath` and `resolvePath` are sliced unmodified;
- `find.ts` (`relativizeFindResultPath` and the `execute` body) and `grep.ts` (the default operations and `execute`) are sliced unmodified.

**The only substitution is `ensureTool`, which returns the pinned engine binary.** That substitution is exactly the TOOL-038 mapping.

**The corpus.** Two corpora, `plain` (no `.git` anywhere above the root; verified) and `repo` (a root `.git/`), are built fresh for each run. They contain:
- source and spec files at two depths, plus hidden files and directories;
- `.gitignore`d files, a nested repository (`nested/.git`) with its own `.gitignore`, and `node_modules`;
- Unicode names, a name with a leading space, and a space in a directory name;
- symlinks to a file and to a directory (a junction on Windows);
- CRLF, CR-only, BOM, invalid-UTF-8, long-line, binary, context, many-match and edge files;
- on Linux, a non-UTF-8 file name.

The bulk corpus has 1,200 files for `find`'s 1000/50 KB limits and a 120-line wide file for `grep`'s 100-match limit.

**Outputs:**
- `out/search-win32.json`: Windows 11, Node v22.15.1;
- `out/search-linux.json`: `node:22.15.1-bookworm-slim`, x86_64.

There are 79 `find` and 93 `grep` observations per platform, plus the bulk summaries. The corpus root is normalized to `<ROOT>`.

```text
node --experimental-strip-types harness/search_probe.mjs <pi checkout> <engine dir> <scratch dir> <out.json>
docker run --rm -v <pi>:/pi:ro -v <linux engines>:/eng-ro:ro -v <this dir>:/w node:22.15.1-bookworm-slim \
  sh -c "mkdir -p /eng /scratch && cp /eng-ro/* /eng/ && chmod +x /eng/fd /eng/rg && cd /w && \
         node --experimental-strip-types harness/search_probe.mjs /pi /eng /scratch out/search-linux.json"
```

## 3. Findings

**F-1. Cross-file order is nondeterministic (both engines, both platforms).**
- ripgrep searches files in parallel, so the order of per-file match blocks varies between runs. `grep/plain/regex-foo` differs between the two platform runs, and differs again across reruns.
- `fd` buffers and sorts its results only when the search finishes quickly. Small corpora came out sorted, but that is an engine heuristic, not a guarantee.
- Under a result limit, **which** results are returned is also traversal-dependent. With `limit: 2` and `limit: 1`, the two platforms returned different subsets.
- Within one file, `rg` keeps a file's matches contiguous and in line order.
- Pi defines no order of its own.

**F-2. On Windows, a full-path `find` pattern loses zero-directory `**` matches.**
- A pattern containing `/` gets `--full-path` and a `**/` prefix. On Windows, Pi then rewrites every `/` to `[/\\]`.
- That rewrite breaks globset's special `/**/` component, which can match zero directories. So `src/**/*.spec.ts` returns `src/sub/d.spec.ts` but not `src/b.spec.ts` on Windows, while Linux returns both (`find/*/full-path-spec`).
- This is a realistic pattern. Pi's behaviour here is a Windows defect.

**F-3. `.gitignore` handling differs between `find` and `grep` outside a git repository.**
- `find` passes `--no-require-git` when no ancestor has `.git`, so `.gitignore` applies.
- `grep` never passes it, so outside a repository `rg` ignores `.gitignore` completely (`grep/plain/gitignored` reports `ignored/g.ts`). Inside a repository it honours it.
- Inside a repository both stop the parent `.gitignore` at a nested repository's boundary (`find/repo/keep-boundary` finds `nested/keep.ts`).
- Outside a repository, `find`'s parent rules apply through `nested/`.
- `--hidden` exposes dotfiles. Under `--hidden`, `fd` lists `nested/.git/`; `rg` searches `.gitignore` itself.

**F-4. Pi's wrapper quirks: DIRECT_PI_PARITY, reproduced exactly.**
- **`find` limits.**
  - `limit: 0` passes `--max-results 0`, which `fd` treats as unlimited. Pi then appends "0 results limit reached. Use limit=0 for more, or refine pattern", because `relativized.length >= 0`.
  - A negative or fractional `limit` produces `fd`'s own usage error text (`limit-negative`, `limit-fraction`).
- **`grep` limits.** `effectiveLimit = Math.max(1, limit ?? 100)`.
  - `0` and `-1` both mean 1.
  - `2.5` returns 3 matches and reports "2.5 matches limit reached. Use limit=5", with `matchLimitReached: 2.5`.
- **`grep` context.** `context > 0 ? context : 0`.
  - A negative value means no context.
  - A fractional value such as `1.5` loops over fractional line numbers and prints lines like `ctx.txt-1.5- ` whose text is empty.
  - Overlapping context windows are **not merged**: each match prints its own block, so lines repeat.
- **Line endings.**
  - Context lines come from a re-read: Node `readFile(path, "utf-8")`, which keeps the BOM and replaces invalid bytes, then CRLF and CR are normalized to LF and the result is split.
  - Matches without context use `rg`'s `lines.text`.
  - So a CR-only file reports `cr.txt:1: xy matchz` without context, but with context the "match" label lands on re-read line 1 (`x`).
  - A BOM file shows U+FEFF only in context lines, because `rg` strips it from `lines.text`.
- **`fd` output lines** are `.replace(/\r$/, "").trim()`med, so a file named ` lead.ts` is reported as `lead.ts`. A directory match carries a trailing `/`.
- **A non-UTF-8 path.**
  - `fd` prints a lossy name (`raw-�.txt`).
  - `rg` reports the path as `path.bytes`, so Pi **counts** the match but does not collect it. The result text is the empty string, not "No matches found" (Linux, `grep/plain/raw-name`).
- **Errors.**
  - A missing `find` path, or a `find` path that is a file, surfaces `fd`'s stderr verbatim: `[fd error]: Search path '<abs>' is not a directory.` followed by `[fd error]: No valid search paths given.`, with native separators.
  - A missing `grep` path gives Pi's `Path not found: <abs>`.
  - An invalid regex surfaces `rg`'s stderr (`rg: regex parse error: ...`).
- **Path forms.** `@`-prefixed and absolute `path` arguments resolve through `resolveToCwd`.
- **Symlinks.** Neither engine follows them. A symlink is listed as an entry, but `link-dir/*.ts` finds nothing, and `rg` does not search through `link-file.ts`.
- **Binary files.** Under directory search `rg` skips them; given the file explicitly, it searches it.
- **Smart case.** An all-lowercase `fd` glob matches case-insensitively (`*.json` matches `y.JSON`).

**F-5. Limits and truncation at scale agree on both platforms.**
- 1,200 files with the default `find` limit return 1000 results, then `truncateHead` cuts them to 51,152 bytes and 867 lines. Both notices appear.
- `grep`'s default 100 matches at about 509 bytes each come to 50,891 bytes, under the 50 KB limit.
- With `limit: 1200`, exactly 1,200 files still reports "1200 results limit reached", because the check is `>=`.

**F-6. Platform differences are path separators in error text, plus F-1 and F-2.** Nothing else differs.

## 4. Owner questions raised (`minion-agent#51`)
- **Q1 (F-2).** Reproduce Pi's Windows full-path `**` defect, or correct it as a bounded practical-parity divergence.
- **Q2 (F-1).** Specify cross-file order as engine-defined and unspecified, keeping Pi's exact argument vectors, or impose a deterministic order.
- **Q3 (`TOOL-038`).** When does engine acquisition happen: lazily at first use, as in Pi but pinned and verified, or only through explicit provisioning, with no network access at tool-call time?

Everything else in §3 follows from the binding decisions and the default DIRECT_PI_PARITY classification of Pi's wrapper logic.
