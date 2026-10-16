$ErrorActionPreference = 'Stop'
. 'E:/AI/Projects/OpenMinds/Minions/Minion-Agent/.agents/project-environment.ps1'
. 'E:/AI/Projects/OpenMinds/Minions/Minion-Agent/.agents/gate-guard.ps1'
$root = 'E:/AI/Projects/OpenMinds/Minions/Minion-Agent'
$env:RUST_ICU_MAJOR_VERSION_NUMBER = '78'
$env:RUSTFLAGS = '-L native=' + $root + '/.toolchain/icu-78.3-src/icu/lib64'
$env:MINION_AGENT_ICU_IDENTITY = $root + '/.toolchain/icu-78.3-src/pinned-icu-identity.txt'
$env:MINION_SEARCH_ENGINE_ARTIFACTS = $root + '/.toolchain/search-engines/dl'
$env:PATH = $root + '/.toolchain/icu-78.3-src/icu/bin64;' + $env:PATH
$env:CARGO_BUILD_JOBS = '4'
$env:CARGO_TARGET_DIR = $root + '/.tmp/cache/cargo-target/windows'
$observer = [IO.File]::ReadAllText($root + '/.tmp/codex-scratch/l12d012-observer.rs')
foreach ($variant in @('main', 'draft')) {
    $tree = $root + '/review-worktrees/codex-l12d012-rust-' + $variant + '-scope'
    $execution = $tree + '/minion-agent-rust/crates/minion-agent/src/execution'
    $module = [IO.File]::ReadAllText($execution + '/mod.rs')
    if ($module.Contains('mod l12d012_scoping;')) { throw 'observer already installed; investigate' }
    $text = $observer
    if ($variant -eq 'draft') {
        $text = $text.Replace('None; // DRAFT_ENTRY', 'Some(super::path::resolve_logical(&FsPath::from(cwd), &raw)); // DRAFT_ENTRY')
    }
    $target = Assert-Inside ($execution + '/l12d012_scoping.rs')
    [IO.File]::WriteAllText($target, $text)
    $target = Assert-Inside ($execution + '/mod.rs')
    [IO.File]::WriteAllText($target, $module + "`n#[cfg(test)]`nmod l12d012_scoping;`n")
    & ($root + '/review-worktrees/ri001-code/minion-agent-python/.venv/Scripts/python.exe') ($tree + '/minion-agent-rust/scripts/cargo-cache-safety.py') --tree ($tree + '/minion-agent-rust')
    if ($LASTEXITCODE -ne 0) { throw 'freshness failed' }
    Push-Location ($tree + '/minion-agent-rust')
    try {
        $log = Assert-Inside ($root + '/.tmp/codex-scratch/l12d012-' + $variant + '-windows-build.jsonl')
        & cargo test --locked -p minion-agent --lib --no-run --message-format=json 1> $log
        $result = $LASTEXITCODE
        if ($result -ne 0) { throw "build failed $variant ($result)" }
        $entries=Get-Content -LiteralPath $log | ForEach-Object { $_ | ConvertFrom-Json }
        $artifacts=@($entries | Where-Object { $_.reason -eq 'compiler-artifact' -and $_.target.name -eq 'minion_agent' -and $_.profile.test -and $_.executable })
        if ($artifacts.Count -ne 1) { throw 'one observer artifact required' }
        $binary=Assert-Inside ($root + '/.tmp/codex-scratch/l12d012-' + $variant + '-observer.exe')
        [IO.File]::Copy($artifacts[0].executable,$binary,$false)
    } finally { Pop-Location }
}
