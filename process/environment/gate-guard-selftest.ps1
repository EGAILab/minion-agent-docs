# Self-test for gate-guard.ps1 (TOOL209-R001). It never touches disk: Invoke-GuardOp is replaced by a
# counter, and Get-GuardAttributes / Test-GuardExists are replaced per case to simulate links and failed
# inspections. Each refusal case must throw AND reach zero mutation calls; each positive case must reach
# exactly one.
#   powershell -NoProfile -File <this dir>\gate-guard-selftest.ps1
. (Join-Path $PSScriptRoot 'gate-guard.ps1')
$script:calls = 0
function Invoke-GuardOp([string]$op, [string]$full, $value) { $script:calls++ }

$root = $GuardRoot
$inside = "$root\.tmp\gate-logs\x.log"
$normal = { param($p) [IO.FileAttributes]::Directory }
$cases = @(
    @{ name = 'contained path, real inspection'; path = $inside; exists = $null; attrs = $null; expect = 'ok' },
    @{ name = 'contained path, simulated plain ancestors'; path = $inside; exists = { param($p) $true }; attrs = $normal; expect = 'ok' },
    @{ name = 'outside path'; path = 'C:\Users\x.log'; expect = 'refuse' },
    @{ name = 'project root itself'; path = $root; expect = 'refuse' },
    @{ name = 'sibling with root prefix'; path = "$root-backup\x.log"; expect = 'refuse' },
    @{ name = 'dot-dot escape'; path = "$root\.tmp\..\..\x.log"; expect = 'refuse' },
    @{ name = 'drive-relative'; path = 'E:x.log'; expect = 'refuse' },
    @{ name = 'UNC'; path = '\\server\share\x.log'; expect = 'refuse' },
    @{ name = 'empty'; path = ''; expect = 'refuse' },
    @{ name = 'junction ancestor (.tmp)'; path = $inside; exists = { param($p) $true }
       attrs = { param($p) if ($p -like '*\.tmp') { [IO.FileAttributes]::Directory -bor [IO.FileAttributes]::ReparsePoint } else { [IO.FileAttributes]::Directory } }
       expect = 'refuse' },
    @{ name = 'junction above the root (Minions)'; path = $inside; exists = { param($p) $true }
       attrs = { param($p) if ($p -like '*\Minions') { [IO.FileAttributes]::ReparsePoint } else { [IO.FileAttributes]::Directory } }
       expect = 'refuse' },
    @{ name = 'link at the target itself'; path = $inside; exists = { param($p) $true }
       attrs = { param($p) if ($p -like '*\x.log') { [IO.FileAttributes]::ReparsePoint } else { [IO.FileAttributes]::Directory } }
       expect = 'refuse' },
    @{ name = 'inspection throws'; path = $inside; exists = { param($p) $true }; attrs = { param($p) throw 'access denied' }; expect = 'refuse' },
    @{ name = 'inspection returns nothing'; path = $inside; exists = { param($p) $true }; attrs = { param($p) $null }; expect = 'refuse' }
)
$failed = 0
foreach ($c in $cases) {
    $script:existsHook = $c.exists
    $script:attrsHook = $c.attrs
    if ($c.exists) { function Test-GuardExists([string]$path) { & $script:existsHook $path } }
    else { function Test-GuardExists([string]$path) { [IO.File]::Exists($path) -or [IO.Directory]::Exists($path) } }
    if ($c.attrs) { function Get-GuardAttributes([string]$path) { & $script:attrsHook $path } }
    else { function Get-GuardAttributes([string]$path) { [IO.File]::GetAttributes($path) } }
    $script:calls = 0
    $refused = $false
    try { [void](Guard-Op 'write' $c.path 'x') } catch { $refused = $true; $why = $_.Exception.Message }
    $ok = if ($c.expect -eq 'ok') { (-not $refused) -and $script:calls -eq 1 } else { $refused -and $script:calls -eq 0 }
    if (-not $ok) { $failed++ }
    "{0} {1}: refused={2} mutation_calls={3}" -f ($(if ($ok) { 'PASS' } else { 'FAIL' }), $c.name, $refused, $script:calls)
}
if ($failed) { "GUARD SELFTEST FAILED ($failed)"; exit 1 } else { "GUARD SELFTEST PASSED ($($cases.Count) cases)"; exit 0 }
