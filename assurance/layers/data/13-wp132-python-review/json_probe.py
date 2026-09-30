import asyncio
import json
from tests.conformance import builtin_mutation_runner as runner
from minion_agent.tools.builtin.edit import prepare_edit_arguments

async def main():
    text = '{"oldText":"alpha","newText":"A","extra":'+('9'*5000)+'}'
    prepared = prepare_edit_arguments({'path':'f.txt','edits':text})
    print('5000-digit valid JSON: prepared edits type',type(prepared['edits']).__name__)
    doc={'builtin_mutation':{'fixture':[{'path':'f.txt','file':{'text':'alpha\n'}}],
        'cases':[{'id':'huge-json-integer-extra','tool':'edit','arguments':{'path':'f.txt','edits':text},
        'expect':{'is_error':False,'text':'Successfully replaced 1 block(s) in f.txt.','files_after':[{'path':'f.txt','text':'A\n'}]}}]}}
    outcome=(await runner.run_cases(doc))[0]['observed']
    print(json.dumps({'is_error':outcome['is_error'],'text_prefix':outcome['text'][:120],'fs_calls':outcome['fs_calls'],'files_after':outcome['files_after']}))
    small=prepare_edit_arguments({'path':'f.txt','edits':'{"oldText":"alpha","newText":"A","extra":9007199254740993}'})
    print('IEEE-754 extra field',small['edits'][0]['extra'])

asyncio.run(main())
