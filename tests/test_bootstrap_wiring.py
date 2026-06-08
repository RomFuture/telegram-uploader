from pathlib import Path
from unittest.mock import MagicMock, patch

from infrastructure.bootstrap import build_facade
from infrastructure.config import AppConfig
from infrastructure.facade import BackupFacade


def _test_config() -> AppConfig:
    return AppConfig(
        app_env="test",
        app_log_level="INFO",
        postgres_dsn="postgresql://test:test@localhost:5432/test",
        redis_url="redis://localhost:6379/0",
        telegram_bot_token="token",
        telegram_bot_api_url="http://localhost:8081",
        telegram_target_chat_id="-1001",
        archive_encryption_key=None,
        archive_cache_dir=Path("/tmp/telegram_uploader"),
    )


@patch("infrastructure.bootstrap.SqlAlchemyRepositories.from_dsn")
@patch("infrastructure.bootstrap.TelegramProviderV1")
@patch("infrastructure.bootstrap.CeleryTaskQueue")
@patch("infrastructure.bootstrap.ArchiveServiceAdapter")
def test_build_facade_returns_backup_facade(
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

    facade = build_facade(_test_config())

    assert isinstance(facade, BackupFacade)
    mock_repos_factory.assert_called_once()
    mock_provider.assert_called_once()
    mock_task_queue.assert_called_once()
    mock_archive_adapter.assert_called_once()
