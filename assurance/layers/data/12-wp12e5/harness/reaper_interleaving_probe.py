"""WP-12.E5 convergence CE-WP12E5-01 (WP12E5-I001): can asyncio's child reaper release the PID
between the identity check and the signal of `Process.terminate_child()`'s POSIX fallback?

    PYTHONPATH=<minion-agent-python/src> python reaper_interleaving_probe.py {loop|threaded}

Adapted from Codex's closure-1 `fallback_reaping_probe.py`. The helper's own `pidfd_open` is made to
fail (ENOSYS), so the fallback (non-reaping `waitid`, then `os.kill`) runs. The wrapper around the
REAL `waitid` lets the child exit right after the check and then waits up to 2 s for the REAL watcher
to reap it before returning -- a controlled pause at the vulnerable boundary.

- `loop`: the default watcher (`PidfdChildWatcher`) reaps in a callback on the event-loop thread.
  The pause blocks that thread, so the reap cannot happen inside the window: the signal reaches the
  still-unreaped child (a zombie, harmless) and the reap follows.
- `threaded`: `ThreadedChildWatcher` reaps on its own thread, inside the window: the signal is
  addressed to a released PID (the I001 hazard).
"""

from __future__ import annotations

import asyncio
import errno
import json
import os
import sys
import threading
import warnings

from minion_agent.execution.subprocess import LocalSubprocess, SpawnOptions, StdioMode

MODE = sys.argv[1]


async def main() -> list[dict[str, object]]:
    loop = asyncio.get_running_loop()
    original_callback = loop._child_watcher_callback  # type: ignore[attr-defined]
    original_schedule = loop.call_soon_threadsafe
    original_waitid, original_kill, original_pidfd_open = os.waitid, os.kill, os.pidfd_open
    reaped = threading.Event()
    owner: dict[str, object] = {}
    trace: list[dict[str, object]] = []

    def schedule(callback, *args, **kwargs):  # type: ignore[no-untyped-def]
        if callback in (original_callback, watcher_callback):  # the threaded watcher publishes here
            trace.append({"reaped": args[0], "on": "watcher thread"})
            reaped.set()
        return original_schedule(callback, *args, **kwargs)

    def watcher_callback(pid, code, transport):  # type: ignore[no-untyped-def]  # loop-thread watcher
        if not reaped.is_set():
            trace.append({"reaped": pid, "on": "event-loop thread"})
            reaped.set()
        original_callback(pid, code, transport)

    def unavailable(pid, *args):  # type: ignore[no-untyped-def]
        raise OSError(errno.ENOSYS, "pidfd unavailable")

    def waitid(*args):  # type: ignore[no-untyped-def]
        result = original_waitid(*args)
        trace.append({"waitid": "running" if result is None else "exited"})
        owner["process"]._proc.stdin.write(b"x")  # type: ignore[attr-defined]  # let it exit now
        trace.append({"reaped_inside_window": reaped.wait(2)})
        return result

    def kill(pid, signum):  # type: ignore[no-untyped-def]
        try:
            original_waitid(os.P_PID, pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)
            target = "unreaped child"
        except ChildProcessError:
            target = "RELEASED PID"
        trace.append({"signal": signum, "target": target})
        return original_kill(pid, signum)

    loop.call_soon_threadsafe = schedule  # type: ignore[method-assign]
    loop._child_watcher_callback = watcher_callback  # type: ignore[attr-defined]
    try:
        result = await LocalSubprocess().spawn(
            [sys.executable, "-c", "import sys; print('ready', flush=True); sys.stdin.buffer.read(1); sys.exit(7)"],
            SpawnOptions(stdin=StdioMode.PIPED, stdout=StdioMode.PIPED),
        )
        process = result.value  # type: ignore[union-attr]
        owner["process"] = process
        await process.stdout.read_chunk()  # type: ignore[union-attr]
        os.waitid, os.kill, os.pidfd_open = waitid, kill, unavailable  # type: ignore[assignment]
        await process.terminate_child()
        os.waitid, os.kill, os.pidfd_open = original_waitid, original_kill, original_pidfd_open
        status = await process.wait()
        trace.append({"final_exit_code": status.value.exit_code})  # type: ignore[union-attr]
    finally:
        loop.call_soon_threadsafe = original_schedule  # type: ignore[method-assign]
        os.waitid, os.kill, os.pidfd_open = original_waitid, original_kill, original_pidfd_open
    return trace


if MODE == "threaded":
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        asyncio.set_child_watcher(asyncio.ThreadedChildWatcher())  # type: ignore[attr-defined]
with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    watcher = type(asyncio.get_child_watcher()).__name__ if MODE == "threaded" else "default"
trace = asyncio.run(main())
print(json.dumps({"python": sys.version.split()[0], "mode": MODE, "watcher": watcher, "trace": trace}))
