from typing import Protocol

from use_cases.repositories.archive_volume import ArchiveVolumeRepository
from use_cases.repositories.loading import (
    map_archive_volumes,
    map_source_items,
    require_archive_volume_record,
    require_archive_volumes_for_session,
    require_session_record,
    require_source_item_record,
)
from use_cases.repositories.session import SessionRepository
from use_cases.repositories.source_item import SourceItemRepository


class Repositories(Protocol):
    """Bundle of repository ports injected into use cases."""

    sessions: SessionRepository
    source_items: SourceItemRepository
    archive_volumes: ArchiveVolumeRepository


__all__ = [
    "ArchiveVolumeRepository",
    "Repositories",
    "SessionRepository",
    "SourceItemRepository",
    "map_archive_volumes",
    "map_source_items",
    "require_archive_volume_record",
    "require_archive_volumes_for_session",
    "require_session_record",
    "require_source_item_record",
]
