"""Celery tasks by pipeline stage (archive / upload / cleanup / restore)."""

from __future__ import annotations

import logging
from collections.abc import Callable
from uuid import UUID

from celery import Task
from celery.exceptions import MaxRetriesExceededError

from infrastructure.bootstrap import build_worker_api
from infrastructure.config import load_config
from infrastructure.worker.celery_app import celery_app
from use_cases.public import WorkerApi

logger = logging.getLogger(__name__)


def _worker_api() -> WorkerApi:
    return build_worker_api(load_config())


def _run_with_failure_report(
    task: Task[..., dict[str, str]],
    stage: str,
    entity_id: str,
    action: str,
    runner: Callable[[], None],
) -> None:
    try:
        runner()
    except Exception as error:
        try:
            raise task.retry(exc=error)
        except MaxRetriesExceededError:
            logger.error("%s exhausted retries %s=%s error=%s", action, stage, entity_id, error)
            api = _worker_api()
            entity_uuid = UUID(entity_id)
            if stage == "archive":
                api.report_archive_failure(entity_uuid)
            elif stage == "upload":
                api.report_upload_failure(entity_uuid)
            elif stage == "cleanup":
                api.report_cleanup_failure_for_volume(entity_uuid)
            raise


@celery_app.task(
    name="infrastructure.worker.tasks.archive_volume",
    bind=True,
    max_retries=3,
)
def archive_volume(self: Task[..., dict[str, str]], source_item_id: str) -> dict[str, str]:
    """CPU/disk-heavy: 7z split/encrypt."""
    logger.info("archive_volume task_id=%s source_item_id=%s", self.request.id, source_item_id)
    _run_with_failure_report(
        self,
        "archive",
        source_item_id,
        "archive_volume",
        lambda: _worker_api().process_archive(UUID(source_item_id)),
    )
    return {"stage": "archive", "source_item_id": source_item_id, "status": "done"}


@celery_app.task(
    name="infrastructure.worker.tasks.upload_volume",
    bind=True,
    max_retries=3,
)
def upload_volume(self: Task[..., dict[str, str]], archive_volume_id: str) -> dict[str, str]:
    """Network-heavy: provider upload."""
    logger.info("upload_volume task_id=%s archive_volume_id=%s", self.request.id, archive_volume_id)
    _run_with_failure_report(
        self,
        "upload",
        archive_volume_id,
        "upload_volume",
        lambda: _worker_api().process_upload(UUID(archive_volume_id)),
    )
    return {"stage": "upload", "archive_volume_id": archive_volume_id, "status": "done"}


@celery_app.task(
    name="infrastructure.worker.tasks.cleanup_volume",
    bind=True,
    max_retries=3,
)
def cleanup_volume(self: Task[..., dict[str, str]], archive_volume_id: str) -> dict[str, str]:
    """Fast I/O: remove temp files after confirmed upload."""
    logger.info(
        "cleanup_volume task_id=%s archive_volume_id=%s",
        self.request.id,
        archive_volume_id,
    )
    _run_with_failure_report(
        self,
        "cleanup",
        archive_volume_id,
        "cleanup_volume",
        lambda: _worker_api().process_cleanup(UUID(archive_volume_id)),
    )
    return {"stage": "cleanup", "archive_volume_id": archive_volume_id, "status": "done"}


@celery_app.task(
    name="infrastructure.worker.tasks.restore_volume",
    bind=True,
    max_retries=3,
)
def restore_volume(self: Task[..., dict[str, str]], archive_volume_id: str) -> dict[str, str]:
    """Network-heavy: provider download for a single archive volume."""
    logger.info(
        "restore_volume task_id=%s archive_volume_id=%s",
        self.request.id,
        archive_volume_id,
    )
    path = _worker_api().process_restore_volume(UUID(archive_volume_id))
    return {
        "stage": "restore",
        "archive_volume_id": archive_volume_id,
        "status": "done",
        "path": str(path),
    }
