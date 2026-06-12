"""Default paths for user config (packaged and dev installs)."""

from __future__ import annotations

import os
from pathlib import Path


def config_dir() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME", "").strip()
    if xdg:
        return Path(xdg) / "telegram-uploader"
    return Path.home() / ".config" / "telegram-uploader"


def default_session_path() -> Path:
    return config_dir() / "session.session"


def default_cache_dir() -> Path:
    return config_dir() / "cache"


def resolve_user_path(raw: str) -> Path:
    expanded = os.path.expandvars(os.path.expanduser(raw.strip()))
    return Path(expanded)


def _parent_writable(path: Path) -> bool:
    parent = path.parent
    if parent.exists():
        return os.access(parent, os.W_OK)
    try:
        parent.mkdir(parents=True, exist_ok=True)
        return os.access(parent, os.W_OK)
    except OSError:
        return False


def session_path_for_use(raw: str | None = None) -> Path:
    """Return a session path the current user can write (Telethon SQLite)."""
    candidate = resolve_user_path(raw) if raw and raw.strip() else default_session_path()
    if _parent_writable(candidate):
        return candidate.resolve()
    fallback = default_session_path()
    fallback.parent.mkdir(parents=True, exist_ok=True)
    return fallback.resolve()
