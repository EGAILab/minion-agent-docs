import asyncio
import math
import tempfile
from pathlib import Path
from minion_agent.tools.builtin.edit import prepare_edit_arguments
from minion_agent.execution import LocalFileSystem
from minion_agent.llm import ToolCallBlock
from minion_agent.tools.builtin import create_edit_tool
from minion_agent.tools.events import TOOLS_PRE_EXECUTE
from minion_agent.tools.execute import execute_call
from minion_agent.tools.registry import ToolRegistry
from tests.conformance.builtin_mutation_runner import _context

for token in ('-0', '-0.0', '-0e0'):
    arguments = {'path': 'f', 'edits': '{"oldText":"a","newText":"b","extra":' + token + '}'}
    value = prepare_edit_arguments(arguments)['edits'][0]['extra']
    print(token, type(value).__name__, repr(value), 'sign', math.copysign(1.0, value))


async def pipeline():
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / 'f'
        target.write_text('a', encoding='utf-8')
        registry = ToolRegistry()
        registry.register(create_edit_tool(LocalFileSystem(tmp)))
        ctx = _context()

        async def inspect_prepared(call, definition, arguments, signal, next_):
            value = arguments['edits'][0]['extra']
            print('real Layer-06 hook sign', math.copysign(1.0, value))
            return await next_()

        ctx.events.on(TOOLS_PRE_EXECUTE, inspect_prepared)
        result = await execute_call(
            ToolCallBlock(id='negative-zero', name='edit', arguments={
                'path': 'f', 'edits': '{"oldText":"a","newText":"b","extra":-0}',
            }), registry=registry, ctx=ctx,
        )
        print('pipeline is_error', result.is_error, 'file', target.read_text(encoding='utf-8'))


asyncio.run(pipeline())
