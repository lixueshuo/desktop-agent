from pathlib import Path
import tempfile
import unittest
from desktop import FileApi


class EditorTests(unittest.TestCase):
    def test_edit_save_and_conflict(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'demo.py'
            p.write_text('value = 1\n',encoding='utf-8')
            api=FileApi(folder)
            data=api.editor_read('demo.py')
            saved=api.save_file('demo.py','value = 2\n',data['revision'])
            self.assertIn('revision',saved)
            self.assertEqual(p.read_text(),'value = 2\n')
            self.assertIn('error',api.save_file('demo.py','value = 3\n',data['revision']))
            self.assertEqual(p.read_text(),'value = 2\n')

    def test_busy_and_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            api=FileApi(folder)
            self.assertIn('error',api.editor_read('../outside.py'))
            api._busy=True
            self.assertIn('error',api.save_file('demo.py','x','anything'))
