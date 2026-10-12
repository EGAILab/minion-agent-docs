# Source before any build/test: keeps every temp and cache file on E: under the project root.
R=E:/AI/Projects/OpenMinds/Minions/Minion-Agent/.tmp
export TMP=$R/tmp TEMP=$R/tmp TMPDIR=$R/tmp
# Build decision 2026-10-12: the SAME cargo home and Windows target as .agents/project-environment.ps1, so
# every agent and worktree shares one dependency cache; at most 4 parallel rustc/link jobs.
export CARGO_HOME=$R/cache/cargo-home CARGO_TARGET_DIR=$R/cache/cargo-target/windows CARGO_BUILD_JOBS=4
export PIP_CACHE_DIR=$R/pip-cache UV_CACHE_DIR=$R/uv-cache npm_config_cache=$R/npm-cache
export PYTHONPYCACHEPREFIX=$R/pycache
export PATH="$HOME/.cargo/bin:$PATH"   # rustup proxies only; registry/git cache live in CARGO_HOME on E:
