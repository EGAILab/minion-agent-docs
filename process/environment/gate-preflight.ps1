# Gate preflight (build decision 2026-10-12). Read-only: it never kills, deletes or changes anything.
#   powershell -NoProfile -File E:\AI\Projects\OpenMinds\Minions\Minion-Agent\.agents\gate-preflight.ps1 [-MinFreeGB 16] [-MaxWaitMinutes 30] [-Sizes]
# 1. Waits until at least MinFreeGB of physical memory is free (the emulator, Minion-Memory batches and
#    other builds are the Owner's or another agent's: wait, never stop them). Exit 2 if it never frees up.
# 2. Reports running cargo/rustc/docker processes (another agent's build; cargo's lock will queue yours).
# 3. Reports E: free space (clean trigger under 300 GB); with -Sizes, the shared cargo targets (report over
#    150 GB, clean trigger over 250 GB). It only REPORTS:
#    cleanup is a destructive operation on a computed path, done separately through the containment
#    helper, and never while another agent may hold cargo's lock.
param([int]$MinFreeGB = 16, [int]$MaxWaitMinutes = 30, [switch]$Sizes)
$root = 'E:\AI\Projects\OpenMinds\Minions\Minion-Agent'
function FreeGB { [math]::Round((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1MB, 1) }

$deadline = (Get-Date).AddMinutes($MaxWaitMinutes)
$free = FreeGB
while ($free -lt $MinFreeGB) {
    if ((Get-Date) -gt $deadline) {
        "PREFLIGHT FAIL: only $free GB free after $MaxWaitMinutes min (need $MinFreeGB). Ask the Owner; do not stop their processes."
        exit 2
    }
    "waiting: $free GB free, need $MinFreeGB"
    Start-Sleep -Seconds 30
    $free = FreeGB
}
"memory: $free GB free (need $MinFreeGB) OK"

$busy = Get-CimInstance Win32_Process -Filter "Name='cargo.exe' OR Name='rustc.exe' OR Name='docker.exe'" |
    Where-Object { $_.CommandLine -notmatch 'conda-script' }
if ($busy) {
    "active builds (another agent?):"
    $busy | ForEach-Object { "  $($_.ProcessId) $($_.Name) $($_.CommandLine.Substring(0, [Math]::Min(90, $_.CommandLine.Length)))" }
} else { "active builds: none" }

# Owner-decided thresholds (#209, 2026-10-12): report a target over 150 GB; clean (once, in a coordinated
# window, stale-worktree artifacts first) when E: has under 300 GB free or a target exceeds 250 GB.
$diskFreeGB = [math]::Round((Get-PSDrive E).Free / 1GB)
if ($diskFreeGB -lt 300) { "disk E: $diskFreeGB GB free -- UNDER 300 GB: CLEAN TRIGGER, report to the coordinator" }
else { "disk E: $diskFreeGB GB free (ok)" }

if ($Sizes) {
    foreach ($t in 'windows', 'linux') {
        $p = Join-Path $root ".tmp\cache\cargo-target\$t"
        if (Test-Path $p) {
            $gb = [math]::Round(((Get-ChildItem $p -Recurse -File -Force -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum) / 1GB, 1)
            $flag = if ($gb -gt 250) { 'OVER 250 GB: CLEAN TRIGGER, report to the coordinator; clean only via the containment helper' }
                elseif ($gb -gt 150) { 'over 150 GB: report' } else { 'ok' }
            "target ${t}: $gb GB ($flag)"
        }
    }
}
exit 0
