# process/tools — `minion-process`

Deterministic workflow mechanics for Minion Agent coordination. The design and scope are in `process/minion-process-cli-design.md`.

```sh
cd process/tools
python -m minion_process status 88
python -m minion_process validate 88
python -m minion_process transition-check CONTRACT_CONVERGENCE FINAL_CONTRACT_REVIEW
python -m minion_process handoff-check 88
python -m minion_process apply 88 patch.py --dry-run
python -m minion_process merge code 90 <approved-sha>
python -m minion_process comment docs 200 review.md --pr
```

**Requirements:** Python ≥ 3.12, `pyyaml`, and an authenticated `gh` CLI.

**Patch files** for `apply` define:

```python
ALLOWED = {"status", "next_owner", "next_action"}  # top-level workflow keys this patch may change


def apply(w):  # mutate the workflow dict in place; optionally return replacement prose
    w["status"] = "IMPLEMENTATION_REVIEW"
    w["next_owner"] = "Codex"
    w["next_action"] = "Targeted closure of R001 at code <sha> / docs <sha>."
```

**Tests** run offline against a fake `gh`:

```sh
python -m pytest -q --cov=minion_process      # 100% statement coverage expected
ruff check . && mypy minion_process
```
