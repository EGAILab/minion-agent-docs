"""WP-13.3 CE-WP133-02-C002 (from Codex checkpoint re-review 2, `.tmp/wp133-review/lookup_termination_race.py`):
a lookup that is live when Minion decides to interrupt it can still complete NATURALLY before the
best-effort tree kill reaches the OS. Layer 12 (section 6, L12-R020) then preserves its real exit code,
and the unchanged selection predicate (status 0 and non-empty stdout) selects its path.

    PYTHONPATH=<accepted minion-agent-python/src> python lookup_termination_race.py <out.json>

Drives the accepted `LocalSubprocess`. The only control point is `_issue_kill`: it lets the real child
exit (code 0) after `terminate()` has claimed EXPLICIT and before forwarding the real tree-kill dispatch.
No exit code or wait result is mocked. Pi's own `spawn_sync` has the same race (`Kill()` checks the
recorded exit first), so this is ordinary parity, not DIV-001."""

from __future__ import annotations

import asyncio
import json
import sys

from minion_agent.execution import subprocess as module
from minion_agent.execution.subprocess import LocalSubprocess, SpawnOptions, StdioMode

PATH = "C:/valid/bash.exe" if sys.platform == "win32" else "/valid/bash"


async def main() -> dict[str, object]:
    result = await LocalSubprocess().spawn(
        [sys.executable, "-c", f"import sys; print({PATH!r}, flush=True); sys.stdin.buffer.read(1); sys.exit(0)"],
        SpawnOptions(stdin=StdioMode.PIPED, stdout=StdioMode.PIPED),
    )
    process = result.value  # type: ignore[union-attr]
    chunk = await process.stdout.read_chunk()  # type: ignore[union-attr]
    stdout = chunk.value.decode()  # type: ignore[union-attr]
    live_at_interruption = process._proc.returncode is None
    original_issue = module._issue_kill

    async def natural_exit_before_dispatch(pid: int):  # type: ignore[no-untyped-def]
        process._proc.stdin.write(b"x")  # the child completes on its own ...
        await process._proc.wait()
        return await original_issue(pid)  # ... then the real tree kill is dispatched

    module._issue_kill = natural_exit_before_dispatch  # type: ignore[assignment]
    try:
        await process.terminate()  # the lookup's interruption (DIV-001 mechanism)
        status = await process.wait()
    finally:
        module._issue_kill = original_issue  # type: ignore[assignment]
    code = status.value.exit_code  # type: ignore[union-attr]
    first = stdout.strip().splitlines()[0] if stdout.strip() else None
    selected = first if code == 0 and stdout else None
    return {
        "python": sys.version.split()[0],
        "platform": sys.platform,
        "live_at_interruption": live_at_interruption,
        "cause": process._kill_cause,
        "wait_exit_code": code,
        "selected": selected,
        # control: discarding the real 0 because an interruption was requested selects nothing
        "control_interruption_forces_no_selection": {"selected": None, "killed": selected is not None},
    }


out = asyncio.run(main())
with open(sys.argv[1], "w", encoding="utf-8") as f:
    f.write(json.dumps(out, indent=1) + "\n")
print(json.dumps(out))
