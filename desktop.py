"""正式界面第一阶段：文件列表与只读预览。"""
from pathlib import Path
import sys
import os
import queue
import threading
from agent.runtime import run, DATA
from agent.tools import Tools

ROOT = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT / '.desktop-deps'))


class FileApi:
    def __init__(self, workspace=None):
        self.workspace = Path(workspace or ROOT / 'examples' / 'practice').resolve()
        self._events = queue.Queue()
        self._cancel = threading.Event()
        self._lock = threading.Lock()
        self._busy = False

    def start_task(self, task):
        if not isinstance(task, str) or not task.strip() or len(task) > 20000:
            return {'error': '请输入 1–20000 字符的任务'}
        with self._lock:
            if self._busy:
                return {'error': '已有任务运行，请等待结束'}
            self._busy = True
            self._cancel = threading.Event()
        def worker():
            try:
                for event in run(task, self.workspace, self._cancel):
                    self._events.put(event)
            except Exception as e:
                self._events.put({'type': 'error', 'text': str(e)})
            finally:
                with self._lock:
                    self._events.put({'type': 'finished'})
                    self._busy = False
        threading.Thread(target=worker, daemon=True).start()
        return {'started': True}

    def poll_events(self):
        events = []
        for _ in range(100):
            try:
                events.append(self._events.get_nowait())
            except queue.Empty:
                break
        return events

    def cancel_task(self):
        self._cancel.set()
        return {'requested': True}

    def save_settings(self, key, model='deepseek-flash'):
        if not isinstance(key, str) or not key.strip() or '\n' in key or '\r' in key:
            return {'error': '请填写有效密钥'}
        if not isinstance(model, str) or not model.strip() or any(c in model for c in '\r\n'):
            return {'error': '模型名称无效'}
        from agent.tools import Tools
        Tools(DATA)._save(DATA / '.env', 'DEEPSEEK_API_KEY=' + key.strip() + '\nDEEPSEEK_BASE_URL=https://api.deepseek.com\nDEEPSEEK_MODEL=' + model.strip() + '\n')
        return {'saved': True}

    def choose_workspace(self):
        with self._lock:
            if self._busy:
                return {'error': '请先结束当前任务'}
            import webview
            selected = webview.windows[0].create_file_dialog(webview.FOLDER_DIALOG)
            if selected:
                self.workspace = Path(selected[0]).resolve()
        return self.files()

    def files(self):
        items = []
        def visit(folder, depth=0):
            if depth > 5 or len(items) >= 300:
                return
            for p in sorted(folder.iterdir(), key=lambda p: p.name.lower()):
                if len(items) >= 300:
                    return
                if p.is_symlink() or p.name.startswith('.') or p.name in {'__pycache__', 'node_modules', 'dist', 'build'}:
                    continue
                if p.is_dir():
                    visit(p, depth + 1)
                elif p.is_file():
                    items.append(p.relative_to(self.workspace).as_posix())
        visit(self.workspace)
        return {'workspace': str(self.workspace), 'files': items}

    def read(self, path):
        try:
            result = Tools(self.workspace).read(path, limit=500)
            return result if isinstance(result, dict) else {'text': '图片预览尚未接入'}
        except Exception as e:
            return {'error': str(e)}


if __name__ == '__main__':
    if '--mcp-server' in sys.argv:
        import os
        if sys.stdin is None:
            sys.stdin = os.fdopen(0, 'r', encoding='utf-8')
        if sys.stdout is None:
            sys.stdout = os.fdopen(1, 'w', encoding='utf-8')
        import runpy
        runpy.run_path(str(ROOT / 'examples' / 'mcp_server.py'), run_name='__main__')
        raise SystemExit(0)
    try:
        # Software rendering also works in remote desktops and screen recordings.
        os.environ.setdefault('WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS', '--disable-gpu')
        import webview
    except ImportError:
        raise SystemExit('请先安装依赖：python -m pip install --target .desktop-deps pywebview')
    webview.create_window('Desktop Agent',
                          html=(ROOT / 'ui' / 'index.html').read_text(encoding='utf-8'), js_api=FileApi(), width=1200, height=800)
    webview.start()
