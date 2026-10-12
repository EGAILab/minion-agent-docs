# Minion Agent — Coding Agent Workflow (pointer)

**Canonical location:** `minion-agent-docs/process/agent-workflow.md`

**Cut over to the Minion-Process kit on 2026-10-12 (PROC-KIT-P2, `minion-agent#212`).** The normative
workflow text for Minion-Agent is now the kit's `WORKFLOW.md` at the version pinned in
`process/profile.yaml` (`EGAILab/minion-process`, tag `v0.2.0`). It carries this file's rules with the
**same section numbers**, so every reference of the form `agent-workflow.md §11.8.7.1` resolves in
`WORKFLOW.md §11.8.7.1`. Read it with the profile, which supplies everything project-specific:

| What | Where |
|---|---|
| Normative rules (§1–§15) | kit `WORKFLOW.md` |
| Kinds, consequence classes, stage skips | kit `consequence-classes.md`; state fields in kit `coordination-state.md` §14 |
| Delegated routes `RT-1`–`RT-6` | kit `routing.md`; authority `minion-agent#75` Amendment 2 |
| State block, invariants, transitions, closure routes | kit `coordination-state.md` (this repository's `process/coordination-state.md` is a pointer) |
| Gate tiers, hazard families, authority dependencies, requirement IDs, feasibility template | kit files of the same names (pointers here) |
| Finding taxonomy | kit `finding-taxonomy.md`; Minion-Agent's `PI_*` names are aliases in the profile |
| Incident narratives behind the rules | kit `lessons/` |
| Minion-Agent-specific sentences that became profile values (Pi pin, authority chain, repositories, panes, the three canonical families) | kit `seed-history/minion-agent-specifics.md`; `process/profile.yaml` |
| Workflow mechanics CLI | kit `minion_process` run from a checkout of the pinned tag (`profile.yaml` header says how); this repository's `process/tools/` is retired |
| Role files | `Minions/Minion-Agent/CLAUDE.md`, `.agents/AGENTS.md`: ownership and environment only |

**Authority of this repository is unchanged** for everything that is not process: the frozen design,
`spec/**`, the parity manifest and canonical conformance in `minion-agent`, and `assurance/**`.

**History.** The full text of this file as Minion-Agent's in-force workflow, through the P1 adoption
header, is at `4dd10da5` (`git show 4dd10da5:process/agent-workflow.md`); the seed the kit was built from
is `dd9fd15`. Changes to the rules land in the kit first and reach this repository by a pin bump in
`process/profile.yaml`, reviewed like any process change (`WORKFLOW.md` §14.3).
