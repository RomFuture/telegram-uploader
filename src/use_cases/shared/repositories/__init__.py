from typing import Protocol

from use_cases.shared.repositories.archive_volume import ArchiveVolumeRepository
from use_cases.shared.repositories.folder import FolderRepository
from use_cases.shared.repositories.loading import (
    map_archive_volumes,
    map_source_items,
    require_archive_volume_record,
    require_archive_volumes_for_session,
    require_session_record,
    require_source_item_record,
)
from use_cases.shared.repositories.session import SessionRepository
from use_cases.shared.repositories.source_item import SourceItemRepository


class Repositories(Protocol):
    """Bundle of repository ports injected into use cases."""

    sessions: SessionRepository
    folders: FolderRepository
    source_items: SourceItemRepository
    archive_volumes: ArchiveVolumeRepository


__all__ = [
    "ArchiveVolumeRepository",
    "FolderRepository",
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
