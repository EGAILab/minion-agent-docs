# Negative controls for gate-watchdog.ps1 -SelfTest (minion-agent#209 item 7). Each mutant must make the
# self-test FAIL, on the case that mutation breaks:
#   powershell -NoProfile -File <this dir>\gate-watchdog-controls.ps1
# It tests the gate-watchdog.ps1 next to this file. Mutants are written only to the literal directory
# .tmp\gate-logs\controls under the project root, and each removal targets the exact file just written.
$src = Join-Path $PSScriptRoot 'gate-watchdog.ps1'
$dir = 'E:\AI\Projects\OpenMinds\Minions\Minion-Agent\.tmp\gate-logs\controls'
[void](New-Item -ItemType Directory -Force -Path $dir)
$text = Get-Content -Raw -LiteralPath $src
$mutants = [ordered]@{
    'never-alerts' = @('elseif (((Get-Date) - $lastGrowth).TotalSeconds -ge $stall)', 'elseif ($false)')
    'ignores-growth' = @('if ($len -ne $lastLen) {', 'if ($false) {')
    'ignores-gate-end' = @("-Pattern '^GATE-END' -Quiet", "-Pattern '^NEVER-MATCHES' -Quiet")
    'missing-log-exit-0' = @('if ($len -lt 0) { "watchdog: launcher $watchPid ended and $log never appeared"; return 3 }', 'if ($len -lt 0) { return 0 }')
}
$killed = 0
foreach ($m in $mutants.Keys) {
    $old, $new = $mutants[$m]
    if (-not $text.Contains($old)) { "MUTANT ${m}: anchor not found (control invalid)"; continue }
    $path = Join-Path $dir "mutant-$m.ps1"
    Set-Content -LiteralPath $path -Value $text.Replace($old, $new) -Encoding UTF8
    $out = & powershell -NoProfile -File $path -SelfTest
    $rc = $LASTEXITCODE
    $verdict = if ($rc -ne 0) { $killed++; 'KILLED' } else { 'SURVIVED' }
    "MUTANT ${m}: $verdict (selftest exit $rc; $(($out | Select-String '^FAIL') -join ' | '))"
    Remove-Item -LiteralPath $path
}
"killed $killed / $($mutants.Count)"
if ($killed -ne $mutants.Count) { exit 1 }
exit 0
