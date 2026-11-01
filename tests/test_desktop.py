import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from desktop import FileApi


class DesktopBridgeTests(unittest.TestCase):
    def test_cancel_rejects_overlap_and_delivers_events(self):
        with tempfile.TemporaryDirectory() as folder:
            api = FileApi(folder)
            entered = threading.Event()
            def fake_run(task, workspace, cancel):
                entered.set()
                cancel.wait(2)
                yield {'type': 'cancelled'}
            with patch('desktop.run', fake_run):
                self.assertIn('error', api.start_task(''))
                self.assertTrue(api.start_task('测试')['started'])
                self.assertTrue(entered.wait(1))
                self.assertIn('error', api.start_task('重复任务'))
                api.cancel_task()
                events = []
                deadline = time.monotonic() + 3
                while time.monotonic() < deadline:
                    events.extend(api.poll_events())
                    if any(e['type'] == 'finished' for e in events):
                        break
                    time.sleep(.01)
                self.assertEqual([e['type'] for e in events], ['cancelled', 'finished'])

    def test_model_failure_releases_running_state(self):
        with tempfile.TemporaryDirectory() as folder:
            api = FileApi(folder)
            with patch('desktop.run', side_effect=RuntimeError('模拟模型失败')):
                api.start_task('测试')
                deadline = time.monotonic() + 3
                events = []
                while time.monotonic() < deadline:
                    events.extend(api.poll_events())
                    if any(e['type'] == 'finished' for e in events):
                        break
                    time.sleep(.01)
                self.assertEqual(events[0]['text'], '模拟模型失败')
                self.assertEqual(events[-1]['type'], 'finished')
