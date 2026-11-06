from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from desktop import FileApi


class SettingsTests(unittest.TestCase):
    def test_local_save_does_not_return_key(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch('desktop.DATA', Path(folder)):
                api = FileApi(folder)
                result = api.save_settings('fake-local-key')
                self.assertEqual(result, {'saved': True})
                self.assertIn('DEEPSEEK_API_KEY=fake-local-key', (Path(folder)/'.env').read_text())

    def test_newline_injection_rejected_without_writing(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch('desktop.DATA', Path(folder)):
                api = FileApi(folder)
                self.assertIn('error', api.save_settings('fake\nEXTRA=value'))
                self.assertIn('error', api.save_settings('fake', 'model\nEXTRA=value'))
                self.assertFalse((Path(folder)/'.env').exists())
