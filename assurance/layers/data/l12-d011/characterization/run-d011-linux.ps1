# HISTORICAL (L12D011-C001, #224 issuecomment-6139260011): this characterization script ran once, in a contained scratch run directory, and its outputs here are its record. Its computed writes were not proven per operation, so it is disabled. The guarded, reproducible evidence is gen/ (run-gen.mjs, gen_spawn_nul.mjs, merge_spawn_nul.mjs, containment-controls.mjs).
throw 'historical characterization script: disabled (L12D011-C001); use ../gen'
# Launch d011-linux.sh in python:3.13. Every bind source is proven inside the project root (no reparse on any
# ancestor) immediately before Docker; only /pipcache and /out are writable.
$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath('E:\AI\Projects\OpenMinds\Minions\Minion-Agent')
function Assert-Inside([string]$p) {
    $full = [IO.Path]::GetFullPath($p)
    if (-not $full.StartsWith($root + '\', [StringComparison]::OrdinalIgnoreCase)) { throw "outside root: $p" }
    $item = Get-Item -LiteralPath $full -Force -ErrorAction Stop
    while ($null -ne $item) {
        if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "reparse point: $($item.FullName)" }
        $item = if ($item -is [IO.DirectoryInfo]) { $item.Parent } else { $item.Directory }
    }
    return $full.Replace('\', '/')
}
$S = "$root\.tmp\claude-scratch\i195"
$out = "$S\" + $args[0]
if (Test-Path -LiteralPath $out) { throw "out exists: $out" }
$null = Assert-Inside $S
New-Item -ItemType Directory -Path $out | Out-Null
$src = Assert-Inside "$root\review-worktrees\claude-i195"
if (git -C $src status --porcelain) { throw 'source worktree dirty' }
$icu = Assert-Inside "$root\.toolchain\icu-78.3-src"
$pi = Assert-Inside "$root\ref-repos\pi"
$node = Assert-Inside "$root\.tmp\cache\node-22.15.1-linux\node"
$art = Assert-Inside "$root\.toolchain\search-engines\dl"
$probes = Assert-Inside $S
$cache = Assert-Inside "$root\.tmp\pip-cache"
$outM = Assert-Inside $out
docker run --rm --tmpfs /tmp:exec,size=6g `
  --mount "type=bind,source=$src,target=/src,readonly" `
  --mount "type=bind,source=$icu,target=/icu-src,readonly" `
  --mount "type=bind,source=$pi,target=/pi,readonly" `
  --mount "type=bind,source=$node,target=/node,readonly" `
  --mount "type=bind,source=$art,target=/artifacts,readonly" `
  --mount "type=bind,source=$probes,target=/probes,readonly" `
  --mount "type=bind,source=$cache,target=/pipcache" `
  --mount "type=bind,source=$outM,target=/out" `
  python:3.13 sh -c "tr -d '\r' < /probes/d011-linux.sh > /tmp/run.sh && sh /tmp/run.sh"
"docker exit $LASTEXITCODE"
exit $LASTEXITCODE
