"""Map persistence records ↔ domain entities."""

from pathlib import Path

import domain as domain
from use_cases.persistence import ArchiveVolumeRecord, SessionRecord, SourceItemRecord
from use_cases.types import ArchiveVolume, Session, SourceItem


def session_record_to_domain(record: SessionRecord) -> Session:
    return Session(
        id=record.id,
        profile_name=record.profile_name,
        encryption_key=record.encryption_key,
        status=domain.SessionStatus(record.status),
        created_at=record.created_at,
    )


def domain_to_session_record(session: Session) -> SessionRecord:
    return SessionRecord(
        id=session.id,
        profile_name=session.profile_name,
        encryption_key=session.encryption_key,
        status=session.status.value,
        created_at=session.created_at,
    )


def source_item_record_to_domain(record: SourceItemRecord) -> SourceItem:
    return SourceItem(
        id=record.id,
        session_id=record.session_id,
        source_path=Path(record.source_path),
        display_name=record.display_name,
        status=domain.SourceItemStatus(record.status),
        created_at=record.created_at,
    )


def domain_to_source_item_record(source_item: SourceItem) -> SourceItemRecord:
    return SourceItemRecord(
        id=source_item.id,
        session_id=source_item.session_id,
        source_path=str(source_item.source_path),
        display_name=source_item.display_name,
        status=source_item.status.value,
        created_at=source_item.created_at,
    )


def archive_volume_record_to_domain(record: ArchiveVolumeRecord) -> ArchiveVolume:
    return ArchiveVolume(
        id=record.id,
        source_item_id=record.source_item_id,
        file_name=record.file_name,
        local_path=Path(record.local_path),
        part_number=record.part_number,
        status=domain.ArchiveVolumeStatus(record.status),
        external_file_id=record.external_file_id,
        external_message_id=record.external_message_id,
        provider_download_ref=record.provider_download_ref,
        created_at=record.created_at,
    )


def domain_to_archive_volume_record(volume: ArchiveVolume) -> ArchiveVolumeRecord:
    return ArchiveVolumeRecord(
        id=volume.id,
        source_item_id=volume.source_item_id,
        file_name=volume.file_name,
        local_path=str(volume.local_path),
        part_number=volume.part_number,
        status=volume.status.value,
        external_file_id=volume.external_file_id,
        external_message_id=volume.external_message_id,
        provider_download_ref=volume.provider_download_ref,
        created_at=volume.created_at,
    )
