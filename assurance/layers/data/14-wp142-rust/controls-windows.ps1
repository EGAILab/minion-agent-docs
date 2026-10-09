. 'E:/AI/Projects/OpenMinds/Minions/Minion-Agent/.agents/project-environment.ps1'
$env:CARGO_BUILD_JOBS='2'
$env:RUST_ICU_MAJOR_VERSION_NUMBER='78'
$env:RUSTFLAGS='-L native=E:/AI/Projects/OpenMinds/Minions/Minion-Agent/.toolchain/icu-78.3-src/icu/lib64'
$env:MINION_AGENT_ICU_IDENTITY='E:/AI/Projects/OpenMinds/Minions/Minion-Agent/.toolchain/icu-78.3-src/pinned-icu-identity.txt'
$env:MINION_SEARCH_ENGINE_ARTIFACTS='E:/AI/Projects/OpenMinds/Minions/Minion-Agent/.toolchain/search-engines/dl'
$env:PATH='E:/AI/Projects/OpenMinds/Minions/Minion-Agent/.toolchain/icu-78.3-src/icu/bin64;'+$env:PATH
$minionScratch='E:/AI/Projects/OpenMinds/Minions/Minion-Agent/.tmp/wp142-rust/controls-code'
robocopy 'E:/AI/Projects/OpenMinds/Minions/Minion-Agent/review-worktrees/wp142-rust/minion-agent-rust' "$minionScratch/minion-agent-rust" /E /NFL /NDL /NJH /NJS /NP
if ($LASTEXITCODE -ge 8) { exit $LASTEXITCODE }
robocopy 'E:/AI/Projects/OpenMinds/Minions/Minion-Agent/review-worktrees/wp142-rust/conformance' "$minionScratch/conformance" /E /NFL /NDL /NJH /NJS /NP
if ($LASTEXITCODE -ge 8) { exit $LASTEXITCODE }
robocopy 'E:/AI/Projects/OpenMinds/Minions/Minion-Agent/review-worktrees/wp142-rust/minion-agent-python/tests' "$minionScratch/minion-agent-python/tests" /E /NFL /NDL /NJH /NJS /NP
if ($LASTEXITCODE -ge 8) { exit $LASTEXITCODE }
$env:CARGO_TARGET_DIR='E:/AI/Projects/OpenMinds/Minions/Minion-Agent/.tmp/cache/cargo-target/windows-wp142-controls'
$env:CARGO_PROFILE_DEV_DEBUG='0'
$env:CARGO_PROFILE_TEST_DEBUG='0'
$env:CARGO_INCREMENTAL='0'
$minionPython='E:/AI/Projects/OpenMinds/Minions/Minion-Agent/minion-agent/minion-agent-python/.venv/Scripts/python.exe'
& $minionPython "$minionScratch/minion-agent-rust/scripts/prompt-assembler-negative-controls.py" --tree "$minionScratch/minion-agent-rust" --logs 'E:/AI/Projects/OpenMinds/Minions/Minion-Agent/.tmp/wp142-rust/controls-assembler-windows-complete'
if ($LASTEXITCODE) { exit $LASTEXITCODE }
& $minionPython "$minionScratch/minion-agent-rust/scripts/request-header-negative-controls.py" --tree "$minionScratch/minion-agent-rust" --logs 'E:/AI/Projects/OpenMinds/Minions/Minion-Agent/.tmp/wp142-rust/controls-header-windows'
if ($LASTEXITCODE) { exit $LASTEXITCODE }
& $minionPython "$minionScratch/minion-agent-rust/scripts/prompt-assembly-negative-controls.py" --tree "$minionScratch/minion-agent-rust" --logs 'E:/AI/Projects/OpenMinds/Minions/Minion-Agent/.tmp/wp142-rust/controls-assembly-windows'
exit $LASTEXITCODE
