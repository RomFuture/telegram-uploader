"""Celery tasks by pipeline stage (archive / upload / cleanup / restore)."""

from __future__ import annotations

import logging
from uuid import UUID

from celery import Task

from infrastructure.bootstrap import build_facade
from infrastructure.config import load_config
from infrastructure.facade import BackupFacade
from infrastructure.worker.celery_app import celery_app

logger = logging.getLogger(__name__)


def _facade() -> BackupFacade:
    return build_facade(load_config())


@celery_app.task(
    name="infrastructure.worker.tasks.archive_volume",
    bind=True,
    max_retries=3,
)
def archive_volume(self: Task, source_item_id: str) -> dict[str, str]:
    """CPU/disk-heavy: 7z split/encrypt."""
    logger.info("archive_volume task_id=%s source_item_id=%s", self.request.id, source_item_id)
    _facade().process_archive_volume(UUID(source_item_id))
    return {"stage": "archive", "source_item_id": source_item_id, "status": "done"}


@celery_app.task(
    name="infrastructure.worker.tasks.upload_volume",
    bind=True,
    max_retries=3,
)
def upload_volume(self: Task, archive_volume_id: str) -> dict[str, str]:
    """Network-heavy: provider upload."""
    logger.info("upload_volume task_id=%s archive_volume_id=%s", self.request.id, archive_volume_id)
    _facade().process_upload_volume(UUID(archive_volume_id))
    return {"stage": "upload", "archive_volume_id": archive_volume_id, "status": "done"}


@celery_app.task(
    name="infrastructure.worker.tasks.cleanup_volume",
    bind=True,
    max_retries=3,
)
def cleanup_volume(self: Task, archive_volume_id: str) -> dict[str, str]:
    """Fast I/O: remove temp files after confirmed upload."""
    logger.info(
        "cleanup_volume task_id=%s archive_volume_id=%s",
        self.request.id,
        archive_volume_id,
    )
    _facade().process_cleanup_volume(UUID(archive_volume_id))
    return {"stage": "cleanup", "archive_volume_id": archive_volume_id, "status": "done"}


@celery_app.task(
    name="infrastructure.worker.tasks.restore_volume",
    bind=True,
    max_retries=3,
)
def restore_volume(self: Task, archive_volume_id: str) -> dict[str, str]:
    """Network-heavy: provider download for a single archive volume."""
    logger.info(
        "restore_volume task_id=%s archive_volume_id=%s",
        self.request.id,
        archive_volume_id,
    )
    path = _facade().process_restore_volume(UUID(archive_volume_id))
    return {
        "stage": "restore",
        "archive_volume_id": archive_volume_id,
        "status": "done",
        "path": str(path),
    }
