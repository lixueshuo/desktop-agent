import json
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from agent.runtime import run

TOKEN = secrets.token_urlsafe(32)
active = {}
lock = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        if self.headers.get('Authorization') != 'Bearer ' + TOKEN:
            self.send_error(401)
            return
        if self.headers.get('Origin'):
            self.send_error(403)
            return
        try:
            size = int(self.headers.get('Content-Length', 0))
            if not 0 < size <= 100000:
                raise ValueError('请求过大或为空')
            data = json.loads(self.rfile.read(size))
            if self.path == '/cancel':
                with lock:
                    for event in active.values():
                        event.set()
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'{"cancel_requested":true}')
                return
            if self.path != '/run':
                self.send_error(404)
                return
            task, workspace = data['task'], data['workspace']
            if not isinstance(task, str) or not task.strip():
                raise ValueError('task 不能为空')
            cancel = threading.Event()
            with lock:
                if active:
                    self.send_error(409, 'Already running')
                    return
                active[1] = cancel
        except (ValueError, KeyError):
            self.send_error(400)
            return
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream; charset=utf-8')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        def emit(event):
            self.wfile.write(('data: ' + json.dumps(event, ensure_ascii=False) + '\n\n').encode())
            self.wfile.flush()
        try:
            for event in run(task, workspace, cancel):
                emit(event)
        except (BrokenPipeError, ConnectionResetError):
            cancel.set()
        except Exception as e:
            try:
                emit({'type': 'error', 'text': str(e)})
            except OSError:
                pass
        finally:
            with lock:
                active.pop(1, None)


if __name__ == '__main__':
    server = ThreadingHTTPServer(('127.0.0.1', 8765), Handler)
    print('后端：http://127.0.0.1:8765', flush=True)
    print('本次本地访问令牌（不是模型 Key）：' + TOKEN, flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        with lock:
            for event in active.values():
                event.set()
        server.server_close()
