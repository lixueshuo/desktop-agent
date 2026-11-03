# 构建记录

依赖：Python 3.14、requirements-desktop.txt、PyInstaller 6.22.3。

安装打包依赖到 .desktop-deps 后，在 PowerShell 中执行：

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) '.desktop-deps')
python -m PyInstaller --noconfirm DesktopAgent.spec
```

输出：dist/DesktopAgent/DesktopAgent.exe，旁边的 _internal 目录必须保留。这只是程序目录，尚非正式安装器。构建不包含 .env，冻结程序从用户目录 DesktopAgent/.env 读取配置。当前尚待安装、窗口及打包后 MCP 验收，不能作为最终 Release。
