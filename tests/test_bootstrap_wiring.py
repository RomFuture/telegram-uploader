from pathlib import Path
from unittest.mock import MagicMock, patch

from infrastructure.bootstrap import (
    build_storage_provider,
    wire_celery_entrypoint,
    wire_gui_entrypoint,
)
from infrastructure.config import AppConfig
from use_cases.public import CeleryEntrypoint, GuiEntrypoint


def _test_config() -> AppConfig:
    return AppConfig(
        app_env="test",
        app_log_level="INFO",
        log_file_path=Path("/tmp/telegram_uploader/telegram-uploader.log"),
        postgres_dsn="postgresql://test:test@localhost:5432/test",
        redis_url="redis://localhost:6379/0",
        telegram_provider="bot",
        telegram_bot_token="token",
        telegram_bot_api_url="http://localhost:8081",
        telegram_api_id=None,
        telegram_api_hash="",
        telegram_session_path=Path("/tmp/telegram_uploader/session.session"),
        telegram_target_chat_id="-1001",
        archive_encryption_key=None,
        archive_cache_dir=Path("/tmp/telegram_uploader"),
    )


@patch("infrastructure.bootstrap.SqlAlchemyRepositories.from_dsn")
@patch("infrastructure.bootstrap.build_storage_provider")
@patch("infrastructure.bootstrap.CeleryTaskQueue")
@patch("infrastructure.bootstrap.ArchiveServiceAdapter")
def test_wire_gui_entrypoint_returns_gui_entrypoint(
    mock_archive_adapter: MagicMock,
    mock_task_queue: MagicMock,
    mock_provider: MagicMock,
    mock_repos_factory: MagicMock,
) -> None:
    mock_repos = MagicMock()
    mock_repos.sessions = MagicMock()
    mock_repos.source_items = MagicMock()
    mock_repos.archive_volumes = MagicMock()
    mock_repos_factory.return_value = mock_repos

    entrypoint = wire_gui_entrypoint(_test_config())

    assert isinstance(entrypoint, GuiEntrypoint)
    mock_repos_factory.assert_called_once()
    mock_provider.assert_called_once()
    mock_task_queue.assert_called_once()
    mock_archive_adapter.assert_called_once()


@patch("infrastructure.bootstrap.SqlAlchemyRepositories.from_dsn")
@patch("infrastructure.bootstrap.build_storage_provider")
@patch("infrastructure.bootstrap.CeleryTaskQueue")
@patch("infrastructure.bootstrap.ArchiveServiceAdapter")
def test_wire_celery_entrypoint_returns_celery_entrypoint(
    mock_archive_adapter: MagicMock,
    mock_task_queue: MagicMock,
    mock_provider: MagicMock,
    mock_repos_factory: MagicMock,
) -> None:
    mock_repos = MagicMock()
    mock_repos.sessions = MagicMock()
    mock_repos.source_items = MagicMock()
    mock_repos.archive_volumes = MagicMock()
    mock_repos_factory.return_value = mock_repos

    entrypoint = wire_celery_entrypoint(_test_config())

    assert isinstance(entrypoint, CeleryEntrypoint)
    mock_repos_factory.assert_called_once()
    mock_provider.assert_called_once()
    mock_task_queue.assert_called_once()
    mock_archive_adapter.assert_called_once()


def test_build_storage_provider_uses_bot_by_default() -> None:
    provider = build_storage_provider(_test_config())
    from infrastructure.providers.telegram_provider import TelegramProviderV1

    assert isinstance(provider, TelegramProviderV1)


def test_build_storage_provider_client_without_credentials_uses_stub() -> None:
    cfg = AppConfig(
        app_env="test",
        app_log_level="INFO",
        log_file_path=Path("/tmp/telegram_uploader/telegram-uploader.log"),
        postgres_dsn="postgresql://test:test@localhost:5432/test",
        redis_url="redis://localhost:6379/0",
        telegram_provider="client",
        telegram_bot_token="",
        telegram_bot_api_url="http://localhost:8081",
        telegram_api_id=None,
        telegram_api_hash="",
        telegram_session_path=Path("/tmp/session.session"),
        telegram_target_chat_id="",
        archive_encryption_key=None,
        archive_cache_dir=Path("/tmp/telegram_uploader"),
    )
    from infrastructure.providers.unconfigured_storage_provider import UnconfiguredStorageProvider

    provider = build_storage_provider(cfg)
    assert isinstance(provider, UnconfiguredStorageProvider)


def test_build_storage_provider_uses_client_when_configured() -> None:
    cfg = AppConfig(
        app_env="test",
        app_log_level="INFO",
        log_file_path=Path("/tmp/telegram_uploader/telegram-uploader.log"),
        postgres_dsn="postgresql://test:test@localhost:5432/test",
        redis_url="redis://localhost:6379/0",
        telegram_provider="client",
        telegram_bot_token="",
        telegram_bot_api_url="http://localhost:8081",
        telegram_api_id=12345,
        telegram_api_hash="abc",
        telegram_session_path=Path("/tmp/session.session"),
        telegram_target_chat_id="-1001",
        archive_encryption_key=None,
        archive_cache_dir=Path("/tmp/telegram_uploader"),
    )
    provider = build_storage_provider(cfg)
    from infrastructure.providers.telegram_client_provider import TelegramClientProvider

    assert isinstance(provider, TelegramClientProvider)
