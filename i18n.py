"""
CC Session Manager - Internationalization (i18n)
Simple dict-based translation system for Chinese and English.
"""

from dataclasses import dataclass


@dataclass
class Lang:
    """All translatable strings in the app."""

    # Window
    window_title: str

    # Top bar
    app_title: str
    search_placeholder: str
    show_subagents: str
    btn_subagent_off: str
    btn_subagent_on: str
    subagents_tooltip: str
    theme_tooltip: str

    # Left panel tabs
    tab_projects: str
    tab_tags: str

    # Right panel
    preview_header: str
    preview_placeholder: str

    # Action buttons
    btn_resume: str
    btn_copy: str
    btn_tag: str
    btn_delete: str

    # Status
    status_loading: str
    status_loaded: str
    status_loaded_with_sub: str
    status_loaded_hidden_sub: str
    status_filtering: str
    status_no_match: str
    status_copied: str
    status_deleted: str
    status_tag_updated: str

    # Tag dialog
    tag_dialog_title: str
    tag_dialog_existing: str
    tag_dialog_new_placeholder: str
    tag_dialog_add: str
    tag_dialog_ok: str
    tag_dialog_cancel: str

    # Tag filter
    tag_no_tags: str

    # Edit title dialog
    edit_title_dialog: str
    edit_title_prompt: str

    # Resume dialog
    resume_dialog_title: str
    resume_terminal_type: str
    resume_wt: str
    resume_cmd: str
    resume_privilege: str
    resume_user: str
    resume_admin: str
    resume_cancel: str
    resume_open: str

    # Settings dialog
    settings_dialog_title: str
    settings_claude_path: str
    settings_codex_path: str
    settings_opencode_path: str
    settings_browse: str
    settings_reset: str
    settings_save: str
    settings_cancel: str
    settings_restart_hint: str

    # Refresh button
    btn_refresh: str

    # Delete dialog
    delete_title: str
    delete_message: str
    delete_file: str

    # Error
    error_terminal: str
    error_delete: str

    # Time
    time_just_now: str
    time_minutes_ago: str
    time_hours_ago: str
    time_yesterday: str
    time_days_ago: str
    time_weeks_ago: str
    time_unknown: str


ZH = Lang(
    window_title="CC Session Manager",
    app_title="CC Session Manager",
    search_placeholder="搜索对话内容、项目路径、Session ID...",
    show_subagents="显示子代理",
    btn_subagent_off="子代理",
    btn_subagent_on="子代理",
    subagents_tooltip="是否显示 subagents 目录下的会话",
    theme_tooltip="切换亮色/暗色主题",
    tab_projects="📁 项目",
    tab_tags="🏷 标签",
    preview_header="💬 对话预览",
    preview_placeholder="点击上方对话查看预览...",
    btn_resume="▶ 在终端中 Resume",
    btn_copy="📋 复制命令",
    btn_tag="🏷 标签",
    btn_delete="🗑 删除",
    status_loading="⏳ 正在扫描 sessions...",
    status_loaded="✅ 共 {count} 个 sessions",
    status_loaded_with_sub="✅ 共 {count} 个 sessions（含子代理）",
    status_loaded_hidden_sub="✅ 共 {count} 个 sessions（已隐藏 {hidden} 个子代理）",
    status_filtering="🔍 显示 {shown} / {total} 个 sessions",
    status_no_match="没有找到匹配的 sessions",
    status_copied="✅ 已复制: {cmd}",
    status_deleted="✅ Session 已删除",
    status_tag_updated="✅ 已更新标签: {tags}",
    tag_dialog_title="管理标签",
    tag_dialog_existing="已有标签（勾选保留，取消移除）：",
    tag_dialog_new_placeholder="输入新标签，回车添加",
    tag_dialog_add="添加",
    tag_dialog_ok="确定",
    tag_dialog_cancel="取消",
    tag_no_tags="暂无标签",
    edit_title_dialog="编辑标题",
    edit_title_prompt="输入新标题:",
    resume_dialog_title="🖥 打开终端",
    resume_terminal_type="终端类型：",
    resume_wt="Windows Terminal",
    resume_cmd="CMD",
    resume_privilege="运行权限：",
    resume_user="普通用户",
    resume_admin="管理员",
    resume_cancel="取消",
    resume_open="打开",
    settings_dialog_title="⚙ 设置",
    settings_claude_path="Claude Code 路径：",
    settings_codex_path="Codex 路径：",
    settings_opencode_path="OpenCode 路径：",
    settings_browse="浏览",
    settings_reset="恢复默认",
    settings_save="保存",
    settings_cancel="取消",
    settings_restart_hint="路径更改后点击刷新按钮生效",
    btn_refresh="🔄 刷新",
    delete_title="确认删除",
    delete_message="确定要删除这个 session 吗？",
    delete_file="文件:",
    error_terminal="无法打开终端:\n{err}",
    error_delete="删除失败",
    time_just_now="刚刚",
    time_minutes_ago="{n} 分钟前",
    time_hours_ago="{n} 小时前",
    time_yesterday="昨天",
    time_days_ago="{n} 天前",
    time_weeks_ago="{n} 周前",
    time_unknown="未知",
)

EN = Lang(
    window_title="CC Session Manager",
    app_title="CC Session Manager",
    search_placeholder="Search by content, project path, Session ID...",
    show_subagents="Show subagents",
    btn_subagent_off="Subagents",
    btn_subagent_on="Subagents",
    subagents_tooltip="Show sessions from subagents directory",
    theme_tooltip="Toggle light/dark theme",
    tab_projects="📁 Projects",
    tab_tags="🏷 Tags",
    preview_header="💬 Preview",
    preview_placeholder="Click a session above to preview...",
    btn_resume="▶ Resume in Terminal",
    btn_copy="📋 Copy Command",
    btn_tag="🏷 Tags",
    btn_delete="🗑 Delete",
    status_loading="⏳ Scanning sessions...",
    status_loaded="✅ {count} sessions",
    status_loaded_with_sub="✅ {count} sessions (including subagents)",
    status_loaded_hidden_sub="✅ {count} sessions ({hidden} subagents hidden)",
    status_filtering="🔍 Showing {shown} / {total} sessions",
    status_no_match="No matching sessions",
    status_copied="✅ Copied: {cmd}",
    status_deleted="✅ Session deleted",
    status_tag_updated="✅ Tags updated: {tags}",
    tag_dialog_title="Manage Tags",
    tag_dialog_existing="Existing tags (check to keep, uncheck to remove):",
    tag_dialog_new_placeholder="New tag, press Enter to add",
    tag_dialog_add="Add",
    tag_dialog_ok="OK",
    tag_dialog_cancel="Cancel",
    tag_no_tags="No tags yet",
    edit_title_dialog="Edit Title",
    edit_title_prompt="Enter new title:",
    resume_dialog_title="🖥 Open Terminal",
    resume_terminal_type="Terminal:",
    resume_wt="Windows Terminal",
    resume_cmd="CMD",
    resume_privilege="Privilege:",
    resume_user="User",
    resume_admin="Admin",
    resume_cancel="Cancel",
    resume_open="Open",
    settings_dialog_title="⚙ Settings",
    settings_claude_path="Claude Code path:",
    settings_codex_path="Codex path:",
    settings_opencode_path="OpenCode path:",
    settings_browse="Browse",
    settings_reset="Reset Default",
    settings_save="Save",
    settings_cancel="Cancel",
    settings_restart_hint="Click refresh button after changing paths",
    btn_refresh="🔄 Refresh",
    delete_title="Confirm Delete",
    delete_message="Are you sure you want to delete this session?",
    delete_file="File:",
    error_terminal="Cannot open terminal:\n{err}",
    error_delete="Delete Failed",
    time_just_now="just now",
    time_minutes_ago="{n} min ago",
    time_hours_ago="{n} hr ago",
    time_yesterday="yesterday",
    time_days_ago="{n} days ago",
    time_weeks_ago="{n} weeks ago",
    time_unknown="unknown",
)

# Map for easy lookup
LANGS = {"zh": ZH, "en": EN}
