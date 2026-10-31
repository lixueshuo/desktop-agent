# 开发记录

## 2026-10-29：初始原型

在 AI 辅助下实现后端循环、四个工具及 Tkinter 桌面原型。8 项后端测试通过，并验证 DeepSeek 实际调用。原型不等于最终作业，正式界面、MCP、打包与交付材料尚待实现。

## 2026-10-30：文件工具报错改进

本次只改进 read/edit 三种失败提示：文件不存在、误传目录、非 UTF-8 文件。提示包含相对路径及下一步建议，不返回整段系统异常。编码错误时不尝试覆盖文件。

新增三个回归测试，分别验证上述情况，检查缺失文件不会被创建、目录仍是目录、无法解码的文件字节保持不变。保留原有 CRLF 精确修改测试。

验证命令：`python -m unittest discover -s tests -v`。本次无需调用模型，不消耗 API 额度。

## 2026-10-31：正式桌面界面第一阶段

新增 pywebview 窗口及 ui/index.html 三栏页面，接通练习项目文件列表与带行号的只读预览。界面使用 textContent 显示文件内容，避免将代码作为 HTML 执行；文件读取仍通过原有路径限制。对话按钮明确禁用，等待后续接入，旧 Tkinter 原型继续保留。

运行：先执行 python -m pip install --target .desktop-deps -r requirements-desktop.txt，再执行 python desktop.py。依赖版本锁定为 pywebview 6.2.1。Windows 需要 WebView2 运行时。

文件桥接检查通过，依赖安装完成。实际窗口视觉检查尚待完成。本次未调用模型。
