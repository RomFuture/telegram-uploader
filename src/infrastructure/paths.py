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
