# Layer 03 — `SES-F007` Narrow Re-Review Package (compaction linearization)

**Prepared:** 2026-08-24
**Prepared by:** Claude (Python/shared-contract owner, per the adopted workflow)
**Why this exists:** Rust's fresh delta review (`02-03-delta-rust-review.md`, reviewing
`minion-agent@f88c79d` / `minion-agent-docs@6f23c96`) returned:

```text
LAYER 02 DELTA CONTRACT
    APPROVED

LAYER 03 DELTA CONTRACT
    REJECTED — CONTRACT_ASSURANCE_DEFECT
    blocking finding: SES-F007 only
```

`SES-F004`, `SES-F005`, `SES-F006`, and `SES-F008` were each independently `APPROVED` in that same
review and are **not reopened by this package** — see `03-session-artifacts-delta-rust-handoff.md`
for their (unchanged, still-valid) review material. **This is not another six-finding audit from
zero.** It asks Rust to verify one narrow addition against one specific rejection.

**Reviewed commits (second `SES-F007` candidate):**

```text
minion-agent        <PUSH_PENDING>   spec/session.md (compaction-linearization paragraph),
                                      tests/session/test_concurrency.py (new provenance test),
                                      minion_agent/session/events.py (SES-F004 docstring
                                      history-accuracy correction, no behavior change)
minion-agent-docs   <PUSH_PENDING>   assurance/layers/02-llm.md, 03-session-artifacts.md (§0
                                      updated: review result recorded, SES-F007 lifecycle,
                                      SES-F004 history correction), this handoff,
                                      03-session-artifacts-delta-rust-handoff.md (status note +
                                      SES-F004 history correction)
```

**Pinned Pi revision:** `b7bb00b936dbe21b8e160b3e89efdec361846699` (unchanged — concurrency
behavior is not Pi-derived; `MINION-002` already marks Session persistence as Minion-owned
architecture).

**Do not modify Rust in response to this package without first recording a verdict.**

---

## 1. What changed, and only what changed

**SHARED CONTRACT** — `spec/session.md` only:

The compaction-mechanics sentence ("Compaction supersedes an effective range with a summary plus
retained-tail provenance and must avoid double inclusion...") is now immediately followed by a new
paragraph:

> In an execution model that admits concurrent Session mutation, a compaction's effective-surface
> and retained-provenance snapshot plus its compaction-event commit form one linearizable operation
> relative to append, reset, and other compaction operations. No append, reset, or compaction may
> commit between a compaction's snapshot and its marker in that operation's observable serialization
> order: events committed before that linearization point participate in the snapshot's derivation
> as normal, and events committed after it do not alter the recorded compaction provenance. This
> does not require every Session implementation to expose thread-safe simultaneous mutation -- an
> implementation whose execution model serializes Session mutation for this operation (for example,
> a single-threaded cooperative scheduler where compact's snapshot read and marker append never
> yield to another caller in between) satisfies the requirement by construction, matching the append
> paragraph's own scoping above. The requirement applies whenever concurrent mutation is admitted by
> that implementation.

The append paragraph itself (already `APPROVED`) is unchanged. No other file in
`conformance/session/**`, `session-scenario.schema.json`, or `pi-parity-manifest.yaml` was touched
— none of Rust's rejection concerned scenario/schema/manifest content, only the missing normative
rule.

**PYTHON — no production-behavior change, evidence only:**

- `tests/session/test_concurrency.py` — new test
  `test_compaction_provenance_matches_exactly_what_committed_before_its_own_marker`: interleaves many
  concurrent appenders and compactors via `asyncio.gather` and asserts every compaction's
  `superseded_through` matches exactly what the log held immediately before that compaction's own
  sequence. This is the specific invariant Rust's rejection named as unpinned by the two pre-existing
  concurrency tests (which prove sequencing/no-tearing, not provenance accuracy against a forced
  interleaving).
- `minion_agent/session/events.py::EventKind.COMPACTION`'s docstring corrected for historical
  accuracy per Rust's own request (§2 below) — no value or behavior change, `"session/compaction"`
  is unchanged.

**No Python production code changed.** `operations.py::compact()`, `derive.py::effective_surface()`,
and `log.py::SessionLog.append()` are byte-identical to the previously-reviewed candidate.

---

## 2. `SES-F004` history correction (requested by Rust, applied here)

Rust's review noted the assurance/code commentary should not describe the pre-delta bare
`"compaction"` spelling as a value "no normative source pinned." At Layer 03's original
certification (`minion-agent-docs@ed1b18e`), `spec/session.md`'s owned-kinds list explicitly read
`(session/forked, session/reset, compaction)` — the bare spelling **was** the certified normative
contract at that time, superseded by this delta audit's new cross-language evidence, not discovered
to have been unpinned all along. `events.py::EventKind.COMPACTION`'s docstring is corrected to state
this. `SES-F004` itself is not reopened — this is a wording-accuracy fix only, applied to preserve
the fact that this was a genuine contract change caused by new evidence, not to make the final state
look inevitable in hindsight.

---

## 3. Reproduction: is Python's existing behavior a defect under the clarified rule?

Traced the real mutation path directly rather than trusting either implementation's self-report:

```text
operations.py::compact()
    surface = effective_surface(log)      # snapshot read, pure function, no await
    return log.append(EventKind.COMPACTION, {...})   # commit, no await

log.py::SessionLog.append()
    validate_event_name(kind)              # no await
    _check_json_safe(data)                 # no await
    self._events.append(event)             # no await

derive.py::effective_surface()
    pure function over log.events, no await anywhere
```

Zero `await` points exist between the snapshot read and the marker commit, in either `compact()` or
anything it calls. Under Python's supported execution model (single-threaded cooperative asyncio), a
coroutine is preempted only at an `await` point — so no other coroutine can execute "between" the
snapshot and the commit once `compact()` has started. **Conclusion: not a Python implementation
defect. The clarified rule is satisfied by construction**, the same reasoning already established
and Rust-approved for the append paragraph.

This conclusion was not simply copied from Rust's own suggestion that "Python's synchronous
cooperative path can satisfy the clarified rule" — it was independently re-derived by reading the
actual call graph.

---

## 4. Rust's required independent verdict, per question — do not trust Python's classification

1. **Language-neutral?** Does the new paragraph state a rule independent of either implementation's
   internal mechanism (mutex vs. no-lock cooperative scheduling), specifying only the observable
   result?
2. **Does it avoid becoming a universal thread-safety mandate?** Re-read the qualification sentence
   directly: does an implementation whose execution model serializes Session mutation satisfy the
   rule "by construction," with no forced lock/mutex requirement for implementations that don't need
   one?
3. **Is the observable intent unambiguous?** Does "no append, reset, or compaction may commit
   between a compaction's snapshot and its marker in that operation's observable serialization
   order" pin the exact failure Rust's own probe demonstrated (a stale-snapshot compaction marker),
   with no room for a second conforming-but-different reading?
4. **Can both Python's supported execution model and Rust's current mutex implementation satisfy it
   naturally?** For Rust specifically: does the existing single-`parking_lot::Mutex`-scope
   `compact()` (spanning read+write) already satisfy this rule without any code change?
5. **Scope check:** does the new paragraph stay confined to append/reset/compaction, or does it leak
   into general Session transactionality, Agent concurrency, or fork semantics beyond the
   already-approved `SES-F006` rule? (Expected: confined.)

---

## 5. Explicitly out of scope for this package

- `SES-F004`/`SES-F005`/`SES-F006`/`SES-F008` — already `APPROVED`, not reopened, no new verdict
  requested.
- `LLM-F011` — already `APPROVED`, not reopened.
- Any Rust implementation change (`ToolResultMessage.tool_name`, `session/compaction` constant
  (already correct), `EventKind::new()`'s validator, or `compact()`'s existing mutex design) — all
  remain `WAIT` until this package returns `APPROVED` and consolidated remediation begins.
- Layer 04 (XFORM).
- General Session concurrency design beyond the one linearization rule above.

---

## 6. Expected outcome

```text
LAYER 03 DELTA CONTRACT
    APPROVED
```

or a precise rejection naming exactly what remains ambiguous or non-language-neutral in the new
paragraph. If approved, both layers' shared contracts are settled and consolidated Rust
implementation remediation (§16 of the originating remediation instruction — `tool_name`,
`session/compaction` constant confirmation, event-name validator alignment, fork-boundary
confirmation, role-typed-content confirmation, and confirmation that the existing mutex-based
`compact()` already satisfies the newly-stated linearization rule) may begin.
