# L12D004-R001: NUL neighbourhood on Linux -- main vs candidate (Python) vs pinned Pi (Node).
# Mounts: /src (candidate worktree), /main (origin/main archive), /probe (this directory), /node, /icu.
set -e
for tree in main candidate; do
  root=/main; [ "$tree" = candidate ] && root=/src
  rm -rf /work/$tree && mkdir -p /work/$tree && cp -r $root/minion-agent-python /work/$tree/
done
pip install -q --root-user-action=ignore "pydantic>=2.7" "pyyaml>=6.0" "jsonschema>=4.22" "httpx>=0.27" "url-py>=2026.5.1" "ada-url==1.15.3" "wasmtime==49.0.0" "PyICU==2.16.2" >/dev/null 2>&1
export PATH=/node/bin:$PATH
BASE=/tmp/rp/base; mkdir -p $BASE
python /probe/fixture.py $BASE > /tmp/rp/cases.json
for tree in main candidate; do
  PYTHONPATH=/work/$tree/minion-agent-python/src python /probe/probe_nul.py $BASE /probe/cases-nul.json /out/nul-$tree.json
done
node --experimental-strip-types --no-warnings /probe/probe_node.mjs $BASE /probe/cases-nul.json /out/nul-node.json
