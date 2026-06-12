"""Idempotency for backup pipeline steps (duplicate task / worker re-run).

Reads entity status via domain types; decides what the use case should do next.
Lives in use_cases — not domain — because it is execution policy, not core state rules.
"""

from enum import Enum

import domain as domain
from use_cases.shared.types import ArchiveVolume, SourceItem


class ArchiveStepAction(str, Enum):
    SKIP = "skip"
    RUN = "run"
    RESUME = "resume"
    FAIL = "fail"


class UploadStepAction(str, Enum):
    SKIP = "skip"
    RUN = "run"
    CONTINUE = "continue"
    FAIL = "fail"


class CleanupStepAction(str, Enum):
    SKIP = "skip"
    RUN = "run"


def decide_archive_on_retry(item: SourceItem) -> ArchiveStepAction:
    """What to do when the archive step runs again for this source item."""
    if item.status in (
        domain.SourceItemStatus.UPLOADING,
        domain.SourceItemStatus.CLEANUP,
        domain.SourceItemStatus.COMPLETED,
    ):
        return ArchiveStepAction.SKIP
    if item.status == domain.SourceItemStatus.QUEUED:
        return ArchiveStepAction.RUN
    if item.status == domain.SourceItemStatus.ARCHIVING:
        return ArchiveStepAction.RESUME
    if item.status == domain.SourceItemStatus.FAILED:
        return ArchiveStepAction.FAIL
    raise domain.DomainError.invalid_status_transition(
        "SourceItem",
        item.status.value,
        "queued/archiving/uploading/cleanup/completed/failed",
    )


def decide_upload_on_retry(volume: ArchiveVolume) -> UploadStepAction:
    """What to do when the upload step runs again for this volume."""
    if volume.status == domain.ArchiveVolumeStatus.UPLOADED:
        return UploadStepAction.SKIP
    if volume.status == domain.ArchiveVolumeStatus.CREATED:
        return UploadStepAction.RUN
    if volume.status == domain.ArchiveVolumeStatus.UPLOADING:
        return UploadStepAction.CONTINUE
    if volume.status == domain.ArchiveVolumeStatus.FAILED:
        return UploadStepAction.FAIL
    raise domain.DomainError.invalid_status_transition(
        "ArchiveVolume",
        volume.status.value,
        "created/uploading/uploaded/failed",
    )


def decide_cleanup_on_retry(_volume: ArchiveVolume, item: SourceItem) -> CleanupStepAction:
    """What to do when the cleanup step runs again for this volume."""
    if item.status == domain.SourceItemStatus.COMPLETED:
        return CleanupStepAction.SKIP
    return CleanupStepAction.RUN
