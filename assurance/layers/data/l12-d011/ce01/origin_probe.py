"""CE-L12D011-01 revision characterization: where a genuine native NUL rejection originates, through the real
LocalSubprocess seam. The NUL check is bypassed in memory (spawn_rejection -> None) so the native call is
reached, exactly as the check-after-native-spawn / default-cwd-unchecked mutants do. No process starts: the
NUL makes the native call fail before creation. No file writes."""

import asyncio
import subprocess
import sys
import traceback
from pathlib import Path

ROOT = Path("E:/AI/Projects/OpenMinds/Minions/Minion-Agent/review-worktrees/claude-d011-py/minion-agent-python")
sys.path.insert(0, str(ROOT / "src"))
from minion_agent.execution import subprocess as seam  # noqa: E402

seam.spawn_rejection = lambda *a, **k: None  # the mutant: no pre-spawn check


async def spawn(argv, **opts):
    provider = seam.LocalSubprocess(str(ROOT))
    return await provider.spawn(argv, seam.SpawnOptions(**opts))


CASES = {
    "argv": (["python", "a\0b"], {}),
    "cwd": (["python"], {"cwd": "d\0"}),
    "env-value": (["python"], {"env": {"K": "v\0"}}),
    "env-name": (["python"], {"env": {"K\0": "v"}}),
}
for name, (argv, opts) in CASES.items():
    try:
        result = asyncio.run(spawn(argv, **opts))
        print(name, "NO EXCEPTION", result)
    except BaseException as error:  # noqa: BLE001
        tb = traceback.extract_tb(error.__traceback__)
        inner = tb[-1]
        print(f"{name}: {type(error).__module__}.{type(error).__qualname__} is ValueError={type(error) is ValueError}"
              f" msg={str(error)!r}")
        print(f"   innermost: {Path(inner.filename).name}:{inner.name}:{inner.lineno}"
              f" is_stdlib_subprocess={Path(inner.filename).resolve() == Path(subprocess.__file__).resolve()}")
        print("   seam frame present:", any(f.name == "spawn" and f.filename.endswith(str(Path("execution/subprocess.py")))
                                         for f in tb))
print(sys.version.split()[0], sys.platform)
