import asyncio
import time
from tests.conformance import builtin_mutation_runner as runner
from tests.tools.builtin.test_wp132_mutation_tools import _mutant, _scenario
from tests.conformance.test_builtin_mutation_conformance import check_queue
from minion_agent.tools.builtin import write as write_module
from minion_agent.tools.builtin import _signal

async def main():
    log = []
    async def later():
        await asyncio.sleep(0.3)
        log.append('timer progressed without any gate release')
    task = asyncio.create_task(later())
    start = time.monotonic()
    await runner._quiesce([],log)
    print('quiesce returned', round(time.monotonic()-start,3),'seconds; timer pending',not task.done())
    await task
    print('after quiesce:',log)
    doc = _scenario('builtin-mutation-queue-released-after-error-and-after-abort')
    mutant = _mutant(write_module,'text = await with_mutation_queue(fs, p, path, work)',
                     'text = await race_abort(with_mutation_queue(fs, p, path, work), signal)')
    mutant.race_abort = _signal.race_abort
    runner.create_write_tool = mutant.create_write_tool
    for interval in (0.01,0.5):
        _signal._POLL_INTERVAL_S = interval
        run = await runner.run_queue(doc)
        try:
            check_queue(run,doc['builtin_mutation']['queue']['expect'])
            result = 'PASS (mutant survived)'
        except AssertionError:
            result = 'FAIL (mutant killed)'
        print('same early-answer mutant, poll interval',interval,result)
        print(run['log'])

asyncio.run(main())
