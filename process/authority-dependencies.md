# Pinned external authority dependencies (pointer)

**Moved to the Minion-Process kit (cut-over 2026-10-12, PROC-KIT-P2, `minion-agent#212`).** The
normative rule and pattern are `authority-dependencies.md` in `EGAILab/minion-process` at the version
pinned in `process/profile.yaml` (tag `v0.2.0`), text preserved. The canonical acquisition helper is the
kit's `authority/acquire_npm_pinned.sh`; the byte-identical copies in this repository's evidence
harnesses (`assurance/layers/data/*/harness/`) are checked by the kit's test suite with
`MINION_PROCESS_EVIDENCE_DATA` pointing at `assurance/layers/data`.

The text as it stood before the cut-over is at `4dd10da5` (`git show 4dd10da5:process/authority-dependencies.md`).
