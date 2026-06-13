"""Create session profiles, folders, and related records."""

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

import domain as domain
from use_cases.shared.folders import DEFAULT_FOLDER_NAME
from use_cases.shared.mappers import domain_to_session_record
from use_cases.shared.persistence import BackupFolderRecord
from use_cases.shared.repositories.folder import FolderRepository
from use_cases.shared.repositories.session import SessionRepository
from use_cases.shared.types import Session


@dataclass(frozen=True, slots=True)
class SessionCreateOutcome:
    session: Session
    generated_encryption_key: str | None


@dataclass(frozen=True, slots=True)
class CreateSessionUseCase:
    """Create a session; generate encryption key when none is provided (tests / start_session)."""

    sessions: SessionRepository

    def execute(self, profile_name: str, encryption_key: str | None) -> SessionCreateOutcome:
        generated_key: str | None = None
        resolved_key = encryption_key.strip() if encryption_key else ""
        if not resolved_key:
            resolved_key = secrets.token_urlsafe(32)
            generated_key = resolved_key

        session = domain.create_session(profile_name, resolved_key)
        self.sessions.add(domain_to_session_record(session))
        return SessionCreateOutcome(session=session, generated_encryption_key=generated_key)


@dataclass(frozen=True, slots=True)
class CreateDatabaseUseCase:
    """Create a new database (session) with a user-provided encryption key and default folder."""

    sessions: SessionRepository
    folders: FolderRepository

    def execute(self, profile_name: str, encryption_key: str) -> Session:
        name = profile_name.strip()
        key = encryption_key.strip()
        if not name:
            raise domain.DomainError.required("Database name")
        if not key:
            raise domain.DomainError.required("Encryption key")
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


@dataclass(frozen=True, slots=True)
class CreateFolderUseCase:
    """Create a folder within a session."""

    folders: FolderRepository

    def execute(self, session_id: UUID, name: str) -> BackupFolderRecord:
        folder_name = name.strip()
        if not folder_name:
            raise domain.DomainError.required("Folder name")
        if self.folders.find_by_name(session_id, folder_name) is not None:
            raise domain.DomainError.folder_already_exists(folder_name)
        record = BackupFolderRecord(
            id=uuid4(),
            session_id=session_id,
            name=folder_name,
            created_at=datetime.now(tz=UTC),
        )
        self.folders.add(record)
        return record
