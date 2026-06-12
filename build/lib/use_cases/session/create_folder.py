"""Create a folder within a session."""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

import domain as domain
from use_cases.shared.persistence import BackupFolderRecord
from use_cases.shared.repositories.folder import FolderRepository


@dataclass(frozen=True, slots=True)
class CreateFolderUseCase:
    folders: FolderRepository

    def execute(self, session_id: UUID, name: str) -> BackupFolderRecord:
        folder_name = name.strip()
        if not folder_name:
            raise domain.DomainError(
                code="invalid_input",
                message="Folder name is required",
            )
        if self.folders.find_by_name(session_id, folder_name) is not None:
            raise domain.DomainError(
                code="folder_already_exists",
                message=f"Folder already exists: {folder_name}",
            )
        record = BackupFolderRecord(
            id=uuid4(),
            session_id=session_id,
            name=folder_name,
            created_at=datetime.now(tz=UTC),
        )
        self.folders.add(record)
        return record
