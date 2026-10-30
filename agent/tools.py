import base64
import difflib
import mimetypes
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import time


class Tools:
    def __init__(self, workspace, cancel=None):
        self.root = Path(workspace).resolve(strict=True)
        self.cancel = cancel or threading.Event()

    def path(self, path):
        p = (self.root / path).resolve()
        if not p.is_relative_to(self.root):
            raise ValueError('路径越界')
        if any(part in {'.git', '.env', '.ssh'} or part.startswith('.env.') and part != '.env.example'
               for part in p.relative_to(self.root).parts):
            raise ValueError('禁止读取或修改密钥、Git 内部文件')
        return p

    def read(self, path, offset=1, limit=200):
        p = self._existing_text_path(path)
        if type(offset) is not int or type(limit) is not int or offset < 1 or not 1 <= limit <= 500:
            raise ValueError('offset 从 1 开始，limit 范围 1–500')
        mime = mimetypes.guess_type(p.name)[0] or ''
        if mime in {'image/png', 'image/jpeg', 'image/webp', 'image/gif'}:
            if p.stat().st_size > 10_000_000:
                raise ValueError('图片超过 10MB')
            data = base64.b64encode(p.read_bytes()).decode()
            return [{'type': 'image_url', 'image_url': {'url': f'data:{mime};base64,{data}'}}]
        if p.stat().st_size > 10_000_000:
            raise ValueError('文本超过 10MB，请先用命令筛选')
        lines = self._read_text(p, path, encoding='utf-8-sig').splitlines()
        selected = lines[offset - 1:offset - 1 + limit]
        return {'path': path, 'total_lines': len(lines),
                'remaining_lines': max(0, len(lines) - (offset - 1 + len(selected))),
                'text': '\n'.join(f'{i}: {s}' for i, s in enumerate(selected, offset))}

    def _save(self, p, content):
        p.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(dir=p.parent, prefix='.agent-')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8', newline='') as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
            os.replace(name, p)
        finally:
            if os.path.exists(name):
                os.unlink(name)

    def write(self, path, content):
        p = self.path(path)
        before = p.read_text(encoding='utf-8') if p.exists() else ''
        self._save(p, content)
        return self._change(path, before, content)

    def edit(self, path, old, new):
        p = self._existing_text_path(path)
        before = self._read_text(p, path)
        count = before.count(old) if old else 0
        if count != 1:
            raise ValueError(f'旧内容出现 {count} 次，必须恰好一次；请读取文件后补充上下文')
        after = before.replace(old, new, 1)
        self._save(p, after)
        return self._change(path, before, after)

    def _existing_text_path(self, path):
        p = self.path(path)
        if not p.exists():
            raise ValueError(f'文件不存在：{path}；请先确认文件名或列出项目文件')
        if not p.is_file():
            raise ValueError(f'这是目录，不是文件：{path}；请提供具体文件路径')
        return p

    @staticmethod
    def _read_text(p, path, encoding='utf-8'):
        try:
            with p.open(encoding=encoding, newline='') as f:
                return f.read()
        except UnicodeDecodeError:
            raise ValueError(f'无法按 UTF-8 读取：{path}；请先确认文件编码或类型，不要直接覆盖') from None

    @staticmethod
    def _change(path, before, after):
        diff = ''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                           fromfile=path, tofile=path))
        return {'path': path, 'old_lines': len(before.splitlines()),
                'new_lines': len(after.splitlines()), 'diff': diff[:24000],
                'diff_truncated': len(diff) > 24000}

    def bash(self, command, timeout=30):
        if not isinstance(command, str) or not command.strip():
            raise ValueError('command 不能为空')
        if not isinstance(timeout, (float, int)) or not 0 < timeout <= 120:
            raise ValueError('timeout 范围为 0–120 秒')
        # Windows uses PowerShell; this is a trusted local execution tool, not an OS sandbox.
        argv = ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', command] if os.name == 'nt' else ['/bin/bash', '-lc', command]
        env = {k: v for k, v in os.environ.items() if not any(s in k.upper() for s in ('KEY', 'TOKEN', 'SECRET', 'PASSWORD'))}
        proc = subprocess.Popen(argv, cwd=self.root, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                env=env, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                                start_new_session=os.name != 'nt')
        buffers = [bytearray(), bytearray()]
        truncated = [False, False]
        def drain(stream, index):
            while chunk := stream.read(4096):
                room = 16000 - len(buffers[index])
                buffers[index].extend(chunk[:max(0, room)])
                if len(chunk) > room:
                    truncated[index] = True
        readers = [threading.Thread(target=drain, args=(s, i), daemon=True)
                   for i, s in enumerate((proc.stdout, proc.stderr))]
        for reader in readers:
            reader.start()
        deadline = time.monotonic() + timeout
        reason = None
        while proc.poll() is None:
            if self.cancel.is_set() or time.monotonic() >= deadline:
                reason = 'cancelled' if self.cancel.is_set() else 'timeout'
                if os.name == 'nt':
                    subprocess.run(['taskkill', '/PID', str(proc.pid), '/T', '/F'], capture_output=True,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
                    if proc.poll() is None:
                        proc.kill()
                else:
                    import signal
                    os.killpg(proc.pid, signal.SIGKILL)
                break
            time.sleep(.05)
        proc.wait(timeout=5)
        for reader in readers:
            reader.join(timeout=2)
        proc.stdout.close()
        proc.stderr.close()
        return {'stdout': buffers[0].decode('utf-8', errors='replace'),
                'stderr': buffers[1].decode('utf-8', errors='replace'), 'exit_code': proc.returncode,
                'reason': reason, 'truncated': any(truncated)}

    def call(self, name, args):
        if name not in {'read', 'write', 'edit', 'bash'}:
            raise ValueError('未知工具')
        if self.cancel.is_set():
            raise RuntimeError('已中断')
        return getattr(self, name)(**args)


def schema(name, description, properties, required):
    return {'type': 'function', 'function': {'name': name, 'description': description,
            'parameters': {'type': 'object', 'properties': {k: {'type': v} for k, v in properties.items()},
                           'required': required, 'additionalProperties': False}}}


SCHEMAS = [
    schema('read', '读取工作区文件。文本带行号分页，offset 从1开始；图片返回图片内容块。',
           {'path': 'string', 'offset': 'integer', 'limit': 'integer'}, ['path']),
    schema('write', '创建文件或在用户要求时覆盖文件，自动创建父目录。已有代码局部修改用 edit。',
           {'path': 'string', 'content': 'string'}, ['path', 'content']),
    schema('edit', '精确替换唯一字符串。先 read，再提供足够上下文；不唯一时重新读取，不猜测。',
           {'path': 'string', 'old': 'string', 'new': 'string'}, ['path', 'old', 'new']),
    schema('bash', '执行命令、搜索文件、运行测试。Windows 使用 PowerShell；命令失败也返回输出。',
           {'command': 'string', 'timeout': 'number'}, ['command']),
]
