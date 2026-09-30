import asyncio
import math
import tempfile
from pathlib import Path
from minion_agent.execution import LocalFileSystem
from minion_agent.llm import ToolCallBlock
from minion_agent.tools.builtin import create_edit_tool
from minion_agent.tools.events import TOOLS_PRE_EXECUTE
from minion_agent.tools.execute import execute_call
from minion_agent.tools.registry import ToolRegistry
from tests.conformance.builtin_mutation_runner import _context


async def main():
    with tempfile.TemporaryDirectory() as tmp:
        target=Path(tmp)/'f'
        target.write_text('a',encoding='utf-8')
        registry=ToolRegistry()
        registry.register(create_edit_tool(LocalFileSystem(tmp)))
        ctx=_context()

        async def observe(call,definition,arguments,signal,next_):
            extra=arguments['edits'][0]['extra']
            print('real Layer-06 hook extra',repr(extra),'isinf',math.isinf(extra))
            return await next_()

        ctx.events.on(TOOLS_PRE_EXECUTE,observe)
        edits='{"oldText":"a","newText":"b","extra":'+'9'*5000+'}'
        result=await execute_call(ToolCallBlock(id='overflow',name='edit',arguments={'path':'f','edits':edits}),registry=registry,ctx=ctx)
        print('is_error',result.is_error,'file',target.read_text(encoding='utf-8'))


asyncio.run(main())
