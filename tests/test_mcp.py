from pathlib import Path
import sys
import unittest
from agent.mcp_client import McpClient


class McpTests(unittest.TestCase):
    def test_separate_server_discovery_and_call(self):
        path = Path(__file__).resolve().parents[1] / 'examples' / 'mcp_server.py'
        client = McpClient([sys.executable, str(path)])
        try:
            tools = client.request('tools/list', {})['tools']
            self.assertEqual(tools[0]['name'], 'current_time')
            result = client.request('tools/call', {'name': 'current_time', 'arguments': {}})
            self.assertIn('+00:00', result['content'][0]['text'])
        finally:
            client.close()
