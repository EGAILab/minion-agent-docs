# L12-D012 native Linux characterization. Every bind source is proven inside the project root (no reparse on any
# ancestor) immediately before Docker; only /out and /pipcache are writable. Private tmpfs /tmp; no named volumes.
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
$S = "$root\.tmp\claude-scratch\i229"
$out = "$S\linux-out"
if (Test-Path -LiteralPath $out) { throw "out exists: $out" }
$null = Assert-Inside $S
New-Item -ItemType Directory -Path $out | Out-Null
$outM = Assert-Inside $out
$pi = Assert-Inside "$root\ref-repos\pi"
$probe = Assert-Inside "$S\native_probe.mjs"
$src = Assert-Inside "$root\review-worktrees\claude-d011-py\minion-agent-python"
$script = Assert-Inside "$S\linux-char.sh"
$cache = Assert-Inside "$root\.tmp\pip-cache"
"pi $(git -C $pi rev-parse HEAD); python src $(git -C $src rev-parse HEAD)"
docker run --rm --tmpfs /tmp:exec,size=1g `
  --mount "type=bind,source=$pi,target=/pi,readonly" `
  --mount "type=bind,source=$probe,target=/probe.mjs,readonly" `
  --mount "type=bind,source=$outM,target=/out" `
  node:22.15.1-bookworm-slim sh -c "cd /tmp && node --no-warnings /probe.mjs /pi > /out/native-linux.json && echo node-ok"
"node docker exit $LASTEXITCODE"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
docker run --rm --tmpfs /tmp:exec,size=2g `
  --mount "type=bind,source=$src,target=/src,readonly" `
  --mount "type=bind,source=$script,target=/char.sh,readonly" `
  --mount "type=bind,source=$cache,target=/pipcache" `
  --mount "type=bind,source=$outM,target=/out" `
  python:3.13 sh -c "tr -d '\r' < /char.sh > /tmp/char.sh && sh /tmp/char.sh"
"python docker exit $LASTEXITCODE"
exit $LASTEXITCODE
