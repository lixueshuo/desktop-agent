# 构建与验收

工具版本：Python 3.14.7、pywebview 6.2.1、PyInstaller 6.22.3、Inno Setup 6.5.4。

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) '.desktop-deps')
python -m PyInstaller --noconfirm --distpath dist/release DesktopAgent.spec
ISCC.exe installer.iss
```

安装包：dist/installer/DesktopAgent-Setup-1.0.0.exe。安装器为当前用户安装，建立快捷方式与卸载入口。安装后模型配置与日志位于用户目录 DesktopAgent，包内不含 .env。

2026-11-06 实际将安装包安装到隔离验收目录，启动窗口、点击文件预览，并从窗口发送真实 DeepSeek 请求；read 与 mcp__current_time 均成功，最终中文回复正常。打包后独立 MCP 工具调用也通过。截图见 docs/screenshots。18项自动化测试通过。

Windows 需 WebView2。命令工具可调用本机 Python，因此运行项目测试仍需相应运行环境。远程桌面环境默认禁用 GPU 加速以兼容捕获。

演示视频采用实际安装版操作时采集的画面，按真实采集时间间隔编码，无配音。它是功能演示，不能代替学生现场五分钟答辩。
