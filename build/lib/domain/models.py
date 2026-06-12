from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from uuid import UUID, uuid4


class SessionStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SourceItemStatus(str, Enum):
    QUEUED = "queued"
    ARCHIVING = "archiving"
    UPLOADING = "uploading"
    CLEANUP = "cleanup"
    COMPLETED = "completed"
    FAILED = "failed"


class ArchiveVolumeStatus(str, Enum):
    CREATED = "created"
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    FAILED = "failed"


def _now_utc() -> datetime:
    return datetime.now(tz=UTC)


@dataclass(slots=True)
class Session:
    id: UUID
    profile_name: str
    encryption_key: str
    status: SessionStatus = SessionStatus.CREATED
    created_at: datetime = field(default_factory=_now_utc)

    @classmethod
    def create(cls, profile_name: str, encryption_key: str) -> "Session":
        return cls(id=uuid4(), profile_name=profile_name, encryption_key=encryption_key)


@dataclass(slots=True)
class SourceItem:
    id: UUID
    session_id: UUID
    source_path: Path
    display_name: str
    status: SourceItemStatus = SourceItemStatus.QUEUED
    created_at: datetime = field(default_factory=_now_utc)

    @classmethod
    def create(cls, session_id: UUID, source_path: Path, display_name: str) -> "SourceItem":
        return cls(
            id=uuid4(),
            session_id=session_id,
            source_path=source_path,
            display_name=display_name,
        )


@dataclass(slots=True)
class ArchiveVolume:
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
        return cls(
            id=uuid4(),
            source_item_id=source_item_id,
            file_name=file_name,
            local_path=local_path,
            part_number=part_number,
        )
