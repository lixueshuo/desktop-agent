import json
import tempfile
import unittest
from unittest.mock import patch
from agent.runtime import run


class CommandOptionTests(unittest.TestCase):
    def test_disabled_command_never_executes(self):
        replies=iter([
            {'role':'assistant','content':None,'tool_calls':[{'id':'one','type':'function',
             'function':{'name':'bash','arguments':json.dumps({'command':'unexpected-command'})}}]},
            {'role':'assistant','content':'已停止命令执行'}])
        with tempfile.TemporaryDirectory() as folder:
            with patch('agent.tools.Tools.bash') as shell:
                events=list(run('测试',folder,model=lambda m:next(replies),allow_commands=False))
                shell.assert_not_called()
                self.assertTrue(next(e for e in events if e['type']=='tool_result')['error'])
