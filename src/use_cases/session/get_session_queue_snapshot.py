"""Build a read-only queue table snapshot for GUI Refresh."""

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from use_cases.shared.repositories.folder import FolderRepository
from use_cases.shared.repositories.source_item import SourceItemRepository

_MISSING_LABEL = "—"


def format_bytes_as_size_label(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    if size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def format_item_modified_label(source_path: str, created_at: datetime) -> str:
    path = Path(source_path)
    if path.is_file():
        mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
        stamp = max(mtime, created_at.astimezone(UTC))
    else:
        stamp = created_at.astimezone(UTC)
    return stamp.astimezone().strftime("%m/%d/%y %I:%M %p")


def read_item_size_label(source_path: str) -> str:
    path = Path(source_path)
    if not path.is_file():
        return _MISSING_LABEL
    return format_bytes_as_size_label(path.stat().st_size)


@dataclass(frozen=True, slots=True)
class QueueItemSnapshot:
    source_item_id: UUID
    display_name: str
    status: str
    folder_id: UUID | None
    folder_name: str | None
    size_label: str
    modified_label: str


@dataclass(frozen=True, slots=True)
class SessionQueueSnapshot:
    session_id: UUID
    items: tuple[QueueItemSnapshot, ...]


@dataclass(frozen=True, slots=True)
class GetSessionQueueSnapshotUseCase:
    source_items: SourceItemRepository
    folders: FolderRepository

    def execute(self, session_id: UUID) -> SessionQueueSnapshot:
        folder_names = {
            folder.id: folder.name for folder in self.folders.list_by_session(session_id)
        }
        items = self.source_items.list_by_session(session_id)
        return SessionQueueSnapshot(
            session_id=session_id,
            items=tuple(
                QueueItemSnapshot(
                    source_item_id=item.id,
                    display_name=item.display_name,
                    status=item.status,
                    folder_id=item.folder_id,
                    folder_name=folder_names.get(item.folder_id) if item.folder_id else None,
                    size_label=read_item_size_label(item.source_path),
                    modified_label=format_item_modified_label(
                        item.source_path, item.created_at
                    ),
                )
                for item in items
            ),
        )
