. 'E:/AI/Projects/OpenMinds/Minions/Minion-Agent/.agents/project-environment.ps1'
$minionRoot='E:/AI/Projects/OpenMinds/Minions/Minion-Agent'
$minionPermissionScript="$minionRoot/.tmp/wp142-rust/permission-linux.sh"
$minionPermissionContent=[IO.File]::ReadAllText($minionPermissionScript).Replace("`r`n", "`n")
[IO.File]::WriteAllText($minionPermissionScript, $minionPermissionContent, (New-Object Text.UTF8Encoding $false))
docker run --rm --read-only --tmpfs /tmp:rw,exec,size=1g --mount "type=bind,source=$minionRoot/.tmp/cache/cargo-target/linux,target=/target,readonly" --mount "type=bind,source=$minionRoot/.tmp/wp142-rust/logs-linux,target=/logs" --mount "type=bind,source=$minionRoot/.toolchain/icu-78.3-linux,target=/icu,readonly" --mount "type=bind,source=$minionPermissionScript,target=/run/permission.sh,readonly" rust:1.97.1-trixie sh /run/permission.sh
exit $LASTEXITCODE
