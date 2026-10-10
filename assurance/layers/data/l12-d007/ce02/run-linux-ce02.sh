#!/bin/bash
# CE-L12D007-02 on Linux: the pinned-Pi probe and the Python probe (the candidate in <code worktree>) over the same
# matrix, as uid 1000. Host mounts are read-only and inside the project root (proven by the reviewed guard first),
# except the project-local pip cache; work happens in the container's private tmpfs /tmp.
# Usage: bash run-linux-ce02.sh <code worktree dir name under review-worktrees>
set -eu
R=E:/AI/Projects/OpenMinds/Minions/Minion-Agent
CODE=$R/review-worktrees/$1
DATA=$R/review-worktrees/l12d007-docs/assurance/layers/data/l12-d007
PI=$R/ref-repos/pi
NODE=$R/.tmp/cache/node-22.15.1-linux
CACHE=$R/.tmp/pip-cache
node --input-type=module -e 'import {pathToFileURL} from "node:url"; const g = await import(pathToFileURL(process.argv[1]).href); for (const p of process.argv.slice(2)) g.proveReferentAbs(p);' "$DATA/fs-guard/fs-guard.mjs" "$CODE" "$DATA" "$PI" "$NODE" "$CACHE"
MSYS_NO_PATHCONV=1 docker run --rm --tmpfs /tmp:exec,size=2g \
  --mount "type=bind,source=$CODE,target=/code,readonly" \
  --mount "type=bind,source=$DATA,target=/data,readonly" \
  --mount "type=bind,source=$PI,target=/pi,readonly" \
  --mount "type=bind,source=$NODE,target=/node,readonly" \
  --mount "type=bind,source=$CACHE,target=/pipcache" \
  python:3.13 sh -ec '
    mkdir -p /tmp/guard-root/scratch /tmp/home /tmp/w
    cp -r /data /tmp/w/data && cp -r /code/minion-agent-python /tmp/w/code-py
    mkdir -p /tmp/w/code && mv /tmp/w/code-py /tmp/w/code/minion-agent-python
    cp /node/node /tmp/node && chmod +x /tmp/node
    PIP_CACHE_DIR=/pipcache pip install -q --root-user-action=ignore "pydantic>=2.7" "pyyaml>=6.0" "jsonschema>=4.22" "httpx>=0.27" "url-py>=2026.5.1" "ada-url==1.15.3" > /tmp/pip.log 2>&1
    chown -R 1000:1000 /tmp/guard-root /tmp/home /tmp/w
    run() { setpriv --reuid=1000 --regid=1000 --clear-groups env HOME=/tmp/home TMPDIR=/tmp FS_GUARD_ROOT=/tmp/guard-root "$@"; }
    cd /tmp/w/data/ce02
    echo "== pi"; run /tmp/node --experimental-strip-types --no-warnings ce02-pi-probe.mjs /pi /tmp/guard-root/scratch
    echo "== py"; run python ce02_py_probe.py /tmp/w/code /tmp/guard-root/scratch
    echo "== pi-recovery"; run /tmp/node --experimental-strip-types --no-warnings ce02-recovery-pi-probe.mjs /pi /tmp/guard-root/scratch
    echo "== py-recovery"; run python ce02_recovery_py_probe.py /tmp/w/code /tmp/guard-root/scratch
    echo "== pi-validation"; run /tmp/node --experimental-strip-types --no-warnings ce02-recovery-pi-probe.mjs /pi /tmp/guard-root/scratch ce02-validation-matrix.json
    echo "== py-validation"; run python ce02_recovery_py_probe.py /tmp/w/code /tmp/guard-root/scratch ce02-validation-matrix.json
  '
