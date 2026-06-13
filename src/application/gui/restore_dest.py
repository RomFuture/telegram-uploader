"""Restore destination helpers for the GUI."""

from __future__ import annotations

import os
from pathlib import Path

_INSTALL_PREFIXES = ("/opt/telegram-uploader",)


def default_restore_dir() -> Path:
    path = Path.home() / "Restored"
    path.mkdir(parents=True, exist_ok=True)
    return path


def is_under_install_root(path: Path) -> bool:
    resolved = str(path.resolve())
    return any(resolved.startswith(prefix) for prefix in _INSTALL_PREFIXES)


def readonly_existing_files(dest: Path) -> list[Path]:
    if not dest.is_dir():
        return []
    return [entry for entry in dest.iterdir() if entry.is_file() and not os.access(entry, os.W_OK)]
