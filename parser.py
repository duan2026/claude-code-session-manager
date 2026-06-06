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
        if not isinstance(entry, dict):
            entry = {}
        custom_title = entry.get("title", "")
        if custom_title:
            s.custom_title = custom_title
        s.tags = entry.get("tags", [])

    # Sort by last_active, most recent first
    sessions.sort(key=lambda s: s.last_active or datetime.min, reverse=True)
    return sessions


# ─── OpenCode Parser ───────────────────────────────────────────────────────

OPENCODE_DIR = Path.home() / ".local" / "share" / "opencode" / "storage"


def parse_opencode_session(file_path: str) -> Optional[Session]:
    """Parse an OpenCode session JSON file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return None

    session_id = data.get("id", "")
    if not session_id:
        return None

    title = data.get("title", "")
    directory = data.get("directory", "")
    project_id = data.get("projectID", "")
    time_info = data.get("time", {})
    size_kb = round(Path(file_path).stat().st_size / 1024, 1)

    # Parse timestamps (milliseconds epoch)
    created_ms = time_info.get("created", 0)
    updated_ms = time_info.get("updated", 0)

    try:
        timestamp = datetime.fromtimestamp(created_ms / 1000) if created_ms else None
        last_active = datetime.fromtimestamp(updated_ms / 1000) if updated_ms else None
    except Exception:
        timestamp = None
        last_active = None

    if not title:
        return None

    # Count messages
    msg_dir = OPENCODE_DIR / "message" / session_id
    message_count = 0
    if msg_dir.exists():
        message_count = len(list(msg_dir.glob("*.json")))

    session = Session(
        session_id=session_id,
        file_path=file_path,
        project_key=project_id if project_id else "global",
        project_dir=directory if directory else "未知项目",
        first_message=title[:150],
        timestamp=timestamp,
        last_active=last_active,
        cwd=directory if directory else "",
        model="",
        message_count=message_count,
        total_tokens=0,
        size_kb=size_kb,
    )

    return session


def load_opencode_session_messages(file_path: str) -> list[tuple[str, str]]:
    """Load message summaries for an OpenCode session for preview."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        session_id = data.get("id", "")
    except Exception:
        return []

    messages = []
    msg_dir = OPENCODE_DIR / "message" / session_id
    if not msg_dir.exists():
        return []

    msg_files = []
    for msg_file in msg_dir.glob("*.json"):
        try:
            with open(msg_file, "r", encoding="utf-8") as f:
                msg_data = json.load(f)
            created = msg_data.get("time", {}).get("created", 0)
            msg_files.append((created, msg_data))
        except Exception:
            continue

    msg_files.sort(key=lambda x: x[0])

    for _, msg_data in msg_files[:30]:
        role = msg_data.get("role", "")
        summary = msg_data.get("summary", {})
        summary_title = summary.get("title", "")
        model_info = msg_data.get("model", {})
        model_id = model_info.get("modelID", "") if isinstance(model_info, dict) else ""

        if role == "user":
            text = summary_title if summary_title else "(用户消息)"
            messages.append(("user", text[:2000]))
        elif role == "assistant":
            text = summary_title if summary_title else "(助手回复)"
            if model_id:
                text = f"[{model_id}] {text}"
            messages.append(("assistant", text[:2000]))

    return messages


def load_all_opencode_sessions() -> list[Session]:
    """Load metadata for all OpenCode sessions."""
    session_dir = OPENCODE_DIR / "session"
    if not session_dir.exists():
        return []

    sessions = []
    for json_file in session_dir.rglob("*.json"):
        session = parse_opencode_session(str(json_file))
        if session:
            sessions.append(session)

    from metadata import load_metadata
    meta = load_metadata()
    for s in sessions:
        entry = meta.get(s.session_id, {})
        if not isinstance(entry, dict):
            entry = {}
        custom_title = entry.get("title", "")
        if custom_title:
            s.custom_title = custom_title
        s.tags = entry.get("tags", [])

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


# ─── Codex Parser ──────────────────────────────────────────────────────────

def parse_codex_session(file_path: str, index_titles: dict[str, str]) -> Optional[Session]:
    """Parse a Codex session JSONL file."""
    path = Path(file_path)
    # Extract session ID from filename: rollout-2026-06-04T14-28-03-UUID.jsonl
    filename = path.stem
    parts = filename.split("-", 3)  # rollout, date, time, UUID
    if len(parts) >= 4:
        session_id = parts[3]  # UUID part
    else:
        session_id = filename

    session = Session(
        session_id=session_id,
        file_path=str(path),
        project_key="",
        project_dir="",
        size_kb=round(path.stat().st_size / 1024, 1),
    )

    first_user_found = False

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i > 80 and first_user_found:
                    break

                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue

                msg_type = obj.get("type", "")

                if msg_type == "session_meta":
                    payload = obj.get("payload", {})
                    meta_id = payload.get("id", "")
                    if meta_id:
                        session.session_id = meta_id
                    session.cwd = payload.get("cwd", "")
                    session.project_key = session.cwd if session.cwd else "unknown"

                elif msg_type == "event_msg":
                    payload = obj.get("payload", {})
                    ptype = payload.get("type", "")
                    if ptype == "user_message":
                        session.message_count += 1
                        msg = payload.get("message", "")
                        if not first_user_found and msg:
                            session.first_message = str(msg)[:150].replace("\n", " ").strip()
                            first_user_found = True
                    ts = obj.get("timestamp")
                    if ts:
                        dt = parse_timestamp(ts)
                        if session.last_active is None or dt > session.last_active:
                            session.last_active = dt
                        if not session.timestamp:
                            session.timestamp = dt

                elif msg_type == "response_item":
                    payload = obj.get("payload", {})
                    role = payload.get("role", "")
                    if role == "user" and not first_user_found:
                        content = payload.get("content", [])
                        if isinstance(content, list):
                            for c in content:
                                if isinstance(c, dict) and c.get("type") == "input_text":
                                    text = c.get("text", "").strip()
                                    # Skip system/environment context
                                    if text and not text.startswith("<environment") and not text.startswith("<permissions") and not text.startswith("<collaboration"):
                                        session.first_message = text[:150].replace("\n", " ").strip()
                                        first_user_found = True
                                        break
                    elif role == "assistant":
                        content = payload.get("content", [])
                        if isinstance(content, list):
                            for c in content:
                                if isinstance(c, dict) and c.get("type") == "output_text":
                                    text = c.get("text", "")
                                    if text:
                                        # Use as first message fallback
                                        if not first_user_found and not session.first_message:
                                            session.first_message = text[:150].replace("\n", " ").strip()
                                            first_user_found = True
                                        break
                    ts = obj.get("timestamp")
                    if ts:
                        dt = parse_timestamp(ts)
                        if session.last_active is None or dt > session.last_active:
                            session.last_active = dt
                        if not session.timestamp:
                            session.timestamp = dt

    except Exception:
        return None

    # Use thread_name from index if available
    if session.session_id in index_titles:
        title = index_titles[session.session_id]
        if title:
            session.first_message = title[:150]

    if not session.first_message:
        return None

    session.project_dir = derive_project_path(session.cwd)
    return session


def load_codex_session_messages(file_path: str) -> list[tuple[str, str]]:
    """Load user/assistant messages from a Codex session for preview."""
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

                if msg_type == "event_msg":
                    payload = obj.get("payload", {})
                    if payload.get("type") == "user_message":
                        msg = payload.get("message", "")
                        if msg:
                            messages.append(("user", str(msg)[:2000]))

                elif msg_type == "response_item":
                    payload = obj.get("payload", {})
                    role = payload.get("role", "")
                    content = payload.get("content", [])
                    if isinstance(content, list):
                        for c in content:
                            if isinstance(c, dict) and c.get("type") in ("input_text", "output_text"):
                                text = c.get("text", "")
                                if text and not text.startswith("<environment") and not text.startswith("<permissions") and not text.startswith("<collaboration"):
                                    r = "user" if role == "user" else "assistant"
                                    messages.append((r, text[:2000]))
                                    break
    except Exception:
        pass

    return messages


def load_codex_index_titles() -> dict[str, str]:
    """Load thread_name from Codex session_index.jsonl."""
    titles = {}
    index_path = Path.home() / ".codex" / "session_index.jsonl"
    if not index_path.exists():
        return titles
    try:
        with open(index_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    sid = obj.get("id", "")
                    name = obj.get("thread_name", "")
                    if sid and name:
                        titles[sid] = name
                except json.JSONDecodeError:
                    continue
    except Exception:
        pass
    return titles


def load_all_codex_sessions() -> list[Session]:
    """Load metadata for all Codex sessions."""
    sessions_dir = Path.home() / ".codex" / "sessions"
    if not sessions_dir.exists():
        return []

    index_titles = load_codex_index_titles()

    sessions = []
    for jsonl_file in sessions_dir.rglob("*.jsonl"):
        session = parse_codex_session(str(jsonl_file), index_titles)
        if session:
            sessions.append(session)

    # Load user-customized metadata
    from metadata import load_metadata
    meta = load_metadata()
    for s in sessions:
        entry = meta.get(s.session_id, {})
        if not isinstance(entry, dict):
            entry = {}
        custom_title = entry.get("title", "")
        if custom_title:
            s.custom_title = custom_title
        s.tags = entry.get("tags", [])

    sessions.sort(key=lambda s: s.last_active or datetime.min, reverse=True)
    return sessions
