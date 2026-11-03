import json
from pathlib import Path
import tempfile
import unittest
from agent.trace import Trace
from agent.runtime import run


class TraceTests(unittest.TestCase):
    def test_redaction_and_unique_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            a = Trace(directory, ['fake-secret'])
            b = Trace(directory)
            self.assertNotEqual(a.path, b.path)
            a.add({'text': 'contains fake-secret'})
            a.close()
            b.close()
            text = a.path.read_text(encoding='utf-8')
            self.assertNotIn('fake-secret', text)
            self.assertIn('[REDACTED]', json.loads(text)['event']['text'])

    def test_failed_model_record_is_labelled_as_test(self):
        with tempfile.TemporaryDirectory() as folder:
            def fail(messages):
                raise RuntimeError('simulated failure')
            with self.assertRaises(RuntimeError):
                list(run('test', folder, model=fail, trace_dir=Path(folder)/'records'))
            path = next((Path(folder)/'records').glob('*.jsonl'))
            rows = [json.loads(s)['event'] for s in path.read_text(encoding='utf-8').splitlines()]
            self.assertEqual(rows[0]['model_mode'], 'test-double')
            self.assertEqual(rows[-1]['text'], 'simulated failure')
