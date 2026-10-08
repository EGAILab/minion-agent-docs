set -e
mkdir -p /work && cp -r /src/minion-agent-python /work/ && cd /work/minion-agent-python && find . -name "*.sh" -exec sed -i "s/\r$//" {} +
eval "$(bash scripts/pinned-icu/build.sh /icu --env)"
pip install -q --root-user-action=ignore "pydantic>=2.7" "pyyaml>=6.0" "jsonschema>=4.22" "httpx>=0.27" "url-py>=2026.5.1" "ada-url==1.15.3" "wasmtime==49.0.0" "PyICU==2.16.2" >/dev/null 2>&1
export PATH=/node/bin:$PATH
BASE=/tmp/rp/base; mkdir -p $BASE
python /probe/fixture.py $BASE > /tmp/rp/cases.json
chmod 000 $BASE/noperm
chmod -R a+rwX /tmp/rp || true; chmod 000 $BASE/noperm
chmod a+rx /work /work/minion-agent-python
cd /work/minion-agent-python
su nobody -s /bin/sh -c "PYTHONPATH=src python /probe/probe_python.py $BASE /tmp/rp/cases.json /tmp/rp/python.json && node --experimental-strip-types --no-warnings /probe/probe_node.mjs $BASE /tmp/rp/cases.json /tmp/rp/node.json"
cp /tmp/rp/python.json /tmp/rp/node.json /out/
