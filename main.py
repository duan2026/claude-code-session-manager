"""
CC Session Manager - Main Application
A lightweight GUI tool for managing Claude Code sessions.
"""

import sys
import subprocess
from pathlib import Path
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QLineEdit,
    QPushButton,
    QLabel,
    QTextBrowser,
    QSplitter,
    QMessageBox,
    QCheckBox,
)
from PyQt5.QtCore import Qt, QSize, QThread, pyqtSignal
from PyQt5.QtGui import QFont

from parser import Session, load_all_sessions, load_session_messages, search_sessions
from theme import GITHUB_LIGHT, GITHUB_DARK


# ─── Helpers ────────────────────────────────────────────────────────────────

def format_time(dt: datetime | None) -> str:
    """Human-readable relative time."""
    if not dt or dt == datetime.min:
        return "未知"
    now = datetime.now(dt.tzinfo)
    diff = now - dt
    if diff.days < 0:
        return dt.strftime("%m/%d %H:%M")
    if diff.days == 0:
        hours = diff.seconds // 3600
        if hours == 0:
            mins = diff.seconds // 60
            return f"{mins} 分钟前" if mins > 0 else "刚刚"
        return f"{hours} 小时前"
    if diff.days == 1:
        return "昨天"
    if diff.days < 7:
        return f"{diff.days} 天前"
    if diff.days < 30:
        return f"{diff.days // 7} 周前"
    return dt.strftime("%Y/%m/%d")


def shorten_path(path: str, max_len: int = 35) -> str:
    """Shorten a file path for display."""
    if len(path) <= max_len:
        return path
    return "..." + path[-(max_len - 3):]


def get_project_display(path: str) -> str:
    """Get a short display name for a project path - last 1-2 directory names."""
    p = path.rstrip("\\/")
    parts = p.replace("/", "\\").split("\\")
    if len(parts) >= 2:
        return parts[-2] + "\\" + parts[-1]
    return parts[-1] if parts else path


def resolve_display_names(display_names: dict[str, str]) -> dict[str, str]:
    """
    Resolve duplicate display names by showing more path context.
    e.g. two projects both showing "workspace\teaching-book-agent"
    will become "D:\\workspace\\teaching-book-agent" and "...\\teaching-book-agent-opencode"
    """
    # Check for collisions
    name_to_keys: dict[str, list[str]] = {}
    for key, full_path in display_names.items():
        short = get_project_display(full_path)
        name_to_keys.setdefault(short, []).append(key)

    result = {}
    for key, full_path in display_names.items():
        short = get_project_display(full_path)
        if len(name_to_keys[short]) > 1:
            # Collision: use full path instead
            result[key] = full_path
        else:
            result[key] = short
    return result


def format_tokens(n: int) -> str:
    """Format token count for display."""
    if n <= 0:
        return ""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1000:
        return f"{n // 1000}k"
    return str(n)


# ─── Background Loader ─────────────────────────────────────────────────────

class SessionLoader(QThread):
    """Load sessions in background to keep UI responsive."""
    loaded = pyqtSignal(list)

    def run(self):
        sessions = load_all_sessions()
        self.loaded.emit(sessions)


# ─── Session Card Widget ────────────────────────────────────────────────────

class SessionCard(QWidget):
    """A single session card displayed in the session list."""

    def __init__(self, session: Session, parent=None):
        super().__init__(parent)
        self.session = session
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(3)

        # Title - first message
        msg = self.session.first_message[:90]
        self.title_label = QLabel(msg)
        self.title_label.setObjectName("cardTitle")
        self.title_label.setWordWrap(False)
        layout.addWidget(self.title_label)

        # Meta line
        time_str = format_time(self.session.last_active)
        tokens_str = format_tokens(self.session.total_tokens)
        parts = [shorten_path(self.session.cwd)]
        if self.session.model:
            parts.append(self.session.model)
        if tokens_str:
            parts.append(f"{tokens_str} tok")
        parts.append(time_str)

        meta_text = " · ".join(parts)
        self.meta_label = QLabel(meta_text)
        self.meta_label.setObjectName("cardMeta")
        layout.addWidget(self.meta_label)


# ─── Main Window ────────────────────────────────────────────────────────────

class CCSessionManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.sessions: list[Session] = []
        self.all_sessions: list[Session] = []  # including subagents
        self.filtered_sessions: list[Session] = []
        self.current_session: Session | None = None
        self.is_dark = False
        self.show_subagents = False

        self._init_ui()
        self._load_sessions()

    # ── UI Setup ─────────────────────────────────────────────────────────

    def _init_ui(self):
        self.setWindowTitle("CC Session Manager")
        self.setMinimumSize(1200, 750)
        self.resize(1400, 900)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Top bar ─────────────────────────────────────────────────────
        top_bar = QWidget()
        top_bar.setObjectName("topBar")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(16, 8, 16, 8)

        title = QLabel("CC Session Manager")
        title.setObjectName("titleLabel")

        self.search_bar = QLineEdit()
        self.search_bar.setObjectName("searchBar")
        self.search_bar.setPlaceholderText("搜索对话内容、项目路径、Session ID...")
        self.search_bar.textChanged.connect(self._on_search)

        self.theme_btn = QPushButton("🌙")
        self.theme_btn.setObjectName("themeBtn")
        self.theme_btn.setFixedSize(56, 48)
        self.theme_btn.setToolTip("切换亮色/暗色主题")
        self.theme_btn.clicked.connect(self._toggle_theme)

        self.subagent_cb = QCheckBox("显示子代理")
        self.subagent_cb.setObjectName("subagentCb")
        self.subagent_cb.setToolTip("是否显示 subagents 目录下的会话")
        self.subagent_cb.setChecked(False)
        self.subagent_cb.toggled.connect(self._toggle_subagents)

        top_layout.addWidget(title)
        top_layout.addSpacing(16)
        top_layout.addWidget(self.search_bar, 1)
        top_layout.addSpacing(8)
        top_layout.addWidget(self.subagent_cb)
        top_layout.addSpacing(4)
        top_layout.addWidget(self.theme_btn)

        root.addWidget(top_bar)

        # ── Body: splitter (left + right) ───────────────────────────────
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        # Left panel - project filter
        left_panel = QWidget()
        left_panel.setObjectName("projectPanel")
        left_panel.setMinimumWidth(200)
        left_panel.setMaximumWidth(500)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        proj_header = QLabel("📁 项目")
        proj_header.setObjectName("sectionLabel")
        left_layout.addWidget(proj_header)

        self.project_list = QListWidget()
        self.project_list.setObjectName("projectList")
        self.project_list.currentRowChanged.connect(self._on_project_filter)
        left_layout.addWidget(self.project_list)

        splitter.addWidget(left_panel)

        # Right panel
        right_panel = QWidget()
        right_panel.setMinimumWidth(500)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(12, 8, 12, 10)
        right_layout.setSpacing(8)

        # Session list
        self.session_list = QListWidget()
        self.session_list.setObjectName("sessionList")
        self.session_list.currentRowChanged.connect(self._on_session_select)
        right_layout.addWidget(self.session_list, 1)

        # Preview label
        preview_header = QLabel("💬 对话预览")
        preview_header.setObjectName("sectionLabel")
        right_layout.addWidget(preview_header)

        # Preview panel
        self.preview = QTextBrowser()
        self.preview.setObjectName("previewPanel")
        self.preview.setOpenExternalLinks(False)
        self.preview.setMaximumHeight(280)
        self.preview.setPlaceholderText("点击上方对话查看预览...")
        right_layout.addWidget(self.preview)

        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.resume_btn = QPushButton("▶ 在终端中 Resume")
        self.resume_btn.setObjectName("primaryBtn")
        self.resume_btn.clicked.connect(self._resume_session)
        self.resume_btn.setEnabled(False)

        self.copy_btn = QPushButton("📋 复制命令")
        self.copy_btn.clicked.connect(self._copy_resume_cmd)
        self.copy_btn.setEnabled(False)

        btn_row.addWidget(self.resume_btn)
        btn_row.addWidget(self.copy_btn)
        btn_row.addStretch()

        self.delete_btn = QPushButton("🗑 删除")
        self.delete_btn.setObjectName("dangerBtn")
        self.delete_btn.clicked.connect(self._delete_session)
        self.delete_btn.setEnabled(False)
        btn_row.addWidget(self.delete_btn)

        right_layout.addLayout(btn_row)

        # Status
        self.status_label = QLabel("加载中...")
        self.status_label.setObjectName("statusLabel")
        right_layout.addWidget(self.status_label)

        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([300, 1100])

        root.addWidget(splitter, 1)

        # Apply initial theme
        self._apply_theme()

    # ── Data Loading ─────────────────────────────────────────────────────

    def _load_sessions(self):
        self.status_label.setText("⏳ 正在扫描 sessions...")
        self._loader = SessionLoader()
        self._loader.loaded.connect(self._on_sessions_loaded)
        self._loader.start()

    def _on_sessions_loaded(self, sessions: list[Session]):
        self.all_sessions = sessions
        self.sessions = self._filter_subagents(sessions)
        self.filtered_sessions = self.sessions.copy()
        self.status_label.setText(f"✅ 共 {len(self.sessions)} 个 sessions")
        self._populate_projects()
        self._populate_sessions()

    def _filter_subagents(self, sessions: list[Session]) -> list[Session]:
        """Filter out subagent sessions based on toggle."""
        if self.show_subagents:
            return sessions
        return [s for s in sessions if s.project_key != "subagents"]

    def _toggle_subagents(self, checked: bool):
        """Toggle subagent visibility."""
        self.show_subagents = checked
        self.sessions = self._filter_subagents(self.all_sessions)
        self._on_search(self.search_bar.text())
        total = len(self.all_sessions)
        shown = len(self.sessions)
        if checked:
            self.status_label.setText(f"✅ 共 {shown} 个 sessions（含子代理）")
        else:
            sub_count = total - shown
            self.status_label.setText(f"✅ 共 {shown} 个 sessions（已隐藏 {sub_count} 个子代理）")
        self._populate_projects()
        self._populate_sessions()

    # ── Project List ─────────────────────────────────────────────────────

    def _populate_projects(self):
        self.project_list.blockSignals(True)
        self.project_list.clear()

        # Group by project_key, collect display name from project_dir (cwd)
        counts: dict[str, int] = {}
        display_names: dict[str, str] = {}
        for s in self.sessions:
            key = s.project_key
            counts[key] = counts.get(key, 0) + 1
            # Use the shortest cwd as the display name (most likely the root)
            if key not in display_names or len(s.project_dir) < len(display_names[key]):
                display_names[key] = s.project_dir

        # "All" item
        all_item = QListWidgetItem(f"📋 全部  ({len(self.sessions)})")
        all_item.setData(Qt.UserRole, "__all__")
        self.project_list.addItem(all_item)

        # Per-project items, sorted by count
        for key, count in sorted(counts.items(), key=lambda x: -x[1]):
            full_path = display_names.get(key, key)
            item = QListWidgetItem(f"📁 {full_path}  ({count})")
            item.setData(Qt.UserRole, key)
            item.setToolTip(full_path)
            self.project_list.addItem(item)

        self.project_list.setCurrentRow(0)
        self.project_list.blockSignals(False)

    # ── Session List ─────────────────────────────────────────────────────

    def _populate_sessions(self):
        self.session_list.clear()

        for s in self.filtered_sessions:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, s.session_id)
            item.setSizeHint(QSize(0, 80))

            card = SessionCard(s)
            self.session_list.addItem(item)
            self.session_list.setItemWidget(item, card)

        if not self.filtered_sessions:
            self.status_label.setText("没有找到匹配的 sessions")

    # ── Search & Filter ──────────────────────────────────────────────────

    def _get_current_project(self) -> str:
        item = self.project_list.currentItem()
        if item:
            return item.data(Qt.UserRole) or "__all__"
        return "__all__"

    def _on_search(self, text: str):
        project = self._get_current_project()
        self.filtered_sessions = search_sessions(self.sessions, text, project)
        self._populate_sessions()
        total = len(self.sessions)
        shown = len(self.filtered_sessions)
        if text or project != "__all__":
            self.status_label.setText(f"🔍 显示 {shown} / {total} 个 sessions")
        else:
            self.status_label.setText(f"✅ 共 {total} 个 sessions")

    def _on_project_filter(self, _row: int):
        self._on_search(self.search_bar.text())

    # ── Session Preview ──────────────────────────────────────────────────

    def _on_session_select(self, row: int):
        if row < 0 or row >= len(self.filtered_sessions):
            self.current_session = None
            self.resume_btn.setEnabled(False)
            self.copy_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)
            return

        session = self.filtered_sessions[row]
        self.current_session = session

        # Load full messages in background? No - it's fast enough for preview.
        messages = load_session_messages(session.file_path)

        # Render HTML
        is_dark = self.is_dark
        user_bg = "#161b22" if is_dark else "#f6f8fa"
        border_color = "#30363d" if is_dark else "#d0d7de"
        text_color = "#e6edf3" if is_dark else "#1f2328"
        dim_color = "#8b949e" if is_dark else "#656d76"

        html_parts = [f'<div style="font-family: Segoe UI, Microsoft YaHei, sans-serif; color: {text_color};">']

        for role, content in messages[:30]:
            content_html = (
                content.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace("\n", "<br>")
            )
            # Truncate very long messages in preview
            if len(content_html) > 600:
                content_html = content_html[:600] + "..."

            if role == "user":
                html_parts.append(
                    f'<div style="margin: 8px 0; padding: 8px 12px; '
                    f'background: {user_bg}; border: 1px solid {border_color}; '
                    f'border-radius: 8px;">'
                    f'<b style="font-size: 22px; color: {dim_color};">👤 你</b><br>'
                    f'<span style="font-size: 26px;">{content_html}</span></div>'
                )
            else:
                html_parts.append(
                    f'<div style="margin: 8px 0; padding: 8px 12px;">'
                    f'<b style="font-size: 22px; color: {dim_color};">🤖 Claude</b><br>'
                    f'<span style="font-size: 26px;">{content_html}</span></div>'
                )

        if not messages:
            html_parts.append(f'<i style="color: {dim_color};">无对话内容</i>')

        if len(messages) > 30:
            html_parts.append(
                f'<div style="text-align: center; color: {dim_color}; padding: 8px;">'
                f"... 还有 {len(messages) - 30} 条消息</div>"
            )

        html_parts.append("</div>")
        self.preview.setHtml("".join(html_parts))

        self.resume_btn.setEnabled(True)
        self.copy_btn.setEnabled(True)
        self.delete_btn.setEnabled(True)

    # ── Actions ──────────────────────────────────────────────────────────

    def _resume_session(self):
        """Open a terminal and run claude --resume."""
        if not self.current_session:
            return

        s = self.current_session
        cmd = f"claude --resume {s.session_id}"
        cwd = s.cwd if s.cwd and Path(s.cwd).exists() else str(Path.home())

        # Try Windows Terminal first, fallback to cmd
        try:
            subprocess.Popen(
                ["wt.exe", "-d", cwd, "--", "cmd.exe", "/k", cmd],
                cwd=cwd,
            )
        except FileNotFoundError:
            try:
                subprocess.Popen(
                    ["cmd.exe", "/k", f'cd /d "{cwd}" && {cmd}'],
                    cwd=cwd,
                )
            except Exception as e:
                QMessageBox.warning(self, "错误", f"无法打开终端:\n{e}")

    def _copy_resume_cmd(self):
        """Copy resume command to clipboard."""
        if not self.current_session:
            return

        cmd = f"claude --resume {self.current_session.session_id}"
        QApplication.clipboard().setText(cmd)
        self.status_label.setText(f"✅ 已复制: {cmd}")

    def _delete_session(self):
        """Delete a session file after confirmation."""
        if not self.current_session:
            return

        s = self.current_session
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除这个 session 吗？\n\n"
            f"{s.first_message[:80]}\n\n"
            f"文件: {s.session_id}.jsonl",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            try:
                Path(s.file_path).unlink()
                self.sessions = [x for x in self.sessions if x.session_id != s.session_id]
                self._on_sessions_loaded(self.sessions)
                self.status_label.setText("✅ Session 已删除")
            except Exception as e:
                QMessageBox.warning(self, "删除失败", str(e))

    # ── Theme ────────────────────────────────────────────────────────────

    def _toggle_theme(self):
        self.is_dark = not self.is_dark
        self.theme_btn.setText("☀️" if self.is_dark else "🌙")
        self._apply_theme()
        # Re-render preview if a session is selected
        if self.current_session:
            row = self.session_list.currentRow()
            if row >= 0:
                self._on_session_select(row)

    def _apply_theme(self):
        theme = GITHUB_DARK if self.is_dark else GITHUB_LIGHT
        self.setStyleSheet(theme)


# ─── Entry Point ────────────────────────────────────────────────────────────

def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 18))

    window = CCSessionManager()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
