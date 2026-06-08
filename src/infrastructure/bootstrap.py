"""Composition root: config, migrations, health checks, facade wiring."""

import logging
import sys
from typing import cast

import redis

from infrastructure.archive import ArchiveServiceAdapter, SevenZipService
from infrastructure.config import AppConfig, load_config
from infrastructure.db.migrate import apply_migrations
from infrastructure.db.sqlalchemy_repositories import SqlAlchemyRepositories
from infrastructure.facade import BackupFacade
from infrastructure.providers import TelegramProviderV1
from infrastructure.worker.celery_task_queue import CeleryTaskQueue
from use_cases.backup.cleanup_volume import CleanupVolumeUseCase
from use_cases.backup.enqueue_source_item import EnqueueSourceItemUseCase
from use_cases.backup.process_archive_volume import ProcessArchiveVolumeUseCase
from use_cases.backup.process_upload_volume import ProcessUploadVolumeUseCase
from use_cases.backup.start_backup_pipeline import StartBackupPipelineUseCase
from use_cases.restore.process_restore_volume import ProcessRestoreVolumeUseCase
from use_cases.restore.restore_session import RestoreSessionUseCase
from use_cases.repositories import Repositories
from use_cases.session.create_session import CreateSessionUseCase


def build_facade(cfg: AppConfig) -> BackupFacade:
    """Wire repositories, ports, and use cases into a single entry point."""
    repos = cast(Repositories, SqlAlchemyRepositories.from_dsn(cfg.postgres_dsn))
    provider = TelegramProviderV1(
        bot_token=cfg.telegram_bot_token,
        base_url=cfg.telegram_bot_api_url,
    )
    task_queue = CeleryTaskQueue()
    archive_service = ArchiveServiceAdapter(service=SevenZipService())
    remote_target = cfg.telegram_target_chat_id

    return BackupFacade(
        repos=repos,
        create_session=CreateSessionUseCase(repos.sessions),
        enqueue_source_item=EnqueueSourceItemUseCase(repos.source_items, task_queue),
        start_backup_pipeline=StartBackupPipelineUseCase(repos, task_queue),
        process_archive=ProcessArchiveVolumeUseCase(
            sessions=repos.sessions,
            source_items=repos.source_items,
            archive_volumes=repos.archive_volumes,
            archive_service=archive_service,
            task_queue=task_queue,
            archive_cache_dir=cfg.archive_cache_dir,
        ),
        process_upload=ProcessUploadVolumeUseCase(
            source_items=repos.source_items,
            archive_volumes=repos.archive_volumes,
            storage_provider=provider,
            task_queue=task_queue,
            remote_target=remote_target,
        ),
        process_cleanup=CleanupVolumeUseCase(
            source_items=repos.source_items,
            archive_volumes=repos.archive_volumes,
        ),
        restore_volume=ProcessRestoreVolumeUseCase(
            archive_volumes=repos.archive_volumes,
            storage_provider=provider,
            staging_dir=cfg.archive_cache_dir / "restore",
        ),
        restore_session=RestoreSessionUseCase(
            archive_volumes=repos.archive_volumes,
            storage_provider=provider,
            staging_dir=cfg.archive_cache_dir / "restore",
        ),
    )


def bootstrap() -> None:
    """Apply migrations, verify runtime dependencies, and wire the facade."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stdout,
    )
    log = logging.getLogger("infrastructure.bootstrap")
    cfg = load_config()
    log.info("Environment: %s", cfg.app_env)
    apply_migrations(cfg.postgres_dsn)
    log.info("Database migrations applied.")
    client = redis.Redis.from_url(cfg.redis_url, decode_responses=False)
    client.ping()
    log.info("Redis ping OK.")
    build_facade(cfg)
    log.info("Facade wired.")


if __name__ == "__main__":
    bootstrap()
