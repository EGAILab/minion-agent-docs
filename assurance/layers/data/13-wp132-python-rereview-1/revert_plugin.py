import json
import subprocess


def pytest_configure(config):
    from tests.conformance import builtin_mutation_runner as runner
    from minion_agent.tools.builtin import edit, write, _utf16

    def old_json_parse(text):
        return json.loads(text, parse_constant=edit._reject_constant)

    edit._json_parse = old_json_parse

    def old_encode(text):
        return _utf16._LONE_SURROGATE.sub(chr(0xFFFD), text).encode('utf-8')

    _utf16.encode_utf8 = old_encode
    write.encode_utf8 = old_encode
    old_source = subprocess.check_output([
        'git', 'show', 'd81872a07b1ff83914f973e945b1469badf9f8f4:minion-agent-python/tests/conformance/builtin_mutation_runner.py',
    ], text=True, encoding='utf-8')
    start = old_source.index('async def _quiesce(')
    end = old_source.index('async def run_queue(', start)
    runner._SETTLE_S = 0.05
    exec(compile(old_source[start:end], 'old_quiesce', 'exec'), runner.__dict__)
