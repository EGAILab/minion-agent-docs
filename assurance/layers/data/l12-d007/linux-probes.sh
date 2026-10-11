#!/bin/sh
# L12-D007 Linux characterization: pinned Pi and Python's LocalFileSystem, same POSIX condition matrix.
# Sources are read-only mounts; every sandbox lives in the container's private tmpfs /tmp
# (FS_GUARD_ROOT=/tmp/guard-root). The only writable host mount is /out.
set -eu
export FS_GUARD_ROOT=/tmp/guard-root FS_GUARD_OUTPUT=/out TMPDIR=/tmp HOME=/tmp/home
mkdir -p "$FS_GUARD_ROOT" /tmp/home /tmp/probe
cp /probe/*.mjs /probe/*.py /tmp/probe/
mkdir -p /tmp/probe/fs-guard && cp /probe/fs-guard/*.py /probe/fs-guard/*.mjs /tmp/probe/fs-guard/
cd /tmp/probe
uid=$(id -u); echo "uid $uid"
/node --experimental-strip-types --no-warnings pi-error-probe.mjs /pi /out/pi-linux.json | tail -1
PIP_CACHE_DIR=/pipcache pip install -q --root-user-action=ignore --target /tmp/site ada-url==1.15.3 "pydantic>=2.7" "pyyaml>=6.0" "jsonschema>=4.22" "httpx>=0.27" "url-py>=2026.5.1" 2>&1 | tail -1
export PYTHONPATH=/src:/tmp/site
python3 py-error-probe.py /out/py-linux.json | tail -1
