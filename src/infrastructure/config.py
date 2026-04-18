from dataclasses import dataclass
from os import getenv
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AppConfig:
    app_env: str
    app_log_level: str
    postgres_dsn: str
    redis_url: str
    telegram_bot_token: str
    telegram_bot_api_url: str
    telegram_target_chat_id: str
    archive_encryption_key: str | None
    archive_cache_dir: Path


def load_config() -> AppConfig:
    postgres_host = getenv("POSTGRES_HOST", "localhost")
    postgres_port = getenv("POSTGRES_PORT", "5432")
    postgres_db = getenv("POSTGRES_DB", "telegram_uploader")
    postgres_user = getenv("POSTGRES_USER", "telegram_uploader")
    postgres_password = getenv("POSTGRES_PASSWORD", "telegram_uploader")

    redis_host = getenv("REDIS_HOST", "localhost")
    redis_port = getenv("REDIS_PORT", "6379")
    redis_db = getenv("REDIS_DB", "0")

    raw_key = getenv("ARCHIVE_ENCRYPTION_KEY", "").strip()
    raw_cache_dir = getenv("ARCHIVE_CACHE_DIR", "/tmp/telegram_uploader").strip()
    return AppConfig(
        app_env=getenv("APP_ENV", "development"),
        app_log_level=getenv("APP_LOG_LEVEL", "INFO"),
        postgres_dsn=f"postgresql://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db}",
        redis_url=f"redis://{redis_host}:{redis_port}/{redis_db}",
        telegram_bot_token=getenv("TELEGRAM_BOT_TOKEN", ""),
        telegram_bot_api_url=getenv("TELEGRAM_BOT_API_URL", "http://localhost:8081"),
        telegram_target_chat_id=getenv("TELEGRAM_TARGET_CHAT_ID", ""),
        archive_encryption_key=raw_key if raw_key else None,
        archive_cache_dir=Path(raw_cache_dir),
    )
