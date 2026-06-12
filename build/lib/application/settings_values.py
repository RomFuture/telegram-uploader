"""GUI settings snapshot (in-memory; workers read .env)."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SettingsValues:
    encryption_key: str | None
    target_chat_id: str
    telegram_provider: str
    telegram_api_id: str
    telegram_api_hash: str
    telegram_session_path: str
    telegram_bot_token: str
    telegram_bot_api_url: str
    archive_ram_limit_mb: int = 1024
