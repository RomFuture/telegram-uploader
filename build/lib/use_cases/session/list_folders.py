"""List virtual folders for a session."""

from dataclasses import dataclass
from uuid import UUID

from use_cases.shared.persistence import BackupFolderRecord
from use_cases.shared.repositories.folder import FolderRepository


@dataclass(frozen=True, slots=True)
class ListFoldersUseCase:
    folders: FolderRepository

    def execute(self, session_id: UUID) -> tuple[BackupFolderRecord, ...]:
        records = self.folders.list_by_session(session_id)
        return tuple(records)
