import json
from pathlib import Path
import tempfile
import threading
import unittest
from agent.tools import Tools
from agent.runtime import run


class BackendTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.tools = Tools(self.root)

    def test_pagination(self):
        self.tools.write('a.txt', 'one\ntwo\nthree\n')
        result = self.tools.read('a.txt', offset=2, limit=1)
        self.assertEqual(result['text'], '2: two')
        self.assertEqual(result['remaining_lines'], 1)

    def test_edit_failure_does_not_modify_file(self):
        self.tools.write('nested/a.txt', 'abc abc')
        with self.assertRaisesRegex(ValueError, '2'):
            self.tools.edit('nested/a.txt', 'abc', 'xyz')
        self.assertEqual((self.root/'nested/a.txt').read_text(), 'abc abc')
        with self.assertRaises(ValueError):
            self.tools.edit('nested/a.txt', 'missing', 'x')

    def test_exact_edit_preserves_crlf(self):
        self.tools.write('a.txt', 'first\r\nsecond\r\n')
        self.tools.edit('a.txt', 'second', 'changed')
        self.assertEqual((self.root/'a.txt').read_bytes(), b'first\r\nchanged\r\n')

    def test_missing_file_error_is_actionable(self):
        for name, args in [('read', {'path': 'missing.txt'}),
                           ('edit', {'path': 'missing.txt', 'old': 'a', 'new': 'b'})]:
            with self.subTest(tool=name):
                with self.assertRaisesRegex(ValueError, '文件不存在：missing.txt'):
                    self.tools.call(name, args)
                self.assertFalse((self.root/'missing.txt').exists())

    def test_directory_is_not_treated_as_file(self):
        (self.root/'folder').mkdir()
        for name, args in [('read', {'path': 'folder'}),
                           ('edit', {'path': 'folder', 'old': 'a', 'new': 'b'})]:
            with self.subTest(tool=name):
                with self.assertRaisesRegex(ValueError, '这是目录'):
                    self.tools.call(name, args)
        self.assertTrue((self.root/'folder').is_dir())

    def test_invalid_encoding_preserves_original_bytes(self):
        original = b'\xff\xfe\x00\x80'
        (self.root/'binary.dat').write_bytes(original)
        for name, args in [('read', {'path': 'binary.dat'}),
                           ('edit', {'path': 'binary.dat', 'old': 'a', 'new': 'b'})]:
            with self.subTest(tool=name):
                with self.assertRaisesRegex(ValueError, '请先确认文件编码或类型'):
                    self.tools.call(name, args)
                self.assertEqual((self.root/'binary.dat').read_bytes(), original)

    def test_traversal_and_secret_rejected(self):
        for path in ('../outside.txt', '.env', '.git/config', '.env.local'):
            with self.assertRaises(ValueError):
                self.tools.path(path)

    def test_nonzero_exit(self):
        result = self.tools.bash('Write-Output hello; exit 3')
        self.assertEqual(result['exit_code'], 3)
        self.assertIn('hello', result['stdout'])

    def test_timeout_and_truncation(self):
        result = self.tools.bash('Start-Sleep -Seconds 10', timeout=.3)
        self.assertEqual(result['reason'], 'timeout')
        result = self.tools.bash("Write-Output ('x' * 50000)")
        self.assertTrue(result['truncated'])
        self.assertLessEqual(len(result['stdout']), 16000)

    def test_cancel_running_command(self):
        timer = threading.Timer(.3, self.tools.cancel.set)
        timer.start()
        self.addCleanup(timer.cancel)
        result = self.tools.bash('Start-Sleep -Seconds 10')
        self.assertEqual(result['reason'], 'cancelled')

    def test_tool_error_is_returned_to_model_then_recovery(self):
        self.tools.write('a.txt', 'same same')
        replies = iter([
            {'role': 'assistant', 'content': None, 'tool_calls': [
                {'id': '1', 'type': 'function', 'function': {'name': 'edit',
                 'arguments': json.dumps({'path': 'a.txt', 'old': 'same', 'new': 'new'})}}]},
            {'role': 'assistant', 'content': '需要更多上下文'}])
        def model(messages):
            if len(messages) > 2:
                self.assertEqual(messages[-1]['tool_call_id'], '1')
                self.assertIn('error', messages[-1]['content'])
            return next(replies)
        events = list(run('修复', self.root, model=model))
        self.assertTrue(next(e for e in events if e['type'] == 'tool_result')['error'])
        self.assertEqual(events[-1]['type'], 'done')


if __name__ == '__main__':
    unittest.main()
