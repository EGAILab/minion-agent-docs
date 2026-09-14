# Layer 11 Pass 2 Slice B — independent Rust final contract review

## Exact candidate

- code PR `EGAILab/minion-agent#31` @
  `9e056afda7b27ce5b25092edbf47751bcaffec68`
- docs PR `EGAILab/minion-agent-docs#77` @
  `1cacc9043b14f2a66be5e8896e50cba5ec63b519`
- pinned Pi `b7bb00b936dbe21b8e160b3e89efdec361846699`
- accepted bases: code `039050710579d6511a63c25077093bfe83006b11`, docs
  `479e388599f4f36a19c15532fd2ce33531b02704`
- previous reviews: docs PR `#78` @ `25334e68981ed977dfef2731a4cbeed2cd142f06`
  and docs PR `#79` @ `2bc1dd2b04c075faf38a1980de148284dee541c7`

Both candidate heads were open, Ready for Review, and remote-reachable. Open coordination issue
`EGAILab/minion-agent#29` named the same exact heads, `NEXT_OWNER: Codex`, and a complete §11.8.8
review. The owner decision for `L11-SB-R006` was independently verified at
`https://github.com/EGAILab/minion-agent/issues/29#issuecomment-5664609556`; it explicitly approves
the narrow Python-binding divergence and no other divergence.

## Independent Pi audit

Re-read before inspecting the convergence implementation:

- `packages/ai/src/auth/types.ts:118-241`;
- `packages/ai/src/models.ts:487-508,565-615`;
- `packages/ai/src/auth/resolve.ts:127-193`;
- real auth-provider `interaction.notify(...)` call sites, including
  `packages/ai/src/auth/oauth/openai-codex.ts:429,456`.

No Pi behavior is uncertain.

## Closure ledger

- `L11-SB-R001`: **CLOSED** — absent/false/true `is_subscription` remains represented.
- `L11-SB-R002`: **CLOSED** — the normalized interaction remains statically usable as the base
  interaction.
- `L11-SB-R003`: **PROVISIONALLY CLOSED on semantics**, but its remediation introduces the new
  current-document accuracy defect below. The contract now says every async callable may fail and
  direct synchronous `notify` throws propagate.
- `L11-SB-R004`: **CLOSED** — construction evidence is no longer presented as interaction-result
  evidence.
- `L11-SB-R005`: **CLOSED** — the public dataclass values remain assignable.
- `L11-SB-R006`: **CLOSED BY GOVERNANCE** — `PROV-015` accurately isolates the owner-approved
  Python static widened-reference assignment divergence. `PROV-014` remains adopted and does not
  silently absorb the divergence. The existing positive typing witness proves the invariant the
  owner chose to preserve. Rust is not instructed to copy Python property mechanics.

## Finding

### L11-SB-R007 — `CONTRACT_ASSURANCE_DEFECT` — R003's new source account overstates Pi and cites a nonexistent path

This is documentary/traceability-only; the Python callable types already permit exceptions and
direct `notify` already propagates synchronously.

The new normative failure paragraph says every async callable's real call site awaits it “inside
its own `try`/`catch` and wraps a rejection.” That is false for both provider-login variants:

```text
models.ts:574  method.login({ ...interaction, signal })
models.ts:575  await raceWithAbortSignal(loginOperation, signal)
```

There is no login-error `try`/`catch` or auth-error wrapper around those statements. The later
`try` block at lines 591-613 covers credential-store mutation, not provider login. Thus Pi permits
login rejection and propagates it through the race, while check/resolve/refresh/toAuth have the
specific wrapping sites cited by the candidate. The high-level rule “all may reject; the caller
owns handling” is sound, but its claimed source trace is not.

The new convergence assurance additionally cites:

```text
packages/coding-agent/src/auth/openai-codex.ts:429,456
```

That path does not exist at pinned Pi. The inspected notification call sites are at:

```text
packages/ai/src/auth/oauth/openai-codex.ts:429,456
```

These inaccuracies matter because the current normative paragraph can lead a later independent
Rust/`PROV-013` implementer to wrap login failure where Pi does not, and the assurance record claims
an independently verified source path that cannot be opened.

**Minimal correction:**

1. retain the correct rule that every async auth callable may reject;
2. state that call-site handling differs: check/resolve/refresh/toAuth use the cited wrapping paths,
   while provider login is not wrapped there and its rejection propagates through
   `raceWithAbortSignal`;
3. keep exact orchestration implementation deferred to `PROV-013`; and
4. correct the assurance source path to `packages/ai/src/auth/oauth/openai-codex.ts`.

No Python behavior or type design needs to change for this finding.

## Contract-quality and Rust feasibility

- `PROV-014` and `PROV-015` now have coherent, separate dispositions.
- The owner-approved divergence is narrow, traceable, and does not prescribe Rust mechanics.
- Typed Rust enums, callback traits/futures returning typed `Result`, and specialized interaction
  views are feasible on the certified auth foundation without a lower-layer reopen.
- `PROV-013` orchestration remains deferred; Slice C and Layer 12 were not started.
- No canonical runner simulates this vocabulary-only surface.

Apart from R007, two independent Rust implementations can derive the same Slice B vocabulary and
failure capability. R007 must be corrected before exact-SHA approval because the current contract
itself asserts the wrong Pi failure trace.

## Fresh gates

Executed against the exact code candidate:

- targeted interaction tests: `16 passed`;
- mypy including typing fixtures: success, `72 source files`;
- manifest validation: `8 passed`;
- targeted ruff: clean;
- full pytest: `1337 passed, 19 xfailed`;
- coverage: `100.00%`, `3308` statements, `0` missed.

The green gates do not detect the false source statement because it is normative prose and
assurance traceability.

## Convergence/final-review status

This is the third rejected Slice B contract review, so the layer-level §11.8 trigger is met.
However, the prior convergence behavior matrix and R003/R006 mechanisms are no longer disputed:
R007 is a mechanically bounded documentary correction with direct line-level Pi evidence. A new
broad characterization exercise would add no information. The remediation owner may perform the
narrow correction above, explicitly recording why this point fix is used under §11.8's trigger
exception, then request another complete §11.8.8 review of the changed exact SHA pair.

## Verdict

```text
shared Layer-11 Pass-2 Slice-B contract
    REJECTED

Python Slice B
    REOPENED (documentation/traceability only)

Rust Slice B
    BLOCKED / NOT_IMPLEMENTED

Layer 11 Pass 2
    NOT CLOSED

Slice C / PROV-012
    NOT STARTED

Layer 12
    NOT STARTED
```

The verdict applies only to code
`9e056afda7b27ce5b25092edbf47751bcaffec68` and docs
`1cacc9043b14f2a66be5e8896e50cba5ec63b519`.

No candidate, Python, shared semantic, canonical, or Rust file was modified by this review. Only
this review artifact was added.

## Next action

Return `L11-SB-R007` to the shared/docs owner for the four narrow documentary corrections above.
Any changed SHA requires another complete exact-SHA review. Do not start Slice C, Rust Slice B, or
Layer 12.
