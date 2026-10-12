# Containment guard for the gate tooling's own writes (minion-agent#209, TOOL209-R001). Dot-source it:
#   . (Join-Path $PSScriptRoot 'gate-guard.ps1')
# Every create, write, append or delete goes through Guard-Op. Guard-Op proves containment IMMEDIATELY
# before that one operation, and nothing runs when the proof fails (fail closed):
#   1. form: refuse empty paths, UNC/device paths (\\...), drive-relative forms (X:foo) and '..' segments;
#   2. lexical: the full path must lie strictly below the project root;
#   3. real path: every existing component from the drive root down to the target is inspected, and a
#      reparse point (junction or link) anywhere, or a failed inspection, refuses the operation.
# Get-GuardAttributes (inspection) and Invoke-GuardOp (the mutation) are the only seams; the guard
# self-test (gate-guard-selftest.ps1) overrides them to count mutation calls without touching disk.
$GuardRoot = 'E:\AI\Projects\OpenMinds\Minions\Minion-Agent'

function Get-GuardAttributes([string]$path) {
    return [IO.File]::GetAttributes($path)
}

function Test-GuardExists([string]$path) {
    return [IO.File]::Exists($path) -or [IO.Directory]::Exists($path)
}

function Assert-Inside([string]$path) {
    if ([string]::IsNullOrWhiteSpace($path)) { throw 'containment: empty path' }
    if ($path.StartsWith('\\') -or $path.StartsWith('//')) { throw "containment: UNC or device path refused: $path" }
    if ($path -match '^[A-Za-z]:(?![\\/])') { throw "containment: drive-relative path refused: $path" }
    if ($path -match '(^|[\\/])\.\.([\\/]|$)') { throw "containment: '..' segment refused: $path" }
    $full = [IO.Path]::GetFullPath($path)
    if (-not $full.StartsWith($GuardRoot + '\', [StringComparison]::OrdinalIgnoreCase)) {
        throw "containment: $full is outside $GuardRoot"
    }
    $parts = $full.Split('\')
    $probe = $parts[0] + '\'
    for ($i = 1; $i -lt $parts.Length; $i++) {
        $probe = if ($i -eq 1) { $probe + $parts[$i] } else { $probe + '\' + $parts[$i] }
        if (-not (Test-GuardExists $probe)) { break }   # nothing below a missing component exists yet
        try { $attrs = Get-GuardAttributes $probe } catch { throw "containment: cannot inspect $probe ($($_.Exception.Message))" }
        if ($null -eq $attrs) { throw "containment: cannot inspect $probe" }
        if ($attrs -band [IO.FileAttributes]::ReparsePoint) { throw "containment: $probe is a junction or link" }
    }
    return $full
}

function Invoke-GuardOp([string]$op, [string]$full, $value) {
    switch ($op) {
        'mkdir'  { [void](New-Item -ItemType Directory -Force -Path $full) }
        'write'  { Set-Content -LiteralPath $full -Value $value -Encoding UTF8 }
        'append' { Add-Content -LiteralPath $full -Value $value }
        'remove' { Remove-Item -LiteralPath $full }          # one entry, never recursive
        default  { throw "guard: unknown operation $op" }
    }
}

function Guard-Op([string]$op, [string]$path, $value = $null) {
    $full = Assert-Inside $path
    Invoke-GuardOp $op $full $value
    return $full
}
