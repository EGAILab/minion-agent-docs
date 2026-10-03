#!/bin/sh
set -eu
pin=04a49455e1489030c520a4bfd2664fa2171e7938d08f2acdbbcb1fda976639fd8b1f0704f2eec89ba59a7b6d118ceaab6ec5a096e40d9085a0895d91ce225245
printf '%s  %s\n' "$pin" /artifacts/icu4c-78.3-sources.tgz | sha512sum -c -
mkdir -p /build/icu-source /build/icu-build
if [ ! -e /build/icu/lib/libicuuc.so.78.3 ]; then
  tar -xzf /artifacts/icu4c-78.3-sources.tgz -C /build/icu-source
  cd /build/icu-build
  /build/icu-source/icu/source/runConfigureICU Linux --prefix=/build/icu --disable-tests --disable-samples
  make -j4
  make install
fi
{
  printf 'source-sha512 %s\nplatform linux\n' "$pin"
  for role in icuuc icui18n icudata; do
    file="lib${role}.so.78.3"
    hash=$(sha256sum "/build/icu/lib/$file" | cut -d' ' -f1)
    printf 'library %s %s %s\n' "$role" "$file" "$hash"
  done
} > /build/icu-identity.txt
export RUST_ICU_MAJOR_VERSION_NUMBER=78
export RUSTFLAGS='-L native=/build/icu/lib'
export LD_LIBRARY_PATH=/build/icu/lib
export MINION_AGENT_ICU_IDENTITY=/build/icu-identity.txt
export CARGO_HOME=/build/cargo-home
export CARGO_TARGET_DIR=/build/target
export CARGO_BUILD_JOBS=3
export CARGO_PROFILE_TEST_DEBUG=0
cd /src/minion-agent-rust
cargo test --locked -p minion-agent --all-features --test fs_path_domain_conformance -- --nocapture
cargo test --locked -p minion-agent --all-features --lib execution::path::tests -- --nocapture
cargo test --locked -p minion-agent --all-features --test fs_path_domain --no-run 2>&1 | tee /build/fs-binding-build.log
binary=$(sed -n 's/.*Executable tests\/fs_path_domain.rs (\(.*\))/\1/p' /build/fs-binding-build.log | tail -n 1)
test -n "$binary"
chmod -R a+rX /build/target /build/icu
runuser -u nobody -- env LD_LIBRARY_PATH="$LD_LIBRARY_PATH" MINION_AGENT_ICU_IDENTITY="$MINION_AGENT_ICU_IDENTITY" "$binary" --include-ignored --nocapture
