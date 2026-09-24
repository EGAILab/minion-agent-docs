#!/usr/bin/env bash
set -euo pipefail
exec > >(tee /work/out/build_icu.log) 2>&1
REL=https://github.com/unicode-org/icu/releases/download/release-78.3
PREFIX=/opt/icu-78.3
if [ -f "$PREFIX/.built" ]; then echo "ICU already built in volume"; exit 0; fi
mkdir -p /opt/src && cd /opt/src
curl -fsSLO "$REL/icu4c-78.3-sources.tgz"; curl -fsSLO "$REL/SHASUM512.txt"
grep -E '[[:space:]]\*?icu4c-78\.3-sources\.tgz$' SHASUM512.txt | tee expected.sha512
sha512sum -c expected.sha512
cp SHASUM512.txt expected.sha512 /work/out/
rm -rf icu && tar xzf icu4c-78.3-sources.tgz && cd icu/source
./runConfigureICU Linux --prefix="$PREFIX" --disable-samples --disable-tests > /opt/src/configure.log
grep -E "^(CFLAGS|CXXFLAGS|CPPFLAGS)" icudefs.mk | tee /work/out/icu_build_flags.txt
make -j"$(nproc)" > /opt/src/make.log 2>&1
make install > /opt/src/install.log 2>&1
touch "$PREFIX/.built"; echo "ICU built"
