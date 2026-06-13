from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SessionResult:
    session_id: UUID
    profile_name: str
    status: str
    generated_encryption_key: str | None = None


@dataclass(frozen=True, slots=True)
class FolderResult:
    folder_id: UUID
    name: str


@dataclass(frozen=True, slots=True)
class QueueItemResult:
    source_item_id: UUID
    display_name: str
    status: str


@dataclass(frozen=True, slots=True)
class QueueItemSnapshotResult:
    source_item_id: UUID
    display_name: str
    status: str
    folder_id: UUID | None = None
    folder_name: str | None = None
    size_label: str = "—"
    modified_label: str = "—"


@dataclass(frozen=True, slots=True)
class SessionQueueSnapshotResult:
    session_id: UUID
    items: tuple[QueueItemSnapshotResult, ...]


@dataclass(frozen=True, slots=True)
class RestoreResult:
    session_id: UUID
    downloaded_paths: tuple[str, ...]
