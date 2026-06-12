"""Launch the backup GUI: python -m application.gui"""

from application.backend_receiver import BackendReceiver
from application.gui.app import BackupApp
from application.settings_values import SettingsValues
from infrastructure.bootstrap import build_backup_api, build_client_provider
from infrastructure.config import AppConfig, load_config
from infrastructure.db.migrate import apply_migrations


def _settings_from_config(config: AppConfig) -> SettingsValues:
    return SettingsValues(
        encryption_key=config.archive_encryption_key,
        target_chat_id=config.telegram_target_chat_id,
        telegram_provider=config.telegram_provider,
        telegram_api_id=str(config.telegram_api_id or ""),
        telegram_api_hash=config.telegram_api_hash,
        telegram_session_path=str(config.telegram_session_path),
        telegram_bot_token=config.telegram_bot_token,
        telegram_bot_api_url=config.telegram_bot_api_url,
        archive_ram_limit_mb=1024,
    )


def main() -> None:
    config = load_config()
    apply_migrations(config.postgres_dsn)
    receiver = BackendReceiver(
        build_backup_api(config),
        build_client_provider=build_client_provider,
    )
    BackupApp(receiver, _settings_from_config(config)).run()


if __name__ == "__main__":
    main()
