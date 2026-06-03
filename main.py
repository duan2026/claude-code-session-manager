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
    QInputDialog,
    QDialog,
    QScrollArea,
    QFrame,
    QStackedWidget,
)
from PyQt5.QtCore import Qt, QSize, QThread, pyqtSignal, pyqtBoundSignal
from PyQt5.QtGui import QFont

from parser import Session, load_all_sessions, load_session_messages, search_sessions
from metadata import get_title, set_title, get_tags, set_tags, get_all_tags, load_metadata
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

    title_changed = pyqtSignal(str)  # emits session_id when title edited

    def __init__(self, session: Session, parent=None):
        super().__init__(parent)
        self.session = session
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(3)

        # Title - custom title or AI-generated title
        title_text = self.session.custom_title or self.session.first_message
        self.title_label = QLabel(title_text[:90])
        self.title_label.setObjectName("cardTitle")
        self.title_label.setWordWrap(False)
        self.title_label.setToolTip("双击编辑标题")
        self.title_label.mouseDoubleClickEvent = self._on_title_double_click
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

        # Tags row
        if self.session.tags:
            tags_layout = QHBoxLayout()
            tags_layout.setSpacing(4)
            tags_layout.setContentsMargins(0, 2, 0, 0)
            for tag in self.session.tags:
                tag_label = QLabel(f" {tag} ")
                tag_label.setObjectName("tagPill")
                tags_layout.addWidget(tag_label)
            tags_layout.addStretch()
            layout.addLayout(tags_layout)

    def _on_title_double_click(self, event):
        """Double-click on title to edit it."""
        current = self.session.custom_title or self.session.first_message
        new_title, ok = QInputDialog.getText(
            self, "编辑标题", "输入新标题:", text=current
        )
        if ok and new_title.strip():
            new_title = new_title.strip()
            set_title(self.session.session_id, new_title)
            self.session.custom_title = new_title
            self.title_label.setText(new_title[:90])
            self.title_changed.emit(self.session.session_id)


# ─── Tag Dialog ──────────────────────────────────────────────────────────────

class TagDialog(QDialog):
    """Dialog for managing tags on a session."""

    def __init__(self, session: Session, all_tags: list[str], parent=None):
        super().__init__(parent)
        self.session = session
        self.all_tags = all_tags
        self.result_tags: list[str] = []
        self._build_ui()

    def _build_ui(self):
        self.setWindowTitle("管理标签")
        self.setMinimumWidth(420)
        self.setMinimumHeight(350)
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Session title info
        title_text = self.session.custom_title or self.session.first_message
        info = QLabel(f"📝 {title_text[:60]}")
        info.setWordWrap(True)
        info.setObjectName("cardMeta")
        layout.addWidget(info)

        # Existing tags as checkboxes
        layout.addWidget(QLabel("已有标签（勾选保留，取消移除）："))
        self.tag_checks: dict[str, QCheckBox] = {}
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        self._scroll_widget = QWidget()
        self._tags_layout = QVBoxLayout(self._scroll_widget)
        self._tags_layout.setSpacing(4)
        for tag in self.all_tags:
            cb = QCheckBox(tag)
            cb.setChecked(tag in self.session.tags)
            self.tag_checks[tag] = cb
            self._tags_layout.addWidget(cb)
        self._tags_layout.addStretch()
        scroll.setWidget(self._scroll_widget)
        layout.addWidget(scroll, 1)

        # New tag input
        new_layout = QHBoxLayout()
        self.new_tag_input = QLineEdit()
        self.new_tag_input.setPlaceholderText("输入新标签，回车添加")
        self.new_tag_input.returnPressed.connect(self._add_new_tag)
        add_btn = QPushButton("添加")
        add_btn.clicked.connect(self._add_new_tag)
        new_layout.addWidget(self.new_tag_input, 1)
        new_layout.addWidget(add_btn)
        layout.addLayout(new_layout)

        # OK / Cancel
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("确定")
        ok_btn.setObjectName("primaryBtn")
        ok_btn.clicked.connect(self._accept)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def _add_new_tag(self):
        tag = self.new_tag_input.text().strip()
        if not tag:
            return
        if tag in self.tag_checks:
            self.tag_checks[tag].setChecked(True)
        else:
            cb = QCheckBox(tag)
            cb.setChecked(True)
            self.tag_checks[tag] = cb
            # Insert before the stretch item
            count = self._tags_layout.count()
            self._tags_layout.insertWidget(count - 1, cb)
        self.new_tag_input.clear()

    def _accept(self):
        self.result_tags = [tag for tag, cb in self.tag_checks.items() if cb.isChecked()]
        self.accept()


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
        self.selected_tags: set[str] = set()  # currently checked tags for filtering

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

        # Left panel - project filter + tag filter
        left_panel = QWidget()
        left_panel.setObjectName("projectPanel")
        left_panel.setMinimumWidth(300)
        left_panel.setMaximumWidth(750)

        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        # Tab switcher: Projects / Tags
        tab_bar = QHBoxLayout()
        tab_bar.setContentsMargins(8, 6, 8, 0)
        tab_bar.setSpacing(0)

        self.proj_tab_btn = QPushButton("📁 项目")
        self.proj_tab_btn.setObjectName("leftTabBtn")
        self.proj_tab_btn.setProperty("active", True)
        self.proj_tab_btn.clicked.connect(lambda: self._switch_left_tab("projects"))

        self.tag_tab_btn = QPushButton("🏷 标签")
        self.tag_tab_btn.setObjectName("leftTabBtn")
        self.tag_tab_btn.setProperty("active", False)
        self.tag_tab_btn.clicked.connect(lambda: self._switch_left_tab("tags"))

        tab_bar.addWidget(self.proj_tab_btn)
        tab_bar.addWidget(self.tag_tab_btn)
        left_layout.addLayout(tab_bar)

        # Stacked content
        self.left_stack = QStackedWidget()
        left_layout.addWidget(self.left_stack)

        # -- Page 0: Projects --
        proj_container = QWidget()
        proj_layout = QVBoxLayout(proj_container)
        proj_layout.setContentsMargins(0, 0, 0, 0)
        proj_layout.setSpacing(0)

        self.project_list = QListWidget()
        self.project_list.setObjectName("projectList")
        self.project_list.currentRowChanged.connect(self._on_project_filter)
        proj_layout.addWidget(self.project_list)

        self.left_stack.addWidget(proj_container)

        # -- Page 1: Tags --
        tag_container = QWidget()
        tag_layout = QVBoxLayout(tag_container)
        tag_layout.setContentsMargins(0, 0, 0, 0)
        tag_layout.setSpacing(0)

        self.tag_scroll = QScrollArea()
        self.tag_scroll.setWidgetResizable(True)
        self.tag_scroll.setFrameShape(QFrame.NoFrame)
        self.tag_scroll.setObjectName("tagScroll")
        self.tag_scroll_content = QWidget()
        self.tag_check_layout = QVBoxLayout(self.tag_scroll_content)
        self.tag_check_layout.setContentsMargins(8, 4, 8, 4)
        self.tag_check_layout.setSpacing(2)
        self.tag_check_layout.addStretch()
        self.tag_scroll.setWidget(self.tag_scroll_content)
        tag_layout.addWidget(self.tag_scroll)

        self.left_stack.addWidget(tag_container)

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

        self.tag_btn = QPushButton("🏷 标签")
        self.tag_btn.clicked.connect(self._manage_tags)
        self.tag_btn.setEnabled(False)

        btn_row.addWidget(self.resume_btn)
        btn_row.addWidget(self.copy_btn)
        btn_row.addWidget(self.tag_btn)
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
        splitter.setSizes([450, 950])

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
        self._populate_tags()
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
        self._populate_tags()
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

    # ── Tag Filter Panel ──────────────────────────────────────────────────

    def _populate_tags(self):
        """Populate tag checkboxes in the left panel."""
        # Clear existing widgets (keep the stretch at the end)
        while self.tag_check_layout.count():
            item = self.tag_check_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Collect tag counts from current sessions
        tag_counts: dict[str, int] = {}
        for s in self.sessions:
            for tag in s.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        if not tag_counts:
            no_tags = QLabel("暂无标签")
            no_tags.setObjectName("cardMeta")
            self.tag_check_layout.addWidget(no_tags)
            self.tag_check_layout.addStretch()
            return

        # Sort by count descending
        for tag, count in sorted(tag_counts.items(), key=lambda x: -x[1]):
            cb = QCheckBox(f"{tag}  ({count})")
            cb.setObjectName("tagFilterCb")
            cb.setChecked(tag in self.selected_tags)
            cb.toggled.connect(lambda checked, t=tag: self._on_tag_filter_toggled(t, checked))
            self.tag_check_layout.addWidget(cb)

        self.tag_check_layout.addStretch()

    def _on_tag_filter_toggled(self, tag: str, checked: bool):
        """Handle tag checkbox toggle in filter panel."""
        if checked:
            self.selected_tags.add(tag)
        else:
            self.selected_tags.discard(tag)
        self._on_search(self.search_bar.text())

    def _switch_left_tab(self, tab: str):
        """Switch between projects and tags view in left panel."""
        if tab == "projects":
            self.left_stack.setCurrentIndex(0)
            self.proj_tab_btn.setProperty("active", True)
            self.tag_tab_btn.setProperty("active", False)
        else:
            self.left_stack.setCurrentIndex(1)
            self.proj_tab_btn.setProperty("active", False)
            self.tag_tab_btn.setProperty("active", True)
        # Force style refresh
        self.proj_tab_btn.style().unpolish(self.proj_tab_btn)
        self.proj_tab_btn.style().polish(self.proj_tab_btn)
        self.tag_tab_btn.style().unpolish(self.tag_tab_btn)
        self.tag_tab_btn.style().polish(self.tag_tab_btn)

    # ── Session List ─────────────────────────────────────────────────────

    def _populate_sessions(self):
        self.session_list.clear()

        for s in self.filtered_sessions:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, s.session_id)
            # Taller card if has tags
            height = 100 if s.tags else 80
            item.setSizeHint(QSize(0, height))

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

        # Apply tag filter (AND: session must have ALL checked tags)
        if self.selected_tags:
            self.filtered_sessions = [
                s for s in self.filtered_sessions
                if self.selected_tags.issubset(set(s.tags))
            ]

        self._populate_sessions()
        total = len(self.sessions)
        shown = len(self.filtered_sessions)
        if text or project != "__all__" or self.selected_tags:
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
            self.tag_btn.setEnabled(False)
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
        self.tag_btn.setEnabled(True)

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

    def _manage_tags(self):
        """Open tag management dialog for the current session."""
        if not self.current_session:
            return

        all_tags = get_all_tags()
        dialog = TagDialog(self.current_session, all_tags, self)
        if dialog.exec_() == QDialog.Accepted:
            new_tags = dialog.result_tags
            set_tags(self.current_session.session_id, new_tags)
            self.current_session.tags = new_tags
            # Refresh tag panel and session list
            self._populate_tags()
            self._populate_sessions()
            self.status_label.setText(f"✅ 已更新标签: {', '.join(new_tags) if new_tags else '无标签'}")

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
