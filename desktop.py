"""正式界面第一阶段：文件列表与只读预览。"""
from pathlib import Path
import sys
from agent.tools import Tools

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / '.desktop-deps'))


class FileApi:
    def __init__(self, workspace=None):
        self.workspace = Path(workspace or ROOT / 'examples' / 'practice').resolve()

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
    try:
        import webview
    except ImportError:
        raise SystemExit('请先安装依赖：python -m pip install --target .desktop-deps pywebview')
    webview.create_window('Desktop Agent · 正式界面预览',
                          str(ROOT / 'ui' / 'index.html'), js_api=FileApi(), width=1200, height=800)
    webview.start()
