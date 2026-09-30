#!/bin/bash
# WP-13.2 Python implementation candidate on Linux, in a disposable python:3.13-slim container:
#   /code = candidate worktree (read-only), /inputs = icu4c-78.3-sources.tgz + pyicu-2.16.2.tar.gz, /out = results.
set -uo pipefail
apt-get update -qq >/dev/null && apt-get install -y -qq g++ make python3-dev >/dev/null 2>&1
mkdir -p /work && (cd /code && tar cf - --exclude=.venv --exclude=.git .) | (cd /work && tar xf -)
cd /work/minion-agent-python
PREFIX=/opt/pinned-icu && mkdir -p $PREFIX && cp /inputs/icu4c-78.3-sources.tgz $PREFIX/
sed -i 's/\r$//' scripts/pinned-icu/build.sh
bash scripts/pinned-icu/build.sh $PREFIX > /out/icu-build.log 2>&1; echo "icu build exit=$?"
eval "$(bash scripts/pinned-icu/build.sh $PREFIX --env)"
echo "006d51e24b5ec76df6ec2130f3dde269c51db8b8cfebb7d45a427dde0d10aa52  /inputs/pyicu-2.16.2.tar.gz" | sha256sum -c -
pip install -q --root-user-action=ignore setuptools wheel >/dev/null 2>&1
pip install -q --root-user-action=ignore --no-build-isolation --no-binary pyicu /inputs/pyicu-2.16.2.tar.gz > /out/pyicu.log 2>&1; echo "pyicu exit=$?"
pip install -q --root-user-action=ignore -e . "pytest>=8" "pytest-asyncio>=0.23" "pytest-cov>=5" "hypothesis>=6.100" > /out/pip.log 2>&1; echo "pip exit=$?"
echo "== WP-13.2 conformance + unit/negative controls (root)"
python3 -m pytest -p no:cacheprovider -o addopts= -q tests/conformance/test_builtin_mutation_conformance.py tests/tools/builtin/test_wp132_mutation_tools.py 2>&1 | tail -3
echo "== WP-13.2 conformance as an unprivileged user"
useradd -m tester; chmod -R a+rwX /work /opt/pinned-icu
su tester -c "cd /work/minion-agent-python && $(env | grep -E '^(LD_LIBRARY_PATH|MINION_AGENT_ICU_IDENTITY|PATH)=' | sed 's/^/export /; s/$/;/' | tr '\n' ' ') python3 -m pytest -p no:cacheprovider -o addopts= -q tests/conformance/test_builtin_mutation_conformance.py" 2>&1 | tail -3
echo "== full suite (root)"
python3 -m pytest -p no:cacheprovider -o addopts= -q 2>&1 | tail -3
