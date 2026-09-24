#!/usr/bin/env bash
# R006-C differential proof. Runs ONLY inside a disposable container; ICU 78.3 comes from the
# named volume built by build_icu.sh from the checksum-verified official tarball.
set -euo pipefail
exec > >(tee /work/out/run.log) 2>&1
PREFIX=/opt/icu-78.3
echo "== container: $(. /etc/os-release; echo "$PRETTY_NAME") / $(uname -m) / $(date -u +%FT%TZ)"
test -f "$PREFIX/.built" || { echo "ICU volume not built"; exit 1; }
echo "== sha512 recorded at build time:"; cat /work/out/expected.sha512

echo "== toolchain packages (inside container only)"
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends \
  python3 python3-dev python3-venv pkg-config clang libclang-dev >/dev/null 2>&1
echo "system ICU dev before purge: $(dpkg -l | awk '/^ii +libicu-dev/{print $2" "$3}')"
DEBIAN_FRONTEND=noninteractive apt-get purge -y -qq libicu-dev >/dev/null 2>&1 || true
if ls /usr/lib/x86_64-linux-gnu/libicu*.so >/dev/null 2>&1 || [ -d /usr/include/unicode ]; then
  echo "FATAL: system ICU dev files still present"; exit 1; fi
echo "system ICU dev after purge: none (no unversioned libicu*.so, no /usr/include/unicode)"

export PKG_CONFIG_PATH="$PREFIX/lib/pkgconfig" LD_LIBRARY_PATH="$PREFIX/lib" PATH="$PREFIX/bin:$PATH"
echo "pkg-config icu-i18n: $(pkg-config --modversion icu-i18n)"

echo "== PyICU 2.16.2 against the shared build"
python3 -m venv /venv
/venv/bin/pip install -q --no-cache-dir --no-binary pyicu "pyicu==2.16.2" 2>&1 | grep -v DEPRECATION || true
PYSO=$(ls /venv/lib/python3*/site-packages/icu/_icu_*.so)
echo "PyICU NEEDED:"; readelf -d "$PYSO" | awk '/NEEDED/ && /icu/{print "  "$NF}'
echo "PyICU resolves:"; ldd "$PYSO" | awk '/icu/{print "  "$1" => "$3}'
ldd "$PYSO" | awk '/icu/{print $3}' | grep -qv "^$PREFIX/lib/" && { echo "FATAL: PyICU resolves ICU outside $PREFIX"; exit 1; } || true

echo "== rust_icu_ucol 5.8.0 against the same shared build"
cd /work/rust
CARGO_TARGET_DIR=/tmp/target cargo build -q --release 2>&1 | grep -v "^warning" || true
BIN=/tmp/target/release/r006c_rust_engine
echo "resolved rust_icu crates:"; awk '/^name = "rust_icu/{n=$3} /^version/ && n{print "  "n" "$3; n=""}' Cargo.lock | tr -d '"'
cp Cargo.lock /work/out/Cargo.lock
echo "Rust resolves:"; ldd "$BIN" | awk '/icu/{print "  "$1" => "$3}'
ldd "$BIN" | awk '/icu/{print $3}' | grep -qv "^$PREFIX/lib/" && { echo "FATAL: Rust resolves ICU outside $PREFIX"; exit 1; } || true

echo "== run engines"
/venv/bin/python /work/py_engine.py /work/corpus.json > /work/out/python.json
"$BIN" /work/corpus.json > /work/out/rust.json
/venv/bin/python /work/compare.py /work/corpus.json /work/out/python.json /work/out/rust.json | tee /work/out/verdict.txt
