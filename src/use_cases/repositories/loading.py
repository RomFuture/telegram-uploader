"""Map persistence records to domain entities; raise when repository lookup misses.

Not-found and empty-list checks live here (use_cases), not in ``domain``.
``domain`` owns status transitions and pipeline rules only.
"""

from uuid import UUID

from domain.errors import DomainError
from use_cases.mappers import (
    archive_volume_record_to_domain,
    session_record_to_domain,
    source_item_record_to_domain,
)
from use_cases.persistence import ArchiveVolumeRecord, SessionRecord, SourceItemRecord
from use_cases.types import ArchiveVolume, Session, SourceItem


def require_session_record(record: SessionRecord | None, session_id: UUID) -> Session:
    if record is None:
        raise DomainError.session_not_found(session_id)
    return session_record_to_domain(record)


def require_source_item_record(
    record: SourceItemRecord | None,
    source_item_id: UUID,
) -> SourceItem:
    if record is None:
        raise DomainError.source_item_not_found(source_item_id)
    return source_item_record_to_domain(record)


def require_archive_volume_record(
    record: ArchiveVolumeRecord | None,
    volume_id: UUID,
) -> ArchiveVolume:
    if record is None:
        raise DomainError.archive_volume_not_found(volume_id)
    return archive_volume_record_to_domain(record)


def map_source_items(records: list[SourceItemRecord]) -> list[SourceItem]:
    return [source_item_record_to_domain(record) for record in records]


def map_archive_volumes(records: list[ArchiveVolumeRecord]) -> list[ArchiveVolume]:
    return [archive_volume_record_to_domain(record) for record in records]


def require_archive_volumes_for_session(
    records: list[ArchiveVolumeRecord],
    session_id: UUID,
) -> list[ArchiveVolume]:
    if not records:
        raise DomainError.no_volumes_for_session(session_id)
    return map_archive_volumes(records)
