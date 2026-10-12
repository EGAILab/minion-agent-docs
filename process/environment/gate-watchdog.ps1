# Gate stall watchdog (minion-agent#209 item 7). ALERT-ONLY: it never kills, stops or deletes anything.
#   powershell -NoProfile -File E:\AI\Projects\OpenMinds\Minions\Minion-Agent\.agents\gate-watchdog.ps1 `
#       -ProgressLog <launcher progress log> -WatchPid <launcher pid> [-StallSeconds 900] [-PollSeconds 30]
#   powershell -NoProfile -File ...\gate-watchdog.ps1 -SelfTest
# Convention (kit-shaped): the gate launcher writes its progress log at .tmp/gate-logs/<run-id>.log, appending
# while it works, and its last line is "GATE-END <exit code>". The watchdog reads only that file's length.
# Whenever the log has not grown for StallSeconds while the launcher is alive, it prints one
# "STALL ALERT" line, then repeats it every further StallSeconds without growth. Run it in the background
# (a Monitor), so an alert reaches the agent, who investigates and decides; nothing stops automatically.
# After a cache reset, a cold link of the heavy crates under 4 jobs can exceed 15 minutes, so the first
# alert after a reset is expected; the alert text says so.
# Exit: 0 when the launcher exits or GATE-END appears; 3 when the log never appears while the launcher lives
# for StallSeconds (after one alert, it keeps watching; it exits 3 only when the launcher ends without a log).
param(
    [string]$ProgressLog,
    [int]$WatchPid = 0,
    [int]$StallSeconds = 900,
    [int]$PollSeconds = 30,
    [switch]$SelfTest
)
$root = 'E:\AI\Projects\OpenMinds\Minions\Minion-Agent'

function Watch([string]$log, [int]$watchPid, [int]$stall, [int]$poll) {
    $lastLen = -1
    $lastGrowth = Get-Date
    $alerts = 0
    while ($true) {
        $alive = ($watchPid -eq 0) -or [bool](Get-Process -Id $watchPid -ErrorAction SilentlyContinue)
        $len = if (Test-Path -LiteralPath $log) { (Get-Item -LiteralPath $log).Length } else { -1 }
        if ($len -ge 0 -and (Select-String -LiteralPath $log -Pattern '^GATE-END' -Quiet)) {
            "watchdog: GATE-END seen in $log; exiting"
            return 0
        }
        if (-not $alive) {
            if ($len -lt 0) { "watchdog: launcher $watchPid ended and $log never appeared"; return 3 }
            "watchdog: launcher $watchPid ended; exiting"
            return 0
        }
        if ($len -ne $lastLen) {
            $lastLen = $len
            $lastGrowth = Get-Date
        } elseif (((Get-Date) - $lastGrowth).TotalSeconds -ge $stall) {
            $alerts++
            $what = if ($len -lt 0) { 'has not appeared' } else { "has not grown ($len bytes)" }
            "STALL ALERT #${alerts}: $log $what for $stall s while launcher $watchPid is alive. " +
                "Investigate (process tree, CPU, memory, lock holders); do not kill automatically. " +
                "The first alert after a cache reset is expected (cold link of the heavy crates)."
            $lastGrowth = Get-Date
        }
        Start-Sleep -Seconds $poll
    }
}

function Assert-Inside([string]$path) {
    # Lexical resolution, then the real path through any links, against the project root (fail closed).
    $full = [IO.Path]::GetFullPath($path)
    if (-not $full.StartsWith($root + '\', [StringComparison]::OrdinalIgnoreCase)) { throw "containment: $full is outside $root" }
    $probe = $full
    while ($probe.Length -gt $root.Length) {
        if (Test-Path -LiteralPath $probe) {
            $item = Get-Item -LiteralPath $probe -Force
            if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "containment: $probe is a link" }
        }
        $probe = [IO.Path]::GetDirectoryName($probe)
    }
    return $full
}

if ($SelfTest) {
    # Writes only inside .tmp/gate-logs/selftest-<pid>, each target checked before every write and the cleanup.
    $dir = Assert-Inside (Join-Path $root ".tmp\gate-logs\selftest-$PID")
    [void](New-Item -ItemType Directory -Force -Path $dir)
    $failed = 0
    $cases = @(
        @{ name = 'stall alerts'; grow = 2; stallAfter = $true; expectAlert = $true; expectExit = 0 },
        @{ name = 'growing log, no alert (control)'; grow = 10; stallAfter = $false; expectAlert = $false; expectExit = 0 },
        @{ name = 'GATE-END ends the watch'; grow = 2; stallAfter = $false; gateEnd = $true; expectAlert = $false; expectExit = 0 }
    )
    $i = 0
    foreach ($c in $cases) {
        $i++
        $log = Assert-Inside (Join-Path $dir "case$i.log")
        # Writer: appends one line per second for `grow` seconds, then idles (stall) or ends.
        $idle = if ($c.stallAfter) { 8 } else { 0 }
        $end = if ($c.gateEnd) { 'Add-Content -LiteralPath $l -Value ''GATE-END 0''; Start-Sleep 30' } else { '' }
        $script = "`$l = '$log'; for (`$k = 0; `$k -lt $($c.grow); `$k++) { Add-Content -LiteralPath `$l -Value `"line `$k`"; Start-Sleep 1 }; Start-Sleep $idle; $end"
        # -EncodedCommand: an argument list would split and unquote the script text.
        $encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($script))
        $writer = Start-Process powershell -ArgumentList '-NoProfile', '-EncodedCommand', $encoded -PassThru -WindowStyle Hidden
        $out = @(Watch $log $writer.Id 3 1)
        $code = $out[-1]
        $text = ($out | Select-Object -SkipLast 1) -join "`n"
        $alerted = $text -match 'STALL ALERT'
        $ok = ($alerted -eq $c.expectAlert) -and ($code -eq $c.expectExit)
        if (-not $ok) { $failed++ }
        "{0} {1}: alert={2} exit={3}" -f ($(if ($ok) { 'PASS' } else { 'FAIL' }), $c.name, $alerted, $code)
        if (-not $writer.HasExited) { $writer.WaitForExit(40000) | Out-Null }
    }
    # Missing log and launcher gone: exit 3.
    $gone = Start-Process powershell -ArgumentList '-NoProfile', '-Command', 'Start-Sleep 2' -PassThru -WindowStyle Hidden
    $missing = Assert-Inside (Join-Path $dir 'never.log')
    $out = @(Watch $missing $gone.Id 60 1)
    $ok = $out[-1] -eq 3
    if (-not $ok) { $failed++ }
    "{0} missing log, launcher ended: exit={1}" -f ($(if ($ok) { 'PASS' } else { 'FAIL' }), $out[-1])
    foreach ($f in Get-ChildItem -LiteralPath $dir -File) { Remove-Item -LiteralPath (Assert-Inside $f.FullName) }
    Remove-Item -LiteralPath (Assert-Inside $dir)
    if ($failed) { "SELFTEST FAILED ($failed)"; exit 1 } else { "SELFTEST PASSED"; exit 0 }
}

if (-not $ProgressLog) { "usage: -ProgressLog <path> -WatchPid <pid> [-StallSeconds 900] | -SelfTest"; exit 64 }
$code = Watch $ProgressLog $WatchPid $StallSeconds $PollSeconds | ForEach-Object { if ($_ -is [int]) { $rc = $_ } else { $_ } }
exit $rc
