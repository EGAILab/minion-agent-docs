# `minion-process` — workflow mechanics CLI (design)

**Status:**
- Phase C1 is implemented in `process/tools/minion_process/`. It is PROPOSED, pending independent process review.
- Later commands are design only.

**Principle.** Agents decide semantics; the tool decides whether a workflow step is mechanically legal. The long-term prompt shrinks to *"Analyze semantics. Use `minion-process` for workflow mechanics."*

| The model decides | The tool decides |
|---|---|
| what Pi means; behavioral equivalence | whether a status transition is legal |
| finding taxonomy and root cause | whether the candidate SHAs are exact, remote-reachable and current PR heads |
| whether a divergence is proposed | whether a PR is open, not draft and mergeable at the approved head |
| whether evidence discriminates | whether a state write round-tripped (semantic + byte) |
| whether a checkpoint is adequate | whether required record fields exist (governance source, negative-control metadata) |

The tool never approves, never merges without an explicit exact SHA from an independent approval, and never writes `AGREED FOR IMPLEMENTATION` or any verdict. Those remain agent/Owner acts recorded with provenance (§11.8.5, §11.10).

## 1. Phase C1 — implemented

Run as `python -m minion_process <command>` from `process/tools/`. It needs `pyyaml` and an authenticated `gh`.

| Command | Enforces |
|---|---|
| `status <issue>` | Reads the current state: status, candidates, open findings, next owner/action, body size |
| `validate <issue> \| --file <body>` | `coordination-state.md` §4–§9 and §13 structural invariants. Errors: unknown status (e.g. the `BLOCKED` incident on #49); active state without owner/action; `BLOCKED_FOR_OWNER` owner ≠ Owner; `WAITING_FOR_TRIGGER` shape; non-40-hex SHA; non-integer PR; convergence episode missing; `FINAL_CONTRACT_REVIEW` with open convergence findings; container shapes; quarantine. Warnings: history-shaped keys, body over the lean budget, legacy v1 finding mappings |
| `transition-check FROM TO` | The reconciled legal-transition table (`coordination-state.md` §10, §10.1) |
| `apply <issue> <patch.py> [--dry-run]` | The full §11.1.1 commit rule. The patch changes only its declared `ALLOWED` keys; the transition is legal; the intended state is valid; one-document write; re-fetch; the remote state is valid, semantically equal to the intended state and byte-equal. Any failure is a FAILED STATE COMMIT, raised before any dependent action |
| `handoff-check <issue>` | §11.11: issue open; status permits a handoff; state valid; owner/action present; not quarantined; each candidate remote-reachable, its PR open, head == recorded SHA, and ready-for-review in review states. Prints `HANDOFF_BLOCKED` on any failure |
| `candidate-check <issue> [--ready]` | §5/§11.3 exact-SHA candidate checks alone |
| `merge <repo> <pr> <sha>` | §11.3/§11.6/§12: PR open, not draft, head == the approved SHA (else STOP), mergeable; squash with `--match-head-commit`; the merge commit is reachable from the default branch |
| `comment <repo> <n> <file> [--pr]` | Posts a history record as one document and verifies it byte-for-byte after re-fetch |

Each is covered offline by `process/tools/tests/` (fake `gh`, 100% statement coverage). The tests include:
- **historical-replay tests** for #49, #79 and #88 transitions;
- **transport-corruption tests**: a flattened body, a remote rewrite, a mangled comment.

## 2. Phase C2 — next (design)

| Command | Enforces |
|---|---|
| `finding add <issue> <ID> --taxonomy T --evidence <link>` | IDs unique; taxonomy ∈ §6; the evidence link must exist (the reviewer factual-evidence rule, §9.2.1). Appends to `open_findings` |
| `finding close <issue> <ID> --review <link> --candidate <sha> --negative-control <record>` | `candidate` == the current candidate; negative-control record fields present (§11.8.7.1, `coordination-state.md` §7) unless documentary with a reason; moves the ID to `provisionally_closed` |
| `review approve <issue> --reviewer <agent> --sha-pair <code>,<docs> --evidence <link>` | Reviewer ≠ the candidate's author (independence); the SHA pair == the current candidate; no open blocking findings; records approval bound to the pair (stale on any change) |
| `transition <issue> <TO> --reason ...` | The legal table plus per-target prerequisites: `FINAL_CONTRACT_REVIEW` route rules (§12.6); `RUST_IMPLEMENTATION` only after a recorded approval and merge containment; `CLOSED` only with registry `CERTIFIED_CLOSED` |
| `convergence counters <issue>` | Triggers A/B/C (§11.8) from finding history: survived-reviews count per finding, successor count per root-cause surface, rejected complete reviews per WP. Prints the mandatory trigger statement |
| `close <issue>` | Closure prerequisites (§4.3): no open findings, accepted milestone recorded, registry disposition for every requirement |
| `registry validate / render` | `process/certification-registry-design.md` invariants and derived status views |
| `schedule` | Lists every open WP with owner, status and dependency edges; prints which WPs each agent can progress now (§11.15) |

## 3. Non-goals

- The tool does not execute tests or decide gate tiers. Gate reporting stays in the handoff (`process/gate-tiers.md`); CI can later run the tiers.
- It does not parse review prose to infer verdicts. Verdicts are explicit command arguments with evidence links.
- It does not replace independent review, and it cannot self-approve: `review approve` refuses a reviewer equal to the candidate author.

## 4. Adoption

1. After independent approval of this change, agents use `apply`, `handoff-check`, `merge` and `comment` in place of ad-hoc scripts.
2. §12.6's executable-validator clause is then satisfied: the re-fetched state passes `validate`.
3. C2 commands land incrementally. Each one moves a prose rule from `agent-workflow.md` into enforcement, and the prose rule is shortened only after its enforcement exists (§12.7).
