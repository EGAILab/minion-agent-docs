. 'E:/AI/Projects/OpenMinds/Minions/Minion-Agent/.agents/project-environment.ps1'
$env:CARGO_BUILD_JOBS='2'
$env:RUST_ICU_MAJOR_VERSION_NUMBER='78'
$env:RUSTFLAGS='-L native=E:/AI/Projects/OpenMinds/Minions/Minion-Agent/.toolchain/icu-78.3-src/icu/lib64'
$env:RUSTDOCFLAGS='-D warnings -L native=E:/AI/Projects/OpenMinds/Minions/Minion-Agent/.toolchain/icu-78.3-src/icu/lib64'
$env:MINION_AGENT_ICU_IDENTITY='E:/AI/Projects/OpenMinds/Minions/Minion-Agent/.toolchain/icu-78.3-src/pinned-icu-identity.txt'
$env:PATH='E:/AI/Projects/OpenMinds/Minions/Minion-Agent/.toolchain/icu-78.3-src/icu/bin64;'+$env:PATH
$env:MINION_SEARCH_ENGINE_ARTIFACTS='E:/AI/Projects/OpenMinds/Minions/Minion-Agent/.toolchain/search-engines/dl'
$minionLogs='E:/AI/Projects/OpenMinds/Minions/Minion-Agent/.tmp/wp142-rust/logs-windows'
New-Item -ItemType Directory -Force $minionLogs | Out-Null
Set-Location 'E:/AI/Projects/OpenMinds/Minions/Minion-Agent/review-worktrees/wp142-rust/minion-agent-rust'
cargo fmt --all -- --check 2>&1 | Tee-Object "$minionLogs/fmt.log"
if ($LASTEXITCODE) { exit $LASTEXITCODE }
cargo clippy --workspace --all-targets --all-features -- -D warnings 2>&1 | Tee-Object "$minionLogs/clippy.log"
if ($LASTEXITCODE) { exit $LASTEXITCODE }
cargo test --workspace --all-features 2>&1 | Tee-Object "$minionLogs/test.log"
if ($LASTEXITCODE) { exit $LASTEXITCODE }
cargo doc --workspace --no-deps 2>&1 | Tee-Object "$minionLogs/doc.log"
if ($LASTEXITCODE) { exit $LASTEXITCODE }
cargo run -p xtask -- conformance verify 2>&1 | Tee-Object "$minionLogs/xtask.log"
exit $LASTEXITCODE
