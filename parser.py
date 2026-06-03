"""
CC Session Manager - Session JSONL Parser
Parses Claude Code session files stored in ~/.claude/projects/
"""

import json
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Session:
    session_id: str
    file_path: str
    project_key: str        # raw encoded dir name, for grouping
    project_dir: str        # display name derived from cwd, e.g. D:\workspace\teaching-book-agent
    first_message: str = ""
    timestamp: Optional[datetime] = None
    last_active: Optional[datetime] = None
    cwd: str = ""
    model: str = ""
    message_count: int = 0
    total_tokens: int = 0
    size_kb: float = 0.0
    custom_title: str = ""
    tags: list = field(default_factory=list)



def parse_timestamp(ts_str: str) -> datetime:
    """Parse ISO timestamp string."""
    try:
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    except Exception:
        return datetime.min


def extract_user_content(content) -> str:
    """Extract text from user message content (can be str or list)."""
    if isinstance(content, str):
        # Strip local-command-caveat tags
        if "<local-command-caveat>" in content:
            return content.split("<local-command-caveat>")[0].strip()
        return content
    if isinstance(content, list):
        texts = []
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                texts.append(part.get("text", ""))
            elif isinstance(part, str):
                texts.append(part)
        return " ".join(texts)
    return ""


def derive_project_path(cwd: str) -> str:
    """Derive a display-friendly project path from cwd."""
    if not cwd:
        return "未知项目"
    # Use the full cwd path as-is; it's already the real path
    return cwd


def parse_session_metadata(file_path: str) -> Optional[Session]:
    """
    Fast parse: read only the first ~80 lines to extract metadata.
    Full message parsing happens on-demand when user selects a session.
    """
    path = Path(file_path)
    session_id = path.stem
    project_key = path.parent.name  # encoded dir name, used as grouping key

    session = Session(
        session_id=session_id,
        file_path=str(path),
        project_key=project_key,
        project_dir="",  # will be derived from cwd after parsing
        size_kb=round(path.stat().st_size / 1024, 1),
    )

    first_user_found = False
    ai_title_found = False

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                # After finding the first user message + ai-title, read a bit more
                if i > 80 and first_user_found and ai_title_found:
                    break

                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue

                msg_type = obj.get("type", "")

                if msg_type == "ai-title":
                    title = obj.get("aiTitle", "").strip()
                    if title:
                        session.first_message = title[:150]
                        ai_title_found = True

                elif msg_type == "user":
                    session.message_count += 1
                    content = extract_user_content(
                        obj.get("message", {}).get("content", "")
                    )

                    if not first_user_found:
                        # Only use first message as title if no ai-title found yet
                        if not ai_title_found:
                            session.first_message = content[:150].replace("\n", " ").strip()
                        ts = obj.get("timestamp")
                        if ts:
                            session.timestamp = parse_timestamp(ts)
                            session.last_active = session.timestamp
                        session.cwd = obj.get("cwd", "")
                        first_user_found = True
                    else:
                        ts = obj.get("timestamp")
                        if ts:
                            session.last_active = parse_timestamp(ts)

                elif msg_type == "assistant":
                    msg = obj.get("message", {})
                    if not session.model:
                        session.model = msg.get("model", "")
                    usage = msg.get("usage", {})
                    session.total_tokens += (
                        usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
                    )
                    ts = obj.get("timestamp")
                    if ts:
                        session.last_active = parse_timestamp(ts)

    except Exception:
        return None

    # Skip sessions with no user messages
    if not session.first_message:
        return None

    # Derive project display name from cwd
    session.project_dir = derive_project_path(session.cwd)

    return session


def load_session_messages(file_path: str) -> list[tuple[str, str]]:
    """Load all user/assistant messages from a session for preview."""
    messages = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue

                msg_type = obj.get("type", "")

                if msg_type == "user":
                    content = extract_user_content(
                        obj.get("message", {}).get("content", "")
                    )
                    if content:
                        messages.append(("user", content[:2000]))

                elif msg_type == "assistant":
                    contents = obj.get("message", {}).get("content", [])
                    if isinstance(contents, list):
                        for c in contents:
                            if isinstance(c, dict) and c.get("type") == "text":
                                text = c.get("text", "")
                                if text:
                                    messages.append(("assistant", text[:2000]))
                                break
    except Exception:
        pass

    return messages


def load_all_sessions() -> list[Session]:
    """Load metadata for all sessions across all projects."""
    projects_dir = Path.home() / ".claude" / "projects"
    if not projects_dir.exists():
        return []

    sessions = []
    for jsonl_file in projects_dir.rglob("*.jsonl"):
        session = parse_session_metadata(str(jsonl_file))
        if session:
            sessions.append(session)

    # Load user-customized metadata (titles & tags)
    from metadata import load_metadata
    meta = load_metadata()
    for s in sessions:
        entry = meta.get(s.session_id, {})
        custom_title = entry.get("title", "")
        if custom_title:
            s.custom_title = custom_title
        s.tags = entry.get("tags", [])

    # Sort by last_active, most recent first
    sessions.sort(key=lambda s: s.last_active or datetime.min, reverse=True)
    return sessions


def search_sessions(
    sessions: list[Session],
    query: str,
    project: str = "__all__",
) -> list[Session]:
    """Filter sessions by search query and project."""
    results = []
    q = query.lower().strip() if query else ""

    for s in sessions:
        # Project filter (use project_key for grouping)
        if project != "__all__" and s.project_key != project:
            continue

        # Text search
        if q:
            searchable = (
                f"{s.first_message} {s.cwd} {s.session_id} {s.project_dir} {s.model}"
            ).lower()
            if q not in searchable:
                continue

        results.append(s)

    return results
