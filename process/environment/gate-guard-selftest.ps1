# Self-test for gate-guard.ps1 (TOOL209-R001). It never touches disk: Invoke-GuardOp is replaced by a
# counter, and Get-GuardAttributes is replaced per case to simulate plain entries, links, missing entries and
# inspection failures. Every case runs all four operations (mkdir, write, append, remove): each refusal must
# throw AND reach zero mutation calls; each positive must reach exactly one call per operation.
#   powershell -NoProfile -File <this dir>\gate-guard-selftest.ps1
. (Join-Path $PSScriptRoot 'gate-guard.ps1')
$script:calls = 0
function Invoke-GuardOp([string]$op, [string]$full, $value) { $script:calls++ }

$root = $GuardRoot
$inside = "$root\.tmp\gate-logs\x.log"
$dirAttr = [IO.FileAttributes]::Directory
$link = [IO.FileAttributes]::Directory -bor [IO.FileAttributes]::ReparsePoint
function NotFound([string]$p) { throw [IO.FileNotFoundException]::new("not found: $p") }
function DirNotFound([string]$p) { throw [IO.DirectoryNotFoundException]::new("dir not found: $p") }
$cases = @(
    @{ name = 'contained path, real inspection'; path = $inside; attrs = $null; expect = 'ok' },
    @{ name = 'contained path, simulated plain ancestors'; path = $inside; attrs = { param($p) $dirAttr }; expect = 'ok' },
    @{ name = 'true missing target below proven parent'; path = $inside
       attrs = { param($p) if ($p -like '*\x.log') { NotFound $p } else { $dirAttr } }; expect = 'ok' },
    @{ name = 'true missing directory below proven parent'; path = $inside
       attrs = { param($p) if ($p -like '*\gate-logs' -or $p -like '*\x.log') { DirNotFound $p } else { $dirAttr } }; expect = 'ok' },
    @{ name = 'outside path'; path = 'C:\Users\x.log'; expect = 'refuse' },
    @{ name = 'project root itself'; path = $root; expect = 'refuse' },
    @{ name = 'sibling with root prefix'; path = "$root-backup\x.log"; expect = 'refuse' },
    @{ name = 'dot-dot escape'; path = "$root\.tmp\..\..\x.log"; expect = 'refuse' },
    @{ name = 'drive-relative'; path = 'E:x.log'; expect = 'refuse' },
    @{ name = 'UNC'; path = '\\server\share\x.log'; expect = 'refuse' },
    @{ name = 'empty'; path = ''; expect = 'refuse' },
    @{ name = 'junction ancestor (.tmp)'; path = $inside
       attrs = { param($p) if ($p -like '*\.tmp') { $link } else { $dirAttr } }; expect = 'refuse' },
    @{ name = 'junction above the root (Minions)'; path = $inside
       attrs = { param($p) if ($p -like '*\Minions') { $link } else { $dirAttr } }; expect = 'refuse' },
    @{ name = 'link at the target itself'; path = $inside
       attrs = { param($p) if ($p -like '*\x.log') { [IO.FileAttributes]::ReparsePoint } else { $dirAttr } }; expect = 'refuse' },
    @{ name = 'access denied on an existing ancestor (.tmp)'; path = $inside
       attrs = { param($p) if ($p -like '*\.tmp') { throw [UnauthorizedAccessException]::new("denied: $p") } else { $dirAttr } }; expect = 'refuse' },
    @{ name = 'access denied on the target'; path = $inside
       attrs = { param($p) if ($p -like '*\x.log') { throw [UnauthorizedAccessException]::new("denied: $p") } else { $dirAttr } }; expect = 'refuse' },
    @{ name = 'other I/O error on an ancestor'; path = $inside
       attrs = { param($p) if ($p -like '*\gate-logs') { throw [IO.IOException]::new("sharing violation: $p") } else { $dirAttr } }; expect = 'refuse' },
    @{ name = 'inspection returns nothing'; path = $inside; attrs = { param($p) $null }; expect = 'refuse' },
    @{ name = 'missing project root'; path = $inside
       attrs = { param($p) if ($p -like '*\Minion-Agent') { DirNotFound $p } else { $dirAttr } }; expect = 'refuse' }
)
$failed = 0
foreach ($c in $cases) {
    $script:attrsHook = $c.attrs
    if ($c.attrs) { function Get-GuardAttributes([string]$path) { & $script:attrsHook $path } }
    else { function Get-GuardAttributes([string]$path) { [IO.File]::GetAttributes($path) } }
    $results = foreach ($op in 'mkdir', 'write', 'append', 'remove') {
        $script:calls = 0
        $refused = $false
        try { [void](Guard-Op $op $c.path 'x') } catch { $refused = $true }
        $ok = if ($c.expect -eq 'ok') { (-not $refused) -and $script:calls -eq 1 } else { $refused -and $script:calls -eq 0 }
        [pscustomobject]@{ op = $op; ok = $ok; refused = $refused; calls = $script:calls }
    }
    $caseOk = @($results | Where-Object { -not $_.ok }).Count -eq 0
    if (-not $caseOk) { $failed++ }
    "{0} {1}: {2}" -f ($(if ($caseOk) { 'PASS' } else { 'FAIL' }), $c.name,
        (($results | ForEach-Object { "$($_.op) refused=$($_.refused) calls=$($_.calls)" }) -join '; '))
}
if ($failed) { "GUARD SELFTEST FAILED ($failed)"; exit 1 } else { "GUARD SELFTEST PASSED ($($cases.Count) cases x 4 operations)"; exit 0 }
