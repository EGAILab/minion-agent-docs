# L12-D011 generation: Windows half natively, then the Linux half in one private container, then the merge into the
# code worktree's conformance/agent/spawn-nul/spawn-nul.json. Every path is proven inside the project root (no reparse
# on any ancestor) immediately before use; only the new out dir and the canonical file are written.
#   powershell -File run-gen.ps1 <out dir name under .tmp\claude-scratch\i195> <code worktree dir under review-worktrees>
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
    return $full
}
$gen = Assert-Inside $PSScriptRoot
$out = "$root\.tmp\claude-scratch\i195\" + $args[0]
if (Test-Path -LiteralPath $out) { throw "out exists: $out" }
$null = Assert-Inside "$root\.tmp\claude-scratch\i195"
New-Item -ItemType Directory -Path "$out\cwd" | Out-Null
$code = Assert-Inside ("$root\review-worktrees\" + $args[1])
$pi = Assert-Inside "$root\ref-repos\pi"
$fd = Assert-Inside "$root\.tmp\wp134-engines-05jabsn8\fd.exe"
$rg = Assert-Inside "$root\.tmp\wp134-engines-05jabsn8\rg.exe"
node --experimental-strip-types --no-warnings "$gen\gen_spawn_nul.mjs" $pi $fd $rg $out "$out\win32-partial.json"
if ($LASTEXITCODE) { throw "windows generation failed" }
$node = (Assert-Inside "$root\.tmp\cache\node-22.15.1-linux\node").Replace('\', '/')
$art = (Assert-Inside "$root\.toolchain\search-engines\dl").Replace('\', '/')
docker run --rm --tmpfs /tmp:exec,size=2g `
  --mount "type=bind,source=$($pi.Replace('\','/')),target=/pi,readonly" `
  --mount "type=bind,source=$node,target=/node,readonly" `
  --mount "type=bind,source=$art,target=/artifacts,readonly" `
  --mount "type=bind,source=$($gen.Replace('\','/')),target=/gen,readonly" `
  --mount "type=bind,source=$((Assert-Inside $out).Replace('\','/')),target=/out" `
  python:3.13 sh -c "tr -d '\r' < /gen/gen-linux.sh > /tmp/gen.sh && sh /tmp/gen.sh"
if ($LASTEXITCODE) { throw "linux generation failed" }
$dest = Assert-Inside "$code\conformance\agent\spawn-nul"
node "$gen\merge_spawn_nul.mjs" "$out\win32-partial.json" "$out\linux-partial.json" "$dest\spawn-nul.json"
if ($LASTEXITCODE) { throw "merge failed" }
'GENERATION COMPLETE'
