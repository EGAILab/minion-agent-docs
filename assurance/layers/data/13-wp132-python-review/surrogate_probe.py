import asyncio
import base64
import json
import yaml
from tests.conformance import builtin_mutation_runner as runner

async def main():
    content = yaml.safe_load('content: "\\uD83D\\uDE00"')['content']
    print('YAML valid paired surrogate representation:',[hex(ord(c)) for c in content])
    doc={'builtin_mutation':{'cases':[{'id':'valid-surrogate-pair','tool':'write','arguments':{'path':'f.txt','content':content},
        'expect':{'is_error':False,'text':'Successfully wrote 2 bytes to f.txt','files_after':[{'path':'f.txt','base64':'8J+YgA=='}]}}]}}
    out=(await runner.run_cases(doc))[0]['observed']
    print(json.dumps(out))
    print('expected UTF-8 hex f09f9880; actual',base64.b64decode(out['files_after'][0]['base64']).hex())

asyncio.run(main())
