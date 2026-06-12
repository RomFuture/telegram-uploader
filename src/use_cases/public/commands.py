from dataclasses import dataclass
from pathlib import Path
from uuid import UUID


@dataclass(frozen=True, slots=True)
class StartSessionCommand:
    profile_name: str
    encryption_key: str | None = None


@dataclass(frozen=True, slots=True)
class UnlockSessionCommand:
    profile_name: str
    encryption_key: str


@dataclass(frozen=True, slots=True)
class CreateDatabaseCommand:
    profile_name: str
    encryption_key: str


@dataclass(frozen=True, slots=True)
class EnqueueFileCommand:
    session_id: UUID
    source_path: Path
    display_name: str
    folder_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class CreateFolderCommand:
    session_id: UUID
    name: str


@dataclass(frozen=True, slots=True)
class RestoreSessionCommand:
    session_id: UUID
    dest_path: Path


@dataclass(frozen=True, slots=True)
class RenameSourceItemCommand:
    source_item_id: UUID
    display_name: str


@dataclass(frozen=True, slots=True)
class MoveSourceItemCommand:
    source_item_id: UUID
    folder_id: UUID


@dataclass(frozen=True, slots=True)
class DeleteSourceItemCommand:
    source_item_id: UUID
