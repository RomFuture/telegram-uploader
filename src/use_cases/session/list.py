"""List session profiles and folders for GUI."""

from dataclasses import dataclass
from uuid import UUID

from use_cases.shared.persistence import BackupFolderRecord
from use_cases.shared.repositories.folder import FolderRepository
from use_cases.shared.repositories.session import SessionRepository


@dataclass(frozen=True, slots=True)
class ListSessionProfilesUseCase:
    """List profile names for the Unlock screen dropdown."""

    sessions: SessionRepository

    def execute(self) -> tuple[str, ...]:
        return self.sessions.list_profiles()


@dataclass(frozen=True, slots=True)
class ListFoldersUseCase:
    """List virtual folders for a session."""

    folders: FolderRepository

    def execute(self, session_id: UUID) -> tuple[BackupFolderRecord, ...]:
        records = self.folders.list_by_session(session_id)
        return tuple(records)
