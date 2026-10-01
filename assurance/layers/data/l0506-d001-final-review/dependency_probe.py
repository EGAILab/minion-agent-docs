"""Read-only proof of the candidate's eight real-edit dependencies and absent baseline tool."""
import json
from pathlib import Path
import subprocess
import sys
import yaml

code, docs = map(Path, sys.argv[1:])
files=subprocess.check_output(['git','-C',str(code),'ls-tree','-r','--name-only','HEAD'],text=True).splitlines()
for path in ['minion-agent-python/src/minion_agent/tools/builtin/edit.py', 'minion-agent-rust/crates/minion-agent/src/tools/builtin/edit.rs']:
    print(path, 'PRESENT' if path in files else 'ABSENT')
cases=[]
for path in (code/'conformance/agent/prepared-runtime').glob('*.yaml'):
    cases.extend(yaml.safe_load(path.read_text(encoding='utf-8'))['prepared_runtime']['cases'])
print('real edit cases:',sum(c['tool']=='edit' for c in cases))
print('custom lower-layer cases:',sum(c['tool']=='custom' for c in cases))
schema=json.loads((code/'conformance/schema/prepared-runtime-scenario.schema.json').read_text())
print('edit fixture rule:',schema['$defs']['editCase']['$comment'])
issue=json.loads(subprocess.check_output(['gh','api','repos/EGAILab/minion-agent/issues/49'],text=True,encoding='utf-8'))
import re
w=yaml.safe_load(re.search(r'```yaml\s*\n(.*?)\n```',issue['body'],re.S).group(1))['workflow']
print('WP-13.2 current next_action:',w['next_action'])
print('WP-13.2 delta dependency:',w['dependencies']['L0506-D001'])
