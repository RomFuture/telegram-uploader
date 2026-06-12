"""Read/write user config at ~/.config/telegram-uploader/.env."""

from __future__ import annotations

import os
from pathlib import Path

from application.settings_values import SettingsValues
from infrastructure.paths import default_session_path

_ENV_KEYS = (
    "TELEGRAM_PROVIDER",
    "TELEGRAM_API_ID",
    "TELEGRAM_API_HASH",
    "TELEGRAM_SESSION_PATH",
    "TELEGRAM_SESSION_DIR",
    "TELEGRAM_TARGET_CHAT_ID",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_BOT_API_URL",
    "ARCHIVE_ENCRYPTION_KEY",
)


def user_env_path() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME", "").strip()
    config_home = Path(xdg) if xdg else Path.home() / ".config"
    return config_home / "telegram-uploader" / ".env"


def _session_dir_from_path(session_path: str) -> str:
    return str(Path(session_path).parent) if session_path else ""


def settings_to_env_updates(values: SettingsValues) -> dict[str, str]:
    session_path = values.telegram_session_path.strip() or str(default_session_path())
    updates: dict[str, str] = {
        "TELEGRAM_PROVIDER": values.telegram_provider.strip() or "client",
        "TELEGRAM_API_ID": values.telegram_api_id.strip(),
        "TELEGRAM_API_HASH": values.telegram_api_hash.strip(),
        "TELEGRAM_SESSION_PATH": session_path,
        "TELEGRAM_SESSION_DIR": _session_dir_from_path(session_path),
        "TELEGRAM_TARGET_CHAT_ID": values.target_chat_id.strip(),
        "TELEGRAM_BOT_TOKEN": values.telegram_bot_token.strip(),
        "TELEGRAM_BOT_API_URL": values.telegram_bot_api_url.strip() or "http://localhost:8081",
    }
    if values.encryption_key:
        updates["ARCHIVE_ENCRYPTION_KEY"] = values.encryption_key
    return updates


def merge_env_file(path: Path, updates: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    seen: set[str] = set()
    if path.is_file():
        lines = path.read_text(encoding="utf-8").splitlines()

    new_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            new_lines.append(line)
            continue
        key, _ = line.split("=", maxsplit=1)
        key = key.strip()
        if key in updates:
            new_lines.append(f"{key}={updates[key]}")
            seen.add(key)
        else:
            new_lines.append(line)

    for key in _ENV_KEYS:
        if key in updates and key not in seen:
            new_lines.append(f"{key}={updates[key]}")

    path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    path.chmod(0o600)


def save_settings_env(values: SettingsValues) -> Path:
    path = user_env_path()
    merge_env_file(path, settings_to_env_updates(values))
    return path
