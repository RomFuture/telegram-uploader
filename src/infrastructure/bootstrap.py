"""Composition root: config, migrations, health checks, API wiring."""

import logging
from pathlib import Path
from typing import cast

import redis

from infrastructure.archive import ArchiveServiceAdapter, SevenZipService
from infrastructure.config import AppConfig, load_config
from infrastructure.db.migrate import apply_migrations
from infrastructure.db.sqlalchemy_repositories import SqlAlchemyRepositories
from infrastructure.providers import TelegramClientProvider, TelegramProviderV1
from infrastructure.providers.unconfigured_storage_provider import UnconfiguredStorageProvider
from infrastructure.worker.celery_task_queue import CeleryTaskQueue
from observation.logging_setup import setup_logging
from use_cases.backup.cleanup_volume import CleanupVolumeUseCase
from use_cases.backup.enqueue_source_item import EnqueueSourceItemUseCase
from use_cases.backup.process_archive_volume import ProcessArchiveVolumeUseCase
from use_cases.backup.process_upload_volume import ProcessUploadVolumeUseCase
from use_cases.backup.report_failure import (
    ReportArchiveFailureUseCase,
    ReportCleanupFailureUseCase,
    ReportUploadFailureUseCase,
)
from use_cases.backup.start_backup_pipeline import StartBackupPipelineUseCase
from use_cases.public import CeleryEntrypoint, GuiEntrypoint
from use_cases.restore.check_restore_ready import CheckRestoreReadyUseCase
from use_cases.restore.process_restore_volume import ProcessRestoreVolumeUseCase
from use_cases.restore.restore_session import RestoreSessionUseCase
from use_cases.session.create import (
    CreateDatabaseUseCase,
    CreateFolderUseCase,
    CreateSessionUseCase,
)
from use_cases.session.get_session_queue_snapshot import GetSessionQueueSnapshotUseCase
from use_cases.session.list import ListFoldersUseCase, ListSessionProfilesUseCase
from use_cases.session.manage_source_item import (
    DeleteSourceItemUseCase,
    MoveSourceItemUseCase,
    RenameSourceItemUseCase,
)
from use_cases.session.unlock_session import UnlockSessionUseCase
from use_cases.shared.ports.storage_provider import StorageProviderPort
from use_cases.shared.repositories import Repositories
from use_cases.telegram.verify_storage_provider import VerifyStorageProviderUseCase


def _wire_repositories(cfg: AppConfig) -> Repositories:
    return cast(Repositories, SqlAlchemyRepositories.from_dsn(cfg.postgres_dsn))


def build_storage_provider(cfg: AppConfig) -> StorageProviderPort:
    if cfg.telegram_provider == "client":
        if cfg.telegram_api_id is None or not cfg.telegram_api_hash:
            return UnconfiguredStorageProvider(mode="client")
        return TelegramClientProvider(
            api_id=cfg.telegram_api_id,
            api_hash=cfg.telegram_api_hash,
            session_path=cfg.telegram_session_path,
        )
    if not cfg.telegram_bot_token:
        return UnconfiguredStorageProvider(mode="bot")
    return TelegramProviderV1(
        bot_token=cfg.telegram_bot_token,
        base_url=cfg.telegram_bot_api_url,
    )


def build_client_provider(
    *,
    api_id: int,
    api_hash: str,
    session_path: Path,
) -> StorageProviderPort:
    return TelegramClientProvider(
        api_id=api_id,
        api_hash=api_hash,
        session_path=session_path,
    )


def _client_api_test_file() -> Path:
    bundled = Path(__file__).resolve().parent / "data" / "client_api_test.md"
    candidates: tuple[Path, ...] = (
        bundled,
        Path("/opt/telegram-uploader/share/client_api_test.md"),
    )
    repo_root = Path(__file__).resolve().parents[2]
    if (repo_root / "pyproject.toml").is_file():
        candidates = (
            *candidates,
            repo_root / "packaging/assets/client_api_test.md",
        )
    for path in candidates:
        if path.is_file():
            return path
    return bundled


def wire_gui_entrypoint(cfg: AppConfig) -> GuiEntrypoint:
    """Wire GUI-facing use cases into GuiEntrypoint (does not start Celery workers)."""
    repos = _wire_repositories(cfg)
    task_queue = CeleryTaskQueue()
    provider = build_storage_provider(cfg)
    archive_service = ArchiveServiceAdapter(service=SevenZipService())
    restore_dir = cfg.archive_cache_dir / "restore"

    return GuiEntrypoint(
        create_session=CreateSessionUseCase(repos.sessions),
        create_database_uc=CreateDatabaseUseCase(repos.sessions, repos.folders),
        unlock_session_uc=UnlockSessionUseCase(repos.sessions),
        list_session_profiles=ListSessionProfilesUseCase(repos.sessions),
        list_folders_uc=ListFoldersUseCase(repos.folders),
        create_folder_uc=CreateFolderUseCase(repos.folders),
        get_session_queue_snapshot=GetSessionQueueSnapshotUseCase(
            repos.source_items, repos.folders
        ),
        enqueue_source_item=EnqueueSourceItemUseCase(repos.source_items, repos.folders),
        start_backup_pipeline=StartBackupPipelineUseCase(repos, task_queue),
        restore_session_uc=RestoreSessionUseCase(
            sessions=repos.sessions,
            source_items=repos.source_items,
            folders=repos.folders,
            archive_volumes=repos.archive_volumes,
            storage_provider=provider,
            archive_service=archive_service,
            staging_dir=restore_dir,
            target_chat_id=cfg.telegram_target_chat_id,
        ),
        check_restore_ready_uc=CheckRestoreReadyUseCase(
            archive_volumes=repos.archive_volumes,
            source_items=repos.source_items,
            folders=repos.folders,
            storage_provider=provider,
            target_chat_id=cfg.telegram_target_chat_id,
        ),
        verify_storage_provider_uc=VerifyStorageProviderUseCase(
            test_file_path=_client_api_test_file(),
        ),
        rename_source_item_uc=RenameSourceItemUseCase(repos.source_items),
        move_source_item_uc=MoveSourceItemUseCase(repos.source_items, repos.folders),
        delete_source_item_uc=DeleteSourceItemUseCase(
            repos.source_items,
            repos.archive_volumes,
        ),
    )


def wire_celery_entrypoint(cfg: AppConfig) -> CeleryEntrypoint:
    """Wire pipeline use cases into CeleryEntrypoint (called when a Celery task runs)."""
    repos = _wire_repositories(cfg)
    task_queue = CeleryTaskQueue()
    provider = build_storage_provider(cfg)
    archive_service = ArchiveServiceAdapter(service=SevenZipService())
    restore_dir = cfg.archive_cache_dir / "restore"

    return CeleryEntrypoint(
        process_archive_uc=ProcessArchiveVolumeUseCase(
            sessions=repos.sessions,
            source_items=repos.source_items,
            archive_volumes=repos.archive_volumes,
            archive_service=archive_service,
            task_queue=task_queue,
            archive_cache_dir=cfg.archive_cache_dir,
        ),
        process_upload_uc=ProcessUploadVolumeUseCase(
            source_items=repos.source_items,
            archive_volumes=repos.archive_volumes,
            storage_provider=provider,
            task_queue=task_queue,
            remote_target=cfg.telegram_target_chat_id,
        ),
        process_cleanup_uc=CleanupVolumeUseCase(
            source_items=repos.source_items,
            archive_volumes=repos.archive_volumes,
        ),
        process_restore_volume_uc=ProcessRestoreVolumeUseCase(
            archive_volumes=repos.archive_volumes,
            storage_provider=provider,
            staging_dir=restore_dir,
            target_chat_id=cfg.telegram_target_chat_id,
        ),
        report_archive_failure_uc=ReportArchiveFailureUseCase(repos.source_items),
        report_upload_failure_uc=ReportUploadFailureUseCase(
            repos.source_items,
            repos.archive_volumes,
        ),
        report_cleanup_failure_uc=ReportCleanupFailureUseCase(repos.source_items),
    )


def bootstrap() -> None:
    """Apply migrations, verify runtime dependencies, and wire APIs."""
    cfg = load_config()
    setup_logging(log_file=cfg.log_file_path, level=cfg.app_log_level)
    log = logging.getLogger("infrastructure.bootstrap")
    log.info("Environment: %s", cfg.app_env)
    apply_migrations(cfg.postgres_dsn)
    log.info("Database migrations applied.")
    client = redis.Redis.from_url(cfg.redis_url, decode_responses=False)
    client.ping()
    log.info("Redis ping OK.")
    wire_gui_entrypoint(cfg)
    wire_celery_entrypoint(cfg)
    log.info("Entrypoints wired.")


if __name__ == "__main__":
    bootstrap()
