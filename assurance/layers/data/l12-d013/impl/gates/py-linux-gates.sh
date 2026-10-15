#!/bin/sh
# #235 L12-D013 Python implementation: full Linux gates (python:3.13), run by run-linux-gates.mjs. Every bind is
# read-only; all work is in the private tmpfs /tmp at fixed literal paths; tests run as uid 1000. STDOUT carries ONLY
# the bundle: for each label in a fixed order, "@@BEGIN <nonce> <label> <exit>@@", its log, "@@END <nonce> <label>@@".
# Everything else goes to that label's log in /tmp or to stderr. Each gate's exit code is recorded as-is.
set -u
N="$GATE_NONCE"
emit() { printf '@@BEGIN %s %s %s@@\n' "$N" "$1" "$2"; cat "$3"; printf '\n@@END %s %s@@\n' "$N" "$1"; }
mkdir -p /tmp/work /tmp/home /tmp/icu
cp -r /src/minion-agent-python /src/conformance /src/pi-parity-manifest.yaml /tmp/work/ >&2
find /tmp/work -name "*.sh" -exec sed -i "s/\r$//" {} + >&2
cd /tmp/work/minion-agent-python || exit 1

cp /icu-src/icu4c-78.3-sources.tgz /tmp/icu/
rc=0; (cd /tmp/icu && bash /tmp/work/minion-agent-python/scripts/pinned-icu/build.sh /tmp/icu build) > /tmp/icu-build.log 2>&1 || rc=$?
emit icu-build "$rc" /tmp/icu-build.log
eval "$(bash scripts/pinned-icu/build.sh /tmp/icu --env)" >&2

rc=0
{ pip install -q --root-user-action=ignore --no-cache-dir "pydantic>=2.7" "pyyaml>=6.0" "jsonschema>=4.22" \
    "httpx>=0.27" "url-py>=2026.5.1" "ada-url==1.15.3" "wasmtime==49.0.0" pytest pytest-asyncio \
    pytest-cov hypothesis ruff mypy setuptools wheel \
  && pip install -q --root-user-action=ignore --no-cache-dir --no-index --no-build-isolation /sdist/pyicu-2.16.2.tar.gz; } \
  > /tmp/pip.log 2>&1 || rc=$?
emit pip "$rc" /tmp/pip.log

rc=0
{ python -c "import icu; print('icu', icu.ICU_VERSION)" && python -m pytest --version \
  && echo "uid $(setpriv --reuid=1000 --regid=1000 --clear-groups id -u)"; } > /tmp/versions.log 2>&1 || rc=$?
emit versions "$rc" /tmp/versions.log

chown -R 1000:1000 /tmp/work /tmp/home
gate() {  # gate <label> <command>: as uid 1000 in the work tree; the log stays in /tmp, then is emitted
  label=$1; shift
  rc=0
  setpriv --reuid=1000 --regid=1000 --clear-groups env HOME=/tmp/home TMPDIR=/tmp MINION_SEARCH_ENGINE_ARTIFACTS=/artifacts \
    sh -c "cd /tmp/work/minion-agent-python && $*" > "/tmp/$label.log" 2>&1 || rc=$?
  emit "$label" "$rc" "/tmp/$label.log"
}
gate pytest "PYTHONPATH=src python -m pytest -p no:cacheprovider --basetemp=/tmp/pt"
gate mypy "PYTHONPATH=src python -m mypy --cache-dir /tmp/mypy-cache src"
gate ruff "python -m ruff check --no-cache src tests"
