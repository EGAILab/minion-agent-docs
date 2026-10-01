import copy
import hashlib
import json
from pathlib import Path
import sys
import subprocess
import yaml
from jsonschema import Draft202012Validator

code, docs, output, generated = map(Path, sys.argv[1:])
ev=docs/'assurance/layers/data/l0506-d001'
for name in ['authority.json']:
    data=(output/name).read_bytes()
    assert data==(ev/'out'/name).read_bytes()
    print(name,hashlib.sha256(data).hexdigest(),'byte-identical')
assert (output/'cases.sha256').read_bytes()==(ev/'cases.sha256').read_bytes()
for path in generated.glob('*.yaml'):
    blob=subprocess.check_output(['git','-C',str(code),'show',f'HEAD:conformance/agent/prepared-runtime/{path.name}'])
    assert path.read_bytes()==blob
print('4/4 scenario bytes identical')
validator=Draft202012Validator(json.loads((code/'conformance/schema/prepared-runtime-scenario.schema.json').read_text()))
base=yaml.safe_load((code/'conformance/agent/prepared-runtime/prepared-runtime-undeclared-field.yaml').read_text())
base['prepared_runtime']['cases']=base['prepared_runtime']['cases'][:1]
for label, mutate in [
    ('custom lacks schema',lambda c:c.pop('schema')),
    ('custom lacks prepare_set',lambda c:c.pop('prepare_set')),
    ('prepared lacks expected observations',lambda c:c['expect'].pop('observed')),
    ('invalid numeric token',lambda c:c['prepare_set'].update(extra='1garbage')),
]:
    document=copy.deepcopy(base)
    mutate(document['prepared_runtime']['cases'][0])
    errors=list(validator.iter_errors(document))
    print(label,'REJECTED' if errors else 'ACCEPTED')
