# Layer 12 Python convergence checkpoint reset -- CE-L12-PY-01-01

Mode: convergence checkpoint reset (`agent-workflow.md` §11.8, per an explicit owner directive
suspending further implementation until this characterization is independently reviewed).

This is a **characterization artifact**, not a remediation. It performs no implementation
change against `minion-agent#44`. It exists to invalidate and rebuild the convergence
checkpoint for `L12-PY-R002`/`L12-PY-R004` before any further implementation is attempted, per
the explicit reset instruction that produced it.

```text
IMPLEMENTATION AUTHORIZED
    NO
```

## Frozen diagnostic candidate

```text
minion-agent#44
d44ea0e2b46e18997a425e514c7ab8f458642f7d
```

Not modified by this artifact. `minion-agent-rust/**` also not modified (inspected read-only
throughout, per the standing Python/shared-owner boundary).

```text
Layer 13
    NOT STARTED
```

## Why the existing checkpoint is invalid

`CE-L12-PY-01-01`'s prior checkpoints for `R002`/`R004` are INADEQUATE. Both findings survived
FIVE targeted closure reviews after remediation attempts, each closing the immediately-prior
witness while (for R002) a new dimension of Node/WHATWG file-URL behavior kept surfacing, or
(for R004) the interpretation of "actual kill causation" kept being refined in a direction that,
this artifact demonstrates below, is now STRICTER than the behavior the already-certified Rust
implementation actually provides. Continuing the `witness -> patch -> witness -> patch` loop
without re-characterizing the underlying semantic surface would very likely have produced a
sixth, seventh, ... review cycle; this reset stops that pattern.

`L12-PY-R002` and `L12-PY-R004` remain **open**, not closed. No new finding ID is created for
either -- this is a checkpoint reset for the existing root causes, not a new finding.

---

# PART A -- L12-PY-R002

## Pi source-chain audit

Pinned Pi commit: `b7bb00b936dbe21b8e160b3e89efdec361846699` (local checkout verified at this
exact SHA before reading).

Exact chain, `packages/agent/src/harness/env/nodejs.ts`:

```text
import { isAbsolute, join, resolve } from "node:path";   -- line 18
import { fileURLToPath } from "node:url";                -- line 20

function resolvePath(cwd: string, path: string): string { -- lines 51-65
    let normalized = path;
    if (normalized === "~") {
        normalized = homedir();
    } else if (normalized.startsWith("~/") || (win32 && normalized.startsWith("~\\"))) {
        normalized = join(homedir(), normalized.slice(2));
    } else if (normalized.startsWith("file://")) {
        try {
            normalized = fileURLToPath(normalized);
        } catch {
            // Keep malformed URLs as ordinary paths so filesystem methods
            // preserve their non-throwing contract.
        }
    }
    return isAbsolute(normalized) ? resolve(normalized) : resolve(cwd, normalized);
}
```

**Pi-owned observable semantics** (the only logic Pi itself authors here):

- the three-way dispatch (`~` / `~/...` / `file://...` / else);
- home-directory expansion via `os.homedir()` + `path.join`;
- the catch-all "keep the malformed URL as a literal path" fallback on `fileURLToPath` throwing;
- final `isAbsolute` ? `resolve(normalized)` : `resolve(cwd, normalized)`.

**Node/WHATWG delegated semantics** (100% of the `file://` conversion logic itself):

- `fileURLToPath` -- percent-decoding, host validation (forbidden-code-point set, IPv4/IPv6
  host parsing and canonicalization, domain-to-Unicode/Punycode decoding, the encoded-`/`-and-
  `\`-rejection guard, drive-letter validation), backslash-to-`/` normalization at the
  WHATWG "special scheme" URL-parsing stage -- is a Node.js **runtime built-in**. Pi contains
  ZERO custom logic for any of this. Pi's own `fileURLToPath` behavior IS, by construction,
  whatever Node's own `url.fileURLToPath` does, for the exact pinned/available Node version.
- `path.isAbsolute` / `path.resolve` -- also Node built-ins, platform-dependent
  (`path.win32` vs `path.posix`, selected via `process.platform`).

**Platform-dependent semantics**: the entire `fileURLToPath` behavior branches internally on
target platform (Windows drive-letter/UNC handling vs POSIX `localhost`-only-host handling),
confirmed via Node's own `fileURLToPath(url, { windows })` override, used throughout this
artifact's own probing to get both platform modes from one host OS.

**Implementation mechanics** (not part of the observable contract, MUST NOT be encoded into the
language-neutral spec or manifest): the specific JS built-in call sequence, Node's internal
error types (`ERR_INVALID_URL`, `ERR_INVALID_FILE_URL_PATH`, `ERR_INVALID_FILE_URL_HOST`) --
only the fact that SOME rejection occurs (causing Pi's own catch-and-fallback), and the exact
fallback shape, are observable.

**Conclusion**: "faithfully reproducing Pi's observable `file://` behavior" is, without any
narrowing, EXACTLY EQUIVALENT to "faithfully reproducing Node's own `url.fileURLToPath`
behavior, for every input Node itself accepts as a `file:` URL." There is no intermediate
Pi-specific business rule to discover. This is precisely why witness-by-witness patching kept
finding new gaps: the true reference surface is Node's ENTIRE WHATWG URL implementation (host
parsing, IPv4/IPv6, IDNA/Punycode with full UTS46 validation, encoding-guard rules, backslash
normalization), not a bounded set of Pi-specific rules.

**Oracle version -- corrected, empirically verified** (an earlier revision of this artifact
generated its corpus against locally available Node `v22.15.1`, BELOW Pi's own declared
`engines.node` floor of `>=22.19.0`, and only asserted stability across the gap rather than
checking it -- not acceptable for a normative acceptance oracle, corrected here): every value
in the differential corpus was REGENERATED against a checksum-verified portable Node
`v22.19.0` (the exact declared floor -- `SHASUMS256.txt` match confirmed before use), used as
the **primary oracle**. A **drift check** against the latest available Node `v22.23.2` (also
checksum-verified) was then run over the identical 68-case probe script: the output was
BYTE-FOR-BYTE IDENTICAL to `v22.19.0` for every single case, zero differences. The original
`v22.15.1` run was also diffed against both and is likewise byte-for-byte identical. **The
WHATWG URL host-parsing algorithm's stability across this entire `22.15.1`-`22.23.2` range is
now an empirically confirmed fact, not an assumption or a disclosed-but-unresolved gap.**

## Normative oracle vs. corpus role -- corrected distinction

An earlier revision of this artifact's `Model A` wording risked treating the committed 65-case
corpus itself as the semantic DEFINITION of the delegated behavior. That would recreate the
same witness-chasing problem this reset exists to stop -- a corpus, however large, is always
finite; treating it as exhaustive invites exactly the "patch the named witness, miss the next
one" pattern that produced five failed review rounds. The hierarchy is corrected here
explicitly:

```text
NORMATIVE SOURCE
    pinned Pi behavior
        -> Pi resolvePath (nodejs.ts:51-65)
        -> Node url.fileURLToPath (nodejs.ts:20)
        -> Node path.isAbsolute / path.resolve

Therefore: Node's EXECUTABLE fileURLToPath/path-resolution behavior, at the Node runtime
version pinned Pi actually declares support for, is the normative oracle -- not this corpus,
not any finite list of examples.

CORPUS ROLE
    The committed 65-case corpus is discriminating regression evidence AND a representative
    acceptance suite. It is NOT an exhaustive definition of the delegated WHATWG/Node
    algorithm. Additional differential/property probes against the SAME oracle (Node's own
    executable behavior at the pinned version) remain legitimate at any time and do not
    require a new semantic decision -- they extend the corpus, they do not replace or
    redefine the normative source.
```

## Differential oracle corpus

Full corpus (65 comparable cases, 3 platform-dependent cases excluded) with all three
implementations' actual output, plus the full primary-oracle/drift-check version methodology:

`assurance/layers/data/12-python-r002-differential-corpus.md`

Equivalence classes covered: ordinary relative/absolute paths, `~`/`~/...`, empty-host and
`localhost` file URLs, Windows drive-letter and UNC URLs, raw-backslash normalization, valid
and invalid/truncated percent escapes, encoded path separators, UTF-8 percent encoding and
invalid UTF-8, ASCII and Unicode hosts, `xn--`/A-label hosts (valid under both IDNA2003 and
UTS46, valid only under UTS46, and invalid under both), mixed Punycode+ordinary-label domains,
underscores, leading/trailing hyphens, empty labels (bare `.` host), multiple dots, bidi-invalid
and combining-mark-invalid labels, IPv4 forms (valid, out-of-range octet, wrong segment count),
numeric-terminal hosts, IPv6 hosts (plain and IPv4-embedded, with canonicalization), a
zero-width-space host, and malformed authorities/URLs that trigger lexical fallback.

Reference values were obtained by literally invoking Node 22's own `url.fileURLToPath` (both
`{windows: true}` and `{windows: false}` modes) plus `path.resolve`'s own root-canonicalization
-- never inferred, guessed, or read secondhand from Python or Rust behavior.

### Result summary

```text
PYTHON (frozen d44ea0e) matches Node/Pi:  61 / 65  (93.8%)
RUST   (certified 2b309ee8) matches Node/Pi: 48 / 65  (73.8%)
```

### Python's 4 new mismatches (not previously exercised by any of the six review rounds)

| input | node/pi | python | root cause |
|---|---|---|---|
| `file://256.256.256.256/share` | rejects (falls through) | accepts as UNC host | no IPv4-octet-range validation -- `256` is out of range for an octet but Python's host check never validates numeric-dotted hosts as IPv4 candidates at all |
| `file://1.2.3.4.5/share` | rejects (falls through) | accepts as UNC host | same root cause -- 5 dot-separated numeric labels don't match valid IPv4, but Python never applies IPv4-shape detection either |
| `file://[::ffff:192.168.1.1]/share` | canonicalizes to `[::ffff:c0a8:101]` | keeps host verbatim, uncanonicalized | Python's IPv6-literal branch (`_file_url_to_path`) passes `parsed.netloc` straight through with zero IPv6 parsing/canonicalization |
| `file://%E2%80%8B/share` | rejects (falls through) | accepts, embeds U+200B (zero-width space) literally in the UNC path | Python's hand-picked `_FORBIDDEN_HOST_CHARS` set covers WHATWG's own listed forbidden code points plus `%`, but not the broader class of invisible/format Unicode characters WHATWG's real host-validation algorithm also rejects |

These are NOT the R002 findings under review (bidi/combining-mark labels, IDNA2003-vs-UTS46).
They are FOUR MORE, independently discovered dimensions, found the first time this artifact's
author built a corpus wider than "the examples named in the most recent review round" instead of
patching against single witnesses. This is direct, first-party evidence for the claim that a
hand-rolled implementation of Node's WHATWG host-parsing surface will keep finding new gaps
indefinitely.

### Rust's 17 mismatches (never previously characterized -- Rust has zero existing tests for any `file://` edge case beyond one trivial happy-path round-trip; confirmed by grep of `execution_filesystem.rs` and `filesystem.rs` itself)

Categories, with exact source citation for the Rust primitive responsible
(`minion-agent-rust/crates/minion-agent/src/execution/filesystem.rs:544-550`,
`expand_path`, delegating to the `url` crate's `Url::parse(...).to_file_path()`):

1. **Invalid/truncated percent-escapes are silently tolerated, not rejected** (`%ZZ`, bare `%`,
   `%2` truncated, `%e2%98` truncated UTF-8, `%ff%fe` invalid UTF-8) -- 5 mismatches (corrected;
   an earlier revision of this artifact miscounted this category as 6 -- the list above has
   exactly 5 items and the corpus data file confirms 5 rows). Node
   throws `URIError`/rejects the whole URL and Pi's own catch-and-fallback produces the literal
   string; the Rust `url` crate's percent-decoder is lenient and leaves an unrecognized escape
   in the output unchanged, so `to_file_path()` still succeeds where Node would have failed.
2. **Encoded path separators are decoded into real separators instead of being rejected**
   (`%2F`, `%5C`, `%5c`, `%2f`) -- 4 mismatches. Node's `fileURLToPath` has an explicit
   pre-decode guard rejecting these (a path-traversal/ambiguity guard); the `url` crate's
   `to_file_path()` has no equivalent guard at all.
3. **IPv6 literal hosts do not become UNC paths** (`file://[::1]/C:/foo` -> Rust: `C:\foo`,
   dropping the host entirely; Node: `\\[::1]\C:\foo`) -- 1 mismatch, but structurally
   significant: Rust's IPv4-textual-host UNC construction (`file://192.168.1.5/...` ->
   `\\192.168.1.5\...`, which DOES match Node) is asymmetric with its own IPv6-literal handling.
4. **Punycode hosts are never decoded to Unicode** (`xn--bcher-kva`, `XN--BCHER-KVA`,
   `xn--fa-hia.de`, `xn--strae-oqa.de`, `xn--zca`) -- 5 mismatches. Rust's `idna` crate (v1.1.0,
   pinned via `url = "2"` -> `Cargo.lock` pins `2.5.8`) DOES perform UTS46 validation for host
   ACCEPTANCE (confirmed: `xn--abc-ppe`/`xn--abc-jdc`, the bidi/combining-mark-invalid labels,
   are CORRECTLY rejected by Rust too -- these 2 cases are NOT mismatches), but
   `to_file_path()`'s own OUTPUT never applies the Unicode-glyph rendering step
   (`domainToUnicode`) Node's `fileURLToPath` applies -- it keeps the accepted ASCII `xn--...`
   label as the literal UNC hostname.
5. **Drive-relative (non-absolute) single-segment paths resolve differently**
   (`file:///C:foo` -> Rust: `C:foo` vs Node: `C:\cwd\foo`; `file:///C:` -> Rust: `C:` vs Node:
   `C:\cwd`) -- 2 mismatches. Rust's own `expand_path`/`resolve_local_path`/`lexical_normalize`
   chain does not apply the SAME "is this actually absolute, else join against cwd" logic Node's
   `path.isAbsolute`/`path.resolve` apply to a drive-relative (colon, no separator) path shape.

```text
5 (invalid percent-escapes) + 4 (encoded separators) + 1 (IPv6-to-UNC) + 5 (Punycode output)
+ 2 (drive-relative) = 17 total mismatches -- matches 65 - 48 = 17 exactly.
```

The overall `48/65` result is unchanged by this count correction (it was already computed
directly from the corpus data, not from the category labels) and is unchanged by the
Node-oracle-version correction above (byte-for-byte identical output confirmed across
`v22.15.1`/`v22.19.0`/`v22.23.2`).

### What this means for Rust's certification

`EXEC-002`/`EXEC-003` (the manifest rows covering this surface) are, as of this artifact,
recorded as `DIRECT_PI_PARITY`. That classification was never differentially validated against
a corpus wider than whatever the certifying Rust review happened to hand-check at the time (no
Rust-side test, unit or integration, exercises ANY `file://` edge case beyond one trivial
round-trip -- confirmed empirically: `grep -n "file://" crates/minion-agent/tests/execution_filesystem.rs
crates/minion-agent/src/execution/filesystem.rs` returns zero matches in either file). A 26%
observed mismatch rate against the SAME oracle this artifact holds Python to is not compatible
with an unqualified `DIRECT_PI_PARITY` classification for this specific requirement pairing.

```text
EXEC-002 / EXEC-003 (file:// URL conversion surface, Rust side)
    REVALIDATE_REQUIRED
```

This is scoped NARROWLY to the `file://`-URL-to-path conversion behavior specifically (i.e.
`expand_path`'s `Url::parse(...).to_file_path()` branch) -- it does not imply the rest of
`EXEC-002`/`EXEC-003`'s Rust implementation (ordinary path handling, `~` expansion, the
filesystem operations built on top of `resolve_local_path`) is in question; those were not
touched by this corpus and are not implicated.

## Research: existing Python WHATWG URL implementations

Per the project's research-first rule, evaluated candidates against this artifact's own corpus
before considering another hand-written parser, rather than selecting by name or IDNA-standard
claim alone.

| candidate | coverage against this corpus | known deviations | maintenance | dependency cost | verdict |
|---|---|---|---|---|---|
| `idna` (kjd/idna, PyPI) -- already adopted in the frozen candidate for Punycode/UTS46 host decoding | correctly decodes valid A-labels (incl. `ß`-containing ones IDNA2003 rejects) AND correctly rejects bidi/combining-mark-invalid labels via `idna.decode()` | does NOT implement IPv4-octet validation, IPv6 parsing/canonicalization, or the general WHATWG "forbidden host code point" set on its own -- it only validates/decodes the DOMAIN-host case, which is why the frozen candidate still hand-rolls the surrounding host-syntax logic (and currently gets 4 of that surrounding logic's cases wrong, see above) | actively maintained, widely used (pulled in transitively by `httpx` already) | already present, now explicit | correct for its OWN narrow scope (Punycode/UTS46 domain decode); NOT a full WHATWG URL/host parser by itself |
| `ada-url` (PyPI, Python bindings for the Ada C++ URL parser) | live-tested against this artifact's own corpus subset: correctly REJECTS `256.256.256.256`/`1.2.3.4.5` (`ValueError: Invalid input`), correctly CANONICALIZES `[::ffff:192.168.1.1]` -> `[::ffff:c0a8:101]` (both matching Node exactly, closing exactly the 3 of Python's 4 new mismatches above that are IPv4/IPv6-shaped) | its own `idna_to_unicode()`/`idna_to_ascii()` helper functions are LENIENT, not strict -- `idna_to_unicode('xn--abc-ppe')` returns the label UNCHANGED instead of raising for a bidi-invalid label, meaning naive use of `ada_url` alone would REOPEN the bidi/combining-mark finding this artifact is characterizing; would need to be paired with `idna`'s own stricter `.decode()` as a validation gate | Ada is the URL engine Node.js itself has used internally for its own `URL`/`fileURLToPath` implementation since Node 18.17 (i.e. this candidate is close to literally the SAME parsing engine as the oracle) | native extension (`cffi`-backed), installs cleanly via `uv pip install ada-url` in this environment, no build toolchain required (prebuilt wheel) | the most promising SINGLE candidate for the host-syntax/IPv4/IPv6 layer, but even combined with `idna` would still need a hand-written layer for `fileURLToPath`-SPECIFIC rules (encoded-separator rejection, drive-letter validation, backslash normalization) that neither library implements -- `ada_url.URL` is a generic WHATWG URL object model, not a file-URL-to-path converter |
| `urlstd` (miute, PyPI) | not evaluated -- **failed to install** in this environment | N/A | claims full WHATWG URL Standard incl. low-level APIs | depends on `icupy`, which requires building ICU C++ bindings via CMake; the build FAILED here (`CMake configuration failed`, `FindICU.cmake`) for lack of a discoverable system ICU install -- a real, demonstrated deployment/portability risk, not a theoretical one | disqualified on dependency-cost/portability grounds alone, independent of behavioral fidelity |
| `whatwg-url` (sethmlarson, PyPI) | not evaluated in depth -- installs cleanly, but... | ...implements the WHATWG URL Standard "as of 2018-08-26" (its own PyPI version string) -- roughly eight years stale relative to today; the Bidi/UTS46/IDNA rules this exact investigation cares about have been refined since. Also exposes only a generic URL object model (`.host` returns raw undecoded `xn--...`), no file-path-conversion utility | last release 2018; no evidence of active maintenance since | pure-Python, cheap to add | not evaluated further given the staleness -- unlikely to match current Node behavior on exactly the newest-standard edge cases this investigation is about, and provides no `fileURLToPath` equivalent to build on regardless |
| `upa_url` (Python bindings for the Upa URL library) | not evaluated (time-boxed out of this pass) | -- | used by Bun/Deno per its own description | native extension | a real remaining candidate for a follow-up evaluation pass; not ruled out, simply not reached |

**No off-the-shelf Python package reproduces Node's own `fileURLToPath` (the FULL algorithm:
WHATWG host parsing + Punycode/UTS46 + the encoded-separator guard + drive-letter validation +
backslash normalization) in one call.** The closest achievable composition identified in this
pass is `ada_url` (host syntax, IPv4, IPv6, forbidden-code-point set) + `idna`'s own stricter
`.decode()` (Punycode/UTS46 bidi/combining-mark validation, used as a gate rather than the
output-producing step) + a hand-written layer reproducing ONLY the `fileURLToPath`-specific
rules (encoded-`/`-and-`\` rejection, drive-letter validation, backslash-to-`/`
pre-normalization) that neither library attempts. This composition has NOT been built or
differentially tested in this pass -- it is a characterized, bounded next step, not a
completed implementation.

## Proposed R002 contract

**Model A (delegated WHATWG compatibility) is proposed**, consistent with the manifest's
existing `DIRECT_PI_PARITY` classification for this requirement pairing and with the Pi
source-chain audit above (Pi delegates 100% of this behavior to Node; there is no narrower
Pi-authored subset to fall back to without contradicting the manifest):

```text
For file:// input, Minion reproduces the observable output of the pinned Pi/Node file URL
conversion behavior (Node's own url.fileURLToPath, both platform modes) over the adopted
input domain, verified against the differential corpus in
assurance/layers/data/12-python-r002-differential-corpus.md as the acceptance oracle.
```

Model B (an intentionally narrower divergence) is NOT selected. Nothing in this investigation
found the full surface to be infeasible -- only that achieving it requires composing existing
libraries plus a bounded custom layer, which has not yet been attempted, rather than continuing
ad hoc hand-rolling. Selecting Model B here would require owner governance per
`agent-workflow.md` §11.10 and is not proposed.

The NEXT implementation pass (only after independent approval of this checkpoint) should:

1. Expand the differential corpus (this artifact's 65 cases, already committed as durable
   acceptance evidence) with any additional equivalence classes an independent reviewer
   identifies during checkpoint review, BEFORE writing new implementation code.
2. Prototype the `ada_url` + `idna`-as-gate + custom-`fileURLToPath`-layer composition sketched
   above against the FULL corpus, not a subset, before integrating.
3. If gaps remain after that composition, characterize them explicitly (per §7's own criteria:
   coverage, deviations, maintenance, cost) rather than patching around the specific witness.
4. Open a companion Rust-side revalidation task (scoped to `expand_path`'s `file://` branch
   only) against the SAME corpus, per the `REVALIDATE_REQUIRED` finding above -- this is Rust
   owner's own work, not something this artifact or its Python-side follow-up should attempt.

---

# PART B -- L12-PY-R004

## Rust's actual causal-classification mechanism (source-verified, not inferred)

`minion-agent-rust/crates/minion-agent/src/execution/subprocess.rs`, certified at `2b309ee8`
(verified: `git log --oneline -- .../subprocess.rs` shows no changes since; local working tree
is clean at this commit).

```text
CAUSE_NONE = 0, CAUSE_SIGNAL = 1, CAUSE_EXPLICIT = 2          -- lines 197-199
cause: Arc<AtomicU8>                                          -- per-Process shared state

Process::terminate() (lines 281-294):
    compare_exchange(CAUSE_NONE, CAUSE_EXPLICIT, AcqRel, Acquire)
    if that CAS succeeds: notify the monitor task once
    (a losing CAS, i.e. cause already claimed, is a complete no-op -- no kill re-attempted,
    no notification sent)

monitor_child() background task, spawned once at Process construction (lines 372-411):
    loop:
        try_wait() -- non-blocking check
            Some(status) => break immediately with that status (whatever `cause` currently is)
            None => (still running)
        if signal.aborted():
            compare_exchange(CAUSE_NONE, CAUSE_SIGNAL, AcqRel, Acquire)   -- eager, UNCONFIRMED
        if cause != CAUSE_NONE (set either by the line above OR by a concurrent terminate()):
            kill_process_tree(&mut child).await   -- issues the OS kill, AWAITED synchronously,
                                                      NO timeout on the external kill command
            break child.wait().await               -- then waits for the real process exit
        else:
            select! { child.wait() | terminate.notified() | sleep(5ms) }

    classify_exit(cause, exit_code):
        cause == CAUSE_SIGNAL -> Err(aborted)
        cause == CAUSE_EXPLICIT or CAUSE_NONE -> Ok(ExitStatus{exit_code})

    outcome.send_replace(Some(result))   -- the ONLY thing Process::wait() ever awaits
```

**`kill_process_tree` (lines 424-458) never touches `cause` at all.** Its own success or
failure (the external `kill`/`taskkill` command's exit status, or the `child.start_kill()`
fallback) has ZERO effect on classification -- `cause` was ALREADY claimed, via CAS, the
instant the poll loop observed `signal.aborted()` while `try_wait()` still reported the process
running, BEFORE `kill_process_tree` is even called.

**This is precisely the "eager, unconfirmed" model** -- classification is determined by
OBSERVATION ORDERING within the poll loop (did the loop see `signal.aborted()` at a moment it
still believed the process alive), not by any subsequent confirmation that the resulting kill
attempt actually found/killed a live target, succeeded to spawn its external helper, or
completed before the process happened to exit on its own for an unrelated reason.

**`Process::wait()` (lines 266-279)** awaits ONLY the shared `watch::Receiver`'s next value,
which is populated exactly once, at the very end of `monitor_child()` -- meaning `wait()`
effectively blocks until `kill_process_tree`'s own await completes too, not merely until the
target process exits. There is NO explicit timeout on the external kill command inside
`kill_process_tree` itself. **This is a real, disclosed asymmetry**: if the external `kill`/
`taskkill` command itself hung indefinitely (not the target process -- the KILL COMMAND
process), Rust's `wait()` would hang too. This is narrower than, and NOT covered by, the R004
open findings (which concern causal classification, not settlement timing under a hung kill
COMMAND specifically) -- flagged here as a genuine discovered gap for the Rust owner's own
consideration, not as part of the state machine below.

**Existing Rust test coverage for this surface** (`crates/minion-agent/tests/execution_process.rs`,
6 tests, all currently passing -- reconfirmed by direct `cargo test` execution, read-only, no
modification):

```text
spawn_is_argv_direct_and_wait_is_repeatable
piped_stdin_and_environment_are_typed_and_live
explicit_termination_is_success_with_the_os_reported_exit_code   -- discards its own exit_code
                                                                     assertion (`let _ = ...`)
cwd_uses_the_filesystem_lexical_normalization_rule
spawn_signal_controls_pre_and_post_spawn_cancellation             -- ONLY the clean-signal-kill
                                                                     case; no race/no-op/failure
missing_program_and_missing_cwd_are_spawn_errors
```

Plus 2 unit tests in `subprocess.rs` itself, both testing `classify_exit()` directly (not the
surrounding race/claim logic). **None of the discriminating scenarios central to this
investigation (states 7, 9, 10 below) have ANY existing Rust test coverage.**

## Reopening the shared causality wording

`spec/execution.md`'s own literal text (§6, the `wait()` classification bullet, lines 926-933):

```text
wait() returns Err(aborted) when the process was killed because the spawn-supplied signal
fired (at any point, before or after the wait() call itself) ... If both occur (the spawn
signal fires and the caller also calls terminate()), whichever caused the actual kill first
determines the classification; a terminate() racing a signal that already fired is a no-op
(idempotence, below) and does not change the classification the signal already established.
```

The phrase "whichever caused the actual kill first" is, in its LITERAL context, about the
SIGNAL-vs-EXPLICIT-TERMINATE race specifically -- it does not, on its own text, address whether
a kill attempt's own SUCCESS OR FAILURE (as opposed to which of the two triggering EVENTS
happened first) should gate classification. Successive Python review rounds generalized this
phrase into an increasingly strict "the kill must be CONFIRMED to have physically caused
termination" reading, and the certified Rust implementation does NOT implement that stronger
reading -- Rust's own `cause` is claimed BEFORE the kill is even attempted, based purely on
poll-loop observation ordering, exactly as characterized above.

## Two independent concerns, corrected

An earlier revision of this artifact combined two genuinely SEPARATE concerns into one "Option
A" proposal:

```text
A. which cause classification wins           (a claim/state-machine question)
B. when wait() is allowed to settle            (a settlement-timing question)
```

The classification model (A) is useful and IS what Rust's own certified source demonstrates.
The settlement rule the earlier revision attached to it (B: "wait() never awaits kill-helper
confirmation") is NOT what Rust's own certified source does, and asserting Rust "satisfies"
that combined model was WRONG. These are corrected as two separate subsections below,
R004-A and R004-B, and the earlier revision's claim that "Rust satisfies Option A 15/15" is
withdrawn.

## R004-A -- cause classification (deterministic first-claim model)

This part of the model is retained, defined independently of kill-helper completion:

```text
state: cause ∈ {NONE, SIGNAL, EXPLICIT}, initially NONE.

Signal claim:
    If the process monitor observes the spawn-time signal as aborted() while its LATEST
    process-liveness observation says the process is still live:
        CAS NONE -> SIGNAL

Explicit termination claim:
    terminate():
        CAS NONE -> EXPLICIT

First claim wins:
    Once cause != NONE, later SIGNAL or EXPLICIT claims do not replace it.

Classification, at final process outcome:
    cause == SIGNAL     -> Err(aborted)
    cause == EXPLICIT   -> Ok(ExitStatus)
    cause == NONE       -> Ok(ExitStatus)
```

The classification MUST NOT depend on proving which kill request physically caused the OS
process to terminate. The success or failure of the kill mechanism itself MUST NOT
retroactively change a cause already claimed. This is the corrected reading of the shared
contract's own ambiguous phrase "whichever caused the actual kill first" (`spec/execution.md`
§6, lines 926-933) -- replaced here with deterministic, observable state-machine language
rather than a phrase that can be (and was, across five review rounds) read progressively more
strictly.

**Rust's own source (`subprocess.rs:197-199, 266-294, 372-411`) matches R004-A exactly**: the
CAS happens the instant the poll loop observes `signal.aborted()` at a still-believed-running
liveness check, BEFORE `kill_process_tree` is even called; that function's own success/failure
is never read back for classification (verified above, unchanged from the prior revision).

**Consequence for the frozen Python candidate**: `d44ea0e`'s `L12-PY-R004` design (round 6)
gates `_kill_cause` recording on `_KillIssue.issued` (whether the OS-level kill command was
successfully ISSUED) -- this makes classification depend on the KILL MECHANISM's own outcome,
which R004-A (and Rust's own certified behavior) explicitly says MUST NOT happen. **The round-5
targeted closure review's own counterexample (a failed Windows `taskkill` spawn must not
classify `Err(aborted)`) demanded behavior STRICTER than what is actually certified in Rust.**
Aligning Python with R004-A means REMOVING the `issued` gate, reverting toward the round-4/5
design's own eager-claim shape -- the opposite direction from where the last two rounds moved.
**This part of the correction is NOT authorized for implementation yet** -- see the settlement
question below, which is unresolved and affects how this classification model interacts with
`wait()`'s own contract.

## R004-B -- wait() settlement timing (Rust implementation defect against the RETAINED contract)

**Corrected per independent checkpoint review** (`minion-agent-docs#120` @
`ca91006402ecf952f5e73691eca684d60ee3edaa`, finding `C12-RESET-R001`): an earlier revision of
this section presented "process-exit-only settlement" and "settlement may await termination
machinery" as two co-equal, currently-undecided policy options. That was wrong. The current
authority chain ALREADY resolves this question -- `spec/execution.md` §6 explicitly states
that `wait()` settles on the process's own exit alone. An implementation contradicting that
text does not make the normative rule undecided, and certified Rust source is not itself a
semantic authority that can implicitly reopen an already-settled contract clause. Documented
exactly, from Rust's own source:

```text
Rust's actual settlement sequence (subprocess.rs:372-411), when a cause is claimed:

    monitor_child() loop:
        cause claimed (by either path)
        -> kill_process_tree(&mut child).await     (AWAITED, no timeout on the external
                                                       kill/taskkill command itself)
        -> break child.wait().await                 (then, only after that, awaits the real
                                                       process exit)
        -> outcome.send_replace(Some(result))        (Process::wait() awaits ONLY this)

Therefore: Process::wait() CANNOT return before the monitor task has finished awaiting
kill_process_tree() AND the process's own exit AND published the outcome. A delayed or hung
EXTERNAL kill-helper process (not the target process itself -- the "kill"/"taskkill" command
process) can therefore delay, or in the hung case indefinitely block, wait() -- even though the
target process may have already exited on its own by then.
```

**Retained current contract**: `wait()` settles on the target process's own exit alone,
independent of any kill-helper's own completion, matching `spec/execution.md` §6's existing,
already-agreed literal text.

**Rust's settlement sequence above is a narrowly-scoped IMPLEMENTATION DEFECT against that
retained contract**, requiring Rust-side revalidation/remediation by Rust's own owner -- it is
NOT a competing policy option available merely because it matches Rust's current behavior.
Observable failure mode:

```text
target process has exited
external kill/taskkill helper remains pending indefinitely

normative contract
    wait() settles from the target exit

certified Rust implementation
    wait() remains pending because monitor_child awaits kill_process_tree first
```

A future revision of the shared contract toward "settlement may await termination machinery"
remains theoretically possible, but **only through an explicit shared-contract/governance
reopen** (`agent-workflow.md` §11.10) -- it is not available as a silent alternative merely
because it happens to match what one language's certified implementation currently does, and
this artifact does not propose or request that reopen.

## R004 state-transition matrix

All 15 states below were evaluated against BOTH the frozen Python candidate (`d44ea0e`, read
from `subprocess.py`, functions `_issue_kill`/`_confirm_kill`/`_watch_signal`/`wait`/
`terminate`, lines 130-422 per `git show d44ea0e:./src/minion_agent/execution/subprocess.py`)
and the certified Rust implementation (`subprocess.rs`, cited above). **Classification** (R004-A)
and **settlement timing** (R004-B) are recorded in SEPARATE columns throughout, precisely to
avoid the earlier revision's mistake of collapsing them into one PASS/FAIL verdict. Rust's
classification behavior is source-derived for every state except the exact tie-break timing in
states 7-8 (genuine race conditions whose interleaving is architecturally constrained by source
structure but not independently confirmed by a new test, since writing one would require
modifying `minion-agent-rust/**`).

| # | state | cause claim (R004-A) | classification | termination attempted | process-exit observation | helper-completion dependency (R004-B) | final Result |
|---|---|---|---|---|---|---|---|
| 1 | natural exit before signal | NONE | `Ok` | no | immediate | none | Rust: `Ok`. Python: `Ok`. Both consistent with R004-A; no settlement-timing question arises (nothing was ever claimed). |
| 2 | natural exit before explicit terminate | NONE | `Ok` | no | immediate | none | Rust: `Ok`. Python: `Ok`. Same as state 1. |
| 3 | signal observed while live; kill succeeds; process exits | SIGNAL | `Err(aborted)` | yes | after kill takes effect | **Rust: YES** (`wait()` awaits `kill_process_tree()` before `child.wait()`) -- **Python: NO** (`_confirm_kill` decoupled) | Classification: both `Err(aborted)`, R004-A-consistent. Settlement: Rust's `wait()` is coupled to the external kill command's own completion here -- the SAME R004-B defect as state 10, merely not exposed by a hung helper in this particular state (the command returns promptly in the ordinary case); Python already conforms to the retained contract. |
| 4 | explicit terminate while live; kill succeeds; process exits | EXPLICIT | `Ok` | yes | after kill takes effect | Rust: YES. Python: NO (`terminate()` itself awaits confirmation by design, since its OWN caller explicitly awaits it -- but `wait()` does not) | Classification: both `Ok`, R004-A-consistent. Settlement: same R004-B defect shape as state 3. |
| 5 | signal wins claim, then explicit terminate arrives | SIGNAL (unchanged) | `Err(aborted)` | yes (signal's attempt only) | after kill takes effect | as state 3 | Classification: both preserve `Err(aborted)`, first-wins confirmed in both (`subprocess.rs:284-293` CAS fails; Python's `if ... and self._kill_cause is None` check). |
| 6 | explicit terminate wins claim, then signal fires | EXPLICIT (unchanged) | `Ok` | yes (terminate's attempt only) | after kill takes effect | as state 4 | Classification: both preserve `Ok`, first-wins confirmed in both. |
| 7 | signal and natural exit race (does classification require the kill to be CONFIRMED effective?) | SIGNAL, deterministically, IF the poll loop observed `aborted()` at a liveness-check that preceded the natural-exit observation -- purely an OBSERVATION-ORDERING question, not a physical-causality one, per R004-A | `Err(aborted)` under that ordering | best-effort, outcome irrelevant to classification per R004-A | varies | Rust: kill_process_tree awaited regardless. Python: decoupled | **Classification: Rust matches R004-A by construction (no existing test exercises this exact interleaving -- source-derived, not test-confirmed). Python FAILS R004-A** -- `d44ea0e`'s `issue.issued` gate makes classification depend on the kill mechanism's own outcome, which R004-A forbids. |
| 8 | explicit terminate and natural exit race | non-deterministic tie-break in Rust's own `tokio::select!` (multiple-ready-branches ordering not documented as deterministic); benign since both `{EXPLICIT, NONE}` classify as `Ok` | `Ok` regardless of which of `{EXPLICIT, NONE}` wins | best-effort | varies | n/a to the benign outcome | Classification: both effectively `Ok` regardless of internal tie-break (benign). Not a settlement-timing case (no kill was necessarily issued if NONE won). |
| 9 | kill helper invocation FAILS before a kill request is issued (e.g. Windows `taskkill.exe` missing, `Popen` raises `OSError`) | Per R004-A: SIGNAL/EXPLICIT already claimed BEFORE the failed issuance attempt -- a failed issuance has NO bearing on the already-recorded cause | classification UNCHANGED from whatever was already claimed (i.e. still `Err(aborted)` if signal-claimed) | attempted, fails to issue | n/a (target process's own fate is independent of this failed attempt) | n/a (nothing to await -- the attempt itself failed) | **Classification: Rust matches R004-A by construction. Python FAILS R004-A -- this is the EXACT scenario `d44ea0e`'s round-6 fix targeted, and it produces the OPPOSITE of R004-A's answer.** `d44ea0e`'s own test (`test_wait_classifies_ok_when_taskkill_itself_fails_to_spawn`) asserts `Ok(exit_code=0)` here -- correct under the round-5 review's own (stricter-than-Rust) demand, wrong under R004-A. |
| 10 | kill request successfully issued but OS/process outcome delayed | already claimed, unaffected by delay | `Err(aborted)` once settled, per R004-A | in flight | delayed | **Rust: YES, unconditionally** (`wait()` cannot return until `kill_process_tree()`'s own await completes -- if the delay is in the EXTERNAL KILL-HELPER PROCESS itself hanging, not the target, Rust's `wait()` hangs too). **Python: NO** (`_confirm_kill` fully decoupled, fire-and-forget; confirmed via this round's own negative-control test) | **Classification consistent with R004-A in both. Settlement timing: Rust is NON-CONFORMING against the RETAINED contract** (`spec/execution.md` §6, "settles on process exit alone") -- this is the state where R004-B's implementation defect is directly observable: Rust's `wait()` remains pending on the external kill-helper even after the target process has already exited. This is a Rust-side defect requiring revalidation/remediation, not an open policy question. Python's own decoupled design already conforms to the retained contract here. |
| 11 | repeated `terminate()` | unchanged after first call | idempotent | first call only (subsequent calls no-op) | n/a | n/a | Both idempotent (Rust: `compare_exchange` fails on repeat; Python: `self._terminate_called` explicit guard). Not a settlement-timing case. |
| 12 | signal already aborted before spawn | n/a -- rejected at `spawn()`, no `Process` ever created | `spawn()` returns `Err(aborted)` | n/a | n/a | n/a | Both consistent (pre-existing, non-controversial, not part of the open findings). |
| 13 | `wait()` called before any cause event | n/a | ordinary blocking wait | n/a | whenever it occurs | n/a until a cause is claimed | Both block naturally, no special handling needed. |
| 14 | `wait()` called after process has already settled | unchanged (cached) | idempotent, no re-blocking | n/a | already observed | n/a (already resolved) | Both return the cached result immediately (Rust: `watch::Receiver::borrow()`; Python: `self._wait_result is not None` short-circuit). |
| 15 | repeated/concurrent `wait()` | unchanged | idempotent, safe for concurrent callers | n/a | shared | n/a | Both safe for concurrent callers (Rust: `tokio::sync::watch`; Python: `self._wait_lock`, existing test `test_wait_is_safe_when_called_concurrently`). |

### Summary

```text
CLASSIFICATION (R004-A) -- Rust satisfies the deterministic first-claim model for all 15
states (by source construction; states 7-8's exact tie-break timing not independently
test-confirmed). Python satisfies 13/15, failing states 7 (partially) and 9 -- both traceable
to round 6's own issue.issued gate, which needs to be REMOVED, not extended, to reach parity.

SETTLEMENT TIMING (R004-B) -- the RETAINED contract (spec/execution.md §6) already states
wait() settles on the process's own exit alone. Rust's wait() is coupled to
kill_process_tree()'s own completion in every state where a cause is claimed (states 3-7,
9-10) -- this is a narrowly-scoped Rust IMPLEMENTATION DEFECT against that retained contract,
most sharply exposed in state 10 (a hung external kill-helper process), not an open policy
question. Python's wait() is decoupled in all states and already conforms. See R004-B above.
```

**Classification-only correction for the frozen candidate**: removing `_KillIssue.issued`'s
gating of `_kill_cause` (reverting toward the round-4/5 design's eager-claim shape) would bring
Python's CLASSIFICATION behavior to parity with R004-A and with Rust. This is characterized,
not authorized -- implementation on either finding remains gated on independent checkpoint
approval.

## Rust revalidation result -- CORRECTED

```text
R004 CLASSIFICATION (R004-A)
    Rust source strongly indicates first-claim classification behavior consistent with the
    deterministic model above, but this has NOT been revalidated with NEW discriminating
    witnesses specifically targeting states 7, 9, and 10 (no such test exists in Rust's
    current suite) -- source-reading is strong evidence, not the same as confirmed evidence.

R004 SETTLEMENT TIMING (R004-B)
    Rust's wait() currently awaits kill_process_tree() before publishing its outcome. The
    RETAINED contract (spec/execution.md §6, "wait() settles on the process's own exit alone")
    already resolves what the correct behavior is -- Rust's own current behavior does NOT
    reopen that question merely by existing. This is a narrowly-scoped Rust implementation
    defect requiring revalidation/remediation by Rust's own owner.

R004 RUST REVALIDATION RESULT
    REVALIDATE_REQUIRED (corrected from an earlier "PASS" verdict, which improperly treated
    classification and settlement timing as one satisfied model)

reason:
    the shared cause-classification semantics are being materially clarified (R004-A); Rust
    source strongly indicates first-claim classification behavior, but new discriminating
    witnesses have not yet revalidated that behavior; additionally, Rust's wait() settlement
    currently awaits kill_process_tree(), a narrowly-scoped implementation defect against the
    already-retained process-exit-only settlement rule (R004-B, spec/execution.md §6), pending
    revalidation/remediation by Rust's own owner.
```

No Rust code change is performed or authorized in this pass. This REVALIDATE_REQUIRED finding
is scoped to the subprocess causal-classification/settlement surface specifically
(`subprocess.rs`'s `monitor_child`/`classify_exit`/`kill_process_tree`/`Process::wait`/
`Process::terminate`), applying the SAME cross-language revalidation rule (§14/§15 below, added
to `agent-workflow.md`) already applied to R002's Rust file:// surface above.

---

# PART C -- PROCESS CORRECTION

Three durable process rules, all added to `process/agent-workflow.md` in this same pass
(process documentation, not implementation code):

1. **Checkpoint invalidation rule** (retained, unchanged) -- if the same material finding fails
   TWO targeted convergence-closure reviews after an approved convergence checkpoint,
   implementation must stop; the checkpoint is presumed inadequate; before a third
   implementation attempt, return to characterization, identify the unmodeled semantic
   dimension, and require fresh approval before another implementation attempt. The count is
   per material/root finding, not per renamed finding ID. Does not apply to ordinary
   remediation outside convergence.
2. **Cross-language revalidation rule** (retained, unchanged) -- if implementation/review of one
   language reveals that a shared semantic requirement was materially mischaracterized, the
   OTHER language's affected certification becomes `REVALIDATE_REQUIRED` until tested against
   the revised shared contract and new discriminating witnesses. Scoped narrowly -- do not
   reopen unrelated layers or requirements. Applied in THIS pass to both R002's Rust `file://`
   conversion surface AND R004's Rust subprocess classification/settlement surface.
3. **Checkpoint proposal/approval terminology -- corrected in this pass.** An earlier revision
   of the checkpoint-invalidation rule permitted the implementation/shared-contract owner to
   write `AGREED FOR IMPLEMENTATION` directly. That is a self-approval, not a two-party barrier
   -- exactly the process defect this whole reset exists to correct. The checkpoint lifecycle is
   now:

   ```text
   characterization/implementation owner authors:
       CONVERGENCE CHECKPOINT
           PROPOSED FOR IMPLEMENTATION

   independent reviewer performs checkpoint review and returns:
       APPROVED  (or REJECTED, with the missing semantic dimension identified)

   only on APPROVED does the control record become:
       CONVERGENCE CONTRACT
           AGREED FOR IMPLEMENTATION
   ```

   No new workflow status is required -- this is checkpoint/evidence metadata within the
   existing `CONTRACT_CONVERGENCE` state, per §11.8.5's own existing shape. This artifact
   itself uses `PROPOSED FOR IMPLEMENTATION` terminology nowhere, because it is NOT proposing
   implementation yet -- it remains a pure characterization pass with `IMPLEMENTATION
   AUTHORIZED: NO`; the corrected terminology applies to the NEXT pass, once this
   characterization itself is approved and a bounded implementation plan is proposed against it.

See the diff to `process/agent-workflow.md` in this same commit for the exact inserted text.

---

# PART D -- CHECKPOINT SUMMARY -- REVISION 2

Revision 1 corrected an unverified Node oracle version (regenerated against the pinned floor
plus a drift check), a category miscount (total unaffected), and separated R004 cause-
classification from settlement-timing semantics after an earlier version improperly asserted
Rust satisfied a combined 15-state model it does not, by construction, fully satisfy.

**Revision 2** (this one) corrects Revision 1's OWN independent review findings
(`minion-agent-docs#120` @ `ca91006402ecf952f5e73691eca684d60ee3edaa`, `C12-RESET-R001`/
`C12-RESET-R002`): Revision 1 still incorrectly presented R004-B's settlement-timing
discrepancy as an unresolved, co-equal choice between two policies, when the shared contract
already resolves it (`spec/execution.md` §6's existing "process-exit-only" text is the
RETAINED rule; Rust's contrary behavior is a narrowly-scoped implementation defect, not a
competing policy) -- corrected throughout this document. Also added a third
`§11.8.11` cross-language-revalidation trigger (in `agent-workflow.md`) covering the case R002
actually is: new evidence that an already-certified implementation fails an existing,
CORRECTLY characterized requirement, distinct from the "requirement was mischaracterized"
trigger R004-A's own clarification fits.

```text
CE-L12-PY-01-01 CHECKPOINT RESET -- REVISION 2

R002 ROOT CAUSE
    Partial hand-written implementation of delegated Node/WHATWG semantics Pi itself contains
    zero custom logic for -- each remediation round closed the immediately prior witness while
    a new, independently-discoverable dimension of the same delegated surface kept surfacing.

R002 NORMATIVE ORACLE
    pinned Pi -> supported Node fileURLToPath/path semantics (Node's own EXECUTABLE behavior,
    not this corpus, not any finite list of examples -- see "Normative oracle vs. corpus role"
    above)

R002 PRIMARY ORACLE VERSION
    Node >= 22.19.0
    exact version used: v22.19.0 (Pi's exact declared floor), checksum-verified against
    Node's own published SHASUMS256.txt before use
    drift check: v22.23.2 (latest available 22.x), also checksum-verified -- output
    BYTE-FOR-BYTE IDENTICAL to v22.19.0 across all 68 generated cases, zero differences;
    the originally-used v22.15.1 is also byte-for-byte identical to both

R002 CORPUS
    65-case (68 generated, 3 platform-dependent excluded) regression/seed corpus
    (assurance/layers/data/12-python-r002-differential-corpus.md) -- NOT an exhaustive
    semantic definition; additional probes against the same oracle remain legitimate at any
    time without a new semantic decision

R002 PYTHON RESULT
    61/65 (93.8%) match against the frozen candidate d44ea0e -- unchanged by the oracle-version
    correction (byte-for-byte identical output confirmed across the whole 22.15.1-22.23.2
    range); 4 NEW mismatches this pass's own wider corpus discovered (IPv4 octet-range,
    multi-numeric-dot host, IPv6 canonicalization, zero-width-space forbidden-char rejection)

R002 RUST RESULT
    48/65 (73.8%) match -- likewise unchanged by the oracle-version correction; 17 mismatches
    across 5 categories (5 invalid-percent-escape leniency + 4 encoded-separator non-rejection
    + 1 IPv6-to-UNC construction + 5 Punycode-to-Unicode-output + 2 drive-relative-path
    divergence = 17, corrected from an earlier miscounted "6" in the first category); zero
    pre-existing Rust test coverage for any file:// edge case

R002 RUST STATUS
    REVALIDATE_REQUIRED (unchanged) -- scoped narrowly to EXEC-002/EXEC-003's file://
    conversion branch specifically (expand_path's Url::parse(...).to_file_path() call); does
    not reopen unrelated filesystem behavior

R002 CONTRACT
    Model A -- delegated Node/Pi compatibility (retained; NOT switched to Model B -- this
    investigation has shown implementation DIFFICULTY, not infeasibility; any intentional
    narrowing from Pi behavior still requires owner governance per §11.10)

R004 CLASSIFICATION MODEL (R004-A)
    deterministic first-claim state machine: cause in {NONE, SIGNAL, EXPLICIT}, first
    successful CAS claim wins, classification MUST NOT depend on proving which kill request
    physically caused OS termination, and the kill mechanism's own success/failure MUST NOT
    retroactively change an already-claimed cause. Replaces the ambiguous shared-contract
    phrase "whichever caused the actual kill first" with this deterministic language.

R004 PHYSICAL CAUSALITY REQUIREMENT
    NONE -- classification is an observable-state-machine question, not a physical-causality
    question, in both the proposed model and Rust's own actual certified source

R004 SETTLEMENT-TIMING STATUS (R004-B)
    RETAINED CONTRACT: wait() settles on the process's own exit alone (spec/execution.md §6,
    already-agreed, not reopened by this pass). Rust's wait() currently awaits
    kill_process_tree() (the external kill-helper process's own completion, no timeout) before
    publishing its outcome, in every state where a cause is claimed -- this is a NARROWLY-
    SCOPED RUST IMPLEMENTATION DEFECT against that retained contract, not an open or
    co-equal policy question. A revision toward "settlement may await termination machinery"
    remains theoretically possible only through an explicit shared-contract/governance reopen
    (§11.10) -- not proposed here, and not available merely because it matches Rust's current
    behavior.

R004 RUST STATUS
    REVALIDATE_REQUIRED (corrected from an earlier "PASS" verdict, which improperly combined
    the classification and settlement-timing concerns into one satisfied model). Rust source
    strongly indicates first-claim classification behavior (R004-A), but this has not been
    revalidated with NEW discriminating witnesses targeting states 7/9/10 specifically (no such
    Rust test currently exists); additionally, R004-B's settlement-timing behavior is a
    narrowly-scoped defect against the retained contract, requiring Rust-side
    revalidation/remediation.

PROCESS
    checkpoint invalidation rule retained (§11.8.10, agent-workflow.md)
    cross-language revalidation rule retained (§11.8.11, agent-workflow.md), applied in THIS
        pass to BOTH R002's Rust file:// surface and R004's Rust subprocess
        classification/settlement surface
    checkpoint author proposes (PROPOSED FOR IMPLEMENTATION); independent reviewer makes it
        agreed (APPROVED -> AGREED FOR IMPLEMENTATION) -- corrected in §11.8.5/§11.8.10,
        agent-workflow.md; no new workflow status required

IMPLEMENTATION AUTHORIZED
    NO
```

## Requested independent checkpoint review

Requesting review of EXACTLY:

```text
R002 differential oracle (now regenerated at Node >=22.19.0 + drift check) and the corrected
    normative-oracle-vs-corpus-role boundary
R004-A deterministic classification state machine
R004-B settlement-timing defect (Rust against the RETAINED contract -- not an open policy
    question)
Rust revalidation implications for BOTH R002's file:// surface and R004's
    classification/settlement surface
process checkpoint proposal/approval lifecycle correction (§11.8.5/§11.8.10)
```

Expected response shape:

```text
CHECKPOINT REVIEW

R002 CHARACTERIZATION
    APPROVED | REJECTED

R004 CHARACTERIZATION
    APPROVED | REJECTED

RUST REVALIDATION
    CLEAR | REQUIRED

PROCESS RULE
    APPROVED | NEEDS REVISION

AGREED FOR IMPLEMENTATION
    YES | NO
```

Only `AGREED FOR IMPLEMENTATION = YES` authorizes another change to `minion-agent#44`. This
artifact stops here.
