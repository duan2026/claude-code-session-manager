"""
CC Session Manager - Metadata Persistence
Stores user-customized titles and tags in a separate JSON file.
Does NOT modify the original Claude Code JSONL session files.
"""

import json
from pathlib import Path
from typing import Optional


METADATA_PATH = Path.home() / ".claude" / "cc-session-metadata.json"


def load_metadata() -> dict:
    """Load all metadata from disk. Returns {session_id: {title, tags}}."""
    if not METADATA_PATH.exists():
        return {}
    try:
        with open(METADATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_metadata(data: dict):
    """Write all metadata to disk."""
    METADATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_title(session_id: str) -> Optional[str]:
    """Get custom title for a session, or None if not set."""
    data = load_metadata()
    entry = data.get(session_id, {})
    title = entry.get("title", "")
    return title if title else None


def set_title(session_id: str, title: str):
    """Set custom title for a session."""
    data = load_metadata()
    if session_id not in data:
        data[session_id] = {}
    data[session_id]["title"] = title
    save_metadata(data)


def get_tags(session_id: str) -> list[str]:
    """Get tags for a session."""
    data = load_metadata()
    entry = data.get(session_id, {})
    if not isinstance(entry, dict):
        return []
    return entry.get("tags", [])


def set_tags(session_id: str, tags: list[str]):
    """Set tags for a session."""
    data = load_metadata()
    if session_id not in data:
        data[session_id] = {}
    data[session_id]["tags"] = tags
    save_metadata(data)


def get_all_tags() -> list[str]:
    """Collect all unique tags across all sessions, sorted alphabetically."""
    data = load_metadata()
    tags_set: set[str] = set()
    for entry in data.values():
        if not isinstance(entry, dict):
            continue
        for tag in entry.get("tags", []):
            tags_set.add(tag)
    return sorted(tags_set)
