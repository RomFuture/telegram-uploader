from typing import Protocol

from use_cases.repositories.archive_volume import ArchiveVolumeRepository
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
]
