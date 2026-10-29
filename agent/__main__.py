import argparse
import json
from .runtime import run

parser = argparse.ArgumentParser(description='Desktop Agent 后端，逐行输出 JSON 事件')
parser.add_argument('task')
parser.add_argument('--workspace', required=True)
args = parser.parse_args()
try:
    for event in run(args.task, args.workspace):
        print(json.dumps(event, ensure_ascii=False), flush=True)
except Exception as e:
    print(json.dumps({'type': 'error', 'text': str(e)}, ensure_ascii=False), flush=True)
    raise SystemExit(1)
