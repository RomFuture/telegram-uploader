"""Create a new database (session) with a user-provided encryption key."""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

import domain as domain
from use_cases.shared.folders import DEFAULT_FOLDER_NAME
from use_cases.shared.mappers import domain_to_session_record
from use_cases.shared.persistence import BackupFolderRecord
from use_cases.shared.repositories.folder import FolderRepository
from use_cases.shared.repositories.session import SessionRepository
from use_cases.shared.types import Session


@dataclass(frozen=True, slots=True)
class CreateDatabaseUseCase:
    sessions: SessionRepository
    folders: FolderRepository

    def execute(self, profile_name: str, encryption_key: str) -> Session:
        name = profile_name.strip()
        key = encryption_key.strip()
        if not name:
            raise domain.DomainError(
                code="invalid_input",
                message="Database name is required",
            )
        if not key:
            raise domain.DomainError(
                code="invalid_input",
                message="Encryption key is required",
            )
        if self.sessions.find_by_profile_name(name) is not None:
            raise domain.DomainError.profile_already_exists(name)

        session = domain.create_session(name, key)
        self.sessions.add(domain_to_session_record(session))
        self.folders.add(
            BackupFolderRecord(
                id=uuid4(),
                session_id=session.id,
                name=DEFAULT_FOLDER_NAME,
                created_at=datetime.now(tz=UTC),
            )
        )
        return session
