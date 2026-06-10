"""Domain actions — entity creation, status checks, and transitions."""

from dataclasses import replace
from pathlib import Path
from typing import overload
from uuid import UUID

from .errors import DomainError
from .models import (
    ArchiveVolume,
    ArchiveVolumeStatus,
    Session,
    SessionStatus,
    SourceItem,
    SourceItemStatus,
)

_Status = SessionStatus | SourceItemStatus | ArchiveVolumeStatus


@overload
def _with_status(entity: Session, status: SessionStatus) -> Session: ...


@overload
def _with_status(entity: SourceItem, status: SourceItemStatus) -> SourceItem: ...


@overload
def _with_status(entity: ArchiveVolume, status: ArchiveVolumeStatus) -> ArchiveVolume: ...


def _with_status(
    entity: Session | SourceItem | ArchiveVolume,
    status: _Status,
) -> Session | SourceItem | ArchiveVolume:
    return replace(entity, status=status)  # type: ignore[arg-type]


def _require_status(status: _Status, *allowed: _Status, entity: str) -> None:
    if status not in allowed:
        raise DomainError.invalid_status_transition(
            entity,
            status.value,
            "/".join(item.value for item in allowed),
        )


def create_session(profile_name: str, encryption_key: str) -> Session:
    """Create a new backup session in ``created`` status."""
    return Session.create(profile_name, encryption_key)


def create_source_item(session_id: UUID, source_path: Path, display_name: str) -> SourceItem:
    """Create a queued source item linked to the given session."""
    return SourceItem.create(session_id, source_path, display_name)


def create_archive_volume(
    source_item_id: UUID,
    file_name: str,
    local_path: Path,
    part_number: int,
) -> ArchiveVolume:
    """Create an archive volume part in ``created`` status (not yet uploaded)."""
    return ArchiveVolume.create(source_item_id, file_name, local_path, part_number)


def verify_session(session: Session, *, status: SessionStatus) -> None:
    """Raise if the session is not in the expected status."""
    _require_status(session.status, status, entity="Session")


def mark_session(session: Session, *, status: SessionStatus) -> Session:
    """Set the session status."""
    return _with_status(session, status)


def verify_source_item(item: SourceItem, *, status: SourceItemStatus) -> None:
    """Raise if the source item is not in the expected status."""
    _require_status(item.status, status, entity="SourceItem")


def mark_source_item(item: SourceItem, *, status: SourceItemStatus) -> SourceItem:
    """Set the source item status."""
    return _with_status(item, status)


def is_source_item(item: SourceItem, *, status: SourceItemStatus) -> bool:
    """Return whether the source item is in the given status."""
    return item.status == status


def verify_archive_volume(volume: ArchiveVolume, *, status: ArchiveVolumeStatus) -> None:
    """Raise if the archive volume is not in the expected status."""
    _require_status(volume.status, status, entity="ArchiveVolume")


def mark_archive_volume(volume: ArchiveVolume, *, status: ArchiveVolumeStatus) -> ArchiveVolume:
    """Set the archive volume status."""
    return _with_status(volume, status)


def mark_archive_volume_uploaded(
    volume: ArchiveVolume,
    *,
    external_file_id: str,
    external_message_id: str,
    provider_download_ref: str,
) -> ArchiveVolume:
    """Set status to ``uploaded`` and store provider metadata for restore."""
    return replace(
        volume,
        status=ArchiveVolumeStatus.UPLOADED,
        external_file_id=external_file_id,
        external_message_id=external_message_id,
        provider_download_ref=provider_download_ref,
    )
