"""FSP-D6: certified Python's file:// path conversion (execution/filesystem.py resolve_local_path, ada-based per
L12-R002) on the same cases as url_probe.mjs. Characterization only."""
import json, struct, sys
from minion_agent.execution.filesystem import resolve_local_path

def units(s):
    d = s.encode("utf-16-le", "surrogatepass"); return list(struct.unpack(f"<{len(d)//2}H", d))

base = "file:///C:/t/" if sys.platform == "win32" else "file:///t/"
cwd = r"C:\cwd" if sys.platform == "win32" else "/cwd"
CASES = {"raw-lone-high": "a\ud800", "raw-lone-low": "a\udc00", "raw-pair": "a\U0001F600", "raw-mixed": "a\U0001F600\udc00",
         "pct-lone-high": "a%ED%A0%80", "pct-lone-low": "a%ED%B0%80", "pct-fffd": "a%EF%BF%BD", "pct-astral": "a%F0%9F%98%80",
         "pct-truncated": "a%F0%9F", "pct-overlong": "a%C0%AF"}
out = {}
for name, tail in CASES.items():
    try:
        p = resolve_local_path(cwd, base + tail)
        sep = "\\" if sys.platform == "win32" else "/"
        out[name] = {"ok": True, "tail_units": units(p[p.rfind(sep) + 1:]), "full_units": units(p)}
    except Exception as e:  # noqa: BLE001
        out[name] = {"ok": False, "raised": type(e).__name__, "message": str(e)[:120]}
json.dump({"platform": sys.platform, "cases": out}, open(sys.argv[1], "w"), indent=1)
print(json.dumps({k: (" ".join(hex(u)[2:] for u in v["tail_units"]) if v["ok"] else "RAISES " + v["raised"]) for k, v in out.items()}))
