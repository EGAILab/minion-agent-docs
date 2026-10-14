$ErrorActionPreference='Stop'
. 'E:/AI/Projects/OpenMinds/Minions/Minion-Agent/.agents/project-environment.ps1'
. 'E:/AI/Projects/OpenMinds/Minions/Minion-Agent/.agents/gate-guard.ps1'
$root='E:/AI/Projects/OpenMinds/Minions/Minion-Agent'
$log=$root+'/.tmp/codex-scratch/l12d012-main-windows-build.jsonl'
$deadline=[DateTime]::UtcNow.AddMinutes(10)
while ([DateTime]::UtcNow -lt $deadline) {
    $lines=Get-Content -LiteralPath $log
    foreach ($line in $lines) {
        try {$j=$line | ConvertFrom-Json} catch {continue}
        if ($j.reason -eq 'compiler-artifact' -and $j.target.name -eq 'minion_agent' -and $j.profile.test -and $j.executable) {
            $dst=Assert-Inside ($root+'/.tmp/codex-scratch/l12d012-main-observer.exe')
            [IO.File]::Copy($j.executable,$dst,$false)
            Write-Output "CAPTURED main $($j.executable) -> $dst"
            exit 0
        }
    }
    Start-Sleep -Milliseconds 500
}
throw 'main artifact capture timed out'
