# Dot-source before project commands. Process-local only; no system/user settings.
$minionWorkspace = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
if ($minionWorkspace -ne 'E:\AI\Projects\OpenMinds\Minions\Minion-Agent') {
    throw "Unexpected workspace for project temp/cache setup: $minionWorkspace"
}
$minionCacheRoot = Join-Path $minionWorkspace '.tmp\cache'
$minionTempRoot = Join-Path $minionWorkspace '.tmp\process-temp'
$minionEnvironment = @{
    TEMP = $minionTempRoot
    TMP = $minionTempRoot
    TMPDIR = $minionTempRoot
    XDG_CACHE_HOME = (Join-Path $minionCacheRoot 'xdg')
    CARGO_HOME = (Join-Path $minionCacheRoot 'cargo-home')
    CARGO_TARGET_DIR = (Join-Path $minionCacheRoot 'cargo-target\windows')
    UV_CACHE_DIR = (Join-Path $minionCacheRoot 'uv')
    PIP_CACHE_DIR = (Join-Path $minionCacheRoot 'pip')
    npm_config_cache = (Join-Path $minionCacheRoot 'npm')
    NODE_COMPILE_CACHE = (Join-Path $minionCacheRoot 'node-compile')
    PYTHONPYCACHEPREFIX = (Join-Path $minionCacheRoot 'pycache')
    MYPY_CACHE_DIR = (Join-Path $minionCacheRoot 'mypy')
    RUFF_CACHE_DIR = (Join-Path $minionCacheRoot 'ruff')
}
foreach ($minionEntry in $minionEnvironment.GetEnumerator()) {
    [void](New-Item -ItemType Directory -Path $minionEntry.Value -Force)
    [Environment]::SetEnvironmentVariable($minionEntry.Key, $minionEntry.Value, 'Process')
}
