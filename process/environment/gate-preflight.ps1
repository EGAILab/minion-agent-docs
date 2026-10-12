# Gate preflight (build decision 2026-10-12, minion-agent#209). Read-only: it never kills, deletes or changes anything.
#   powershell -NoProfile -File E:\AI\Projects\OpenMinds\Minions\Minion-Agent\.agents\gate-preflight.ps1 [-MinFreeGB 16] [-MaxWaitMinutes 30] [-Sizes]
#   powershell -NoProfile -File ...\gate-preflight.ps1 -SelfTest     # boundary tests of the memory decision
# 1. Waits until at least MinFreeGB (GiB: 1 GB = 2^30 bytes) of physical memory is free. The comparison uses
#    exact bytes; rounding is for display only and always rounds DOWN (TOOL209-R003). The emulator,
#    Minion-Memory batches and other builds are the Owner's or another agent's: wait, never stop them.
#    Exit 2 if memory never frees up within MaxWaitMinutes; a launcher must refuse to start the gate.
# 2. Reports running cargo/rustc/docker processes (another agent's build; cargo's lock will queue yours).
# 3. Reports E: free space against the 300 GB clean trigger; with -Sizes, the shared cargo targets against
#    150 GB (report) and 250 GB (clean trigger). It only REPORTS: cleanup is a separate, coordinated,
#    contained operation, never run while another agent may hold cargo's lock.
param([int]$MinFreeGB = 16, [int]$MaxWaitMinutes = 30, [switch]$Sizes, [switch]$SelfTest)
$root = 'E:\AI\Projects\OpenMinds\Minions\Minion-Agent'

function Test-MemoryEnough([double]$freeKB, [int]$minGB) {
    # Win32_OperatingSystem.FreePhysicalMemory is in KiB. Exact comparison in bytes; no rounding.
    return ([decimal]$freeKB * 1024) -ge ([decimal]$minGB * 1GB)
}

function Format-GBDown([double]$freeKB) {
    # Display only: two decimals, rounded down, so a value below the threshold never prints as the threshold.
    return [math]::Floor(([double]$freeKB * 1024 / 1GB) * 100) / 100
}

function FreeKB { [double](Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory }

if ($SelfTest) {
    $kib16 = 16 * 1MB   # 16 GiB in KiB
    $cases = @(
        @{ name = '15.96 GiB below 16'; kb = 15.96 * 1MB; expect = $false; display = '15.96' },
        @{ name = 'one KiB below 16 GiB'; kb = $kib16 - 1; expect = $false; display = '15.99' },
        @{ name = 'exactly 16 GiB'; kb = $kib16; expect = $true; display = '16' },
        @{ name = 'one KiB above 16 GiB'; kb = $kib16 + 1; expect = $true; display = '16' },
        @{ name = '30.5 GiB'; kb = 30.5 * 1MB; expect = $true; display = '30.5' },
        @{ name = 'zero'; kb = 0; expect = $false; display = '0' }
    )
    $failed = 0
    foreach ($c in $cases) {
        $got = Test-MemoryEnough $c.kb 16
        $shown = "$(Format-GBDown $c.kb)"
        $ok = ($got -eq $c.expect) -and ($shown -eq $c.display)
        if (-not $ok) { $failed++ }
        "{0} {1}: enough={2} display={3}" -f ($(if ($ok) { 'PASS' } else { 'FAIL' }), $c.name, $got, $shown)
    }
    if ($failed) { "PREFLIGHT SELFTEST FAILED ($failed)"; exit 1 } else { "PREFLIGHT SELFTEST PASSED ($($cases.Count) cases)"; exit 0 }
}

$deadline = (Get-Date).AddMinutes($MaxWaitMinutes)
$kb = FreeKB
while (-not (Test-MemoryEnough $kb $MinFreeGB)) {
    if ((Get-Date) -gt $deadline) {
        "PREFLIGHT FAIL: only $(Format-GBDown $kb) GB free after $MaxWaitMinutes min (need $MinFreeGB). Ask the Owner; do not stop their processes."
        exit 2
    }
    "waiting: $(Format-GBDown $kb) GB free, need $MinFreeGB"
    Start-Sleep -Seconds 30
    $kb = FreeKB
}
"memory: $(Format-GBDown $kb) GB free (need $MinFreeGB) OK"

$busy = Get-CimInstance Win32_Process -Filter "Name='cargo.exe' OR Name='rustc.exe' OR Name='docker.exe'" |
    Where-Object { $_.CommandLine -notmatch 'conda-script' }
if ($busy) {
    "active builds (another agent?):"
    $busy | ForEach-Object { "  $($_.ProcessId) $($_.Name) $($_.CommandLine.Substring(0, [Math]::Min(90, $_.CommandLine.Length)))" }
} else { "active builds: none" }

# Owner-decided thresholds (#209, 2026-10-12): report a target over 150 GB; clean (once, in a coordinated
# window, stale-worktree artifacts first) when E: has under 300 GB free or a target exceeds 250 GB.
$diskFreeGB = [math]::Floor((Get-PSDrive E).Free / 1GB)
if ($diskFreeGB -lt 300) { "disk E: $diskFreeGB GB free -- UNDER 300 GB: CLEAN TRIGGER, report to the coordinator" }
else { "disk E: $diskFreeGB GB free (ok)" }

if ($Sizes) {
    foreach ($t in 'windows', 'linux') {
        $p = Join-Path $root ".tmp\cache\cargo-target\$t"
        if (Test-Path $p) {
            $bytes = (Get-ChildItem $p -Recurse -File -Force -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
            $gb = [math]::Floor($bytes / 1GB * 10) / 10
            $flag = if ($bytes -gt 250GB) { 'OVER 250 GB: CLEAN TRIGGER, report to the coordinator; clean only via the containment helper' }
                elseif ($bytes -gt 150GB) { 'over 150 GB: report' } else { 'ok' }
            "target ${t}: $gb GB ($flag)"
        }
    }
}
exit 0
