# CC Session Manager

中文 | [English](../README.md)

一个轻量级的 Claude Code 会话管理工具，让你快速找到并恢复历史对话。

## 功能

- 📋 **会话列表** — 自动扫描所有 Claude Code session，显示标题、时间、模型、token 用量
- 🔍 **搜索过滤** — 按内容、项目路径、Session ID 搜索
- 📁 **项目分组** — 左侧面板按项目分组浏览
- ✏️ **自定义标题** — 双击标题即可修改，数据持久保存
- 🏷 **标签系统** — 给 session 添加多个标签，按标签筛选
- 🌙 **明暗主题** — GitHub 风格 UI，一键切换亮色/暗色
- ▶ **快速恢复** — 一键在终端中执行 `claude --resume`

## 安装

### 直接使用 exe（推荐）

从 `dist/` 目录获取 `CCSessionManager.exe`，双击运行即可，无需安装 Python。

### 从源码运行

```bash
pip install PyQt5 pyinstaller
python main.py
```

### 打包 exe

```bash
build.bat
```

或手动执行：

```bash
pyinstaller --onefile --windowed --name "CCSessionManager" ^
  --hidden-import theme --hidden-import parser --hidden-import metadata main.py
```

打包结果在 `dist/CCSessionManager.exe`。

## 使用说明

| 操作 | 说明 |
|------|------|
| 双击标题 | 编辑 session 标题 |
| 点击「🏷 标签」按钮 | 管理 session 标签（添加/移除） |
| 左侧「项目/标签」切换 | 切换项目列表和标签筛选 |
| 勾选标签 | 筛选同时包含所有勾选标签的 session |
| 搜索框 | 按内容、路径、ID 模糊搜索 |
| 🌙/☀️ 按钮 | 切换亮色/暗色主题 |
| 「显示子代理」勾选 | 是否显示 subagents 目录下的会话 |

## 数据存储

| 文件 | 说明 |
|------|------|
| `~/.claude/projects/**/*.jsonl` | Claude Code 原始会话数据（只读） |
| `~/.claude/cc-session-metadata.json` | 用户自定义标题和标签（自动创建） |

本工具**不会修改**任何 Claude Code 原始文件。

## 系统要求

- Windows 10/11（64位）
- [Claude Code](https://claude.ai/code) 已安装并使用过

## 技术栈

- Python 3.13 + PyQt5
- PyInstaller 打包
- GitHub 风格 QSS 主题

## 许可

MIT License
