$ErrorActionPreference='Stop'
$root='E:/AI/Projects/OpenMinds/Minions/Minion-Agent'
. ($root+'/.agents/project-environment.ps1')
. ($root+'/.agents/gate-guard.ps1')
& ($root+'/.agents/gate-preflight.ps1')
if ($LASTEXITCODE -ne 0) {throw 'preflight'}
$logroot=$root+'/.tmp/codex-scratch/l12d012-linux-observations'
if ([IO.Directory]::Exists($logroot)) {throw 'existing run; investigate'}
Guard-Op mkdir $logroot | Out-Null
$mounts=@{
    '/main'=$root+'/review-worktrees/codex-l12d012-rust-main-scope'
    '/draft'=$root+'/review-worktrees/codex-l12d012-rust-draft-scope'
    '/pi'=$root+'/ref-repos/pi'
    '/scripts'=$root+'/.tmp/codex-scratch'
    '/matrix'=$root+'/review-worktrees/codex-l12d012-scoping-docs/assurance/layers/data/l12-d012/scoping/scope-node.json'
    '/cargo-home'=$root+'/.tmp/cache/cargo-home-linux'
    '/target'=$root+'/.tmp/cache/cargo-target/linux'
    '/build'=$root+'/.toolchain/icu-78.3-linux'
    '/node'=$root+'/.tmp/cache/node-22.15.1-linux/node'
    '/search-artifacts'=$root+'/.toolchain/search-engines/dl'
    '/logs'=$logroot
}
$dockerArgs=@('run','--rm','--read-only','--tmpfs','/tmp:exec,size=6g')
foreach ($entry in $mounts.GetEnumerator()) {
    $source=(Resolve-Path -LiteralPath $entry.Value).Path
    $flags=if ($entry.Key -in @('/cargo-home','/target','/logs')) {''} else {',readonly'}
    $dockerArgs+=@('--mount',"type=bind,source=$source,target=$($entry.Key)$flags")
}
$dockerArgs+=@('-e','TMP=/tmp','-e','TEMP=/tmp','-e','TMPDIR=/tmp','-e','CARGO_BUILD_JOBS=4',
    'sha256:b1b3c9c0d921d7fa0a6d1f9ec7e4eab87f8c8ec97644c3d791450f131dec813f',
    'python3','-B','/scripts/l12d012-linux.py')
# Immediately before Docker, prove every resolved real source, not just writable mounts.
foreach ($entry in $mounts.GetEnumerator()) {
    $source=(Resolve-Path -LiteralPath $entry.Value).Path
    Assert-Inside $source | Out-Null
}
& docker @dockerArgs
if ($LASTEXITCODE -ne 0) {throw 'Linux observations failed; investigate, do not rerun blindly'}
