# CC Session Manager

[中文文档](resource/README_CN.md) | English

A lightweight GUI tool for managing Claude Code sessions — find and resume conversations quickly.

## Features

- 📋 **Session List** — Auto-scan all Claude Code sessions with title, time, model, and token usage
- 🔍 **Search & Filter** — Search by content, project path, or Session ID
- 📁 **Project Grouping** — Browse sessions grouped by project in the left panel
- ✏️ **Custom Titles** — Double-click any title to rename it; changes are persisted
- 🏷 **Tag System** — Add multiple tags to sessions and filter by tags
- 🌙 **Light/Dark Theme** — GitHub-style UI with one-click theme toggle
- ▶ **Quick Resume** — One-click to open a terminal and run `claude --resume`

## Installation

### Use the exe (Recommended)

Grab `CCSessionManager.exe` from the `dist/` directory and double-click to run. No Python installation required.

### Run from Source

```bash
pip install PyQt5 pyinstaller
python main.py
```

### Build exe

```bash
build.bat
```

Or manually:

```bash
pyinstaller --onefile --windowed --name "CCSessionManager" ^
  --hidden-import theme --hidden-import parser --hidden-import metadata main.py
```

The output will be at `dist/CCSessionManager.exe`.

## Usage

| Action | Description |
|--------|-------------|
| Double-click title | Edit session title |
| Click "🏷 标签" button | Manage session tags (add/remove) |
| Left panel tabs | Switch between project list and tag filter |
| Check tags | Filter sessions that have ALL checked tags |
| Search bar | Fuzzy search by content, path, or ID |
| 🌙/☀️ button | Toggle light/dark theme |
| "显示子代理" checkbox | Show/hide subagent sessions |

## Data Storage

| File | Description |
|------|-------------|
| `~/.claude/projects/**/*.jsonl` | Claude Code raw session data (read-only) |
| `~/.claude/cc-session-metadata.json` | User-customized titles and tags (auto-created) |

This tool does **NOT** modify any original Claude Code files.

## Requirements

- Windows 10/11 (64-bit)
- [Claude Code](https://claude.ai/code) installed and used

## Tech Stack

- Python 3.13 + PyQt5
- PyInstaller for packaging
- GitHub-style QSS themes

## License

MIT License
