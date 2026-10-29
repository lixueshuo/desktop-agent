# Desktop Agent

Python 桌面 AI 编程助手课程项目。当前已实现独立后端、四个内置工具、本地 SSE 事件接口和 Tkinter 桌面原型；MCP、安装包尚待实现。课件列举 pywebview/Electron/Tauri，正式提交前应按课程要求迁移到其中一种；当前 Tkinter 窗口用于本地验证交互。

## 打开桌面原型

双击 `启动桌面助手.bat`，或在项目目录运行 `python app.py`。默认打开 `examples/practice`，里面有一个故意写错的均值函数和对应测试，供验证模型真实修改代码。发送默认任务后，右侧显示工具参数、输出、修改 diff 和失败信息。每次任务独立开始，不保留前次对话上下文。

## 后端启动（三步）

1. 安装 Python 3.14，将 `.env.example` 复制为 `.env`，在本地填写 DeepSeek API Key。已有 `.env` 时不要覆盖它。
2. 在仓库目录打开 PowerShell，执行 `python -m server`。
3. 另一个 PowerShell 窗口调用下面接口，或用命令行运行智能体。

当前后端仅用 Python 标准库，无第三方依赖。

```powershell
python -m agent "读取代码并运行相关测试，说明发现的问题" --workspace "C:\你的练习项目"
```

SSE：启动后端时终端显示一个临时本地访问令牌，将下面 TOKEN 换成它。此令牌不是 DeepSeek Key。

```powershell
curl.exe -N http://127.0.0.1:8765/run -H "Authorization: Bearer TOKEN" -H "Content-Type: application/json" --data-binary '@request.json'
```

`request.json` 示例（Windows 路径反斜杠必须转义）：

```json
{"task":"读取文件，运行测试并说明结果","workspace":"C:\\你的练习项目"}
```

中断接口为 `POST /cancel`，使用相同本地令牌，JSON 请求体 `{}`。正在执行的命令会终止进程树；正在等待的模型 HTTP 请求最迟在 60 秒超时，期间不再执行新工具。

## 工具

- read：UTF-8 文本带行号分页，图片使用多模态内容块。
- write：创建父目录，临时文件写完后原子替换，报告前后行数和 diff。
- edit：旧字符串必须恰好出现一次，否则不修改文件；保留原有换行。
- bash：Windows 实际使用 PowerShell，返回 stdout、stderr、退出码，最长 120 秒，输出有截断。

文件工具限制在工作区内，并拒绝 `.env`、`.git`、`.ssh`。**命令工具拥有当前用户的系统权限，不是操作系统沙箱**，只对可信练习项目使用。不要选择存有密钥或私人资料的目录作为工作区。

## 测试

```powershell
python -m unittest discover -s tests -v
```

覆盖精确修改失败不写盘、分页、目录越界、秘密文件、CRLF 换行、命令失败、超时、输出截断、中断，以及模拟模型的工具错误回灌。模拟测试不能代替真实 DeepSeek 工具调用验证。

API 返回 402 表示余额不足。模型名称、接口地址可在 `.env` 配置；密钥不得上传。

## 后续交付

- 按课程指定技术完善正式桌面窗口，改进长请求中断。
- 外部 MCP 服务集成、真实运行 trace。
- Windows 安装包、Release、报告和演示视频。
- 至少 15 次真实提交，开发跨度至少 7 天。

参考接口：https://api-docs.deepseek.com/guides/tool_calls/
