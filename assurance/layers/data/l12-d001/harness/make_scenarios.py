"""Generate the L12-D001 canonical scenarios (minion-agent conformance/agent/fs-path-domain/) from the pinned-Pi
authority's Linux AND Windows outputs, which must agree exactly (the contract is platform-neutral; macOS is
DEFERRED_WITH_REASON, Owner decision FSP-Q001 section 13).

    python make_scenarios.py <cases.json> <pi-linux.json> <pi-win32.json> <target dir>

Every step's `expect` is pinned Pi's own observation at that step.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PI = "b7bb00b936dbe21b8e160b3e89efdec361846699"
AUTHORITY = ("pinned Pi b7bb00b9 packages/agent/src/harness/env/nodejs.ts NodeExecutionEnv (imported unmodified) + "
             "coding-agent core/tools/file-mutation-queue.ts getMutationQueueKey (sliced unmodified), Node 22.15.1, "
             "identical on Linux (node:22.15.1-alpine) and Windows 11 (L12-D001 authority)")
DOCUMENTS = [
    ("fs-path-names", lambda i: i.startswith(("file/", "dir/")),
     "Each name (BMP, valid pair, explicit U+FFFD, unpaired high/low at start/middle/end, mixed, low-then-high) as "
     "the final component and as a directory component: target_key while missing (raw), write, read via the name and "
     "via its explicit U+FFFD spelling, listing (projected), canonical_path (projected), target_key once existing "
     "(projected), absolute_path (logical, raw), exists, file_info (logical name)."),
    ("fs-path-missing", lambda i: i.startswith("missing/"),
     "Missing targets: provider errors report the PROJECTED path (Node's err.path); target_key and absolute_path "
     "keep the raw logical path (Owner decision sections 7 and 11)."),
    ("fs-path-alias", lambda i: i.startswith("alias/"),
     "Owner decision sections 6-8: a<D800>, a<DC00> and a<FFFD> while missing have three distinct target keys; "
     "after a write through the first, every spelling reads the same file and shares the projected key; a second "
     "write through another spelling overwrites it; listing and canonical_path report the projected name."),
    ("fs-path-file-url", lambda i: i.startswith("file-url/"),
     "FSP-D6: a raw unpaired surrogate in a file:// string is U+FFFD after WHATWG URL parsing (before any fs call); "
     "valid percent-encoded sequences decode; percent-encoded invalid UTF-8 keeps the literal URL as an ordinary "
     "path at this Layer-12 seam (certified rule; the tool pipeline's R002-A rejection is TOOL-026's)."),
]


def main(cases_path: str, linux_path: str, win_path: str, target: str) -> None:
    cases = {c["id"]: c for c in json.load(open(cases_path, encoding="utf-8"))}
    linux = {r["id"]: r["observed"] for r in json.load(open(linux_path, encoding="utf-8"))["results"]}
    win = {r["id"]: r["observed"] for r in json.load(open(win_path, encoding="utf-8"))["results"]}
    assert linux == win, "Linux and Windows authority outputs must agree"
    docs = {name: [] for name, _, _ in DOCUMENTS}
    for cid, case in cases.items():
        observed = linux[cid]
        assert len(observed) == len(case["steps"])
        steps = [{**s, "expect": o} for s, o in zip(case["steps"], observed)]
        for name, match, _ in DOCUMENTS:
            if match(cid):
                docs[name].append({"id": cid, "steps": steps})
                break
        else:
            raise AssertionError(f"unplaced case {cid}")
    out = Path(target)
    out.mkdir(parents=True, exist_ok=True)
    for name, _, notes in DOCUMENTS:
        with open(out / f"{name}.json", "w", encoding="utf-8", newline="\n") as fh:
            json.dump({"name": name, "family": "agent", "authority": AUTHORITY, "pi_revision": PI,
                       "requirements": ["EXEC-002", "EXEC-003"], "witnesses": ["fs_path_javascript_string_domain"],
                       "platforms": ["linux", "win32"],
                       "notes": notes + " GENERATED from the pinned-Pi L12-D001 probe; regenerate with "
                                        "harness/make_scenarios.py.",
                       "fs_path_domain": {"cases": docs[name]}}, fh, indent=1)
            fh.write("\n")
    print({name: len(docs[name]) for name, _, _ in DOCUMENTS})


if __name__ == "__main__":
    main(*sys.argv[1:5])
