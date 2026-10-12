#!/bin/bash
# L12-D008 / DIV-008 on Linux: the pinned-Pi probe and the Python probe (the code worktree's binding) over
# div008-matrix.json, as uid 1000 (the natural rows need a non-root user for chmod 0555 to deny). Host mounts are
# read-only and inside the project root (proven by the reviewed guard first), except the project-local pip cache;
# all work happens in the container's private tmpfs /tmp. Output: one "== pi" and one "== py" section of JSONL.
# Usage: bash run-linux-div008.sh <code worktree dir name under review-worktrees>
set -eu
R=E:/AI/Projects/OpenMinds/Minions/Minion-Agent
CODE=$R/review-worktrees/$1
DATA=$R/review-worktrees/l12d008-docs/assurance/layers/data
PI=$R/ref-repos/pi
NODE=$R/.tmp/cache/node-22.15.1-linux
CACHE=$R/.tmp/pip-cache
node --input-type=module -e 'import {pathToFileURL} from "node:url"; const g = await import(pathToFileURL(process.argv[1]).href); for (const p of process.argv.slice(2)) g.proveReferentAbs(p);' "$DATA/l12-d007/fs-guard/fs-guard.mjs" "$CODE" "$DATA" "$PI" "$NODE" "$CACHE"
MSYS_NO_PATHCONV=1 docker run --rm --tmpfs /tmp:exec,size=2g \
  --mount "type=bind,source=$CODE,target=/code,readonly" \
  --mount "type=bind,source=$DATA,target=/data,readonly" \
  --mount "type=bind,source=$PI,target=/pi,readonly" \
  --mount "type=bind,source=$NODE,target=/node,readonly" \
  --mount "type=bind,source=$CACHE,target=/pipcache" \
  python:3.13 sh -ec '
    mkdir -p /tmp/guard-root/scratch /tmp/home /tmp/w/data /tmp/w/code
    cp -r /data/l12-d007 /data/l12-d008 /tmp/w/data/ && cp -r /code/minion-agent-python /tmp/w/code/
    cp /node/node /tmp/node && chmod +x /tmp/node
    PIP_CACHE_DIR=/pipcache pip install -q --root-user-action=ignore "pydantic>=2.7" "pyyaml>=6.0" "jsonschema>=4.22" "httpx>=0.27" "url-py>=2026.5.1" "ada-url==1.15.3" > /tmp/pip.log 2>&1
    chown -R 1000:1000 /tmp/guard-root /tmp/home /tmp/w
    run() { setpriv --reuid=1000 --regid=1000 --clear-groups env HOME=/tmp/home TMPDIR=/tmp FS_GUARD_ROOT=/tmp/guard-root "$@"; }
    cd /tmp/w/data/l12-d008
    echo "== pi"; run /tmp/node --experimental-strip-types --no-warnings div008-pi-probe.mjs /pi /tmp/guard-root/scratch
    echo "== py"; run python div008_py_probe.py /tmp/w/code /tmp/guard-root/scratch
  '
