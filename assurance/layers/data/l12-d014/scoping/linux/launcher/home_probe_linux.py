"""#236 L12-D014 scoping probe, POSIX half: where `~` gets its home directory, pinned Pi vs Python vs Rust.

Runs INSIDE a container (private tmpfs /tmp; read-only binds). Read-only: children run with cwd /tmp and a crafted
environment; nothing is created, written, renamed or deleted; results go to stdout only. Home values are strings
(or raw bytes) handed to children, never paths this probe touches. Children (each optional):
  node   -- pinned Pi resolvePath, sliced unmodified from the pinned blob (the oracle); os.homedir() too
  python -- Python LocalFileSystem.absolute_path from --pysrc (observation)
  rust   -- the ignored native_observer test of a Linux Rust test binary (observation)
Partition: HOME x USERPROFILE x uid {0 (passwd root), 1000 (no passwd entry)} x input, provider cwd /x.

    python3 home_probe_linux.py --node /node/bin/node --pi /pi [--pysrc /src] [--rust /bin/observer]
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

PI_COMMIT = "b7bb00b936dbe21b8e160b3e89efdec361846699"

NODE_CHILD = r"""
import { readFileSync } from "node:fs";
import { homedir } from "node:os";
import path from "node:path";
import { stripTypeScriptTypes } from "node:module";
import { fileURLToPath } from "node:url";
const src = readFileSync(`${process.argv[1]}/packages/agent/src/harness/env/nodejs.ts`, "utf8");
const body = stripTypeScriptTypes(src.slice(src.indexOf("function resolvePath(cwd: string, path: string): string {"),
  src.indexOf("function fileKindFromStats("))) + "\nreturn resolvePath;";
const resolvePath = new Function("homedir", "join", "fileURLToPath", "isAbsolute", "resolve", "process", body)(
  homedir, path.join, fileURLToPath, path.isAbsolute, path.resolve, process);
const units = (s) => Array.from({ length: s.length }, (_, i) => s.charCodeAt(i));
const text = (u) => String.fromCharCode(...u);
const provider = text(JSON.parse(process.argv[2]));
const inputs = JSON.parse(process.argv[3]).map(text);
let home;
try { home = { value: units(homedir()) }; } catch (e) { home = { error: String(e && e.code || e) }; }
console.log(JSON.stringify({ home, rows: inputs.map((i) => {
  try { return { value: units(resolvePath(provider, i)) }; }
  catch (e) { return { error: String(e && e.code || e) }; } }) }));
"""

PY_CHILD = r"""
import asyncio, json, os, sys
sys.path.insert(0, sys.argv[1])
from minion_agent.execution.filesystem import LocalFileSystem
def units(s):
    return list(memoryview(s.encode("utf-16-le", "surrogatepass")).cast("H"))
def text(u):
    return b"".join(x.to_bytes(2, "little") for x in u).decode("utf-16-le", "surrogatepass")
fs = LocalFileSystem(text(json.loads(sys.argv[2])))
rows = []
for u in json.loads(sys.argv[3]):
    try:
        result = asyncio.run(fs.absolute_path(text(u)))
        if hasattr(result, "value"):
            rows.append({"value": units(result.value)})
        else:
            rows.append({"error": str(getattr(result.error, "code", result.error))})
    except Exception as e:
        rows.append({"error": type(e).__name__})
print(json.dumps({"home": {"value": units(os.path.expanduser("~"))}, "rows": rows}))
"""

INPUTS = ["~", "~/a", "~\\a", "~/", "~/..", "~/a/../b", "~a", "a~"]
PROVIDER = "/x"


def units(value: str) -> list[int]:
    return list(memoryview(value.encode("utf-16-le", "surrogatepass")).cast("H"))


def complete(result: object, count: int) -> bool:
    if not isinstance(result, dict) or not isinstance(result.get("rows"), list) or len(result["rows"]) != count:
        return False
    return all(well_formed(r) for r in result["rows"])


def well_formed(row: object) -> bool:
    """Exactly one of: value = a list of UTF-16 code units (ints 0..65535), or error = a non-empty string."""
    if not isinstance(row, dict) or set(row) not in ({"value"}, {"error"}):
        return False
    if "error" in row:
        return isinstance(row["error"], str) and row["error"] != ""
    value = row["value"]
    return isinstance(value, list) and all(type(u) is int and 0 <= u <= 0xFFFF for u in value)


def as_uid(uid: int, argv: list[str]) -> list[str]:
    return argv if uid == 0 else ["setpriv", f"--reuid={uid}", f"--regid={uid}", "--clear-groups", *argv]


def run_json(argv: list[str], env: dict[bytes, bytes]) -> dict[str, object]:
    try:
        out = subprocess.run(argv, cwd="/tmp", env=env, capture_output=True, timeout=60)
    except OSError as error:
        return {"spawn_error": repr(error)}
    if out.returncode != 0:
        return {"exit": out.returncode, "stderr": out.stderr.decode("utf-8", "replace")[-400:]}
    return json.loads(out.stdout)


def run_rust(binary: str, uid: int, inputs: list[list[int]], env: dict[bytes, bytes]) -> dict[str, object]:
    payload = {"provider_cwd": units(PROVIDER), "inputs": inputs, "absent_entries": [], "process_cwd_drive_not": []}
    env = {**env, b"MINION_PATH_PROBE": json.dumps(payload).encode()}
    try:
        out = subprocess.run(as_uid(uid, [binary, "execution::path::tests::native_observer", "--exact", "--ignored",
                                          "--nocapture"]), cwd="/tmp", env=env, capture_output=True, timeout=90)
    except OSError as error:
        return {"spawn_error": repr(error)}
    lines = [x for x in out.stdout.decode("utf-8", "replace").splitlines() if x.startswith("PATH_PROBE ")]
    if out.returncode != 0 or len(lines) != 1:
        return {"exit": out.returncode, "tail": (out.stdout + out.stderr).decode("utf-8", "replace")[-600:]}
    record = json.loads(lines[0][len("PATH_PROBE "):])
    return {"rows": [{"value": r["absolute_path"]} for r in record["rows"]]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--node", required=True)
    parser.add_argument("--pi", required=True)
    parser.add_argument("--pysrc")
    parser.add_argument("--rust")
    args = parser.parse_args()
    if sys.platform != "linux":
        raise SystemExit("linux only")
    if subprocess.run([args.node, "--version"], capture_output=True, text=True, check=True).stdout.strip() != "v22.15.1":
        raise SystemExit("node is not v22.15.1")
    homes = [("unset", None), ("empty", b""), ("root", b"/"), ("ordinary", b"/h/px"), ("trailing", b"/h/px/"),
             ("double-lead", b"//h/px"), ("relative", b"rel/px"), ("non-utf8", b"/h/p\xff"),
             ("backslash", b"/h\\px"), ("long-5000", b"/" + b"p" * 4999)]
    profiles = [("unset", None), ("set", b"/u/px")]
    inputs = [units(i) for i in INPUTS]
    base = {k: v for k, v in os.environb.items() if k not in (b"HOME", b"USERPROFILE")}
    base[b"PYTHONDONTWRITEBYTECODE"] = b"1"
    report = []
    for uid in (0, 1000):
        for hname, hvalue in homes:
            for pname, pvalue in profiles:
                if pname == "set" and hname not in ("unset", "empty", "ordinary"):
                    continue  # USERPROFILE can only matter where HOME is absent or empty
                env = dict(base)
                if hvalue is not None:
                    env[b"HOME"] = hvalue
                if pvalue is not None:
                    env[b"USERPROFILE"] = pvalue
                row: dict[str, object] = {"uid": uid, "home": hname, "userprofile": pname}
                row["node"] = run_json(as_uid(uid, [args.node, "--no-warnings", "--input-type=module", "-e", NODE_CHILD,
                                                    args.pi, json.dumps(units(PROVIDER)), json.dumps(inputs)]), env)
                if args.pysrc:
                    row["python"] = run_json(as_uid(uid, [sys.executable, "-c", PY_CHILD, args.pysrc,
                                                          json.dumps(units(PROVIDER)), json.dumps(inputs)]), env)
                if args.rust:
                    row["rust"] = run_rust(args.rust, uid, inputs, env)
                # Setup failures are separated from semantic mismatches: equality is computed ONLY when the
                # oracle and the observed child both returned exactly one well-formed row per input.
                children = ["node"] + [k for k in ("python", "rust") if k in row]
                incomplete = [k for k in children if not complete(row[k], len(inputs))]
                row["status"] = "SETUP_FAILURE" if incomplete else "COMPLETE"
                if incomplete:
                    row["setup_failures"] = incomplete
                else:
                    for name in children[1:]:
                        row[name + "_equal"] = [a == b for a, b in zip(row["node"]["rows"], row[name]["rows"],
                                                                         strict=True)]
                report.append(row)
    expected_rows = 2 * (len(homes) + 3)  # uids x (every HOME with USERPROFILE unset, plus 3 HOME values with it set)
    if len(report) != expected_rows:
        raise SystemExit(f"report has {len(report)} rows, expected {expected_rows}")
    print(json.dumps({"pi": PI_COMMIT, "inputs": INPUTS, "provider": PROVIDER, "rows": len(report),
                      "setup_failures": sum(r["status"] == "SETUP_FAILURE" for r in report), "report": report},
                     indent=1, ensure_ascii=True))


if __name__ == "__main__":
    main()
