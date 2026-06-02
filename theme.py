"""
CC Session Manager - GitHub Style Themes
Light and Dark QSS stylesheets matching GitHub's design language.
"""

GITHUB_LIGHT = """
/* === Global === */
QMainWindow, QWidget {
    background-color: #ffffff;
    color: #1f2328;
    font-family: "Segoe UI", "Microsoft YaHei", system-ui, sans-serif;
    font-size: 28px;
}

/* === Top Bar === */
#topBar {
    background-color: #ffffff;
    border-bottom: 1px solid #d0d7de;
    padding: 14px 20px;
}

#titleLabel {
    font-size: 36px;
    font-weight: 700;
    color: #1f2328;
}

/* === Search Bar === */
#searchBar {
    background-color: #f6f8fa;
    border: 1px solid #d0d7de;
    border-radius: 8px;
    padding: 12px 18px;
    font-size: 26px;
    color: #1f2328;
    min-height: 36px;
}
#searchBar:focus {
    border-color: #0969da;
    background-color: #ffffff;
}

/* === Theme Toggle Button === */
#themeBtn {
    background-color: transparent;
    border: 1px solid #d0d7de;
    border-radius: 8px;
    padding: 6px 14px;
    font-size: 30px;
    min-width: 56px;
}
#themeBtn:hover {
    background-color: #f6f8fa;
    border-color: #0969da;
}

/* === Subagent Checkbox === */
#subagentCb {
    font-size: 22px;
    spacing: 6px;
}
#subagentCb::indicator {
    width: 22px;
    height: 22px;
}

/* === Left Panel - Projects === */
#projectPanel {
    background-color: #f6f8fa;
    border-right: 1px solid #d0d7de;
}

#sectionLabel {
    color: #1f2328;
    font-size: 24px;
    font-weight: 600;
    padding: 12px 14px 8px;
}

#projectList {
    background-color: #f6f8fa;
    border: none;
    outline: none;
    padding: 2px 8px;
    font-size: 26px;
}
#projectList::item {
    padding: 10px 12px;
    border-radius: 8px;
    margin: 2px 0;
    color: #1f2328;
}
#projectList::item:selected {
    background-color: #0969da;
    color: #ffffff;
}
#projectList::item:hover:!selected {
    background-color: #eaeef2;
}

/* === Session List === */
#sessionList {
    background-color: #ffffff;
    border: 1px solid #d0d7de;
    border-radius: 8px;
    outline: none;
    padding: 2px;
}
#sessionList::item {
    padding: 2px;
    border-bottom: 1px solid #d8dee4;
    border-radius: 0;
}
#sessionList::item:selected {
    background-color: #ddf4ff;
}
#sessionList::item:hover:!selected {
    background-color: #f6f8fa;
}
#sessionList::item:last-child {
    border-bottom: none;
}

/* Session card inner widgets */
#cardTitle {
    font-size: 28px;
    font-weight: 600;
    color: #1f2328;
}
#cardMeta {
    font-size: 22px;
    color: #656d76;
}

/* === Preview Panel === */
#previewPanel {
    background-color: #ffffff;
    border: 1px solid #d0d7de;
    border-radius: 8px;
    padding: 8px;
    color: #1f2328;
    font-size: 28px;
}

/* === Action Buttons === */
QPushButton {
    background-color: #f6f8fa;
    border: 1px solid rgba(31,35,40,0.15);
    border-radius: 8px;
    padding: 10px 28px;
    color: #1f2328;
    font-weight: 500;
    font-size: 26px;
    min-height: 40px;
}
QPushButton:hover {
    background-color: #0969da;
    color: #ffffff;
    border-color: #0969da;
}
QPushButton:pressed {
    background-color: #0550ae;
}
QPushButton:disabled {
    background-color: #f6f8fa;
    color: #8b949e;
    border-color: #d0d7de;
}

/* Primary (green) button */
#primaryBtn {
    background-color: #2da44e;
    color: #ffffff;
    border-color: rgba(31,35,40,0.15);
    font-weight: 600;
}
#primaryBtn:hover {
    background-color: #2c974b;
    border-color: rgba(31,35,40,0.15);
}
#primaryBtn:disabled {
    background-color: #94d3a2;
    color: #ffffff;
}

/* Danger (red) button */
#dangerBtn {
    color: #d1242f;
    border-color: #d1242f;
}
#dangerBtn:hover {
    background-color: #d1242f;
    color: #ffffff;
}

/* === Status Label === */
#statusLabel {
    color: #656d76;
    font-size: 22px;
    padding: 4px 6px;
}

/* === Scrollbars === */
QScrollBar:vertical {
    background: transparent;
    width: 14px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #d0d7de;
    border-radius: 7px;
    min-height: 40px;
}
QScrollBar::handle:vertical:hover {
    background: #b0b8c1;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
    background: none;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}

/* === Splitter === */
QSplitter::handle {
    background-color: #d0d7de;
    width: 2px;
}
"""

GITHUB_DARK = """
/* === Global === */
QMainWindow, QWidget {
    background-color: #0d1117;
    color: #e6edf3;
    font-family: "Segoe UI", "Microsoft YaHei", system-ui, sans-serif;
    font-size: 28px;
}

/* === Top Bar === */
#topBar {
    background-color: #0d1117;
    border-bottom: 1px solid #30363d;
    padding: 14px 20px;
}

#titleLabel {
    font-size: 36px;
    font-weight: 700;
    color: #e6edf3;
}

/* === Search Bar === */
#searchBar {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 12px 18px;
    font-size: 26px;
    color: #e6edf3;
    min-height: 36px;
}
#searchBar:focus {
    border-color: #58a6ff;
    background-color: #0d1117;
}

/* === Theme Toggle Button === */
#themeBtn {
    background-color: transparent;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 6px 14px;
    font-size: 30px;
    min-width: 56px;
}
#themeBtn:hover {
    background-color: #21262d;
    border-color: #58a6ff;
}

/* === Subagent Checkbox === */
#subagentCb {
    font-size: 22px;
    spacing: 6px;
}
#subagentCb::indicator {
    width: 22px;
    height: 22px;
}

/* === Left Panel - Projects === */
#projectPanel {
    background-color: #161b22;
    border-right: 1px solid #30363d;
}

#sectionLabel {
    color: #e6edf3;
    font-size: 24px;
    font-weight: 600;
    padding: 12px 14px 8px;
}

#projectList {
    background-color: #161b22;
    border: none;
    outline: none;
    padding: 2px 8px;
    font-size: 26px;
}
#projectList::item {
    padding: 10px 12px;
    border-radius: 8px;
    margin: 2px 0;
    color: #e6edf3;
}
#projectList::item:selected {
    background-color: #58a6ff;
    color: #0d1117;
}
#projectList::item:hover:!selected {
    background-color: #21262d;
}

/* === Session List === */
#sessionList {
    background-color: #0d1117;
    border: 1px solid #30363d;
    border-radius: 8px;
    outline: none;
    padding: 2px;
}
#sessionList::item {
    padding: 2px;
    border-bottom: 1px solid #21262d;
    border-radius: 0;
}
#sessionList::item:selected {
    background-color: #1f3a5f;
}
#sessionList::item:hover:!selected {
    background-color: #161b22;
}
#sessionList::item:last-child {
    border-bottom: none;
}

/* Session card inner widgets */
#cardTitle {
    font-size: 28px;
    font-weight: 600;
    color: #e6edf3;
}
#cardMeta {
    font-size: 22px;
    color: #8b949e;
}

/* === Preview Panel === */
#previewPanel {
    background-color: #0d1117;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 8px;
    color: #e6edf3;
    font-size: 28px;
}

/* === Action Buttons === */
QPushButton {
    background-color: #21262d;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 10px 28px;
    color: #e6edf3;
    font-weight: 500;
    font-size: 26px;
    min-height: 40px;
}
QPushButton:hover {
    background-color: #58a6ff;
    color: #0d1117;
    border-color: #58a6ff;
}
QPushButton:pressed {
    background-color: #388bfd;
}
QPushButton:disabled {
    background-color: #21262d;
    color: #484f58;
    border-color: #30363d;
}

/* Primary (green) button */
#primaryBtn {
    background-color: #238636;
    color: #ffffff;
    border-color: #238636;
    font-weight: 600;
}
#primaryBtn:hover {
    background-color: #2ea043;
    border-color: #2ea043;
}
#primaryBtn:disabled {
    background-color: #238636;
    color: rgba(255,255,255,0.5);
}

/* Danger (red) button */
#dangerBtn {
    color: #f85149;
    border-color: #f85149;
}
#dangerBtn:hover {
    background-color: #f85149;
    color: #ffffff;
}

/* === Status Label === */
#statusLabel {
    color: #8b949e;
    font-size: 22px;
    padding: 4px 6px;
}

/* === Scrollbars === */
QScrollBar:vertical {
    background: transparent;
    width: 14px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #30363d;
    border-radius: 7px;
    min-height: 40px;
}
QScrollBar::handle:vertical:hover {
    background: #484f58;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
    background: none;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}

/* === Splitter === */
QSplitter::handle {
    background-color: #30363d;
    width: 2px;
}
"""
