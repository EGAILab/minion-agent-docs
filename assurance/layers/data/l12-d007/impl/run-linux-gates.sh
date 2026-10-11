#!/bin/bash
# Launch py-linux-gates.sh in python:3.13. Every host mount is inside the project root; only /pipcache and
# /out are writable. Work happens in the container's private tmpfs /tmp.
set -u
R=E:/AI/Projects/OpenMinds/Minions/Minion-Agent
OUT=$R/.tmp/claude-scratch/l12d007/py-linux-gates
mkdir -p "$OUT" "$R/.tmp/pip-cache"
MSYS_NO_PATHCONV=1 docker run --rm --tmpfs /tmp:exec,size=6g \
  --mount "type=bind,source=$R/review-worktrees/l12d007-code,target=/src,readonly" \
  --mount "type=bind,source=$R/.toolchain/icu-78.3-src,target=/icu-src,readonly" \
  --mount "type=bind,source=$R/.tmp/pip-cache,target=/pipcache" \
  --mount "type=bind,source=$OUT,target=/out" \
  --mount "type=bind,source=$R/.tmp/claude-scratch/l12d007/py-linux-gates.sh,target=/gates.sh,readonly" \
  python:3.13 sh /gates.sh
