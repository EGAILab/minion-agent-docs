#!/bin/bash
# CE-L13-WP131-03 Linux evidence, in a disposable python:3.12-slim container:
#   /code  = minion-agent candidate worktree (read-only), /evid = this directory (read-only),
#   /inputs = icu4c-78.3-sources.tgz + pyicu-2.16.2.tar.gz (read-only), /out = results.
set -uo pipefail
apt-get update -qq >/dev/null && apt-get install -y -qq g++ make python3-dev >/dev/null 2>&1
cp -r /code /work && cd /work/minion-agent-python && rm -rf .venv
PREFIX=/opt/pinned-icu && mkdir -p $PREFIX && cp /inputs/icu4c-78.3-sources.tgz $PREFIX/
sed -i 's/\r$//' scripts/pinned-icu/build.sh
echo "== build.sh (verified tarball -> fresh extract -> compile -> clean install -> identity)"
time bash scripts/pinned-icu/build.sh $PREFIX > /out/build.log 2>&1; echo "build exit=$?"
cat $PREFIX/pinned-icu-identity.txt
eval "$(bash scripts/pinned-icu/build.sh $PREFIX --env)"
echo "== PyICU 2.16.2 from the hash-checked sdist against the pinned build"
echo "006d51e24b5ec76df6ec2130f3dde269c51db8b8cfebb7d45a427dde0d10aa52  /inputs/pyicu-2.16.2.tar.gz" | sha256sum -c -
pip install -q --root-user-action=ignore --no-build-isolation setuptools wheel >/dev/null 2>&1
pip install -q --root-user-action=ignore --no-build-isolation --no-binary pyicu /inputs/pyicu-2.16.2.tar.gz > /out/pyicu.log 2>&1; echo "pyicu exit=$?"
pip install -q --root-user-action=ignore "pydantic>=2.7" "pyyaml>=6.0" "jsonschema>=4.22" "httpx>=0.27" "url-py>=2026.5.1" "ada-url==1.15.3" "wasmtime==49.0.0" "pytest>=8" "pytest-asyncio>=0.23" "hypothesis>=6.100" >/dev/null 2>&1
pip install -q --root-user-action=ignore --no-deps . >/dev/null 2>&1
LIB=$PREFIX/install/lib
F=/tmp/foreign && mkdir -p $F
cd /tmp
echo "== witnesses (each a fresh process)"
python3 /evid/probe.py verified-only
cp "$(readlink -f $LIB/libicui18n.so.78)" $F/libicui18n.so.78.3 && printf '\0another 78.3 build' >> $F/libicui18n.so.78.3
python3 /evid/probe.py W-F1-second-foreign-i18n-mapping $F/libicui18n.so.78.3
mkdir -p /tmp/twin && cp "$(readlink -f $LIB/libicui18n.so.78)" /tmp/twin/libicui18n.so.78.3
python3 /evid/probe.py W-F2-byte-identical-twin /tmp/twin/libicui18n.so.78.3
mkdir -p /tmp/other && cp "$(readlink -f $LIB/libicuuc.so.78)" /tmp/other/libicuuc.so.77.1
python3 /evid/probe.py W-F3-unlisted-icu-library /tmp/other/libicuuc.so.77.1
mkdir -p /tmp/stand-in/icu && printf 'VERSION = "2.16.2"\nICU_VERSION = "78.3"\n' > /tmp/stand-in/icu/__init__.py
PYTHONPATH=/tmp/stand-in python3 /evid/probe.py W-F7-stand-in-binding
echo "== W-F5: no re-attestation of a substituted binary"
cp $PREFIX/pinned-icu-identity.txt /tmp/identity.before
printf '\0substituted after the build' >> "$(readlink -f $LIB/libicui18n.so.78)"
bash /work/minion-agent-python/scripts/pinned-icu/build.sh $PREFIX --identity; echo "--identity exit=$?"
cmp -s /tmp/identity.before $PREFIX/pinned-icu-identity.txt && echo "identity file unchanged"
python3 /evid/probe.py W-F6-substituted-same-version-binary-in-the-verified-prefix
echo "== identity unit tests on Linux (Windows-only real tests skip)"
cd /work/minion-agent-python && python3 -m pytest -p no:cacheprovider -o addopts= -q tests/tools/builtin/test_collation_build_identity.py 2>&1 | tail -3
