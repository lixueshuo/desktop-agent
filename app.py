"""Native desktop client; backend remains independently runnable."""
import json
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from agent.runtime import ROOT, run
from agent.tools import Tools


class Desktop:
    def __init__(self, window):
        self.window = window
        window.title('Desktop Agent · Python 编程助手')
        window.geometry('1280x820')
        window.minsize(960, 620)
        self.workspace = ROOT / 'examples' / 'practice'
        self.events = queue.Queue()
        self.cancel = threading.Event()
        self.busy = False
        self.files = {}
        self.current = None
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TButton', padding=7)
        header = ttk.Frame(window, padding=12)
        header.pack(fill='x')
        ttk.Label(header, text='Desktop Agent', font=('Microsoft YaHei UI', 18, 'bold')).pack(side='left')
        self.path_label = ttk.Label(header, text=str(self.workspace))
        self.path_label.pack(side='left', padx=20)
        self.choose = ttk.Button(header, text='选择项目', command=self.select_workspace)
        self.choose.pack(side='right')
        ttk.Button(header, text='配置说明', command=self.settings).pack(side='right', padx=8)
        pane = ttk.Panedwindow(window, orient='horizontal')
        pane.pack(fill='both', expand=True, padx=12)
        left = ttk.Frame(pane)
        middle = ttk.Frame(pane)
        right = ttk.Frame(pane)
        pane.add(left, weight=1)
        pane.add(middle, weight=3)
        pane.add(right, weight=3)
        ttk.Label(left, text='项目文件', padding=8).pack(anchor='w')
        self.tree = ttk.Treeview(left, show='tree')
        self.tree.pack(fill='both', expand=True)
        self.tree.bind('<<TreeviewSelect>>', self.preview)
        ttk.Button(left, text='刷新文件', command=self.refresh).pack(fill='x')
        self.filename = ttk.Label(middle, text='选择文件查看内容', padding=8)
        self.filename.pack(anchor='w')
        self.code = self.textbox(middle)
        self.code.configure(state='disabled')
        ttk.Label(right, text='对话与工具记录', padding=8).pack(anchor='w')
        self.log = self.textbox(right)
        self.log.tag_configure('error', foreground='#bf2525')
        self.log.tag_configure('tool', foreground='#176e86')
        self.log.tag_configure('done', foreground='#21633a')
        self.log.configure(state='disabled')
        bottom = ttk.Frame(window, padding=12)
        bottom.pack(fill='x')
        self.input = tk.Text(bottom, height=3, font=('Microsoft YaHei UI', 11), wrap='word')
        self.input.pack(side='left', fill='x', expand=True)
        self.input.insert('1.0', '检查 stats.py，运行测试，修复问题后再次运行测试。')
        self.send = ttk.Button(bottom, text='发送任务', command=self.submit)
        self.send.pack(side='left', padx=8)
        self.stop = ttk.Button(bottom, text='中断', command=self.interrupt, state='disabled')
        self.stop.pack(side='left')
        self.status = ttk.Label(window, text='就绪 · 请仅选择可信练习项目，命令工具拥有当前用户权限', padding=(12, 4))
        self.status.pack(fill='x')
        self.refresh()
        self.append('已打开练习项目。请配置 API 后发送任务。工具调用和错误会显示在这里。\n')
        window.after(100, self.poll)
        window.protocol('WM_DELETE_WINDOW', self.close)

    @staticmethod
    def textbox(parent):
        frame = ttk.Frame(parent)
        frame.pack(fill='both', expand=True)
        text = tk.Text(frame, wrap='none', font=('Consolas', 11), undo=False)
        scroll = ttk.Scrollbar(frame, command=text.yview)
        scroll.pack(side='right', fill='y')
        text.configure(yscrollcommand=scroll.set)
        text.pack(fill='both', expand=True)
        return text

    def append(self, text, tag=''):
        self.log.configure(state='normal')
        self.log.insert('end', text, tag)
        self.log.see('end')
        self.log.configure(state='disabled')

    def select_workspace(self):
        folder = filedialog.askdirectory(title='选择可信练习项目')
        if folder:
            self.workspace = Path(folder).resolve()
            self.path_label.configure(text=str(self.workspace))
            self.current = None
            self.refresh()

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        self.files.clear()
        count = 0
        def visit(folder, parent='', depth=0):
            nonlocal count
            if depth > 6 or count >= 500:
                return
            try:
                entries = sorted(folder.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
            except OSError:
                return
            for p in entries:
                if count >= 500:
                    break
                if p.name.startswith('.') or p.name in {'__pycache__', 'node_modules', 'dist', 'build'} or p.is_symlink():
                    continue
                item = self.tree.insert(parent, 'end', text=p.name, open=depth == 0)
                self.files[item] = p
                count += 1
                if p.is_dir():
                    visit(p, item, depth + 1)
        visit(self.workspace)

    def preview(self, event=None):
        selection = self.tree.selection()
        if not selection:
            return
        path = self.files.get(selection[0])
        if path and path.is_file():
            self.current = path
            self.show_file()

    def show_file(self):
        try:
            relative = str(self.current.relative_to(self.workspace))
            data = Tools(self.workspace).read(relative, limit=500)
            content = data['text'] if isinstance(data, dict) else '[图片文件，read 工具可发送图片内容块]'
            self.filename.configure(text=relative)
        except Exception as e:
            content = str(e)
        self.code.configure(state='normal')
        self.code.delete('1.0', 'end')
        self.code.insert('1.0', content)
        self.code.configure(state='disabled')

    def submit(self):
        task = self.input.get('1.0', 'end').strip()
        if self.busy or not task:
            return
        self.busy = True
        self.cancel = threading.Event()
        self.send.configure(state='disabled')
        self.choose.configure(state='disabled')
        self.stop.configure(state='normal')
        self.append('\n你：' + task + '\n')
        self.status.configure(text='正在运行…')
        workspace = self.workspace
        cancel = self.cancel
        def work():
            try:
                for event in run(task, workspace, cancel):
                    self.events.put(event)
            except Exception as e:
                self.events.put({'type': 'error', 'text': str(e)})
            finally:
                self.events.put({'type': 'finished'})
        threading.Thread(target=work, daemon=True).start()

    def interrupt(self):
        self.cancel.set()
        self.stop.configure(state='disabled')
        self.status.configure(text='已请求中断；命令正在停止，模型网络请求最多等待 60 秒，不再执行新工具')
        self.append('\n已请求中断。\n', 'error')

    def poll(self):
        try:
            while True:
                event = self.events.get_nowait()
                kind = event['type']
                if kind == 'step':
                    self.status.configure(text=f"第 {event['step']} 步：等待模型")
                elif kind == 'tool_start':
                    names = {'read': '正在读取文件', 'write': '正在写入文件', 'edit': '正在修改代码', 'bash': '正在运行命令'}
                    self.append('\n' + names.get(event['name'], event['name']) + '\n', 'tool')
                    try:
                        args = json.loads(event['arguments'])
                        self.append(str(args.get('path') or args.get('command') or '') + '\n', 'tool')
                    except (ValueError, TypeError):
                        pass
                    self.status.configure(text='执行工具：' + event['name'])
                elif kind == 'tool_result':
                    result = event['result']
                    if isinstance(result, dict):
                        if 'error' in result:
                            output = '操作失败：' + str(result['error'])
                        elif event['name'] == 'read':
                            output = '读取完成，共 ' + str(result.get('total_lines', 0)) + ' 行。\n' + result.get('text', '')
                        elif event['name'] in {'write', 'edit'}:
                            output = f"修改已保存：{result.get('old_lines')} 行 → {result.get('new_lines')} 行\n" + result.get('diff', '')
                        else:
                            output = f"命令结束，退出码：{result.get('exit_code')}\n" + result.get('stdout', '') + result.get('stderr', '')
                            if result.get('reason'):
                                output += '\n停止原因：' + str(result['reason'])
                    else:
                        output = str(result)
                    self.append(output + '\n', 'error' if event['error'] else 'tool')
                    if event['name'] in {'write', 'edit'} and not event['error']:
                        self.refresh()
                        if self.current:
                            self.show_file()
                elif kind in {'done', 'error', 'cancelled'}:
                    prefix = '\n助手回复：\n' if kind == 'done' else '\n'
                    self.append(prefix + event.get('text', '已中断') + '\n', 'done' if kind == 'done' else 'error')
                elif kind == 'finished':
                    self.busy = False
                    self.send.configure(state='normal')
                    self.choose.configure(state='normal')
                    self.stop.configure(state='disabled')
                    self.status.configure(text='本次运行已结束')
        except queue.Empty:
            pass
        self.window.after(100, self.poll)

    def settings(self):
        messagebox.showinfo('API 配置', '在项目的 .env 文件中配置 Key、接口地址和模型名称。\n不要将 Key 填入对话框或上传 GitHub。\n每次发送任务会重新读取配置。')

    def close(self):
        self.cancel.set()
        self.window.destroy()


if __name__ == '__main__':
    root = tk.Tk()
    Desktop(root)
    root.mainloop()
