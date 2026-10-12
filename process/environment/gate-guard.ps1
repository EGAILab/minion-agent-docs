# Containment guard for the gate tooling's own writes (minion-agent#209, TOOL209-R001). Dot-source it:
#   . (Join-Path $PSScriptRoot 'gate-guard.ps1')
# Every create, write, append or delete goes through Guard-Op. Guard-Op proves containment IMMEDIATELY
# before that one operation, and nothing runs when the proof fails (fail closed):
#   1. form: refuse empty paths, UNC/device paths (\\...), drive-relative forms (X:foo) and '..' segments;
#   2. lexical: the full path must lie strictly below the project root;
#   3. real path: every component from the drive root down to the target is inspected with a THROWING,
#      no-follow attribute read (GetFileAttributes does not follow links). Each result is classified:
#        plain    -> continue to the next component;
#        reparse  -> refuse (junction or link);
#        missing  -> only a FileNotFound / DirectoryNotFound error, for a component whose parent was just
#                    proven plain; nothing below it can exist yet, so the walk ends;
#        anything else (access denied, sharing or other I/O error, an empty result) -> refuse.
#      No error-suppressing boolean (File.Exists, Directory.Exists, Test-Path) is ever used as the proof.
# Get-GuardAttributes (inspection) and Invoke-GuardOp (the mutation) are the only seams; the guard
# self-test (gate-guard-selftest.ps1) overrides them to count mutation calls without touching disk.
$GuardRoot = 'E:\AI\Projects\OpenMinds\Minions\Minion-Agent'

function Get-GuardAttributes([string]$path) {
    return [IO.File]::GetAttributes($path)
}

function Test-GuardNotFound($err) {
    # True only when the error, or an exception it wraps, is a not-found error.
    $e = $err.Exception
    while ($null -ne $e) {
        if ($e -is [IO.FileNotFoundException] -or $e -is [IO.DirectoryNotFoundException]) { return $true }
        $e = $e.InnerException
    }
    return $false
}

function Get-GuardState([string]$path) {
    try { $attrs = Get-GuardAttributes $path }
    catch {
        if (Test-GuardNotFound $_) { return 'missing' }
        throw "containment: cannot inspect $path ($($_.Exception.Message))"
    }
    if ($null -eq $attrs) { throw "containment: cannot inspect $path (no result)" }
    if ($attrs -band [IO.FileAttributes]::ReparsePoint) { return 'reparse' }
    return 'plain'
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
    $rootLen = ($GuardRoot.Split('\')).Length
    for ($i = 1; $i -lt $parts.Length; $i++) {
        $probe = if ($i -eq 1) { $probe + $parts[$i] } else { $probe + '\' + $parts[$i] }
        $state = Get-GuardState $probe
        if ($state -eq 'reparse') { throw "containment: $probe is a junction or link" }
        if ($state -eq 'missing') {
            # The project root and its ancestors must exist: a missing one is not a valid place to write.
            if ($i -lt $rootLen) { throw "containment: $probe (at or above the project root) does not exist" }
            break
        }
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
