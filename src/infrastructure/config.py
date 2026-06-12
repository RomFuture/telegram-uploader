from dataclasses import dataclass
from os import environ, getenv
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AppConfig:
    app_env: str
    app_log_level: str
    postgres_dsn: str
    redis_url: str
    telegram_provider: str
    telegram_bot_token: str
    telegram_bot_api_url: str
    telegram_api_id: int | None
    telegram_api_hash: str
    telegram_session_path: Path
    telegram_target_chat_id: str
    archive_encryption_key: str | None
    archive_cache_dir: Path


def _load_dotenv(path: Path | None = None) -> None:
    """Load ``.env`` into ``os.environ`` when running outside docker compose."""
    env_path = path or Path(".env")
    if not env_path.is_file():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", maxsplit=1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in environ:
            environ[key] = value


def load_config() -> AppConfig:
    _load_dotenv()
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
    raw_api_id = getenv("TELEGRAM_API_ID", "").strip()
    raw_session_path = getenv(
        "TELEGRAM_SESSION_PATH",
        "/tmp/telegram_uploader/session.session",
    ).strip()
    return AppConfig(
        app_env=getenv("APP_ENV", "development"),
        app_log_level=getenv("APP_LOG_LEVEL", "INFO"),
        postgres_dsn=f"postgresql://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db}",
        redis_url=f"redis://{redis_host}:{redis_port}/{redis_db}",
        telegram_provider=getenv("TELEGRAM_PROVIDER", "client").strip().lower(),
        telegram_bot_token=getenv("TELEGRAM_BOT_TOKEN", ""),
        telegram_bot_api_url=getenv("TELEGRAM_BOT_API_URL", "http://localhost:8081"),
        telegram_api_id=int(raw_api_id) if raw_api_id.isdigit() else None,
        telegram_api_hash=getenv("TELEGRAM_API_HASH", ""),
        telegram_session_path=Path(raw_session_path),
        telegram_target_chat_id=getenv("TELEGRAM_TARGET_CHAT_ID", ""),
        archive_encryption_key=raw_key if raw_key else None,
        archive_cache_dir=Path(raw_cache_dir),
    )
