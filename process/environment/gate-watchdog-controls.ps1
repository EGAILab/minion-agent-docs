# Negative controls for the gate tooling self-tests: watchdog, containment guard and preflight memory
# decision (minion-agent#209 items 4 and 7; TOOL209-R001/R002/R003).
#   powershell -NoProfile -File <this dir>\gate-watchdog-controls.ps1                  # run the controls
#   powershell -NoProfile -File <this dir>\gate-watchdog-controls.ps1 -DriverSelfTest  # prove the driver's rules
# Rules (kit WORKFLOW.md section 9.7):
# - BASELINE first: each unmutated self-test must exit 0, print its pass marker and a PASS line for every one
#   of its cases. A baseline that is not green makes the whole run INVALID (exit 2); nothing is credited.
# - A mutant is KILLED only if its anchor was found, its source really changed, the self-test exited 1 with
#   its fail marker, EVERY intended case printed FAIL, and every other case printed PASS. Anything else is
#   INVALID, never a kill: setup, parse or usage errors (for example exit 64), missing cases, unrelated
#   failures, a wrong exit code, or a timeout.
# - Exit 0 only when the baseline is green and every mutant is KILLED; 1 when any mutant SURVIVED or is
#   INVALID; 2 when the baseline is invalid.
# Writes go only through gate-guard.ps1's Guard-Op, below .tmp\gate-logs\controls-<pid>, each checked
# immediately before it; cleanup removes exactly the files written. Nothing is killed: a timed-out child is
# reported INVALID and left to finish.
param([switch]$DriverSelfTest, [int]$TimeoutSeconds = 300)
. (Join-Path $PSScriptRoot 'gate-guard.ps1')

$targets = [ordered]@{
    watchdog = @{
        file = 'gate-watchdog.ps1'; args = @('-SelfTest'); pass = 'SELFTEST PASSED'; fail = 'SELFTEST FAILED'
        cases = @('stall alerts', 'growing log, no alert (control)', 'GATE-END ends the watch', 'missing log, launcher ended')
    }
    guard = @{
        file = 'gate-guard-selftest.ps1'; mutates = 'gate-guard.ps1'; args = @(); pass = 'GUARD SELFTEST PASSED'; fail = 'GUARD SELFTEST FAILED'
        cases = @('contained path, real inspection', 'contained path, simulated plain ancestors', 'outside path', 'project root itself',
            'sibling with root prefix', 'dot-dot escape', 'drive-relative', 'UNC', 'empty', 'junction ancestor (.tmp)',
            'junction above the root (Minions)', 'link at the target itself', 'inspection throws', 'inspection returns nothing')
    }
    preflight = @{
        file = 'gate-preflight.ps1'; args = @('-SelfTest'); pass = 'PREFLIGHT SELFTEST PASSED'; fail = 'PREFLIGHT SELFTEST FAILED'
        cases = @('15.96 GiB below 16', 'one KiB below 16 GiB', 'exactly 16 GiB', 'one KiB above 16 GiB', '30.5 GiB', 'zero')
    }
}
$mutants = @(
    @{ name = 'never-alerts'; target = 'watchdog'; intended = @('stall alerts')
       old = 'elseif (((Get-Date) - $lastGrowth).TotalSeconds -ge $stall)'; new = 'elseif ($false)' },
    @{ name = 'ignores-growth'; target = 'watchdog'; intended = @('growing log, no alert (control)')
       old = 'if ($len -ne $lastLen) {'; new = 'if ($false) {' },
    @{ name = 'ignores-gate-end'; target = 'watchdog'; intended = @('GATE-END ends the watch')
       old = "-Pattern '^GATE-END' -Quiet"; new = "-Pattern '^NEVER-MATCHES' -Quiet" },
    @{ name = 'missing-log-exit-0'; target = 'watchdog'; intended = @('missing log, launcher ended')
       old = 'if ($len -lt 0) { "watchdog: launcher $watchPid ended and $log never appeared"; return 3 }'; new = 'if ($len -lt 0) { return 0 }' },
    @{ name = 'guard-ignores-links'; target = 'guard'; intended = @('junction ancestor (.tmp)', 'junction above the root (Minions)', 'link at the target itself')
       old = 'if ($attrs -band [IO.FileAttributes]::ReparsePoint) { throw "containment: $probe is a junction or link" }'; new = '' },
    @{ name = 'guard-inspection-failure-passes'; target = 'guard'; intended = @('inspection throws')
       old = 'try { $attrs = Get-GuardAttributes $probe } catch { throw "containment: cannot inspect $probe ($($_.Exception.Message))" }'
       new = 'try { $attrs = Get-GuardAttributes $probe } catch { continue }' },
    @{ name = 'preflight-rounds-before-compare'; target = 'preflight'; intended = @('15.96 GiB below 16', 'one KiB below 16 GiB')
       old = 'return ([decimal]$freeKB * 1024) -ge ([decimal]$minGB * 1GB)'
       new = 'return [math]::Round([double]$freeKB * 1024 / 1GB, 1) -ge $minGB' }
)

function Invoke-Child([string]$path, [string[]]$childArgs, [string]$tag) {
    $job = Start-Job -ScriptBlock { param($p, $a) $o = & powershell -NoProfile -File $p @a 2>&1 | ForEach-Object { "$_" }; [pscustomobject]@{ code = $LASTEXITCODE; lines = $o } } -ArgumentList $path, $childArgs
    if (-not (Wait-Job $job -Timeout $TimeoutSeconds)) { return [pscustomobject]@{ code = $null; lines = @('TIMEOUT') } }
    $r = Receive-Job $job
    Remove-Job $job
    return $r
}

function Case-Verdicts($lines, [string[]]$cases) {
    $v = @{}
    foreach ($c in $cases) {
        $hits = @($lines | Where-Object { $_ -match ('^(PASS|FAIL) ' + [regex]::Escape($c) + ':') })
        $v[$c] = if ($hits.Count -eq 1) { $hits[0].Substring(0, 4) } else { 'MISSING' }
    }
    return $v
}

function Has-Marker($lines, [string]$marker) {
    # A marker line is the marker itself, optionally followed by " (detail)".
    return @($lines | Where-Object { $_ -match ('^' + [regex]::Escape($marker) + '( \(.*\))?$') }).Count -eq 1
}

function Run-Controls {
    $src = $PSScriptRoot
    $summary = [pscustomobject]@{ baseline = $true; killed = 0; survived = 0; invalid = 0; rc = 0 }
    foreach ($t in $targets.Keys) {
        $spec = $targets[$t]
        $r = Invoke-Child (Join-Path $src $spec.file) $spec.args "baseline:$t"
        $v = Case-Verdicts $r.lines $spec.cases
        $bad = @($spec.cases | Where-Object { $v[$_] -ne 'PASS' })
        $green = ($r.code -eq 0) -and (Has-Marker $r.lines $spec.pass) -and $bad.Count -eq 0
        "BASELINE ${t}: $(if ($green) { 'GREEN' } else { "INVALID (exit $($r.code); not passing: $($bad -join ', '))" })"
        if (-not $green) { $summary.baseline = $false }
    }
    if (-not $summary.baseline) { 'RESULT: INVALID baseline; no mutant credited'; $summary.rc = 2; return $summary }

    $work = Guard-Op 'mkdir' (Join-Path $GuardRoot ".tmp\gate-logs\controls-$PID")
    $written = @()
    foreach ($m in $mutants) {
        $spec = $targets[$m.target]
        $mutFile = if ($spec.mutates) { $spec.mutates } else { $spec.file }
        $text = Get-Content -Raw -LiteralPath (Join-Path $src $mutFile)
        if (-not $text.Contains($m.old)) { "MUTANT $($m.name): INVALID (anchor not found)"; $summary.invalid++; continue }
        $mutated = $text.Replace($m.old, $m.new)
        if ($mutated -eq $text) { "MUTANT $($m.name): INVALID (source unchanged)"; $summary.invalid++; continue }
        $mdir = Guard-Op 'mkdir' (Join-Path $work $m.name)
        foreach ($f in @('gate-guard.ps1', $spec.file) | Select-Object -Unique) {
            $content = if ($f -eq $mutFile) { $mutated } else { Get-Content -Raw -LiteralPath (Join-Path $src $f) }
            $written += Guard-Op 'write' (Join-Path $mdir $f) $content
        }
        $r = Invoke-Child (Join-Path $mdir $spec.file) $spec.args "mutant:$($m.name)"
        $v = Case-Verdicts $r.lines $spec.cases
        $intendedFail = @($m.intended | Where-Object { $v[$_] -eq 'FAIL' }).Count -eq $m.intended.Count
        $othersPass = @($spec.cases | Where-Object { $m.intended -notcontains $_ -and $v[$_] -ne 'PASS' }).Count -eq 0
        $verdict =
            if ($r.code -eq 1 -and (Has-Marker $r.lines $spec.fail) -and $intendedFail -and $othersPass) { 'KILLED' }
            elseif ($r.code -eq 0 -and (Has-Marker $r.lines $spec.pass)) { 'SURVIVED' }
            else { "INVALID (exit $($r.code); intended FAIL=$intendedFail; others PASS=$othersPass)" }
        "MUTANT $($m.name): $verdict"
        switch -Wildcard ($verdict) { 'KILLED' { $summary.killed++ } 'SURVIVED' { $summary.survived++ } default { $summary.invalid++ } }
    }
    foreach ($f in $written) { if (Test-Path -LiteralPath $f) { [void](Guard-Op 'remove' $f) } }
    foreach ($m in $mutants) { $d = Join-Path $work $m.name; if (Test-Path -LiteralPath $d) { [void](Guard-Op 'remove' $d) } }
    [void](Guard-Op 'remove' $work)
    "RESULT: killed $($summary.killed) / $($mutants.Count); survived $($summary.survived); invalid $($summary.invalid)"
    $summary.rc = if ($summary.killed -eq $mutants.Count) { 0 } else { 1 }
    return $summary
}

if ($DriverSelfTest) {
    # The driver's own rules, with a fake child and no disk writes (Invoke-GuardOp is a no-op counter).
    function Invoke-GuardOp([string]$op, [string]$full, $value) { }
    function Fake-Lines($spec, [string[]]$failing, [string[]]$omit, [string]$marker) {
        $l = @(foreach ($c in $spec.cases) { if ($omit -notcontains $c) { if ($failing -contains $c) { "FAIL ${c}: x" } else { "PASS ${c}: x" } } })
        return $l + $marker
    }
    $scenarios = @(
        @{ name = 'every child exits 64 with no witness'; expectRc = 2; expectKilled = 0
           child = { param($p, $a, $tag) [pscustomobject]@{ code = 64; lines = @('usage error') } } },
        @{ name = 'green baseline, mutants exit 64'; expectRc = 1; expectKilled = 0
           child = { param($p, $a, $tag) $s = $targets[$tag.Split(':')[1]]; if ($tag -like 'baseline:*') { [pscustomobject]@{ code = 0; lines = (Fake-Lines $s @() @() $s.pass) } } else { [pscustomobject]@{ code = 64; lines = @('setup error') } } } },
        @{ name = 'green baseline, mutants fail an unintended case'; expectRc = 1; expectKilled = 0
           child = { param($p, $a, $tag) if ($tag -like 'baseline:*') { $s = $targets[$tag.Split(':')[1]]; [pscustomobject]@{ code = 0; lines = (Fake-Lines $s @() @() $s.pass) } }
                     else { $m = $mutants | Where-Object { $_.name -eq $tag.Split(':')[1] }; $s = $targets[$m.target]; $wrong = @($s.cases | Where-Object { $m.intended -notcontains $_ })[0]; [pscustomobject]@{ code = 1; lines = (Fake-Lines $s @($wrong) @() $s.fail) } } } },
        @{ name = 'green baseline, intended FAIL but another case missing'; expectRc = 1; expectKilled = 0
           child = { param($p, $a, $tag) if ($tag -like 'baseline:*') { $s = $targets[$tag.Split(':')[1]]; [pscustomobject]@{ code = 0; lines = (Fake-Lines $s @() @() $s.pass) } }
                     else { $m = $mutants | Where-Object { $_.name -eq $tag.Split(':')[1] }; $s = $targets[$m.target]; $other = @($s.cases | Where-Object { $m.intended -notcontains $_ })[0]; [pscustomobject]@{ code = 1; lines = (Fake-Lines $s $m.intended @($other) $s.fail) } } } },
        @{ name = 'baseline missing a case'; expectRc = 2; expectKilled = 0
           child = { param($p, $a, $tag) $s = $targets[$tag.Split(':')[1]]; [pscustomobject]@{ code = 0; lines = (Fake-Lines $s @() @($s.cases[0]) $s.pass) } } },
        @{ name = 'timeout'; expectRc = 2; expectKilled = 0
           child = { param($p, $a, $tag) [pscustomobject]@{ code = $null; lines = @('TIMEOUT') } } },
        @{ name = 'positive: exactly the intended cases fail'; expectRc = 0; expectKilled = $mutants.Count
           child = { param($p, $a, $tag) if ($tag -like 'baseline:*') { $s = $targets[$tag.Split(':')[1]]; [pscustomobject]@{ code = 0; lines = (Fake-Lines $s @() @() $s.pass) } }
                     else { $m = $mutants | Where-Object { $_.name -eq $tag.Split(':')[1] }; $s = $targets[$m.target]; [pscustomobject]@{ code = 1; lines = (Fake-Lines $s $m.intended @() $s.fail) } } } }
    )
    $failed = 0
    foreach ($sc in $scenarios) {
        $script:childHook = $sc.child
        function Invoke-Child([string]$path, [string[]]$childArgs, [string]$tag) { & $script:childHook $path $childArgs $tag }
        $out = @(Run-Controls)
        $s = $out[-1]
        $ok = ($s.rc -eq $sc.expectRc) -and ($s.killed -eq $sc.expectKilled)
        if (-not $ok) { $failed++ }
        "{0} {1}: rc={2} killed={3}" -f ($(if ($ok) { 'PASS' } else { 'FAIL' }), $sc.name, $s.rc, $s.killed)
    }
    if ($failed) { "DRIVER SELFTEST FAILED ($failed)"; exit 1 } else { "DRIVER SELFTEST PASSED ($($scenarios.Count) scenarios)"; exit 0 }
}

$out = @(Run-Controls)
$out | Select-Object -SkipLast 1
exit $out[-1].rc
