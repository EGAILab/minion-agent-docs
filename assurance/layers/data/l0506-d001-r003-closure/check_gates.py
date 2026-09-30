"""Read-only R003 gate and semantic-delta verification."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import yaml
from jsonschema import Draft202012Validator

code=Path(sys.argv[1])
old='23344258c02b8d2868b756ed395b18769b2af092'
schema_path='conformance/schema/prepared-runtime-scenario.schema.json'
schema=json.loads((code/schema_path).read_text())
previous=json.loads(subprocess.check_output(['git','-C',str(code),'show',f'{old}:{schema_path}']))
reduced=copy.deepcopy(schema)
reduced['required'].remove('gate')
reduced['properties'].pop('gate')
reduced.pop('allOf')
reduced.pop('$comment')
previous.pop('$comment')
assert reduced==previous,'Unexpected schema semantic delta beyond gate rules/comment'
print('Schema semantic change limited to gate requirement/property/allOf/comment')
documents=[]
for path in sorted((code/'conformance/agent/prepared-runtime').glob('*.yaml')):
    doc=yaml.safe_load(path.read_text())
    old_doc=yaml.safe_load(subprocess.check_output(['git','-C',str(code),'show',f'{old}:conformance/agent/prepared-runtime/{path.name}']))
    assert doc['prepared_runtime']==old_doc['prepared_runtime']
    documents.append(doc)
delta=[d for d in documents if d['gate']=='L0506-D001']
integration=[d for d in documents if d['gate']=='WP-13.2']
assert len(delta)==3 and sum(len(d['prepared_runtime']['cases']) for d in delta)==19
assert all(c['tool']=='custom' for d in delta for c in d['prepared_runtime']['cases'])
assert len(integration)==1 and len(integration[0]['prepared_runtime']['cases'])==8
assert all(c['tool']=='edit' for c in integration[0]['prepared_runtime']['cases'])
validator=Draft202012Validator(schema)
for doc in documents:
    assert not list(validator.iter_errors(doc))
for name,doc in [('missing gate',copy.deepcopy(delta[0])),('edit in delta',copy.deepcopy(integration[0]))]:
    if name=='missing gate':
        doc.pop('gate')
    else:
        doc['gate']='L0506-D001'
    assert list(validator.iter_errors(doc)),name
    print(name,'REJECTED')
    if name=='edit in delta':
        mutant=copy.deepcopy(schema)
        mutant.pop('allOf')
        assert not list(Draft202012Validator(mutant).iter_errors(doc))
        print('Negative control: removing gate allOf accepts moved edit; original rejects it')
print('Delta selection: 3 documents / 19 custom cases; WP-13.2 selection: 1 document / 8 real edit cases')
print('All case inputs/expectations unchanged; deferred edit cases NOT counted as delta execution')
