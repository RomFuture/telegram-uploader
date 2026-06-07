"""Domain guards — not-found checks and preconditions."""

from typing import TypeVar
from uuid import UUID

from .errors import DomainError
from .models import ArchiveVolume, Session, SourceItem

T = TypeVar("T")


def require_session(session: Session | None, session_id: UUID) -> Session:
    if session is None:
        raise DomainError.session_not_found(session_id)
    return session


def require_source_item(item: SourceItem | None, item_id: UUID) -> SourceItem:
    if item is None:
        raise DomainError.source_item_not_found(item_id)
    return item


def require_archive_volume(volume: ArchiveVolume | None, volume_id: UUID) -> ArchiveVolume:
    if volume is None:
        raise DomainError.archive_volume_not_found(volume_id)
    return volume


def require_non_empty_volumes(volumes: list[T], session_id: UUID) -> list[T]:
    if not volumes:
        raise DomainError.no_volumes_for_session(session_id)
    return volumes


def require_external_file_id(external_file_id: str | None, volume_id: UUID) -> str:
    if external_file_id is None:
        raise DomainError.missing_external_file_id(volume_id)
    return external_file_id
