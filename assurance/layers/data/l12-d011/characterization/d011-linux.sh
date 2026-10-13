#!/bin/sh
# L12-D011 characterization on Linux (python:3.13). Read-only mounts: /src (Claude's main worktree), /icu-src,
# /pi, /node, /artifacts, /probes. Writable: /pipcache and /out (a new run dir), both inside the project root.
# All work in the private tmpfs /tmp; probes run as uid 1000. No deletes on host paths.
set -eu
mkdir -p /tmp/work /tmp/home /tmp/run/cwd /tmp/fd
printf 'x\n' > /tmp/run/cwd/a.ts
cp -r /src/minion-agent-python /tmp/work/
cd /tmp/work/minion-agent-python
find . -name "*.sh" -exec sed -i "s/\r$//" {} +
mkdir -p /tmp/icu && cp /icu-src/icu4c-78.3-sources.tgz /tmp/icu/
(cd /tmp/icu && bash /tmp/work/minion-agent-python/scripts/pinned-icu/build.sh /tmp/icu build > /out/icu-build.log 2>&1); echo "icu build $?"
eval "$(bash scripts/pinned-icu/build.sh /tmp/icu --env)"
PIP_CACHE_DIR=/pipcache pip install -q --root-user-action=ignore "pydantic>=2.7" "pyyaml>=6.0" "jsonschema>=4.22" \
  "httpx>=0.27" "url-py>=2026.5.1" "ada-url==1.15.3" "wasmtime==49.0.0" setuptools wheel > /out/pip.log 2>&1
pip install -q --root-user-action=ignore --no-cache-dir --no-index --no-build-isolation /pipcache/sdist/pyicu-2.16.2.tar.gz >> /out/pip.log 2>&1
python -c "import icu; print('icu', icu.ICU_VERSION)"
tar -xzf /artifacts/fd-v10.4.2-x86_64-unknown-linux-gnu.tar.gz -C /tmp/fd
FD=$(find /tmp/fd -name fd -type f | head -1)
cp /node /tmp/node && chmod +x /tmp/node
chown -R 1000:1000 /tmp/work /tmp/home /tmp/run
run() { setpriv --reuid=1000 --regid=1000 --clear-groups env HOME=/tmp/home TMPDIR=/tmp PATH=/tmp:/usr/local/bin:/usr/bin:/bin "$@"; }
run /tmp/node --experimental-strip-types --no-warnings /probes/d011_pi_probe.mjs /pi "$FD" /tmp/run /tmp/run/pi-linux.json
run sh -c "cd /tmp/work/minion-agent-python && PYTHONPATH=src python /probes/d011_py_probe.py /tmp/run /artifacts"
cp /tmp/run/pi-linux.json /tmp/run/py-linux.json /out/
echo "D011 LINUX DONE"
