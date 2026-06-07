from domain.errors import InvalidStatusTransition
from domain.models import ArchiveVolumeStatus, SessionStatus, SourceItemStatus


def ensure_session_status(
    status: SessionStatus,
    *allowed: SessionStatus,
    entity: str = "Session",
) -> None:
    if status not in allowed:
        raise InvalidStatusTransition.create(
            entity,
            status.value,
            "/".join(item.value for item in allowed),
        )


def ensure_source_item_status(
    status: SourceItemStatus,
    *allowed: SourceItemStatus,
    entity: str = "SourceItem",
) -> None:
    if status not in allowed:
        raise InvalidStatusTransition.create(
            entity,
            status.value,
            "/".join(item.value for item in allowed),
        )


def ensure_archive_volume_status(
    status: ArchiveVolumeStatus,
    *allowed: ArchiveVolumeStatus,
    entity: str = "ArchiveVolume",
) -> None:
    if status not in allowed:
        raise InvalidStatusTransition.create(
            entity,
            status.value,
            "/".join(item.value for item in allowed),
        )
