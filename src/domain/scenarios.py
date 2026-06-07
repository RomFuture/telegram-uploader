"""Scenario entry points — preconditions for pipeline steps."""

from .actions import ensure_archive_volume, ensure_session, ensure_source_item
from .guards import require_external_file_id
from .models import (
    ArchiveVolume,
    ArchiveVolumeStatus,
    Session,
    SessionStatus,
    SourceItem,
    SourceItemStatus,
)


def prepare_session_for_backup(session: Session) -> None:
    ensure_session(session, status=SessionStatus.RUNNING)


def prepare_source_item_for_archive(item: SourceItem) -> None:
    ensure_source_item(item, status=SourceItemStatus.QUEUED)


def prepare_archive_volume_for_upload(volume: ArchiveVolume) -> None:
    ensure_archive_volume(volume, status=ArchiveVolumeStatus.CREATED)


def external_file_id_for_restore(volume: ArchiveVolume) -> str:
    return require_external_file_id(volume.external_file_id, volume.id)
