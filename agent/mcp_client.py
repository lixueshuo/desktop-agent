"""Minimal stdio MCP client for local text tools."""
import json
import subprocess
import threading
import queue


class McpClient:
    def __init__(self, command):
        self.proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     text=True, encoding='utf-8',
                                     creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        self.responses = queue.Queue()
        self.seq = 0
        def reader():
            for line in self.proc.stdout:
                try:
                    self.responses.put(json.loads(line))
                except ValueError:
                    self.responses.put({'error': {'message': 'MCP stdout 含非法 JSON'}})
        threading.Thread(target=reader, daemon=True).start()
        try:
            self.request('initialize', {'protocolVersion': '2024-11-05',
                         'capabilities': {}, 'clientInfo': {'name': 'desktop-agent', 'version': '0.1'}})
            self.send({'jsonrpc': '2.0', 'method': 'notifications/initialized'})
        except Exception:
            self.close()
            raise

    def send(self, value):
        self.proc.stdin.write(json.dumps(value) + '\n')
        self.proc.stdin.flush()

    def request(self, method, params):
        self.seq += 1
        self.send({'jsonrpc': '2.0', 'id': self.seq, 'method': method, 'params': params})
        while True:
            try:
                response = self.responses.get(timeout=10)
            except queue.Empty:
                raise RuntimeError('MCP 请求超时') from None
            if 'error' in response:
                raise RuntimeError(str(response['error']))
            if response.get('id') == self.seq:
                return response['result']

    def close(self):
        if self.proc.poll() is None:
            self.proc.terminate()
            self.proc.wait(timeout=5)
        self.proc.stdin.close()
        self.proc.stdout.close()
