"""One CE-L13-WP131-03 witness in a FRESH process: import the real PyICU (which loads its ICU), load
any extra shared objects by absolute path, print the ICU mappings, then load `ls` collation and
report ACCEPTED/REJECTED. Usage: python probe.py <label> [extra .so ...]"""

import ctypes
import sys

from minion_agent.tools.builtin import collation

label, extras = sys.argv[1], sys.argv[2:]
try:
    import icu  # noqa: F401  -- the real binding (a stand-in may shadow it via PYTHONPATH)
except ImportError:
    pass
for path in extras:
    ctypes.CDLL(path)
with open("/proc/self/maps", encoding="utf-8") as maps:
    mapped = sorted({line.split()[-1] for line in maps if "libicu" in line})
try:
    outcome = "ACCEPTED " + repr(collation.pinned_collation().sort(["b", "a"]))
except collation.PinnedIcuError as exc:
    outcome = f"REJECTED {exc}"
print(f"[{label}] ICU mappings: {mapped}")
print(f"[{label}] {outcome}")
