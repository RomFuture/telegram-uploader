"""Load persistence records as domain entities with not-found guards."""

from uuid import UUID

import domain as domain
from use_cases.mappers import (
    archive_volume_record_to_domain,
    session_record_to_domain,
    source_item_record_to_domain,
)
from use_cases.persistence import ArchiveVolumeRecord, SessionRecord, SourceItemRecord
from use_cases.types import ArchiveVolume, Session, SourceItem


def require_session_record(record: SessionRecord | None, session_id: UUID) -> Session:
    return domain.require_session(
        session_record_to_domain(record) if record else None,
        session_id,
    )


def require_source_item_record(
    record: SourceItemRecord | None,
    source_item_id: UUID,
) -> SourceItem:
    return domain.require_source_item(
        source_item_record_to_domain(record) if record else None,
        source_item_id,
    )


def require_archive_volume_record(
    record: ArchiveVolumeRecord | None,
    volume_id: UUID,
) -> ArchiveVolume:
    return domain.require_archive_volume(
        archive_volume_record_to_domain(record) if record else None,
        volume_id,
    )


def map_source_items(records: list[SourceItemRecord]) -> list[SourceItem]:
    return [source_item_record_to_domain(record) for record in records]


def map_archive_volumes(records: list[ArchiveVolumeRecord]) -> list[ArchiveVolume]:
    return [archive_volume_record_to_domain(record) for record in records]


def require_archive_volumes_for_session(
    records: list[ArchiveVolumeRecord],
    session_id: UUID,
) -> list[ArchiveVolume]:
    domain.require_non_empty_volumes(records, session_id)
    return map_archive_volumes(records)
