"""L12-D007 implementation stage: widen the 10 L12-D001 Linux-only (#67) error-origin cases of
conformance/agent/fs-path-domain/fs-path-error-origin.json to both platforms.

Authority for Windows: pinned Pi's real provider through the guarded L12-D007 oracle
(`pi_oracle.mjs` on these cases' own steps -> d001-oracle-win32.json). A step whose Windows
observation equals its existing (Linux) expectation keeps `expect`; otherwise it becomes
`expect_by_platform`. The `platforms` / `platform_note` limitation (#67) is removed; L12-D007
closes #67. Deterministic; refuses to run if any case is missing.

    python widen_d001.py <fs-path-error-origin.json> <d001-oracle-win32.json>
"""

import json
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fs-guard"))
from fs_guard import assert_output  # noqa: E402


path, oracle_path = sys.argv[1], sys.argv[2]
doc = json.load(open(path, encoding="utf-8"))
win = {r["id"]: r["observed"] for r in json.load(open(oracle_path, encoding="utf-8"))["results"]}
widened = 0
for case in doc["fs_path_domain"]["cases"]:
    if case.get("platforms") != ["linux"]:
        continue
    if "#67" not in case.get("platform_note", ""):
        sys.exit(f"{case['id']}: Linux-only for a reason other than #67; not widened")
    observed = win[case["id"]]
    for i, step in enumerate(case["steps"]):
        if "expect" not in step:
            sys.exit(f"{case['id']} step {i}: already per-platform")
        if observed[i] != step["expect"]:
            step["expect_by_platform"] = {"linux": step.pop("expect"), "win32": observed[i]}
    del case["platforms"]
    del case["platform_note"]
    widened += 1
if widened != len(win):
    sys.exit(f"widened {widened}, oracle has {len(win)}")
with open(assert_output(path), "w", encoding="utf-8", newline="\n") as f:
    json.dump(doc, f, indent=1, ensure_ascii=False)
    f.write("\n")
print(f"widened {widened} cases to both platforms")
