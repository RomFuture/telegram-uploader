"""Celery tasks by pipeline stage (archive / upload / cleanup / restore).

Implementations are stubs until wired to use cases and repositories.
"""

from __future__ import annotations

import logging

from celery import Task

from infrastructure.worker.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="infrastructure.worker.tasks.archive_volume", bind=True)
def archive_volume(self: Task, source_item_id: str) -> dict[str, str]:
    """CPU/disk-heavy: 7z split/encrypt (future)."""
    logger.info("archive_volume task_id=%s source_item_id=%s", self.request.id, source_item_id)
    return {"stage": "archive", "source_item_id": source_item_id, "status": "stub"}


@celery_app.task(name="infrastructure.worker.tasks.upload_volume", bind=True)
def upload_volume(self: Task, archive_volume_id: str) -> dict[str, str]:
    """Network-heavy: provider upload (future)."""
    logger.info("upload_volume task_id=%s archive_volume_id=%s", self.request.id, archive_volume_id)
    return {"stage": "upload", "archive_volume_id": archive_volume_id, "status": "stub"}


@celery_app.task(name="infrastructure.worker.tasks.cleanup_volume", bind=True)
def cleanup_volume(self: Task, archive_volume_id: str) -> dict[str, str]:
    """Fast I/O: remove temp files after confirmed upload (future)."""
    logger.info(
        "cleanup_volume task_id=%s archive_volume_id=%s",
        self.request.id,
        archive_volume_id,
    )
    return {"stage": "cleanup", "archive_volume_id": archive_volume_id, "status": "stub"}


@celery_app.task(name="infrastructure.worker.tasks.restore_volume", bind=True)
def restore_volume(self: Task, archive_volume_id: str) -> dict[str, str]:
    """Network-heavy: provider download/restore (future)."""
    logger.info(
        "restore_volume task_id=%s archive_volume_id=%s",
        self.request.id,
        archive_volume_id,
    )
    return {"stage": "restore", "archive_volume_id": archive_volume_id, "status": "stub"}
