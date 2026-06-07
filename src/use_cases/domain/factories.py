"""Factory helpers — the only way use case modules obtain new domain entities."""

from pathlib import Path
from uuid import UUID

from domain.models import ArchiveVolume, Session, SourceItem


def session_create(profile_name: str, encryption_key: str) -> Session:
    return Session.create(profile_name, encryption_key)


def source_item_create(session_id: UUID, source_path: Path, display_name: str) -> SourceItem:
    return SourceItem.create(session_id, source_path, display_name)


def archive_volume_create(
    source_item_id: UUID,
    file_name: str,
    local_path: Path,
    part_number: int,
) -> ArchiveVolume:
    return ArchiveVolume.create(source_item_id, file_name, local_path, part_number)
