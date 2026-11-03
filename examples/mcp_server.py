"""Separate demonstration MCP server; no model API or network required."""
import datetime
import json
import sys

for line in sys.stdin:
    req = json.loads(line)
    if 'id' not in req:
        continue
    method = req['method']
    if method == 'initialize':
        result = {'protocolVersion': '2024-11-05', 'capabilities': {'tools': {}},
                  'serverInfo': {'name': 'class-clock', 'version': '1.0'}}
    elif method == 'tools/list':
        result = {'tools': [{'name': 'current_time', 'description': '查询当前 UTC 时间，回答当前时间时使用。',
                            'inputSchema': {'type': 'object', 'properties': {}}}]}
    elif method == 'tools/call' and req['params']['name'] == 'current_time':
        result = {'content': [{'type': 'text', 'text': datetime.datetime.now(datetime.timezone.utc).isoformat()}]}
    else:
        print(json.dumps({'jsonrpc': '2.0', 'id': req['id'], 'error': {'code': -32601, 'message': 'Unknown method or tool'}}), flush=True)
        continue
    print(json.dumps({'jsonrpc': '2.0', 'id': req['id'], 'result': result}), flush=True)
