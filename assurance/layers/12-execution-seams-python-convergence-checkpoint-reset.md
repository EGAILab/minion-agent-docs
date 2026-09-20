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

**Version-gap caveat** (disclosed, not resolved by this artifact): Pi's own `engines.node` pins
`>=22.19.0`; every live probe in this artifact ran against locally available Node `v22.15.1`.
The core WHATWG URL host-parsing algorithm has been stable across this range and no known
breaking change to `fileURLToPath`/IDNA/IPv6-canonicalization exists between these two
versions, but this has not been independently verified against the exact pinned floor version.

## Differential oracle corpus

Full corpus (65 comparable cases, 3 platform-dependent cases excluded) with all three
implementations' actual output:

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
   `%2` truncated, `%e2%98` truncated UTF-8, `%ff%fe` invalid UTF-8) -- 6 mismatches. Node
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

## Proposed shared state machine (Option A -- deterministic event-order/claim model)

Selected over Option B (literal physical causality) because Option B would require reopening
Rust's own already-certified implementation and building a stronger acknowledgement/termination
model in BOTH languages -- a scope well beyond a Python-only remediation, and not something this
artifact escalates to the owner absent a concrete reason to prefer it. Option A is, by
construction, what Rust ALREADY does.

```text
state: cause ∈ {NONE, SIGNAL, EXPLICIT}, initially NONE.
       An atomic compare-and-swap-style CLAIM: the FIRST of the two trigger conditions below to
       occur wins; the loser is a permanent no-op for classification purposes (idempotent,
       first-wins).

Rule 1 (claim):
  (a) SIGNAL claim: the poll loop observes the spawn-signal aborted() at a moment it still
      believes the process to be running (its own most recent liveness check said so) --
      claims cause = SIGNAL, if cause is still NONE.
  (b) EXPLICIT claim: terminate() is called while cause is still NONE -- claims
      cause = EXPLICIT.
  Both (a) and (b) are ATOMIC, NON-BLOCKING claims -- neither involves awaiting the kill
  mechanism itself.

Rule 2 (best-effort termination, decoupled from classification):
  Once a cause is claimed (by EITHER path), a best-effort kill-the-tree attempt is issued.
  This attempt's own success, failure to find a live target, or failure to even ISSUE (e.g. the
  platform kill helper fails to spawn) has NO EFFECT on the classification already recorded by
  Rule 1. The attempt MAY be confirmed/cleaned-up asynchronously, but that confirmation is
  never awaited by wait().

Rule 3 (settlement):
  wait() settles the moment the underlying OS process is OBSERVED to have exited -- by whatever
  means -- and reads whichever `cause` value has been claimed AT THAT MOMENT:
      cause == SIGNAL              -> Err(aborted)
      cause == EXPLICIT or NONE    -> Ok(ExitStatus{exit_code})
  wait() NEVER awaits Rule 2's own confirmation/cleanup step.

Rule 4 (idempotence):
  wait() is safe to call repeatedly/concurrently, always returning the same settled result once
  settled. terminate() is safe to call repeatedly; every call after the first that loses the
  Rule-1 claim is a no-op for classification purposes.
```

**Consequence for the frozen Python candidate**: `d44ea0e`'s `L12-PY-R004` design (round 6)
gates `_kill_cause` recording on `_KillIssue.issued` (whether the OS-level kill command was
successfully ISSUED, not merely decided upon) -- this is a Rule-2-level check being used to gate
a Rule-1-level claim, which Option A / Rust's own certified behavior does NOT do. **The round-5
targeted closure review's own counterexample (a failed Windows `taskkill` spawn must not
classify `Err(aborted)`) demanded behavior STRICTER than what is actually certified in Rust.**
Aligning Python with Option A means REMOVING the `issued` gate, reverting toward the round-4/5
design's own eager-claim shape -- the opposite direction from where the last two rounds moved.

## R004 state-transition matrix

All 15 states below were evaluated against BOTH the frozen Python candidate (`d44ea0e`, read
from `subprocess.py`, functions `_issue_kill`/`_confirm_kill`/`_watch_signal`/`wait`/
`terminate`, lines 130-422 per `git show d44ea0e:./src/minion_agent/execution/subprocess.py`)
and the certified Rust implementation (`subprocess.rs`, cited above), against the Option A
contract. Rust's classification is source-derived for every state EXCEPT the exact tie-break
timing in states 7-8 (genuine race conditions whose PRECISE outcome ordering is architecturally
guaranteed by source structure but not independently confirmed by a new test, since writing one
would require modifying `minion-agent-rust/**`).

| # | state | cause | termination attempted | wait() blocks on | Option A result | Rust (`2b309ee8`) | Python (`d44ea0e`) |
|---|---|---|---|---|---|---|---|
| 1 | natural exit before signal | NONE | no | process exit only | `Ok(exit_code)` | PASS (`try_wait` breaks before any cause-check, `subprocess.rs:380-381`) | PASS (`_kill_cause` never touched, watcher loop exits on `returncode != None`) |
| 2 | natural exit before explicit terminate | NONE | no | process exit only | `Ok(exit_code)` | PASS (terminate() never called, trivial) | PASS (trivial, same reasoning) |
| 3 | signal observed while live; kill succeeds; process exits | SIGNAL | yes | process exit only | `Err(aborted)` | PASS (`subprocess.rs:385-396`) | PASS (normal case: `_issue_kill` succeeds, `issued=True`, `_kill_cause="signal"` set) |
| 4 | explicit terminate while live; kill succeeds; process exits | EXPLICIT | yes | process exit only | `Ok(exit_code)` | PASS | PASS (normal case) |
| 5 | signal wins claim, then explicit terminate arrives | SIGNAL (unchanged) | yes (signal's own attempt only) | process exit only | `Err(aborted)` | PASS (`terminate()`'s own CAS fails against already-SIGNAL `cause`, `subprocess.rs:284-293`, no-op) | PASS (`if issue.issued and self._kill_cause is None` -- already `"signal"`, not overwritten) |
| 6 | explicit terminate wins claim, then signal fires | EXPLICIT (unchanged) | yes (terminate's own attempt only) | process exit only | `Ok(exit_code)` | PASS (monitor loop's own signal-branch CAS also fails against already-EXPLICIT `cause`) | PASS (same first-wins guard) |
| 7 | signal and natural exit race (kill attempt does not need to be CONFIRMED effective for classification) | SIGNAL, IF the poll loop observed `aborted()` at a liveness-check moment that preceded the natural-exit observation; NONE otherwise -- deterministic given the SAME poll loop's own discrete check ordering, not a physical-causality question | best-effort, outcome irrelevant to classification | process exit only | `Err(aborted)` in the "loop saw it first" ordering; `Ok` otherwise | PASS by construction (CAS happens before `kill_process_tree` is even called; the function's own success/failure is never read for classification) -- **no existing test exercises this exact interleaving; source-derived, not test-confirmed** | **FAIL relative to Option A** -- `d44ea0e`'s `issue.issued` gate (added in round 6) makes classification depend on Rule 2 (whether `_issue_kill` succeeds), not purely on Rule 1's observation ordering; a genuinely no-effect-but-successfully-ISSUED kill still passes (matches), but see state 9 for where this diverges concretely |
| 8 | explicit terminate and natural exit race | non-deterministic tie-break in Rust specifically (see note below); benign either way | best-effort | process exit only | `Ok(exit_code)` regardless of which of {EXPLICIT, NONE} wins, since both map to `Ok` | Rust's `terminate()` CAS is fully decoupled from the monitor's own `tokio::select!` polling cadence -- if the real process exits at nearly the same instant `terminate()` is called, `tokio::select!`'s own multi-ready-branch tie-break is used (not deterministically documented as ordered); OBSERVABLE result is unaffected either way (PASS, benign) | PASS (Python's `await`-point-yielding `terminate()` has an analogous internal race between "did `_kill_cause` get set to `explicit` before `wait()` reads it", but since both `explicit` and `None` classify identically via `Ok`, the observable result is unaffected -- benign) |
| 9 | kill helper invocation fails before a kill request is issued (e.g. Windows `taskkill.exe` missing, `Popen` raises `OSError`) | Per Option A: SIGNAL/EXPLICIT already claimed by Rule 1 BEFORE Rule 2 runs -- a Rule-2 failure has NO bearing on the ALREADY-recorded cause | attempted, fails to issue | process exit only | classification UNCHANGED from whatever Rule 1 already claimed (i.e. still `Err(aborted)` if signal-claimed) | PASS by construction -- `kill_process_tree`'s own internal fallback-to-`child.start_kill()` logic is entirely about attempting an alternate kill mechanism, NEVER about reporting back to `cause` | **FAIL relative to Option A -- this is the EXACT scenario `d44ea0e`'s round-6 fix targeted, and it produces the OPPOSITE of Option A's answer.** `d44ea0e`'s own test (`test_wait_classifies_ok_when_taskkill_itself_fails_to_spawn`) asserts `Ok(exit_code=0)` for this exact scenario -- CORRECT under the round-5 review's own (stricter-than-Rust) demand, but WRONG under Option A / Rust's actual certified behavior, which would classify `Err(aborted)` here since the cause was already claimed before the failed issuance attempt |
| 10 | kill request successfully issued but OS/process outcome delayed | already claimed (Rule 1), unaffected by delay | in flight | process exit only, NEVER the kill's own confirmation | `Err(aborted)` once the process eventually exits, whenever that is | Rust's `wait()` blocks on `kill_process_tree`'s own await too (see the disclosed asymmetry above) -- if the delay is in the TARGET PROCESS itself (still exiting eventually), PASS; if the delay is in the KILL COMMAND helper process itself hanging, Rust's `wait()` would ALSO hang (a genuine, narrower gap, not part of Option A's own text) | PASS -- `d44ea0e`'s `_confirm_kill` dispatch is fully decoupled (fire-and-forget background task), `wait()` never awaits it regardless of how long confirmation takes, confirmed via this round's own negative-control test |
| 11 | repeated `terminate()` | unchanged after first call | first call only (subsequent calls no-op) | n/a | idempotent | PASS (`compare_exchange` fails on subsequent calls, `notify_one()` not re-sent) | PASS (`self._terminate_called` explicit guard, even more directly idempotent) |
| 12 | signal already aborted before spawn | n/a -- rejected at `spawn()`, no `Process` ever created | n/a | n/a | `spawn()` itself returns `Err(aborted)` | PASS (`subprocess.rs`, spawn's own pre-check) | PASS (`spawn()`'s own pre-check) -- both already-established, non-controversial, not part of the open findings |
| 13 | `wait()` called before any cause event | n/a | n/a | ordinary blocking wait | blocks until settled, no special handling needed | PASS (trivial -- `watch::Receiver::changed()` blocks naturally) | PASS (trivial -- `self._proc.wait()` blocks naturally) |
| 14 | `wait()` called after process has already settled | unchanged (cached) | n/a | none -- returns cached result immediately | idempotent, no re-blocking | PASS (`watch::Receiver::borrow()` returns the last-sent value without re-blocking) | PASS (`self._wait_result is not None` short-circuit, double-checked under the lock) |
| 15 | repeated/concurrent `wait()` | unchanged | n/a | none for callers after the first settles | idempotent, safe for concurrent callers | PASS (`tokio::sync::watch` is inherently safe for multiple concurrent receivers) | PASS (`self._wait_lock` serializes; existing test `test_wait_is_safe_when_called_concurrently` already covers this) |

### Summary

```text
States where Rust (2b309ee8) satisfies Option A:      15 / 15 (by source construction;
                                                         states 7-8's exact tie-break timing
                                                         not independently test-confirmed)
States where Python (d44ea0e) satisfies Option A:      13 / 15
Python's 2 Option-A violations:                        states 7 (partially -- see note) and 9
                                                        (the round-6 `issue.issued` gate)
```

**The frozen candidate's OWN R004 fix (round 6) is the thing that needs to be reverted**, not
extended, to reach Option A parity with Rust. The correct next Python implementation pass
should remove `_KillIssue.issued`'s gating of `_kill_cause`, returning to an eager,
observation-ordering-based claim -- closer to the round-4/5 design than to round 6 -- while
KEEPING round 5's genuinely-good fix (the `_issue_kill`/`_confirm_kill` SPLIT itself, which
correctly decoupled confirmation from `wait()`'s own settlement timing, state 10 above).

## Rust revalidation result

```text
R004 state machine (Option A)
    PASS (source-verified for all 15 states; states 7 and 8's precise tie-break ordering is
          architecturally guaranteed by the source structure -- CAS-before-kill-attempt,
          decoupled classification -- but not independently confirmed by a NEW discriminating
          test, since adding one would require modifying minion-agent-rust/**, out of scope
          for this Python-owned characterization pass)

Existing Rust test coverage for the discriminating states (7, 9, 10)
    NONE -- a genuine, pre-existing gap in Rust's own certification evidence, disclosed here,
    not remediated here (Rust-owner scope)
```

No Rust code change is implied by adopting Option A -- Rust already implements it. The
CLARIFICATION aligns the shared contract's prose with Rust's own already-certified behavior; it
is Python that needs to move.

---

# PART C -- PROCESS CORRECTION

Both of the following are added to `process/agent-workflow.md` as durable process rules in this
same pass (process documentation, not implementation code):

1. **Checkpoint invalidation rule** -- if the same material finding fails TWO targeted
   convergence-closure reviews after an `AGREED FOR IMPLEMENTATION` checkpoint, implementation
   must stop; the checkpoint is presumed inadequate; before a third implementation attempt,
   return to characterization, identify the unmodeled semantic dimension, and obtain a NEW,
   independently-reviewed `AGREED FOR IMPLEMENTATION` approval. The count is per material/root
   finding, not per renamed finding ID.
2. **Cross-language revalidation rule** -- if implementation/review of one language discovers a
   new shared semantic requirement, or reveals an existing shared requirement was materially
   mischaracterized, an already-certified OTHER language does not remain automatically
   certified for the AFFECTED semantic surface; it becomes `REVALIDATE_REQUIRED` until checked
   against the revised shared contract and new discriminating witnesses. Scoped narrowly to the
   affected surface, not a blanket reopening.

See the diff to `process/agent-workflow.md` in this same commit for the exact inserted text.

---

# PART D -- CHECKPOINT SUMMARY

```text
CE-L12-PY-01-01 CHECKPOINT RESET

R002 ROOT CAUSE
    Hand-written, partial, witness-driven emulation of a delegated WHATWG/Node algorithm
    Pi itself contains zero custom logic for -- each remediation round closed the immediately
    prior witness while a new, independently-discoverable dimension of the same delegated
    surface (IDNA2003-vs-UTS46, bidi/combining-mark validation, IPv4/IPv6 host validation and
    canonicalization, general forbidden-Unicode-code-point rejection) kept surfacing.

R002 REFERENCE ORACLE
    Pinned Pi (b7bb00b936dbe21b8e160b3e89efdec361846699) via Node 22's own url.fileURLToPath
    (nodejs.ts:51-65/20) -- Node IS the oracle, not a proxy for it.

R002 CORPUS
    assurance/layers/data/12-python-r002-differential-corpus.md (65 cases)

R002 PYTHON RESULT
    61/65 (93.8%) match against the frozen candidate d44ea0e; 4 NEW mismatches discovered by
    this pass's own wider corpus (IPv4 octet-range, multi-numeric-dot host, IPv6
    canonicalization, zero-width-space forbidden-char rejection)

R002 RUST REVALIDATION RESULT
    48/65 (73.8%) match; REVALIDATE_REQUIRED for EXEC-002/EXEC-003's file:// URL conversion
    surface specifically (17 mismatches across 5 categories, zero pre-existing Rust test
    coverage for any file:// edge case)

R002 PROPOSED CONTRACT
    Model A (delegated WHATWG compatibility) against the corpus above as acceptance oracle;
    Model B (narrower divergence) explicitly NOT selected absent owner governance

R004 ROOT CAUSE
    Successive Python review rounds progressively strengthened "actual kill causation" from an
    event-ordering/claim model into a confirmed-physical-effect model that the already-
    certified Rust implementation does not itself provide -- each round's fix satisfied its own
    review's counterexample while silently diverging further from the shared, certified
    baseline.

R004 CURRENT RUST BEHAVIOR
    Atomic CAS-based first-wins claim (CAUSE_NONE/SIGNAL/EXPLICIT), claimed the instant the
    poll loop observes signal.aborted() at a still-believed-running liveness check, BEFORE the
    kill is even attempted; the kill attempt's own success/failure has zero effect on the
    already-claimed cause (subprocess.rs:197-199, 266-294, 372-422)

R004 PROPOSED SHARED STATE MACHINE
    Option A (deterministic event-order/claim model) -- full 15-state matrix above; Rust
    already satisfies all 15 states by source construction; the frozen Python candidate
    satisfies 13/15, failing states 7 (partially) and 9, both traceable to round 6's own
    issue.issued gate, which needs to be REMOVED, not extended, to reach parity

R004 RUST REVALIDATION RESULT
    PASS (source-verified against all 15 states; states 7/8's exact tie-break timing not
    independently test-confirmed, since confirming it would require new Rust-side tests,
    out of this Python-owned pass's scope)

PROCESS DEFECT
    The convergence checkpoint after CE-L12-PY-01-01's original trigger (§11.8) was not
    independently re-challenged against the ALREADY-certified Rust behavior at each subsequent
    review round -- each round's own refined counterexample was accepted and implemented
    without cross-checking whether the resulting stricter interpretation remained consistent
    with what was actually shared/certified, letting Python's own interpretation drift
    progressively further from Rust's real behavior across five review rounds.

PROPOSED PROCESS FIX
    Two failed targeted closures against the SAME material finding, after an AGREED FOR
    IMPLEMENTATION checkpoint, invalidate that checkpoint and require a fresh, independently-
    reviewed checkpoint before a third implementation attempt (added to agent-workflow.md,
    this same pass). Cross-language revalidation rule added alongside it.

IMPLEMENTATION AUTHORIZED
    NO
```

## Requested independent checkpoint review

Per the reset instruction's own §18, requesting review of EXACTLY:

```text
R002 differential oracle + adopted behavior boundary
R004 deterministic state machine
Rust revalidation implications
process checkpoint-invalidation rule
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
