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
    return Session.create(profile_name, encryption_key)


def create_source_item(session_id: UUID, source_path: Path, display_name: str) -> SourceItem:
    return SourceItem.create(session_id, source_path, display_name)


def create_archive_volume(
    source_item_id: UUID,
    file_name: str,
    local_path: Path,
    part_number: int,
) -> ArchiveVolume:
    return ArchiveVolume.create(source_item_id, file_name, local_path, part_number)


def ensure_session(session: Session, *, status: SessionStatus) -> None:
    _require_status(session.status, status, entity="Session")


def mark_session(session: Session, *, status: SessionStatus) -> Session:
    return _with_status(session, status)


def ensure_source_item(item: SourceItem, *, status: SourceItemStatus) -> None:
    _require_status(item.status, status, entity="SourceItem")


def mark_source_item(item: SourceItem, *, status: SourceItemStatus) -> SourceItem:
    return _with_status(item, status)


def is_source_item(item: SourceItem, *, status: SourceItemStatus) -> bool:
    return item.status == status


def ensure_archive_volume(volume: ArchiveVolume, *, status: ArchiveVolumeStatus) -> None:
    _require_status(volume.status, status, entity="ArchiveVolume")


def mark_archive_volume(volume: ArchiveVolume, *, status: ArchiveVolumeStatus) -> ArchiveVolume:
    return _with_status(volume, status)


def mark_archive_volume_uploaded(
    volume: ArchiveVolume,
    *,
    external_file_id: str,
    external_message_id: str,
    provider_download_ref: str,
) -> ArchiveVolume:
    return replace(
        volume,
        status=ArchiveVolumeStatus.UPLOADED,
        external_file_id=external_file_id,
        external_message_id=external_message_id,
        provider_download_ref=provider_download_ref,
    )
