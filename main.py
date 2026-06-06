"""
CC Session Manager - Main Application
A lightweight GUI tool for managing Claude Code sessions.
"""

import sys
import subprocess
import ctypes
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
    QRadioButton,
    QFileDialog,
)
from PyQt5.QtCore import Qt, QSize, QThread, pyqtSignal
from PyQt5.QtGui import QFont

from parser import (
    Session, load_all_sessions, load_session_messages, search_sessions,
    load_all_codex_sessions, load_codex_session_messages,
    load_all_opencode_sessions, load_opencode_session_messages,
)
from metadata import set_title, set_tags, get_all_tags, load_metadata, save_metadata, get_settings, save_settings
from theme import GITHUB_LIGHT, GITHUB_DARK
from i18n import LANGS, Lang


# ─── Helpers ────────────────────────────────────────────────────────────────

def format_time(dt: datetime | None, t: Lang) -> str:
    """Human-readable relative time."""
    if not dt or dt == datetime.min:
        return t.time_unknown
    now = datetime.now(dt.tzinfo)
    diff = now - dt
    if diff.days < 0:
        return dt.strftime("%m/%d %H:%M")
    if diff.days == 0:
        hours = diff.seconds // 3600
        if hours == 0:
            mins = diff.seconds // 60
            return t.time_minutes_ago.format(n=mins) if mins > 0 else t.time_just_now
        return t.time_hours_ago.format(n=hours)
    if diff.days == 1:
        return t.time_yesterday
    if diff.days < 7:
        return t.time_days_ago.format(n=diff.days)
    if diff.days < 30:
        return t.time_weeks_ago.format(n=diff.days // 7)
    return dt.strftime("%Y/%m/%d")


def shorten_path(path: str, max_len: int = 35) -> str:
    """Shorten a file path for display."""
    if len(path) <= max_len:
        return path
    return "..." + path[-(max_len - 3):]


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

    def __init__(self):
        super().__init__()
        self.tool = "claude"

    def run(self):
        if self.tool == "codex":
            sessions = load_all_codex_sessions()
        elif self.tool == "opencode":
            sessions = load_all_opencode_sessions()
        else:
            sessions = load_all_sessions()
        self.loaded.emit(sessions)


# ─── Session Card Widget ────────────────────────────────────────────────────

class SessionCard(QWidget):
    """A single session card displayed in the session list."""

    title_changed = pyqtSignal(str)

    def __init__(self, session: Session, lang: Lang, parent=None):
        super().__init__(parent)
        self.session = session
        self.lang = lang
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(3)

        title_text = self.session.custom_title or self.session.first_message
        self.title_label = QLabel(title_text[:90])
        self.title_label.setObjectName("cardTitle")
        self.title_label.setWordWrap(False)
        self.title_label.setToolTip(self.lang.edit_title_dialog)
        self.title_label.mouseDoubleClickEvent = self._on_title_double_click
        layout.addWidget(self.title_label)

        time_str = format_time(self.session.last_active, self.lang)
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
        current = self.session.custom_title or self.session.first_message
        new_title, ok = QInputDialog.getText(
            self, self.lang.edit_title_dialog, self.lang.edit_title_prompt, text=current
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

    def __init__(self, session: Session, all_tags: list[str], lang: Lang, parent=None):
        super().__init__(parent)
        self.session = session
        self.all_tags = all_tags
        self.lang = lang
        self.result_tags: list[str] = []
        self._build_ui()

    def _build_ui(self):
        self.setWindowTitle(self.lang.tag_dialog_title)
        self.setMinimumWidth(420)
        self.setMinimumHeight(350)
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title_text = self.session.custom_title or self.session.first_message
        info = QLabel(f"📝 {title_text[:60]}")
        info.setWordWrap(True)
        info.setObjectName("cardMeta")
        layout.addWidget(info)

        layout.addWidget(QLabel(self.lang.tag_dialog_existing))
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

        new_layout = QHBoxLayout()
        self.new_tag_input = QLineEdit()
        self.new_tag_input.setPlaceholderText(self.lang.tag_dialog_new_placeholder)
        self.new_tag_input.returnPressed.connect(self._add_new_tag)
        add_btn = QPushButton(self.lang.tag_dialog_add)
        add_btn.clicked.connect(self._add_new_tag)
        new_layout.addWidget(self.new_tag_input, 1)
        new_layout.addWidget(add_btn)
        layout.addLayout(new_layout)

        btn_layout = QHBoxLayout()
        ok_btn = QPushButton(self.lang.tag_dialog_ok)
        ok_btn.setObjectName("primaryBtn")
        ok_btn.clicked.connect(self._accept)
        cancel_btn = QPushButton(self.lang.tag_dialog_cancel)
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
            count = self._tags_layout.count()
            self._tags_layout.insertWidget(count - 1, cb)
        self.new_tag_input.clear()

    def _accept(self):
        self.result_tags = [tag for tag, cb in self.tag_checks.items() if cb.isChecked()]
        self.accept()


# ─── Resume Dialog ──────────────────────────────────────────────────────────

class ResumeDialog(QDialog):
    """Dialog for choosing terminal type and privilege level."""

    def __init__(self, lang: Lang, last_terminal: str, last_admin: bool, parent=None):
        super().__init__(parent)
        self.lang = lang
        self.terminal = last_terminal  # "wt" or "cmd"
        self.as_admin = last_admin
        self._build_ui()

    def _build_ui(self):
        t = self.lang
        self.setWindowTitle(t.resume_dialog_title)
        self.setMinimumWidth(420)
        self.setFixedHeight(300)
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Terminal type
        layout.addWidget(QLabel(t.resume_terminal_type))
        term_row = QHBoxLayout()
        term_row.setSpacing(8)

        self.wt_btn = QPushButton(t.resume_wt)
        self.wt_btn.setObjectName("leftTabBtn")
        self.wt_btn.setProperty("active", self.terminal == "wt")
        self.wt_btn.clicked.connect(lambda: self._select_terminal("wt"))

        self.cmd_btn = QPushButton(t.resume_cmd)
        self.cmd_btn.setObjectName("leftTabBtn")
        self.cmd_btn.setProperty("active", self.terminal == "cmd")
        self.cmd_btn.clicked.connect(lambda: self._select_terminal("cmd"))

        term_row.addWidget(self.wt_btn)
        term_row.addWidget(self.cmd_btn)
        term_row.addStretch()
        layout.addLayout(term_row)

        # Privilege
        layout.addWidget(QLabel(t.resume_privilege))
        priv_row = QHBoxLayout()
        priv_row.setSpacing(16)

        self.user_radio = QRadioButton(t.resume_user)
        self.admin_radio = QRadioButton(t.resume_admin)
        if self.as_admin:
            self.admin_radio.setChecked(True)
        else:
            self.user_radio.setChecked(True)

        priv_row.addWidget(self.user_radio)
        priv_row.addWidget(self.admin_radio)
        priv_row.addStretch()
        layout.addLayout(priv_row)

        layout.addStretch()

        # Buttons
        btn_row = QHBoxLayout()
        cancel_btn = QPushButton(t.resume_cancel)
        cancel_btn.clicked.connect(self.reject)
        open_btn = QPushButton(t.resume_open)
        open_btn.setObjectName("primaryBtn")
        open_btn.clicked.connect(self._accept)
        btn_row.addStretch()
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(open_btn)
        layout.addLayout(btn_row)

    def _select_terminal(self, term: str):
        self.terminal = term
        self.wt_btn.setProperty("active", term == "wt")
        self.cmd_btn.setProperty("active", term == "cmd")
        self.wt_btn.style().unpolish(self.wt_btn)
        self.wt_btn.style().polish(self.wt_btn)
        self.cmd_btn.style().unpolish(self.cmd_btn)
        self.cmd_btn.style().polish(self.cmd_btn)

    def _accept(self):
        self.as_admin = self.admin_radio.isChecked()
        self.accept()


# ─── Settings Dialog ────────────────────────────────────────────────────────

class SettingsDialog(QDialog):
    """Dialog for configuring custom installation paths."""

    def __init__(self, lang: Lang, parent=None):
        super().__init__(parent)
        self.lang = lang
        self.settings = get_settings()
        self._build_ui()

    def _build_ui(self):
        t = self.lang
        self.setWindowTitle(t.settings_dialog_title)
        self.setMinimumWidth(520)
        self.setMaximumWidth(600)
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 16)

        from pathlib import Path
        home = str(Path.home())

        # Claude Code section
        self.claude_edit = self._card_section(
            layout, "🟠 Claude Code",
            t.settings_claude_path,
            self.settings.get("claude_path", ""),
            f"{home}\\.claude\\projects"
        )

        # Codex section
        self.codex_edit = self._card_section(
            layout, "🟢 Codex",
            t.settings_codex_path,
            self.settings.get("codex_path", ""),
            f"{home}\\.codex\\sessions"
        )

        # OpenCode section
        self.opencode_edit = self._card_section(
            layout, "🔵 OpenCode",
            t.settings_opencode_path,
            self.settings.get("opencode_path", ""),
            f"{home}\\.local\\share\\opencode\\storage\\session"
        )

        # Hint
        hint = QLabel(t.settings_restart_hint)
        hint.setObjectName("cardMeta")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        layout.addStretch()

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        reset_btn = QPushButton(t.settings_reset)
        reset_btn.clicked.connect(self._reset_defaults)
        cancel_btn = QPushButton(t.settings_cancel)
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton(t.settings_save)
        save_btn.setObjectName("primaryBtn")
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(reset_btn)
        btn_row.addStretch()
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    def _card_section(self, parent_layout, title, label_text, current_value, default_path) -> QLineEdit:
        """Create a card-style section with title, label, input + browse button."""
        card = QFrame()
        card.setObjectName("settingsCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 10, 14, 10)
        card_layout.setSpacing(6)

        # Section title
        header = QLabel(title)
        header.setObjectName("cardTitle")
        card_layout.addWidget(header)

        # Label
        label = QLabel(label_text)
        label.setObjectName("cardMeta")
        card_layout.addWidget(label)

        # Input + browse row
        row = QHBoxLayout()
        row.setSpacing(8)
        edit = QLineEdit(current_value)
        edit.setPlaceholderText(f"默认: {default_path}")
        edit.setMinimumHeight(40)
        browse_btn = QPushButton(self.lang.settings_browse)
        browse_btn.setFixedWidth(80)
        browse_btn.clicked.connect(lambda: self._browse(edit, title))
        row.addWidget(edit, 1)
        row.addWidget(browse_btn)
        card_layout.addLayout(row)

        parent_layout.addWidget(card)
        return edit

    def _browse(self, edit: QLineEdit, hint: str):
        path = QFileDialog.getExistingDirectory(self, hint)
        if path:
            edit.setText(path)

    def _reset_defaults(self):
        self.claude_edit.clear()
        self.codex_edit.clear()
        self.opencode_edit.clear()

    def _save(self):
        self.settings = {
            "claude_path": self.claude_edit.text().strip(),
            "codex_path": self.codex_edit.text().strip(),
            "opencode_path": self.opencode_edit.text().strip(),
        }
        save_settings(self.settings)
        self.accept()


# ─── Main Window ────────────────────────────────────────────────────────────

class CCSessionManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.sessions: list[Session] = []
        self.all_sessions: list[Session] = []
        self.filtered_sessions: list[Session] = []
        self.current_session: Session | None = None
        self.is_dark = False
        self.show_subagents = False
        self.selected_tags: set[str] = set()
        self.lang_code = "zh"
        self.t = LANGS[self.lang_code]
        self.current_tool = "claude"  # "claude", "codex", or "opencode"

        self._init_ui()
        self._load_sessions()

    # ── UI Setup ─────────────────────────────────────────────────────────

    def _init_ui(self):
        t = self.t
        self.setWindowTitle(t.window_title)
        self.setMinimumSize(1200, 750)
        self.resize(1400, 900)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Unified top bar (tabs + search + actions) ───────────────────
        top_bar = QWidget()
        top_bar.setObjectName("topBar")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(16, 8, 16, 8)

        # Left: tool tabs (card-style)
        self.claude_tab = QPushButton("Claude Code")
        self.claude_tab.setObjectName("toolTabBtn")
        self.claude_tab.setProperty("active", True)
        self.claude_tab.clicked.connect(lambda: self._switch_tool("claude"))

        self.codex_tab = QPushButton("Codex")
        self.codex_tab.setObjectName("toolTabBtn")
        self.codex_tab.setProperty("active", False)
        self.codex_tab.clicked.connect(lambda: self._switch_tool("codex"))

        self.opencode_tab = QPushButton("OpenCode")
        self.opencode_tab.setObjectName("toolTabBtn")
        self.opencode_tab.setProperty("active", False)
        self.opencode_tab.clicked.connect(lambda: self._switch_tool("opencode"))

        # Center: search
        self.search_bar = QLineEdit()
        self.search_bar.setObjectName("searchBar")
        self.search_bar.setPlaceholderText(t.search_placeholder)
        self.search_bar.textChanged.connect(self._on_search)

        # Right: utility buttons
        self.subagent_btn = QPushButton(t.btn_subagent_off)
        self.subagent_btn.setObjectName("subagentBtn")
        self.subagent_btn.setToolTip(t.subagents_tooltip)
        self.subagent_btn.setProperty("active", False)
        self.subagent_btn.clicked.connect(self._toggle_subagents)

        self.refresh_btn = QPushButton(t.btn_refresh)
        self.refresh_btn.setObjectName("refreshBtn")
        self.refresh_btn.setToolTip("刷新会话列表")
        self.refresh_btn.clicked.connect(self._load_sessions)

        self.settings_btn = QPushButton("⚙")
        self.settings_btn.setObjectName("settingsBtn")
        self.settings_btn.setToolTip("设置")
        self.settings_btn.clicked.connect(self._open_settings)

        self.lang_btn = QPushButton("EN")
        self.lang_btn.setObjectName("langBtn")
        self.lang_btn.setFixedSize(56, 48)
        self.lang_btn.setToolTip("Switch language / 切换语言")
        self.lang_btn.clicked.connect(self._toggle_lang)

        self.theme_btn = QPushButton("🌙")
        self.theme_btn.setObjectName("themeBtn")
        self.theme_btn.setFixedSize(56, 48)
        self.theme_btn.setToolTip(t.theme_tooltip)
        self.theme_btn.clicked.connect(self._toggle_theme)

        # Layout: [Tabs] spacing [Search(flex)] spacing [Buttons]
        top_layout.addWidget(self.claude_tab)
        top_layout.addWidget(self.codex_tab)
        top_layout.addWidget(self.opencode_tab)
        top_layout.addSpacing(16)
        top_layout.addWidget(self.search_bar, 1)
        top_layout.addSpacing(12)
        top_layout.addWidget(self.subagent_btn)
        top_layout.addWidget(self.refresh_btn)
        top_layout.addWidget(self.settings_btn)
        top_layout.addWidget(self.lang_btn)
        top_layout.addWidget(self.theme_btn)

        root.addWidget(top_bar)

        # ── Body: splitter (left + right) ───────────────────────────────
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        # Left panel
        left_panel = QWidget()
        left_panel.setObjectName("projectPanel")
        left_panel.setMinimumWidth(300)
        left_panel.setMaximumWidth(750)

        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        # Tab switcher
        tab_bar = QHBoxLayout()
        tab_bar.setContentsMargins(8, 6, 8, 0)
        tab_bar.setSpacing(0)

        self.proj_tab_btn = QPushButton(t.tab_projects)
        self.proj_tab_btn.setObjectName("leftTabBtn")
        self.proj_tab_btn.setProperty("active", True)
        self.proj_tab_btn.clicked.connect(lambda: self._switch_left_tab("projects"))

        self.tag_tab_btn = QPushButton(t.tab_tags)
        self.tag_tab_btn.setObjectName("leftTabBtn")
        self.tag_tab_btn.setProperty("active", False)
        self.tag_tab_btn.clicked.connect(lambda: self._switch_left_tab("tags"))

        tab_bar.addWidget(self.proj_tab_btn)
        tab_bar.addWidget(self.tag_tab_btn)
        left_layout.addLayout(tab_bar)

        self.left_stack = QStackedWidget()
        left_layout.addWidget(self.left_stack)

        # Page 0: Projects
        proj_container = QWidget()
        proj_layout = QVBoxLayout(proj_container)
        proj_layout.setContentsMargins(0, 0, 0, 0)
        proj_layout.setSpacing(0)

        self.project_list = QListWidget()
        self.project_list.setObjectName("projectList")
        self.project_list.currentRowChanged.connect(self._on_project_filter)
        proj_layout.addWidget(self.project_list)

        self.left_stack.addWidget(proj_container)

        # Page 1: Tags
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

        self.session_list = QListWidget()
        self.session_list.setObjectName("sessionList")
        self.session_list.currentRowChanged.connect(self._on_session_select)
        right_layout.addWidget(self.session_list, 1)

        self.preview_header = QLabel(t.preview_header)
        self.preview_header.setObjectName("sectionLabel")
        right_layout.addWidget(self.preview_header)

        self.preview = QTextBrowser()
        self.preview.setObjectName("previewPanel")
        self.preview.setOpenExternalLinks(False)
        self.preview.setMaximumHeight(280)
        self.preview.setPlaceholderText(t.preview_placeholder)
        right_layout.addWidget(self.preview)

        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.resume_btn = QPushButton(t.btn_resume)
        self.resume_btn.setObjectName("primaryBtn")
        self.resume_btn.clicked.connect(self._resume_session)
        self.resume_btn.setEnabled(False)

        self.copy_btn = QPushButton(t.btn_copy)
        self.copy_btn.clicked.connect(self._copy_resume_cmd)
        self.copy_btn.setEnabled(False)

        self.tag_btn = QPushButton(t.btn_tag)
        self.tag_btn.clicked.connect(self._manage_tags)
        self.tag_btn.setEnabled(False)

        btn_row.addWidget(self.resume_btn)
        btn_row.addWidget(self.copy_btn)
        btn_row.addWidget(self.tag_btn)
        btn_row.addStretch()

        self.delete_btn = QPushButton(t.btn_delete)
        self.delete_btn.setObjectName("dangerBtn")
        self.delete_btn.clicked.connect(self._delete_session)
        self.delete_btn.setEnabled(False)
        btn_row.addWidget(self.delete_btn)

        right_layout.addLayout(btn_row)

        self.status_label = QLabel(t.status_loading)
        self.status_label.setObjectName("statusLabel")
        right_layout.addWidget(self.status_label)

        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([450, 950])

        root.addWidget(splitter, 1)
        self._apply_theme()

    # ── Language Toggle ──────────────────────────────────────────────────

    def _toggle_lang(self):
        self.lang_code = "en" if self.lang_code == "zh" else "zh"
        self.t = LANGS[self.lang_code]
        self.lang_btn.setText("中" if self.lang_code == "en" else "EN")
        self._refresh_ui_text()

    def _switch_tool(self, tool: str):
        """Switch between Claude Code, Codex, and OpenCode."""
        if tool == self.current_tool:
            return
        self.current_tool = tool
        self.claude_tab.setProperty("active", tool == "claude")
        self.codex_tab.setProperty("active", tool == "codex")
        self.opencode_tab.setProperty("active", tool == "opencode")
        self.claude_tab.style().unpolish(self.claude_tab)
        self.claude_tab.style().polish(self.claude_tab)
        self.codex_tab.style().unpolish(self.codex_tab)
        self.codex_tab.style().polish(self.codex_tab)
        self.opencode_tab.style().unpolish(self.opencode_tab)
        self.opencode_tab.style().polish(self.opencode_tab)
        # Show/hide subagent button (only for Claude Code)
        self.subagent_btn.setVisible(tool == "claude")
        self._load_sessions()

    def _refresh_ui_text(self):
        """Update all visible text after language switch."""
        t = self.t

        self.setWindowTitle(t.window_title)
        self.search_bar.setPlaceholderText(t.search_placeholder)
        self.theme_btn.setToolTip(t.theme_tooltip)
        self.subagent_btn.setToolTip(t.subagents_tooltip)
        self.subagent_btn.setText(t.btn_subagent_on if self.show_subagents else t.btn_subagent_off)
        self.proj_tab_btn.setText(t.tab_projects)
        self.tag_tab_btn.setText(t.tab_tags)
        self.preview_header.setText(t.preview_header)
        self.preview.setPlaceholderText(t.preview_placeholder)
        self.resume_btn.setText(t.btn_resume)
        self.copy_btn.setText(t.btn_copy)
        self.tag_btn.setText(t.btn_tag)
        self.delete_btn.setText(t.btn_delete)

        # Refresh dynamic content
        self._populate_projects()
        self._populate_tags()
        self._populate_sessions()
        self._update_status()

    def _update_status(self):
        """Refresh status label based on current state."""
        t = self.t
        total = len(self.sessions)
        shown = len(self.filtered_sessions)
        text = self.search_bar.text()
        project = self._get_current_project()

        if shown == 0 and (text or project != "__all__" or self.selected_tags):
            self.status_label.setText(t.status_no_match)
        elif text or project != "__all__" or self.selected_tags:
            self.status_label.setText(t.status_filtering.format(shown=shown, total=total))
        else:
            if self.show_subagents:
                self.status_label.setText(t.status_loaded_with_sub.format(count=total))
            else:
                sub_count = len(self.all_sessions) - total
                self.status_label.setText(t.status_loaded_hidden_sub.format(count=total, hidden=sub_count))

    # ── Data Loading ─────────────────────────────────────────────────────

    def _load_sessions(self):
        self.status_label.setText(self.t.status_loading)
        self._loader = SessionLoader()
        self._loader.tool = self.current_tool
        self._loader.loaded.connect(self._on_sessions_loaded)
        self._loader.start()

    def _on_sessions_loaded(self, sessions: list[Session]):
        self.all_sessions = sessions
        self.sessions = self._filter_subagents(sessions)
        self.filtered_sessions = self.sessions.copy()
        self._populate_projects()
        self._populate_tags()
        self._populate_sessions()
        self._update_status()

    def _filter_subagents(self, sessions: list[Session]) -> list[Session]:
        if self.show_subagents:
            return sessions
        return [s for s in sessions if s.project_key != "subagents"]

    def _toggle_subagents(self):
        self.show_subagents = not self.show_subagents
        t = self.t
        if self.show_subagents:
            self.subagent_btn.setText(t.btn_subagent_on)
            self.subagent_btn.setProperty("active", True)
        else:
            self.subagent_btn.setText(t.btn_subagent_off)
            self.subagent_btn.setProperty("active", False)
        self.subagent_btn.style().unpolish(self.subagent_btn)
        self.subagent_btn.style().polish(self.subagent_btn)
        self.sessions = self._filter_subagents(self.all_sessions)
        self._on_search(self.search_bar.text())
        self._populate_projects()
        self._populate_tags()
        self._populate_sessions()
        self._update_status()

    # ── Project List ─────────────────────────────────────────────────────

    def _populate_projects(self):
        self.project_list.blockSignals(True)
        self.project_list.clear()

        counts: dict[str, int] = {}
        display_names: dict[str, str] = {}
        for s in self.sessions:
            key = s.project_key
            counts[key] = counts.get(key, 0) + 1
            if key not in display_names or len(s.project_dir) < len(display_names[key]):
                display_names[key] = s.project_dir

        all_item = QListWidgetItem(f"📋 全部  ({len(self.sessions)})")
        all_item.setData(Qt.UserRole, "__all__")
        self.project_list.addItem(all_item)

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
        while self.tag_check_layout.count():
            item = self.tag_check_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        tag_counts: dict[str, int] = {}
        for s in self.sessions:
            for tag in s.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        if not tag_counts:
            no_tags = QLabel(self.t.tag_no_tags)
            no_tags.setObjectName("cardMeta")
            self.tag_check_layout.addWidget(no_tags)
            self.tag_check_layout.addStretch()
            return

        for tag, count in sorted(tag_counts.items(), key=lambda x: -x[1]):
            cb = QCheckBox(f"{tag}  ({count})")
            cb.setObjectName("tagFilterCb")
            cb.setChecked(tag in self.selected_tags)
            cb.toggled.connect(lambda checked, t=tag: self._on_tag_filter_toggled(t, checked))
            self.tag_check_layout.addWidget(cb)

        self.tag_check_layout.addStretch()

    def _on_tag_filter_toggled(self, tag: str, checked: bool):
        if checked:
            self.selected_tags.add(tag)
        else:
            self.selected_tags.discard(tag)
        self._on_search(self.search_bar.text())

    def _switch_left_tab(self, tab: str):
        if tab == "projects":
            self.left_stack.setCurrentIndex(0)
            self.proj_tab_btn.setProperty("active", True)
            self.tag_tab_btn.setProperty("active", False)
        else:
            self.left_stack.setCurrentIndex(1)
            self.proj_tab_btn.setProperty("active", False)
            self.tag_tab_btn.setProperty("active", True)
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
            height = 100 if s.tags else 80
            item.setSizeHint(QSize(0, height))

            card = SessionCard(s, self.t)
            self.session_list.addItem(item)
            self.session_list.setItemWidget(item, card)

        if not self.filtered_sessions:
            self.status_label.setText(self.t.status_no_match)

    # ── Search & Filter ──────────────────────────────────────────────────

    def _get_current_project(self) -> str:
        item = self.project_list.currentItem()
        if item:
            return item.data(Qt.UserRole) or "__all__"
        return "__all__"

    def _on_search(self, text: str):
        project = self._get_current_project()
        self.filtered_sessions = search_sessions(self.sessions, text, project)

        if self.selected_tags:
            self.filtered_sessions = [
                s for s in self.filtered_sessions
                if self.selected_tags.issubset(set(s.tags))
            ]

        self._populate_sessions()
        self._update_status()

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

        if self.current_tool == "codex":
            messages = load_codex_session_messages(session.file_path)
        elif self.current_tool == "opencode":
            messages = load_opencode_session_messages(session.file_path)
        else:
            messages = load_session_messages(session.file_path)

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
            if len(content_html) > 600:
                content_html = content_html[:600] + "..."

            if role == "user":
                html_parts.append(
                    f'<div style="margin: 8px 0; padding: 8px 12px; '
                    f'background: {user_bg}; border: 1px solid {border_color}; '
                    f'border-radius: 8px;">'
                    f'<b style="font-size: 22px; color: {dim_color};">👤 You</b><br>'
                    f'<span style="font-size: 26px;">{content_html}</span></div>'
                )
            else:
                html_parts.append(
                    f'<div style="margin: 8px 0; padding: 8px 12px;">'
                    f'<b style="font-size: 22px; color: {dim_color};">🤖 Claude</b><br>'
                    f'<span style="font-size: 26px;">{content_html}</span></div>'
                )

        if not messages:
            html_parts.append(f'<i style="color: {dim_color};">No messages</i>')

        if len(messages) > 30:
            html_parts.append(
                f'<div style="text-align: center; color: {dim_color}; padding: 8px;">'
                f"... +{len(messages) - 30} more messages</div>"
            )

        html_parts.append("</div>")
        self.preview.setHtml("".join(html_parts))

        self.resume_btn.setEnabled(True)
        self.copy_btn.setEnabled(True)
        self.delete_btn.setEnabled(True)
        self.tag_btn.setEnabled(True)

    # ── Actions ──────────────────────────────────────────────────────────

    def _resume_session(self):
        if not self.current_session:
            return

        s = self.current_session
        if self.current_tool == "codex":
            cmd = f"codex resume {s.session_id}"
        elif self.current_tool == "opencode":
            cmd = f"opencode --session {s.session_id}"
        else:
            cmd = f"claude --resume {s.session_id}"
        cwd = s.cwd if s.cwd and Path(s.cwd).exists() else str(Path.home())

        # Load last choices
        meta = load_metadata()
        last_terminal = meta.get("_resume_terminal", "wt")
        last_admin = meta.get("_resume_admin", False)

        dialog = ResumeDialog(self.t, last_terminal, last_admin, self)
        if dialog.exec_() != QDialog.Accepted:
            return

        terminal = dialog.terminal
        as_admin = dialog.as_admin

        # Save choices for next time
        meta = load_metadata()
        meta["_resume_terminal"] = terminal
        meta["_resume_admin"] = as_admin
        save_metadata(meta)

        try:
            if terminal == "wt":
                if as_admin:
                    # Run wt.exe as admin via ShellExecute
                    args = f'-d "{cwd}" -- cmd.exe /k {cmd}'
                    ctypes.windll.shell32.ShellExecuteW(
                        None, "runas", "wt.exe", args, cwd, 1
                    )
                else:
                    subprocess.Popen(
                        ["wt.exe", "-d", cwd, "--", "cmd.exe", "/k", cmd],
                        cwd=cwd,
                    )
            else:  # cmd
                if as_admin:
                    args = f'/k cd /d "{cwd}" && {cmd}'
                    ctypes.windll.shell32.ShellExecuteW(
                        None, "runas", "cmd.exe", args, cwd, 1
                    )
                else:
                    subprocess.Popen(
                        ["cmd.exe", "/k", f'cd /d "{cwd}" && {cmd}'],
                        cwd=cwd,
                    )
        except Exception as e:
            QMessageBox.warning(self, "Error", self.t.error_terminal.format(err=e))

    def _copy_resume_cmd(self):
        if not self.current_session:
            return

        if self.current_tool == "codex":
            cmd = f"codex resume {self.current_session.session_id}"
        elif self.current_tool == "opencode":
            cmd = f"opencode --session {self.current_session.session_id}"
        else:
            cmd = f"claude --resume {self.current_session.session_id}"
        QApplication.clipboard().setText(cmd)
        self.status_label.setText(self.t.status_copied.format(cmd=cmd))

    def _delete_session(self):
        if not self.current_session:
            return

        s = self.current_session
        t = self.t
        reply = QMessageBox.question(
            self,
            t.delete_title,
            f"{t.delete_message}\n\n"
            f"{s.first_message[:80]}\n\n"
            f"{t.delete_file} {s.session_id}.jsonl",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            try:
                Path(s.file_path).unlink()
                self.sessions = [x for x in self.sessions if x.session_id != s.session_id]
                self._on_sessions_loaded(self.sessions)
                self.status_label.setText(t.status_deleted)
            except Exception as e:
                QMessageBox.warning(self, t.error_delete, str(e))

    def _manage_tags(self):
        if not self.current_session:
            return

        all_tags = get_all_tags()
        dialog = TagDialog(self.current_session, all_tags, self.t, self)
        if dialog.exec_() == QDialog.Accepted:
            new_tags = dialog.result_tags
            set_tags(self.current_session.session_id, new_tags)
            self.current_session.tags = new_tags
            self._populate_tags()
            self._populate_sessions()
            tags_str = ", ".join(new_tags) if new_tags else "—"
            self.status_label.setText(self.t.status_tag_updated.format(tags=tags_str))

    # ── Theme ────────────────────────────────────────────────────────────

    def _toggle_theme(self):
        self.is_dark = not self.is_dark
        self.theme_btn.setText("☀️" if self.is_dark else "🌙")
        self._apply_theme()
        if self.current_session:
            row = self.session_list.currentRow()
            if row >= 0:
                self._on_session_select(row)

    def _apply_theme(self):
        theme = GITHUB_DARK if self.is_dark else GITHUB_LIGHT
        self.setStyleSheet(theme)

    def _open_settings(self):
        dialog = SettingsDialog(self.t, self)
        if dialog.exec_() == QDialog.Accepted:
            self.status_label.setText("✅ 设置已保存，正在刷新...")
            self._load_sessions()


# ─── Entry Point ────────────────────────────────────────────────────────────

def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 18))

    window = CCSessionManager()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
