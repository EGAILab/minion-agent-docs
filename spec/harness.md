# Harness Semantics

Phase 6-7 parity includes execution seams, built-in tools, prompt assembly, skills, compaction, and
built-in harness message projections.

Skill behavior follows pinned Pi discovery, validation, diagnostics, deterministic traversal, and
available-skills XML/escaping. `disable-model-invocation` skills are excluded from model-visible
available-skills output.

Compaction defaults: reserve_tokens=16384, keep_recent_tokens=20000. Context estimate finds the most
recent usable assistant usage, ignores error/aborted/zero usage, prefers total_tokens, otherwise uses
component sum, then estimates trailing messages; with no usable usage it estimates the full history.
Summary calls use no prompt-cache retention and a fresh session identity.

Durable AgentHarness lanes/operations/suspend-resume/replay/navigation/pending writes remain explicit
`deferred parity` for Phase 9.
