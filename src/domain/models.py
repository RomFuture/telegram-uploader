"""Domain entities and status enums — pure data, no I/O.

See ``MANUAL.md`` in this package for layer overview and lifecycle diagrams.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from uuid import UUID, uuid4


class SessionStatus(str, Enum):
    """Lifecycle status of a backup profile (database session).

    Values: ``created``, ``running``, ``paused``, ``completed``, ``failed``, ``cancelled``.
    """

    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SourceItemStatus(str, Enum):
    """Lifecycle status of one file in the backup queue.

    Values: ``queued``, ``archiving``, ``uploading``, ``cleanup``, ``completed``, ``failed``.
    """

    QUEUED = "queued"
    ARCHIVING = "archiving"
    UPLOADING = "uploading"
    CLEANUP = "cleanup"
    COMPLETED = "completed"
    FAILED = "failed"


class ArchiveVolumeStatus(str, Enum):
    """Lifecycle status of one 7z split part awaiting or after Telegram upload.

    Values: ``created``, ``uploading``, ``uploaded``, ``failed``.
    """

    CREATED = "created"
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    FAILED = "failed"


def _now_utc() -> datetime:
    """Default timestamp factory for entity ``created_at`` fields."""
    return datetime.now(tz=UTC)


@dataclass(slots=True)
class Session:
    """Backup profile: display name, encryption key, and session-level status."""

    id: UUID
    profile_name: str
    encryption_key: str
    status: SessionStatus = SessionStatus.CREATED
    created_at: datetime = field(default_factory=_now_utc)

    @classmethod
    def create(cls, profile_name: str, encryption_key: str) -> "Session":
        """Low-level factory; prefer ``domain.create_session`` from actions."""
        return cls(id=uuid4(), profile_name=profile_name, encryption_key=encryption_key)


@dataclass(slots=True)
class SourceItem:
    """One user file enqueued for backup within a session."""

    id: UUID
    session_id: UUID
    source_path: Path
    display_name: str
    status: SourceItemStatus = SourceItemStatus.QUEUED
    created_at: datetime = field(default_factory=_now_utc)

    @classmethod
    def create(cls, session_id: UUID, source_path: Path, display_name: str) -> "SourceItem":
        """Low-level factory; prefer ``domain.create_source_item`` from actions."""
        return cls(
            id=uuid4(),
            session_id=session_id,
            source_path=source_path,
            display_name=display_name,
        )


@dataclass(slots=True)
class ArchiveVolume:
    """One part of a split 7z archive produced for Telegram upload."""

    id: UUID
    source_item_id: UUID
    file_name: str
    local_path: Path
    part_number: int
    status: ArchiveVolumeStatus = ArchiveVolumeStatus.CREATED
    external_file_id: str | None = None
    external_message_id: str | None = None
    provider_download_ref: str | None = None
    created_at: datetime = field(default_factory=_now_utc)

    @classmethod
    def create(
        cls,
        source_item_id: UUID,
        file_name: str,
        local_path: Path,
        part_number: int,
    ) -> "ArchiveVolume":
        """Low-level factory; prefer ``domain.create_archive_volume`` from actions."""
        return cls(
            id=uuid4(),
            source_item_id=source_item_id,
            file_name=file_name,
            local_path=local_path,
            part_number=part_number,
        )
