#!/bin/sh
set -eu
export TMP=/tmp TEMP=/tmp TMPDIR=/tmp
export CARGO_HOME=/cargo-home CARGO_TARGET_DIR=/target CARGO_BUILD_JOBS=2
export RUSTUP_HOME=/cargo-home/rustup
if [ ! -d "$RUSTUP_HOME/toolchains/1.97.1-x86_64-unknown-linux-gnu" ]; then
    mkdir -p "$RUSTUP_HOME"
    cp -r /usr/local/rustup/. "$RUSTUP_HOME/"
fi
export RUSTUP_TOOLCHAIN=1.97.1
/usr/local/cargo/bin/rustup component add rustfmt clippy > /logs/toolchain.log 2>&1
export RUST_ICU_MAJOR_VERSION_NUMBER=78
export RUSTFLAGS='-L native=/icu/icu/lib'
export RUSTDOCFLAGS='-D warnings -L native=/icu/icu/lib'
export MINION_AGENT_ICU_IDENTITY=/icu/icu-identity.txt
export LD_LIBRARY_PATH=/icu/icu/lib
export MINION_SEARCH_ENGINE_ARTIFACTS=/search-artifacts
export PYTHONPYCACHEPREFIX=/cargo-home/pycache XDG_CACHE_HOME=/cargo-home/xdg
export NODE_COMPILE_CACHE=/cargo-home/node-cache npm_config_cache=/cargo-home/npm
export PIP_CACHE_DIR=/cargo-home/pip UV_CACHE_DIR=/cargo-home/uv
mkdir -p /tmp/work /tmp/bin /logs
cp -r /source/. /tmp/work/
cp /node /tmp/bin/node
chmod +x /tmp/bin/node
export PATH=/tmp/bin:/cargo-home/rustup/toolchains/1.97.1-x86_64-unknown-linux-gnu/bin:$PATH
find /tmp/work -name '*.sh' -exec sed -i 's/\r$//' {} +
cd /tmp/work/minion-agent-rust
node --version
cargo fmt --all -- --check > /logs/fmt.log 2>&1
cargo clippy --workspace --all-targets --all-features -- -D warnings > /logs/clippy.log 2>&1
cargo test --workspace --all-features > /logs/test.log 2>&1
cargo doc --workspace --no-deps > /logs/doc.log 2>&1
cargo run -p xtask -- conformance verify > /logs/xtask.log 2>&1
# Mutants only touch this disposable tmpfs copy, after the complete green gate.
export CARGO_TARGET_DIR=/target/controls
export CARGO_PROFILE_DEV_DEBUG=0 CARGO_PROFILE_TEST_DEBUG=0 CARGO_INCREMENTAL=0
python3 scripts/prompt-assembler-negative-controls.py --tree . --logs /logs/assembler-controls
python3 scripts/request-header-negative-controls.py --tree . --logs /logs/header-controls
python3 scripts/prompt-assembly-negative-controls.py --tree . --logs /logs/assembly-controls
echo 'LINUX ALL GATES AND CONTROLS PASS'
