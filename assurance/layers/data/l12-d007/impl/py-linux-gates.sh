#!/bin/sh
# L12-D007 Python implementation: full Linux gates (python:3.13). Mounts: /src the implementation worktree
# (read-only); /icu the pinned ICU 78.3 Linux tree (read-only); /pipcache and /out (writable, inside the
# project root). Work happens in the private tmpfs /tmp; tests run as non-root uid 1000.
set -eu
mkdir -p /tmp/work /tmp/home
cp -r /src/minion-agent-python /src/conformance /src/pi-parity-manifest.yaml /tmp/work/
cd /tmp/work/minion-agent-python
find . -name "*.sh" -exec sed -i "s/\r$//" {} +
# Pinned ICU 78.3 built in the private tmpfs from the project's verified source tarball (build.sh
# checks its SHA-512 and writes the identity for the libraries THIS run produced).
mkdir -p /tmp/icu && cp /icu-src/icu4c-78.3-sources.tgz /tmp/icu/
(cd /tmp/icu && bash /tmp/work/minion-agent-python/scripts/pinned-icu/build.sh /tmp/icu build > /out/icu-build.log 2>&1); echo "icu build $?"
eval "$(bash scripts/pinned-icu/build.sh /tmp/icu --env)"
PIP_CACHE_DIR=/pipcache pip install -q --root-user-action=ignore "pydantic>=2.7" "pyyaml>=6.0" "jsonschema>=4.22" \
  "httpx>=0.27" "url-py>=2026.5.1" "ada-url==1.15.3" "wasmtime==49.0.0" pytest pytest-asyncio \
  pytest-cov hypothesis ruff mypy setuptools wheel > /out/pip.log 2>&1
# PyICU is compiled against THIS run's ICU (its rpath names /tmp/icu); a cached wheel would carry another prefix.
# The SOURCE archive is kept in the project-local cache (an intermittent PyPI lookup failure otherwise aborts
# the run); it is still compiled here, against this run's ICU.
mkdir -p /pipcache/sdist
ls /pipcache/sdist/pyicu-2.16.2.tar.gz > /dev/null 2>&1 || pip download -q --retries 10 --no-deps --no-binary :all: "PyICU==2.16.2" -d /pipcache/sdist >> /out/pip.log 2>&1
pip install -q --root-user-action=ignore --no-cache-dir --no-index --no-build-isolation /pipcache/sdist/pyicu-2.16.2.tar.gz >> /out/pip.log 2>&1
python -c "import icu; print('icu', icu.ICU_VERSION)"
chown -R 1000:1000 /tmp/work /tmp/home
run() { setpriv --reuid=1000 --regid=1000 --clear-groups env HOME=/tmp/home TMPDIR=/tmp "$@"; }
echo "uid $(setpriv --reuid=1000 --regid=1000 --clear-groups id -u)"
rc=0; run sh -c "PYTHONPATH=src python -m pytest -p no:cacheprovider --no-cov --basetemp=/tmp/pt > /tmp/pytest.log 2>&1" || rc=$?; echo "pytest $rc"
cp /tmp/pytest.log /out/pytest.log
grep -E "passed|failed" /out/pytest.log | tail -1
grep -E "^FAILED|^ERROR" /out/pytest.log | head -30 || true
rc=0; run sh -c "PYTHONPATH=src python -m mypy src > /tmp/mypy.log 2>&1" || rc=$?; echo "mypy $rc"; tail -1 /tmp/mypy.log; cp /tmp/mypy.log /out/
