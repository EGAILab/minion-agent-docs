#!/usr/bin/env bash
set -euo pipefail
exec > >(tee /work/out/run2.log) 2>&1
PREFIX=/opt/icu-78.3
echo "== container: $(. /etc/os-release; echo "$PRETTY_NAME") / $(date -u +%FT%TZ)"
test -f "$PREFIX/.built" || { echo "ICU volume not built"; exit 1; }
cat /work/out/expected.sha512
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends python3 python3-dev python3-venv pkg-config clang libclang-dev >/dev/null 2>&1
DEBIAN_FRONTEND=noninteractive apt-get purge -y -qq libicu-dev >/dev/null 2>&1 || true
if ls /usr/lib/x86_64-linux-gnu/libicu*.so >/dev/null 2>&1 || [ -d /usr/include/unicode ]; then echo "FATAL: system ICU dev present"; exit 1; fi
export PKG_CONFIG_PATH="$PREFIX/lib/pkgconfig" LD_LIBRARY_PATH="$PREFIX/lib" PATH="$PREFIX/bin:$PATH"
python3 -m venv /venv && /venv/bin/pip install -q --no-cache-dir --no-binary pyicu "pyicu==2.16.2" 2>&1 | grep -v DEPRECATION || true
PYSO=$(ls /venv/lib/python3*/site-packages/icu/_icu_*.so)
ldd "$PYSO" | awk '/icu/{print $3}' | grep -qv "^$PREFIX/lib/" && { echo "FATAL: PyICU ICU outside $PREFIX"; exit 1; } || true
cd /work/rust2 && CARGO_TARGET_DIR=/tmp/t2 cargo build -q --release 2>&1 | grep -v "^warning" || true
BIN=/tmp/t2/release/r006c_rust_engine2
ldd "$BIN" | awk '/icu/{print $3}' | grep -qv "^$PREFIX/lib/" && { echo "FATAL: Rust ICU outside $PREFIX"; exit 1; } || true
echo "rust_icu crates:"; awk '/^name = "rust_icu/{n=$3} /^version/ && n{print "  "n" "$3; n=""}' Cargo.lock | tr -d '"'
cp Cargo.lock /work/out/Cargo2.lock
/venv/bin/python /work/py_engine2.py /work/corpus2.json > /work/out/python2.json
"$BIN" /work/corpus2.json > /work/out/rust2.json
/venv/bin/python /work/compare2.py /work/corpus2.json /work/out/python2.json /work/out/rust2.json /work/node_reference.json | tee /work/out/verdict2.txt
